import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

import auth as authlib
import engine
import reports as reportlib
from defaults import default_project, default_tower

client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]

app = FastAPI(title="Aptimizer API")
api = APIRouter(prefix="/api")
logger = logging.getLogger("aptimizer")

WRITE_ROLES = ("admin", "engineer")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Resource not found")


async def get_current_user(request: Request) -> dict:
    return await authlib.current_user_from_request(request, db)


# ---------------------------------------------------------------- auth models
class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = "engineer"
    org: str = ""
    contact: str = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    name: Optional[str] = None
    org: Optional[str] = None
    contact: Optional[str] = None


class ProjectIn(BaseModel):
    name: str
    client: str = ""
    location: str = ""
    plot_reference: str = ""


class ProjectPatch(BaseModel):
    updates: Dict[str, Any]
    note: Optional[str] = None


class VersionIn(BaseModel):
    label: str


class ShareIn(BaseModel):
    email: EmailStr
    role: str = "viewer"


# ---------------------------------------------------------------- auth routes
@api.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    role = body.role if body.role in authlib.ROLES else "engineer"
    doc = {"name": body.name, "email": email, "password_hash": authlib.hash_password(body.password),
           "role": role, "org": body.org, "contact": body.contact, "created_at": now_iso()}
    res = await db.users.insert_one(doc)
    doc["_id"] = res.inserted_id
    access = authlib.create_access_token(str(res.inserted_id), email)
    authlib.set_auth_cookies(response, access, authlib.create_refresh_token(str(res.inserted_id)))
    return {"user": authlib.public_user(doc), "access_token": access}


@api.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    ip = request.client.host if request.client else "unknown"
    ident = f"{ip}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": ident})
    if attempt and attempt.get("count", 0) >= 5:
        locked_at = datetime.fromisoformat(attempt["last_at"])
        if (datetime.now(timezone.utc) - locked_at).total_seconds() < 900:
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email})
    if not user or not authlib.verify_password(body.password, user.get("password_hash", "")):
        await db.login_attempts.update_one(
            {"identifier": ident},
            {"$inc": {"count": 1}, "$set": {"last_at": now_iso()}}, upsert=True)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.login_attempts.delete_one({"identifier": ident})
    access = authlib.create_access_token(str(user["_id"]), email)
    authlib.set_auth_cookies(response, access, authlib.create_refresh_token(str(user["_id"])))
    return {"user": authlib.public_user(user), "access_token": access}


@api.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = authlib.decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = await db.users.find_one({"_id": oid(payload["sub"])})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    access = authlib.create_access_token(str(user["_id"]), user["email"])
    authlib.set_auth_cookies(response, access, authlib.create_refresh_token(str(user["_id"])))
    return {"user": authlib.public_user(user), "access_token": access}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return authlib.public_user(user)


@api.put("/users/me")
async def update_profile(body: ProfileIn, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"_id": user["_id"]}, {"$set": updates})
    fresh = await db.users.find_one({"_id": user["_id"]})
    return authlib.public_user(fresh)


@api.get("/users")
async def list_users(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    users = await db.users.find().sort("created_at", -1).to_list(500)
    return [authlib.public_user(u) for u in users]


# ---------------------------------------------------------------- helpers
def serialize_project(doc: dict) -> dict:
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    return d


async def load_project(project_id: str, user: dict, write: bool = False) -> dict:
    proj = await db.projects.find_one({"_id": oid(project_id)})
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    role = None
    if str(proj["owner_id"]) == str(user["_id"]):
        role = "admin"
    elif user.get("role") == "admin":
        role = "admin"
    else:
        share = await db.shares.find_one({"project_id": str(proj["_id"]), "user_id": str(user["_id"])})
        if share:
            role = share.get("role", "viewer")
    if role is None:
        raise HTTPException(status_code=403, detail="You do not have access to this project")
    if write and role not in WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Viewer role cannot modify this project")
    out = dict(proj)
    out["_access_role"] = role
    return out


async def log_activity(project_id: str, user: dict, action: str, detail: str = ""):
    await db.activity.insert_one({
        "project_id": project_id, "user_id": str(user["_id"]),
        "user_name": user.get("name") or user.get("email"),
        "action": action, "detail": detail, "at": now_iso(),
    })


# ---------------------------------------------------------------- projects
@api.get("/projects")
async def list_projects(user: dict = Depends(get_current_user)):
    shared = await db.shares.find({"user_id": str(user["_id"])}).to_list(500)
    shared_ids = [oid(s["project_id"]) for s in shared]
    query = {} if user.get("role") == "admin" else {
        "$or": [{"owner_id": str(user["_id"])}, {"_id": {"$in": shared_ids}}]}
    docs = await db.projects.find(query).sort("updated_at", -1).to_list(200)
    out = []
    for d in docs:
        a = engine.analyse(d)
        out.append({
            "id": str(d["_id"]), "name": d.get("name"), "client": d.get("client"),
            "location": d.get("location"), "status": d.get("status", "draft"),
            "plot_reference": d.get("plot_reference"),
            "updated_at": d.get("updated_at"), "created_at": d.get("created_at"),
            "owner_id": d.get("owner_id"),
            "shared": str(d["owner_id"]) != str(user["_id"]),
            "summary": {
                "plot_area_sqm": a["areas"]["plot_area_sqm"],
                "builtup_area_sqm": a["areas"]["builtup_area_sqm"],
                "total_units": a["areas"]["total_units"],
                "towers": len(d.get("towers") or []),
                "far": a["areas"]["far"],
                "cost_total": a["cost"]["total"],
                "compliance_score": a["compliance"]["score"],
            },
        })
    return out


@api.post("/projects")
async def create_project(body: ProjectIn, user: dict = Depends(get_current_user)):
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="Viewer role cannot create projects")
    doc = default_project(body.name, body.client, body.location, body.plot_reference, str(user["_id"]))
    doc["created_at"] = now_iso()
    doc["updated_at"] = now_iso()
    res = await db.projects.insert_one(doc)
    await log_activity(str(res.inserted_id), user, "project.created", body.name)
    doc["_id"] = res.inserted_id
    return serialize_project(doc)


