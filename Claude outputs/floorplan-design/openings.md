# backend/floorplan/openings.py

## Summary
openings.py turns a frozen topology plus realised room geometry into REAL door and window objects with full plan geometry, and is the only module that decides where an opening is cut in a wall. It owns rulebook section 7 (door count, size, corner offset, swing side, swing-arc clash, leaf-vs-window, placement side, facing leaves across a corridor), section 8 (landlocked reject, aggregate glazing ratio, toilet ventilation, window position on its facade segment, daylight depth), and rule 3.5 entry-sightline privacy as a ray cast from the main door. It enforces the rules it can enforce by construction during candidate selection, then re-checks every one of them geometrically on the emitted result, keeping hard violations (H01, H02, H03, H09, H13, H14), soft score terms, and code findings in three separate lists that are never merged. It also owns the serialisation of doors and windows into the stored plan payload, because the frontend renderer currently fakes a swing arc in every room's bottom-left corner and a window band on every room's top edge, and those fakes are deleted in favour of these arrays.

## Interface
```python
# backend/floorplan/openings.py
"""Doors and windows as real objects. Rulebook sections 7, 8 and rule 3.5.

Internal unit is the INTEGER MILLIMETRE, plan-absolute, matching the rulebook.
Axes match the floor plate the app already draws: +x East, +y South (so -y is
North, and y increases downward exactly as SVG does). The conversion boundary
to the metres the renderer and the stored payload use is exactly two functions,
`door_payload` and `window_payload`; nothing else in this module sees a metre.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Any, Iterable, Literal, Mapping, Sequence

# ============================================================ vocabulary

Axis = Literal["v", "h"]              # "v": constant x. "h": constant y.
Cardinal = Literal["N", "E", "S", "W"]
Vec = tuple[int, int]                 # unit normal, one of (1,0) (-1,0) (0,1) (0,-1)

DoorKind = Literal["swing", "sliding", "opening", "panel"]
DoorRole = Literal["main", "room", "ensuite", "utility", "balcony",
                   "service", "through", "panel"]
WindowKind = Literal["window", "french", "ventilator", "louvre"]
OpensTo = Literal["air", "shaft", "balcony"]
FindingStatus = Literal["pass", "fail", "unverified"]

# Room `type` strings are the ones FloorPlate.jsx already colours; do not invent new ones.
THROUGH_SPACE_TYPES = frozenset({"living", "dining", "entrance", "foyer",
                                 "passage", "corridor", "common", "lounge"})
FOYER_TYPES         = frozenset({"entrance", "foyer"})
CORRIDOR_TYPES      = frozenset({"passage", "corridor"})
HABITABLE_TYPES     = frozenset({"living", "dining", "bedroom", "kitchen",
                                 "study", "office", "servant"})
WET_TYPES           = frozenset({"bathroom", "toilet", "wc", "powder"})
SERVICE_TYPES       = frozenset({"utility", "pantry", "wash", "shaft"})
DEPENDENT_TYPES     = frozenset({"balcony", "terrace", "closet", "shaft"}) | WET_TYPES

# ============================================================ inputs (built by __init__.py)

@dataclass(frozen=True)
class WallSeg:
    """One axis-aligned run of a room boundary. `inward` points INTO `room_id`."""
    axis: Axis
    fixed: int                  # mm; x for axis "v", y for axis "h"
    lo: int                     # mm along the varying axis, lo < hi
    hi: int
    room_id: str
    inward: Vec

    @property
    def length_mm(self) -> int: ...
    @property
    def outward(self) -> Vec: ...
    @property
    def cardinal(self) -> Cardinal: ...        # cardinal of `outward`
    def point_at(self, t_mm: int) -> tuple[int, int]: ...   # t measured from `lo`
    def key(self) -> str: ...                  # "v|12400|5000|8200" — stable, hashable

@dataclass(frozen=True)
class RoomShape:
    id: str
    type: str                                  # FloorPlate COLORS key
    name: str
    unit_id: str
    unit_index: int
    polygon: tuple[tuple[int, int], ...]       # mm, axis-aligned, CW in screen space,
                                               # first vertex NOT repeated, <= 6 vertices (5.4.1)
    area_sqm: float
    is_habitable: bool

@dataclass(frozen=True)
class FurnitureRect:
    """Emitted by geometry.py's rule 5.3 packing test. `fixed` is load-bearing:
    a swing arc over a wardrobe or a WC is a hard clash, over a bed it is a penalty."""
    room_id: str
    role: Literal["bed", "wardrobe", "sofa", "tv_wall", "dining_table",
                  "counter", "wc", "basin", "shower", "fridge", "aisle"]
    x: int; y: int; w: int; h: int             # mm, plan-absolute
    fixed: bool

@dataclass(frozen=True)
class FacadeSeg:
    """A run of the unit envelope that is open to something. `opens_to` decides
    whether a window on it counts for rule 8.1/8.2 and at what confidence."""
    axis: Axis
    fixed: int
    lo: int
    hi: int
    outward: Vec
    cardinal: Cardinal
    opens_to: OpensTo | Literal["party", "corridor"]
    shaft_id: str | None = None
    shaft_clear_sqm: float | None = None

@dataclass(frozen=True)
class AccessEdge:
    """One connection from the FROZEN access graph. openings never adds or removes one."""
    a: str                     # room id, or "" for outside the unit (main door)
    b: str                     # room id
    role: DoorRole
    serves: str                # room id whose one-door budget this consumes; "" for through/main

@dataclass(frozen=True)
class OpeningsContext:
    unit_id: str
    unit_index: int
    unit_type: str                             # "2BHK" etc, for reporting only
    rooms: tuple[RoomShape, ...]
    edges: tuple[AccessEdge, ...]
    furniture: tuple[FurnitureRect, ...]
    facade: tuple[FacadeSeg, ...]
    entry_point: tuple[int, int]               # mm, where the common lobby meets the unit
    entry_cardinal: Cardinal                   # outward cardinal of the entry wall
    lobby_room_id: str | None = None           # plate-level corridor, if it is a room
    climate_zone: str | None = None            # one of spec.CLIMATE_ZONES, or None = unknown
    code_version: str | None = None            # iscodes.NBC_2016 / SP7_2026 / None = default

    @classmethod
    def build(cls, *, unit_id: str, unit_index: int, unit_type: str,
              rooms: Sequence[RoomShape], edges: Sequence[AccessEdge],
              furniture: Sequence[FurnitureRect], facade: Sequence[FacadeSeg],
              entry_point: tuple[int, int], entry_cardinal: Cardinal,
              lobby_room_id: str | None = None, climate_zone: str | None = None,
              code_version: str | None = None) -> "OpeningsContext": ...

# ============================================================ outputs

@dataclass(frozen=True)
class Anchor:
    """Where an opening sits, expressed so it survives a dimension change.
    The GA (rule 11.3) mutates ONLY `t0`/`t1`; everything else is topology."""
    room_id: str
    wall_key: str              # WallSeg.key() of the anchoring room's wall
    t0: float                  # fraction along the wall from `lo`, 0..1
    t1: float

@dataclass(frozen=True)
class DoorCode:
    width_status: FindingStatus
    height_status: FindingStatus
    clause_key: str            # iscodes.CLAUSES key, e.g. "door_width"
    required_mm: int | None    # None when the standard value is UNREAD
    provided_mm: int
    note: str

@dataclass(frozen=True)
class Door:
    id: str
    kind: DoorKind
    role: DoorRole
    unit_id: str
    unit_index: int
    room_a: str                # "" == outside the unit
    room_b: str
    serves_room: str           # "" for through-spaces and the main door
    swing_room: str            # "" for kind "opening"/"panel"/"sliding"
    wall: WallSeg              # oriented so `inward` points into `swing_room`
                               # (into `room_b` for leafless kinds)
    offset_mm: int             # hinge / opening start, measured from wall.lo
    clear_width_mm: int
    height_mm: int
    corner_offset_mm: int      # distance from the nearer perpendicular wall (rule 7.3)
    hinge_at_lo: bool          # True: hinge at the `lo` end; False: at the `hi` end
    slide_to_lo: bool | None   # kind "sliding" only: which way the leaf retracts
    faces: Cardinal | None     # main door only: outward cardinal (rule 3.7)
    anchor: Anchor
    code: DoorCode

@dataclass(frozen=True)
class WindowCode:
    ratio_status: FindingStatus
    clause_key: str
    required_sqm: float | None
    provided_sqm: float
    ratio_used: float
    climate_zone: str | None
    note: str

@dataclass(frozen=True)
class Window:
    id: str
    kind: WindowKind
    unit_id: str
    unit_index: int
    room_id: str
    wall: WallSeg              # oriented so `inward` points into `room_id`
    offset_mm: int             # opening start from wall.lo
    width_mm: int
    sill_mm: int
    head_mm: int
    opens_to: OpensTo
    shaded_by_balcony: bool
    faces: Cardinal
    anchor: Anchor
    code: WindowCode

    @property
    def area_sqm(self) -> float: ...           # width_mm * (head_mm - sill_mm) / 1e6
    @property
    def openable_sqm(self) -> float: ...       # area_sqm * spec.WINDOW_OPENABLE_FRACTION_MIN

@dataclass(frozen=True)
class Violation:
    """HARD. Never merged with a soft term or a code finding."""
    code: str                  # "H01" | "H02" | "H03" | "H09" | "H13" | "H14"
    rule: str                  # rulebook rule number, e.g. "7.5"
    message: str
    room_ids: tuple[str, ...] = ()
    door_ids: tuple[str, ...] = ()

@dataclass(frozen=True)
class CodeFinding:
    """A claim about a published standard. Its `status` may be "unverified",
    which is neither a pass nor a fail and must never be counted as either."""
    key: str                   # "vent_window" | "vent_toilet" | "door_width" | ...
    status: FindingStatus
    clause_key: str            # iscodes.CLAUSES key for citation
    code_version: str
    subject_id: str            # room or door id
    required: float | None
    provided: float
    units: str                 # "sqm" | "mm"
    message: str

@dataclass(frozen=True)
class SightlineHit:
    target: Literal["toilet_door", "bedroom_interior", "kitchen_counter", "dining_table"]
    target_id: str
    ray_angle_deg: float
    point: tuple[int, int]
    distance_mm: int

@dataclass(frozen=True)
class SightlineReport:
    origin: tuple[int, int]
    rays_cast: int
    hits: tuple[SightlineHit, ...]
    exposure: dict[str, float]     # target -> fraction of rays that reached it, 0..1
    penalty: float                 # 0..1, the raw "entry privacy" soft term
    unverified: tuple[str, ...]    # targets that could not be tested (no furniture supplied)

@dataclass(frozen=True)
class OpeningsResult:
    unit_id: str
    doors: tuple[Door, ...]
    windows: tuple[Window, ...]
    hard: tuple[Violation, ...]
    soft: dict[str, float]         # see SOFT_TERMS; each raw 0..1, validate.py weights them
    code_findings: tuple[CodeFinding, ...]
    sightline: SightlineReport
    notes: tuple[str, ...]

# ============================================================ public API

def place_openings(ctx: OpeningsContext) -> OpeningsResult:
    """The one entry point. Runs the schedule, doors, windows, reconcile, re-check."""

def plan_door_schedule(ctx: OpeningsContext) -> tuple[tuple[ScheduledDoor, ...],
                                                      tuple[Violation, ...]]:
    """Rule 7.1 counts and rule 7.2 sizing, before any geometry. If this returns any
    violation, NO geometry is emitted: a plan with two bedroom doors is a topology
    defect and guessing at its geometry would launder it into a drawable plan."""

def place_doors(ctx: OpeningsContext,
                schedule: Sequence["ScheduledDoor"]) -> tuple[tuple[Door, ...],
                                                              tuple[Violation, ...],
                                                              tuple[str, ...]]:
    """Rules 7.3–7.5, 7.7, 7.8. Returns (doors, hard violations, notes)."""

def place_windows(ctx: OpeningsContext,
                  doors: Sequence[Door]) -> tuple[tuple[Window, ...],
                                                  tuple[Violation, ...],
                                                  tuple[CodeFinding, ...],
                                                  tuple[str, ...]]:
    """Rules 8.1–8.5. Takes the doors so a window is never born under a leaf (7.6)."""

def reconcile_door_window(doors: Sequence[Door], windows: Sequence[Window],
                          ctx: OpeningsContext) -> tuple[tuple[Door, ...],
                                                         tuple[Window, ...],
                                                         tuple[str, ...]]:
    """Rule 7.6 repair pass. May flip a door's handedness or slide a window along its
    wall. Never moves a door to a different wall — that would be a topology change."""

def entry_sightline(ctx: OpeningsContext, doors: Sequence[Door],
                    windows: Sequence[Window]) -> SightlineReport:
    """Rule 3.5. Soft only — rulebook test T10 says soft penalty, not reject."""

def check_doors(ctx: OpeningsContext, doors: Sequence[Door],
                windows: Sequence[Window]) -> tuple[tuple[Violation, ...],
                                                    dict[str, float],
                                                    tuple[CodeFinding, ...]]:
    """Re-check every door rule geometrically on the emitted result. Called by
    place_openings AND independently by validate.py on a stored or hand-edited plan,
    where nothing was enforced by construction."""

def check_windows(ctx: OpeningsContext, windows: Sequence[Window],
                  doors: Sequence[Door]) -> tuple[tuple[Violation, ...],
                                                  dict[str, float],
                                                  tuple[CodeFinding, ...]]: ...

def landlocked_rooms(ctx: OpeningsContext) -> tuple[str, ...]:
    """Habitable rooms with neither facade nor shaft. Rule 8.1 / H03."""

# --- geometry helpers, public because validate.py and the tests need them ---

def room_walls(room: RoomShape) -> tuple[WallSeg, ...]:
    """Boundary of a rectangle or L, as inward-oriented segments."""

def shared_walls(a: RoomShape, b: RoomShape) -> tuple[tuple[WallSeg, WallSeg], ...]:
    """Every co-linear, opposite-facing overlap between two rooms. Each pair is
    (segment as seen from a, segment as seen from b), already clipped to the overlap."""

def swing_sector(d: Door) -> tuple[tuple[int, int], ...]:
    """The 90 degree swept leaf, as a convex polygon that CIRCUMSCRIBES the true
    sector, so a clash is never under-reported. Empty for leafless kinds."""

def polygons_overlap(p: Sequence[tuple[int, int]],
                     q: Sequence[tuple[int, int]], slack_mm: int = 0) -> bool:
    """Separating-axis test on two convex polygons. No third-party dependency."""

def door_points(d: Door) -> dict[str, Any]:
    """Everything the SVG needs, still in mm. Keys exactly as in door_payload below."""

# --- GA hooks (rule 11.3: dimensions and door offsets only) ---

OffsetBounds = tuple[int, int]
def offset_bounds(d: Door, ctx: OpeningsContext) -> OffsetBounds:
    """Legal range for `offset_mm` on this door's wall, honouring 7.3 and the jamb piers."""

def with_offset(d: Door, offset_mm: int, ctx: OpeningsContext) -> Door:
    """A copy at a new offset, with corner_offset_mm and anchor recomputed."""

def reanchor(d: Door | Window, rooms: Mapping[str, RoomShape]) -> Door | Window:
    """Recompute absolute geometry from `anchor` after geometry.py resized a room."""

# ============================================================ serialisation

OPENINGS_PAYLOAD_VERSION = 1
PAYLOAD_DP = 3                 # 1 mm. Rooms MUST also serialise at 3 dp (see risks).

def door_payload(d: Door) -> dict:
    """Metres, 3 dp. Exact shape rendered by frontend/src/components/FloorPlate.jsx:

    {
      "id": "unit-1-d03",
      "kind": "swing",                       # swing | sliding | opening | panel
      "role": "room",                        # main|room|ensuite|utility|balcony|service|through|panel
      "unit_id": "unit-1", "unit_index": 0,
      "room_a": "unit-1-passage",            # "" == outside the unit
      "room_b": "unit-1-bed1",
      "serves_room": "unit-1-bed1",          # "" for through-spaces and the main door
      "swing_room": "unit-1-bed1",           # "" when there is no leaf
      "wall": {"axis": "v", "fixed": 12.400, "lo": 5.000, "hi": 8.200, "cardinal": "E"},
      "opening_start": {"x": 12.400, "y": 5.150},   # the wall gap, hinge end first
      "opening_end":   {"x": 12.400, "y": 6.050},
      "hinge":         {"x": 12.400, "y": 5.150},   # null for opening/panel/sliding
      "leaf_closed":   {"x": 12.400, "y": 6.050},   # == opening_end for a swing leaf
      "leaf_open":     {"x": 13.300, "y": 5.150},   # null when there is no leaf
      "arc_radius": 0.900,                          # metres; scale by the same px/m as rooms
      "arc_sweep": 1,                               # SVG sweep-flag, large-arc-flag is always 0
      "hand": "right",                              # left | right | null
      "swing_normal": {"x": 1, "y": 0},             # unit vector into swing_room
      "slide_to": {"x": 12.400, "y": 5.150},        # sliding only, else null
      "clear_width_mm": 900, "height_mm": 2100, "sill_mm": 0,
      "leaf_thickness_mm": 40, "corner_offset_mm": 150,
      "faces": null,                                # "N"|"E"|"S"|"W" on the main door only
      "anchor": {"room_id": "unit-1-bed1", "edge": "v|12400|5000|8200",
                 "t0": 0.0469, "t1": 0.3281},
      "code": {"width_status": "unverified", "height_status": "unverified",
               "clause": "door_width", "code_version": "nbc2016",
               "required_mm": null, "provided_mm": 900,
               "note": "Sized from the rulebook practice table (7.2, marked [verify]). "
                       "NBC Part 3 residential door widths have not been read into "
                       "iscodes, so this is not a compliance pass."}
    }

    SVG, given `X(v)=(v-minX)*scale+padding` and `Y(v)=(v-minY)*scale+padding`:
      wall gap : line opening_start -> opening_end, stroke = paper colour, width 3
      leaf     : line hinge -> leaf_open, stroke #1E293B, width 1.5
      arc      : path "M X(leaf_open) Y(leaf_open) A r r 0 0 {arc_sweep}
                       X(leaf_closed) Y(leaf_closed)", r = arc_radius*scale, dashed
    """

def window_payload(w: Window) -> dict:
    """Metres, 3 dp:

    {
      "id": "unit-1-w02",
      "kind": "window",                      # window | french | ventilator | louvre
      "unit_id": "unit-1", "unit_index": 0,
      "room_id": "unit-1-bed1",
      "wall": {"axis": "h", "fixed": 4.200, "lo": 10.100, "hi": 13.400, "cardinal": "N"},
      "p1": {"x": 11.150, "y": 4.200},
      "p2": {"x": 12.650, "y": 4.200},
      "outward": {"x": 0, "y": -1},          # points away from room_id, toward the air
      "opens_to": "air",                     # air | shaft | balcony
      "shaded_by_balcony": false,
      "faces": "N",
      "width_mm": 1500, "sill_mm": 900, "head_mm": 2100,
      "area_sqm": 1.800, "openable_sqm": 0.900,
      "anchor": {"room_id": "unit-1-bed1", "edge": "h|4200|10100|13400",
                 "t0": 0.3182, "t1": 0.7727},
      "code": {"ratio_status": "unverified", "clause": "vent_window",
               "code_version": "nbc2016", "required_sqm": 1.400, "provided_sqm": 1.800,
               "ratio_used": 0.1, "climate_zone": "composite",
               "note": "Sized to the rulebook 8.2 ratio, marked [verify]. NBC Part 8 "
                       "has not been read into iscodes, so this is not a pass."}
    }

    SVG: line p1 -> p2, stroke #38BDF8, width 3.5, over a paper-coloured wall break.
    """

def openings_payload(results: Sequence[OpeningsResult]) -> dict:
    """{"doors": [...], "windows": [...], "openings_version": 1}"""

def attach_openings(entry: dict, results: Sequence[OpeningsResult]) -> dict:
    """Merge into a tower.floor_layouts[floor] entry IN PLACE and return it.
    Adds only the three sibling keys; `rooms`, `validation`, `seed`, `unit_mix_hash`,
    `generated_at`, `ai_generated` are untouched."""

def has_openings(entry: Mapping[str, Any]) -> bool:
    """True when a stored entry carries real openings. Every reader — backend and
    frontend — uses `entry.get("doors") or []`, so a plan stored before this module
    existed loads as zero doors and zero windows rather than raising."""
```

