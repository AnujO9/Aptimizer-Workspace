# backend/floorplan/spec.py and backend/floorplan/envelope.py

## Summary
spec.py is the single constant surface for the whole floorplan package: the room-type vocabulary, the shared integer-millimetre rectangle primitive, every rulebook number from sections 2-11, and the resolver that reconciles a rulebook design target against a code minimum read from iscodes.py. It fabricates nothing: values the rulebook marks [verify] that this platform does not already assert as code figures are carried as design targets clearly labelled as opinion, not as statute, and the four figures the platform *does* already publish as NBC/IS numbers move into a new versioned iscodes table so the clause card and the checker read the same constant. envelope.py is the section 1.1 plannability gate — the four rejects (facade budget, depth/width cap, minimum area, no-facade) computed in integer mm with rounding biased so a rounding artefact can never turn a fail into a pass. It never short-circuits: a rejection reports every failing test plus the derived requirements (max depth, min facade, min area) an envelope would have to meet, and translates those into a `SiteLayoutConfig` override dict that `siteplan.plan.plan_site(project, overrides)` already accepts — no new siteplan API is invented, because none exists to reshape a single block.

## Interface
```python
# =====================================================================================
# backend/floorplan/spec.py
# =====================================================================================
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable, Literal, Mapping, Optional, Sequence

import iscodes  # backend/ is on sys.path already (aifloorplan does `import vastu`)

# ---------------------------------------------------------------- unit boundary
MM_PER_M: int = 1000
MM2_PER_M2: int = 1_000_000

def m_to_mm(v: float) -> int: ...          # round-half-away-from-zero
def m_to_mm_floor(v: float) -> int: ...    # for SUPPLY quantities (area available, facade available)
def m_to_mm_ceil(v: float) -> int: ...     # for DEMAND quantities (area required, facade required)
def mm_to_m(v: int) -> float: ...          # round(v / 1000.0, 3)
def sqm_to_mm2(v: float) -> int: ...       # int(round(v * 1_000_000))
def sqm_to_mm2_ceil(v: float) -> int: ...
def mm2_to_sqm(v: int) -> float: ...       # round(v / 1e6, 3)

SETTING_OUT_MODULE_MM: int = 25   # engine choice, NOT a code value. See constants note.
def snap(v: int, module: int = SETTING_OUT_MODULE_MM) -> int: ...        # nearest
def snap_up(v: int, module: int = SETTING_OUT_MODULE_MM) -> int: ...
def snap_down(v: int, module: int = SETTING_OUT_MODULE_MM) -> int: ...

# ---------------------------------------------------------------- shared primitives
Edge = Literal["N", "S", "E", "W"]
EDGES: tuple[Edge, ...] = ("N", "E", "S", "W")
OPPOSITE_EDGE: dict[Edge, Edge] = {"N": "S", "S": "N", "E": "W", "W": "E"}
# Axes match vastu.py and FloorPlate.jsx: +x is East, -y is North, y grows going South.

@dataclass(frozen=True, slots=True)
class RectMM:
    """Axis-aligned rectangle in integer millimetres. THE geometry primitive of the package.

    Every floorplan module imports this rather than defining its own. Integers, not floats:
    vastu.py needed EPS = 0.03 m (30 mm) to survive float-metre comparisons, and that
    tolerance is larger than the rulebook's 100-300 mm door corner offset and its 150 mm
    grid tolerance — a tolerance that swallows the rule it is meant to check.
    """
    x: int
    y: int
    w: int
    h: int
    def __post_init__(self) -> None: ...        # raises ValueError if w <= 0 or h <= 0
    @property
    def x2(self) -> int: ...
    @property
    def y2(self) -> int: ...
    @property
    def area_mm2(self) -> int: ...
    @property
    def long_mm(self) -> int: ...
    @property
    def short_mm(self) -> int: ...
    @property
    def aspect(self) -> float: ...              # long / short, always >= 1.0
    def edge_length_mm(self, edge: Edge) -> int: ...
    def to_metres(self) -> dict[str, float]: ... # {"x","y","w","h"} floats, 3 dp — API boundary only

def rect_from_metres(x: float, y: float, w: float, h: float) -> RectMM: ...

# ---------------------------------------------------------------- room vocabulary
class RoomType(StrEnum):
    FOYER = "foyer"
    LIVING = "living"
    DINING = "dining"
    LIVING_DINING = "living_dining"      # open-plan; counts as ONE facade-needing room
    KITCHEN = "kitchen"
    UTILITY = "utility"
    MASTER_BEDROOM = "master_bedroom"
    BEDROOM = "bedroom"
    ATTACHED_TOILET = "attached_toilet"
    COMMON_TOILET = "common_toilet"
    BATH = "bath"                        # bath only, no WC
    WC = "wc"                            # WC only
    DRESSING = "dressing"
    PUJA = "puja"
    BALCONY = "balcony"
    CORRIDOR = "corridor"
    SHAFT = "shaft"
    STORE = "store"

HABITABLE: frozenset[RoomType]   # rule 8.1: LIVING, DINING, LIVING_DINING, KITCHEN,
                                 #           MASTER_BEDROOM, BEDROOM
SLEEPING: frozenset[RoomType]    # MASTER_BEDROOM, BEDROOM
WET: frozenset[RoomType]         # ATTACHED_TOILET, COMMON_TOILET, BATH, WC, KITCHEN, UTILITY
TOILETS: frozenset[RoomType]     # ATTACHED_TOILET, COMMON_TOILET, BATH, WC
THROUGH_SPACES: frozenset[RoomType]   # rule 7.1: LIVING, DINING, LIVING_DINING, FOYER, CORRIDOR
FACADE_EXEMPT_WITH_SHAFT: frozenset[RoomType]   # {KITCHEN} only — rule 9.5

# The renderer (FloorPlate.jsx) colours by `type` and only knows the legacy vocabulary.
# Conversion happens once, in floorplan/__init__.py, on the way out.
LEGACY_TYPE: dict[RoomType, str] = {
    RoomType.FOYER: "entrance", RoomType.LIVING: "living", RoomType.DINING: "living",
    RoomType.LIVING_DINING: "living", RoomType.KITCHEN: "kitchen",
    RoomType.UTILITY: "utility", RoomType.MASTER_BEDROOM: "bedroom",
    RoomType.BEDROOM: "bedroom", RoomType.ATTACHED_TOILET: "bathroom",
    RoomType.COMMON_TOILET: "bathroom", RoomType.BATH: "bathroom", RoomType.WC: "bathroom",
    RoomType.DRESSING: "closet", RoomType.PUJA: "pooja", RoomType.BALCONY: "balcony",
    RoomType.CORRIDOR: "passage", RoomType.SHAFT: "shaft", RoomType.STORE: "store",
}
def legacy_type(rt: RoomType) -> str: ...

# ---------------------------------------------------------------- unit programme
UnitTypeKey = str      # "1rk" | "1bhk" | "2bhk" | "2.5bhk" | "3bhk"
UNIT_TYPES: tuple[UnitTypeKey, ...] = ("1rk", "1bhk", "2bhk", "2.5bhk", "3bhk")

UNIT_PROGRAMME: dict[UnitTypeKey, tuple[RoomType, ...]]
def normalise_unit_type(raw: str) -> UnitTypeKey: ...   # "2 BHK", "2bhk", "Penthouse" -> key
def programme(unit_type: str) -> tuple[RoomType, ...]: ...
def habitable_count(unit_type: str) -> int: ...
def min_carpet_area_mm2(unit_type: str, version: Optional[str] = None) -> int: ...

# ---------------------------------------------------------------- code/design resolver
@dataclass(frozen=True, slots=True)
class Minimum:
    """One resolved threshold, with its provenance attached. Never a bare number."""
    key: str                     # e.g. "master_bedroom.min_area"
    value: int                   # mm or mm2, per `unit`
    unit: Literal["mm", "mm2", "ratio"]
    binding: Literal["code", "design", "both"]
    code_value: Optional[int]    # None when the code figure is UNREAD or has no entry
    design_value: Optional[int]  # None when the rulebook gives no target
    code_version: str            # iscodes.code_version(...) result
    clause_key: Optional[str]    # key into iscodes.CLAUSES, for citation
    verified: bool               # False when the code figure has not been read from a
                                 # controlled copy of the standard (mirrors WIND_CF_VERIFIED)
    note: str                    # prose the report prints beside the number

class SpecUnavailable(RuntimeError):
    """Neither a code minimum nor a design target exists for this key. Refuse, never guess."""

def min_area(room_type: RoomType, version: Optional[str] = None,
             *, unit_type: str = "2bhk") -> Minimum: ...
def min_width(room_type: RoomType, version: Optional[str] = None) -> Minimum: ...
def min_height(room_type: RoomType, version: Optional[str] = None) -> Minimum: ...
def window_area_ratio(version: Optional[str] = None,
                      *, climate: Literal["default", "hot_humid"] = "default") -> Minimum: ...
def toilet_vent_area(version: Optional[str] = None) -> Minimum: ...
def corridor_min_width(version: Optional[str] = None, *, accessible: bool = False) -> Minimum: ...

SPEC_CONFLICTS: tuple[dict[str, Any], ...]   # built at import; see constants section
def spec_conflicts(version: Optional[str] = None) -> list[dict[str, Any]]: ...
def unread_room_keys(version: Optional[str] = None) -> list[str]: ...   # wraps iscodes.unread_keys

# ---------------------------------------------------------------- section 5.1 aspect
@dataclass(frozen=True, slots=True)
class AspectCap:
    ideal: float
    warn: float
    reject: float                # None-able is NOT used; CORRIDOR is simply absent

ASPECT_CAPS: dict[RoomType, AspectCap]
ASPECT_EXEMPT: frozenset[RoomType]           # CORRIDOR, BALCONY, SHAFT, DRESSING, STORE
def aspect_cap(room_type: RoomType) -> Optional[AspectCap]: ...   # None => exempt

# ---------------------------------------------------------------- section 5.3 furniture
@dataclass(frozen=True, slots=True)
class FurniturePiece:
    key: str
    w_mm: int                    # extent along the piece's local +x
    d_mm: int                    # extent along local +y; the BACK face is at local y = 0
    clear_back_mm: int
    clear_front_mm: int
    clear_left_mm: int
    clear_right_mm: int
    placement: Literal["against_wall", "free"]
    mirrorable: bool             # True when left/right clearances differ; packer may reflect
    required: bool = True

@dataclass(frozen=True, slots=True)
class LinearRunRequirement:
    key: str
    min_run_mm: int
    depth_mm: int
    clear_front_mm: int
    allow_L: bool
    corner_deduction_mm: int     # overlap counted once when an L is used

@dataclass(frozen=True, slots=True)
class FacingPair:
    a: str                       # FurniturePiece.key
    b: str
    min_gap_mm: int              # clear distance between the two footprints
    min_overlap_mm: int          # length over which their projections must overlap

@dataclass(frozen=True, slots=True)
class FurnitureProgramme:
    pieces: tuple[FurniturePiece, ...]
    runs: tuple[LinearRunRequirement, ...] = ()
    pairs: tuple[FacingPair, ...] = ()

FURNITURE: dict[RoomType, FurnitureProgramme]
def furniture_for(room_type: RoomType) -> Optional[FurnitureProgramme]: ...   # None => no test

WALL_CONTACT_TOL_MM: int = 50
FURNITURE_SEARCH_STEP_MM: int = 50
FURNITURE_SEARCH_MAX_NODES: int = 20_000

# ---------------------------------------------------------------- section 5.4 shape
MAX_ROOM_VERTICES: int = 6
MIN_INTERNAL_ANGLE_DEG: float = 75.0
L_LEG_MIN_WIDTH_MM: int = 1800
L_LEG_MIN_AREA_FRACTION: float = 0.25
MIN_CLEAR_DIMENSION_MM: int = 900

# ---------------------------------------------------------------- section 2 zoning
class Zone(StrEnum):
    PUBLIC = "public"
    SEMI_PRIVATE = "semi_private"
    PRIVATE = "private"
    SERVICE = "service"

ZONE_OF_ROOM: dict[RoomType, Zone]
ZONE_ORDER: tuple[Zone, ...] = (Zone.PUBLIC, Zone.SEMI_PRIVATE, Zone.PRIVATE)  # H11 axis
PUBLIC_ZONE_DEPTH_FRACTION: float = 0.30
SERVICE_MUST_TOUCH: frozenset[Zone] = frozenset({Zone.SEMI_PRIVATE})
SERVICE_MUST_NOT_TOUCH: frozenset[Zone] = frozenset({Zone.PUBLIC})
def zone_of(room_type: RoomType) -> Zone: ...

# ---------------------------------------------------------------- section 3 entry/foyer
MAIN_ENTRANCE_COUNT: int = 1
FOYER_MIN_WIDTH_MM: int = 1200
FOYER_PREF_WIDTH_MM: int = 1500
FOYER_MIN_DEPTH_MM: int = 1200
FOYER_PREF_DEPTH_MM: int = 1800
FOYER_MIN_AREA_MM2: int = 1_500_000          # 1.5 m2
FOYER_PREF_AREA_MM2: int = 2_500_000         # 2.5 m2
FOYER_MAY_CONNECT_TO: frozenset[RoomType]    # LIVING, LIVING_DINING, CORRIDOR, STORE
MAIN_DOOR_OPENS_INTO: frozenset[RoomType] = frozenset({RoomType.FOYER})   # H02
ENTRY_SEQUENCE: tuple[str, ...] = ("common_lobby", "main_door", "foyer", "living",
                                   "dining|corridor", "private_zone")
ENTRY_SIGHTLINE_FORBIDDEN: frozenset[str]    # {"toilet_door","bedroom_interior",
                                             #  "kitchen_counter","dining_table"}
PREFERRED_ENTRY_ORIENTATIONS: tuple[str, ...] = ("N", "NE", "E")
VASTU_TIEBREAK_WEIGHT: float = 0.01          # applied AFTER the 11.2 score, never merged in

# ---------------------------------------------------------------- section 4 circulation
CORRIDOR_MIN_WIDTH_MM: int = 900
CORRIDOR_PREF_WIDTH_MM: int = 1050
CORRIDOR_ACCESSIBLE_WIDTH_MM: int = 1200
CIRCULATION_MIN_PCT: float = 8.0
CIRCULATION_TARGET_PCT: float = 10.0
CIRCULATION_SOFT_MAX_PCT: float = 12.0
CIRCULATION_HARD_MAX_PCT: float = 15.0       # H10
CORRIDOR_MIN_DOORS_SERVED: int = 2
CORRIDOR_DEAD_END_MAX_MM: int = 600
MAX_DIRECTION_CHANGES: int = 2
CORRIDOR_SHAPES: frozenset[str] = frozenset({"straight", "L"})
PASS_THROUGH_ALLOWED: frozenset[tuple[RoomType, RoomType]]   # (through, reached) — rule 4.6

# ---------------------------------------------------------------- section 6 adjacency
Adjacency = Literal["R", "P", "A", "F"]
def adjacency(a: RoomType, b: RoomType) -> Adjacency: ...     # symmetric; default "F"
ADJACENCY: dict[frozenset[RoomType], Adjacency]               # canonical store
WALL_FORBIDDEN_PAIRS: frozenset[frozenset[RoomType]]          # rule 6.5 — shared wall, not door
ADJACENCY_MISS_PENALTY: dict[Adjacency, float] = {"R": 10.0, "P": 3.0, "A": 0.0, "F": 0.0}

# ---------------------------------------------------------------- section 7 doors
@dataclass(frozen=True, slots=True)
class DoorSpec:
    key: str
    width_mm: int
    height_mm: int
    min_width_mm: int            # used when a range is given (utility/balcony 750-900)

DOORS: dict[str, DoorSpec]       # "main","bedroom","kitchen","toilet","utility","balcony"
def door_spec(room_type: RoomType, *, is_main: bool = False,
              accessible: bool = False) -> DoorSpec: ...
DOOR_CORNER_OFFSET_MIN_MM: int = 100
DOOR_CORNER_OFFSET_MAX_MM: int = 300
DOOR_SWING_ANGLE_DEG: float = 90.0
TOILET_OUTWARD_SWING_BELOW_MM2: int = 1_500_000
FACING_DOOR_MIN_OFFSET_MM: int = 300
MAX_DOORS_PER_ROOM: int = 1                  # H14; THROUGH_SPACES exempt

# ---------------------------------------------------------------- section 8 light/vent
WINDOW_AREA_RATIO_DEFAULT: float = 1.0 / 10.0
WINDOW_AREA_RATIO_HOT_HUMID: float = 1.0 / 6.0
WINDOW_OPENABLE_FRACTION: float = 0.5
TOILET_VENT_MIN_AREA_MM2: int = 300_000      # 0.3 m2
WINDOW_HEAD_HEIGHT_MM: int = 2100
DAYLIGHT_DEPTH_FACTOR: float = 2.5           # rule 8.4
MIN_FACADE_PER_HABITABLE_MM: int = 2500      # rule 8.5 minimum  -> hard check
PREF_FACADE_PER_HABITABLE_MM: int = 3000     # rule 8.5 preferred -> soft term AND the 1.1 gate

# ---------------------------------------------------------------- sections 9, 10
WC_TRAP_TO_STACK_MAX_MM: int = 2000
SHAFT_MIN_CLEAR_MM: int = 600                # 600 x 600
WALL_TO_GRID_TOLERANCE_MM: int = 150
MAX_BEAM_SPAN_MM: int = 6000

# ---------------------------------------------------------------- section 11.2 soft score
SOFT_WEIGHTS: dict[str, float] = {
    "aspect_deviation": 0.20, "circulation_efficiency": 0.18,
    "adjacency_satisfaction": 0.16, "entry_privacy": 0.12,
    "facade_utilisation": 0.10, "wet_core_compactness": 0.08,
    "door_placement_quality": 0.08, "structural_alignment": 0.05,
    "carpet_efficiency": 0.03,
}
CARPET_EFFICIENCY_TARGET: float = 0.78
HARD_CODES: tuple[str, ...] = ("H01", "H02", ..., "H15")
HARD_RULE_TEXT: dict[str, str]               # H01 -> "entrance_count != 1", verbatim from 11.1


# =====================================================================================
# backend/floorplan/envelope.py
# =====================================================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Optional, Sequence

from siteplan.errors import LayoutError          # siteplan/errors.py imports nothing: no cycle
from .spec import Edge, RectMM, RoomType, UnitTypeKey

DEPTH_TO_FACADE_CAP: float = 2.2               # rule 1.1
CARPET_TO_ENVELOPE_FACTOR: float = 1.18        # rule 1.1, +18% walls & circulation
FACADE_PER_HABITABLE_MM: int = 3000            # rule 1.1 (== spec.PREF_FACADE_PER_HABITABLE_MM)

@dataclass(frozen=True, slots=True)
class UnitEnvelope:
    rect: RectMM
    entry_edge: Edge
    open_edges: frozenset[Edge]                 # edges facing open space
    party_edges: frozenset[Edge] = frozenset()  # shared with the mirrored neighbour
    shaft_point: Optional[tuple[int, int]] = None
    unit_id: str = ""
    tower_id: str = ""
    floor: int = 0
    def __post_init__(self) -> None: ...        # raises ValueError on the invariants below
    @property
    def facade_edges(self) -> frozenset[Edge]: ...      # open_edges - {entry_edge} - party_edges
    @property
    def primary_facade_edge(self) -> Optional[Edge]: ...
    @property
    def facade_width_mm(self) -> int: ...
    @property
    def depth_mm(self) -> int: ...

def envelope_from_metres(box: Mapping[str, float], entry_edge: Edge,
                         exterior_edges: Sequence[str], **kw) -> UnitEnvelope: ...

@dataclass(frozen=True, slots=True)
class EnvelopeFinding:
    code: Literal["E01", "E02", "E03", "E04", "E05", "E06"]
    rule: str                  # "1.1" for E01-E04, "engine" for E05, "input" for E06
    message: str
    measured: float
    required: float
    unit: Literal["mm", "mm2", "ratio", "count"]

@dataclass(frozen=True, slots=True)
class EnvelopeMetrics:
    habitable_count: int
    shaft_served: tuple[RoomType, ...]
    facade_required_mm: int
    facade_available_mm: int
    facade_width_mm: int
    depth_mm: int
    depth_ratio: float
    area_mm2: int
    min_carpet_mm2: int
    required_area_mm2: int
    primary_facade_edge: Optional[Edge]
    widest_room_min_width_mm: int

@dataclass(frozen=True, slots=True)
class EnvelopeRequirements:
    """What this envelope would have to become. Every field is a mm/mm2 integer."""
    min_facade_mm: int
    max_depth_mm: int              # floor(DEPTH_TO_FACADE_CAP * facade_width_mm)
    min_facade_width_mm: int       # ceil(depth_mm / DEPTH_TO_FACADE_CAP)
    min_area_mm2: int
    min_short_dimension_mm: int

@dataclass(frozen=True, slots=True)
class PlannabilityResult:
    ok: bool
    unit_type: UnitTypeKey
    envelope: UnitEnvelope
    findings: tuple[EnvelopeFinding, ...]      # ALL failures, never short-circuited
    warnings: tuple[str, ...]
    metrics: EnvelopeMetrics
    requirements: EnvelopeRequirements
    code_version: str
    def to_dict(self) -> dict[str, Any]: ...   # metres/m2 in the payload, mm kept alongside

class EnvelopeRejected(LayoutError):
    """Rule 1.1: this footprint cannot hold this unit. code == 'ENVELOPE_UNPLANNABLE'."""
    def __init__(self, result: PlannabilityResult): ...
    result: PlannabilityResult

def check_envelope(env: UnitEnvelope, unit_type: str, *,
                   version: Optional[str] = None,
                   shaft_served: Sequence[RoomType] = ()) -> PlannabilityResult: ...
def require_plannable(env: UnitEnvelope, unit_type: str, **kw) -> PlannabilityResult: ...
    # returns the result on success, raises EnvelopeRejected on failure

# ---------------------------------------------------------------- feedback to siteplan
def siteplan_feedback(results: Sequence[PlannabilityResult],
                      tower: Mapping[str, Any],
                      config: Optional[Mapping[str, Any]] = None,
                      *, rows: int = 2) -> dict[str, Any]: ...
def merge_overrides(base: Optional[Mapping[str, Any]],
                    overrides: Mapping[str, Any]) -> dict[str, Any]: ...

# siteplan_feedback returns exactly:
# {
#   "ok": False,
#   "reason": "unit_envelope_unplannable",
#   "rule": "1.1",
#   "tower_id": str, "tower_name": str,
#   "units_rejected": [ {"unit_id": str, "unit_type": str,
#                        "codes": ["E02","E03"], "messages": [str, ...]} , ... ],
#   "required": {                       # binding across every rejected unit
#       "max_unit_depth_mm": int, "min_unit_facade_mm": int,
#       "min_unit_width_mm": int, "min_unit_area_mm2": int,
#       "max_tower_depth_m": float, "min_tower_width_m": float},
#   "config_overrides": {"towers": {"candidate_depths": [float, ...],
#                                   "candidate_widths": [float, ...]}},
#   "apply_with": "siteplan.plan.plan_site(project, merge_overrides(current, feedback['config_overrides']))",
#   "manual_actions": [str, ...],       # prose when no config override can fix it
#   "confidence": "direct" | "advisory",
#   "invalidates": ["towers[*].floor_layouts"],
# }
```

