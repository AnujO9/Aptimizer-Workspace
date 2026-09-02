"""Civil engineering calculation engine. Pure functions over a project document."""
import math

import iscodes
import layout as layoutlib
import parking as parkinglib
import takeoff as takeofflib

OCCUPANCY_PER_UNIT = {"studio": 2, "1bhk": 3, "2bhk": 4, "3bhk": 5, "4bhk": 6, "penthouse": 6, "custom": 4}


def polygon_area_sqm(coords):
    """Shoelace on an equirectangular projection. coords = [[lat, lng], ...]"""
    if not coords or len(coords) < 3:
        return 0.0
    lat0 = sum(c[0] for c in coords) / len(coords)
    k = math.cos(math.radians(lat0))
    pts = [(c[1] * 111320.0 * k, c[0] * 110540.0) for c in coords]
    total = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def plot_metrics(plot):
    coords = plot.get("coordinates") or []
    area = polygon_area_sqm(coords)
    if area <= 0:
        area = float(plot.get("length") or 0) * float(plot.get("width") or 0)
    return {
        "plot_area_sqm": round(area, 2),
        "plot_area_acres": round(area / 4046.86, 4),
        "plot_area_hectare": round(area / 10000.0, 4),
        "orientation_deg": float(plot.get("orientation_deg") or 0),
        "vertices": len(coords),
        "road_edges": plot.get("road_edges") or [],
    }


def tower_metrics(tower, cfg):
    floors = int(tower.get("floors") or 0)
    fh = float(tower.get("floor_height") or 3.0)
    units = tower.get("units") or []
    units_per_floor = sum(int(u.get("count") or 0) for u in units)
    carpet_per_floor = sum(float(u.get("carpet_area") or 0) * int(u.get("count") or 0) for u in units)
    balcony_per_floor = sum(float(u.get("balcony_area") or 0) * int(u.get("count") or 0) for u in units)
    wall_factor = float(cfg.get("wall_thickness_factor") or 0.10)
    loading = float(cfg.get("common_area_loading") or 0.25)

    corridor_area = float(tower.get("corridor_width") or 0) * float(tower.get("corridor_length") or 0)
    stair_area = sum(float(s.get("width") or 0) * float(s.get("width") or 0) * 2.6 * int(s.get("count") or 0)
                     for s in (tower.get("staircases") or []))
    lift_area = sum(int(l.get("count") or 0) * 4.5 for l in (tower.get("lifts") or []))
    service_core_per_floor = round(corridor_area + stair_area + lift_area, 2)

    carpet = carpet_per_floor * floors
    builtup_per_floor = (carpet_per_floor + balcony_per_floor) * (1 + wall_factor) + service_core_per_floor
    builtup = builtup_per_floor * floors
    common_area = float(tower.get("common_area") or 0)
    super_builtup = builtup * (1 + loading)

    occupants = sum(int(u.get("count") or 0) * OCCUPANCY_PER_UNIT.get(str(u.get("type", "custom")).lower(), 4)
                    for u in units) * floors

    rooms = layoutlib.reference_rooms(tower)
    room_area = sum(float(r.get("w") or 0) * float(r.get("h") or 0) for r in rooms)

    return {
        "id": tower.get("id"),
        "name": tower.get("name"),
        "floors": floors,
        "floor_height": fh,
        "height_m": round(floors * fh, 2),
        "units_per_floor": units_per_floor,
        "total_units": units_per_floor * floors,
        "footprint_sqm": float(tower.get("footprint_area") or 0),
        "carpet_sqm": round(carpet, 2),
        "balcony_sqm": round(balcony_per_floor * floors, 2),
        "builtup_per_floor_sqm": round(builtup_per_floor, 2),
        "builtup_sqm": round(builtup, 2),
        "super_builtup_sqm": round(super_builtup, 2),
        "service_core_per_floor_sqm": service_core_per_floor,
        "common_area_sqm": common_area,
        "occupants": occupants,
        "room_area_sqm": round(room_area, 2),
        "stair_min_width": min([float(s.get("width") or 0) for s in (tower.get("staircases") or [])] or [0]),
        "stair_count": sum(int(s.get("count") or 0) for s in (tower.get("staircases") or [])),
        "lift_count": sum(int(l.get("count") or 0) for l in (tower.get("lifts") or [])),
        "corridor_width": float(tower.get("corridor_width") or 0),
        "exits_per_floor": int(tower.get("exits_per_floor") or 0),
        "max_travel_distance_m": float(tower.get("max_travel_distance") or 0),
    }


