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

import vastu
from floorplan.realistic import generate_unit as generate_realistic_unit

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


def audit_vastu_and_mep(rooms: List[Dict[str, Any]], floor: int = 1, total_floors: int = 1,
                        boxes: Optional[Dict[str, Any]] = None,
                        meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """What the plan actually achieves against the manual, stated as found.

    Two lists, never merged. `violations` are hard rules broken — a balcony off an internal
    wall, a pooja room with no door onto the living room or a wall shared with a bathroom,
    overlapping rooms, plan that belongs to no room. `anchors` reports the soft sector
    targets one by one, each carrying the sector the room is actually in.

    The previous version of this function returned a fixed dictionary of "Compliant"
    strings regardless of what the checks found, so a plan with a logged VIOLATION still
    reported every anchor as met. An audit that cannot say no is not an audit.
    """
    if not rooms:
        return {"score": 0, "status": "No rooms defined", "anchors": {}, "violations": [],
                "unit_audits": {}}

    boxes = boxes or {}
    meta = meta or {}

    units_rooms: Dict[str, List[Dict[str, Any]]] = {}
    for r in rooms:
        uid = r.get("unit_id")
        if uid:
            units_rooms.setdefault(uid, []).append(r)

    unit_audits: Dict[str, Any] = {}
    all_violations: List[str] = []
    anchor_tally = {"pooja": [0, 0], "kitchen": [0, 0], "master": [0, 0]}   # [met, placed]
    total_score = 0.0

    for uid, urooms in units_rooms.items():
        box = boxes.get(uid) or _bounding_box(urooms)
        info = meta.get(uid, {})
        exterior = info.get("exterior_edges") or ["N", "S", "E", "W"]
        entry = info.get("entry_edge") or "S"

        hard = vastu.check_unit(urooms, box, exterior, entry)
        sectors = vastu.sector_report(urooms, box)
        for key, rep in sectors.items():
            if rep.get("placed"):
                anchor_tally[key][1] += 1
                if rep.get("met"):
                    anchor_tally[key][0] += 1

        # Score is the share of the manual's rules this flat actually meets: hard rules
        # carry three quarters of it because a broken one is a defect, not a preference.
        placed = [k for k, r in sectors.items() if r.get("placed")]
        soft = (sum(1 for k in placed if sectors[k].get("met")) / len(placed)) if placed else 1.0
        hard_share = 0.0 if hard["violations"] else 1.0
        score = round((hard_share * 0.75 + soft * 0.25) * 100, 1)
        total_score += score

        all_violations.extend(f"{uid}: {v}" for v in hard["violations"])
        unit_audits[uid] = {
            "score": score,
            "unit_type": info.get("unit_type"),
            "entry_edge": entry,
            "facing": {"S": "South facing", "N": "North facing",
                       "E": "East facing", "W": "West facing"}.get(entry, entry),
            "coverage_pct": hard["coverage_pct"],
            "violations": hard["violations"],
            "anchors": sectors,
            "notes": info.get("notes", []),
            "checks": [f"{k}: {v['detail']}" for k, v in sectors.items() if v.get("placed")],
        }

    n_units = max(len(units_rooms), 1)
    avg_score = round(total_score / n_units, 1)

    def anchor_line(key, label):
        met, placed = anchor_tally[key]
        if not placed:
            return f"{label}: not in this floor's programme"
        if met == placed:
            return f"{label}: in sector in all {placed} flat(s)"
        return f"{label}: in sector in {met} of {placed} flat(s)"

    return {
        "score": avg_score,
        # Wording follows the violations, not the score: any hard breach is "Non-compliant"
        # however well the flat scores on sectors.
        "status": ("Non-compliant — hard rules broken" if all_violations
                   else "Fully Compliant" if avg_score >= 88
                   else "Compliant, some sector targets unmet"),
        "floor_tier": ("Top Floor (Penthouse Level with wrap-around terraces)"
                       if floor == total_floors and total_floors >= 3
                       else f"Floor {floor} (Residential Level)"),
        "violations": all_violations,
        "anchors": {
            "ishanya_ne_pooja": anchor_line("pooja", "Pooja (Ishanya, NE)"),
            "agni_se_kitchen": anchor_line("kitchen", "Kitchen (Agni, SE / NW)"),
            "nairutya_sw_master": anchor_line("master", "Master bedroom (Nairutya, SW)"),
            "balconies_on_air": ("every balcony projects from an exterior wall"
                                 if not any("balcony" in v for v in all_violations)
                                 else "a balcony is not on an exterior wall — see violations"),
            "pooja_door_from_living": ("every pooja room takes its door off the living room"
                                       if not any("pooja" in v for v in all_violations)
                                       else "a pooja room fails its door or bathroom rule — see violations"),
            "privacy_gradients": ("bedroom doors route through a passage or foyer"
                                  if not any("passage or foyer" in v for v in all_violations)
                                  else "a bedroom has no transitional space to open onto"),
        },
        "unit_audits": unit_audits,
    }


def _bounding_box(rooms: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The flat's box, recovered from its rooms — used when the caller did not supply one
    (an audit of a stored plan, or of one an LLM returned)."""
    xs = [float(r.get("x", 0)) for r in rooms]
    ys = [float(r.get("y", 0)) for r in rooms]
    x2 = [float(r.get("x", 0)) + float(r.get("w", 0)) for r in rooms]
    y2 = [float(r.get("y", 0)) + float(r.get("h", 0)) for r in rooms]
    return {"x": min(xs), "y": min(ys), "w": max(x2) - min(xs), "h": max(y2) - min(ys)}


def generate_architectural_template(tower: Dict[str, Any], floor: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """A floor plate packed to the Generative Architecture & Vastu Logic Manual.

    Placement is delegated to `vastu.pack_unit`, which subdivides each flat by guillotine
    cuts: every cut consumes its rectangle exactly, so rooms cannot overlap and no strip of
    plan is left belonging to nothing. What no room claims becomes passage — which is also
    the transitional corridor the manual requires bedroom doors to route through instead of
    opening onto the living room.

    The hard rules (balconies on air, the pooja's door off the living room and its walls
    clear of any bathroom, utility snapped to the kitchen, full coverage) are enforced by
    construction and then re-checked by `vastu.check_unit`. The sector anchors are targeted
    and reported as achieved or not — a flat with one facade cannot always give all three
    their sector, and saying otherwise would be the least useful thing this could do.
    """
    total_floors = max(int(tower.get("floors") or 1), 1)
    is_top_floor = (floor == total_floors and total_floors >= 3)

    raw_units = tower.get("units") or [{"type": "2bhk", "count": 2, "carpet_area": 85.0}]
    expanded_units = []
    for u in raw_units:
        count = max(int(u.get("count") or 1), 1)
        u_type = u.get("type", "2bhk")
        carpet = float(u.get("carpet_area") or 85.0)
        # The manual's top-tier progression: the top floor lifts 3/4BHK stock to penthouse.
        if is_top_floor and ("3bhk" in u_type.lower() or "4bhk" in u_type.lower()):
            u_type = "penthouse"
            carpet = max(carpet * 1.35, 160.0)
        for _ in range(count):
            expanded_units.append({"type": u_type, "carpet": carpet})
    if not expanded_units:
        expanded_units = [{"type": "2bhk", "carpet": 85.0}, {"type": "3bhk", "carpet": 115.0}]

    corridor_w = max(float(tower.get("corridor_width") or 2.0), 1.8)
    n = len(expanded_units)
    north_units = expanded_units[:(n + 1) // 2]
    south_units = expanded_units[(n + 1) // 2:]

    # A flat is proportioned to its own carpet area; the row is as deep as its deepest flat
    # so both rows meet the corridor on a straight line.
    def dims(u):
        """Choose a usable depth before asking a room planner to divide the unit.

        The former full-depth-column packer made an 85 m2 two-bedroom unit roughly 20.5 m
        wide and only 7 m deep. Every room then became a long strip by construction. The
        realistic planner needs enough depth for a foyer, living zone and private passage,
        so standard 1-3BHK units receive a compact, practical envelope first.
        """
        prog = vastu.unit_programme(u["type"], u["carpet"])
        if prog["beds"] <= 5:
            # Larger homes get more circulation and service allowance, but still preserve
            # enough suite width for one bedroom plus one attached bath per bedroom.
            gross = u["carpet"] * (1.18 if prog["beds"] <= 3 else 1.28)
            if prog["beds"] == 1:
                # A studio-sized unit still needs a real entry sequence; below this depth
                # a foyer plus living room collapses into a single strip.
                return max(round(math.sqrt(gross * 1.15), 1), 9.0), 9.0
            # At least 4.8 m per bedroom suite gives beds and baths enough width without
            # forcing the facade into a line of narrow, full-depth boxes.
            w = max(math.sqrt(gross * 1.15), prog["beds"] * 4.8)
            h = gross / w
            min_depth = {2: 9.2, 3: 9.8, 4: 10.5, 5: 11.2}[prog["beds"]]
            return round(w, 1), round(max(h, min_depth), 1)

        # Large/penthouse programmes retain the legacy packer until the full multi-zone
        # generator is enabled for their service and secondary-entry requirements.
        # bedrooms + living + kitchen, each wanting a column on the facade.
        facade_rooms = prog["beds"] + 2 + (1 if prog["is_penthouse"] else 0)
        # The columns are not equal: the master, the living room and the kitchen are wider
        # than a secondary bedroom, so an equal-share estimate under-reads the frontage and
        # the narrowest column still lands below the minimum. The 2.15 is that extra width,
        # expressed in bedroom-widths, taken from the slot weights in vastu.pack_unit.
        needed = (facade_rooms + 2.15) * (vastu.MIN_COLUMN_W + 0.35) + 2.4   # + pooja strip
        w = max(round(math.sqrt(u["carpet"] * 1.15), 1), round(needed, 1), 7.5)
        return w, max(round(u["carpet"] / w, 1), 7.0)

    north_dims = [dims(u) for u in north_units]
    south_dims = [dims(u) for u in south_units]
    north_h = max([h for _, h in north_dims], default=0.0)
    south_h = max([h for _, h in south_dims], default=0.0)
    corridor_y = north_h

    rooms: List[Dict[str, Any]] = []
    unit_boxes: Dict[str, Dict[str, Any]] = {}
    unit_meta: Dict[str, Dict[str, Any]] = {}

    def place_row(units, dimensions, is_north):
        """Lay one row of flats along the corridor.

        The corridor is the wall each flat is entered from, so it is also the one wall that
        is NOT open to air. A north-row flat is entered from its south wall and is therefore
        South-facing in the manual's rotation matrix; a south-row flat is North-facing. End
        flats gain their outer side wall as a second facade.
        """
        cursor = 0.0
        entry_edge = "S" if is_north else "N"
        last = len(units) - 1
        for idx, (u, (uw, uh)) in enumerate(zip(units, dimensions)):
            uid = f"unit-{'N' if is_north else 'S'}{idx + 1}"
            box_y = (corridor_y - uh) if is_north else (corridor_y + corridor_w)
            box = {"x": round(cursor, 2), "y": round(box_y, 2), "w": uw, "h": uh}
            exterior = ["N"] if is_north else ["S"]
            if idx == 0:
                exterior.append("W")
            if idx == last:
                exterior.append("E")
            packed, notes = generate_realistic_unit(box, u["type"], u["carpet"], entry_edge,
                                                    uid, idx, exterior)
            if not packed:
                packed, legacy_notes = vastu.pack_unit(box, u["type"], u["carpet"], entry_edge,
                                                        exterior, uid, idx)
                notes = notes + legacy_notes
            rooms.extend(packed)
            unit_boxes[uid] = box
            unit_meta[uid] = {"entry_edge": entry_edge, "exterior_edges": exterior,
                              "notes": notes, "unit_type": u["type"], "carpet": u["carpet"]}
            cursor += uw + 0.5      # party wall between flats
        return max(cursor - 0.5, 0.0)

    north_w = place_row(north_units, north_dims, True)
    south_w = place_row(south_units, south_dims, False)

    total_floor_w = max(north_w, south_w, 12.0)
    rooms.append({
        "id": f"corridor-{floor}",
        "name": f"Central Spine Corridor (Floor {floor})",
        "type": "common",
        "x": 0.0, "y": round(corridor_y, 2),
        "w": round(total_floor_w, 2), "h": round(corridor_w, 2),
        "has_window": True, "exterior": True,
    })

    validation = {"vastu": audit_vastu_and_mep(rooms, floor, total_floors,
                                               boxes=unit_boxes, meta=unit_meta)}
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
        rooms, validation = generate_architectural_template(tower, floor)
        validation["vastu"]["source"] = "packer (no model key configured)"
        return rooms, validation

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
            # The model's plan is checked against the same hard rules the packer is held to,
            # and is used only if it passes. A layout is geometry: overlapping rooms, a
            # balcony off an internal wall or a pooja room walled against a bathroom are
            # wrong whoever drew them, and a plausible-looking plan that fails them is worse
            # than the deterministic one, because it looks considered.
            vastu_report = audit_vastu_and_mep(rooms, floor, total_floors)
            if not vastu_report.get("violations"):
                vastu_report["source"] = "model"
                return rooms, {"vastu": vastu_report}
            logger.info("AI floor plan rejected on %d hard rule(s): %s",
                        len(vastu_report["violations"]), "; ".join(vastu_report["violations"][:3]))
            rejected = vastu_report["violations"][:6]
            rooms, validation = generate_architectural_template(tower, floor)
            validation["vastu"]["source"] = "packer (model plan rejected)"
            validation["vastu"]["rejected_model_plan"] = rejected
            return rooms, validation
    except Exception as e:
        logger.warning(f"AI floor plan generation failed or timed out ({e}); using Generative Vastu Template engine.")

    rooms, validation = generate_architectural_template(tower, floor)
    validation["vastu"]["source"] = "packer"
    return rooms, validation

