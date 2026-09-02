"""Unit tests for AI and architectural floor plan generation."""
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

    # Check that all coordinates and dimensions are positive
    for r in rooms:
        assert r["w"] > 0
        assert r["h"] > 0
        assert r["x"] >= 0
        assert r["y"] >= 0


import asyncio


def test_ai_floor_layout_fallback_or_generation():
    tower = default_tower("Tower B")
    rooms, validation = asyncio.run(aifloorplan.generate_ai_floor_layout(tower, floor=2))
    assert len(rooms) >= 8
    assert all("name" in r and "type" in r for r in rooms)