def area_metrics(project):
    cfg = project.get("config") or {}
    pm = plot_metrics(project.get("plot") or {})
    towers = [tower_metrics(t, cfg) for t in (project.get("towers") or [])]

    society_amenities = project.get("society_amenities") or []
    society_amenities_sqm = round(sum(float(a.get("area") or 0) for a in society_amenities), 2)

    plot_area = pm["plot_area_sqm"]
    carpet = sum(t["carpet_sqm"] for t in towers)
    builtup = sum(t["builtup_sqm"] for t in towers)
    super_builtup = sum(t["super_builtup_sqm"] for t in towers) + society_amenities_sqm
    footprint = sum(t["footprint_sqm"] for t in towers)
    common = sum(t["common_area_sqm"] for t in towers) + society_amenities_sqm
    units = sum(t["total_units"] for t in towers)
    occupants = sum(t["occupants"] for t in towers)

    ground_coverage_pct = (footprint / plot_area * 100) if plot_area else 0
    far = (builtup / plot_area) if plot_area else 0
    fsi = far * float(cfg.get("fsi_factor") or 1.0)
    open_space = max(plot_area - footprint, 0)

    return {
        "plot": pm,
        "towers": towers,
        "plot_area_sqm": plot_area,
        "plot_area_acres": pm["plot_area_acres"],
        "carpet_area_sqm": round(carpet, 2),
        "builtup_area_sqm": round(builtup, 2),
        "super_builtup_area_sqm": round(super_builtup, 2),
        "common_area_sqm": round(common, 2),
        "society_amenities_sqm": society_amenities_sqm,
        "ground_footprint_sqm": round(footprint, 2),
        "ground_coverage_pct": round(ground_coverage_pct, 2),
        "far": round(far, 3),
        "fsi": round(fsi, 3),
        "open_space_sqm": round(open_space, 2),
        "open_space_pct": round((open_space / plot_area * 100) if plot_area else 0, 2),
        "total_units": units,
        "occupants": occupants,
        "density_units_per_acre": round((units / pm["plot_area_acres"]) if pm["plot_area_acres"] else 0, 2),
        "density_persons_per_hectare": round((occupants / pm["plot_area_hectare"]) if pm["plot_area_hectare"] else 0, 2),
        "total_floors": max([t["floors"] for t in towers] or [0]),
        "max_height_m": max([t["height_m"] for t in towers] or [0]),
    }


def parking_metrics(project, areas):
    """Delegates to the per-building parking engine.

    Kept as a thin wrapper so every existing caller -- compliance, the IS/NBC parking and
    accessibility modules, scheme comparison and the reports -- keeps its import and every
    key it reads. `_legacy_parking_metrics` below is the flat site-wide calculation this
    replaced, retained only for reference.
    """
    return parkinglib.plan(project, areas)


def _legacy_parking_metrics(project, areas):
    p = project.get("parking") or {}
    units = areas["total_units"]
    area_per_slot = float(p.get("area_per_slot") or 30)
    basement_levels = int(p.get("basement_levels") or 0)
    basement_area = float(p.get("basement_area_per_level") or 0)
    ground_area = float(p.get("ground_area") or 0)

    basement_slots = int((basement_levels * basement_area) / area_per_slot) if area_per_slot else 0
    ground_slots = int(ground_area / area_per_slot) if area_per_slot else 0
    provided = basement_slots + ground_slots
    ratio = float(p.get("ratio_per_unit") or 1.5)
    required = math.ceil(units * ratio)
    visitor_required = math.ceil(required * float(p.get("visitor_pct") or 10) / 100)
    ev_required = math.ceil(required * float(p.get("ev_pct") or 20) / 100)
    accessible_required = math.ceil(required * float(p.get("accessible_pct") or 2) / 100)

    ramp = p.get("ramp") or {}
    slope = float(ramp.get("slope_pct") or 0)
    ramp_width = float(ramp.get("width") or 0)
    turning_radius = float(ramp.get("turning_radius") or 0)
    ramp_checks = [
        {"label": "Ramp slope <= 12.5%", "pass": slope <= 12.5, "value": f"{slope}%"},
        {"label": "Ramp width >= 3.6 m (two-way 6.0 m)", "pass": ramp_width >= 3.6, "value": f"{ramp_width} m"},
        {"label": "Turning radius >= 6.0 m", "pass": turning_radius >= 6.0, "value": f"{turning_radius} m"},
    ]

    total_area = basement_levels * basement_area + ground_area
    return {
        "units": units,
        "ratio_per_unit": ratio,
        "required_slots": required,
        "provided_slots": provided,
        "basement_slots": basement_slots,
        "ground_slots": ground_slots,
        "deficit": max(required - provided, 0),
        "surplus": max(provided - required, 0),
        "visitor_required": visitor_required,
        "ev_required": ev_required,
        "accessible_required": accessible_required,
        "visitor_provided": int(p.get("visitor_provided") or 0),
        "ev_provided": int(p.get("ev_provided") or 0),
        "accessible_provided": int(p.get("accessible_provided") or 0),
        "total_parking_area_sqm": round(total_area, 2),
        "area_per_slot_actual": round(total_area / provided, 2) if provided else 0,
        "efficiency_pct": round((provided * area_per_slot / total_area * 100) if total_area else 0, 2),
        "ramp_checks": ramp_checks,
        "ramp_pass": all(c["pass"] for c in ramp_checks),
    }


DEFAULT_RATIOS = {
    "concrete_m3_per_sqm": 0.40,
    "cement_bags_per_sqm": 4.30,
    "steel_kg_per_sqm": 45.0,
    "bricks_nos_per_sqm": 55.0,
    "sand_m3_per_sqm": 0.26,
    "aggregate_m3_per_sqm": 0.36,
    "tiles_sqm_per_sqm": 1.30,
    "paint_sqm_per_sqm": 3.20,
    "doors_per_unit": 5.0,
    "windows_per_unit": 6.0,
    "plumbing_fixtures_per_unit": 9.0,
    "electrical_points_per_unit": 35.0,
    "waterproofing_sqm_per_sqm": 0.25,
    "finishing_sqm_per_sqm": 1.10,
}

