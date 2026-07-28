"""Civil engineering calculation engine. Pure functions over a project document."""
import math

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

    rooms = tower.get("rooms") or []
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

    plot_area = pm["plot_area_sqm"]
    carpet = sum(t["carpet_sqm"] for t in towers)
    builtup = sum(t["builtup_sqm"] for t in towers)
    super_builtup = sum(t["super_builtup_sqm"] for t in towers)
    footprint = sum(t["footprint_sqm"] for t in towers)
    common = sum(t["common_area_sqm"] for t in towers)
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


def quantities(project, areas):
    ratios = {**DEFAULT_RATIOS, **(project.get("quantity_ratios") or {})}
    area = areas["builtup_area_sqm"]
    units = areas["total_units"] or 0
    rows = []
    for key, (label, unit, ratio_key, basis) in MATERIAL_META.items():
        r = float(ratios.get(ratio_key) or 0)
        qty = r * (area if basis == "area" else units)
        rows.append({"key": key, "label": label, "unit": unit, "ratio_key": ratio_key,
                     "ratio": r, "basis": basis, "quantity": round(qty, 2)})
    return {"ratios": ratios, "items": rows, "basis_area_sqm": area, "basis_units": units}


def boq(project, areas, qty):
    rates = {**DEFAULT_RATES, **(project.get("rates") or {})}
    qmap = {i["key"]: i for i in qty["items"]}
    materials = []
    for i in qty["items"]:
        rate = float(rates.get(i["key"]) or 0)
        materials.append({**i, "rate": rate, "amount": round(i["quantity"] * rate, 2)})
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

    grand = round(material_total + labour_total + equipment_total, 2)
    units = areas["total_units"] or 0
    ba = areas["builtup_area_sqm"] or 0
    return {
        "materials": materials, "labour": labour, "equipment": equipment,
        "material_total": material_total, "labour_total": labour_total,
        "equipment_total": equipment_total, "grand_total": grand,
        "cost_per_unit": round(grand / units, 2) if units else 0,
        "cost_per_sqm": round(grand / ba, 2) if ba else 0,
        "currency": (project.get("config") or {}).get("currency", "INR"),
    }


def utilities(project, areas):
    u = project.get("utility_config") or {}
    persons = areas["occupants"]
    lpcd = float(u.get("lpcd") or 135)
    demand = persons * lpcd  # litres/day
    domestic = demand * 0.7
    flushing = demand * 0.3
    ug_days = float(u.get("ug_tank_days") or 1.0)
    oh_hours = float(u.get("oh_tank_hours") or 8.0)
    ug = demand * ug_days
    oh = demand * (oh_hours / 24.0)
    stp = demand * float(u.get("sewage_factor") or 0.8)
    wtp = demand * float(u.get("wtp_factor") or 1.0)
    roof = areas["ground_footprint_sqm"]
    rainfall_mm = float(u.get("annual_rainfall_mm") or 900)
    runoff = float(u.get("runoff_coefficient") or 0.85)
    rwh = roof * (rainfall_mm / 1000.0) * runoff * 1000  # litres/year
    connected_load = areas["total_units"] * float(u.get("kw_per_unit") or 4.0)
    return {
        "persons": persons,
        "lpcd": lpcd,
        "water_demand_lpd": round(demand, 0),
        "domestic_lpd": round(domestic, 0),
        "flushing_lpd": round(flushing, 0),
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
    {"id": "corridor_width", "code": "NBC-COR", "label": "Minimum corridor width", "param": "min_corridor_width", "operator": "min", "threshold": 1.5, "unit": "m", "enabled": True},
    {"id": "lift_ratio", "code": "LFT-01", "label": "Minimum lifts per tower (>= floors/8)", "param": "lift_shortfall", "operator": "max", "threshold": 0, "unit": "nos", "enabled": True},
    {"id": "fire_exits", "code": "FIR-01", "label": "Minimum fire exits per floor", "param": "min_exits_per_floor", "operator": "min", "threshold": 2, "unit": "nos", "enabled": True},
    {"id": "travel_distance", "code": "FIR-02", "label": "Maximum travel distance to exit", "param": "max_travel_distance_m", "operator": "max", "threshold": 30.0, "unit": "m", "enabled": True},
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


def analyse(project):
    areas = area_metrics(project)
    park = parking_metrics(project, areas)
    qty = quantities(project, areas)
    bill = boq(project, areas, qty)
    util = utilities(project, areas)
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
    }
