"""Compact, human-readable residential unit layouts.

This is deliberately a deterministic layout engine, not a language-model drawing.  It
creates one front door, an entry foyer that opens into the living room, and a separate
private passage for bedrooms.  Coordinates are returned in the legacy metre payload so
the existing plan renderer and storage format continue to work.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple


def _programme(unit_type: str) -> int:
    text = (unit_type or "2bhk").lower()
    if "penthouse" in text:
        return 5
    for beds in (5, 4, 3, 2, 1):
        if f"{beds}bhk" in text:
            return beds
    return 2


def _rect(x: float, y: float, w: float, h: float) -> Dict[str, float]:
    return {"x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "h": round(h, 2)}


def _orient(rect: Dict[str, float], width: float, height: float, entry_edge: str) -> Dict[str, float]:
    """Rotate the canonical south-entry plan without changing room proportions."""
    x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
    if entry_edge == "S":
        return _rect(x, y, w, h)
    if entry_edge == "N":
        return _rect(x, height - y - h, w, h)
    if entry_edge == "E":
        return _rect(height - y - h, x, h, w)
    # West entry: a quarter turn in the other direction.
    return _rect(y, width - x - w, h, w)


def generate_unit(box: Dict[str, float], unit_type: str, carpet: float, entry_edge: str,
                  uid: str, unit_index: int, exterior_edges: Sequence[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Generate a practical unit layout that tiles ``box``.

    The room sequence is intentionally fixed: external main door -> foyer -> living;
    bedrooms are reached from a private hallway and bathrooms are never represented as
    extra entrances.  Larger programmes keep their additional rooms in the same zoned
    pattern rather than squeezing more full-depth columns into the envelope.
    """
    beds = _programme(unit_type)
    width, height = float(box["w"]), float(box["h"])
    canonical = entry_edge in ("S", "N")
    plan_w, plan_h = (width, height) if canonical else (height, width)
    x0, y0 = (float(box["x"]), float(box["y"])) if canonical else (float(box["y"]), float(box["x"]))

    # A unit with less depth than this cannot hold a foyer, living room and private hall
    # without making at least one habitable room a corridor-shaped rectangle.  The caller
    # keeps the existing packer for those envelopes and reports the constraint upstream.
    if plan_w < 9.0 or plan_h < 8.0:
        return [], ["Envelope is too constrained for the realistic unit planner; use a wider/deeper unit envelope."]

    north_h = min(3.4, plan_h * 0.30)
    hall_h = max(0.9, min(1.05, plan_h * 0.10))
    entry_h = min(2.15, plan_h * 0.23)
    middle_h = plan_h - north_h - hall_h - entry_h
    if middle_h < 3.0:
        return [], ["Envelope leaves less than 2.45 m for a living room after required circulation."]

    rooms: List[Dict[str, Any]] = []

    def emit(key: str, name: str, room_type: str, rect: Dict[str, float], **extra: Any) -> Dict[str, Any]:
        placed = _orient(rect, plan_w, plan_h, entry_edge)
        # _orient produces local coordinates. Move its origin back to the unit location.
        placed["x"] = round(placed["x"] + x0, 2)
        placed["y"] = round(placed["y"] + y0, 2)
        room: Dict[str, Any] = {
            "id": f"{uid}-{key}", "name": name, "type": room_type,
            "unit_id": uid, "unit_type": unit_type, "unit_index": unit_index,
            **placed, **extra,
        }
        rooms.append(room)
        return room

    # Private suites sit on the quiet facade.  Every programme receives exactly one
    # attached bathroom for each bedroom: no generic common bath is silently reused.
    suite_w = plan_w / beds
    for index in range(beds):
        key = "mbed" if index == 0 else f"bed{index + 1}"
        bath_key = "mbath" if index == 0 else f"bath{index + 1}"
        bath_w = min(max(1.45, suite_w * 0.30), suite_w * 0.42)
        bed_w = suite_w - bath_w
        x = index * suite_w
        bed_name = "Master Bedroom" if index == 0 else f"Bedroom {index + 1}"
        bath_name = "Master Ensuite Bath" if index == 0 else f"Bedroom {index + 1} Ensuite Bath"
        emit(key, bed_name, "bedroom", _rect(x, 0, bed_w, north_h),
             has_window=True, door_to="passage",
             **({"headboard": "South or West wall"} if index == 0 else {}))
        emit(bath_key, bath_name, "bathroom", _rect(x + bed_w, 0, bath_w, north_h),
             has_window=False, door_to=key, door_child_of=key)

    hall_y = north_h
    emit("passage", "Private Passage", "passage", _rect(0, hall_y, plan_w, hall_h),
         door_to="living")

    middle_y = hall_y + hall_h
    social_h = min(3.2, middle_h)
    social_y = middle_y + middle_h - social_h
    kitchen_w = min(3.0, max(2.45, plan_w * 0.16))
    non_kitchen_w = plan_w - kitchen_w
    living_w = min(5.2, max(3.6, non_kitchen_w * 0.48))
    dining_w = min(3.2, max(2.4, non_kitchen_w * 0.28)) if beds >= 2 else 0.0
    flexible_w = non_kitchen_w - living_w - dining_w
    emit("living", "Living", "living", _rect(0, social_y, living_w, social_h),
         has_window=True, door_to="foyer")
    if dining_w:
        emit("dining", "Dining", "living", _rect(living_w, social_y, dining_w, social_h), has_window=True)
    if flexible_w > 0.3:
        extra_name = "Family Lounge" if beds >= 4 else "Study / Family Nook"
        extra_type = "living" if beds >= 4 else "study"
        emit("family", extra_name, extra_type, _rect(living_w + dining_w, social_y, flexible_w, social_h),
             has_window=True)
    emit("kitchen", "Kitchen", "kitchen", _rect(non_kitchen_w, social_y, kitchen_w, social_h),
         has_window=True, door_to="dining" if dining_w else "living", hob_faces="East")

    # Larger homes receive a second social/work zone, rather than an inflated kitchen or
    # dining room.  This band also makes their circulation visibly distinct from 1-3BHK.
    if social_y > middle_y:
        upper_h = social_y - middle_y
        if beds >= 5:
            office_w = min(3.5, plan_w * 0.22)
            emit("office", "Home Office", "office", _rect(0, middle_y, office_w, upper_h), has_window=True)
            emit("family_upper", "Family Lounge", "living", _rect(office_w, middle_y, plan_w - office_w, upper_h), has_window=True)
        elif beds == 4:
            emit("family_upper", "Family Lounge", "living", _rect(0, middle_y, plan_w, upper_h), has_window=True)
        else:
            emit("upper_passage", "Gallery Passage", "passage", _rect(0, middle_y, plan_w, upper_h), door_to="passage")

    entry_y = middle_y + middle_h
    foyer_w = min(2.6, max(2.2, plan_w * 0.22))
    foyer_x = round(max(0, min(living_w - foyer_w, (living_w - foyer_w) / 2)), 2)
    # The foyer is the only room with an external main door.  The adjacent circulation
    # areas are internal access only and carry no external openings.
    left_w, right_x = foyer_x, foyer_x + foyer_w
    # This compact service strip keeps the plumbing core beside the kitchen/bathrooms
    # without turning it into a second way into the apartment.
    if beds >= 2 and left_w >= 2.45:
        shaft_w = 0.85
        pooja_w = min(1.75, left_w - shaft_w)
        emit("pooja", "Pooja Room", "pooja", _rect(0, entry_y, pooja_w, entry_h),
             door_to="living", faces="East")
        emit("shaft", "MEP Duct Shaft", "shaft", _rect(pooja_w, entry_y, shaft_w, entry_h),
             has_window=False)
        if left_w - pooja_w - shaft_w > 0:
            emit("entrypassage_w", "Entry Passage", "passage",
                 _rect(pooja_w + shaft_w, entry_y, left_w - pooja_w - shaft_w, entry_h), door_to="foyer")
    elif left_w > 0:
        emit("entrypassage_w", "Entry Passage", "passage", _rect(0, entry_y, left_w, entry_h), door_to="foyer")
    emit("foyer", "Entrance Foyer", "entrance", _rect(foyer_x, entry_y, foyer_w, entry_h),
         door_to="living", main_entrance=True, entry_edge=entry_edge)
    if plan_w - right_x > 0:
        emit("entrypassage_e", "Entry Passage", "passage", _rect(right_x, entry_y, plan_w - right_x, entry_h), door_to="foyer")

    # Utility is adjacent to the kitchen and does not gain an external/main door.
    utility_w = min(kitchen_w, plan_w - right_x)
    utility = next((r for r in rooms if r["id"].endswith("-entrypassage_e")), None)
    if utility is not None:
        utility.update({"id": f"{uid}-utility", "name": "Utility / Wash Area", "type": "utility",
                        "door_to": "kitchen", "has_window": False})

    return rooms, [
        "One main entrance is placed on the unit entry wall.",
        "Arrival sequence is main entrance -> foyer -> living and dining.",
        "Bedroom and bathroom doors are served by the private passage; they do not open into the living room.",
    ]
