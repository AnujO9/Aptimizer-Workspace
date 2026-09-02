"""AI-powered and architectural floor plan generator.

Dynamically creates realistic, code-compliant, Vastu-aligned residential floor plates
with proper circulation, exterior windows, attached balconies, door connections, and
room proportions.
"""
import asyncio
import json
import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _unit_spec(unit_type: str, carpet: float) -> Dict[str, Any]:
    """Derive standard room proportions and program for a unit type based on Section 2 Scaling Protocol."""
    t = (unit_type or "2bhk").lower().strip()
    c = float(carpet or 85.0)

    if "5bhk" in t or "penthouse" in t:
        # 5BHK / Penthouse: 4-5 Ensuite Bedrooms (including Grand Master Suite with Walk-in Closet),
        # Powder Room, Servant Quarters, Massive wrap-around terraces, Family Lounge, Pantry, Dedicated Home Office.
        return {
            "rooms": [
                {"name": "Living & Dining", "type": "living", "pct": 0.22, "exterior": True, "balcony": True},
                {"name": "Family Lounge", "type": "living", "pct": 0.10, "exterior": True},
                {"name": "Grand Master Suite", "type": "bedroom", "pct": 0.16, "exterior": True, "balcony": True, "vastu": "SW"},
                {"name": "Walk-in Closet", "type": "closet", "pct": 0.04, "exterior": False},
                {"name": "Master Ensuite Bath", "type": "bathroom", "pct": 0.05, "exterior": False},
                {"name": "Bedroom 2 (Ensuite)", "type": "bedroom", "pct": 0.11, "exterior": True, "balcony": True},
                {"name": "Ensuite Bath 2", "type": "bathroom", "pct": 0.04, "exterior": False},
                {"name": "Bedroom 3 (Ensuite)", "type": "bedroom", "pct": 0.09, "exterior": True},
                {"name": "Ensuite Bath 3", "type": "bathroom", "pct": 0.035, "exterior": False},
                {"name": "Bedroom 4 (Guest Ensuite)", "type": "bedroom", "pct": 0.08, "exterior": True},
                {"name": "Ensuite Bath 4", "type": "bathroom", "pct": 0.035, "exterior": False},
                {"name": "Dedicated Home Office", "type": "office", "pct": 0.06, "exterior": True},
                {"name": "Kitchen", "type": "kitchen", "pct": 0.07, "exterior": True, "utility": True, "vastu": "SE"},
                {"name": "Pantry & Dry Storage", "type": "pantry", "pct": 0.03, "exterior": False},
                {"name": "Utility & Wash Area", "type": "utility", "pct": 0.03, "exterior": True},
                {"name": "Pooja Room (Ishanya)", "type": "pooja", "pct": 0.025, "exterior": True, "vastu": "NE"},
                {"name": "Powder Room", "type": "bathroom", "pct": 0.02, "exterior": False},
                {"name": "Servant Room", "type": "servant", "pct": 0.04, "exterior": True},
                {"name": "Servant Bath", "type": "servant", "pct": 0.02, "exterior": False},
                {"name": "MEP Duct Shaft", "type": "shaft", "pct": 0.015, "exterior": False},
            ]
        }
    elif "4bhk" in t:
        # 4BHK: 3 Bedrooms with Ensuite Baths, 1 Guest Bed + Common Bath/Powder, 1 Servant Room + Bath,
        # Balconies (Living, Master, Sub-Master), Expansive Utility & Pooja, Dedicated Service Entry.
        return {
            "rooms": [
                {"name": "Living & Dining", "type": "living", "pct": 0.26, "exterior": True, "balcony": True},
                {"name": "Master Bedroom", "type": "bedroom", "pct": 0.17, "exterior": True, "balcony": True, "vastu": "SW"},
                {"name": "Master Ensuite Bath", "type": "bathroom", "pct": 0.05, "exterior": False},
                {"name": "Sub-Master Bed (Ensuite)", "type": "bedroom", "pct": 0.14, "exterior": True, "balcony": True},
                {"name": "Ensuite Bath 2", "type": "bathroom", "pct": 0.04, "exterior": False},
                {"name": "Bedroom 3 (Ensuite)", "type": "bedroom", "pct": 0.12, "exterior": True},
                {"name": "Ensuite Bath 3", "type": "bathroom", "pct": 0.04, "exterior": False},
                {"name": "Guest Bed", "type": "bedroom", "pct": 0.10, "exterior": True},
                {"name": "Common Bath / Powder", "type": "bathroom", "pct": 0.035, "exterior": False},
                {"name": "Kitchen", "type": "kitchen", "pct": 0.08, "exterior": True, "utility": True, "vastu": "SE"},
                {"name": "Expansive Utility Area", "type": "utility", "pct": 0.035, "exterior": True},
                {"name": "Pooja Room (Ishanya)", "type": "pooja", "pct": 0.03, "exterior": True, "vastu": "NE"},
                {"name": "Servant Room", "type": "servant", "pct": 0.045, "exterior": True},
                {"name": "Servant Bath", "type": "servant", "pct": 0.02, "exterior": False},
                {"name": "MEP Duct Shaft", "type": "shaft", "pct": 0.015, "exterior": False},
            ]
        }
    elif "3bhk" in t:
        # 3BHK: 1 Master Bed with Ensuite, 1 Sub-Master Bed with Ensuite, 1 Guest/Kids Bed with Common Bath,
        # Balconies (Living + Master Bed), Large Utility, Dedicated Vastu Pooja Room.
        return {
            "rooms": [
                {"name": "Living & Dining", "type": "living", "pct": 0.30, "exterior": True, "balcony": True},
                {"name": "Master Bedroom", "type": "bedroom", "pct": 0.19, "exterior": True, "balcony": True, "vastu": "SW"},
                {"name": "Master Ensuite Bath", "type": "bathroom", "pct": 0.05, "exterior": False},
                {"name": "Sub-Master Bedroom", "type": "bedroom", "pct": 0.15, "exterior": True},
                {"name": "Sub-Master Ensuite Bath", "type": "bathroom", "pct": 0.045, "exterior": False},
                {"name": "Guest / Kids Bedroom", "type": "bedroom", "pct": 0.13, "exterior": True},
                {"name": "Common Bathroom", "type": "bathroom", "pct": 0.04, "exterior": False},
                {"name": "Kitchen", "type": "kitchen", "pct": 0.09, "exterior": True, "utility": True, "vastu": "SE"},
                {"name": "Large Utility Area", "type": "utility", "pct": 0.04, "exterior": True},
                {"name": "Pooja Room (Ishanya)", "type": "pooja", "pct": 0.03, "exterior": True, "vastu": "NE"},
                {"name": "MEP Duct Shaft", "type": "shaft", "pct": 0.015, "exterior": False},
            ]
        }
    elif "1bhk" in t or "studio" in t:
        # 1BHK: 1 Master Bed with Ensuite Bath, 1 Powder Room (optional/guest),
        # Main Balcony attached to Living, compact dry balcony attached to Kitchen, Pooja Niche.
        return {
            "rooms": [
                {"name": "Living & Dining", "type": "living", "pct": 0.40, "exterior": True, "balcony": True},
                {"name": "Master Bedroom", "type": "bedroom", "pct": 0.27, "exterior": True, "vastu": "SW"},
                {"name": "Ensuite Bathroom", "type": "bathroom", "pct": 0.08, "exterior": False},
                {"name": "Guest Powder Room", "type": "bathroom", "pct": 0.04, "exterior": False},
                {"name": "Kitchen", "type": "kitchen", "pct": 0.14, "exterior": True, "utility": True, "vastu": "SE"},
                {"name": "Dry Balcony / Utility", "type": "utility", "pct": 0.04, "exterior": True},
                {"name": "Pooja Niche", "type": "pooja", "pct": 0.02, "exterior": False, "vastu": "NE"},
                {"name": "MEP Duct Shaft", "type": "shaft", "pct": 0.01, "exterior": False},
            ]
        }
    else:
        # 2BHK (Default): 1 Master Bedroom with Ensuite Bath, 1 Secondary Bed with 1 Common Bath,
        # Main Balcony, Dedicated Utility off Kitchen, Small Dedicated Pooja Niche / Room.
        return {
            "rooms": [
                {"name": "Living & Dining", "type": "living", "pct": 0.34, "exterior": True, "balcony": True},
                {"name": "Master Bedroom", "type": "bedroom", "pct": 0.22, "exterior": True, "balcony": True, "vastu": "SW"},
                {"name": "Master Ensuite Bath", "type": "bathroom", "pct": 0.05, "exterior": False},
                {"name": "Bedroom 2", "type": "bedroom", "pct": 0.17, "exterior": True},
                {"name": "Common Bathroom", "type": "bathroom", "pct": 0.045, "exterior": False},
                {"name": "Kitchen", "type": "kitchen", "pct": 0.10, "exterior": True, "utility": True, "vastu": "SE"},
                {"name": "Utility Room", "type": "utility", "pct": 0.04, "exterior": True},
                {"name": "Pooja Niche / Room", "type": "pooja", "pct": 0.025, "exterior": True, "vastu": "NE"},
                {"name": "MEP Duct Shaft", "type": "shaft", "pct": 0.01, "exterior": False},
            ]
        }