## Constants
## A. The internal unit — decided

**Internal unit is the integer millimetre.** Metres exist only at the public API boundary
(`floorplan/__init__.py`), where `RectMM.to_metres()` / `rect_from_metres()` convert.

Why mm and not the codebase's existing metres: `vastu.py` needs `EPS = 0.03` (30 mm) to
make float-metre comparisons behave. Several rulebook thresholds are *smaller than that
tolerance* — door corner offset 100–300 mm (7.3), wall-to-grid 150 mm (10.1), facing-door
offset 300 mm (7.8). A tolerance that swallows the rule cannot check the rule. Integer mm
also makes tiling exact, so `check_unit`'s `coverage < 0.985` fudge becomes exact equality.

Conversion rules, all mandatory:
- Convert **once at each boundary**. Never round-trip mid-algorithm.
- **Supply quantities floor, demand quantities ceil.** `facade_available` and `area_mm2`
  use `m_to_mm_floor` / a floored `sqm_to_mm2`; `facade_required` and `required_area_mm2`
  use `m_to_mm_ceil` / `sqm_to_mm2_ceil`. A sub-millimetre rounding artefact must never be
  able to turn a fail into a pass. Stated as a rule because it is the one place the gate
  could silently lie.
- Areas cross module boundaries as `int` mm²; reports print m² via `mm2_to_sqm`.
- `SETTING_OUT_MODULE_MM = 25` is an **engine choice, not a code value** — it stops the GA
  emitting a 2437.3 mm room. IS 3861's own basic module is not read (see below).

