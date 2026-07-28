"""RBAC verification for V2 GIS endpoints + V1 regression spot checks."""
import os
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"


def _login(email, pwd):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _register_if_missing(email, name, role, pwd):
    requests.post(f"{API}/auth/register", json={
        "name": name, "email": email, "password": pwd, "role": role
    }, timeout=30)


def test_rbac_viewer_cannot_run_gis_but_can_read():
    _register_if_missing("viewer@aptimizer.com", "Viewer", "viewer", "Viewer@123")
    admin = _login("admin@aptimizer.com", "Admin@123")
    ah = {"Authorization": f"Bearer {admin}"}

    # create a project + share to viewer
    p = requests.post(f"{API}/projects", json={"name": "TEST_RBAC_V2", "client": "QA",
                                               "location": "Bengaluru"}, headers=ah, timeout=30).json()
    pid = p["id"]
    try:
        requests.post(f"{API}/projects/{pid}/shares",
                      json={"email": "viewer@aptimizer.com", "role": "viewer"},
                      headers=ah, timeout=30)
        viewer = _login("viewer@aptimizer.com", "Viewer@123")
        vh = {"Authorization": f"Bearer {viewer}"}

        # GET /gis allowed
        r_get = requests.get(f"{API}/projects/{pid}/gis", headers=vh, timeout=30)
        assert r_get.status_code == 200, r_get.text

        # POST /gis/analyse -> 403 (viewer role blocked)
        r_post = requests.post(f"{API}/projects/{pid}/gis/analyse", json={"radius_m": 300},
                               headers=vh, timeout=30)
        assert r_post.status_code == 403, f"expected 403, got {r_post.status_code}: {r_post.text}"

        # POST /gis/ai-summary -> 403 (viewer)
        r_ai = requests.post(f"{API}/projects/{pid}/gis/ai-summary", headers=vh, timeout=30)
        assert r_ai.status_code == 403, f"expected 403, got {r_ai.status_code}: {r_ai.text}"
    finally:
        requests.delete(f"{API}/projects/{pid}", headers=ah, timeout=30)


def test_v1_regression_analysis_and_reports():
    """V1 spot check: /analysis still returns expected values and PDF+xlsx still download."""
    admin = _login("admin@aptimizer.com", "Admin@123")
    ah = {"Authorization": f"Bearer {admin}"}

    projects = requests.get(f"{API}/projects", headers=ah, timeout=30).json()
    assert projects, "no projects available"
    pid = projects[0]["id"]

    an = requests.get(f"{API}/projects/{pid}/analysis", headers=ah, timeout=30)
    assert an.status_code == 200, an.text
    body = an.json()
    assert "areas" in body and "compliance" in body and "cost" in body

    # BOQ xlsx download
    x = requests.get(f"{API}/projects/{pid}/boq.xlsx", headers=ah, timeout=60)
    assert x.status_code == 200
    assert len(x.content) > 500
    assert x.headers.get("content-type", "").startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml"
    )

    # Executive PDF download
    pdf = requests.get(f"{API}/projects/{pid}/reports/executive", headers=ah, timeout=60)
    assert pdf.status_code == 200
    assert len(pdf.content) > 500
    assert pdf.content[:4] == b"%PDF"
