# Aptimizer — Product Requirements & Build Log

## Original problem statement
Production-grade civil engineering SaaS ("Aptimizer") for apartment planning, quantity & cost
estimation, GIS site intelligence, compliance calculations and 3D visualisation.
Stack: React + FastAPI + MongoDB + JWT auth, Leaflet/OSM maps.

## User choices (confirmed)
- Phase 1 slice: core chain — Auth + Projects + Plot (map draw) + Apartment Planning + Calculations
  + BOQ/Cost + Compliance + Reports.
- Map layer: Leaflet / OpenStreetMap (no Google key). Esri satellite tiles added as a base-layer toggle.
- AI site analysis: Claude Sonnet 4.6 / GPT-5.5 via Emergent Universal Key — deferred to GIS phase.
- Auth: JWT email/password with Admin/Engineer/Viewer roles (Google social login deferred).
- Design: agent-decided — Swiss/high-contrast data-dense dashboard, Work Sans + JetBrains Mono.

## Architecture
- `backend/server.py` — all `/api` routes (auth, users, projects, towers, analysis, versions, shares,
  activity, reports, defaults). Dual auth: httpOnly cookies + Bearer token.
- `backend/auth.py` — bcrypt hashing, JWT access/refresh, role list, brute-force lockout support.
- `backend/engine.py` — pure calculation engine: polygon area, area statement, FAR/FSI, parking,
  quantities (editable thumb rules), BOQ (material/labour/equipment), cost, utilities, compliance rules.
- `backend/defaults.py` — seeded default project model (plot polygon, 1 tower, parking, ratios, rates, 12 rules).
- `backend/reports.py` — reportlab PDFs (7 report types) + openpyxl BOQ workbook.
- MongoDB collections: `users`, `projects` (single embedded project model driving every module),
  `versions` (snapshots), `shares`, `activity`, `login_attempts`.
- Frontend: `pages/` (Login, Register, Projects, Workspace, Profile, Admin) and `modules/`
  (Plot, Planning, Calculations, Parking, Quantities, BOQ, Cost, Utilities, Compliance, Reports,
  Collaboration). Workspace owns project state, POSTs `/api/analyse` for live recalculation (250 ms)
  and autosaves via PUT (900 ms).

## Implemented (28 Jun 2026)
- JWT auth + RBAC (admin/engineer/viewer), profile page, admin user list, brute-force lockout.
- Projects dashboard with live summary metrics, create/delete, sharing, versioning, activity log.
- Plot management: Leaflet polygon draw, draggable vertices, coordinate table, satellite toggle,
  orientation, road-access edges, live area in m²/acres.
- Apartment planning: multi-tower, floors/height/footprint, unit mix, corridors, staircases, lifts,
  common areas/amenities, room planning with clickable 2D SVG floor plate, floor slider.
- Calculations: carpet / built-up / super built-up, ground coverage, FAR, configurable FSI factor,
  open space, density (units/acre, persons/ha) — all live.
- Parking: basement/ground capacity, visitor/EV/accessible allocation, deficit, efficiency, ramp checks.
- Quantities: 14 materials with editable per-project thumb-rule ratios.
- BOQ: material/labour/equipment tables with editable rates; PDF + Excel export.
- Cost: material/labour/equipment totals, per flat, per m², pie + bar charts, budget summary.
- Utilities: water demand, UG/OH tanks, STP, WTP, rainwater harvesting, electrical & pump rooms.
- Compliance: 12 editable rules (add/remove/toggle/threshold) with pass/fail and violation messages.
- Reports: 7 PDF reports + BOQ Excel, all generated live from project data.
- QA: 32/32 backend pytest tests pass; frontend flows verified (iteration_1.json, 100%).

## Implemented — V2 (28 Jul 2026)
- GIS & Site Intelligence module (`backend/gis.py`, `modules/GisModule.jsx`): Overpass feature detection
  (buildings/roads/green/water/transit, 3 mirror endpoints with fallback), Open-Elevation terrain grid +
  diagonal profile + slope class, rule-based flood risk (low-lying vs surrounding ring + water proximity),
  regional wind dataset + wind rose, NOAA sun-path (solstices/equinox) with per-facade daylight guidance,
  accessibility scoring, weighted 4-factor site suitability score, buildability constraint flags,
  and an AI site analysis via Claude Sonnet 4.6 (Emergent Universal Key).
  Stored on the same project document under `project.gis`; `stale` flag when the plot polygon changes.