MATERIAL_META = {
    "concrete": ("Concrete (M25)", "m3", "concrete_m3_per_sqm", "area"),
    "cement": ("Cement (OPC 53)", "bags", "cement_bags_per_sqm", "area"),
    "steel": ("Reinforcement Steel", "kg", "steel_kg_per_sqm", "area"),
    "bricks": ("Bricks / Blocks", "nos", "bricks_nos_per_sqm", "area"),
    "sand": ("Sand", "m3", "sand_m3_per_sqm", "area"),
    "aggregate": ("Coarse Aggregate", "m3", "aggregate_m3_per_sqm", "area"),
    "tiles": ("Floor & Wall Tiles", "m2", "tiles_sqm_per_sqm", "area"),
    "paint": ("Paint (2 coats)", "m2", "paint_sqm_per_sqm", "area"),
    "waterproofing": ("Waterproofing", "m2", "waterproofing_sqm_per_sqm", "area"),
    "finishing": ("Finishing Materials", "m2", "finishing_sqm_per_sqm", "area"),
    "doors": ("Doors", "nos", "doors_per_unit", "unit"),
    "windows": ("Windows", "nos", "windows_per_unit", "unit"),
    "plumbing_fixtures": ("Plumbing Fixtures", "nos", "plumbing_fixtures_per_unit", "unit"),
    "electrical_points": ("Electrical Points", "nos", "electrical_points_per_unit", "unit"),
}

DEFAULT_RATES = {
    "concrete": 6500, "cement": 420, "steel": 72, "bricks": 9, "sand": 2200,
    "aggregate": 1800, "tiles": 950, "paint": 180, "waterproofing": 550,
    "finishing": 1200, "doors": 9500, "windows": 7500,
    "plumbing_fixtures": 4500, "electrical_points": 850,
}

LABOUR_TRADES = [
    ("mason", "Mason", "bricks", 500.0, 1100),
    ("carpenter", "Carpenter / Shuttering", "concrete", 2.5, 1200),
    ("bar_bender", "Bar Bender", "steel", 350.0, 1150),
    ("concretor", "Concretor / Helper", "concrete", 3.0, 900),
    ("tiler", "Tiler", "tiles", 12.0, 1100),
    ("painter", "Painter", "paint", 35.0, 950),
    ("plumber", "Plumber", "plumbing_fixtures", 2.0, 1200),
    ("electrician", "Electrician", "electrical_points", 8.0, 1200),
]

EQUIPMENT = [
    ("mixer", "Concrete Mixer / Batching", "concrete", 12.0, 3500),
    ("vibrator", "Needle Vibrator", "concrete", 25.0, 900),
    ("hoist", "Material Hoist", "area", 900.0, 4500),
    ("crane", "Tower Crane / Lifting", "area", 2500.0, 15000),
    ("scaffold", "Scaffolding Set", "area", 600.0, 2500),
]


# Materials whose quantity follows the STRUCTURE, and so is taken off the designed
# sections rather than a per-m2 rule. Everything else -- tiles, paint, doors, fixtures --
# genuinely does scale with floor area or unit count, and keeps its ratio.
DERIVED_KEYS = {
    "concrete": ("concrete_m3", 1.0),
    "steel": ("steel_kg", 1.0),
    "cement": ("cement_bags", 1.0),
    "sand": ("sand_m3", 1.0),
    "aggregate": ("aggregate_m3", 1.0),
}


def quantities(project, areas, use_takeoff=True):
    """Bill quantities. Structural items come from the take-off; the rest from ratios.

    `use_takeoff=False` restores the old all-ratios behaviour, which is what the payload
    reports alongside the derived figures so an estimator can see both.
    """
    ratios = {**DEFAULT_RATIOS, **(project.get("quantity_ratios") or {})}
    area = areas["builtup_area_sqm"]
    units = areas["total_units"] or 0

    derived = None
    if use_takeoff and (areas.get("towers") or []):
        try:
            derived = takeofflib.structural_takeoff(project, areas)
        except Exception:          # a take-off failure must not take the whole bill down
            derived = None

    rows = []
    for key, (label, unit, ratio_key, basis) in MATERIAL_META.items():
        r = float(ratios.get(ratio_key) or 0)
        qty = r * (area if basis == "area" else units)
        source = "ratio"
        if derived and key in DERIVED_KEYS:
            tk, factor = DERIVED_KEYS[key]
            qty = float(derived["totals"].get(tk) or 0) * factor
            source = "take-off"
        rows.append({"key": key, "label": label, "unit": unit, "ratio_key": ratio_key,
                     "ratio": r, "basis": basis, "quantity": round(qty, 2), "source": source})

    return {"ratios": ratios, "items": rows, "basis_area_sqm": area, "basis_units": units,
            "takeoff": derived, "derived": bool(derived)}


# Site wastage, as a share of the delivered quantity. Cut-and-bend loss on steel, spillage
# and over-ordering on concrete, breakage on tiles: real material that is bought and paid
# for but does not end up in the building.
DEFAULT_WASTAGE_PCT = {
    "concrete": 2.0, "cement": 3.0, "steel": 3.0, "bricks": 5.0, "sand": 6.0,
    "aggregate": 6.0, "tiles": 8.0, "paint": 5.0, "waterproofing": 5.0, "finishing": 5.0,
    "doors": 0.0, "windows": 0.0, "plumbing_fixtures": 2.0, "electrical_points": 2.0,
}

