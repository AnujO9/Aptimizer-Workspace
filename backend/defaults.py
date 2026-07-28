import uuid

from engine import DEFAULT_RATIOS, DEFAULT_RATES, DEFAULT_RULES


def default_rooms():
    layout = [
        ("Living / Dining", "living", 0, 0, 6.0, 4.5),
        ("Master Bedroom", "bedroom", 6.2, 0, 4.2, 3.9),
        ("Bedroom 2", "bedroom", 10.6, 0, 3.6, 3.6),
        ("Kitchen", "kitchen", 0, 4.7, 3.2, 3.0),
        ("Bathroom 1", "bathroom", 3.4, 4.7, 2.2, 2.0),
        ("Bathroom 2", "bathroom", 5.8, 4.7, 2.2, 2.0),
        ("Balcony", "balcony", 8.2, 4.7, 4.0, 1.8),
        ("Lobby", "common", 12.4, 4.7, 3.2, 3.0),
    ]
    return [{"id": str(uuid.uuid4())[:8], "name": n, "type": t, "x": x, "y": y, "w": w, "h": h}
            for n, t, x, y, w, h in layout]


def default_tower(name="Tower A"):
    return {
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
        "rooms": default_rooms(),
        "common_spaces": [
            {"id": str(uuid.uuid4())[:8], "name": "Entrance Lobby", "type": "lobby", "area": 90.0},
            {"id": str(uuid.uuid4())[:8], "name": "Clubhouse", "type": "clubhouse", "area": 110.0},
            {"id": str(uuid.uuid4())[:8], "name": "Gym", "type": "amenity", "area": 40.0},
        ],
    }


def default_project(name, client, location, plot_reference, owner_id):
    return {
        "name": name,
        "client": client,
        "location": location,
        "plot_reference": plot_reference,
        "status": "draft",
        "owner_id": owner_id,
        "plot": {
            "coordinates": [
                [12.971600, 77.594600], [12.971600, 77.595337],
                [12.971148, 77.595337], [12.971148, 77.594600],
            ],
            "length": 80.0,
            "width": 50.0,
            "orientation_deg": 0,
            "road_edges": [{"edge_index": 0, "width": 12.0}],
            "center": [12.9708, 77.5956],
        },
        "towers": [default_tower()],
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
    }
