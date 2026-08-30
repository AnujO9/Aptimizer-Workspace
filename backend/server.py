import math
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

import ai as ailib
import auth as authlib
import engine
import engineering as englib
import finance as financelib
import gis as gislib
import iscodes as iscodes
import layout as layoutlib
import reports as reportlib
import schedule as schedlib
import siteplan as siteplanlib
from defaults import default_project, default_tower, floor_layout_entry

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
    latitude: Optional[float] = None
    longitude: Optional[float] = None


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
            "public_token": d.get("public_token"),
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
    doc = default_project(body.name, body.client, body.location, body.plot_reference, str(user["_id"]),
                          latitude=body.latitude, longitude=body.longitude)
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
               "utility_config", "compliance_rules", "gis", "engineering", "society_amenities"}
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


# ---------------------------------------------------------------- public compliance link
@api.post("/projects/{project_id}/public-link")
async def create_public_link(project_id: str, user: dict = Depends(get_current_user)):
    await load_project(project_id, user, write=True)
    token = secrets.token_urlsafe(16)
    await db.projects.update_one({"_id": oid(project_id)},
                                 {"$set": {"public_token": token, "updated_at": now_iso()}})
    await log_activity(project_id, user, "public_link.created", "compliance share link")
    return {"public_token": token}


@api.delete("/projects/{project_id}/public-link")
async def revoke_public_link(project_id: str, user: dict = Depends(get_current_user)):
    await load_project(project_id, user, write=True)
    await db.projects.update_one({"_id": oid(project_id)}, {"$unset": {"public_token": ""}})
    await log_activity(project_id, user, "public_link.revoked", "compliance share link")
    return {"ok": True}


@api.get("/public/compliance/{token}")
async def public_compliance(token: str):
    proj = await db.projects.find_one({"public_token": token})
    if not proj:
        raise HTTPException(status_code=404, detail="This link is invalid or has been revoked")
    a = engine.analyse(proj)
    ar = a["areas"]
    return {
        "project": {"name": proj.get("name"), "client": proj.get("client"),
                    "location": proj.get("location"), "plot_reference": proj.get("plot_reference"),
                    "status": proj.get("status", "draft"), "updated_at": proj.get("updated_at")},
        "metrics": {"plot_area_sqm": ar["plot_area_sqm"], "plot_area_acres": ar["plot_area_acres"],
                    "builtup_area_sqm": ar["builtup_area_sqm"], "far": ar["far"], "fsi": ar["fsi"],
                    "ground_coverage_pct": ar["ground_coverage_pct"], "open_space_pct": ar["open_space_pct"],
                    "total_units": ar["total_units"], "towers": len(proj.get("towers") or []),
                    "max_height_m": ar["max_height_m"]},
        "compliance": a["compliance"],
    }