# Everything between the works cost and the figure a developer actually commits. Omitting
# these is why the old grand total sat well under any real tender: a bill of materials plus
# labour is not a project cost.
DEFAULT_COST_ADDERS = {
    "preliminaries_pct": 3.0,     # site setup, temporary works, supervision
    "overhead_profit_pct": 12.0,  # contractor's overhead and margin
    "contingency_pct": 5.0,       # design development and unforeseen
    "escalation_pct": 4.0,        # price movement over the build period
    "gst_pct": 18.0,              # works contract; 1% / 5% regimes apply to some housing
}


def boq(project, areas, qty):
    rates = {**DEFAULT_RATES, **(project.get("rates") or {})}
    wastage = {**DEFAULT_WASTAGE_PCT, **(project.get("wastage_pct") or {})}
    qmap = {i["key"]: i for i in qty["items"]}
    materials = []
    for i in qty["items"]:
        rate = float(rates.get(i["key"]) or 0)
        w = float(wastage.get(i["key"]) or 0)
        ordered = i["quantity"] * (1 + w / 100.0)
        materials.append({**i, "rate": rate, "wastage_pct": w,
                          "quantity_ordered": round(ordered, 2),
                          "amount": round(ordered * rate, 2)})
    material_total = round(sum(m["amount"] for m in materials), 2)

    labour = []
    for key, label, src, output_per_day, wage in LABOUR_TRADES:
        base_qty = qmap.get(src, {}).get("quantity", 0)
        wage = float((project.get("labour_rates") or {}).get(key) or wage)
        mandays = round(base_qty / output_per_day, 1) if output_per_day else 0
        labour.append({"key": key, "label": label, "unit": "man-days", "quantity": mandays,
                       "rate": wage, "amount": round(mandays * wage, 2)})
    labour_total = round(sum(l["amount"] for l in labour), 2)

    equipment = []
    for key, label, src, divisor, rate in EQUIPMENT:
        base = areas["builtup_area_sqm"] if src == "area" else qmap.get(src, {}).get("quantity", 0)
        days = round(base / divisor, 1) if divisor else 0
        rate = float((project.get("equipment_rates") or {}).get(key) or rate)
        equipment.append({"key": key, "label": label, "unit": "days", "quantity": days,
                          "rate": rate, "amount": round(days * rate, 2)})
    equipment_total = round(sum(e["amount"] for e in equipment), 2)

    works = round(material_total + labour_total + equipment_total, 2)

    # Applied in sequence, each on the running total, which is how a bill is actually
    # built up: profit is earned on preliminaries, and tax is charged on the lot.
    add = {**DEFAULT_COST_ADDERS, **(project.get("cost_adders") or {})}
    running = works
    adders = []
    for key, label in (("preliminaries_pct", "Preliminaries and site establishment"),
                       ("overhead_profit_pct", "Contractor overhead and profit"),
                       ("contingency_pct", "Contingency"),
                       ("escalation_pct", "Price escalation"),
                       ("gst_pct", "GST on works contract")):
        pct = float(add.get(key) or 0)
        amount = round(running * pct / 100.0, 2)
        adders.append({"key": key, "label": label, "pct": pct, "amount": amount,
                       "on": round(running, 2)})
        running = round(running + amount, 2)
    grand = running

    units = areas["total_units"] or 0
    ba = areas["builtup_area_sqm"] or 0
    return {
        "materials": materials, "labour": labour, "equipment": equipment,
        "material_total": material_total, "labour_total": labour_total,
        "equipment_total": equipment_total,
        "works_total": works, "adders": adders, "adders_total": round(grand - works, 2),
        "grand_total": grand,
        "cost_per_unit": round(grand / units, 2) if units else 0,
        "cost_per_sqm": round(grand / ba, 2) if ba else 0,
        "currency": (project.get("config") or {}).get("currency", "INR"),
    }


def water_demand(project, areas):
    """IS 1172:1993 water demand — the single source of truth for the whole app.

    Both this module's Utilities panel and the IS/NBC Water module (engineering.m5_water)
    call this, so a project can no longer show two different daily demands and two
    different sump sizes. Occupancy comes from the per-unit-type figures in `areas`, which
    is finer-grained than a flat persons-per-unit assumption.

    A user-supplied `utility_config.lpcd` overrides the code total; the domestic /
    flushing / external split is then scaled to it rather than being re-invented.
    """
    u = project.get("utility_config") or {}
    persons = areas["occupants"]

    code_lpcd = iscodes.WATER_LPCD
    code_total = code_lpcd["domestic"] + code_lpcd["flushing"] + code_lpcd["external"]
    lpcd = float(u.get("lpcd") or code_total)
    scale = lpcd / code_total if code_total else 1.0

    domestic = persons * code_lpcd["domestic"] * scale
    flushing = persons * code_lpcd["flushing"] * scale
    external = persons * code_lpcd["external"] * scale
    demand = domestic + flushing + external
    return {
        "persons": persons, "lpcd": lpcd,
        "domestic_lpd": domestic, "flushing_lpd": flushing, "external_lpd": external,
        "total_lpd": demand,
        "sewage_lpd": demand * float(u.get("sewage_factor") or iscodes.SEWAGE_FACTOR),
    }


