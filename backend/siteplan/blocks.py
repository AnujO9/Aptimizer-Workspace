"""Straight-line circulation geometry.

Roads on a site plan are built, not grown: a contractor sets out a straight centreline and
kerbs it. The previous reservation derived the access ring from `envelope.buffer(-w)`,
which traces the plot boundary — so on any plot that is not a rectangle the "road" came
out curved, kinked, or split into slivers, and the internal spines were clipped polygons
rather than corridors. Nothing downstream could even name a centreline for it.

This module reserves circulation the way it is actually laid out:

  1. Find the plot's own grid — the principal axis of the buildable envelope — and work in
     it, so the network is orthogonal to the site rather than to north.
  2. Inside that frame, take the largest axis-aligned rectangle that fits in the envelope.
     That rectangle is the development block; every road is a rectangle cut from it, so
     straightness holds by construction rather than by tolerance.
  3. The perimeter ring is four straight bands (N/S/E/W) around the block; the internal
     spines are full-span bands across the core. Each corridor carries its own centreline
     so the renderer never has to reverse-engineer one from a polygon.
  4. Land inside the envelope but outside the block is not packable — it is the leftover
     landscape strip, and it is returned as such so it can be planted rather than built on.

Everything is produced in the rotated frame and rotated back once, at the end.
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np
from shapely import contains_xy
from shapely.affinity import rotate
from shapely.geometry import LineString, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .frame import polygons_of

# Raster used to seed the inscribed-rectangle search. The seed is refined analytically
# afterwards, so this only has to be close — it is not the accuracy of the result.
_TARGET_CELLS = 20_000
_MIN_CELL_M = 0.20
_MAX_CELLS_PER_AXIS = 400
# Binary-search refinement: 24 halvings take a 500 m span to well under a millimetre.
_REFINE_STEPS = 24


@dataclass
class RoadCorridor:
    """One straight road. `polygon` is always a rectangle; `centreline` is its axis."""
    polygon: Polygon
    centreline: LineString
    width_m: float
    kind: str          # "ring" | "spine"
    label: str         # "north" / "east" / ... / "spine 1"


@dataclass
class BlockNetwork:
    """The development blocks and the circulation cut out of them, in the world frame.

    A plot that is not a rectangle cannot be served by one rectangular block without
    abandoning land, so the envelope is covered by up to `max_blocks` rectangles taken
    largest-first. Each is a self-contained sector: its own straight ring, its own drives.
    Whatever no block can cover is `leftover` — landscape, not building land.
    """
    blocks: List[Polygon] = field(default_factory=list)
    core: BaseGeometry = field(default_factory=Polygon)        # inside the rings
    residual: BaseGeometry = field(default_factory=Polygon)    # core minus spines
    ring: List[RoadCorridor] = field(default_factory=list)
    spines: List[RoadCorridor] = field(default_factory=list)
    leftover: BaseGeometry = field(default_factory=Polygon)
    angle_deg: float = 0.0
    warnings: List[str] = field(default_factory=list)

    @property
    def block(self) -> BaseGeometry:
        return unary_union(self.blocks) if self.blocks else Polygon()

    @property
    def corridors(self) -> List[RoadCorridor]:
        return self.ring + self.spines

    @property
    def ring_geometry(self) -> BaseGeometry:
        return unary_union([c.polygon for c in self.ring]) if self.ring else Polygon()

    @property
    def spine_geometry(self) -> BaseGeometry:
        return unary_union([c.polygon for c in self.spines]) if self.spines else Polygon()


# ---------------------------------------------------------------- principal frame
def principal_angle(geom: BaseGeometry) -> float:
    """Degrees of the long axis of `geom`'s minimum rotated rectangle, in [0, 180)."""
    if geom is None or geom.is_empty:
        return 0.0
    try:
        pts = list(geom.minimum_rotated_rectangle.exterior.coords[:-1])
    except (AttributeError, ValueError):
        return 0.0
    if len(pts) < 4:
        return 0.0
    e1 = math.dist(pts[0], pts[1])
    e2 = math.dist(pts[1], pts[2])
    a, b = (pts[0], pts[1]) if e1 >= e2 else (pts[1], pts[2])
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0


