"""Site layout engine — Stage 2 (road ring, driveways, amenity reservation).

    pytest backend/tests/siteplan_reserve_test.py -v
"""
import math
import os
import sys

import pytest
from shapely.geometry import Point

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from siteplan import (AmenityBlock, LayoutError, SiteLayoutConfig, build_envelope,  # noqa: E402
                      reserve, reserve_from_coordinates, reserve_site, resolve_amenity_size)
from siteplan.frame import LocalFrame, polygons_of  # noqa: E402
from siteplan.reserve import driveway_network, perimeter_ring  # noqa: E402

LAT0, LNG0 = 12.9716, 77.5946
FRAME = LocalFrame(LAT0, LNG0)


def to_latlng(points):
    return [FRAME.to_latlng(x, y) for x, y in points]


def box_pts(w, h, x0=0.0, y0=0.0):
    return [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]


def conf(**over):
    """Config with a small setback so tests focus on stage 2, not stage 1."""
    base = {"setbacks": {"default": 5}}
    base.update(over)
    return SiteLayoutConfig.from_dict(base)


def run(shape, roads=None, **over):
    return reserve_from_coordinates(to_latlng(shape), roads or [], conf(**over))


# ---------------------------------------------------------------- perimeter ring
def test_ring_is_an_annulus_of_the_configured_width():
    # Amenities off: an amenity spanning a full edge of the core would shift its bounds.
    r = run(box_pts(120, 90), amenities={"enabled": False})
    ring_w = r.envelope.config.road.ring_width
    # The core is inset from the envelope by exactly the ring width.
    env_b = r.envelope.envelope.bounds
    core_b = r.residual.bounds
    assert core_b[0] - env_b[0] == pytest.approx(ring_w, abs=0.3)
    assert env_b[2] - core_b[2] == pytest.approx(ring_w, abs=0.3)
    assert not r.ring.is_empty


def test_ring_and_residual_do_not_overlap():
    r = run(box_pts(120, 90))
    assert r.ring.intersection(r.residual).area == pytest.approx(0.0, abs=1e-6)


def test_ring_plus_core_reconstructs_the_envelope():
    r = run(box_pts(120, 90), amenities={"enabled": False})
    rebuilt = r.ring.union(r.residual).union(r.driveways)
    assert rebuilt.area == pytest.approx(r.envelope.envelope.area, rel=1e-3)


def test_ring_disabled_leaves_the_whole_envelope_packable():
    r = run(box_pts(100, 80), road={"enabled": False}, amenities={"enabled": False})
    assert r.ring.is_empty and r.driveways.is_empty
    assert r.residual.area == pytest.approx(r.envelope.envelope.area, rel=1e-6)


def test_envelope_narrower_than_the_ring_warns_and_leaves_nothing_packable():
    env = build_envelope(to_latlng(box_pts(26, 26)), [],
                         SiteLayoutConfig.from_dict({"setbacks": {"default": 5}}))
    r = reserve(env, env.config)
    assert r.residual.is_empty
    assert any("narrower than" in w for w in r.warnings)


# ---------------------------------------------------------------- driveways
def test_deep_core_gets_driveways_so_nothing_is_stranded():
    reach = 30.0
    r = run(box_pts(260, 200), road={"max_distance_to_road": reach},
            amenities={"enabled": False})
    assert not r.driveways.is_empty

    # Residual parts are bounded only by the ring and the driveways, so "every point is
    # within `reach` of a road" is exactly "eroding the part by `reach` empties it".
    # That is the real reachability property, not a spot check on one interior point.
    for part in polygons_of(r.residual):
        assert part.buffer(-reach).is_empty, (
            f"a {part.area:.0f} m2 pocket sits more than {reach} m from any road")


def test_shallow_core_needs_no_driveways():
    r = run(box_pts(90, 70), road={"max_distance_to_road": 60.0},
            amenities={"enabled": False})
    assert r.driveways.is_empty


def test_driveways_stay_inside_the_core_and_off_the_residual():
    r = run(box_pts(240, 180), road={"max_distance_to_road": 25.0},
            amenities={"enabled": False})
    assert r.envelope.envelope.buffer(1e-6).contains(r.driveways)
    assert r.driveways.intersection(r.residual).area == pytest.approx(0.0, abs=1e-6)