def utilities(project, areas, city=None):
    u = project.get("utility_config") or {}
    w = water_demand(project, areas)
    persons, lpcd, demand = w["persons"], w["lpcd"], w["total_lpd"]
    domestic, flushing = w["domestic_lpd"], w["flushing_lpd"]
    ug_days = float(u.get("ug_tank_days") or 1.0)
    oh_hours = float(u.get("oh_tank_hours") or 8.0)
    ug = demand * ug_days
    oh = demand * (oh_hours / 24.0)
    stp = w["sewage_lpd"]
    wtp = demand * float(u.get("wtp_factor") or 1.0)
    roof = areas["ground_footprint_sqm"]
    # Default to the project city's own rainfall rather than a flat 900 mm, so this and
    # the Storm/RWH module (which always used the city table) agree.
    city_rainfall = (city or {}).get("annual_rainfall_mm")
    rainfall_mm = float(u.get("annual_rainfall_mm") or city_rainfall or 900)
    runoff = float(u.get("runoff_coefficient") or iscodes.RUNOFF_C["rcc_roof"])
    rwh = roof * (rainfall_mm / 1000.0) * runoff * 1000  # litres/year
    connected_load = areas["total_units"] * float(u.get("kw_per_unit") or 4.0)
    return {
        "persons": persons,
        "lpcd": lpcd,
        "water_demand_lpd": round(demand, 0),
        "domestic_lpd": round(domestic, 0),
        "flushing_lpd": round(flushing, 0),
        "external_lpd": round(w["external_lpd"], 0),
        "annual_rainfall_mm": rainfall_mm,
        "ug_tank_litres": round(ug, 0),
        "ug_tank_cum": round(ug / 1000.0, 2),
        "oh_tank_litres": round(oh, 0),
        "oh_tank_cum": round(oh / 1000.0, 2),
        "stp_capacity_kld": round(stp / 1000.0, 2),
        "wtp_capacity_kld": round(wtp / 1000.0, 2),
        "rwh_annual_litres": round(rwh, 0),
        "rwh_storage_cum": round(rwh / 1000.0 * 0.05, 2),
        "electrical_room_sqm": round(max(20.0, connected_load * 0.35), 2),
        "pump_room_sqm": round(max(12.0, areas["total_units"] * 0.12), 2),
        "connected_load_kw": round(connected_load, 1),
    }


DEFAULT_RULES = [
    {"id": "far_max", "code": "FAR-01", "label": "Maximum permissible FAR", "param": "far", "operator": "max", "threshold": 3.0, "unit": "ratio", "enabled": True},
    {"id": "fsi_max", "code": "FSI-01", "label": "Maximum permissible FSI", "param": "fsi", "operator": "max", "threshold": 3.0, "unit": "ratio", "enabled": True},
    {"id": "ground_coverage", "code": "GC-01", "label": "Maximum ground coverage", "param": "ground_coverage_pct", "operator": "max", "threshold": 40.0, "unit": "%", "enabled": True},
    {"id": "open_space", "code": "OS-01", "label": "Minimum open space", "param": "open_space_pct", "operator": "min", "threshold": 30.0, "unit": "%", "enabled": True},
    {"id": "stair_width", "code": "NBC-STR", "label": "Minimum staircase width", "param": "min_stair_width", "operator": "min", "threshold": 1.5, "unit": "m", "enabled": True},
    {"id": "corridor_width", "code": "NBC-COR", "label": "Minimum corridor width (means of egress)", "param": "min_corridor_width", "operator": "min", "threshold": iscodes.FIRE["corridor_min_m"], "unit": "m", "enabled": True},
    {"id": "lift_ratio", "code": "LFT-01", "label": "Minimum lifts per tower (>= floors/8)", "param": "lift_shortfall", "operator": "max", "threshold": 0, "unit": "nos", "enabled": True},
    {"id": "fire_exits", "code": "FIR-01", "label": "Minimum fire exits per floor", "param": "min_exits_per_floor", "operator": "min", "threshold": 2, "unit": "nos", "enabled": True},
    {"id": "travel_distance", "code": "FIR-02", "label": "Maximum travel distance to exit", "param": "max_travel_distance_m", "operator": "max", "threshold": iscodes.FIRE["max_travel_m"], "unit": "m", "enabled": True},
    {"id": "ramp_slope", "code": "ACC-01", "label": "Maximum ramp slope", "param": "ramp_slope_pct", "operator": "max", "threshold": 12.5, "unit": "%", "enabled": True},
    {"id": "accessible_parking", "code": "ACC-02", "label": "Minimum accessible parking", "param": "accessible_parking_pct", "operator": "min", "threshold": 2.0, "unit": "%", "enabled": True},
    {"id": "parking_provision", "code": "PRK-01", "label": "Parking provided vs required", "param": "parking_deficit", "operator": "max", "threshold": 0, "unit": "nos", "enabled": True},
]