## Constants
GOVERNING PRINCIPLE, stated because it decides where every number below lives.
A number used to GENERATE geometry must always produce a value or nothing can be drawn;
a number used to ASSERT compliance must refuse when nobody read it. These are the same
physical quantity with opposite failure modes, so they are two entries, not one:
  - generation values -> plain constants in backend/floorplan/spec.py, each paired with a
    `*_VERIFIED = False` flag, following the existing iscodes.WIND_CF_VERIFIED precedent.
  - compliance values -> versioned dicts in backend/iscodes.py, UNREAD where unread,
    following the existing _FIRE_NBC_2016 / _FIRE_SP7_2026 / fire_table() pattern.
openings.py declares NO numeric literal of its own except the four tolerances at the end.
It imports the rest by name from spec.py; a missing name is an ImportError at load, which
is the correct loud failure and far better than a local fallback that silently diverges.

--------------------------------------------------------------------- spec.py, doors
Rulebook 7.2 is marked [verify]. These are market-practice sizes, NOT code minima, and
must never be reported as code:
DOOR_SIZES_MM = {
    "main":    {"clear_w": 1000, "clear_h": 2100},   # rulebook 3.6 / 7.2  [verify]
    "bedroom": {"clear_w":  900, "clear_h": 2100},   # [verify]
    "kitchen": {"clear_w":  900, "clear_h": 2100},   # [verify]
    "toilet":  {"clear_w":  750, "clear_h": 2000},   # [verify]
    "utility": {"clear_w":  750, "clear_h": 2100},   # [verify]
    "balcony": {"clear_w":  900, "clear_h": 2100},   # [verify]
    "pooja":   {"clear_w":  750, "clear_h": 2100},   # not in the rulebook; house default
    "study":   {"clear_w":  900, "clear_h": 2100},
    "servant": {"clear_w":  750, "clear_h": 2000},
    "shaft":   {"clear_w":  600, "clear_h": 1200},   # maintenance panel, rule 9.4
}
DOOR_SIZES_VERIFIED = False        # 7.2 carries [verify]; surfaced in every DoorCode note
CASED_OPENING_MIN_MM  = 1200
CASED_OPENING_PREF_MM = 1800
CASED_OPENING_MAX_MM  = 2400
DOOR_LEAF_THICKNESS_MM = 40        # drawing/3D only, not a rule

