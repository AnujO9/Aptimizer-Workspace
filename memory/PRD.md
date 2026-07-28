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
- Tests: `backend/tests/gis_test.py` (11 tests) + existing `backend_test.py` (32) all pass.

## Backlog
P1 — Google Maps JS API layer (needs paid key), project thumbnails, Google social login.
P1 — GIS: transit isochrones, infrastructure (power/water lines) inference from OSM tags.
P2 — Per-floor room variants (non-typical floors), multi-currency rate libraries, DXF/CAD export.
P2 — 3D: real tower footprint polygons (draw on plan), shadow-study export, GPU instancing for rooms.

## Next tasks
1. Scheme comparison view (two saved versions side by side: FAR, units, cost/flat, compliance).
2. Include GIS suitability + buildability in the Executive Summary PDF.