# ---------------------------------------------------------------- scheme comparison
@api.get("/projects/{project_id}/versions/compare")
def _scheme_geometry(doc, an):
    """Footprint rectangles and tower positions, for comparing two schemes by shape.

    Scalar metrics cannot tell two schemes apart when one is four squat towers and the
    other is two slender ones on the same FAR. This returns only what is needed to draw
    them side by side -- a bounding box and one rectangle per tower, in plot-local metres
    -- never the full polygon vertex arrays.
    """
    plot = doc.get("plot") or {}
    area = float(an["areas"]["plot_area_sqm"] or 0)
    length = float(plot.get("length") or 0)
    width = float(plot.get("width") or 0)

    # The recorded length x width often disagrees with the drawn polygon's area -- the
    # sample project is 80 x 50 against a 15,219 m2 polygon. Drawing the box anyway would
    # put the towers on 4,000 m2 and make the coverage look four times what it is, so the
    # box is only trusted when it roughly agrees with the area it claims to enclose.
    box_ok = length > 0 and width > 0 and area > 0 and abs(length * width - area) / area < 0.15
    if box_ok:
        basis = "recorded plot dimensions"
    elif area > 0:
        # Keep the drawn aspect ratio where there is one, but scale it to the real area.
        ratio = (length / width) if (length > 0 and width > 0) else 1.0
        width = math.sqrt(area / ratio)
        length = width * ratio
        basis = "scaled to the drawn polygon area"
    else:
        length = width = 0.0
        basis = "no plot geometry"

    towers = []
    positioned = 0
    for t, tm in zip(doc.get("towers") or [], an["areas"]["towers"]):
        fp = float(tm.get("footprint_sqm") or 0)
        # Towers carry an area, not a shape; assume the square that area implies, which is
        # what the massing tools already do.
        side = math.sqrt(fp) if fp > 0 else 0
        pos = t.get("position") or {}
        px, py = float(pos.get("x") or 0), float(pos.get("y") or 0)
        if px or py:
            positioned += 1
        towers.append({
            "id": tm.get("id"), "name": tm.get("name"),
            "x": round(px, 2), "y": round(py, 2),
            "w": round(side, 2), "d": round(side, 2),
            "rotation_deg": round(float(t.get("rotation_deg") or 0), 1),
            "floors": tm.get("floors"), "height_m": tm.get("height_m"),
            "footprint_sqm": round(fp, 1),
        })

    # Without stored positions every tower sits at the origin, which draws them stacked on
    # top of each other. Spread them along the plot instead and mark the layout indicative,
    # so the comparison shows massing rather than a single misleading square.
    placed = "as positioned"
    if towers and positioned == 0:
        gap = 4.0
        run = sum(t["w"] for t in towers) + gap * (len(towers) - 1)
        cursor = max((length - run) / 2, 0.0)
        for t in towers:
            t["x"] = round(cursor, 2)
            t["y"] = round(max((width - t["d"]) / 2, 0.0), 2)
            cursor += t["w"] + gap
        placed = "indicative -- no tower positions recorded"

    return {
        "plot": {"length_m": round(length, 2), "width_m": round(width, 2),
                 "area_sqm": area, "basis": basis,
                 "orientation_deg": float(plot.get("orientation_deg") or 0)},
        "towers": towers, "placement": placed,
        "ground_coverage_pct": an["areas"]["ground_coverage_pct"],
        "open_space_pct": an["areas"]["open_space_pct"],
    }


async def compare_versions(project_id: str, a: str = "", b: str = "",
                           user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user)

    async def scheme(vid):
        if vid == "current":
            return {"id": "current", "label": "Current project", "at": proj.get("updated_at"),
                    "doc": proj}
        v = await db.versions.find_one({"_id": oid(vid), "project_id": project_id})
        if not v:
            raise HTTPException(status_code=404, detail="Version not found")
        return {"id": vid, "label": v["label"], "at": v["at"], "doc": v["snapshot"]}

    out = []
    for vid in (a, b):
        if not vid:
            raise HTTPException(status_code=400, detail="Pick two schemes to compare")
        s = await scheme(vid)
        an = engine.analyse(s["doc"])
        ar, co, pk = an["areas"], an["compliance"], an["parking"]
        util = an["utilities"]

        # Sustainability and money are what a scheme is actually chosen on, and neither
        # was comparable before: two layouts with identical areas can differ by hundreds
        # of tonnes of carbon and several points of margin.
        try:
            eng = englib.analyse_engineering(s["doc"], an)
            green = eng["modules"]["green"]
            carbon = eng["modules"]["carbon"]
            green_score = next((o["value"] for o in green["outputs"] if o["label"] == "Score"), None)
            carbon_per_sqm = carbon["derived"]["per_sqm_kg"]
            carbon_total = carbon["derived"]["total_tco2e"]
            trees = eng["summary"].get("trees_required")
        except Exception:            # a scheme too incomplete to engineer still compares
            green_score = carbon_per_sqm = carbon_total = trees = None

        # Water efficiency: how much of the yearly demand rainwater harvesting can meet.
        demand_yr = float(util.get("water_demand_lpd") or 0) * 365.0
        rwh_yr = float(util.get("rwh_annual_litres") or 0)
        water_eff = round(rwh_yr / demand_yr * 100, 1) if demand_yr else None

        try:
            fin = financelib.analyse(s["doc"], an, s["doc"].get("finance"))
            roi, margin = fin["profit"]["roi_pct"], fin["profit"]["margin_pct"]
            irr, payback = fin["profit"]["irr_pct"], fin["timing"]["payback_month"]
            revenue = fin["revenue"]["gross"]
        except Exception:
            roi = margin = irr = payback = revenue = None

        out.append({
            "id": s["id"], "label": s["label"], "at": s["at"],
            "metrics": {
                "Plot area (m²)": ar["plot_area_sqm"], "Built-up area (m²)": ar["builtup_area_sqm"],
                "Carpet area (m²)": ar["carpet_area_sqm"], "FAR": ar["far"], "FSI": ar["fsi"],
                "Ground coverage (%)": ar["ground_coverage_pct"], "Open space (%)": ar["open_space_pct"],
                "Towers": len(s["doc"].get("towers") or []), "Total units": ar["total_units"],
                "Max height (m)": ar["max_height_m"], "Density (units/acre)": ar["density_units_per_acre"],
                "Parking required": pk["required_slots"], "Parking provided": pk["provided_slots"],
                "Total cost (INR)": an["cost"]["total"], "Cost per flat (INR)": an["cost"]["per_unit"],
                "Cost per m² (INR)": an["cost"]["per_sqm"],
                "Compliance passed": f"{co['passed']}/{co['total']}", "Compliance score (%)": co["score"],
                "Green score (%)": green_score,
                "Embodied carbon (tCO₂e)": carbon_total,
                "Carbon per m² (kgCO₂e)": carbon_per_sqm,
                "Water met by rainwater (%)": water_eff,
                "Trees required": trees,
                "Gross revenue (INR)": revenue,
                "Return on cost (%)": roi,
                "Profit margin (%)": margin,
                "Annual IRR (%)": irr,
                "Cash positive (month)": payback,
            },
            "geometry": _scheme_geometry(s["doc"], an),
        })
    keys = list(out[0]["metrics"].keys())
    return {"schemes": out, "keys": keys, "currency": "INR"}


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


