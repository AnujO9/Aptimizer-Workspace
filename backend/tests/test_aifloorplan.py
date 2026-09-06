"""Unit tests for AI and architectural floor plan generation."""
import asyncio
import pytest
from defaults import default_project, default_tower
import aifloorplan


def test_architectural_template_generates_rooms_and_balconies():
    tower = default_tower("Tower A")
    tower["units"] = [
        {"type": "2bhk", "count": 2, "carpet_area": 85.0},
        {"type": "3bhk", "count": 1, "carpet_area": 120.0},
    ]
    rooms, validation = aifloorplan.generate_architectural_template(tower, floor=1)
    assert len(rooms) >= 10
    types = {r["type"] for r in rooms}
    assert "living" in types
    assert "bedroom" in types
    assert "kitchen" in types
    assert "bathroom" in types
    assert "balcony" in types
    assert "pooja" in types
    assert "shaft" in types

    # Check that all coordinates and dimensions are positive
    for r in rooms:
        assert r["w"] > 0
        assert r["h"] > 0
        assert r["x"] >= 0
        assert r["y"] >= 0


def test_vastu_anchors_and_rotation_matrix():
    tower = default_tower("Tower Vastu")
    tower["units"] = [
        {"type": "3bhk", "count": 2, "carpet_area": 130.0},
    ]
    rooms, validation = aifloorplan.generate_architectural_template(tower, floor=2)
    val = validation.get("vastu") or validation
    assert val["score"] >= 88.0
    assert val["status"] == "Fully Compliant"

    # Verify Master Bedroom in SW sector and Pooja in NE sector
    master_beds = [r for r in rooms if r["id"].endswith("-mbed")]
    poojas = [r for r in rooms if r["type"] == "pooja"]
    kitchens = [r for r in rooms if r["type"] == "kitchen"]
    shafts = [r for r in rooms if r["type"] == "shaft"]

    assert len(master_beds) >= 2
    assert len(poojas) >= 2
    assert len(kitchens) >= 2
    assert len(shafts) >= 2

    # The `vastu` label is the sector the room is ACTUALLY in, so it is checked against the
    # geometry rather than taken at face value. It used to be a constant written onto every
    # master bedroom regardless of placement, which made asserting on it meaningless.
    import vastu as vastulib
    by_unit = {}
    for r in rooms:
        if r.get("unit_id"):
            by_unit.setdefault(r["unit_id"], []).append(r)
    boxes = {uid: vastulib._bounding_box_of(rs) for uid, rs in by_unit.items()}

    for mb in master_beds:
        assert vastulib.sector_of(mb, boxes[mb["unit_id"]]) in mb["vastu"]
        # Nairutya is the target; NE is the one sector the manual forbids outright.
        assert "NE" not in mb["vastu"]
    for p in poojas:
        assert "NE" in p.get("vastu", "")

    # A flat entered from the south has its corridor on the south wall, so a daylit SW is
    # not available to it; the row entered from the north does get a true SW master.
    south_row = [mb for mb in master_beds if mb["unit_id"].startswith("unit-S")]
    assert south_row and all("SW" in mb["vastu"] for mb in south_row)


def test_scaling_protocol_1bhk_to_5bhk_penthouse():
    # 1BHK scaling
    spec_1bhk = aifloorplan._unit_spec("1bhk", 50.0)
    names_1bhk = [r["name"] for r in spec_1bhk["rooms"]]
    assert "Ensuite Bathroom" in names_1bhk
    assert any("pooja" in n.lower() for n in names_1bhk)

    # 4BHK scaling
    spec_4bhk = aifloorplan._unit_spec("4bhk", 160.0)
    names_4bhk = [r["name"] for r in spec_4bhk["rooms"]]
    assert "Servant Room" in names_4bhk
    assert "Servant Bath" in names_4bhk
    assert "Pooja Room (Ishanya)" in names_4bhk

    # 5BHK Penthouse scaling
    spec_5bhk = aifloorplan._unit_spec("5bhk", 240.0)
    names_5bhk = [r["name"] for r in spec_5bhk["rooms"]]
    assert "Grand Master Suite" in names_5bhk
    assert "Walk-in Closet" in names_5bhk
    assert "Dedicated Home Office" in names_5bhk
    assert "Family Lounge" in names_5bhk
    assert "Pantry & Dry Storage" in names_5bhk