--------------------------------------------------------------------- spec.py, placement
CORNER_OFFSET_MIN_MM  = 100        # rule 7.3, exact
CORNER_OFFSET_MAX_MM  = 300        # rule 7.3, exact
CORNER_OFFSET_PREF_MM = 150        # house preference inside the rulebook band
CORNER_OFFSET_CANDIDATES_MM = (150, 100, 200, 250, 300)   # preference order
JAMB_MIN_MM           = 100        # pier a jamb needs; not in the rulebook, house value
OPENING_GAP_MIN_MM    = 150        # pier between two openings on one wall; house value
FACING_OFFSET_MIN_MM  = 300        # rule 7.8, exact
FACING_ALIGN_TOL_MM   =  25        # how exact "aligned exactly" is; house value
TOILET_INWARD_SWING_MIN_SQM = 1.5  # rule 7.4, exact: below this the leaf goes out or slides
SLIDING_POCKET_FACTOR = 2.0        # a pocket needs 2x leaf width of clear wall; house value
BALCONY_SLIDING_DEFAULT = True     # balcony leaves slide, which deletes a whole class of
                                   # 7.5 clashes in the living room; house decision
LEAF_WINDOW_CLEAR_MM  = 100        # rule 7.6 clearance from an open leaf to a window

--------------------------------------------------------------------- spec.py, sightline
SIGHTLINE_EYE_OFFSET_MM = 300      # observer stands this far inside the open main door
SIGHTLINE_RAY_COUNT     =  61      # 3 degree spacing over the 180 degree door half-plane
SIGHTLINE_SPAN_DEG      = 180.0
SIGHTLINE_MAX_MM        = 12000    # no ray inside a flat usefully travels further
SIGHTLINE_TARGET_WEIGHT = {"toilet_door": 1.0, "bedroom_interior": 1.0,
                           "kitchen_counter": 0.6, "dining_table": 0.4}
