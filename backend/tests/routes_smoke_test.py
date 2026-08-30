"""HTTP-level smoke test for the new endpoints.

Everything else tests the Python functions. This tests the layer between them and the
browser: route wiring, Pydantic request models, dependency injection, and the JSON encoder
FastAPI actually uses. A function can be perfect and the endpoint still 422 because a body
model has no default, or 500 because something in the payload will not encode.

Auth is bypassed by overriding the dependency rather than by logging in -- these are
route-shape tests, not access-control tests, and rbac has its own suite.

Skipped entirely when MongoDB is not reachable, so the suite stays green on a machine
without one.

Every HTTP test in the suite shares one session-scoped TestClient, defined in
tests/conftest.py. motor binds an event loop the first time it is used and keeps it, so a
second TestClient in the same process leaves it holding a closed loop and every later
request dies with "Event loop is closed" -- which is exactly what happened when a second
HTTP test module was added.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

import server


# Function-scoped, because api_project is: each test gets a clean project and
# they cannot leak state into one another.
@pytest.fixture
def client_and_project(api_project):
    """The shared client and a throwaway project. See tests/conftest.py."""
    return api_project


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


def test_suggestions_change_with_the_module(client_and_project):
    """The gap this replaced: the same four questions on every tab."""
    client, pid = client_and_project
    seen = {}
    for module in ("boq", "cost", "parking", "compliance", "programme"):
        data = _ok(client.get(f"/api/projects/{pid}/ai/chat/suggestions",
                              params={"module": module}), f"suggestions/{module}")
        assert data["module"] == module
        assert 3 <= len(data["suggestions"]) <= 4
        seen[module] = data["suggestions"]
    assert seen["boq"] != seen["cost"] != seen["parking"]
    assert any("largest line" in q for q in seen["boq"])
    assert any("slots" in q for q in seen["parking"])


def test_reports_all_returns_one_merged_pdf(client_and_project):
    import io as _io2
    from pypdf import PdfReader
    client, pid = client_and_project
    r = client.get(f"/api/projects/{pid}/reports/all")
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")
    assert len(PdfReader(_io2.BytesIO(r.content)).pages) > 11


def test_a_merged_away_report_id_still_downloads(client_and_project):
    """An old bookmark should land on the numbers, not a 400."""
    client, pid = client_and_project
    for old_id in ("utilities", "quantity", "accessibility", "parking"):
        r = client.get(f"/api/projects/{pid}/reports/{old_id}")
        assert r.status_code == 200, f"{old_id}: {r.status_code}"
        assert r.content.startswith(b"%PDF")


def test_an_unknown_report_id_is_still_rejected(client_and_project):
    client, pid = client_and_project
    assert client.get(f"/api/projects/{pid}/reports/nonsense").status_code == 400


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