def candidate_angles(geom: BaseGeometry, limit: int = 5) -> List[float]:
    """Grid orientations worth trying, best guess first.

    The minimum rotated rectangle is the usual answer, but it is a poor one for a plot
    shaped like a cross or a Y, where the enclosing rectangle says nothing about how the
    land actually runs. The plot's own longest edges nearly always do, so they are offered
    as alternatives and the caller keeps whichever covers the most land.
    """
    out = [principal_angle(geom)]
    out.append((out[0] + 90.0) % 180.0)
    edges: List[Tuple[float, float]] = []
    for part in polygons_of(geom):
        ring = list(part.exterior.coords)
        for i in range(len(ring) - 1):
            (x1, y1), (x2, y2) = ring[i], ring[i + 1]
            length = math.hypot(x2 - x1, y2 - y1)
            if length > 1e-6:
                edges.append((length, math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0))
    edges.sort(reverse=True)
    for _, a in edges:
        out.append(a)
    seen: List[float] = []
    for a in out:
        a = round(a % 180.0, 2)
        if all(abs(a - s) > 2.0 and abs(abs(a - s) - 180.0) > 2.0 for s in seen):
            seen.append(a)
        if len(seen) >= limit:
            break
    return seen


# ---------------------------------------------------------------- inscribed rectangle
def _max_rect_in_mask(mask: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    """Largest all-True axis-aligned rectangle in a boolean matrix.

    Classic maximal-rectangle: per row, maintain the height of the True run ending at each
    column, then take the largest rectangle in that histogram with the usual monotonic
    stack. O(rows x cols).

    Returns (row0, col0, row1, col1) inclusive, or None when the mask is all False.
    """
    rows, cols = mask.shape
    if rows == 0 or cols == 0:
        return None

    heights = [0] * cols
    best_area = 0
    best: Optional[Tuple[int, int, int, int]] = None

    for r in range(rows):
        row = mask[r]
        for c in range(cols):
            heights[c] = heights[c] + 1 if row[c] else 0

        stack: List[Tuple[int, int]] = []          # (start column, height)
        for c in range(cols + 1):
            h = heights[c] if c < cols else 0
            start = c
            while stack and stack[-1][1] >= h:
                idx, hh = stack.pop()
                area = hh * (c - idx)
                if area > best_area:
                    best_area = area
                    best = (r - hh + 1, idx, r, c - 1)
                start = idx
            stack.append((start, h))

    return best


def _grow(poly: Polygon, rect: Tuple[float, float, float, float],
          limits: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """Push each side of `rect` outward as far as `poly` still contains it.

    The raster seed is quantised to a cell, which on a rectangular plot would lose up to
    one cell of land on every side. Four independent binary searches recover the exact
    edge, which is what makes this return the plot itself when the plot *is* a rectangle.
    """
    minx, miny, maxx, maxy = rect
    lo_x, lo_y, hi_x, hi_y = limits

    def push(side: int, target: float) -> float:
        lo, hi = 0.0, abs(target - (minx, miny, maxx, maxy)[side])
        if hi <= 1e-9:
            return (minx, miny, maxx, maxy)[side]
        for _ in range(_REFINE_STEPS):
            mid = (lo + hi) / 2.0
            trial = [minx, miny, maxx, maxy]
            trial[side] += -mid if side < 2 else mid
            if poly.contains(box(*trial)):
                lo = mid
            else:
                hi = mid
        return (minx, miny, maxx, maxy)[side] + (-lo if side < 2 else lo)

    minx = push(0, lo_x)
    miny = push(1, lo_y)
    maxx = push(2, hi_x)
    maxy = push(3, hi_y)
    return minx, miny, maxx, maxy


def largest_inscribed_rect(poly: Polygon, safety: float = 0.0) -> Optional[Polygon]:
    """Largest axis-aligned rectangle contained in `poly` (approximate, then refined).

    `safety` is held clear of the boundary, so the result is contained in `poly` with room
    to spare — the layout engine treats any containment breach as a hard error, and a
    rectangle that touches the envelope to the last float is one rounding away from one.
    """
    if poly is None or poly.is_empty or poly.area <= 0:
        return None

    inner = poly.buffer(-safety) if safety > 0 else poly
    parts = polygons_of(inner)
    if not parts:
        return None
    host = parts[0]

    minx, miny, maxx, maxy = host.bounds
    span_x, span_y = maxx - minx, maxy - miny
    if span_x <= 0 or span_y <= 0:
        return None

    # A rectangular plot is the common case and deserves an exact answer, not a raster.
    mrr = host.minimum_rotated_rectangle
    if mrr.area > 0 and host.area / mrr.area > 0.999:
        rect = box(minx, miny, maxx, maxy)
        if host.contains(rect):
            return rect

    cell = max(math.sqrt(span_x * span_y / _TARGET_CELLS), _MIN_CELL_M)
    ncols = min(max(int(span_x / cell), 1), _MAX_CELLS_PER_AXIS)
    nrows = min(max(int(span_y / cell), 1), _MAX_CELLS_PER_AXIS)
    dx, dy = span_x / ncols, span_y / nrows

    # A cell counts only when its whole square is inside, which is exactly "its centre is
    # inside the polygon eroded by the cell's half-diagonal". Testing centres against the
    # eroded polygon is one vectorised call instead of ncols x nrows contains() tests.
    half_diag = math.hypot(dx, dy) / 2.0
    safe = host.buffer(-half_diag)
    if safe.is_empty:
        return None

    xs = minx + (np.arange(ncols) + 0.5) * dx
    ys = miny + (np.arange(nrows) + 0.5) * dy
    gx, gy = np.meshgrid(xs, ys)
    mask = contains_xy(safe, gx.ravel(), gy.ravel()).reshape(nrows, ncols)
    if not mask.any():
        return None

    found = _max_rect_in_mask(mask)
    if not found:
        return None
    r0, c0, r1, c1 = found

    # Span cell *centres*, not cell edges: every cell in the block has its full square
    # inside, so the centre-to-centre rectangle is strictly interior even before refining.
    seed = (float(xs[c0]), float(ys[r0]), float(xs[c1]), float(ys[r1]))
    if seed[2] - seed[0] <= 0 or seed[3] - seed[1] <= 0:
        return None

    grown = _grow(host, seed, (minx, miny, maxx, maxy))
    rect = box(*grown)
    if not host.contains(rect):
        rect = box(*seed)
        if not host.contains(rect):
            return None
    return rect


# ---------------------------------------------------------------- corridors
def _corridor(rect: Polygon, a: Tuple[float, float], b: Tuple[float, float],
              width: float, kind: str, label: str) -> RoadCorridor:
    return RoadCorridor(polygon=rect, centreline=LineString([a, b]),
                        width_m=round(width, 3), kind=kind, label=label)


def _ring_bands(minx: float, miny: float, maxx: float, maxy: float,
                w: float) -> List[RoadCorridor]:
    """Four straight bands whose union is the rectangular annulus of width `w`.

    The east and west bands are trimmed to the span between the north and south bands, so
    the four rectangles tile the annulus exactly instead of overlapping at the corners —
    which keeps every reported road area additive.
    """
    h = w / 2.0
    return [
        _corridor(box(minx, maxy - w, maxx, maxy),
                  (minx + h, maxy - h), (maxx - h, maxy - h), w, "ring", "north"),
        _corridor(box(minx, miny, maxx, miny + w),
                  (minx + h, miny + h), (maxx - h, miny + h), w, "ring", "south"),
        _corridor(box(minx, miny + w, minx + w, maxy - w),
                  (minx + h, miny + h), (minx + h, maxy - h), w, "ring", "west"),
        _corridor(box(maxx - w, miny + w, maxx, maxy - w),
                  (maxx - h, miny + h), (maxx - h, maxy - h), w, "ring", "east"),
    ]


def _spine_bands(minx: float, miny: float, maxx: float, maxy: float,
                 width: float, reach: float, central_min: float) -> Tuple[List[RoadCorridor], str]:
    """Straight full-span drives across the core.

    Reachability is a one-dimensional property: a strip is within `reach` of a road
    everywhere as soon as its *thinnest* dimension is under 2 x reach, so the core only
    ever needs subdividing in one direction. Both are costed and the cheaper — less land
    under tarmac — is chosen.
    """
    W, H = maxx - minx, maxy - miny
    if W <= 0 or H <= 0:
        return [], ""

    n_x = n_y = 0
    if reach > 0 and min(W, H) > 2.0 * reach:
        n_y = max(math.ceil(H / (2.0 * reach)) - 1, 0)     # bands running east-west
        n_x = max(math.ceil(W / (2.0 * reach)) - 1, 0)     # bands running north-south
        # Cost is the tarmac each option lays down.
        if n_y * W <= n_x * H:
            n_x = 0
        else:
            n_y = 0

    note = "reach"
    if n_x == 0 and n_y == 0:
        # No road is *required*, but a core deep enough to hold two rows of flats reads as
        # a car park without one, and the drive is what the surface bays line.
        if central_min > 0 and min(W, H) >= central_min:
            note = "central"
            if H >= W:
                n_y = 1
            else:
                n_x = 1
        else:
            return [], ""

    out: List[RoadCorridor] = []
    half = width / 2.0
    if n_y:
        step = H / (n_y + 1)
        for i in range(1, n_y + 1):
            y = miny + step * i
            out.append(_corridor(box(minx, y - half, maxx, y + half),
                                 (minx, y), (maxx, y), width, "spine", f"spine {i}"))
    if n_x:
        step = W / (n_x + 1)
        for i in range(1, n_x + 1):
            x = minx + step * i
            out.append(_corridor(box(x - half, miny, x + half, maxy),
                                 (x, miny), (x, maxy), width, "spine", f"spine {i}"))
    return out, note


def _rotate_corridor(c: RoadCorridor, angle: float, origin) -> RoadCorridor:
    return RoadCorridor(polygon=rotate(c.polygon, angle, origin=origin),
                        centreline=rotate(c.centreline, angle, origin=origin),
                        width_m=c.width_m, kind=c.kind, label=c.label)


# ---------------------------------------------------------------- entry point
def _serve_block(rect: Polygon, ring_width: float, driveway_width: float,
                 reach: float, central_spine_min_core: float, index: int,
                 ) -> Tuple[List[RoadCorridor], List[RoadCorridor], BaseGeometry, List[str]]:
    """One rectangle -> its ring, its drives, and the core inside the ring."""
    warnings: List[str] = []
    minx, miny, maxx, maxy = rect.bounds
    W, H = maxx - minx, maxy - miny
    ring: List[RoadCorridor] = []
    spines: List[RoadCorridor] = []

    if ring_width > 0:
        if min(W, H) <= 2.0 * ring_width:
            if index == 0:
                warnings.append(
                    f"The buildable envelope is narrower than the {ring_width:g} m access "
                    "ring, so the whole block is reserved for circulation and no land "
                    "remains for towers. Reduce the setbacks or the ring width.")
            return _ring_bands(minx, miny, maxx, maxy, min(W, H) / 2.0), [], Polygon(), warnings
        ring = _ring_bands(minx, miny, maxx, maxy, ring_width)
        core = box(minx + ring_width, miny + ring_width, maxx - ring_width, maxy - ring_width)
    else:
        core = box(minx, miny, maxx, maxy)

    if driveway_width > 0 and not core.is_empty:
        cminx, cminy, cmaxx, cmaxy = core.bounds
        spines, note = _spine_bands(cminx, cminy, cmaxx, cmaxy, driveway_width,
                                    reach, central_spine_min_core)
        for i, c in enumerate(spines):
            c.label = f"spine {index + 1}.{i + 1}" if index else f"spine {i + 1}"
        if spines and note == "reach":
            warnings.append(
                f"Added {len(spines)} straight internal drive(s) so no buildable land sits "
                f"more than {reach:.0f} m from a road.")
    return ring, spines, core, warnings


def _cover(local: BaseGeometry, ring_width: float, ring_offset: float,
           safety: float, max_blocks: int, min_block_area: float,
           min_region_area: float) -> Tuple[List[Polygon], List[str]]:
    """Cover an axis-aligned envelope with straight-sided blocks, largest first."""
    warnings: List[str] = []
    rects: List[Polygon] = []
    remaining: BaseGeometry = local

    # A secondary block is only worth taking if it can hold a ring and a building; below
    # that it is landscape.
    min_secondary_extent = 2.0 * ring_width + 20.0
    for i in range(max(max_blocks, 1)):
        parts = [p for p in polygons_of(remaining) if p.area >= min_region_area]
        if not parts:
            break
        best: Optional[Polygon] = None
        for part in parts:
            if best is not None and part.area <= best.area:
                break                       # parts are area-sorted; nothing left can win
            cand = largest_inscribed_rect(part, safety=safety)
            if cand is not None and (best is None or cand.area > best.area):
                best = cand
        if best is None:
            break
        if i > 0:
            bminx, bminy, bmaxx, bmaxy = best.bounds
            if (best.area < min_block_area
                    or min(bmaxx - bminx, bmaxy - bminy) < min_secondary_extent):
                break
        if i == 0 and ring_offset > 0:
            trial = best.buffer(-ring_offset, join_style="mitre")
            if trial.is_empty or trial.area <= 0 or not isinstance(trial, Polygon):
                warnings.append(f"A {ring_offset:g} m ring offset consumes the whole "
                                "development block; the offset was ignored.")
            else:
                best = box(*trial.bounds)
        rects.append(best)
        remaining = remaining.difference(best)

    return rects, warnings


def build_network(envelope: BaseGeometry, ring_width: float, ring_offset: float,
                  driveway_width: float, max_distance_to_road: float,
                  central_spine_min_core: float = 0.0,
                  safety: float = 0.02, max_blocks: int = 3,
                  min_block_area: float = 900.0,
                  min_region_area: float = 25.0) -> Optional[BlockNetwork]:
    """Envelope -> development blocks + straight ring and spine corridors.

    Returns None when no rectangle of any use fits inside the envelope; the caller decides
    whether that is a warning or an error.
    """
    if envelope is None or envelope.is_empty:
        return None
    pivot = envelope.centroid

    # Try a handful of site grids and keep the one that leaves the least land unbuildable.
    best_angle, best_rects, warnings = 0.0, [], []
    best_area = -1.0
    for angle in candidate_angles(envelope):
        local = rotate(envelope, -angle, origin=pivot)
        if not polygons_of(local):
            continue
        rects, notes = _cover(local, ring_width, ring_offset, safety,
                              max_blocks, min_block_area, min_region_area)
        covered = sum(r.area for r in rects)
        if covered > best_area:
            best_area, best_angle, best_rects, warnings = covered, angle, rects, notes

    if not best_rects:
        return None

    angle = best_angle
    rects = best_rects
    local = rotate(envelope, -angle, origin=pivot)

    ring: List[RoadCorridor] = []
    spines: List[RoadCorridor] = []
    cores: List[BaseGeometry] = []
    for i, rect in enumerate(rects):
        r, s, core, w = _serve_block(rect, ring_width, driveway_width,
                                     max_distance_to_road, central_spine_min_core, i)
        ring += r
        spines += s
        if not core.is_empty:
            cores.append(core)
        warnings += w

    if len(rects) > 1:
        warnings.append(
            f"The boundary is not rectangular, so the buildable land was laid out as "
            f"{len(rects)} straight-sided blocks; land outside them is landscaped.")

    core_local = unary_union(cores) if cores else Polygon()
    spine_geom_local = unary_union([c.polygon for c in spines]) if spines else Polygon()
    residual_local = (core_local.difference(spine_geom_local)
                      if not spine_geom_local.is_empty else core_local)
    leftover_local = local.difference(unary_union(rects))

    def back(geom: BaseGeometry) -> BaseGeometry:
        return rotate(geom, angle, origin=pivot) if geom is not None and not geom.is_empty else Polygon()

    return BlockNetwork(
        blocks=[rotate(r, angle, origin=pivot) for r in rects],
        core=back(core_local),
        residual=back(residual_local),
        ring=[_rotate_corridor(c, angle, pivot) for c in ring],
        spines=[_rotate_corridor(c, angle, pivot) for c in spines],
        leftover=back(leftover_local),
        angle_deg=round(angle, 3),
        warnings=warnings,
    )


def corridors_to_dict(corridors: Sequence[RoadCorridor], frame) -> List[dict]:
    """Serialise corridors with both their footprint and their centreline.

    The centreline is the point of this: a renderer that has to infer one from a polygon
    gets it wrong the moment the polygon is not the rectangle it assumed.
    """
    from .frame import geom_to_latlng   # local import keeps frame.py dependency-free

    out = []
    for c in corridors:
        line_local = [[round(x, 3), round(y, 3)] for x, y in c.centreline.coords]
        out.append({
            "kind": c.kind,
            "label": c.label,
            "width_m": c.width_m,
            "length_m": round(c.centreline.length, 2),
            "polygons": geom_to_latlng(c.polygon, frame),
            "polygons_local": [[[[round(x, 3), round(y, 3)]
                                 for x, y in c.polygon.exterior.coords[:-1]]]],
            "centreline_local": line_local,
            "centreline": [frame.to_latlng(x, y) for x, y in c.centreline.coords],
        })
    return out