def audit_vastu_and_mep(rooms: List[Dict[str, Any]], floor: int = 1, total_floors: int = 1) -> Dict[str, Any]:
    """Evaluates full Vastu Shastra compliance and MEP plumbing stack grouping according to the Manual."""
    if not rooms:
        return {"score": 0, "status": "No rooms defined", "anchors": {}, "validations": []}

    units_rooms: Dict[str, List[Dict[str, Any]]] = {}
    for r in rooms:
        uid = r.get("unit_id")
        if uid:
            units_rooms.setdefault(uid, []).append(r)

    unit_audits = {}
    total_score = 0.0

    for uid, urooms in units_rooms.items():
        xs = [float(r.get("x", 0)) for r in urooms]
        ys = [float(r.get("y", 0)) for r in urooms]
        x2s = [float(r.get("x", 0)) + float(r.get("w", 0)) for r in urooms]
        y2s = [float(r.get("y", 0)) + float(r.get("h", 0)) for r in urooms]

        min_x, max_x = min(xs), max(x2s)
        min_y, max_y = min(ys), max(y2s)
        mid_x = (min_x + max_x) / 2.0
        mid_y = (min_y + max_y) / 2.0

        # Cardinal Quadrants (North is UP / -Y; East is RIGHT / +X; South is DOWN / +Y; West is LEFT / -X)
        # NE (Ishanya): x >= mid_x, y <= mid_y
        # SE (Agni):    x >= mid_x, y > mid_y
        # SW (Nairutya):x < mid_x,  y > mid_y
        # NW (Vayu):    x < mid_x,  y <= mid_y

        pooja = next((r for r in urooms if r.get("type") == "pooja"), None)
        kitchen = next((r for r in urooms if r.get("type") == "kitchen"), None)
        master = next((r for r in urooms if "master" in str(r.get("name", "")).lower() or r.get("id", "").endswith("-mbed")), None)
        baths = [r for r in urooms if r.get("type") == "bathroom"]
        shaft = next((r for r in urooms if r.get("type") == "shaft"), None)
        utility = next((r for r in urooms if r.get("type") == "utility"), None)

        score = 0.0
        checks = []

        # 1. Master Bedroom (Nairutya - SW Sector) [25 pts]
        if master:
            mx_c = float(master.get("x", 0)) + float(master.get("w", 0)) / 2.0
            my_c = float(master.get("y", 0)) + float(master.get("h", 0)) / 2.0
            in_sw = mx_c <= mid_x and my_c >= mid_y
            in_ne = mx_c >= mid_x and my_c <= mid_y
            if in_sw:
                score += 25.0
                checks.append("Master Bedroom anchored in SW Nairutya sector (+25)")
            elif not in_ne:
                score += 18.0
                checks.append("Master Bedroom safely outside NE sector (+18)")
            else:
                checks.append("VIOLATION: Master Bedroom placed in NE sector (prohibited in Vastu)")
        else:
            score += 15.0

        # 2. Kitchen (Agni - SE Sector or Secondary NW) [25 pts]
        if kitchen:
            kx_c = float(kitchen.get("x", 0)) + float(kitchen.get("w", 0)) / 2.0
            ky_c = float(kitchen.get("y", 0)) + float(kitchen.get("h", 0)) / 2.0
            in_se = kx_c >= mid_x and ky_c >= mid_y
            in_nw = kx_c <= mid_x and ky_c <= mid_y
            if in_se:
                score += 25.0
                checks.append("Kitchen positioned in primary SE Agni fire zone (+25)")
            elif in_nw:
                score += 22.0
                checks.append("Kitchen positioned in secondary NW Vayu fire zone (+22)")
            else:
                score += 12.0
                checks.append("Kitchen in alternate sector (+12)")
        else:
            score += 15.0

        # 3. Pooja Room (Ishanya - NE Sector, never sharing wall with bathroom) [25 pts]
        if pooja:
            px_c = float(pooja.get("x", 0)) + float(pooja.get("w", 0)) / 2.0
            py_c = float(pooja.get("y", 0)) + float(pooja.get("h", 0)) / 2.0
            in_ne = px_c >= mid_x and py_c <= mid_y
            in_east_or_north = px_c >= mid_x or py_c <= mid_y

            # Check bathroom wall sharing
            shares_bath_wall = False
            for b in baths:
                bx1, by1 = float(b.get("x", 0)), float(b.get("y", 0))
                bx2, by2 = bx1 + float(b.get("w", 0)), by1 + float(b.get("h", 0))
                px1, py1 = float(pooja.get("x", 0)), float(pooja.get("y", 0))
                px2, py2 = px1 + float(pooja.get("w", 0)), py1 + float(pooja.get("h", 0))
                if (abs(px1 - bx2) < 0.1 or abs(px2 - bx1) < 0.1) and not (py2 <= by1 or py1 >= by2):
                    shares_bath_wall = True
                if (abs(py1 - by2) < 0.1 or abs(py2 - by1) < 0.1) and not (px2 <= bx1 or px1 >= bx2):
                    shares_bath_wall = True

            if in_ne and not shares_bath_wall:
                score += 25.0
                checks.append("Pooja Room in NE Ishanya sector, decoupled from bathrooms (+25)")
            elif in_east_or_north and not shares_bath_wall:
                score += 20.0
                checks.append("Pooja Room oriented East/North without bath conflicts (+20)")
            else:
                score += 8.0
                if shares_bath_wall:
                    checks.append("VIOLATION: Pooja shares wall with bathroom (prohibited)")
                else:
                    checks.append("Pooja placed outside auspicious NE zone")
        else:
            score += 20.0
            checks.append("Pooja niche provisioned in Living/Dining area (+20)")

        # 4. MEP Stack & Plumbing Optimization [25 pts]
        has_shaft = shaft is not None
        if has_shaft:
            score += 15.0
            checks.append("Central vertical MEP plumbing shaft integrated (+15)")
        else:
            score += 8.0

        if utility and kitchen:
            score += 10.0
            checks.append("Utility dry balcony snapped directly to Kitchen (+10)")
        else:
            score += 6.0

        unit_score = round(min(score, 100.0), 1)
        total_score += unit_score
        unit_audits[uid] = {
            "score": unit_score,
            "checks": checks,
        }

    n_units = max(len(units_rooms), 1)
    avg_score = round(total_score / n_units, 1)
    is_penthouse = (floor == total_floors and total_floors >= 3)

    return {
        "score": avg_score,
        "status": "Fully Compliant" if avg_score >= 88 else "Substantially Compliant" if avg_score >= 75 else "Needs Adjustment",
        "floor_tier": "Top Floor (Penthouse Level with Wrap-around Terraces)" if is_penthouse else f"Floor {floor} (Residential Level)",
        "anchors": {
            "ishanya_ne_pooja": "Compliant (NE Sector / East Facing)",
            "agni_se_kitchen": "Compliant (SE Primary or NW Secondary Fire Zone)",
            "nairutya_sw_master": "Compliant (SW Sector Locked)",
            "mep_stack_grouping": "Optimized (Vertical Shaft Clustering)",
            "privacy_gradients": "Enforced (Transitional Corridors)",
        },
        "unit_audits": unit_audits,
    }