## B. New additions to backend/iscodes.py — exact

Placed immediately after the `ACCESS` block, under a header
`# ---------------------------------------------------------------- NBC Part 3 / IS 3861 room minima`.

```python
# The four figures this platform already publishes as code numbers — on the is3861 card in
# CODE_LIBRARY and in layout.ROOM_SCHEMA — move here so the card and the checker read one
# constant. That is the same fix the nbc4 card comment describes: the card must not be able
# to say anything the engine is not checking. Everything the platform does NOT already
# assert stays UNREAD rather than being filled from the rule book, because a rule book is
# not a standard and a number sourced from one would carry a clause's authority without a
# clause behind it.
ROOM_MINIMA_VERIFIED = False   # no controlled copy of Part 3 has been read; mirrors WIND_CF_VERIFIED

_ROOM_NBC_2016 = {
    "habitable_min_area_sqm":            9.5,      # single-room dwelling
    "habitable_min_area_multi_sqm":      UNREAD,   # two-or-more-room dwelling (book says 7.5)
    "habitable_min_width_mm":            2400,
    "habitable_min_height_mm":           UNREAD,   # book says 2750
    "kitchen_min_area_sqm":              5.5,
    "kitchen_min_width_mm":              UNREAD,   # book says 1800
    "kitchen_with_dining_min_area_sqm":  UNREAD,   # book says 7.5
    "bath_min_area_sqm":                 1.8,
    "bath_min_width_mm":                 UNREAD,   # book says 1200
    "wc_min_area_sqm":                   UNREAD,   # book says 1.1
    "wc_min_width_mm":                   UNREAD,   # book says 900
    "combined_toilet_min_area_sqm":      UNREAD,   # book says 2.8
    "toilet_min_height_mm":              UNREAD,   # book says 2400
    "window_area_ratio":                 UNREAD,   # book says 1/10, 1/6 hot-humid (Part 8)
    "window_openable_fraction":          UNREAD,   # book says 0.5
    "toilet_vent_min_area_sqm":          UNREAD,   # book says 0.3
}
_ROOM_SP7_2026 = {k: UNREAD for k in _ROOM_NBC_2016}
ROOM_BY_VERSION = {NBC_2016: _ROOM_NBC_2016, SP7_2026: _ROOM_SP7_2026}
ROOM = _ROOM_NBC_2016          # legacy alias, exactly as FIRE = _FIRE_NBC_2016

def room_minima(version=None):
    """Room dimension minima for a code version. Unread entries are UNREAD, never a number."""
    return ROOM_BY_VERSION[code_version(version)]
```