All five are house values. Rule 3.5 names the targets but no geometry; the rulebook's own
test T10 grades a visible toilet as a SOFT penalty, so nothing here can reject.

--------------------------------------------------------------------- spec.py, windows
WINDOW_AREA_RATIO_DEFAULT     = 1.0 / 10.0   # rule 8.2  [verify]
WINDOW_AREA_RATIO_WARM_HUMID  = 1.0 /  6.0   # rule 8.2  [verify]
WINDOW_OPENABLE_FRACTION_MIN  = 0.5          # rule 8.2  [verify]
WINDOW_RATIO_VERIFIED = False
TOILET_VENT_MIN_SQM   = 0.30                 # rule 8.3  [verify]
TOILET_VENT_VERIFIED  = False
SILL_HABITABLE_MM = 900
SILL_KITCHEN_MM   = 1200        # clears a 900 counter with a 300 splashback
SILL_TOILET_MM    = 1500
SILL_FRENCH_MM    = 0
HEAD_HABITABLE_MM = 2100        # matches the door head; rule 8.4 keys off it
HEAD_TOILET_MM    = 2100
WINDOW_JAMB_MIN_MM  = 300       # pier each side of a window; house value
WINDOW_MIN_WIDTH_MM = 600
WINDOW_MAX_WIDTH_MM = 3000
MAX_WINDOWS_PER_ROOM = 3
DAYLIGHT_DEPTH_FACTOR      = 2.5    # rule 8.4, exact -> 5250 depth cap at a 2100 head
FACADE_MIN_PER_HABITABLE_MM  = 2500 # rule 8.5, exact
FACADE_PREF_PER_HABITABLE_MM = 3000 # rule 8.5, exact
CLIMATE_ZONES = ("hot_dry", "warm_humid", "composite", "temperate", "cold")
WARM_HUMID_ZONES = frozenset({"warm_humid"})
CARDINAL_GLAZING_PENALTY = {"N": 0.00, "NE": 0.05, "E": 0.10, "SE": 0.25,
                            "S": 0.30, "SW": 0.55, "W": 0.60, "NW": 0.35}
The glazing-cardinal table is a soft Indian-context preference of the same character as
vastu.py's sector anchors. Weight it low; it must never move a window off the wall that
rule 8.2 needs.

--------------------------------------------------------------------- iscodes.py additions
These are the entries that must be able to REFUSE. All follow fire_table() exactly.

_DOOR_NBC_2016 = {
    "accessible_min_clear_w_mm": ACCESS["door_width_mm"],   # 900 — genuinely read,
                                                            # NBC 2016 Part 3 Cl. 13.5
    "main_min_clear_w_mm":      UNREAD,
    "habitable_min_clear_w_mm": UNREAD,
    "toilet_min_clear_w_mm":    UNREAD,
    "min_clear_height_mm":      UNREAD,
}
_DOOR_SP7_2026 = {k: UNREAD for k in _DOOR_NBC_2016}
DOOR_BY_VERSION = {NBC_2016: _DOOR_NBC_2016, SP7_2026: _DOOR_SP7_2026}
def door_table(version=None): return DOOR_BY_VERSION[code_version(version)]

_VENT_NBC_2016 = {
    "window_area_ratio":             UNREAD,
    "window_area_ratio_warm_humid":  UNREAD,
    "openable_fraction_min":         UNREAD,
    "toilet_vent_min_sqm":           UNREAD,
    "habitable_shaft_min_area_sqm":  UNREAD,
}
_VENT_SP7_2026 = {k: UNREAD for k in _VENT_NBC_2016}
VENT_BY_VERSION = {NBC_2016: _VENT_NBC_2016, SP7_2026: _VENT_SP7_2026}
def vent_table(version=None): return VENT_BY_VERSION[code_version(version)]

Every NBC 2016 entry above is UNREAD on purpose except the one that already exists in
ACCESS. NBC Part 8's light-and-ventilation clause and Part 3's residential door schedule
have not been read into this repository. Writing 1/10 into iscodes on the strength of the
rulebook would manufacture a compliance pass carrying the authority of a clause nobody
opened — the one outcome this codebase treats as worse than refusing. Generation is
unaffected because it reads spec.py; only the CLAIM refuses. When someone reads the
clauses, they fill these five values and every finding flips from "unverified" to a real
pass or fail with no change to the generator.

New CLAUSES entries (for citation and deep-linking, same shape as the existing ones):
"vent_window": {"code": "NBC 2016 Part 8", "clause": "Cl. 4.2",
                "topic": "Window area >= 1/10 of floor area, at least half openable"}
"vent_toilet": {"code": "NBC 2016 Part 8", "clause": "Cl. 4.2.3",
                "topic": "Toilet ventilation opening >= 0.3 m2 or mechanical extract"}
"door_width":  {"code": "NBC 2016 Part 3", "clause": "Cl. 13.5",
                "topic": "Minimum clear door width"}
"vent_shaft":  {"code": "NBC 2016 Part 8", "clause": "Cl. 4.3",
                "topic": "Minimum ventilation shaft area serving habitable rooms"}

--------------------------------------------------------------------- openings.py local
Only four, all pure implementation tolerances with no rulebook meaning:
EPS_MM = 1                  # mm; below this two coordinates are the same point
ARC_SAMPLES = 12            # chords per 90 degree sector
ARC_SAFETY_MM = 5           # sector polygon is inflated by this so a clash is never missed
MAX_GROUP_COMBOS = 20000    # exhaustive search cap per swing-room group; deterministic
FACING_REPAIR_PASSES = 3    # rule 7.8 cross-corridor repair iterations
OPENINGS_PAYLOAD_VERSION = 1
PAYLOAD_DP = 3

## Algorithm
======================================================================
PHASE 0 — SCHEDULE (rule 7.1, 7.2). plan_door_schedule()
======================================================================
1. Index rooms by id. Build door_budget[room_id] = count of edges whose `serves` is that
   room. `serves` is the room whose ONE-DOOR budget the opening consumes, and it is
   never the parent: a bedroom's en-suite door is charged to the toilet, a balcony door
   to the balcony. Without this distinction, every master bedroom in the codebase reads
   as a 3-door hard reject and rule 7.1 becomes unusable.
2. For every room whose type is NOT in THROUGH_SPACE_TYPES:
     budget != 1  ->  Violation. Code H14 when the room type is "bedroom" (the rulebook
     names bedrooms explicitly), otherwise H14 with the room type in the message.
     budget == 0 for a room that is not a shaft -> H08-adjacent, but H08 belongs to
     circulation.py; emit H14 with message "no door scheduled" and let validate rank it.
3. Count edges with role == "main". != 1 -> H01. Its `b` room type must be in
   FOYER_TYPES -> else H02. This is checked here, before geometry, because a main door
   into a living room is not a placement problem that a better hinge could fix.
4. Reject a toilet edge whose other end is a kitchen or dining room -> H13 (rule 6.4).
5. Size each scheduled door from spec.DOOR_SIZES_MM via role and the served room's type:
     main -> "main"; served type in WET_TYPES -> "toilet"; "bedroom"/"kitchen"/"study"/
     "pooja"/"servant" -> their own key; role utility|service -> "utility";
     role balcony -> "balcony"; role panel -> "shaft"; anything else -> "bedroom".
     role "through" -> a CASED OPENING with no leaf; width is decided at placement time
     as clamp(wall_len - 2*JAMB_MIN_MM, CASED_OPENING_MIN_MM, CASED_OPENING_MAX_MM),
     preferring CASED_OPENING_PREF_MM. This is what makes rule 7.5 satisfiable at all:
     living/dining/foyer/corridor are through-spaces, so they are joined by leafless
     openings and contribute no arcs.