# ---------------------------------------------------------------- per-floor room layout
class FloorLayoutIn(BaseModel):
    floor: int
    regenerate: bool = False


@api.post("/projects/{project_id}/towers/{tower_id}/floor-layout")
async def floor_layout(project_id: str, tower_id: str, body: FloorLayoutIn,
                       user: dict = Depends(get_current_user)):
    """Fetch (generating on first visit) or explicitly regenerate one floor's room layout.
    Existing layouts are never silently overwritten — only `regenerate: true` reseeds a
    floor, so hand-edited rooms survive normal navigation between floors/towers."""
    if body.floor < 1:
        raise HTTPException(status_code=400, detail="Floor must be 1 or higher")
    proj = await load_project(project_id, user, write=True)
    towers = proj.get("towers") or []
    tower = next((t for t in towers if t.get("id") == tower_id), None)
    if not tower:
        raise HTTPException(status_code=404, detail="Tower not found")

    tower.setdefault("floor_layouts", {})
    key = str(body.floor)
    existing = tower["floor_layouts"].get(key)
    current_hash = layoutlib.unit_mix_hash(tower)

    if existing and not body.regenerate:
        return {"tower": tower, "towers": towers, "rooms": existing["rooms"],
                "validation": existing.get("validation") or {},
                "stale": existing.get("unit_mix_hash") != current_hash}

    nonce = (int(existing.get("seed", -1)) + 1) if (existing and body.regenerate) else 0
    entry = floor_layout_entry(tower, body.floor, nonce)
    tower["floor_layouts"][key] = entry
    if body.floor == 1:
        tower["rooms"] = entry["rooms"]

    await db.projects.update_one({"_id": oid(project_id)},
                                 {"$set": {"towers": towers, "updated_at": now_iso()}})
    await log_activity(project_id, user, "tower.floor_layout_generated",
                       f"{tower.get('name')} · floor {body.floor}")
    return {"tower": tower, "towers": towers, "rooms": entry["rooms"],
            "validation": entry.get("validation") or {}, "stale": False}


@api.get("/projects/{project_id}/analysis")
async def project_analysis(project_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user)
    return engine.analyse(proj)


class AnalyseIn(BaseModel):
    project: Dict[str, Any]


class GisIn(BaseModel):
    radius_m: int = 500


@api.post("/analyse")
async def analyse_live(body: AnalyseIn, user: dict = Depends(get_current_user)):
    """Stateless calculation endpoint for live editing before save."""
    return engine.analyse(body.project)


# ---------------------------------------------------------------- IS/NBC engineering modules
@api.post("/engineering/analyse")
async def engineering_live(body: AnalyseIn, user: dict = Depends(get_current_user)):
    """Stateless IS/NBC module calculations for live editing."""
    base = engine.analyse(body.project)
    return englib.analyse_engineering(body.project, base)


