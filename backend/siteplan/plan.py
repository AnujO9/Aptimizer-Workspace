"""Full pipeline: envelope -> reservation -> tower packing -> serialisable layout."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from shapely.geometry.base import BaseGeometry

from .config import SiteLayoutConfig
from .envelope import build_envelope
from .errors import LayoutError
from .fitness import FitnessResult, PackContext, TowerPlacement, evaluate
from .frame import geom_to_latlng, geom_to_local, polygons_of
from .pack import greedy_pack
from .reserve import ReserveResult, reserve


@dataclass
class LayoutResult:
    reservation: ReserveResult
    towers: List[TowerPlacement]
    fitness: FitnessResult
    warnings: List[str] = field(default_factory=list)
    method: str = "greedy"

    def to_dict(self) -> Dict[str, Any]:
        res = self.reservation
        frame = res.envelope.frame
        cfg = res.envelope.config
        plot_area = res.envelope.plot.area

        floor_area = sum(t.floor_area for t in self.towers)
        footprint = sum(t.footprint_area for t in self.towers)
        units = sum(t.units(cfg) for t in self.towers)
        open_space = plot_area - footprint

        base = res.to_dict()
        base.update({
            "stage": "layout",
            "method": self.method,
            "towers": [
                {
                    "name": t.name,
                    "polygons": geom_to_latlng(t.polygon, frame),
                    "polygons_local": geom_to_local(t.polygon),
                    "centre_local": [round(t.cx, 3), round(t.cy, 3)],
                    "centre_latlng": frame.to_latlng(t.cx, t.cy),
                    "width_m": round(t.width, 2),
                    "depth_m": round(t.depth, 2),
                    "rotation_deg": round(t.rotation_deg, 2),
                    "floors": t.floors,
                    "floor_height_m": t.floor_height,
                    "height_m": round(t.height_m, 2),
                    "footprint_sqm": round(t.footprint_area, 2),
                    "floor_area_sqm": round(t.floor_area, 2),
                    "units": t.units(cfg),
                }
                for t in self.towers
            ],
            "layout_metrics": {
                "tower_count": len(self.towers),
                "total_buildable_area_sqm": round(floor_area, 2),
                "total_footprint_sqm": round(footprint, 2),
                "achieved_far": round(floor_area / plot_area, 3) if plot_area else 0.0,
                "far_cap": cfg.far_cap,
                "ground_coverage_pct": round(footprint / plot_area * 100, 2) if plot_area else 0.0,
                "open_space_pct": round(open_space / plot_area * 100, 2) if plot_area else 0.0,
                "unit_count": units,
                "feasible": self.fitness.feasible,
                "score": round(self.fitness.score, 2) if self.fitness.feasible else None,
                "penalties": {k: round(v, 2) for k, v in self.fitness.penalties.items()},
            },
        })
        base["warnings"] = base.get("warnings", []) + self.warnings
        return base


def plan(coordinates: Sequence[Sequence[float]],
         road_edges: Optional[Sequence[Dict[str, Any]]] = None,
         config: Optional[SiteLayoutConfig] = None) -> LayoutResult:
    cfg = config or SiteLayoutConfig()
    env = build_envelope(coordinates, road_edges, cfg)
    res = reserve(env, cfg)

    ctx = PackContext(region=res.residual, roads=res.roads,
                      plot_area=env.plot.area, cfg=cfg)
    towers, notes = greedy_pack(ctx)
    fit = evaluate(towers, ctx)

    warnings = list(notes)
    if not towers:
        warnings.append("No tower footprint fits the packable land at the configured sizes. "
                        "Reduce the setbacks, the ring width or the minimum footprint.")
    if not fit.feasible:
        warnings.append("Layout failed a hard constraint: " + "; ".join(fit.hard_violations[:3]))

    return LayoutResult(reservation=res, towers=towers, fitness=fit,
                        warnings=warnings, method="greedy")


def plan_site(project: Dict[str, Any],
              overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Stage 3 entry point: project document -> full optimised site layout."""
    plot = project.get("plot") or {}
    cfg = SiteLayoutConfig.from_dict(overrides)
    try:
        return plan(plot.get("coordinates") or [],
                    plot.get("road_edges") or [], cfg).to_dict()
    except LayoutError as exc:
        return exc.to_dict()