def compliance(project, areas, park):
    rules = project.get("compliance_rules") or DEFAULT_RULES
    towers = areas["towers"]
    lift_shortfall = 0
    for t in towers:
        needed = max(1, math.ceil(t["floors"] / 8.0))
        lift_shortfall += max(needed - t["lift_count"], 0)
    ramp = (project.get("parking") or {}).get("ramp") or {}
    provided_acc = park["accessible_provided"] or park["accessible_required"]
    params = {
        "far": areas["far"],
        "fsi": areas["fsi"],
        "ground_coverage_pct": areas["ground_coverage_pct"],
        "open_space_pct": areas["open_space_pct"],
        "min_stair_width": min([t["stair_min_width"] for t in towers] or [0]),
        "min_corridor_width": min([t["corridor_width"] for t in towers] or [0]),
        "lift_shortfall": lift_shortfall,
        "min_exits_per_floor": min([t["exits_per_floor"] for t in towers] or [0]),
        "max_travel_distance_m": max([t["max_travel_distance_m"] for t in towers] or [0]),
        "ramp_slope_pct": float(ramp.get("slope_pct") or 0),
        "accessible_parking_pct": round((provided_acc / park["required_slots"] * 100) if park["required_slots"] else 0, 2),
        "parking_deficit": park["deficit"],
    }
    results = []
    for r in rules:
        if not r.get("enabled", True):
            continue
        actual = float(params.get(r["param"], 0))
        threshold = float(r.get("threshold") or 0)
        ok = actual <= threshold if r.get("operator") == "max" else actual >= threshold
        results.append({
            "id": r.get("id"), "code": r.get("code"), "label": r.get("label"),
            "param": r.get("param"), "operator": r.get("operator"),
            "threshold": threshold, "unit": r.get("unit"), "actual": round(actual, 3),
            "status": "pass" if ok else "fail",
            "message": ("Compliant" if ok else
                        f"{r.get('label')}: actual {round(actual, 3)}{r.get('unit', '')} violates "
                        f"{'maximum' if r.get('operator') == 'max' else 'minimum'} {threshold}{r.get('unit', '')}"),
        })
    passed = sum(1 for r in results if r["status"] == "pass")
    return {
        "params": params, "results": results, "total": len(results), "passed": passed,
        "failed": len(results) - passed,
        "score": round(passed / len(results) * 100, 1) if results else 0,
        "overall": "pass" if passed == len(results) else "fail",
    }


def far_derivation(project, areas):
    """Every step from plot area to the reported FAR, as the engine actually computes it.

    Written against the real calculation rather than a plausible one, because the point of
    the panel is that a reader can reproduce the number. Three things it has to be honest
    about, all of which are surprising:

      1. THERE ARE NO DEDUCTIONS. Built-up is summed straight from the towers. Parking and
         society amenities are excluded by never being added, not by a deduction step, so
         there is no itemised deduction list to show -- claiming one would be fiction.
      2. FSI IS FAR TIMES A FACTOR, defaulting to 1.0. The two are the same number unless
         somebody sets `config.fsi_factor`. They are not two different area bases.
      3. Built-up per floor is (carpet + balcony) x (1 + wall thickness factor) + service
         core. The loading that produces super built-up is NOT in it, which is why super
         built-up is larger and is not what FAR is measured on.
    """
    cfg = project.get("config") or {}
    plot_area = float(areas["plot_area_sqm"] or 0)
    builtup = float(areas["builtup_area_sqm"] or 0)
    wall_factor = float(cfg.get("wall_thickness_factor") or 0.10)
    loading = float(cfg.get("common_area_loading") or 0.25)
    fsi_factor = float(cfg.get("fsi_factor") or 1.0)

    towers = [{
        "name": t.get("name"), "floors": t.get("floors"),
        "carpet_sqm": t.get("carpet_sqm"), "balcony_sqm": t.get("balcony_sqm"),
        "service_core_per_floor_sqm": t.get("service_core_per_floor_sqm"),
        "builtup_per_floor_sqm": t.get("builtup_per_floor_sqm"),
        "builtup_sqm": t.get("builtup_sqm"),
        "share_pct": round(float(t.get("builtup_sqm") or 0) / builtup * 100, 1) if builtup else 0.0,
    } for t in (areas.get("towers") or [])]

    # What the engine leaves OUT of the FAR numerator. Listed as "not counted" rather than
    # "deducted" because that is what the code does -- these areas are never added.
    excluded = [
        {"item": "Society amenities", "area_sqm": areas.get("society_amenities_sqm", 0),
         "reason": "Counted in super built-up, never in built-up, so it never enters FAR."},
        {"item": "Common-area loading",
         "area_sqm": round(sum(float(t.get("super_builtup_sqm") or 0)
                               - float(t.get("builtup_sqm") or 0)
                               for t in (areas.get("towers") or [])), 2),
         "reason": (f"The {loading:.0%} loading that turns built-up into super built-up is a "
                    "sales convention, not floor area, so FAR is measured before it.")},
    ]

    limits = {}
    for rule in (project.get("compliance_rules") or DEFAULT_RULES):
        if rule.get("id") in ("far_max", "fsi_max") and rule.get("enabled", True):
            limits[rule["id"]] = rule

    far = round(builtup / plot_area, 3) if plot_area else 0.0
    fsi = round(far * fsi_factor, 3)
    cap = float(limits.get("far_max", {}).get("threshold") or 0)

    return {
        "formula": "FAR = total built-up area / plot area",
        "inputs": [
            {"label": "Plot area", "value": round(plot_area, 2), "unit": "m2",
             "source": "Plot polygon, or the recorded length x width"},
            {"label": "Total built-up area", "value": round(builtup, 2), "unit": "m2",
             "source": "Sum of every tower's built-up area"},
        ],
        "builtup_rule": ("Built-up per floor = (carpet + balcony) x (1 + "
                         f"{wall_factor:.0%} wall thickness) + service core; "
                         "multiplied by the floor count."),
        "towers": towers,
        "excluded": excluded,
        "substitution": (f"FAR = {builtup:,.2f} / {plot_area:,.2f} = {far}"
                         if plot_area else "FAR cannot be computed without a plot area"),
        "far": far,
        "fsi": fsi,
        "fsi_factor": fsi_factor,
        # The honest statement about the two figures, decided by the config not by prose.
        "far_vs_fsi": (
            "FAR and FSI are the same number in this project. FSI is FAR multiplied by "
            f"config.fsi_factor, which is {fsi_factor:g}. They are not two different area "
            "bases, and they will only differ if that factor is changed."
            if abs(fsi_factor - 1.0) < 1e-9 else
            f"FSI is FAR x {fsi_factor:g} (config.fsi_factor). The two differ only by that "
            "multiplier -- the area basis underneath them is identical."),
        "identical": abs(fsi_factor - 1.0) < 1e-9,
        "permissible": {
            "far_cap": cap,
            "governing_control": limits.get("far_max", {}).get("label", "not set"),
            "headroom_ratio": round(cap - far, 3) if cap else None,
            "headroom_sqm": round((cap - far) * plot_area, 1) if cap and plot_area else None,
            "used_pct": round(far / cap * 100, 1) if cap else None,
        },
        "no_deductions_note": (
            "This engine applies no FSI deductions. Areas commonly deducted elsewhere -- "
            "parking, stilts, service floors, refuge areas -- are excluded here by never "
            "being added to built-up in the first place. If your authority requires an "
            "explicit deduction schedule, it is not modelled."),
    }