@api.get("/projects/{project_id}/engineering")
async def engineering_for_project(project_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user)
    return englib.analyse_engineering(proj, engine.analyse(proj))


# ---------------------------------------------------------------- site layout engine
class SiteLayoutIn(BaseModel):
    """Partial config override; anything omitted falls back to SiteLayoutConfig defaults."""
    config: Dict[str, Any] = Field(default_factory=dict)


class SiteLayoutLiveIn(SiteLayoutIn):
    project: Dict[str, Any]


@api.post("/projects/{project_id}/site-layout/envelope")
async def site_layout_envelope(project_id: str, body: SiteLayoutIn,
                               user: dict = Depends(get_current_user)):
    """Stage 1 — buildable envelope for a saved project."""
    proj = await load_project(project_id, user)
    return siteplanlib.buildable_envelope(proj, body.config)


@api.post("/site-layout/envelope")
async def site_layout_envelope_live(body: SiteLayoutLiveIn,
                                    user: dict = Depends(get_current_user)):
    """Stateless envelope for live editing before save — mirrors /analyse."""
    return siteplanlib.buildable_envelope(body.project, body.config)


@api.post("/projects/{project_id}/site-layout/reserve")
async def site_layout_reserve(project_id: str, body: SiteLayoutIn,
                              user: dict = Depends(get_current_user)):
    """Stage 2 — envelope plus reserved roads, amenities and the residual packable region."""
    proj = await load_project(project_id, user)
    return siteplanlib.reserve_site(proj, body.config)


@api.post("/site-layout/reserve")
async def site_layout_reserve_live(body: SiteLayoutLiveIn,
                                   user: dict = Depends(get_current_user)):
    """Stateless reservation for live editing before save."""
    return siteplanlib.reserve_site(body.project, body.config)


@api.post("/projects/{project_id}/site-layout/plan")
async def site_layout_plan(project_id: str, body: SiteLayoutIn,
                           user: dict = Depends(get_current_user)):
    """Stage 3 — full layout: envelope, reservation and packed towers."""
    proj = await load_project(project_id, user)
    return siteplanlib.plan_site(proj, body.config)


@api.post("/site-layout/plan")
async def site_layout_plan_live(body: SiteLayoutLiveIn,
                                user: dict = Depends(get_current_user)):
    """Stateless full layout for live editing before save."""
    return siteplanlib.plan_site(body.project, body.config)


class RecommendIn(BaseModel):
    plot_area_sqm: float
    road_width_m: float = 0.0
    city: str = ""
    state: str = ""
    floor_height: float = 3.0
    area_per_unit: float = 95.0
    far_override: Optional[float] = None


@api.post("/site-layout/recommend")
async def site_layout_recommend(body: RecommendIn, user: dict = Depends(get_current_user)):
    """Recommend setbacks, height, floors and unit yield from the plot and its frontage."""
    return siteplanlib.recommend_controls(
        plot_area=body.plot_area_sqm, road_width=body.road_width_m,
        city=body.city, state=body.state, floor_height=body.floor_height,
        area_per_unit=body.area_per_unit, far_override=body.far_override)


@api.get("/site-layout/defaults")
async def site_layout_defaults():
    return {"config": siteplanlib.SiteLayoutConfig().to_dict()}


@api.get("/iscodes")
async def code_library(q: str = "", id: str = ""):
    term = (q or "").lower().strip()
    entries = iscodes.CODE_LIBRARY
    if id:
        entries = [c for c in entries if c["id"] == id]
    elif term:
        entries = [c for c in entries if term in c["code"].lower() or term in c["topic"].lower()
                   or term in c["key_value"].lower() or term in c["clause"].lower()
                   or term in c.get("keywords", "")]
    return {"entries": entries, "count": len(entries), "query": q}


@api.get("/cities")
async def city_list(q: str = ""):
    term = (q or "").lower().strip()
    items = [{"city": name, "state": v[0], "zone": v[1], "wind_speed": v[2],
              "annual_rainfall_mm": v[3], "rain_intensity_mm_hr": v[4]}
             for name, v in sorted(iscodes.CITIES.items())]
    if term:
        items = [i for i in items if term in i["city"].lower() or term in i["state"].lower()]
    return {"cities": items, "count": len(items),
            "soils": [{"key": k, **v} for k, v in iscodes.SOILS.items()],
            "exposures": list(iscodes.EXPOSURE.keys()),
            "structural_systems": list(iscodes.RESPONSE_R.keys()),
            "green_checklist": iscodes.GREEN_CHECKLIST}