def test_driveway_width_is_honoured():
    width = 7.0
    r = run(box_pts(300, 220), road={"max_distance_to_road": 30.0, "driveway_width": width},
            amenities={"enabled": False})
    part = polygons_of(r.driveways)[0]
    # A spine clipped to a rectangular core is itself a rectangle, so w and L are the two
    # roots of x^2 - (P/2)x + A = 0. Take the smaller root as the width.
    half_p, area = part.length / 2.0, part.area
    disc = half_p ** 2 - 4 * area
    assert disc >= 0
    assert (half_p - math.sqrt(disc)) / 2.0 == pytest.approx(width, rel=0.02)


# ---------------------------------------------------------------- amenity sizing
def test_explicit_dimensions_win_over_percentage():
    block = AmenityBlock("club", "Clubhouse", dimensions=[30, 20], plot_area_pct=50)
    w, d, area = resolve_amenity_size(block, plot_area=10000)
    assert (w, d, area) == (30.0, 20.0, 600.0)


def test_explicit_area_wins_over_percentage():
    block = AmenityBlock("club", "Clubhouse", area_sqm=400, plot_area_pct=50, aspect=1.0)
    w, d, area = resolve_amenity_size(block, plot_area=10000)
    assert area == 400.0
    assert w == pytest.approx(20.0) and d == pytest.approx(20.0)


def test_percentage_of_plot_area_sizing():
    block = AmenityBlock("club", "Clubhouse", plot_area_pct=2.0, aspect=1.0)
    w, d, area = resolve_amenity_size(block, plot_area=10000)
    assert area == pytest.approx(200.0)
    assert w == pytest.approx(math.sqrt(200.0))


def test_block_with_no_sizing_is_reported_not_crashed():
    r = run(box_pts(160, 120), amenities={"blocks": [
        {"key": "ghost", "name": "Mystery Block"},
    ]})
    assert r.amenities == []
    assert any("no size" in w for w in r.warnings)


# ---------------------------------------------------------------- amenity placement
def test_amenities_are_placed_inside_the_envelope_and_clear_of_roads():
    r = run(box_pts(200, 150))
    assert len(r.amenities) == 3
    for a in r.amenities:
        assert r.envelope.envelope.buffer(1e-6).contains(a.polygon)
        assert a.polygon.intersection(r.roads).area == pytest.approx(0.0, abs=1e-6)


def test_amenities_do_not_overlap_each_other():
    r = run(box_pts(200, 150))
    for i, a in enumerate(r.amenities):
        for b in r.amenities[i + 1:]:
            assert a.polygon.intersection(b.polygon).area == pytest.approx(0.0, abs=1e-6)


def test_amenities_are_subtracted_from_the_residual():
    r = run(box_pts(200, 150))
    for a in r.amenities:
        assert a.polygon.intersection(r.residual).area == pytest.approx(0.0, abs=1e-6)


def test_amenity_footprints_respect_the_total_cap():
    r = run(box_pts(200, 150), amenities={"total_cap_pct": 3.0, "blocks": [
        {"key": "a", "name": "Huge A", "plot_area_pct": 6.0},
        {"key": "b", "name": "Huge B", "plot_area_pct": 6.0},
    ]})
    total = sum(a.area_sqm for a in r.amenities)
    assert total <= r.envelope.plot.area * 0.03 + 1.0
    assert any("cap" in w for w in r.warnings)


def test_amenity_that_cannot_fit_is_reported_not_dropped_silently():
    r = run(box_pts(70, 60), amenities={"total_cap_pct": 100.0, "blocks": [
        {"key": "mega", "name": "Mega Hall", "dimensions": [200, 90]},
    ]})
    assert r.amenities == []
    assert any("does not fit" in w for w in r.warnings)


def test_amenities_carry_their_own_low_rise_height():
    r = run(box_pts(200, 150))
    by_key = {a.key: a for a in r.amenities}
    assert by_key["clubhouse"].height_m == 7.5 and by_key["clubhouse"].floors == 2
    assert by_key["pool"].height_m == 1.5
    assert all(a.height_m <= 8 for a in r.amenities), "amenities must stay low-rise"


def _min_pairwise_gap(result):
    polys = [a.polygon for a in result.amenities]
    return min(a.distance(b) for i, a in enumerate(polys) for b in polys[i + 1:])