def test_dynamic_floor_progression_typical_vs_penthouse():
    tower = default_tower("Tower Highrise")
    tower["floors"] = 12
    tower["units"] = [
        {"type": "3bhk", "count": 2, "carpet_area": 120.0},
    ]

    # Typical floor (Floor 4)
    rooms_f4, val_f4 = aifloorplan.generate_architectural_template(tower, floor=4)
    v4 = val_f4.get("vastu") or val_f4
    assert "Residential Level" in v4["floor_tier"]
    assert any(r["type"] == "balcony" for r in rooms_f4)

    # Top floor (Floor 12 - Penthouse tier)
    rooms_f12, val_f12 = aifloorplan.generate_architectural_template(tower, floor=12)
    v12 = val_f12.get("vastu") or val_f12
    assert "Penthouse Level" in v12["floor_tier"]
    types_f12 = {r["type"] for r in rooms_f12}
    assert "terrace" in types_f12          # balconies become wrap-around terraces up here

    # The home office needs a column of facade of its own, so it appears only when the flat
    # has the frontage for it. A 120 m2 3BHK lifted to penthouse does not: five bedrooms,
    # living, kitchen and pooja already use every metre, and the packer drops the office
    # rather than squeezing the rooms that need daylight. It says so in the notes.
    office_note = [n for u in v12["unit_audits"].values() for n in u["notes"] if "Office omitted" in n]
    assert ("office" in types_f12) or office_note, v12["unit_audits"]

    # Given the frontage, it is placed.
    wide = default_tower("Tower Wide")
    wide["floors"] = 12
    wide["units"] = [{"type": "penthouse", "count": 2, "carpet_area": 420.0}]
    rooms_wide, _ = aifloorplan.generate_architectural_template(wide, floor=12)
    assert "office" in {r["type"] for r in rooms_wide}


def test_ai_floor_layout_fallback_or_generation():
    tower = default_tower("Tower B")
    rooms, validation = asyncio.run(aifloorplan.generate_ai_floor_layout(tower, floor=2))
    assert len(rooms) >= 8
    assert all("name" in r and "type" in r for r in rooms)
    assert "vastu" in validation or "score" in validation


def test_standard_units_use_one_entry_and_a_private_bedroom_route():
    """The deterministic planner must not turn every rendered door into an entrance."""
    tower = default_tower("Tower Logical")
    tower["units"] = [
        {"type": "1bhk", "count": 1, "carpet_area": 55.0},
        {"type": "2bhk", "count": 1, "carpet_area": 85.0},
        {"type": "3bhk", "count": 1, "carpet_area": 130.0},
    ]
    rooms, _ = aifloorplan.generate_architectural_template(tower, floor=1)
    by_unit = {}
    for room in rooms:
        if room.get("unit_id"):
            by_unit.setdefault(room["unit_id"], []).append(room)

    assert len(by_unit) == 3
    for unit_rooms in by_unit.values():
        assert sum(room.get("main_entrance") is True for room in unit_rooms) == 1
        assert any(room["type"] == "living" and room.get("door_to") == "foyer"
                   for room in unit_rooms)
        assert all(room.get("door_to") == "passage" for room in unit_rooms
                   if room["type"] == "bedroom")

        habitable = [room for room in unit_rooms
                     if room["type"] in {"living", "bedroom", "kitchen"}]
        assert max(max(room["w"], room["h"]) / min(room["w"], room["h"])
                   for room in habitable) <= 2.8