6. Choose kind: "opening" for role through; "panel" for role panel; "sliding" for role
   balcony when BALCONY_SLIDING_DEFAULT; "sliding" or outward "swing" for a toilet whose
   clear floor area < TOILET_INWARD_SWING_MIN_SQM (rule 7.4 exception, decided in
   phase 2); "swing" otherwise.
7. Assign ids deterministically: sort the schedule by
   (ROLE_RANK[role], serves, room_a, room_b) with ROLE_RANK = main 0, through 1, room 2,
   ensuite 3, utility 4, balcony 5, service 6, panel 7, then id = f"{unit_id}-d{n:02d}".
   The sort key is pure topology, so ids survive every GA mutation.
8. If any violation was raised, return (schedule=(), violations). Emit no geometry.

======================================================================
PHASE 1 — CANDIDATE WALLS AND OFFSETS (rules 7.3, 7.4, 7.7)
======================================================================
For each scheduled door:
1. Candidate segments = shared_walls(room_a, room_b), each clipped to the co-linear
   opposite-facing overlap. For the main door, room_a is outside the unit: candidates are
   the foyer's wall segments that lie on the entry facade, ranked by distance from
   ctx.entry_point. If there are no candidates at all, emit a Violation (rule 6 adjacency
   was satisfied by area, not by a shared wall) and stop for this door.
2. Fix the swing side (rule 7.4). The leaf swings into the room served, never into a
   corridor. Orient the WallSeg so `inward` points into that room; that room becomes
   `swing_room`. Exceptions, in order:
     a. served room is a toilet with clear floor area < TOILET_INWARD_SWING_MIN_SQM:
        try kind "swing" with the normal reversed (outward, into the parent room);
        if that arc fails phase 2, fall back to kind "sliding".
     b. sliding needs a pocket: SLIDING_POCKET_FACTOR * clear_width of uninterrupted
        wall on the toilet side of the opening, free of other openings and of fixed
        furniture. If neither inward, nor outward, nor sliding works, the toilet is too
        small to have a door — report it as a rule 5.2 geometry failure with a note that
        names the room, NOT as a door failure. Blaming the door here would send the GA
        chasing hinge offsets for a room that can never take a leaf.
     c. never orient a leaf so that swing_room's type is in CORRIDOR_TYPES.
3. Candidate offsets on a segment of length L, for a clear width W:
     - Determine which of the two segment ends is an ANCHORABLE CORNER: the end
       coincides (within EPS_MM) with a convex corner of the swing room, i.e. there is a
       real perpendicular wall there for the open leaf to lie against. The end of a
       shared overlap that is merely where the neighbour stops is not a corner.
     - For each anchorable end e and each d in CORNER_OFFSET_CANDIDATES_MM:
         hinge at distance d from e, closed leaf running from the hinge toward the
         segment interior, open leaf swinging back toward e so it finishes parallel to
         and d away from that perpendicular wall. This is what rule 7.3 means by
         "opens flat against the wall".
       Require d + W + JAMB_MIN_MM <= L when the far end is also a corner, else
       d + W <= L.
     - If NEITHER end is anchorable (a segment floating in the middle of a longer wall),
       fall back to centring the opening on the segment and record the soft penalty rule
       7.3 calls a soft reject for a centred door.
   For cased openings, sliding leaves and panels the corner rule does not apply; centre
   on the segment, clamped to WINDOW/JAMB piers.
4. Independent hard filters, applied per candidate before any cross-door work:
     F5  the opening plus its piers fits the segment.
     F1b the swept sector lies inside swing_room's polygon, inflated by EPS_MM. A 900
         leaf inside a 1200 deep room hits the far wall; that is a real defect, not a
         near miss.
     F2  the swept sector does not overlap any FurnitureRect in swing_room with
         fixed=True. Overlap with fixed=False furniture is a soft penalty, not a filter.
         If ctx.furniture contains NO entry for a room type that rule 5.3 requires a
         packing test for, RAISE FurnitureMissing rather than passing the door. Silently
         skipping the check that the rulebook calls "the rule most often broken" would
         reproduce exactly the failure this rewrite exists to fix.
5. Keep at most 12 surviving candidates per door, ordered by the phase-4 soft cost, so
   the phase-3 product stays bounded.

======================================================================
PHASE 2 — CLASH RESOLUTION (rule 7.5 / H09)
======================================================================
Key structural observation that makes this cheap and exactly right: a leaf sweeps into
exactly ONE room, so two leaves can collide only if they swing into the SAME room. Doors
on opposite sides of a wall cannot clash however close they are.
1. Group doors by swing_room (leafless kinds are in no group).
2. Within a group, exhaustively evaluate the product of candidate lists, capped at
   MAX_GROUP_COMBOS; if the cap would be exceeded, truncate each door's candidate list
   evenly from the tail (worst cost first) until the product fits, and add a note saying
   the search was truncated. Reject any combination in which two sectors overlap
   (polygons_overlap with slack ARC_SAFETY_MM). Choose the minimum-total-soft-cost
   surviving combination; ties break on (hinge.x, hinge.y, wall.key()) so the result is
   deterministic and reproducible without an RNG.
3. If a group has no clash-free combination, emit Violation H09 naming every door in the
   group, and keep the least-bad combination so the plan is still drawable and the defect
   is visible. Do not silently drop a door.
4. SAME-WALL PIER RULE (F1c), applied across groups: any two openings whose spans lie on
   the same axis and the same `fixed` coordinate must be separated by at least
   OPENING_GAP_MIN_MM of pier. Two 900 leaves 600 apart on one corridor wall fail here.
   Report it as H09 citing rule 7.5 — it is the same physical defect as an arc clash, and
   the rulebook's test T06 expects H09.
5. Swept sector construction, exactly: centre = hinge; radius r = clear_width_mm;
   start angle = atan2 of (leaf_closed - hinge); end angle = start +/- 90 degrees in the
   direction of swing_normal. Sample ARC_SAMPLES + 1 points at radius
   r / cos(pi/(4*ARC_SAMPLES)) + ARC_SAFETY_MM, so the polygon CIRCUMSCRIBES the true
   sector and a clash is never under-reported. Prepend the hinge. The result is convex,
   so polygons_overlap is a plain separating-axis test over both polygons' edge normals.

======================================================================
PHASE 3 — FACING LEAVES (rule 7.8)
======================================================================
For each corridor room (type in CORRIDOR_TYPES), collect the doors whose opening lies on
one of its two long opposite walls. Project each opening span onto the corridor axis.
For every cross-wall pair, require either
   disjoint by >= FACING_OFFSET_MIN_MM, or
   aligned: |start_a - start_b| <= FACING_ALIGN_TOL_MM and equal widths.
Partial overlap is a collision zone. Repair by re-picking from the alternates of whichever
door of the pair has the cheaper next candidate, re-running phase 2 for that door's swing
group, up to FACING_REPAIR_PASSES. If still unresolved, keep the geometry and record a
SOFT penalty. This rule is enforced by construction but scored on re-check, never
hard-rejected: it is not in H01-H15, and hard-rejecting a stored or hand-edited plan on a
rule the rulebook did not list would be inventing a hard constraint.