def test_spread_term_disperses_amenities_instead_of_clustering():
    """With the spread weight zeroed the blocks huddle; with it on they separate."""
    clustered = run(box_pts(220, 160), amenities={"spread_weight": 0.0, "compactness_weight": 0.85})
    dispersed = run(box_pts(220, 160))
    assert len(clustered.amenities) == len(dispersed.amenities) == 3
    assert _min_pairwise_gap(dispersed) > _min_pairwise_gap(clustered)


def test_dispersed_amenities_are_a_meaningful_distance_apart():
    r = run(box_pts(220, 160))
    # Auto target separation is 0.55 * sqrt(packable area); require at least half of it.
    target = math.sqrt(r.residual.area) * 0.55
    assert _min_pairwise_gap(r) >= target * 0.5


def test_explicit_target_separation_overrides_the_derived_one():
    r = run(box_pts(300, 220), amenities={"target_separation": 60.0})
    assert _min_pairwise_gap(r) >= 30.0


def test_spread_does_not_push_amenities_off_the_roads():
    """Dispersion must not win by exiling blocks into the middle of the packable land."""
    r = run(box_pts(220, 160))
    for a in r.amenities:
        assert a.polygon.distance(r.roads) <= 2.0, f"{a.name} floats away from circulation"


def test_amenities_disabled_leaves_residual_untouched():
    a = run(box_pts(200, 150), amenities={"enabled": False})
    assert a.amenities == []
    assert a.residual.area > 0


# ---------------------------------------------------------------- concave / containment
@pytest.mark.parametrize("shape", [
    box_pts(200, 150),
    [(0, 0), (200, 0), (200, 120), (100, 120), (100, 220), (0, 220)],       # big L
    [(0, 0), (220, 0), (220, 160), (150, 90), (80, 160), (0, 160)],         # notched
])
def test_everything_reserved_stays_inside_the_envelope(shape):
    r = run(shape)
    guard = r.envelope.envelope.buffer(1e-6)
    assert guard.contains(r.ring)
    assert guard.contains(r.driveways) or r.driveways.is_empty
    assert guard.contains(r.residual) or r.residual.is_empty
    for a in r.amenities:
        assert guard.contains(a.polygon)


def test_reserved_areas_sum_to_the_envelope():
    r = run(box_pts(200, 150))
    total = (r.ring.area + r.driveways.area + r.residual.area
             + sum(a.area_sqm for a in r.amenities))
    # Clearance buffers around amenities are unreserved slack, so the sum is a lower bound.
    assert total <= r.envelope.envelope.area + 1.0
    assert total >= r.envelope.envelope.area * 0.85


# ---------------------------------------------------------------- API surface
def test_reserve_site_payload_is_a_superset_of_stage_one():
    project = {"plot": {"coordinates": to_latlng(box_pts(200, 150)),
                        "road_edges": [{"edge_index": 0, "width": 12}]}}
    out = reserve_site(project, {"setbacks": {"default": 5, "front": 9}})

    assert out["ok"] is True and out["stage"] == "reserve"
    assert out["envelope"]["area_sqm"] > 0          # stage 1 fields still present
    assert out["edges"][0]["class"] == "front"

    assert out["roads"]["ring_area_sqm"] > 0
    assert out["roads"]["ring_polygons"]
    assert len(out["amenities"]) == 3
    assert out["amenities"][0]["polygons"]
    assert out["residual"]["area_sqm"] > 0
    assert 0 < out["residual"]["pct_of_envelope"] < 100

    s = out["reservation_summary"]
    assert s["packable_area_sqm"] + s["road_area_sqm"] + s["amenity_area_sqm"] <= s["envelope_area_sqm"] + 1


def test_reserve_site_returns_error_dict_for_a_bad_polygon():
    out = reserve_site({"plot": {"coordinates": []}})
    assert out["ok"] is False and out["error"]["code"] == "no_polygon"


def test_reserve_site_surfaces_a_collapsed_envelope():
    out = reserve_site({"plot": {"coordinates": to_latlng(box_pts(15, 15))}},
                       {"setbacks": {"default": 9}})
    assert out["ok"] is False and out["error"]["code"] == "envelope_collapsed"