@api.get("/projects/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user)
    role = proj.pop("_access_role")
    return {**serialize_project(proj), "access_role": role}


@api.put("/projects/{project_id}")
async def patch_project(project_id: str, body: ProjectPatch, user: dict = Depends(get_current_user)):
    await load_project(project_id, user, write=True)
    allowed = {"name", "client", "location", "plot_reference", "status", "plot", "towers", "parking",
               "config", "quantity_ratios", "rates", "labour_rates", "equipment_rates",
               "utility_config", "compliance_rules"}
    updates = {k: v for k, v in body.updates.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    updates["updated_at"] = now_iso()
    await db.projects.update_one({"_id": oid(project_id)}, {"$set": updates})
    await log_activity(project_id, user, "project.updated",
                       body.note or ", ".join(k for k in updates if k != "updated_at"))
    proj = await db.projects.find_one({"_id": oid(project_id)})
    return serialize_project(proj)


@api.delete("/projects/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user, write=True)
    if str(proj["owner_id"]) != str(user["_id"]) and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only the owner or an admin can delete a project")
    await db.projects.delete_one({"_id": oid(project_id)})
    await db.versions.delete_many({"project_id": project_id})
    await db.shares.delete_many({"project_id": project_id})
    return {"ok": True}


@api.post("/projects/{project_id}/towers")
async def add_tower(project_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user, write=True)
    towers = proj.get("towers") or []
    tower = default_tower(f"Tower {chr(65 + len(towers))}")
    towers.append(tower)
    await db.projects.update_one({"_id": oid(project_id)},
                                 {"$set": {"towers": towers, "updated_at": now_iso()}})
    await log_activity(project_id, user, "tower.added", tower["name"])
    return {"tower": tower, "towers": towers}


@api.get("/projects/{project_id}/analysis")
async def project_analysis(project_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user)
    return engine.analyse(proj)


class AnalyseIn(BaseModel):
    project: Dict[str, Any]


@api.post("/analyse")
async def analyse_live(body: AnalyseIn, user: dict = Depends(get_current_user)):
    """Stateless calculation endpoint for live editing before save."""
    return engine.analyse(body.project)


# ---------------------------------------------------------------- versions
@api.get("/projects/{project_id}/versions")
async def list_versions(project_id: str, user: dict = Depends(get_current_user)):
    await load_project(project_id, user)
    docs = await db.versions.find({"project_id": project_id}).sort("at", -1).to_list(100)
    return [{"id": str(d["_id"]), "label": d["label"], "at": d["at"],
             "user_name": d.get("user_name", "")} for d in docs]


@api.post("/projects/{project_id}/versions")
async def create_version(project_id: str, body: VersionIn, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user, write=True)
    proj.pop("_access_role", None)
    snapshot = serialize_project(proj)
    snapshot.pop("id", None)
    res = await db.versions.insert_one({
        "project_id": project_id, "label": body.label, "at": now_iso(),
        "user_name": user.get("name") or user.get("email"), "snapshot": snapshot})
    await log_activity(project_id, user, "version.saved", body.label)
    return {"id": str(res.inserted_id), "label": body.label}


@api.post("/projects/{project_id}/versions/{version_id}/restore")
async def restore_version(project_id: str, version_id: str, user: dict = Depends(get_current_user)):
    await load_project(project_id, user, write=True)
    v = await db.versions.find_one({"_id": oid(version_id), "project_id": project_id})
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    snap = dict(v["snapshot"])
    snap.pop("created_at", None)
    snap["updated_at"] = now_iso()
    await db.projects.update_one({"_id": oid(project_id)}, {"$set": snap})
    await log_activity(project_id, user, "version.restored", v["label"])
    proj = await db.projects.find_one({"_id": oid(project_id)})
    return serialize_project(proj)


# ---------------------------------------------------------------- sharing & activity
@api.get("/projects/{project_id}/shares")
async def list_shares(project_id: str, user: dict = Depends(get_current_user)):
    await load_project(project_id, user)
    docs = await db.shares.find({"project_id": project_id}).to_list(100)
    return [{"id": str(d["_id"]), "email": d["email"], "role": d["role"],
             "user_id": d["user_id"], "at": d.get("at")} for d in docs]


@api.post("/projects/{project_id}/shares")
async def share_project(project_id: str, body: ShareIn, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user, write=True)
    if proj["_access_role"] != "admin":
        raise HTTPException(status_code=403, detail="Only project admins can share")
    target = await db.users.find_one({"email": body.email.lower()})
    if not target:
        raise HTTPException(status_code=404, detail="No registered user with that email")
    if str(target["_id"]) == str(proj["owner_id"]):
        raise HTTPException(status_code=400, detail="Owner already has full access")
    role = body.role if body.role in authlib.ROLES else "viewer"
    await db.shares.update_one(
        {"project_id": project_id, "user_id": str(target["_id"])},
        {"$set": {"email": target["email"], "role": role, "at": now_iso()}}, upsert=True)
    await log_activity(project_id, user, "project.shared", f"{target['email']} as {role}")
    return {"ok": True, "email": target["email"], "role": role}


@api.delete("/projects/{project_id}/shares/{share_id}")
async def unshare(project_id: str, share_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user, write=True)
    if proj["_access_role"] != "admin":
        raise HTTPException(status_code=403, detail="Only project admins can manage sharing")
    await db.shares.delete_one({"_id": oid(share_id)})
    await log_activity(project_id, user, "project.unshared", share_id)
    return {"ok": True}


@api.get("/projects/{project_id}/activity")
async def project_activity(project_id: str, user: dict = Depends(get_current_user)):
    await load_project(project_id, user)
    docs = await db.activity.find({"project_id": project_id}).sort("at", -1).to_list(200)
    return [{"id": str(d["_id"]), "user_name": d.get("user_name"), "action": d["action"],
             "detail": d.get("detail", ""), "at": d["at"]} for d in docs]


# ---------------------------------------------------------------- reports
@api.get("/projects/{project_id}/reports/{report_type}")
async def download_report(project_id: str, report_type: str, user: dict = Depends(get_current_user)):
    if report_type not in reportlib.REPORT_TITLES:
        raise HTTPException(status_code=400, detail="Unknown report type")
    proj = await load_project(project_id, user)
    proj.pop("_access_role", None)
    pdf = reportlib.build_pdf(report_type, proj, engine.analyse(proj))
    name = f"{proj.get('name', 'project').replace(' ', '_')}_{report_type}.pdf"
    import io
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


@api.get("/projects/{project_id}/boq.xlsx")
async def download_boq_excel(project_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user)
    proj.pop("_access_role", None)
    xl = reportlib.build_boq_excel(proj, engine.analyse(proj))
    name = f"{proj.get('name', 'project').replace(' ', '_')}_BOQ.xlsx"
    import io
    return StreamingResponse(
        io.BytesIO(xl),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}"'})


@api.get("/defaults")
async def get_defaults():
    return {"ratios": engine.DEFAULT_RATIOS, "rates": engine.DEFAULT_RATES,
            "rules": engine.DEFAULT_RULES,
            "unit_types": ["studio", "1bhk", "2bhk", "3bhk", "4bhk", "penthouse", "custom"],
            "room_types": ["living", "bedroom", "kitchen", "bathroom", "balcony", "utility", "common"],
            "stair_types": ["dog-legged", "open-well", "spiral", "straight-flight"]}


@api.get("/")
async def root():
    return {"service": "Aptimizer API", "status": "ok"}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000"), "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.projects.create_index("owner_id")
    await db.shares.create_index([("project_id", 1), ("user_id", 1)])
    await db.activity.create_index("project_id")
    admin_email = os.environ["ADMIN_EMAIL"].lower()
    admin_password = os.environ["ADMIN_PASSWORD"]
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "name": "Aptimizer Admin", "email": admin_email,
            "password_hash": authlib.hash_password(admin_password), "role": "admin",
            "org": "Aptimizer", "contact": "", "created_at": now_iso()})
        logger.info("Seeded admin user %s", admin_email)
    elif not authlib.verify_password(admin_password, existing.get("password_hash", "")):
        await db.users.update_one({"email": admin_email},
                                  {"$set": {"password_hash": authlib.hash_password(admin_password)}})


@app.on_event("shutdown")
async def shutdown():
    client.close()