**The inclusion test**, stated once so a future editor can apply it: a value enters
`_ROOM_NBC_2016` as a number only if this platform already asserts it as an NBC/IS figure
somewhere a user can see. That is true of exactly four: 9.5 (is3861 card + `layout.py`),
5.5 (same), 1.8 (same), 2400 (card says "min width 2.4 m"; `layout.py` bedroom `min_dim`).
Everything else is UNREAD. This makes the table small and every entry defensible.

**Rewrite the `is3861` CODE_LIBRARY entry** to format from the table, as `nbc4` already does:

```python
{"id": "is3861", "code": "IS 3861:2002 / NBC 2016 Part 3",
 "topic": "Method of measurement / apartment planning minimums",
 "key_value": ("Habitable room min {habitable_min_area_sqm} m2, kitchen "
               "{kitchen_min_area_sqm} m2, bath {bath_min_area_sqm} m2, min width "
               "{habitable_min_width_mm} mm").format(**_ROOM_NBC_2016),
 "clause": "Cl. 4"},
```
Use plain `{key}` and never `{key:g}`: `_Unread` has no `__format__`, so an empty spec
prints `UNREAD` but `:g` raises `TypeError`. Only the four read keys are formatted anyway.

**New CLAUSES keys** (four; `acc_corridor` already exists and is reused for the accessible
corridor width, so no duplicate is added):

```python
"room_min_area":   {"code": "NBC 2016 Part 3", "clause": "Part 3, Sec. 1 — Development Control (sub-clause not verified)",
                    "topic": "Minimum area of habitable rooms, kitchens and toilets", "verified": False},
"room_min_width":  {"code": "NBC 2016 Part 3", "clause": "Part 3, Sec. 1 — Development Control (sub-clause not verified)",
                    "topic": "Minimum clear width of habitable rooms and kitchens", "verified": False},
"room_min_height": {"code": "NBC 2016 Part 3", "clause": "Part 3, Sec. 1 — Development Control (sub-clause not verified)",
                    "topic": "Minimum clear height of habitable rooms and toilets", "verified": False},
"room_light_vent": {"code": "NBC 2016 Part 8, Sec. 1", "clause": "Part 8, Sec. 1 — Lighting and Ventilation (sub-clause not verified)",
                    "topic": "Window area as a fraction of floor area; openable fraction; toilet vent opening", "verified": False},
```
`"verified": False` is additive: `clause()` does `{**c, ...}`, so it passes straight through
to the UI with no change to `clause()` itself. Existing keys have no `verified` key;
consumers read `c.get("verified", True)`.

## C. Section 5.2 — the split, and the disagreement rule

Everything in 5.2 is `[verify all]`. spec.py splits it in two:

**Code minima** (statutory floor an approval is checked against) → iscodes, table above:
habitable-room area and width, kitchen area and width, bath/WC/combined-toilet area and
width, clear heights, window ratios, toilet vent.

**Design targets** (the rulebook's own architectural opinion; no Indian code distinguishes
a master bedroom from a secondary bedroom, so these cannot be code) → `ROOM_DESIGN_TARGETS`
in spec.py, mm / mm² integers:

| RoomType | min_width_mm | min_area_mm2 | typical_area_mm2 range |
|---|---|---|---|
| MASTER_BEDROOM | 3000 | 11_000_000 | 12–16 m² |
| BEDROOM | 2700 | 8_500_000 | 9–12 m² |
| LIVING | 3300 | 12_000_000 | 14–20 m² |
| LIVING_DINING | 3300 | 19_000_000 | 20–28 m² (living + dining, engine-derived) |
| DINING | 2400 | 7_000_000 | 8–11 m² |
| KITCHEN | 1800 | 5_000_000 | 6–9 m² |
| KITCHEN (with dining) | 2400 | 7_500_000 | 9–12 m² |
| BATH | 1200 | 1_800_000 | 2.2 m² |
| WC | 900 | 1_100_000 | 1.4 m² |
| ATTACHED_TOILET / COMMON_TOILET | 1200 | 2_800_000 | 3.2–4.0 m² |
| UTILITY | 1200 | 2_000_000 | 2.5 m² |
| BALCONY | 900 | — | — |
| FOYER | 1200 | 1_500_000 | 2.5 m² (from rule 3.3) |
| CORRIDOR | 900 | — | — |

`LIVING_DINING` is engine-derived (LIVING + DINING areas), flagged as such in its `note`.

**The disagreement rule — `_resolve()`, one function used by every resolver:**

1. Code value read **and** design target present → `value = max(code, design)`.
   `binding` is whichever is larger, `"both"` on a tie.
2. Design target is **looser** than the code (design < code) — the kitchen case,
   rulebook 5.0 m² vs iscodes 5.5 m² — the **code always wins**, and the pair is appended
   to `SPEC_CONFLICTS` at import. The rulebook is an opinion; the code is a legal floor and
   a looser opinion cannot lower it. Never silently pick one.
3. Code value is `UNREAD`, design target present → `value = design`,
   `binding = "design"`, `verified = False`, note: *"No code minimum has been read from
   {version} for this room type. The figure shown is the rule book's design target and is
   not a statutory floor."* The resolver must **branch on `is UNREAD` before any
   arithmetic** — `max(UNREAD, x)` raises `CodeValueUnread`, which is correct behaviour for
   a check but wrong here, where a conservative substitution exists and is honest as long
   as it is labelled.
