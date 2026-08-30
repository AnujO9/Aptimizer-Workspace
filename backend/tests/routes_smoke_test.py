"""HTTP-level smoke test for the new endpoints.

Everything else tests the Python functions. This tests the layer between them and the
browser: route wiring, Pydantic request models, dependency injection, and the JSON encoder
FastAPI actually uses. A function can be perfect and the endpoint still 422 because a body
model has no default, or 500 because something in the payload will not encode.

Auth is bypassed by overriding the dependency rather than by logging in -- these are
route-shape tests, not access-control tests, and rbac has its own suite.

Skipped entirely when MongoDB is not reachable, so the suite stays green on a machine
without one.

One shared client for the module, entered as a context manager. motor binds its event loop
the first time it is used and keeps it; a TestClient used outside a context manager starts
a fresh loop per request, so the second request finds motor holding a closed one. The
context manager keeps one portal, and therefore one loop, alive across the whole module.
(pytest.ini already pins a module to a single xdist worker via --dist loadscope.)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient

import server
from defaults import default_project


@pytest.fixture(scope="module")
def client_and_project():
    """A real project row, an admin session, and cleanup afterwards."""
    from bson import ObjectId

    admin = {"_id": ObjectId(), "email": "routes-test@local", "role": "admin",
             "name": "Route Test"}
    server.app.dependency_overrides[server.get_current_user] = lambda: admin

    doc = default_project("Route Smoke", "QA", "Hyderabad", "RS-1", str(admin["_id"]))
    doc["owner_id"] = str(admin["_id"])

    # server.db is a motor (async) handle -- calling insert_one on it here returns an
    # un-awaited coroutine, inserts nothing, and every request then 404s on a project id
    # that was never a real ObjectId. Setup uses a sync pymongo client against the same
    # database instead; the app under test still talks to it through motor.
    try:
        from pymongo import MongoClient
        sync = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=3000)
        sync.admin.command("ping")
        sync_db = sync[os.environ["DB_NAME"]]
        pid = str(sync_db.projects.insert_one(doc).inserted_id)
    except Exception as exc:                     # no mongo on this machine
        server.app.dependency_overrides.clear()
        pytest.skip(f"MongoDB not reachable: {exc}")

    with TestClient(server.app) as client:
        yield client, pid

    try:
        sync_db.projects.delete_one({"_id": server.oid(pid)})
        sync.close()
    except Exception:
        pass
    server.app.dependency_overrides.clear()


def _ok(resp, label):
    assert resp.status_code == 200, f"{label}: {resp.status_code} {resp.text[:300]}"
    try:
        return json.loads(resp.text)          # strict: rejects NaN/Infinity
    except ValueError as exc:
        pytest.fail(f"{label}: response is not valid JSON -- {exc}")


def test_finance_defaults(client_and_project):
    client, _ = client_and_project
    data = _ok(client.get("/api/finance/defaults"), "finance defaults")
    assert "sale_rate_per_sqft" in data


def test_finance_route(client_and_project):
    client, pid = client_and_project
    data = _ok(client.post(f"/api/projects/{pid}/finance",
                           json={"config": {"sale_rate_per_sqft": 6500}, "save": False}),
               "finance")
    assert data["ok"] and data["revenue"]["gross"] > 0
    assert "cash_flow" in data and data["profit"]["margin_pct"] is not None


def test_optimise_route(client_and_project):
    client, pid = client_and_project
    data = _ok(client.post(f"/api/projects/{pid}/optimise", json={"target_budget": 0}),
               "optimise")
    for key in ("waste", "quantity", "budget", "materials"):
        assert key in data, key
        assert set(data[key]["current"]) >= {"value", "unit", "label"}


def test_optimise_accepts_an_empty_body(client_and_project):
    """The panel posts {} on first load. A body model without a default 422s here."""
    client, pid = client_and_project
    _ok(client.post(f"/api/projects/{pid}/optimise", json={}), "optimise empty body")


def test_planning_optimise_route(client_and_project):
    client, pid = client_and_project
    data = _ok(client.post(f"/api/projects/{pid}/optimise/planning", json={}), "planning")
    for key in ("floors", "far", "fsi", "open_space", "mix", "parking", "utilities"):
        assert key in data, key
        assert data[key]["changes"], f"{key} proposed no change"


def test_chat_thread_starts_empty_and_clears(client_and_project):
    client, pid = client_and_project
    data = _ok(client.get(f"/api/projects/{pid}/ai/chat"), "chat thread")
    assert data["thread"] == []
    _ok(client.delete(f"/api/projects/{pid}/ai/chat"), "chat clear")


def test_chat_suggestions_are_built_from_this_project(client_and_project):
    """The empty state must never be a blank box."""
    client, pid = client_and_project
    data = _ok(client.get(f"/api/projects/{pid}/ai/chat/suggestions"), "suggestions")
    assert 3 <= len(data["suggestions"]) <= 4
    assert all(isinstance(q, str) and q.strip().endswith(("?", ".")) for q in data["suggestions"])


def test_chat_rejects_an_empty_message_list(client_and_project):
    client, pid = client_and_project
    r = client.post(f"/api/projects/{pid}/ai/chat", json={"messages": []})
    assert r.status_code == 400


def test_chat_rejects_a_thread_ending_on_the_assistant(client_and_project):
    """Nothing to answer -- must be a clean 400, not a call to the provider."""
    client, pid = client_and_project
    r = client.post(f"/api/projects/{pid}/ai/chat",
                    json={"messages": [{"role": "assistant", "content": "hi"}]})
    assert r.status_code == 400


def test_compare_versions_carries_the_new_metrics_and_geometry(client_and_project):
    client, pid = client_and_project
    data = _ok(client.get(f"/api/projects/{pid}/versions/compare",
                          params={"a": "current", "b": "current"}), "compare")
    keys = data["keys"]
    for k in ("Green score (%)", "Embodied carbon (tCO₂e)", "Carbon per m² (kgCO₂e)",
              "Water met by rainwater (%)", "Return on cost (%)", "Annual IRR (%)"):
        assert k in keys, f"missing compare metric: {k}"
    geom = data["schemes"][0]["geometry"]
    assert geom["plot"]["length_m"] > 0 and geom["towers"]
    assert "basis" in geom["plot"] and "placement" in geom


def test_engineering_route_exposes_the_new_modules(client_and_project):
    """Carbon and plantation have to reach the tab, not just the orchestrator."""
    client, pid = client_and_project
    data = _ok(client.get(f"/api/projects/{pid}/engineering"), "engineering")
    mods = data["modules"]
    assert "carbon" in mods and "trees" in mods
    assert mods["carbon"]["derived"]["total_tco2e"] > 0
    assert mods["trees"]["derived"]["required"] > 0
    # And the beam layout has to arrive with the grid module.
    assert mods["grid"]["beam_layout"]["summary"]["beam_count"] > 0
    for key in ("embodied_carbon_tco2e", "carbon_per_sqm_kg", "trees_required"):
        assert key in data["summary"], key