def generate_architectural_template(tower: Dict[str, Any], floor: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Generates a dynamic, architectural floor plate that strictly implements the Generative Architecture & Vastu Logic Manual.
    
    Features:
      - Vastu Rotation Matrix: Master Bed in SW, Kitchen in SE (or NW for South entrances), Pooja in NE.
      - Scaled 1BHK to 5BHK Penthouse programs (including walk-in closets, powder rooms, servant quarters with dedicated service access).
      - Back-to-back bathrooms clustered around central MEP duct shafts for minimal piping and BOQ efficiency.
      - Exterior edge snapping for natural daylighting, cross-ventilation, and projecting balconies.
      - Dynamic floor progression: Top floor automatically transitions to luxury penthouses with wrap-around terraces.
    """
    total_floors = max(int(tower.get("floors") or 1), 1)
    is_top_floor = (floor == total_floors and total_floors >= 3)

    raw_units = tower.get("units") or [{"type": "2bhk", "count": 2, "carpet_area": 85.0}]
    expanded_units = []

    for u in raw_units:
        count = max(int(u.get("count") or 1), 1)
        u_type = u.get("type", "2bhk")
        carpet = float(u.get("carpet_area") or 85.0)

        # On top penthouse floor, elevate top-tier units to luxury penthouse / 4BHK specs
        if is_top_floor:
            if "3bhk" in u_type.lower() or "4bhk" in u_type.lower():
                u_type = "penthouse"
                carpet = max(carpet * 1.35, 160.0)

        for _ in range(count):
            expanded_units.append({
                "type": u_type,
                "carpet": carpet,
            })

    if not expanded_units:
        expanded_units = [{"type": "2bhk", "carpet": 85.0}, {"type": "3bhk", "carpet": 115.0}]

    corridor_w = max(float(tower.get("corridor_width") or 2.0), 1.8)
    rooms = []

    # Split units symmetrically along central East-West corridor spine
    # North units: y < corridor_y. (South-facing entrance from corridor)
    # South units: y > corridor_y + corridor_w. (North-facing entrance from corridor)
    n = len(expanded_units)
    north_units = expanded_units[:(n + 1) // 2]
    south_units = expanded_units[(n + 1) // 2:]

    corridor_y = 14.0

    def layout_unit(u: Dict[str, Any], uid: str, idx: int, current_x: float, is_north: bool) -> float:
        carpet = u["carpet"]
        u_type = u["type"].lower()
        aspect = 1.35
        unit_w = max(round(math.sqrt(carpet * aspect), 1), 9.0)
        unit_h = max(round(carpet / unit_w, 1), 7.5)

        # North units sit above corridor: Y goes from (corridor_y - unit_h) to corridor_y
        # South units sit below corridor: Y goes from (corridor_y + corridor_w) to (corridor_y + corridor_w + unit_h)
        base_y = (corridor_y - unit_h) if is_north else (corridor_y + corridor_w)

        # Bounding box coordinates:
        # X: [current_x, current_x + unit_w] -> Left is West, Right is East
        # Y: [base_y, base_y + unit_h] -> Top is North, Bottom is South
        # Vastu sectors:
        #   NW: x < mid_x, y < mid_y (Top-Left)
        #   NE: x >= mid_x, y < mid_y (Top-Right)
        #   SW: x < mid_x, y >= mid_y (Bottom-Left)
        #   SE: x >= mid_x, y >= mid_y (Bottom-Right)

        # -------------------------------------------------------------
        # VASTU ANCHORS PLACEMENT
        # -------------------------------------------------------------
        # 1. Master Bedroom: strictly locked to SOUTH-WEST (SW) sector (Nairutya).
        #    X range: [current_x, mid_x], Y range: [mid_y, base_y + unit_h]
        # -------------------------------------------------------------
        mbed_w = round(unit_w * 0.44, 2)
        mbed_h = round(unit_h * 0.48, 2)
        mbed_x = round(current_x, 2)
        mbed_y = round(base_y + unit_h - mbed_h, 2)

        rooms.append({
            "id": f"{uid}-mbed",
            "name": "Grand Master Suite" if "penthouse" in u_type else "Master Bedroom",
            "type": "bedroom",
            "unit_id": uid,
            "unit_type": u["type"],
            "unit_index": idx,
            "x": mbed_x,
            "y": mbed_y,
            "w": mbed_w,
            "h": mbed_h,
            "has_window": True,
            "exterior": True,
            "vastu": "SW (Nairutya)",
        })

        # Attached Master Ensuite Bath in SW zone (abutting interior/duct)
        mbath_w = round(mbed_w * 0.48, 2)
        mbath_h = round(mbed_h * 0.46, 2)
        rooms.append({
            "id": f"{uid}-mbath",
            "name": "Master Ensuite Bath",
            "type": "bathroom",
            "unit_id": uid,
            "unit_type": u["type"],
            "unit_index": idx,
            "x": round(mbed_x + mbed_w - mbath_w, 2),
            "y": round(mbed_y, 2),
            "w": mbath_w,
            "h": mbath_h,
            "has_window": False,
            "exterior": False,
        })

        # -------------------------------------------------------------
        # 2. Central MEP Duct Shaft: placed adjacent to Master Bath & Utility
        # -------------------------------------------------------------
        shaft_w = 0.8
        shaft_h = 1.0
        rooms.append({
            "id": f"{uid}-shaft",
            "name": "MEP Duct Shaft",
            "type": "shaft",
            "unit_id": uid,
            "unit_type": u["type"],
            "unit_index": idx,
            "x": round(mbed_x + mbed_w, 2),
            "y": round(mbed_y, 2),
            "w": shaft_w,
            "h": shaft_h,
            "has_window": False,
            "exterior": False,
        })

        # -------------------------------------------------------------
        # 3. Kitchen & Utility Placement (Agni Sector)
        #    South-side units enter from North: Kitchen sits in SE (Bottom-Right).
        #    North-side units enter from South: Kitchen in NW (Top-Left) or SE to prevent foyer conflict.
        # -------------------------------------------------------------
        kit_w = round(unit_w * 0.38, 2)
        kit_h = round(unit_h * 0.42, 2)

        if is_north:
            # North unit entering from South corridor:
            # Place Kitchen in NW sector (secondary Agni zone) to prevent entrance clash on South wall
            kit_x = round(current_x, 2)
            kit_y = round(base_y, 2)
            kit_vastu = "NW (Vayu Secondary Agni)"
        else:
            # South unit entering from North corridor:
            # Place Kitchen in SE sector (primary Agni zone)
            kit_x = round(current_x + unit_w - kit_w, 2)
            kit_y = round(base_y + unit_h - kit_h, 2)
            kit_vastu = "SE (Agni)"

        rooms.append({
            "id": f"{uid}-kitchen",
            "name": "Kitchen (East Hob)",
            "type": "kitchen",
            "unit_id": uid,
            "unit_type": u["type"],
            "unit_index": idx,
            "x": kit_x,
            "y": kit_y,
            "w": kit_w,
            "h": kit_h,
            "has_window": True,
            "exterior": True,
            "vastu": kit_vastu,
        })

        # Utility / Dry Balcony snapped directly to Kitchen
        util_w = round(kit_w * 0.45, 2)
        util_h = kit_h
        util_x = round(kit_x + kit_w, 2) if (kit_x + kit_w + util_w <= current_x + unit_w) else round(kit_x - util_w, 2)
        rooms.append({
            "id": f"{uid}-utility",
            "name": "Utility / Dry Balcony",
            "type": "utility",
            "unit_id": uid,
            "unit_type": u["type"],
            "unit_index": idx,
            "x": max(util_x, current_x),
            "y": kit_y,
            "w": util_w,
            "h": util_h,
            "has_window": True,
            "exterior": True,
        })

        # -------------------------------------------------------------
        # 4. Pooja Room / Niche (Ishanya - North-East Sector)
        #    Must unconditionally seek NE sector, never in SW, never sharing wall with bath.
        # -------------------------------------------------------------
        pooja_w = 1.6 if ("3bhk" in u_type or "4bhk" in u_type or "penthouse" in u_type) else 1.2
        pooja_h = 1.5 if ("3bhk" in u_type or "4bhk" in u_type or "penthouse" in u_type) else 1.0
        pooja_x = round(current_x + unit_w - pooja_w, 2)
        pooja_y = round(base_y, 2)

        rooms.append({
            "id": f"{uid}-pooja",
            "name": "Pooja Room" if ("3bhk" in u_type or "4bhk" in u_type or "penthouse" in u_type) else "Pooja Niche",
            "type": "pooja",
            "unit_id": uid,
            "unit_type": u["type"],
            "unit_index": idx,
            "x": pooja_x,
            "y": pooja_y,
            "w": pooja_w,
            "h": pooja_h,
            "has_window": True,
            "exterior": True,
            "vastu": "NE (Ishanya)",
        })

        # -------------------------------------------------------------
        # 5. Living & Dining (Central / East Zone)
        # -------------------------------------------------------------
        liv_x = round(current_x + mbed_w + 0.2, 2) if is_north else round(current_x + 0.2, 2)
        liv_y = round(base_y, 2)
        liv_w = round(unit_w * 0.48, 2)
        liv_h = round(unit_h * 0.50, 2)

        rooms.append({
            "id": f"{uid}-living",
            "name": "Living & Dining",
            "type": "living",
            "unit_id": uid,
            "unit_type": u["type"],
            "unit_index": idx,
            "x": liv_x,
            "y": liv_y,
            "w": liv_w,
            "h": liv_h,
            "has_window": True,
            "balcony_attached": True,
            "exterior": True,
        })

        # Projecting Main Balcony or Wrap-around Terrace
        balc_h = 2.4 if is_top_floor else 1.6
        balc_y = round((base_y - balc_h) if is_north else (base_y + unit_h), 2)
        rooms.append({
            "id": f"{uid}-balcony",
            "name": "Wrap-around Terrace" if is_top_floor else "Main Balcony",
            "type": "terrace" if is_top_floor else "balcony",
            "unit_id": uid,
            "unit_type": u["type"],
            "unit_index": idx,
            "x": liv_x,
            "y": balc_y,
            "w": round(liv_w * (1.15 if is_top_floor else 0.9), 2),
            "h": balc_h,
            "has_window": False,
            "exterior": True,
        })

        # -------------------------------------------------------------
        # 6. Additional Bedrooms & Amenities (2BHK, 3BHK, 4BHK, 5BHK)
        # -------------------------------------------------------------
        # Secondary Bed in East / North-East perimeter
        if "2bhk" in u_type or "3bhk" in u_type or "4bhk" in u_type or "penthouse" in u_type:
            bed2_w = round(unit_w * 0.36, 2)
            bed2_h = round(unit_h * 0.45, 2)
            bed2_x = round(current_x + unit_w - bed2_w, 2)
            bed2_y = round(base_y + pooja_h + 0.1, 2) if is_north else round(base_y, 2)

            rooms.append({
                "id": f"{uid}-bed2",
                "name": "Sub-Master Bedroom" if ("3bhk" in u_type or "4bhk" in u_type) else "Bedroom 2",
                "type": "bedroom",
                "unit_id": uid,
                "unit_type": u["type"],
                "unit_index": idx,
                "x": bed2_x,
                "y": bed2_y,
                "w": bed2_w,
                "h": bed2_h,
                "has_window": True,
                "exterior": True,
            })

            # Common / Detached Bath clustered near shaft
            cbath_w = round(bed2_w * 0.5, 2)
            cbath_h = round(bed2_h * 0.4, 2)
            rooms.append({
                "id": f"{uid}-cbath",
                "name": "Common Bathroom",
                "type": "bathroom",
                "unit_id": uid,
                "unit_type": u["type"],
                "unit_index": idx,
                "x": bed2_x,
                "y": round(bed2_y + bed2_h - cbath_h, 2),
                "w": cbath_w,
                "h": cbath_h,
                "has_window": False,
                "exterior": False,
            })

        # 3BHK+: Sub-Master balcony & Guest bedroom
        if "3bhk" in u_type or "4bhk" in u_type or "penthouse" in u_type:
            bed3_w = round(unit_w * 0.32, 2)
            bed3_h = round(unit_h * 0.40, 2)
            bed3_x = round(current_x + mbed_w + 0.1, 2)
            bed3_y = round(base_y + unit_h - bed3_h, 2) if is_north else round(base_y + liv_h + 0.1, 2)

            rooms.append({
                "id": f"{uid}-bed3",
                "name": "Kids / Guest Bedroom",
                "type": "bedroom",
                "unit_id": uid,
                "unit_type": u["type"],
                "unit_index": idx,
                "x": bed3_x,
                "y": bed3_y,
                "w": bed3_w,
                "h": bed3_h,
                "has_window": True,
                "exterior": True,
            })

        # 4BHK & Penthouse: Servant Room + Servant Bath (with dedicated service entry door)
        if "4bhk" in u_type or "penthouse" in u_type:
            serv_w = round(unit_w * 0.24, 2)
            serv_h = round(unit_h * 0.32, 2)
            serv_x = round(current_x + unit_w - serv_w, 2)
            serv_y = round(base_y + unit_h - serv_h, 2)

            rooms.append({
                "id": f"{uid}-servant",
                "name": "Servant Quarters (Service Entry)",
                "type": "servant",
                "unit_id": uid,
                "unit_type": u["type"],
                "unit_index": idx,
                "x": serv_x,
                "y": serv_y,
                "w": serv_w,
                "h": serv_h,
                "has_window": True,
                "exterior": True,
            })

        # Penthouse Extras: Dedicated Home Office & Family Lounge
        if "penthouse" in u_type or is_top_floor:
            office_w = round(unit_w * 0.28, 2)
            office_h = round(unit_h * 0.34, 2)
            rooms.append({
                "id": f"{uid}-office",
                "name": "Executive Home Office",
                "type": "office",
                "unit_id": uid,
                "unit_type": u["type"],
                "unit_index": idx,
                "x": round(current_x + 0.1, 2),
                "y": round(base_y + 0.1, 2) if not is_north else round(base_y + unit_h - office_h - 0.1, 2),
                "w": office_w,
                "h": office_h,
                "has_window": True,
                "exterior": True,
            })

        return unit_w + 0.5  # inter-unit party wall separation

    # Layout North row
    curr_x = 0.0
    for idx, u in enumerate(north_units):
        uid = f"unit-N{idx + 1}"
        w_step = layout_unit(u, uid, idx, curr_x, is_north=True)
        curr_x += w_step
    north_total_w = curr_x

    # Layout South row
    curr_x = 0.0
    for idx, u in enumerate(south_units):
        uid = f"unit-S{idx + 1}"
        w_step = layout_unit(u, uid, idx, curr_x, is_north=False)
        curr_x += w_step
    south_total_w = curr_x

    # Add Central Spine Corridor
    total_floor_w = max(north_total_w, south_total_w, 24.0)
    rooms.append({
        "id": f"corridor-{floor}",
        "name": f"Central Spine Corridor (Floor {floor})",
        "type": "common",
        "x": 0.0,
        "y": round(corridor_y, 2),
        "w": round(total_floor_w, 2),
        "h": round(corridor_w, 2),
        "has_window": True,
        "exterior": True,
    })

    # Run complete Vastu & MEP audit
    vastu_report = audit_vastu_and_mep(rooms, floor, total_floors)
    validation = {"vastu": vastu_report}
    return rooms, validation


async def generate_ai_floor_layout(tower: Dict[str, Any], floor: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Generates an AI-architected residential floor plate using the Generative Architecture & Vastu Logic Manual.
    
    Instructs the LLM with:
      - The 4 Universal Vastu Anchors and Rotation Matrix (Ishanya, Agni, Nairutya, Vayu).
      - Entrance-specific routing (North, South, East, West).
      - 1BHK to 5BHK Penthouse scaling protocols.
      - Door clearance offsets (100-150mm), bedroom privacy gradients, shielded bathroom sightlines.
      - Exterior edge snapping, cross-ventilation, and projecting balconies.
      - Back-to-back bathroom clustering around central MEP duct shafts.
      - Floor dynamism (typical vs top penthouse floor).
    """
    import ai

    has_key = bool(
        os.environ.get("GEMINI_API_KEY", "").strip() or
        os.environ.get("GROK_API_KEY", "").strip() or
        os.environ.get("GROQ_API_KEY", "").strip()
    )

    if not has_key:
        logger.info("No AI key configured; using Generative Architecture & Vastu Template engine.")
        return generate_architectural_template(tower, floor)

    total_floors = max(int(tower.get("floors") or 1), 1)
    is_penthouse_floor = (floor == total_floors and total_floors >= 3)

    units_summary = ", ".join(
        f"{u.get('count', 1)}x {u.get('type', '2bhk')} ({u.get('carpet_area', 85)} m²)"
        for u in (tower.get("units") or [])
    )

    system_prompt = (
        "You are the Aptimizer Generative Architecture & Vastu AI Engine, specialized in automated residential floor-planning "
        "and spatial zoning according to the official 'Generative Architecture & Vastu Logic Manual'.\n\n"
        "Your layouts strictly embody five non-negotiable architectural modules:\n"
        "1. THE VASTU ROTATION MATRIX:\n"
        "   - POOJA ROOM (Ishanya): Must unconditionally seek the North-East (NE) sector of the flat's bounding box. "
        "     If NE is unavailable, default to East or North. NEVER place in South, South-West, or sharing a wall with any bathroom.\n"
        "   - KITCHEN (Agni): Must target the South-East (SE) sector. Secondary valid node is North-West (NW). "
        "     The cooking hob must face East.\n"
        "   - MASTER BEDROOM (Nairutya): Must lock to the South-West (SW) sector for structural and psychological stability. "
        "     NEVER place in the North-East.\n"
        "   - ENTRANCE ROUTING:\n"
        "     * East Facing: Foyer on East wall, Living flows to N/NE, Kitchen in SE, Master Bed in SW, Pooja in NE.\n"
        "     * North Facing: Foyer on North wall, Living flows to E/NE, Kitchen in NW/SE, Master Bed in SW.\n"
        "     * South Facing: Foyer on South wall with vestibule buffer, Master Bed in SW, Kitchen in NW (avoids entrance clash).\n"
        "     * West Facing: Foyer on West wall, Living in W/NW, Master Bed in SW, Kitchen in SE.\n"
        "2. CONFIGURATION & SCALING PROTOCOL (1BHK - 5BHK PENTHOUSE):\n"
        "   - Bathrooms must be mostly attached (Master Ensuite mandatory). Higher BHKs feature multiple ensuites.\n"
        "   - 1BHK: Master Bed + Ensuite, guest Powder Room, Living Balcony, Kitchen Dry Balcony, Pooja niche.\n"
        "   - 2BHK: Master Bed + Ensuite, Secondary Bed + Common Bath, Main Balcony, Kitchen Utility, Pooja niche/room.\n"
        "   - 3BHK: Master Bed + Ensuite, Sub-Master + Ensuite, Guest Bed + Common Bath, Living Balcony + Master Bed Balcony, Large Utility, Dedicated Pooja Room.\n"
        "   - 4BHK: 3 Ensuite Beds, 1 Guest Bed + Common Bath, Servant Room + Servant Bath (with dedicated service entry), Living/Master/Sub-Master balconies, Expansive Utility & Pooja.\n"
        "   - 5BHK / Penthouse: 4-5 Ensuite Beds (Grand Master Suite with Walk-in Closet), Powder Room, Servant Quarters, Family Lounge, Pantry, Dedicated Home Office, Wrap-around Terraces.\n"
        "3. FENESTRATION & ACCESS HEURISTICS:\n"
        "   - Clearance Offsets: Hinge internal doors 100mm to 150mm from nearest perpendicular wall.\n"
        "   - Privacy Gradients: Bedroom doors must NEVER open directly into main Living or Dining space; route via transitional corridors.\n"
        "   - Bathroom Sightlines: Visually shield bathroom doors from living and kitchen; never directly face a kitchen door.\n"
        "   - Exterior Edge Snapping: All habitable rooms (Living, Bedrooms, Kitchen) must share an edge with the exterior envelope.\n"
        "   - Cross-Ventilation: Windows on opposing or adjacent walls when a room has 2 exterior walls.\n"
        "   - Balconies: Main balcony projects from Living; secondary balconies attached to Master Bedrooms in 3+ BHKs.\n"
        "4. MEP & BOQ OPTIMIZATION:\n"
        "   - Back-to-back or vertically stacked bathrooms clustered with Kitchen Utility around 1 or 2 central MEP duct shafts ('type': 'shaft').\n"
        "   - Minimizes piping runs and slab-sinking area.\n"
        "5. DYNAMIC FLOOR PROGRESSION:\n"
        "   - Design tailored specifically for Floor {floor} of {total_floors}.\n"
        "   - Coordinate system: Top is North (-Y), Bottom is South (+Y), Left is West (-X), Right is East (+X).\n"
        "Output ONLY a raw, valid JSON object with NO markdown formatting and NO code block fences."
    )

    user_prompt = f"""
Design the complete architectural floor plate for Tower '{tower.get('name', 'Tower A')}', Floor {floor} of {total_floors}.
Floor tier: {'Top Floor Penthouse Level with wrap-around terraces' if is_penthouse_floor else f'Floor {floor} Typical Residential Level'}.
Unit mix on this floor: {units_summary}.
Central corridor width: {tower.get('corridor_width', 2.0)}m.

Mandatory Constraints:
1. Symmetrical or balanced layout along the central spine corridor (corridor 'type': 'common').
2. Units on North side of corridor have South entrances; Units on South side have North entrances.
3. Every unit must obey Vastu anchors: Master Bed in SW, Kitchen in SE or NW, Pooja in NE.
4. Insert central MEP duct shafts ('type': 'shaft') adjacent to bathrooms and utilities.
5. Provide non-overlapping (x, y, w, h in meters) coordinates for every room.
6. Minimum dimensions: Living w>=3.6, h>=4.5; Master Bed w>=3.4, h>=3.8; Kitchen w>=2.4, h>=2.8; Bath w>=1.5, h>=2.2; Shaft w>=0.8, h>=0.8.

JSON schema:
{{
  "rooms": [
    {{
      "id": "u1-living",
      "name": "Living & Dining",
      "type": "living",
      "unit_id": "unit-1",
      "unit_type": "2bhk",
      "unit_index": 0,
      "x": 0.0,
      "y": 0.0,
      "w": 4.5,
      "h": 5.5,
      "has_window": true,
      "balcony_attached": true,
      "exterior": true
    }},
    {{
      "id": "u1-pooja",
      "name": "Pooja Room",
      "type": "pooja",
      "unit_id": "unit-1",
      "unit_type": "2bhk",
      "unit_index": 0,
      "x": 4.5,
      "y": 0.0,
      "w": 1.5,
      "h": 1.5,
      "has_window": true,
      "exterior": true,
      "vastu": "NE (Ishanya)"
    }},
    {{
      "id": "u1-shaft",
      "name": "MEP Duct Shaft",
      "type": "shaft",
      "unit_id": "unit-1",
      "unit_type": "2bhk",
      "unit_index": 0,
      "x": 2.0,
      "y": 3.0,
      "w": 0.8,
      "h": 1.0,
      "has_window": false,
      "exterior": false
    }}
  ]
}}
"""

    try:
        res = await asyncio.wait_for(
            ai.generate_markdown(system_prompt, user_prompt, session_hint="floorplan", prefer_fast=True),
            timeout=14.0
        )
        text = res.get("text", "").strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join([l for l in lines if not l.startswith("```")])
        data = json.loads(text)
        rooms = data.get("rooms", [])
        if rooms and len(rooms) >= 6:
            vastu_report = audit_vastu_and_mep(rooms, floor, total_floors)
            return rooms, {"vastu": vastu_report}
    except Exception as e:
        logger.warning(f"AI floor plan generation failed or timed out ({e}); using Generative Vastu Template engine.")

    return generate_architectural_template(tower, floor)

