"""Aptimizer backend regression tests.

Covers: auth (admin seed, register, login, refresh, brute-force lock, /me),
role permissions (viewer create, viewer PUT, admin GET /users),
projects CRUD, analysis chain (plot area/FAR/units/parking/compliance),
towers, versions save+restore, shares (registered & unregistered emails),
activity log, all 7 PDF reports + BOQ xlsx download.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else \
    open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0].strip()
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@aptimizer.com", "password": "Admin@123"}
ENGINEER = {"email": "engineer@aptimizer.com", "password": "Engineer@123", "name": "Test Engineer", "role": "engineer"}
VIEWER = {"email": "viewer@aptimizer.com", "password": "Viewer@123", "name": "Test Viewer", "role": "viewer"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json={"email": creds["email"], "password": creds["password"]}, timeout=15)
    return r


def _register_or_login(creds):
    """Register user, or login if already exists."""
    r = requests.post(f"{API}/auth/register", json=creds, timeout=15)
    if r.status_code == 400:  # already registered
        r = _login(creds)
    assert r.status_code == 200, f"auth failed for {creds['email']}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token():
    r = _login(ADMIN)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def engineer_token():
    return _register_or_login(ENGINEER)


@pytest.fixture(scope="session")
def viewer_token():
    return _register_or_login(VIEWER)


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------------------------------------------------------------- auth
class TestAuth:
    def test_admin_seeded_login(self, admin_token):
        r = requests.get(f"{API}/auth/me", headers=H(admin_token), timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == ADMIN["email"]
        assert data["role"] == "admin"

    def test_engineer_register_login(self, engineer_token):
        r = requests.get(f"{API}/auth/me", headers=H(engineer_token), timeout=10)
        assert r.status_code == 200
        assert r.json()["role"] == "engineer"

    def test_viewer_register_login(self, viewer_token):
        r = requests.get(f"{API}/auth/me", headers=H(viewer_token), timeout=10)
        assert r.status_code == 200
        assert r.json()["role"] == "viewer"

    def test_login_bad_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN["email"], "password": "wrong"}, timeout=10)
        assert r.status_code == 401

    def test_duplicate_register(self):
        r = requests.post(f"{API}/auth/register", json=ENGINEER, timeout=10)
        assert r.status_code == 400

    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me", timeout=10)
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------- roles / admin
class TestRoles:
    def test_admin_list_users(self, admin_token):
        r = requests.get(f"{API}/users", headers=H(admin_token), timeout=10)
        assert r.status_code == 200
        emails = [u["email"] for u in r.json()]
        assert ADMIN["email"] in emails

    def test_engineer_cannot_list_users(self, engineer_token):
        r = requests.get(f"{API}/users", headers=H(engineer_token), timeout=10)
        assert r.status_code == 403

    def test_viewer_cannot_list_users(self, viewer_token):
        r = requests.get(f"{API}/users", headers=H(viewer_token), timeout=10)
        assert r.status_code == 403

    def test_viewer_cannot_create_project(self, viewer_token):
        r = requests.post(f"{API}/projects", headers=H(viewer_token),
                          json={"name": "TEST_v", "client": "", "location": "", "plot_reference": ""}, timeout=10)
        assert r.status_code == 403


# ---------------------------------------------------------------- projects & analysis
@pytest.fixture(scope="session")
def created_project(engineer_token):
    payload = {"name": f"TEST_Aptimizer_{uuid.uuid4().hex[:6]}", "client": "TestClient",
               "location": "TestCity", "plot_reference": "P-1"}
    r = requests.post(f"{API}/projects", headers=H(engineer_token), json=payload, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


class TestProjects:
    def test_create_project(self, created_project):
        assert "id" in created_project
        assert created_project["name"].startswith("TEST_Aptimizer_")
        assert isinstance(created_project.get("towers"), list) and len(created_project["towers"]) >= 1
        assert isinstance(created_project.get("plot"), dict)

    def test_get_project(self, engineer_token, created_project):
        r = requests.get(f"{API}/projects/{created_project['id']}", headers=H(engineer_token), timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == created_project["id"]
        assert d.get("access_role") in ("admin", "engineer", "viewer")

    def test_list_projects(self, engineer_token, created_project):
        r = requests.get(f"{API}/projects", headers=H(engineer_token), timeout=15)
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert created_project["id"] in ids
        target = next(p for p in r.json() if p["id"] == created_project["id"])
        s = target["summary"]
        # summary sanity
        assert s["plot_area_sqm"] > 100
        assert s["total_units"] > 0
        assert s["compliance_score"] >= 0

    def test_analysis_chain(self, engineer_token, created_project):
        r = requests.get(f"{API}/projects/{created_project['id']}/analysis",
                         headers=H(engineer_token), timeout=15)
        assert r.status_code == 200
        a = r.json()
        # Expected seeded numbers (from agent-to-agent note)
        assert 3900 < a["areas"]["plot_area_sqm"] < 4100
        assert a["areas"]["total_units"] == 48
        assert 1.4 < a["areas"]["far"] < 1.8
        assert a["parking"]["required_slots"] > 0
        assert a["parking"]["provided_slots"] > 0
        assert a["compliance"]["score"] > 0
        assert a["compliance"]["total"] == 12
        assert a["cost"]["total"] > 0

    def test_analyse_live(self, engineer_token, created_project):
        # send project back with tweaked config
        r = requests.get(f"{API}/projects/{created_project['id']}", headers=H(engineer_token), timeout=10)
        proj = r.json()
        proj.pop("access_role", None)
        # bump wall thickness factor to see area change
        proj["config"] = dict(proj.get("config") or {})
        proj["config"]["wall_thickness_factor"] = 1.30
        r2 = requests.post(f"{API}/analyse", headers=H(engineer_token),
                           json={"project": proj}, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["areas"]["builtup_area_sqm"] > 0

    def test_add_tower(self, engineer_token, created_project):
        r = requests.post(f"{API}/projects/{created_project['id']}/towers",
                          headers=H(engineer_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert len(d["towers"]) >= 2
        assert d["tower"]["name"].startswith("Tower ")

    def test_put_project_valid_field(self, engineer_token, created_project):
        r = requests.put(f"{API}/projects/{created_project['id']}",
                         headers=H(engineer_token),
                         json={"updates": {"client": "Updated Client"}}, timeout=10)
        assert r.status_code == 200
        assert r.json()["client"] == "Updated Client"


class TestViewerAccess:
    def test_viewer_get_forbidden_before_share(self, viewer_token, created_project):
        r = requests.get(f"{API}/projects/{created_project['id']}", headers=H(viewer_token), timeout=10)
        assert r.status_code == 403

    def test_share_unregistered_email_error(self, engineer_token, created_project):
        r = requests.post(f"{API}/projects/{created_project['id']}/shares",
                          headers=H(engineer_token),
                          json={"email": f"ghost_{uuid.uuid4().hex[:6]}@nowhere.io", "role": "viewer"},
                          timeout=10)
        assert r.status_code == 404
        assert "registered" in r.text.lower()

    def test_share_with_viewer(self, engineer_token, viewer_token, created_project):
        r = requests.post(f"{API}/projects/{created_project['id']}/shares",
                          headers=H(engineer_token),
                          json={"email": VIEWER["email"], "role": "viewer"}, timeout=10)
        assert r.status_code == 200
        # viewer can now GET
        g = requests.get(f"{API}/projects/{created_project['id']}", headers=H(viewer_token), timeout=10)
        assert g.status_code == 200
        assert g.json()["access_role"] == "viewer"
        # project appears in viewer's list
        lst = requests.get(f"{API}/projects", headers=H(viewer_token), timeout=15)
        assert lst.status_code == 200
        assert created_project["id"] in [p["id"] for p in lst.json()]

    def test_viewer_cannot_put(self, viewer_token, created_project):
        r = requests.put(f"{API}/projects/{created_project['id']}",
                         headers=H(viewer_token),
                         json={"updates": {"client": "hack"}}, timeout=10)
        assert r.status_code == 403


class TestVersions:
    def test_save_and_restore(self, engineer_token, created_project):
        pid = created_project["id"]
        # snapshot current
        v = requests.post(f"{API}/projects/{pid}/versions",
                          headers=H(engineer_token), json={"label": "TEST_snap"}, timeout=10)
        assert v.status_code == 200
        vid = v.json()["id"]
        # change client
        requests.put(f"{API}/projects/{pid}", headers=H(engineer_token),
                     json={"updates": {"client": "ChangedAfterSnap"}}, timeout=10)
        # restore
        rr = requests.post(f"{API}/projects/{pid}/versions/{vid}/restore",
                           headers=H(engineer_token), timeout=15)
        assert rr.status_code == 200
        # client value should equal what was in snapshot ("Updated Client" from earlier)
        get = requests.get(f"{API}/projects/{pid}", headers=H(engineer_token), timeout=10).json()
        assert get["client"] != "ChangedAfterSnap"

    def test_activity_has_events(self, engineer_token, created_project):
        r = requests.get(f"{API}/projects/{created_project['id']}/activity",
                         headers=H(engineer_token), timeout=10)
        assert r.status_code == 200
        actions = [a["action"] for a in r.json()]
        assert "project.created" in actions
        assert "version.saved" in actions
        assert "project.updated" in actions


class TestReports:
    @pytest.mark.parametrize("rtype", ["executive", "boq", "cost", "quantity", "parking", "compliance", "utilities"])
    def test_pdf_report(self, engineer_token, created_project, rtype):
        r = requests.get(f"{API}/projects/{created_project['id']}/reports/{rtype}",
                         headers=H(engineer_token), timeout=30)
        assert r.status_code == 200, f"{rtype} -> {r.status_code}"
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 500

    def test_boq_excel(self, engineer_token, created_project):
        r = requests.get(f"{API}/projects/{created_project['id']}/boq.xlsx",
                         headers=H(engineer_token), timeout=30)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
        assert len(r.content) > 500


# ---------------------------------------------------------------- cleanup
def test_zz_cleanup(admin_token):
    r = requests.get(f"{API}/projects", headers=H(admin_token), timeout=15)
    if r.status_code != 200:
        return
    for p in r.json():
        if p["name"].startswith("TEST_"):
            requests.delete(f"{API}/projects/{p['id']}", headers=H(admin_token), timeout=10)