4. Code value read, no design target → `value = code`, `binding = "code"`.
5. Neither → raise `SpecUnavailable`. Unreachable for any key in the frozen tables; an
   import-time self-check asserts that.

Special case — `habitable_min_area_multi_sqm` is UNREAD, so a 2BHK bedroom has no
multi-room code floor. `min_area()` falls back to the **single-room** figure (9.5 m²),
which is the stricter direction, with `note` recording `"fallback: single-room minimum
applied because the two-or-more-room figure is unread"`. Substituting a stricter known
value is not fabrication; substituting a looser guess would be.

`SPEC_CONFLICTS` is a module-level tuple built at import. Exactly one entry today:

```python
{"room_type": "kitchen", "field": "min_area",
 "code_sqm": 5.5, "code_source": "iscodes._ROOM_NBC_2016.kitchen_min_area_sqm",
 "rulebook_sqm": 5.0, "rulebook_source": "floor-plan-rulebook.md section 5.2",
 "governing": "code", "governing_value_mm2": 5_500_000,
 "reason": "The rule book's figure is looser than the code minimum this platform already "
           "publishes, so it cannot govern. Both numbers are reported; neither is hidden."}
```

## D. Section 5.1 — aspect caps (plain spec.py constants, no code involvement)

`ASPECT_CAps` as `AspectCap(ideal, warn, reject)`, ratio = long ÷ short:

| RoomType | ideal | warn | reject |
|---|---|---|---|
| LIVING, LIVING_DINING | 1.3 | 1.5 | 1.8 |
| MASTER_BEDROOM | 1.2 | 1.4 | 1.6 |
| BEDROOM | 1.25 | 1.45 | 1.7 |
| DINING | 1.2 | 1.4 | 1.7 |
| KITCHEN | 1.6 | 2.0 | 2.4 |
| ATTACHED_TOILET, COMMON_TOILET, BATH, WC | 1.5 | 1.8 | 2.2 |
| UTILITY | 2.0 | 2.5 | 3.0 |
| FOYER | 1.5 | 1.8 | 2.2 (engine choice, book silent — flagged in the docstring) |

`ASPECT_EXEMPT = {CORRIDOR, BALCONY, SHAFT, DRESSING, STORE}`; `aspect_cap()` returns None.

## E. Section 5.3 — furniture, as packable data

```
MASTER_BEDROOM:
  bed       1830 x 2000  against_wall  back 0  front 900  left 600  right 600  mirrorable=False
  wardrobe  2100 x  600  against_wall  back 0  front 900  left 0    right 0
SECONDARY (RoomType.BEDROOM):
  bed       1370 x 1900  against_wall  back 0  front 750  left 600  right 0    mirrorable=True
  wardrobe  1500 x  600  against_wall  back 0  front 750  left 0    right 0
LIVING / LIVING_DINING:
  sofa      2100 x  900  against_wall  back 0  front 1200 left 0    right 0
  tv_unit   2400 x  450  against_wall  back 0  front 0    left 0    right 0
  pairs: FacingPair("sofa", "tv_unit", min_gap_mm=1200, min_overlap_mm=1500)
DINING (and the dining half of LIVING_DINING):
  table     1500 x  900  free          back 900 front 900 left 900  right 900
KITCHEN:
  runs: LinearRunRequirement("counter", min_run_mm=3000, depth_mm=600,
                             clear_front_mm=1050, allow_L=True, corner_deduction_mm=600)
TOILETS, FOYER, CORRIDOR, BALCONY, PUJA, UTILITY, STORE, DRESSING, SHAFT: no programme.
  furniture_for() returns None — area + clear width IS the test. No fixture dimensions are
  invented for these, because the rule book gives none.
```

Packing contract for `geometry.furniture_fits(room: RectMM, room_type, obstacles=())`:
1. Axis-aligned placement, rotations 0/90/180/270; a `mirrorable` piece may also reflect.
2. `against_wall` → the back face lies within `WALL_CONTACT_TOL_MM = 50` of a room wall.
3. Piece **footprints** may not overlap each other or any obstacle.
4. A piece's **halo** may not overlap any *other piece's footprint* or any obstacle.
   **Halos MAY overlap each other** — 600 mm beside a bed and 900 mm in front of a wardrobe
   are the same square metre of floor. Without this rule no real bedroom passes and the
   whole test gets disabled by the first person who runs it.
5. Footprint + halo must lie inside the room rect.
6. Search: pieces largest-first, candidate positions wall-anchored on a
   `FURNITURE_SEARCH_STEP_MM = 50` grid plus corner snaps, backtracking, node cap
   `FURNITURE_SEARCH_MAX_NODES = 20_000`. Result is `"fits" | "no_fit" | "undecided"`.
   `"undecided"` (cap hit) is treated by H07 as a **failure**, labelled distinctly — the
   search giving up is not evidence the furniture fits.
7. Door swing rectangles are passed as `obstacles` on the H07 re-check only; the step-7
   feasibility call runs without them, because doors do not exist yet at that point.

## F. Section 6 — adjacency as data

Stored as `ADJACENCY: dict[frozenset[RoomType], Adjacency]`. **Symmetric** — a door
connects both ways. Every pair the rulebook gives in both directions already agrees; an
import-time self-check re-derives the matrix from the literal table and raises on any
future asymmetry. Default for an unlisted pair is `"F"`: a permissive default is how a
toilet door ends up on the dining room.

Transcribed pairs (`—` and blank cells excluded): Foyer–Living R; Foyer–Dining A;
Foyer–Kitchen F; Foyer–Utility F; Foyer–MBed F; Foyer–Bed F; Foyer–AttToilet F;
Foyer–ComToilet A; Foyer–Balcony F; Living–Dining R; Living–Kitchen F; Living–Utility F;
Living–MBed P; Living–Bed P; Living–AttToilet F; Living–ComToilet A; Living–Balcony R;
Dining–Kitchen R; Dining–Utility F; Dining–MBed F; Dining–Bed F; Dining–AttToilet F;
Dining–ComToilet A; Dining–Balcony P; Kitchen–Utility R; Kitchen–MBed F; Kitchen–Bed F;
Kitchen–AttToilet F; Kitchen–ComToilet F; Kitchen–Balcony P; MBed–Bed F; MBed–AttToilet R;
MBed–ComToilet F; MBed–Balcony P; Bed–AttToilet A; Bed–ComToilet P; Bed–Balcony A;
ComToilet–Balcony F.

Rows the rulebook omits, added from rules 6.1–6.5 and existing `vastu.check_unit`
behaviour, each flagged `derived=True` in a parallel `ADJACENCY_SOURCE` dict:
Puja–Living R; Puja–Foyer A; Puja–(every toilet) F; Puja–Kitchen F;
Dressing–MBed R; Dressing–Bed A; Dressing–everything-else F;
Corridor–(Foyer, Living, Dining, MBed, Bed, ComToilet, Store, Utility) A.

`WALL_FORBIDDEN_PAIRS` is a **different and stronger** relation from `"F"`: `"F"` forbids a
door, this forbids a shared wall, floor or ceiling. From rule 6.5, one member:
`{PUJA, ATTACHED_TOILET}`, `{PUJA, COMMON_TOILET}`, `{PUJA, BATH}`, `{PUJA, WC}`.
`vastu.check_unit` already enforces exactly this, so the precedent is the codebase's own.

## G. Section 7.2 door sizes, section 8 ratios

`DOORS`: main 1000×2100; bedroom 900×2100; kitchen 900×2100; toilet 750×2000;
utility 900×2100 with `min_width_mm=750`; balcony 900×2100 with `min_width_mm=750`.
All `[verify]` in the rulebook and all plain spec.py constants — a door leaf size is a
joinery dimension, not a code minimum, **except** the barrier-free 900 mm clear width,
which iscodes already carries as `ACCESS["door_width_mm"]` (NBC Part 3 Cl. 13.5, `acc_door`).
So `door_spec(..., accessible=True)` raises every leaf to `iscodes.ACCESS["door_width_mm"]`,
which promotes the 750 toilet leaf to 900. Non-accessible units keep 750.