def area_derivation(project, areas):
    """Detailed step-by-step arithmetic derivation of Carpet, Built-up and Super Built-up areas.

    Explains service core empirical multipliers, wall thickness allowance, common area loading,
    society amenities add-on, and reconciles the implied multiplier for easy manual verification.
    """
    cfg = project.get("config") or {}
    wall_factor = float(cfg.get("wall_thickness_factor") or 0.10)
    loading = float(cfg.get("common_area_loading") or 0.25)
    society_amenities = project.get("society_amenities") or []
    society_amenities_sqm = float(areas.get("society_amenities_sqm") or 0)

    plot_sqm = float(areas.get("plot_area_sqm") or 0)
    carpet_sqm = float(areas.get("carpet_area_sqm") or 0)
    builtup_sqm = float(areas.get("builtup_area_sqm") or 0)
    super_builtup_sqm = float(areas.get("super_builtup_area_sqm") or 0)

    towers_raw = project.get("towers") or []
    towers_derived = areas.get("towers") or []

    tower_breakdowns = []
    total_corridor_sqm = 0.0
    total_stairs_sqm = 0.0
    total_lifts_sqm = 0.0
    total_walls_sqm = 0.0

    for t_raw in towers_raw:
        t_id = t_raw.get("id")
        t_der = next((td for td in towers_derived if td.get("id") == t_id), {})
        floors = int(t_der.get("floors") or 0)

        # Unit breakdown
        units = t_raw.get("units") or []
        carpet_floor = sum(float(u.get("carpet_area") or 0) * int(u.get("count") or 0) for u in units)
        balcony_floor = sum(float(u.get("balcony_area") or 0) * int(u.get("count") or 0) for u in units)

        # Service core components
        corridor_w = float(t_raw.get("corridor_width") or 0)
        corridor_l = float(t_raw.get("corridor_length") or 0)
        corridor_floor = corridor_w * corridor_l

        stairs = t_raw.get("staircases") or []
        stair_floor = sum(float(s.get("width") or 0) * float(s.get("width") or 0) * 2.6 * int(s.get("count") or 0) for s in stairs)

        lifts = t_raw.get("lifts") or []
        lift_floor = sum(int(l.get("count") or 0) * 4.5 for l in lifts)

        core_floor = corridor_floor + stair_floor + lift_floor
        walls_floor = (carpet_floor + balcony_floor) * wall_factor
        builtup_floor = (carpet_floor + balcony_floor) + walls_floor + core_floor

        t_builtup = builtup_floor * floors
        t_super = t_builtup * (1 + loading)

        total_corridor_sqm += corridor_floor * floors
        total_stairs_sqm += stair_floor * floors
        total_lifts_sqm += lift_floor * floors
        total_walls_sqm += walls_floor * floors

        tower_breakdowns.append({
            "id": t_id,
            "name": t_der.get("name") or t_raw.get("name"),
            "floors": floors,
            "units_per_floor": t_der.get("units_per_floor"),
            "total_units": t_der.get("total_units"),
            "carpet_per_floor_sqm": round(carpet_floor, 2),
            "balcony_per_floor_sqm": round(balcony_floor, 2),
            "service_core": {
                "corridor_sqm": round(corridor_floor, 2),
                "stair_sqm": round(stair_floor, 2),
                "lift_sqm": round(lift_floor, 2),
                "total_floor_sqm": round(core_floor, 2),
                "total_tower_sqm": round(core_floor * floors, 2),
                "stair_formula": "stair_count × (stair_width)² × 2.6",
                "lift_formula": "lift_count × 4.5 m² per shaft",
                "corridor_formula": f"{corridor_w} m width × {corridor_l} m length",
            },
            "wall_allowance_floor_sqm": round(walls_floor, 2),
            "builtup_per_floor_sqm": round(builtup_floor, 2),
            "builtup_sqm": round(t_builtup, 2),
            "super_builtup_sqm": round(t_super, 2),
            "loading_factor": loading,
            "loading_added_sqm": round(t_super - t_builtup, 2),
        })

    towers_builtup_total = sum(t["builtup_sqm"] for t in tower_breakdowns)
    towers_super_total = sum(t["super_builtup_sqm"] for t in tower_breakdowns)
    implied_multiplier = round(super_builtup_sqm / builtup_sqm, 4) if builtup_sqm else 1.0

    return {
        "summary": {
            "plot_area_sqm": plot_sqm,
            "carpet_area_sqm": carpet_sqm,
            "builtup_area_sqm": builtup_sqm,
            "super_builtup_area_sqm": super_builtup_sqm,
            "wall_allowance_pct": round(wall_factor * 100, 1),
            "common_area_loading_pct": round(loading * 100, 1),
            "society_amenities_sqm": society_amenities_sqm,
            "implied_multiplier": implied_multiplier,
            "implied_loading_pct": round((implied_multiplier - 1.0) * 100, 2),
        },
        "step_by_step_formulas": [
            {
                "step": 1,
                "title": "Carpet Area",
                "formula": "Sum of internal usable room area across all apartment units",
                "explanation": "Net usable floor area of an apartment excluding walls, shafts and balconies (RERA definition).",
                "result": f"{carpet_sqm:,.2f} m²",
            },
            {
                "step": 2,
                "title": "Wall Thickness Allowance",
                "formula": f"(Carpet Area + Balcony Area) × {wall_factor:.0%}",
                "explanation": f"Accounts for internal partition and external perimeter brick/block walls ({wall_factor:.0%} of floor plate).",
                "result": f"+{total_walls_sqm:,.2f} m²",
            },
            {
                "step": 3,
                "title": "Service Core per Floor",
                "formula": "Corridor (W × L) + Staircases (N × W² × 2.6) + Lifts (N × 4.5 m²)",
                "explanation": "Vertical and horizontal circulation on every typical floor. Staircase multiplier 2.6 covers waist slab, landings and mid-landings; 4.5 m² covers lift shaft + wall enclosure.",
                "result": f"+{sum(t['service_core']['total_tower_sqm'] for t in tower_breakdowns):,.2f} m²",
            },
            {
                "step": 4,
                "title": "Built-up Area (Plinth Area)",
                "formula": "[(Carpet + Balcony) × 1.10 + Service Core] × Floors",
                "explanation": "Total structural slab area constructed across all floors of all towers.",
                "result": f"= {builtup_sqm:,.2f} m²",
            },
            {
                "step": 5,
                "title": "Common Area Loading (Tower Level)",
                "formula": f"Tower Built-up × (1 + {loading:.0%})",
                "explanation": f"Commercial loading factor of {loading:.0%} applied to built-up area for common corridors, entrance lobbies, and tower services.",
                "result": f"= {towers_super_total:,.2f} m² (across towers)",
            },
            {
                "step": 6,
                "title": "Society Amenities Add-On (Clubhouse, Pool, etc.)",
                "formula": "Sum of stand-alone society amenities",
                "explanation": "Shared community structures (Clubhouse, Gym, Swimming pool, etc.) that belong to all residents are added to the saleable pool.",
                "result": f"+{society_amenities_sqm:,.2f} m²",
            },
            {
                "step": 7,
                "title": "Total Super Built-up Area (Saleable Area)",
                "formula": "Towers Super Built-up + Society Amenities",
                "explanation": f"{towers_super_total:,.2f} m² + {society_amenities_sqm:,.2f} m²",
                "result": f"= {super_builtup_sqm:,.2f} m²",
            },
            {
                "step": 8,
                "title": "Implied / Effective Multiplier Reconciled",
                "formula": f"Total Super Built-up ÷ Total Built-up = {super_builtup_sqm:,.2f} ÷ {builtup_sqm:,.2f}",
                "explanation": f"Notice this is {implied_multiplier:g}× (or {(implied_multiplier - 1.0) * 100:.2f}% total loading) instead of exactly {loading * 100:g}%. The difference ({((implied_multiplier - 1.0) - loading) * 100:.2f}%) is precisely the society amenities ({society_amenities_sqm} m²) distributed over the built-up area!",
                "result": f"{implied_multiplier:g}×",
            },
        ],
        "towers": tower_breakdowns,
        "society_amenities": society_amenities,
    }


def analyse(project):
    areas = area_metrics(project)
    park = parking_metrics(project, areas)
    qty = quantities(project, areas)
    bill = boq(project, areas, qty)
    # The engineering config carries the project city; passing its reference data here
    # keeps the Utilities RWH yield consistent with the Storm/RWH module.
    eng_cfg = project.get("engineering") or {}
    city = iscodes.city_reference(eng_cfg.get("city"), eng_cfg.get("state"))
    util = utilities(project, areas, city)
    comp = compliance(project, areas, park)
    return {
        "areas": areas, "parking": park, "quantities": qty, "boq": bill,
        "cost": {
            "material": bill["material_total"], "labour": bill["labour_total"],
            "equipment": bill["equipment_total"], "total": bill["grand_total"],
            "per_unit": bill["cost_per_unit"], "per_sqm": bill["cost_per_sqm"],
            "currency": bill["currency"],
            "breakdown": [
                {"name": "Material", "value": bill["material_total"]},
                {"name": "Labour", "value": bill["labour_total"]},
                {"name": "Equipment", "value": bill["equipment_total"]},
            ],
        },
        "utilities": util, "compliance": comp,
        "far_derivation": far_derivation(project, areas),
        "area_derivation": area_derivation(project, areas),
    }