# ---------------------------------------------------------------- GIS & site intelligence
@api.get("/projects/{project_id}/gis")
async def get_gis(project_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user)
    stored = proj.get("gis")
    coords = (proj.get("plot") or {}).get("coordinates") or []
    stale = bool(stored) and stored.get("polygon_signature") != gislib._signature(coords)
    return {"gis": stored, "stale": stale, "has_polygon": len(coords) >= 3}


@api.post("/projects/{project_id}/gis/analyse")
async def run_gis(project_id: str, body: GisIn, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user, write=True)
    try:
        result = await gislib.analyse_site(proj, body.radius_m)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.projects.update_one({"_id": oid(project_id)},
                                 {"$set": {"gis": result, "updated_at": now_iso()}})
    await log_activity(project_id, user, "gis.analysed",
                       f"radius {result['radius_m']} m · suitability {result['suitability']['score']}")
    return {"gis": result, "stale": False, "has_polygon": True}


# ---------------------------------------------------------------- AI assistance
# Every AI feature shares one shape: build a context dict out of numbers the app has
# ALREADY computed, hand it to ai.generate_markdown with a task-specific system prompt,
# and store the markdown on the project so it survives a reload. The model never
# calculates anything -- it only explains what the engine produced.

async def _run_ai(kind: str, context: dict, *, store_at: str = "", project_id: str = "",
                  user: dict = None, activity: str = "") -> dict:
    """Shared tail of every AI endpoint: call the model, store, log."""
    try:
        result = await ailib.generate_markdown(
            ailib.PROMPTS[kind],
            "Use only the JSON data below.\n\n" + ailib.context_block(context),
            session_hint=f"{kind}-{project_id}",
        )
    except ailib.AIUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ailib.AIFailed as exc:
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {exc}")

    summary = {"text": result["text"], "model": result["model"],
               "provider": result["provider"], "generated_at": now_iso()}
    if store_at and project_id:
        await db.projects.update_one({"_id": oid(project_id)},
                                     {"$set": {store_at: summary, "updated_at": now_iso()}})
    if activity and project_id and user:
        await log_activity(project_id, user, activity, f"{result['model']} analysis generated")
    return summary


@api.get("/ai/status")
async def ai_status(user: dict = Depends(get_current_user)):
    """Lets the UI grey out AI buttons (and say why) instead of failing on click."""
    return ailib.provider()


@api.post("/projects/{project_id}/gis/ai-summary")
async def gis_ai_summary(project_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user, write=True)
    stored = proj.get("gis")
    if not stored:
        raise HTTPException(status_code=400, detail="Run the site analysis before generating an AI summary")
    context = gislib.ai_context(proj, stored)
    return await _run_ai("gis", context, store_at="gis.ai_summary",
                         project_id=project_id, user=user, activity="gis.ai_summary")


@api.post("/projects/{project_id}/ai/compliance")
async def ai_compliance(project_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user, write=True)
    an = engine.analyse(proj)
    comp = an["compliance"]
    context = {
        "project": {"name": proj.get("name"), "location": proj.get("location")},
        "score_pct": comp["score"], "passed": comp["passed"], "failed": comp["failed"],
        "total_rules": comp["total"], "overall": comp["overall"],
        "measured_parameters": comp["params"],
        "rules": [{"code": r["code"], "label": r["label"], "param": r["param"],
                   "requirement": f"{r['operator']} {r['threshold']}{r.get('unit') or ''}",
                   "actual": r["actual"], "status": r["status"]} for r in comp["results"]],
        "context_for_fixes": {
            "far": an["areas"]["far"], "ground_coverage_pct": an["areas"]["ground_coverage_pct"],
            "open_space_pct": an["areas"]["open_space_pct"],
            "total_units": an["areas"]["total_units"],
            "parking_required": an["parking"]["required_slots"],
            "parking_provided": an["parking"]["provided_slots"],
            "towers": [{"name": t.get("name"), "floors": t.get("floors")}
                       for t in (proj.get("towers") or [])],
        },
    }
    return await _run_ai("compliance", context, store_at="ai.compliance",
                         project_id=project_id, user=user, activity="ai.compliance")


