"""GIS & site-intelligence endpoint tests (V2). Run against the live preview URL:
    pytest /app/backend/tests/gis_test.py -v
"""
import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://aptimizer-build.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
ADMIN = {"email": "admin@aptimizer.com", "password": "Admin@123"}


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def project(headers):
    r = requests.post(f"{API}/projects", json={"name": "TEST_GIS_V2", "client": "QA", "location": "Bengaluru",
                                               "plot_reference": "GIS-1"}, headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    requests.delete(f"{API}/projects/{pid}", headers=headers, timeout=30)


@pytest.fixture(scope="module")
def gis(project, headers):
    r = requests.post(f"{API}/projects/{project}/gis/analyse", json={"radius_m": 400},
                      headers=headers, timeout=180)
    assert r.status_code == 200, r.text
    return r.json()["gis"]


def test_gis_empty_before_analysis(headers):
    r = requests.post(f"{API}/projects", json={"name": "TEST_GIS_EMPTY"}, headers=headers, timeout=30)
    pid = r.json()["id"]
    try:
        g = requests.get(f"{API}/projects/{pid}/gis", headers=headers, timeout=30).json()
        assert g["gis"] is None and g["has_polygon"] is True and g["stale"] is False
        ai = requests.post(f"{API}/projects/{pid}/gis/ai-summary", headers=headers, timeout=60)
        assert ai.status_code == 400
    finally:
        requests.delete(f"{API}/projects/{pid}", headers=headers, timeout=30)


def test_gis_requires_polygon(headers):
    r = requests.post(f"{API}/projects", json={"name": "TEST_GIS_NOPOLY"}, headers=headers, timeout=30)
    pid = r.json()["id"]
    try:
        requests.put(f"{API}/projects/{pid}", json={"updates": {"plot": {"coordinates": [], "orientation_deg": 0}}},
                     headers=headers, timeout=30)
        bad = requests.post(f"{API}/projects/{pid}/gis/analyse", json={"radius_m": 300}, headers=headers, timeout=60)
        assert bad.status_code == 400
        assert "polygon" in bad.json()["detail"].lower()
    finally:
        requests.delete(f"{API}/projects/{pid}", headers=headers, timeout=30)


def test_features_detected(gis):
    for key in ("buildings", "roads", "green", "water", "transit"):
        assert key in gis["features"]
    assert gis["feature_counts"]["roads"] > 0, "expected roads near the default Bengaluru plot"
    road = gis["features"]["roads"][0]
    assert {"id", "kind", "geometry", "distance_m"} <= set(road)
    assert road["road_width_m"] > 0


def test_terrain_and_slope(gis):
    t = gis["terrain"]
    assert t["available"] is True
    assert t["min_m"] <= t["mean_m"] <= t["max_m"]
    assert len(t["profile"]) == 11
    assert t["avg_slope_pct"] >= 0
    assert t["slope_class"] in ("flat", "gentle", "moderate", "steep")


def test_flood_rule_based(gis):
    f = gis["flood"]
    assert f["level"] in ("low", "moderate", "high")
    assert 0 <= f["score"] <= 100
    assert isinstance(f["reasons"], list) and f["reasons"]


def test_wind_and_sun(gis):
    w = gis["wind"]
    assert w["region"] and w["prevailing"] and len(w["rose"]) == 8
    s = gis["sun"]
    assert len(s["paths"]) == 3
    for p in s["paths"]:
        assert p["points"], f"no sun points for {p['key']}"
        assert 0 < p["peak_elevation"] <= 90
        assert p["daylight_hours"] > 6
    assert len(s["facades"]) == 4
    assert s["orientation_deg"] == 0


def test_accessibility_and_scores(gis):
    a = gis["accessibility"]
    assert 0 <= a["score"] <= 100
    assert a["nearest_road_m"] is not None
    s = gis["suitability"]
    assert 0 <= s["score"] <= 100
    assert s["grade"] in ("excellent", "good", "fair", "poor")
    assert len(s["breakdown"]) == 4
    assert sum(b["weight_pct"] for b in s["breakdown"]) == 100
    b = gis["buildability"]
    assert isinstance(b["buildable"], bool)
    assert b["flags"]


def test_persisted_and_staleness(project, headers, gis):
    stored = requests.get(f"{API}/projects/{project}/gis", headers=headers, timeout=30).json()
    assert stored["gis"]["polygon_signature"] == gis["polygon_signature"]
    assert stored["stale"] is False

    proj = requests.get(f"{API}/projects/{project}", headers=headers, timeout=30).json()
    plot = proj["plot"]
    plot["coordinates"] = plot["coordinates"] + [[plot["coordinates"][0][0] + 0.0004,
                                                  plot["coordinates"][0][1] + 0.0004]]
    requests.put(f"{API}/projects/{project}", json={"updates": {"plot": plot}}, headers=headers, timeout=30)
    after = requests.get(f"{API}/projects/{project}/gis", headers=headers, timeout=30).json()
    assert after["stale"] is True, "GIS must be flagged stale after the plot polygon changes"


def test_activity_logged(project, headers, gis):
    acts = requests.get(f"{API}/projects/{project}/activity", headers=headers, timeout=30).json()
    assert any(a["action"] == "gis.analysed" for a in acts)


def test_ai_summary(project, headers, gis):
    r = requests.post(f"{API}/projects/{project}/gis/ai-summary", headers=headers, timeout=180)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["model"] == "claude-sonnet-4-6"
    assert len(data["text"]) > 200
    stored = requests.get(f"{API}/projects/{project}/gis", headers=headers, timeout=30).json()
    assert stored["gis"]["ai_summary"]["text"] == data["text"]


def test_viewer_cannot_run_gis(project, headers):
    requests.post(f"{API}/auth/register", json={"name": "Viewer", "email": "viewer@aptimizer.com",
                                                "password": "Viewer@123", "role": "viewer"}, timeout=30)
    v = requests.post(f"{API}/auth/login", json={"email": "viewer@aptimizer.com", "password": "Viewer@123"},
                      timeout=30).json()
    vh = {"Authorization": f"Bearer {v['access_token']}"}
    requests.post(f"{API}/projects/{project}/shares", json={"email": "viewer@aptimizer.com", "role": "viewer"},
                  headers=headers, timeout=30)
    r = requests.post(f"{API}/projects/{project}/gis/analyse", json={"radius_m": 300}, headers=vh, timeout=60)
    assert r.status_code == 403
    assert requests.get(f"{API}/projects/{project}/gis", headers=vh, timeout=30).status_code == 200
