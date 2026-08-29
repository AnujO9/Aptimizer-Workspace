import hashlib
import uuid
from datetime import datetime, timezone

import iscodes
import layout as layoutlib
from engine import DEFAULT_RATIOS, DEFAULT_RATES, DEFAULT_RULES


def floor_layout_entry(tower, floor, nonce=0):
    """Generate + wrap one floor's room layout for storage in tower['floor_layouts'].
    `validation` maps unit_id -> any schema/adjacency violations left after layout.py's
    own reject-and-regenerate retries (empty dict = every unit fully validated)."""
    rooms, validation = layoutlib.generate_floor_layout(tower, floor, nonce)
    return {
        "rooms": rooms,
        "validation": validation,
        "seed": nonce,
        "unit_mix_hash": layoutlib.unit_mix_hash(tower),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def default_society_amenities():
    """Shared, society-wide facilities — entered ONCE per project, not duplicated per tower.
    Building-specific spaces (entrance lobby, lift lobby) stay on the tower itself."""
    return [
        {"id": str(uuid.uuid4())[:8], "name": "Clubhouse", "type": "clubhouse", "area": 300.0},
        {"id": str(uuid.uuid4())[:8], "name": "Gymnasium", "type": "amenity", "area": 80.0},
        {"id": str(uuid.uuid4())[:8], "name": "Swimming Pool", "type": "amenity", "area": 150.0},
        {"id": str(uuid.uuid4())[:8], "name": "Children's Play Area", "type": "amenity", "area": 100.0},
    ]


def default_tower(name="Tower A"):
    tower = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "floors": 12,
        "floor_height": 3.0,
        "footprint_area": 620.0,
        "common_area": 240.0,
        "corridor_width": 1.8,
        "corridor_length": 32.0,
        "exits_per_floor": 2,
        "max_travel_distance": 24.0,
        "units": [
            {"id": str(uuid.uuid4())[:8], "type": "2bhk", "count": 2, "carpet_area": 78.0, "balcony_area": 8.0},
            {"id": str(uuid.uuid4())[:8], "type": "3bhk", "count": 2, "carpet_area": 110.0, "balcony_area": 12.0},
        ],
        "staircases": [{"id": str(uuid.uuid4())[:8], "count": 2, "width": 1.5, "type": "dog-legged", "location": "core"}],
        "lifts": [{"id": str(uuid.uuid4())[:8], "count": 2, "capacity": 8, "location": "core"}],
        "common_spaces": [
            {"id": str(uuid.uuid4())[:8], "name": "Entrance Lobby", "type": "lobby", "area": 90.0},
        ],
    }
    # Ground-floor layout is generated up front so the plate isn't empty on first load;
    # "rooms" mirrors floor 1 for the engineering calcs (engine.py, engineering.py) and the
    # 3D view (scene.js) that still read a single flat room list per tower.
    ground_floor = floor_layout_entry(tower, 1)
    tower["floor_layouts"] = {"1": ground_floor}
    tower["rooms"] = ground_floor["rooms"]
    return tower


def _plot_jitter(seed_text, scale=0.0035):
    """Deterministic pseudo-offset (~up to ~350 m) derived from the plot reference / project name,
    so two projects in the same city don't land on the literal same default box. Not a real
    geocode — just prevents every new project from being visually identical before the user
    draws their actual boundary."""
    h = hashlib.sha256((seed_text or "").encode("utf-8")).hexdigest()
    fx = (int(h[:8], 16) / 0xFFFFFFFF) - 0.5
    fy = (int(h[8:16], 16) / 0xFFFFFFFF) - 0.5
    return fx * scale, fy * scale


def default_project(name, client, location, plot_reference, owner_id, latitude=None, longitude=None):
    """`latitude`/`longitude`, when supplied, are the plot's actual GPS coordinates and are
    used directly as the placeholder box's centre. There is no public geocoder for Indian
    cadastral survey numbers, so a survey/plot reference alone cannot be resolved to a real
    location -- without coordinates we fall back to a small deterministic offset from the
    selected city's centre, purely as a starting point for the user to redraw over."""
    if latitude is not None and longitude is not None:
        lat, lng = float(latitude), float(longitude)
    else:
        base_lat, base_lng = iscodes.city_center(location)
        jx, jy = _plot_jitter(f"{plot_reference}|{name}")
        lat, lng = base_lat + jy, base_lng + jx
    _city = iscodes.city_reference(next((c for c in iscodes.CITIES if c.lower() in (location or "").lower()), location))
    d_lat, d_lng = 0.00045, 0.00072  # ~100 m × 160 m box around the location centre
    return {
        "name": name,
        "client": client,
        "location": location,
        "plot_reference": plot_reference,
        "status": "draft",
        "owner_id": owner_id,
        "plot": {
            "coordinates": [
                [round(lat + d_lat, 6), round(lng - d_lng, 6)], [round(lat + d_lat, 6), round(lng + d_lng, 6)],
                [round(lat - d_lat, 6), round(lng + d_lng, 6)], [round(lat - d_lat, 6), round(lng - d_lng, 6)],
            ],
            "length": 80.0,
            "width": 50.0,
            "orientation_deg": 0,
            "road_edges": [{"edge_index": 0, "width": 12.0}],
            "center": [round(lat, 6), round(lng, 6)],
            "boundary_points": [],
            "is_placeholder": True,
        },
        "towers": [default_tower()],
        "society_amenities": default_society_amenities(),
        "parking": {
            "basement_levels": 2,
            "basement_area_per_level": 1000.0,
            "ground_area": 400.0,
            "ratio_per_unit": 1.5,
            "area_per_slot": 30.0,
            "visitor_pct": 10.0,
            "ev_pct": 20.0,
            "accessible_pct": 2.0,
            "visitor_provided": 8,
            "ev_provided": 16,
            "accessible_provided": 2,
            "ramp": {"slope_pct": 10.0, "width": 3.6, "turning_radius": 6.0},
        },
        "config": {
            "wall_thickness_factor": 0.10,
            "common_area_loading": 0.25,
            "fsi_factor": 1.0,
            "currency": "INR",
        },
        "quantity_ratios": dict(DEFAULT_RATIOS),
        "rates": dict(DEFAULT_RATES),
        "labour_rates": {},
        "equipment_rates": {},
        "utility_config": {
            "lpcd": 135,
            "ug_tank_days": 1.0,
            "oh_tank_hours": 8.0,
            "sewage_factor": 0.8,
            "wtp_factor": 1.0,
            "annual_rainfall_mm": 900,
            "runoff_coefficient": 0.85,
            "kw_per_unit": 4.0,
        },
        "compliance_rules": [dict(r) for r in DEFAULT_RULES],
        "engineering": {"city": _city["city"], "state": _city["state"]} if _city["source"] != "default" else {},
    }