@api.post("/projects/{project_id}/ai/report")
async def ai_report(project_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user, write=True)
    an = engine.analyse(proj)
    ar, co, pk, cost = an["areas"], an["compliance"], an["parking"], an["cost"]
    context = {
        "project": {"name": proj.get("name"), "client": proj.get("client"),
                    "location": proj.get("location"), "status": proj.get("status")},
        "scale": {"plot_area_sqm": ar["plot_area_sqm"], "plot_area_acres": ar["plot_area_acres"],
                  "builtup_area_sqm": ar["builtup_area_sqm"], "carpet_area_sqm": ar["carpet_area_sqm"],
                  "far": ar["far"], "fsi": ar["fsi"],
                  "ground_coverage_pct": ar["ground_coverage_pct"],
                  "open_space_pct": ar["open_space_pct"], "total_units": ar["total_units"],
                  "max_height_m": ar["max_height_m"],
                  "density_units_per_acre": ar["density_units_per_acre"],
                  "tower_count": len(proj.get("towers") or [])},
        "cost_inr": {"total": cost["total"], "per_unit": cost["per_unit"],
                     "per_sqm": cost["per_sqm"], "material": cost["material"],
                     "labour": cost["labour"], "equipment": cost["equipment"]},
        "parking": {"required": pk["required_slots"], "provided": pk["provided_slots"],
                    "deficit": pk["deficit"]},
        "compliance": {"score_pct": co["score"], "passed": co["passed"], "failed": co["failed"],
                       "failing_rules": [r["label"] for r in co["results"] if r["status"] == "fail"]},
        "utilities": an.get("utilities"),
    }
    return await _run_ai("report", context, store_at="ai.report",
                         project_id=project_id, user=user, activity="ai.report")


@api.post("/projects/{project_id}/ai/cost")
async def ai_cost(project_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user, write=True)
    an = engine.analyse(proj)
    bill = an["boq"]
    context = {
        "project": {"name": proj.get("name"), "location": proj.get("location")},
        "scale": {"builtup_area_sqm": an["areas"]["builtup_area_sqm"],
                  "carpet_area_sqm": an["areas"]["carpet_area_sqm"],
                  "total_units": an["areas"]["total_units"]},
        "cost_inr": an["cost"],
        "quantities": an["quantities"],
        "boq": {k: v for k, v in bill.items() if k != "currency"},
        "configured_rates": {"materials": proj.get("rates"), "labour": proj.get("labour_rates"),
                             "equipment": proj.get("equipment_rates")},
        "quantity_ratios": proj.get("quantity_ratios"),
    }
    return await _run_ai("cost", context, store_at="ai.cost",
                         project_id=project_id, user=user, activity="ai.cost")


@api.post("/projects/{project_id}/ai/engineering")
async def ai_engineering(project_id: str, user: dict = Depends(get_current_user)):
    proj = await load_project(project_id, user, write=True)
    eng = englib.analyse_engineering(proj, engine.analyse(proj))
    context = {
        "project": {"name": proj.get("name"), "location": proj.get("location")},
        "city_reference": eng.get("city_reference"),
        "summary": eng.get("summary"),
        "modules": {k: {"title": m.get("title"), "outputs": m.get("outputs"),
                        "derived": m.get("derived"),
                        "recommendation": m.get("recommendation"),
                        "code_refs": m.get("code_refs") or m.get("codes")}
                    for k, m in (eng.get("modules") or {}).items()},
        "per_tower": eng.get("per_tower"),
        "missing_inputs": eng.get("missing_inputs"),
        "warnings": eng.get("warnings"),
    }
    return await _run_ai("engineering", context, store_at="ai.engineering",
                         project_id=project_id, user=user, activity="ai.engineering")


