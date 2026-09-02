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

    for mb in master_beds:
        assert "SW" in mb.get("vastu", "")
    for p in poojas:
        assert "NE" in p.get("vastu", "")


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
    # Wrap-around terrace and office on penthouse floor
    types_f12 = {r["type"] for r in rooms_f12}
    assert "terrace" in types_f12
    assert "office" in types_f12


def test_ai_floor_layout_fallback_or_generation():
    tower = default_tower("Tower B")
    rooms, validation = asyncio.run(aifloorplan.generate_ai_floor_layout(tower, floor=2))
    assert len(rooms) >= 8
    assert all("name" in r and "type" in r for r in rooms)
    assert "vastu" in validation or "score" in validation