======================================================================
PHASE 4 — DOOR SOFT COST (the 0.08 "Door placement quality" term)
======================================================================
Per door, each sub-term normalised to 0..1, combined by the weights shown, then averaged
over all doors in the unit to give soft["door_placement"]:
  0.35  corner_offset: 0 when CORNER_OFFSET_MIN_MM <= corner_offset_mm <=
        CORNER_OFFSET_MAX_MM; ramps to 1 as the opening approaches the wall midpoint
        (rule 7.3's soft reject for a centred door).
  0.30  longest_wall: after cutting every door and window opening out of the served
        room's walls, take the longest uninterrupted run F. Penalty =
        clamp((F_best - F) / F_best, 0, 1) where F_best is the longest run achievable
        over all of that door's surviving candidates. Directly encodes rule 7.7.
  0.15  facing: 1 when a rule 7.8 pair is still partially overlapping, else 0.
  0.10  short_side: 0 when the door sits on the wall end nearer the room's SHORT side
        (rule 7.7's stated preference), 1 otherwise.
  0.10  movable_clash: fraction of the sector's area overlapping fixed=False furniture.

======================================================================
PHASE 5 — WINDOWS (rules 8.1 to 8.5)
======================================================================
For each room, in order living, bedrooms by area descending, dining, kitchen, study,
toilets, utility:
1. Collect the room's wall segments that overlap a FacadeSeg. Classify each overlap:
     opens_to "air"     -> counts fully for 8.1 and 8.2
     opens_to "balcony" -> counts, but shaded_by_balcony=True and the room's 8.2 finding
                           is forced to "unverified" (NBC's balcony-shading deduction has
                           not been read)
     opens_to "shaft"   -> satisfies 8.1's "code-compliant ventilation shaft" only when
                           services.py supplied shaft_clear_sqm; because
                           iscodes.vent_table()["habitable_shaft_min_area_sqm"] is UNREAD,
                           a habitable room lit only from a shaft yields a CodeFinding of
                           status "unverified", never "pass"
     opens_to "party"/"corridor" -> not an opening surface; ignored
2. If the room is habitable and the total of air + shaft + balcony overlap is zero ->
   Violation H03, rule 8.1. This is the ONLY hard reject in section 8.
3. Required area. ratio = WINDOW_AREA_RATIO_WARM_HUMID when
   ctx.climate_zone in WARM_HUMID_ZONES, WINDOW_AREA_RATIO_DEFAULT when the zone is a
   known non-humid zone, and WINDOW_AREA_RATIO_WARM_HUMID when the zone is None. An
   unknown zone takes the STRICTER ratio because over-glazing is the safe direction for
   daylight, and the finding is marked "unverified" with a note naming the missing zone.
   required_sqm = room.area_sqm * ratio; openable target = required_sqm *
   WINDOW_OPENABLE_FRACTION_MIN.
4. Sill and head by room type: toilets SILL_TOILET_MM / HEAD_TOILET_MM; kitchen
   SILL_KITCHEN_MM / HEAD_HABITABLE_MM; a room with a balcony door on that wall gets
   kind "french" with SILL_FRENCH_MM; everything else SILL_HABITABLE_MM /
   HEAD_HABITABLE_MM. Vision height h = head - sill; required width = ceil(
   required_sqm * 1e6 / h).
5. Segment choice. Rank candidate facade overlaps by
   (daylight_ok desc, length desc, CARDINAL_GLAZING_PENALTY[cardinal] asc, lo asc), where
   daylight_ok is rule 8.4: the room's perpendicular depth from that wall <=
   DAYLIGHT_DEPTH_FACTOR * head. A wall that fails 8.4 is still usable, it just sorts
   last and contributes to the soft term.
6. Position on the chosen segment: centre the opening, then
     a. clamp so both jambs keep WINDOW_JAMB_MIN_MM of pier;
     b. slide to keep OPENING_GAP_MIN_MM of pier from every door opening on that wall;
     c. slide out from under any open leaf (rule 7.6): the window span must not lie
        within LEAF_WINDOW_CLEAR_MM of the open-leaf segment's projection onto the wall.
        If the wall cannot accommodate both, mark the window for the reconcile pass;
     d. clamp width to [WINDOW_MIN_WIDTH_MM, WINDOW_MAX_WIDTH_MM].
   If one segment cannot carry the required area, take the next-ranked segment and add
   another window, up to MAX_WINDOWS_PER_ROOM.
7. Toilets: one ventilator of width ceil(TOILET_VENT_MIN_SQM * 1e6 / (HEAD_TOILET_MM -
   SILL_TOILET_MM)) = 500 mm at the stated sill/head. If the toilet has no facade and no
   shaft, emit no window and a CodeFinding "vent_toilet" with status "unverified" and a
   note that rule 8.3's mechanical-extract alternative is a services.py decision this
   module cannot see. Never emit a fabricated window into a party wall.
8. Aggregate check per room. provided = sum of window area on that room. Shortfall is
   NOT a hard reject (8.2 is absent from H01-H15); it becomes a CodeFinding with
   status "fail" only if iscodes.vent_table() carries a read ratio, and "unverified"
   otherwise, plus a contribution to the soft facade term. Rule 8.5's
   FACADE_MIN_PER_HABITABLE_MM feeds soft["facade_utilisation"] =
   fraction of habitable rooms with facade run < FACADE_PREF_PER_HABITABLE_MM, with a
   double weight on those below FACADE_MIN_PER_HABITABLE_MM.

======================================================================
PHASE 6 — RECONCILE (rule 7.6). reconcile_door_window()
======================================================================
The mandatory generation order puts doors at step 8 and windows at step 9, but rule 7.6
constrains the pair. Rather than reorder the rulebook's sequence, run one bounded repair:
for every (door, window) pair flagged in phase 5c, try in this order
   1. slide the window to the far side of the wall, if the piers allow;
   2. flip the door's handedness (hinge from the `lo` end to the `hi` end, same wall,
      same width), then re-run phase 2 for that door's swing group;
   3. accept the conflict and emit a soft penalty plus a note.
Never move a door to a different wall here: the wall is a topology decision made in
phase 1 from the access graph, and changing it silently would break rule 11.3's promise
that the search only touches dimensions and offsets.

======================================================================
PHASE 7 — ENTRY SIGHTLINE (rule 3.5). entry_sightline()
======================================================================
1. Origin = midpoint of the main door's clear opening, pushed SIGHTLINE_EYE_OFFSET_MM
   along the door's inward normal. Standing exactly in the wall plane produces degenerate
   rays that run along the wall.
2. Cast SIGHTLINE_RAY_COUNT rays evenly over SIGHTLINE_SPAN_DEG centred on the inward
   normal, each of length SIGHTLINE_MAX_MM.
3. The test is run with every internal door OPEN. That is the worst case the rule guards
   against — a visitor at the door while someone comes out of a bedroom — and it makes
   the model coherent: a door opening is an APERTURE (rays pass), the open LEAF is an
   opaque blocker (rays stop), a cased opening is an aperture with no leaf.
4. Blockers = every wall segment of every room in the unit, minus the span of every door
   and window opening, plus one segment per open leaf (hinge -> leaf_open).
5. Targets:
     toilet_door      -> the opening span segment of any door whose serves_room type is
                         in WET_TYPES. Seeing the DOOR is the violation, per 3.5's wording.
     bedroom_interior -> the polygon of any room of type "bedroom".
     kitchen_counter  -> the FurnitureRect with role "counter" in the kitchen.
     dining_table     -> the FurnitureRect with role "dining_table".
   When ctx.furniture supplies no counter or no table, that target goes into
   SightlineReport.unverified. It does NOT silently pass: a privacy report that says
   "clear" because it had nothing to look for is the fabricated result this codebase
   treats as the worst outcome.
6. Per ray: intersect against blockers and target edges, sort hits by t ascending, walk
   from the nearest. The first hit that is a target and is not preceded by a blocker is
   recorded as a SightlineHit. Apertures are not hits and do not stop the walk.
7. exposure[target] = hitting_rays / rays_cast. penalty =
   sum(SIGHTLINE_TARGET_WEIGHT[t] * exposure[t]) / sum(SIGHTLINE_TARGET_WEIGHT.values()),
   clamped to 0..1, written to soft["entry_privacy"]. Never a Violation — rulebook test
   T10 grades this soft.

======================================================================
PHASE 8 — RE-CHECK. check_doors() / check_windows()
======================================================================
Every rule enforced by construction above is re-verified here from the emitted geometry
alone, with no memory of the placement decisions. validate.py calls these two functions
directly on stored, AI-generated and hand-edited plans, where nothing was enforced by
construction at all. The hard codes this module can raise are exactly:
   H01 count of role=="main" doors per unit != 1
   H02 the main door's swing_room type is not in FOYER_TYPES
   H03 a habitable room with no facade and no shaft overlap
   H09 two swept sectors in one room overlap, OR two openings share a wall with less
       than OPENING_GAP_MIN_MM of pier, OR a sector leaves its swing room
   H13 a door with a WET_TYPES end and a kitchen or dining end
   H14 a non-through-space room whose serves-budget is not exactly 1
Everything else this module produces is either a soft term or a CodeFinding. The three
lists are returned separately by every function and are never concatenated.

======================================================================
PHASE 9 — SERIALISATION
======================================================================
door_payload / window_payload convert mm ints to metres rounded to PAYLOAD_DP = 3 and
compute the drawing fields:
  swing_normal = wall.inward (into swing_room)
  hinge        = wall.point_at(offset_mm) when hinge_at_lo else
                 wall.point_at(offset_mm + clear_width_mm)
  leaf_closed  = the other jamb
  leaf_open    = hinge + swing_normal * clear_width_mm
  arc_radius   = clear_width_mm / 1000
  arc_sweep    = 1 if cross(leaf_open - hinge, leaf_closed - hinge) > 0 else 0,
                 where cross(u, v) = u.x*v.y - u.y*v.x. In this y-down frame a positive
                 cross is clockwise on screen, which is exactly SVG's sweep-flag 1, so
                 the renderer substitutes the value with no further reasoning.
  hand         = "right" if cross(swing_normal, unit(leaf_closed - hinge)) > 0 else "left"
  WORKED EXAMPLE, to be pinned by a unit test: a vertical wall at x=12.400 running
  y 5.000 -> 8.200 with the room to its EAST; hinge (12.400, 5.150), leaf_closed
  (12.400, 6.050), swing_normal (1, 0), leaf_open (13.300, 5.150). Then
  cross(leaf_open-hinge, leaf_closed-hinge) = cross((0.9,0),(0,0.9)) = 0.81 > 0 ->
  arc_sweep = 1; cross(swing_normal, (0,1)) = 1 > 0 -> hand = "right", which is what an
  observer standing east of the wall facing the door sees (hinge on their right).
attach_openings(entry, results) sets entry["doors"], entry["windows"] and
entry["openings_version"] and touches nothing else.

======================================================================
PAYLOAD COMPATIBILITY AND THE RENDERER
======================================================================
tower["floor_layouts"][str(floor)] gains three SIBLING keys next to the existing rooms /
validation / seed / unit_mix_hash / generated_at / ai_generated. Nothing existing changes
shape, so every stored plan keeps loading. Every reader uses
  doors  = entry.get("doors")  or []
  windows= entry.get("windows") or []
so a plan written before this module existed loads as zero openings rather than raising.
server.py mirrors them onto the tower for floor 1 exactly as it already mirrors rooms:
  tower["doors"] = entry["doors"]; tower["windows"] = entry["windows"]
so ThreeDModule.jsx's `tower?.rooms` pattern extends to `tower?.doors || []`.

FloorPlate.jsx changes, precisely:
  - signature becomes ({ rooms = [], doors = [], windows = [], selectedId, onSelect,
    corridor })
  - DELETE the fake window band (the `hasWindow` line and the <line> block that draws a
    cyan stroke across every room's top edge) and DELETE the fake swing arc (the <g
    opacity="0.65"> block that draws an arc in every room's bottom-left corner). They are
    decoration unrelated to any opening and they are what this module exists to replace.
  - add ONE new <g> AFTER the rooms map, so openings paint over the room strokes:
      for each window: a paper-coloured line p1->p2 at strokeWidth 3 to break the wall,
        then a #38BDF8 line p1->p2 at strokeWidth 3.5.
      for each door: a paper-coloured line opening_start->opening_end at strokeWidth 3;
        then if kind === "swing": <line hinge->leaf_open stroke #1E293B width 1.5> and
        <path d={`M ${X(leaf_open)} ${Y(leaf_open)} A ${r} ${r} 0 0 ${arc_sweep}
        ${X(leaf_closed)} ${Y(leaf_closed)}`} fill=none stroke=#64748B strokeDasharray="2
        2"> with r = arc_radius * scale; if kind === "sliding": a line from opening_start
        to slide_to offset 0.06 m along swing_normal; if kind === "opening": the wall
        break alone; if kind === "panel": a dashed rectangle on the opening span.
  - when rooms.length > 0 and doors.length === 0 and windows.length === 0, render a small
    badge reading "openings not generated for this plan - regenerate this floor". An
    honest blank is better than the fake arc it replaces.
  - PlanningModule.jsx reads them off the same entry it already reads rooms from and
    passes them down; its hand-edit path (setRooms) must call reanchor server-side on the
    next save, or mark the entry stale, because moving a room leaves its openings behind.

## hard_rules
- H01 entrance_count != 1 - enforced in plan_door_schedule by counting edges with role=='main' per unit before any geometry is emitted, and re-checked in check_doors from the emitted doors alone. Rulebook rule 3.1 / 7.1, test T01.
- H02 main door opens into a room other than foyer - enforced in plan_door_schedule (the main edge's `b` room type must be in FOYER_TYPES) and re-checked as the emitted main door's swing_room type. Rulebook rule 3.2, test T02.
- H03 any habitable room with no external wall or shaft - detected in place_windows phase 5 step 2 when a habitable room has zero facade overlap of any kind, and exposed independently as landlocked_rooms() so validate.py can raise it without running window placement. Rulebook rule 8.1, test T07.
- H09 any door swing arc collision - enforced by the phase 2 group search (two sectors overlapping inside one swing room), by F1b (a sector leaving its swing room), by F2 (a sector over fixed furniture) and by F1c (two openings sharing a wall with less than OPENING_GAP_MIN_MM of pier), and re-checked geometrically in check_doors via swing_sector + polygons_overlap. Rulebook rule 7.5, test T06.
- H13 toilet door opens into kitchen or dining - rejected in plan_door_schedule on the room-type pair, re-checked on the emitted room_a/room_b pair. Rulebook rule 6.4.
- H14 bedroom with more than one door - enforced by the serves-budget count in plan_door_schedule, which charges an en-suite door to the toilet and a balcony door to the balcony so a normal master bedroom does not read as a three-door reject, and re-checked from the emitted doors. Rulebook rule 7.1.
- Rule 7.3 corner offset 100-300 - enforced by construction (CORNER_OFFSET_CANDIDATES_MM never leaves the band) but scored, not rejected, because the rulebook calls a centred door a SOFT reject and it is absent from H01-H15.
- Rule 7.4 swing side - enforced by construction: the WallSeg is oriented into the room served and a leaf is never oriented into a CORRIDOR_TYPES room. The small-toilet exception below TOILET_INWARD_SWING_MIN_SQM is taken in phase 1 step 2 before any candidate is scored.
- Rule 7.6 leaf must not cover a window - enforced by window placement (phase 5 step 6c) and by the bounded reconcile pass, then scored. Absent from H01-H15, so never a hard reject.
- Rule 7.8 facing leaves across a corridor - enforced by construction in phase 3 and scored on re-check. Deliberately not a hard code: hard-rejecting a stored plan on a rule the rulebook did not list in H01-H15 would be inventing a constraint.
- Rule 8.2 aggregate glazing ratio and rule 8.3 toilet ventilation - neither is in H01-H15, so both are CodeFindings, not Violations. Both resolve to status 'unverified' under the current iscodes tables because NBC Part 8 has not been read into this repository.

## soft_terms
- entry_privacy (rulebook 11.2 weight 0.12) - soft['entry_privacy'], computed by entry_sightline as sum(SIGHTLINE_TARGET_WEIGHT[t] * exposure[t]) / sum(weights), clamped 0..1. Rule 3.5; graded soft on the authority of rulebook test T10, which calls a toilet visible from the open main door a soft penalty, not a reject.
- door_placement (rulebook 11.2 weight 0.08) - soft['door_placement'], the per-door mean of 0.35*corner_offset + 0.30*longest_wall + 0.15*facing + 0.10*short_side + 0.10*movable_clash. Covers rules 7.3 (centred doors), 7.7 (longest uninterrupted furniture wall, wall end nearer the short side) and 7.8 (faced leaves), which is exactly the rulebook's own definition of this term: 'centred doors, short corner offsets, faced leaves'.
- facade_utilisation (rulebook 11.2 weight 0.10) - soft['facade_utilisation'], the fraction of habitable rooms whose facade run is below FACADE_PREF_PER_HABITABLE_MM (3000), double-weighted for those below FACADE_MIN_PER_HABITABLE_MM (2500). Rule 8.5. openings computes it because facade allocation per room is only fully known once windows are placed, but geometry.py may also claim this term; validate.py must take it from exactly one source or it will be double-counted.
- daylight_depth (no rulebook weight of its own) - soft['daylight_depth'], the fraction of habitable rooms whose depth from the chosen window wall exceeds DAYLIGHT_DEPTH_FACTOR * head height. Rule 8.4 explicitly says it reinforces the section 5.1 aspect caps, so validate.py should fold it into the 0.20 aspect-deviation term rather than giving it a weight of its own.
- glazing_orientation (no rulebook weight) - soft['glazing_orientation'], the area-weighted mean of CARDINAL_GLAZING_PENALTY over all windows. A soft Indian-context preference of the same character as vastu.py's sector anchors; weight it at most 0.02 and never let it move a window off the wall rule 8.2 needs.

## depends_on
- backend/floorplan/spec.py - every rulebook constant listed in the constants section, imported by an explicit `from .spec import (...)` list. openings.py declares no numeric literal of its own beyond four implementation tolerances. A missing name is an ImportError at load, which is the correct loud failure.
- backend/floorplan/topology.py - the frozen access graph as a sequence of AccessEdge(a, b, role, serves). openings never adds, removes or re-routes an edge; it only decides which wall the opening is cut in. topology must set `serves` to the room whose one-door budget the edge consumes (the toilet for an en-suite, the balcony for a balcony door, '' for a through-space or the main door), or rule 7.1 is unenforceable. topology also supplies entry_point and entry_cardinal.
- backend/floorplan/geometry.py - realised RoomShape polygons in integer millimetres, axis-aligned, at most 6 vertices per rule 5.4.1, and the FurnitureRect list produced by the rule 5.3 packing test with `fixed` correctly set (wardrobe, counter, wc, basin, shower, fridge fixed=True; bed, sofa, dining_table, tv_wall, aisle fixed=False). Rule 7.5 is unenforceable without the fixed set, so openings raises FurnitureMissing rather than passing a door it could not check. geometry must also serialise room x/y/w/h at 3 decimal places, not the 2 the current code uses.
- backend/floorplan/services.py - FacadeSeg entries with opens_to 'shaft' and shaft_clear_sqm, for the rule 8.1 shaft alternative and the rule 9.5 kitchen exhaust duct. Without shaft_clear_sqm a shaft-lit habitable room is reported unverified, never compliant.
- backend/floorplan/envelope.py - the FacadeSeg list for opens_to 'air' / 'party' / 'corridor' and its cardinals, derived from the section 1.1 plannability gate's facade budget.
- backend/iscodes.py - new door_table(version) and vent_table(version) built on the existing _FIRE_NBC_2016 / _FIRE_SP7_2026 / UNREAD pattern, plus four new CLAUSES entries (vent_window, vent_toilet, door_width, vent_shaft) for citation. openings reads these ONLY to produce CodeFindings, never to generate geometry, so an UNREAD entry downgrades a claim without stopping a plan.
- backend/floorplan/validate.py - consumes OpeningsResult.hard for H01/H02/H03/H09/H13/H14, OpeningsResult.soft for the 0.12 entry-privacy, 0.08 door-placement and 0.10 facade-utilisation terms, and OpeningsResult.code_findings as a third list it must render separately from both.
- backend/floorplan/search.py - the GA's only legal door mutation is offset_bounds() plus with_offset(), per rule 11.3. It must never change a door's wall, room pair, kind or swing side.
- backend/floorplan/__init__.py - builds OpeningsContext per unit via OpeningsContext.build(), calls place_openings once per unit, and calls attach_openings on the floor_layouts entry.
- frontend/src/components/FloorPlate.jsx, frontend/src/modules/PlanningModule.jsx, frontend/src/modules/ThreeDModule.jsx - accept `doors` and `windows` props defaulting to [], delete the faked arc and window band, and read entry.doors / entry.windows with an `|| []` guard.
- backend/server.py - mirrors entry['doors'] and entry['windows'] onto tower['doors'] / tower['windows'] for floor 1, exactly as it already mirrors tower['rooms'].

## risks
- The mandatory generation order puts doors at step 8 and windows at step 9, but rule 7.6 couples them. I resolved this with a bounded reconcile pass that may only flip a door's handedness. If a unit needs a door moved to a different wall to clear a window, this design will emit a soft penalty rather than fix it, and the plan ships with a leaf across a window. The alternative - letting openings re-choose walls - would break rule 11.3's guarantee that topology is frozen, so I chose the visible defect over the silent topology change. Flagging it as the sharpest unresolved tension in this module.
- Rulebook test T06 ('toilet door and bedroom door 600 apart, both 900 leaves - reject H09') is ambiguous. Under my model, two doors swinging into DIFFERENT rooms across a corridor wall cannot clash by arc, and the case is caught only by the same-wall pier rule F1c. Under the other reading (both leaves swinging into one room) it is caught by the phase 2 group search. I made both paths raise H09, but the implementer must write TWO tests, one per reading, or T06 will appear to pass for the wrong reason. If '600 apart' means 600 mm of clear pier rather than 600 mm hinge-to-hinge, F1c will not fire and only the arc test can catch it - and it will not, because the arcs are in different rooms. That case may be a genuine gap in my model.
- The hand and arc_sweep conventions are derived, not read from a standard. I worked one example through and pinned it in the algorithm so it is testable, but if the renderer's coordinate frame ever flips (a viewBox with a negative scale, a mirrored plan), every arc will draw on the wrong side and nothing will error. The sweep flag should be regression-tested against a rendered snapshot, not just a unit test on the number.
- Room coordinates are serialised at 2 decimal places today (10 mm) and I require 3 (1 mm) for openings. If geometry.py keeps 2 dp for rooms, a 100 mm corner offset can land up to 5 mm off the wall face and a door will appear detached from its room at high zoom. This is a cross-module requirement that another agent has to honour and nothing will fail loudly if they do not.
- Rule 5.4.1 permits L-shaped rooms. My wall derivation handles them, but the 'anchorable corner' test only accepts CONVEX corners - at a concave (inside) corner there is no wall for the leaf to lie flat against. In an L-shaped bedroom whose only corridor wall meets the notch, every candidate falls through to the centred fallback and takes the rule 7.3 soft penalty. That may be architecturally correct or it may be the module giving up; I have not validated it against a real L-shaped plan.
- The entry sightline is cast with every internal door open, which is the worst case. It will report a toilet door visible in plans a human architect would accept, inflating the 0.12 privacy term and pulling the GA toward foyer geometry nobody asked for. The weight, not the geometry, is the lever if that happens.
- kitchen_counter and dining_table sightline targets depend on geometry.py emitting FurnitureRects with those exact `role` strings. If it emits different strings, those two targets silently land in SightlineReport.unverified forever and rule 3.5 is half-checked while looking fully checked. The role vocabulary needs to be a shared constant, and I have put it in this spec's FurnitureRect definition rather than in spec.py, which is a coordination weakness.
- Every window compliance finding resolves to 'unverified' under the iscodes tables I specify, because NBC Part 8 is genuinely unread. That is the honest answer, but it means the product will show zero glazing passes on every plan until someone reads the clause. Whoever owns the UI must be told that 'unverified' is a third state, or it will get rendered as a failure and read as a regression.
- MAX_GROUP_COMBOS truncation is deterministic but arbitrary: when a swing group is too large the module drops the worst-cost candidates and notes it. A pathological unit could have its only clash-free combination truncated away and then be reported H09 when a solution existed. The cap is generous relative to any 1BHK-3BHK unit, but it is a real failure mode, not a theoretical one.
- A toilet too small for any of inward swing, outward swing or a sliding pocket is reported as a rule 5.2 geometry failure with a note, not as a door failure. That routing decision is mine and it is not in the rulebook; if validate.py does not know to look for that note, the defect will be invisible in the report.
- Hand-editing a room in PlanningModule writes back only `rooms`, leaving doors and windows at their old absolute coordinates. I added `anchor` so reanchor() can repair them, but the frontend edit path currently has no hook to call it, so the first hand-edit after this ships will visibly detach every opening in that room unless that path is changed at the same time.