- 3D interactive layer (`modules/ThreeDModule.jsx`, `lib/scene.js`, react-three-fiber + drei):
  GIS-driven terrain heightfield, plot outline + road-access edge + compass/orientation, animated sun
  (time-of-day + season), instanced nearby buildings / floor slabs / parking slots, tower massing with
  click-to-isolate, detailed floor-slab view colour-coded by unit type, 3D floor plan with extruded
  walls + door openings + window bands, floor slider, section cut, walk mode (pointer lock + WASD),
  layer toggles (parking/balconies/common/violations), compliance-violation red highlighting per tower,
  selection side panel with live carpet area / cost per m² / compliance, and a simple 2D fallback toggle.
- Tests: `backend/tests/gis_test.py` (11 tests) + `rbac_v2_test.py` (2) + existing `backend_test.py` (32)
  = **45/45 pass**. Frontend verified by testing_agent in iterations 2 and 3 (see `/app/test_result.md`
  and `/app/test_reports/iteration_{2,3}.json`); the only two findings (drei `<Html>` label click
  pointer-capture and slider keyboard support) were fixed with stopPropagation handlers and explicit
  floor/sun stepper buttons.

## Implemented — IS/NBC Engineering layer (04 Aug 2026)
User choices: all 12 modules at once (leaner UI), one sidebar section with sub-tabs, ~60 major Indian
cities + state fallback + manual override, new Structural/Water/Fire/Accessibility PDFs + executive
values, shared engineering fields editable inside the section with defaults.
- `backend/iscodes.py` — single source of truth: 59-entry CLAUSES registry (code + clause + topic +
  `library_id` deep-link), ~60 CITIES (seismic zone, basic wind speed, annual rainfall, rain intensity)
  with state fallback and national default, SOILS (SBC/φ/γ), EXPOSURE, MIX tables, RESPONSE_R,
  GREEN_CHECKLIST, GRIHA/IGBC bands, 20-entry CODE_LIBRARY + CODE_KEYWORDS search index,
  CLAUSE_LIBRARY overrides for clauses that cite two standards.
- `backend/engineering.py` — `analyse_engineering(project, base)` returns `{config, city_reference,
  modules, missing_inputs, warnings, summary}` for 11 calculators: structural loads (IS 875 P1–3),
  seismic & base shear (IS 1893:2016), foundation advisor (IS 6403/1904), mix design (IS 10262:2019),
  water infrastructure (IS 1172/NBC 9), storm + RWH (IS 3764/NBC 9), parking NBC/SP:21, fire safety
  (NBC 4, per-floor checklist), accessibility (NBC 3/RPwD), green rating (GRIHA/IGBC), column grid
  optimiser (IS 456/3861). Module 10 is the searchable library served by `/api/iscodes`.
  Missing shared data is reported per module instead of failing.
- Interactions: loads → foundation (column service load, footing area, raft/pile switch on soft clay);
  mix design → BOQ material rows for the project concrete volume; water + storm → auto-credited
  green-rating points; grid optimiser flags columns clashing with planned rooms.
- Endpoints: `POST /api/engineering/analyse`, `GET /api/projects/{id}/engineering`,
  `GET /api/iscodes?q=&id=`, `GET /api/cities`. `engineering` added to the project PUT allow-list and
  to the frontend autosave whitelist.
- Frontend: `modules/EngineeringModule.jsx` (shared-data header with derived zone/wind/rainfall/base
  shear/column metrics, missing-input and warning banners, 12 sub-tabs, per-module inputs, checks
  lists, SBC/BOQ/floor/grid tables, green checklist) + `components/Clause.jsx` clause chips that
  deep-link into the library dialog. Registered as the "IS/NBC Engineering" sidebar section.
- Reports: new Structural / Water / Fire / Accessibility / Engineering-summary PDFs, engineering
  values added to the Executive Summary.
- QA: new `backend/tests/engineering_test.py` (43 tests) — full suite **87/87 pass**; testing_agent
  iteration 4 (60/61 frontend assertions). Bugs found & fixed: engineering config not persisted
  (backend allow-list + frontend EDITABLE whitelist), 11 clause chips deep-linking to an empty
  library, unknown soil_type silently defaulting, and a cross-file test cleanup that deleted other
  suites' projects.

## Backlog
P1 — Google Maps JS API layer (needs paid key), project thumbnails, Google social login.
P1 — GIS: transit isochrones, infrastructure (power/water lines) inference from OSM tags.
P2 — Per-floor room variants (non-typical floors), multi-currency rate libraries, DXF/CAD export.
P2 — 3D: real tower footprint polygons (draw on plan), shadow-study export, GPU instancing for rooms.

## Next tasks
1. Scheme comparison view (two saved versions side by side: FAR, units, cost/flat, compliance).
2. Include GIS suitability + buildability in the Executive Summary PDF.
3. Engineering: derive per-tower (not tallest-only) loads/seismic when towers differ in height.