Corridor width (rule 4.1): in-unit passage minimum 900 is a spec.py design constant, not a
code value — nothing in NBC governs a corridor inside a dwelling. `corridor_min_width(
accessible=True)` returns `iscodes.ACCESS["corridor_min_mm"]` = 1200 with the `acc_corridor`
citation. This mirrors the note iscodes already writes distinguishing `FIRE["corridor_min_m"]`
(egress) from `ACCESS` (barrier-free): three different corridor rules, three different
numbers, never merged.

Window ratio (8.2) and toilet vent (8.3) go through the same resolver, keyed to the UNREAD
`window_area_ratio` / `window_openable_fraction` / `toilet_vent_min_area_sqm` slots, falling
back to the rulebook's 1/10, 1/6, 0.5, 0.3 m² as labelled design targets.

## H. Section 11.2 weights

Verbatim from the table; sum asserted at import to be 1.0 within 1e-9 (it is).
`ADJACENCY_MISS_PENALTY = {"R": 10.0, "P": 3.0, "A": 0.0, "F": 0.0}`,
`CIRCULATION_TARGET_PCT = 10.0`, `CARPET_EFFICIENCY_TARGET = 0.78`.

**Circulation band conflict, resolved:** rule 4.2 says the band is 8–12% and then says
above 15% is a hard reject, leaving 12–15% undefined. Resolution: 8–12% is the soft target
band; 12–15% is a soft penalty growing with distance from 12; **>15% only** is H10. Stated
here so `circulation.py` and `validate.py` cannot resolve it two different ways.

**Rule 3.7 is not one of the nine.** The rulebook's 11.2 table has no vastu term.
`VASTU_TIEBREAK_WEIGHT = 0.01` is applied *after* the 11.2 score as a separate tiebreak and
is never summed into it — the same discipline that keeps hard violations out of the soft list.

## I. envelope.py constants

`DEPTH_TO_FACADE_CAP = 2.2`; `CARPET_TO_ENVELOPE_FACTOR = 1.18`;
`FACADE_PER_HABITABLE_MM = 3000`.

**Facade-figure conflict, resolved:** rule 1.1's gate uses 3000 mm per habitable room while
rule 8.5 gives 2500 minimum / 3000 preferred. Resolution: the *gate* uses 3000 (being
generous at the gate is the gate's entire purpose — it is what eliminates the long-rectangle
output); the per-room *hard* check in validate.py uses `MIN_FACADE_PER_HABITABLE_MM = 2500`;
the 11.2 "facade utilisation" soft term counts rooms under `PREF_FACADE_PER_HABITABLE_MM =
3000`. Three uses, three numbers, all named, none guessed.

## Algorithm
## spec.py

Almost all of spec.py is literal data. The three pieces with behaviour:

### 1. `_resolve(key, code_raw, design_value, unit, clause_key, version) -> Minimum`

```
version = iscodes.code_version(version)
code_present = code_raw is not None and code_raw is not iscodes.UNREAD
    # test identity FIRST. Any comparison or arithmetic on UNREAD raises CodeValueUnread.
code_value = convert(code_raw) if code_present else None     # sqm -> mm2 ceil, m -> mm
if code_present and design_value is not None:
    if design_value > code_value:  binding, value = "design", design_value
    elif design_value < code_value:
        binding, value = "code", code_value
        _register_conflict(key, code_value, design_value)    # appends to SPEC_CONFLICTS
    else: binding, value = "both", code_value
elif code_present:            binding, value = "code",   code_value
elif design_value is not None: binding, value = "design", design_value
else: raise SpecUnavailable(key)
verified = code_present and iscodes.ROOM_MINIMA_VERIFIED
note = one of four fixed sentences chosen by (code_present, binding)
return Minimum(key, value, unit, binding, code_value, design_value, version, clause_key, verified, note)
```

`_register_conflict` is idempotent (keyed on `key`) so repeated calls do not grow the list.
`SPEC_CONFLICTS` is materialised at import by walking every (room_type, field) pair once, so
the conflict registry is complete before any caller asks, and a test can assert it contains
exactly the kitchen entry.

### 2. `min_area(room_type, version, unit_type)`

```
code_key = _CODE_AREA_KEY[room_type]        # RoomType -> _ROOM_* key, or None
table    = iscodes.room_minima(version)
raw      = table.get(code_key) if code_key else None
# multi-room fallback: habitable rooms in a unit with >1 room read
# habitable_min_area_multi_sqm; when that is UNREAD, read habitable_min_area_sqm
# (the single-room figure) instead — stricter, therefore safe — and append
# "fallback: single-room minimum applied ..." to the note.
design   = ROOM_DESIGN_TARGETS[room_type].min_area_mm2
return _resolve(f"{room_type}.min_area", raw, design, "mm2", "room_min_area", version)
```
`min_width` and `min_height` are the same shape against `room_min_width` / `room_min_height`.
Kitchen has two design targets (5.0 standalone, 7.5 with dining); `unit_type` selects, and
the choice is recorded in `Minimum.note`.

### 3. Import-time self-checks (these are real rejections, not decoration)

- `abs(sum(SOFT_WEIGHTS.values()) - 1.0) < 1e-9` else `AssertionError`.
- `ADJACENCY` rebuilt from the literal table both ways; any pair whose two directions
  disagree raises with both cells named.
- Every `RoomType` appears in `ZONE_OF_ROOM` and in `LEGACY_TYPE`.
- Every `RoomType` in `UNIT_PROGRAMME` resolves through `min_area`/`min_width` without
  raising `SpecUnavailable`.
- `HARD_RULE_TEXT` has exactly the 15 codes H01–H15.

These run at import so a bad edit fails collection, not a request.

---

## envelope.py — `check_envelope(env, unit_type, version, shaft_served)`

Never short-circuits. Runs every test, collects every finding, then returns.

```
1.  ut       = spec.normalise_unit_type(unit_type)
    prog     = spec.programme(ut)
    version  = iscodes.code_version(version)

2.  INPUT VALIDITY  (E06)
    facade_edges = env.open_edges - {env.entry_edge} - env.party_edges
    if env.rect.w <= 0 or env.rect.h <= 0            -> E06 (unreachable: RectMM guards it)
    if env.entry_edge in env.party_edges             -> E06
    A unit entered off its own facade is legal (a ground-floor garden entry) but the entry
    edge is still excluded from the facade budget, because the common lobby is on it. Emit
    a warning, not a finding, when env.entry_edge in env.open_edges.

3.  FACADE BUDGET  (E01, E02)                                          rule 1.1
    hab = [r for r in prog if r in spec.HABITABLE and r not in shaft_served]
      # Only RoomType.KITCHEN may be shaft-served (spec.FACADE_EXEMPT_WITH_SHAFT, rule 9.5).
      # Any other room passed in shaft_served is ignored and raises a warning naming it.
      # LIVING_DINING counts as ONE room; a programme using separate LIVING + DINING
      # counts two. The programme decides, not this function.
    facade_required  = len(hab) * FACADE_PER_HABITABLE_MM         # DEMAND -> exact int
    facade_available = sum(env.rect.edge_length_mm(e) for e in facade_edges)   # SUPPLY
    if facade_available == 0                    -> E01 "no wall open to air"
    elif facade_available < facade_required     -> E02

4.  DEPTH vs FACADE WIDTH  (E03)                                       rule 1.1
    primary = OPPOSITE_EDGE[entry_edge] if it is in facade_edges
              else the longest edge in facade_edges (ties -> N, E, S, W order)
              # mirrors vastu.pack_unit's existing facade choice, deliberately
    facade_width = env.rect.edge_length_mm(primary)
    depth        = the rect extent perpendicular to `primary`
    if primary is None -> depth ratio is undefined; E01 already fired, skip E03
    if depth * 10 > int(DEPTH_TO_FACADE_CAP * 10) * facade_width   -> E03
      # integer arithmetic: 22 * depth > ... avoids a float 2.2 comparison deciding a
      # boundary case differently on two runs. Implement as: depth * 10 > 22 * facade_width.

5.  AREA  (E04)                                                        rule 1.1
    min_carpet = spec.min_carpet_area_mm2(ut, version)
      # = sum over prog of min_area(...).value for every room EXCEPT CORRIDOR and FOYER.
      # Circulation is deliberately excluded: the x1.18 factor is stated to cover "walls &
      # circulation", so including it here would double-count. FOYER is circulation.
    required_area = ceil(min_carpet * CARPET_TO_ENVELOPE_FACTOR)       # DEMAND -> ceil
    if env.rect.area_mm2 < required_area   -> E04

6.  SHORT DIMENSION  (E05, engine addition beyond rule 1.1)
    widest = max(spec.min_width(r, version).value for r in prog if r in spec.HABITABLE)
    if env.rect.short_mm < widest  -> E05
      # A 2400 mm-deep envelope cannot hold a 3000 mm-wide master bedroom in any
      # orientation. Rule 1.1 does not test this and the gate is cheap; flagged as an
      # engine addition in the finding's `rule` field ("engine", not "1.1") so a reader
      # can tell it apart from the rule book's own four.

7.  ADVISORY WARNINGS (never findings)
    - depth > DAYLIGHT_DEPTH_FACTOR * WINDOW_HEAD_HEIGHT_MM  (= 5250)
      "rooms on this envelope will run deeper than daylight reaches (rule 8.4)"
    - any Minimum in the programme with binding == "design"
      "no code minimum has been read for {room}; the check used the rule book's target"
    - SPEC_CONFLICTS non-empty -> one line naming each conflict

8.  requirements = EnvelopeRequirements(
        min_facade_mm        = facade_required,
        max_depth_mm         = (22 * facade_width) // 10,
        min_facade_width_mm  = -(-10 * depth // 22),          # ceil division
        min_area_mm2         = required_area,
        min_short_dimension_mm = widest)
    Computed ALWAYS, pass or fail: the caller re-shaping a block needs the target even
    when only one of four tests failed.

9.  return PlannabilityResult(ok=not findings, ...)
```