@api.get("/projects/{project_id}/ai/compare")
async def ai_compare(project_id: str, a: str = "", b: str = "",
                     user: dict = Depends(get_current_user)):
    """Narrative for a two-scheme comparison. Not stored -- it belongs to the chosen pair,
    not to the project, so caching it on the document would go stale silently."""
    if not a or not b:
        raise HTTPException(status_code=400, detail="Pick two schemes to compare")
    comparison = await compare_versions(project_id, a=a, b=b, user=user)
    schemes = comparison["schemes"]
    keys = comparison["keys"]
    context = {
        "currency": comparison["currency"],
        "scheme_a": {"label": schemes[0]["label"], "saved_at": schemes[0]["at"],
                     "metrics": schemes[0]["metrics"]},
        "scheme_b": {"label": schemes[1]["label"], "saved_at": schemes[1]["at"],
                     "metrics": schemes[1]["metrics"]},
        "metrics_that_differ": [k for k in keys
                                if schemes[0]["metrics"].get(k) != schemes[1]["metrics"].get(k)],
    }
    return await _run_ai("compare", context, project_id=project_id)


# ---------------------------------------------------------------- development finance
class FinanceIn(BaseModel):
    """Partial config; anything omitted falls back to FinanceConfig defaults."""
    config: Dict[str, Any] = Field(default_factory=dict)
    save: bool = True           # keep the inputs on the project so the tab reopens as left


@api.get("/finance/defaults")
async def finance_defaults(user: dict = Depends(get_current_user)):
    return financelib.FinanceConfig().to_dict()


@api.post("/projects/{project_id}/finance")
async def project_finance(project_id: str, body: FinanceIn,
                          user: dict = Depends(get_current_user)):
    """Revenue, profit, return and cash flow for a project the engine can already price."""
    proj = await load_project(project_id, user, write=body.save)
    result = financelib.analyse(proj, engine.analyse(proj), body.config)
    if body.save:
        await db.projects.update_one(
            {"_id": oid(project_id)},
            {"$set": {"finance": result["config"], "updated_at": now_iso()}})
    return result


@api.post("/projects/{project_id}/ai/finance")
async def ai_finance(project_id: str, body: FinanceIn = FinanceIn(),
                     user: dict = Depends(get_current_user)):
    """Body is optional: with none, the assumptions last saved on the project are used."""
    proj = await load_project(project_id, user, write=True)
    an = engine.analyse(proj)
    fin = financelib.analyse(proj, an, body.config or proj.get("finance"))
    context = {
        "project": {"name": proj.get("name"), "location": proj.get("location")},
        "scale": {"builtup_area_sqm": an["areas"]["builtup_area_sqm"],
                  "total_units": an["areas"]["total_units"],
                  "saleable_sqft": fin["saleable"]["total_sqft"]},
        "assumptions": fin["config"],
        "revenue_inr": fin["revenue"],
        "cost_inr": fin["cost"],
        "profit_inr": fin["profit"],
        "break_even": fin["break_even"],
        "timing": fin["timing"],
    }
    return await _run_ai("finance", context, store_at="ai.finance",
                         project_id=project_id, user=user, activity="ai.finance")


# ---------------------------------------------------------------- programme
class ScheduleIn(BaseModel):
    """Partial config; anything omitted falls back to ScheduleConfig defaults."""
    config: Dict[str, Any] = Field(default_factory=dict)
    summary: bool = False       # headline figures only -- see schedule.plan_schedule


@api.get("/schedule/defaults")
async def schedule_defaults(user: dict = Depends(get_current_user)):
    return {"config": schedlib.ScheduleConfig().to_dict(),
            "formwork_is456": schedlib.FORMWORK_IS456,
            "curing_min_days": schedlib.CURING_MIN_DAYS}


@api.post("/projects/{project_id}/schedule")
async def build_schedule(project_id: str, body: ScheduleIn,
                         user: dict = Depends(get_current_user)):
    """Derive the construction programme from the project's own quantities."""
    proj = await load_project(project_id, user)
    return schedlib.plan_schedule(proj, engine.analyse(proj), body.config, summary=body.summary)


class ScheduleLiveIn(ScheduleIn):
    project: Dict[str, Any]


@api.post("/schedule")
async def build_schedule_live(body: ScheduleLiveIn, user: dict = Depends(get_current_user)):
    """Stateless variant for live editing before save."""
    return schedlib.plan_schedule(body.project, engine.analyse(body.project), body.config,
                                  summary=body.summary)


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
    snapshot.pop("public_token", None)
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
    base = engine.analyse(proj)
    eng = englib.analyse_engineering(proj, base)
    pdf = reportlib.build_pdf(report_type, proj, base, eng)
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