`require_plannable` calls `check_envelope` and raises
`EnvelopeRejected(result)` when `not result.ok`. `EnvelopeRejected.__init__` builds the
`LayoutError` payload: `code="ENVELOPE_UNPLANNABLE"`, `message` = the first finding's
message plus `"(+N more)"`, `context = result.to_dict()`. Reusing `LayoutError` means
`server.py` serialises it through the path it already has for siteplan failures.

---

## envelope.py — `siteplan_feedback(results, tower, config, rows=2)`

Rule 1.1: *"Feed the failure back to the tower packer in siteplan/ and make it re-shape or
re-split the block."* There is no per-block reshape API in `siteplan/` — `plan()` re-plans
the whole site from a `SiteLayoutConfig`, and `plan_site(project, overrides)` accepts a
partial override dict deep-merged by `SiteLayoutConfig.from_dict`. That is the only real
hook, so the feedback is shaped as that override dict. Nothing else is invented.

```
1.  failed = [r for r in results if not r.ok]; if none, return {"ok": True}.

2.  BINDING REQUIREMENTS across every failed unit:
      max_unit_depth_mm  = min(r.requirements.max_depth_mm        for r in failed)
      min_unit_facade_mm = max(r.requirements.min_facade_mm       for r in failed)
      min_unit_width_mm  = max(r.requirements.min_facade_width_mm for r in failed)
      min_unit_area_mm2  = max(r.requirements.min_area_mm2        for r in failed)

3.  TOWER GEOMETRY.
      corridor_m = max(float(tower.get("corridor_width") or 2.0), 1.8)   # aifloorplan's own rule
      width_m, depth_m = tower.get("width_m"), tower.get("depth_m")      # siteplan LayoutResult shape
      if either is missing, derive from tower["footprint_area"] assuming the configured
      aspect band and set confidence = "advisory"; otherwise confidence = "direct".
      rows: 2 for a double-loaded plate (aifloorplan lays two rows), 1 for single-loaded.

4.  TRANSLATE unit requirements into tower requirements:
      max_tower_depth_m = rows * mm_to_m(max_unit_depth_mm) + corridor_m
      units_per_row     = ceil(total unit count / rows)   from tower["units"] counts
      min_tower_width_m = units_per_row * mm_to_m(min_unit_width_mm)

5.  CONFIG OVERRIDES against the ACTUAL fields siteplan.pack._candidate_footprints reads:
      base = SiteLayoutConfig.from_dict(config).towers
      depths = [d for d in base.candidate_depths if d <= max_tower_depth_m]
      widths = [w for w in base.candidate_widths if w >= min_tower_width_m]
      if not depths:
          synthesise a ladder down from max_tower_depth_m in 2.0 m steps to a floor of
          9.0 m (below that a double-loaded plate cannot hold a corridor plus two flats),
          rounded down to 0.5 m. If the ladder is empty, depths stays empty.
      if not widths:
          synthesise up from min_tower_width_m in 9.0 m steps, three entries.
      Emit only the keys that actually changed; never echo an unchanged list.
      If `depths` is still empty, emit NO towers override and instead push a
      manual_action: the plate cannot be made shallow enough at this unit mix, so the
      fix is fewer/smaller units per floor or a single-loaded corridor — a change to
      project data, not to SiteLayoutConfig, and saying otherwise would be a fix that
      does nothing.

6.  manual_actions also gets, when relevant:
      - "reduce units per floor from N to M" when min_tower_width_m exceeds the largest
        candidate width even after synthesis
      - "raise road.max_blocks / lower road.min_block_area to re-split the envelope into
        narrower blocks" when the site's blocks are the binding constraint (detectable
        only when `config` carries a road section; otherwise it is offered unconditionally
        as a suggestion, marked as such)

7.  invalidates: ["towers[*].floor_layouts"] — a re-plan moves every tower, so every stored
    floor layout is stale. The caller MUST clear or re-stamp them; the field exists so it
    cannot be forgotten silently.

8.  Return the dict documented in the interface. It is data. `siteplan_feedback` NEVER
    calls plan_site itself: re-planning the whole site is a decision with consequences for
    towers that were fine, and this module is not entitled to make it.
```

`merge_overrides(base, overrides)` is a two-level dict merge (section dicts merged key by
key, scalars replaced) producing something `SiteLayoutConfig.from_dict` accepts verbatim.

## hard_rules
- Rule 1.1 (envelope plannability) — envelope.py is the whole gate. E01 no facade at all, E02 facade_available < habitable_count x 3000, E03 depth > 2.2 x facade_width, E04 area < min_carpet x 1.18. Rejection is by construction: check_envelope is the first call in generate_unit_plan and require_plannable raises EnvelopeRejected before any room exists.
- Rule 8.1 (landlocked habitable room) — partially pre-empted by E01/E02: an envelope that cannot give every habitable room facade is rejected before geometry. Only RoomType.KITCHEN may be substituted by a shaft (rule 9.5); envelope.py ignores any other room passed in shaft_served and warns, so no bedroom can be talked out of its window.
- Rule 8.5 (2500 min facade per habitable room) — spec.MIN_FACADE_PER_HABITABLE_MM is the constant validate.py checks; envelope.py's gate uses the 3000 preferred figure per rule 1.1. Both named, neither guessed.
- H04 (room area < code minimum) — spec.min_area() is the sole source of the threshold, with provenance attached. validate.py rejects on it; spec.py guarantees the number is either read from a standard or explicitly labelled as an unread-fallback design target.
- H05 (room clear width < code minimum) — spec.min_width(), same contract.
- H06 (aspect > hard reject cap) — spec.ASPECT_CAPS[rt].reject; spec.ASPECT_EXEMPT names the room types that have no cap so an implementer cannot invent one.
- H07 (furniture packing failed) — spec.FURNITURE plus the six-clause packing contract, including the load-bearing rule that halos may overlap each other but never another footprint, and the rule that an exhausted search returns 'undecided' and H07 treats that as a failure.
- H10 (circulation > 15% of carpet) — spec.CIRCULATION_HARD_MAX_PCT = 15.0, with the 8/12/15 band ambiguity in rule 4.2 resolved once here so circulation.py and validate.py cannot disagree.
- H11 (zone order not monotonic) — spec.ZONE_ORDER fixes the axis order and spec.ZONE_OF_ROOM the assignment; SERVICE is excluded from the ordering per rule 2.2 rather than being wedged into it.
- H13 (toilet door into kitchen or dining) and H14 (bedroom with more than one door) — enforced by construction from spec.ADJACENCY ('F' for every toilet-kitchen and toilet-dining pair) and spec.MAX_DOORS_PER_ROOM = 1 with spec.THROUGH_SPACES as the only exemption.
- Rule 6.5 (puja not sharing a wall with a toilet) — spec.WALL_FORBIDDEN_PAIRS, kept as a strictly stronger relation than adjacency 'F'. 'F' forbids a door; this forbids a shared wall, floor or ceiling. vastu.check_unit already enforces exactly this, so the distinction is the codebase's own precedent, not a new idea.
- Refusal over fabrication (house rule, and iscodes' stated contract) — every 5.2 value this platform has not actually read from a standard is UNREAD in iscodes, and spec.py branches on `is UNREAD` before any arithmetic. Where a conservative substitution exists (the multi-room habitable minimum falling back to the stricter single-room figure) it is used and labelled; where none exists, SpecUnavailable is raised. Every resolved Minimum carries binding, code_value, verified and a note, so no caller can print a number without its provenance.

## soft_terms
- spec.SOFT_WEIGHTS is the authoritative table of all nine section 11.2 terms with the rule book's weights verbatim (aspect_deviation 0.20, circulation_efficiency 0.18, adjacency_satisfaction 0.16, entry_privacy 0.12, facade_utilisation 0.10, wet_core_compactness 0.08, door_placement_quality 0.08, structural_alignment 0.05, carpet_efficiency 0.03). spec.py contributes no term of its own; it supplies the constants every term is measured against, and asserts at import that the weights sum to 1.0.
- aspect_deviation (0.20) — measured against spec.ASPECT_CAPS[rt].ideal, area-weighted per the rule book.
- circulation_efficiency (0.18) — measured against spec.CIRCULATION_TARGET_PCT = 10.0, penalty growing outside the 8-12% band and up to the 15% hard limit.
- adjacency_satisfaction (0.16) — spec.ADJACENCY plus spec.ADJACENCY_MISS_PENALTY {'R': 10.0, 'P': 3.0}.
- entry_privacy (0.12) — spec.ENTRY_SIGHTLINE_FORBIDDEN names the four targets of rule 3.5.
- facade_utilisation (0.10) — counts habitable rooms with less than spec.PREF_FACADE_PER_HABITABLE_MM = 3000 of external wall, distinct from the 2500 hard floor.
- wet_core_compactness (0.08) — pipe runs against spec.WC_TRAP_TO_STACK_MAX_MM = 2000.
- door_placement_quality (0.08) — spec.DOOR_CORNER_OFFSET_MIN_MM/MAX_MM (100/300) and spec.FACING_DOOR_MIN_OFFSET_MM (300).
- structural_alignment (0.05) — spec.WALL_TO_GRID_TOLERANCE_MM = 150.
- carpet_efficiency (0.03) — spec.CARPET_EFFICIENCY_TARGET = 0.78.
- spec.VASTU_TIEBREAK_WEIGHT = 0.01 for rule 3.7's preferred N/NE/E entry orientation. Explicitly NOT one of the nine: it is applied after the 11.2 score as a separate tiebreak and never summed into it, on the same principle that keeps hard violations out of the soft list.
- envelope.py contributes NO soft term. Rule 1.1 is a gate: an envelope is plannable or it is not. Its advisory warnings (daylight depth beyond 5250, unread code minima, spec conflicts) are prose attached to the result and are never scored.

## depends_on
- backend/iscodes.py — imports UNREAD, CodeValueUnread, code_version, version_label, unread_keys, CLAUSES, clause, ACCESS, and the NEW room_minima()/ROOM_BY_VERSION/_ROOM_NBC_2016/ROOM_MINIMA_VERIFIED this spec adds. spec.py is the only floorplan module that imports iscodes; every other module reads code-derived numbers through spec.min_area/min_width/min_height/window_area_ratio/corridor_min_width so there is exactly one place the version dispatch happens.
- backend/siteplan/errors.py — envelope.py imports LayoutError as the base of EnvelopeRejected. errors.py imports nothing, so there is no import cycle with siteplan.
- backend/siteplan/config.py — envelope.siteplan_feedback imports SiteLayoutConfig only to read the current towers.candidate_widths / candidate_depths defaults when building an override. It never constructs a plan. If the implementer wants to avoid the import entirely, the same lists can be passed in via the `config` argument; the import is a convenience, not a requirement.
- NO floorplan module. spec.py and envelope.py are the base of the package: spec.py imports nothing from floorplan, envelope.py imports only spec. The reverse dependencies are total — topology.py, circulation.py, geometry.py, openings.py, services.py, validate.py, search.py and templates.py all read spec.py, and __init__.py calls envelope.require_plannable first. That means these two files must land before the others compile, and their names must not drift.

## risks
- The RectMM ownership claim is a boundary I am taking that the assignment did not explicitly grant to spec.py. geometry.py (section 5) is the obvious alternative owner, but it sits downstream of envelope.py, which needs a rectangle at step 1. If the geometry.py agent defines its own rect type the two will silently coexist and every cross-module call will need conversion. This needs one line of coordination: RectMM lives in spec.py, everyone imports it.
- spec.UNIT_PROGRAMME overlaps templates.py (section 13). I own it because envelope.py runs at step 1, before a template is selected, and needs the room list to count habitable rooms and sum minimum areas. templates.py must derive its programme FROM spec.UNIT_PROGRAMME rather than restating it. If it restates it, a template with four bedrooms will pass a gate sized for three.
- The iscodes inclusion test ('only numbers the platform already asserts') leaves twelve of sixteen keys UNREAD, so most H04/H05 checks will report binding='design' and verified=False. That is honest, but it means the compliance output will be full of 'not a statutory floor' caveats until someone reads NBC Part 3. If a stakeholder reads that as the engine being broken, the pressure to fill the table with plausible numbers will be strong, and doing so would defeat the entire UNREAD mechanism. Worth saying out loud before the first demo.
- The multi-room habitable fallback (using the stricter 9.5 single-room figure when 7.5 is unread) will reject secondary bedrooms between 7.5 and 9.5 m-sq that a real approval would pass. That is the conservative direction and it is labelled, but it will visibly shrink the achievable unit count on tight plates and someone will want to override it. There is no override designed in, deliberately.
- facade_required = habitable_count x 3000 is severe. A 3BHK with separate living, dining, kitchen and three bedrooms needs 18 m of facade; a 15 m-wide flat on a double-loaded bar cannot supply it, so most of the current tower stock will fail E02. That IS the rule book's stated intent (section 0), but it means the gate will reject nearly everything on day one and the templates/site config will have to move to meet it. The LIVING_DINING single-room option is the main relief valve and it should be the default programme for 2BHK and below.
- siteplan_feedback produces a whole-site re-plan override, because siteplan has no per-block reshape entry point. Applying it moves every tower, including ones whose units were fine, and invalidates every stored floor_layout. The `invalidates` field flags this but nothing enforces it — a caller that applies the override and does not clear tower['floor_layouts'] will leave stale layouts stamped against moved towers, which is the exact failure mode siteplan/version.py's polygon_signature was added to prevent. A floor-plan-level signature is probably needed and is not in scope here.
- The candidate_depths synthesis assumes a double-loaded plate (rows=2) matching aifloorplan.generate_architectural_template. A single-loaded or point-block tower would need rows=1 and the caller has to pass it; nothing in the tower dict records loading type, so the default of 2 will silently be wrong for any future point block.
- The CLAUSES entries I am adding carry part-level citations with the sub-clause explicitly marked unverified. That is honest but it is also the first time this codebase has published a clause reference it cannot pin, and the UI has no rendering for the new `verified: False` flag. Without a UI change the caveat is invisible and the citation reads as authoritative.
- The furniture packer's node cap makes H07 sensitive to search order: a room that is genuinely furnishable can return 'undecided' and be rejected. The cap value 20000 is a guess at the tractability boundary, not a measured one, and it should be tuned against a real corpus before it decides anything.
- E05 (short dimension < widest room minimum) is my addition, not the rule book's. It is cheap and correct, but it adds a rejection reason the rule book's section 14 test cases do not cover, so T01-T11 will not exercise it and a regression in it will go unnoticed.

