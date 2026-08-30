# Aptimizer — 24-feature implementation report

Six blocks, built in sequence with `pytest` and `npm run build` green between each and a
commit per block.

---

## 1. Feature status

| # | Feature | Category | Status | Files | Approach |
|---|---|---|---|---|---|
| 1 | Carbon Footprint | Sustainability | done | `backend/engineering.py` (`m13_carbon`), `backend/iscodes.py` (`EMBODIED_CARBON`) | Cradle-to-gate coefficients multiplied through `engine.quantities()`. Concrete carries batching/placing only — see §3. |
| 2 | Solar Potential | Sustainability | done | `backend/gis.py` (`annual_insolation`, `solar_potential`), `frontend/src/modules/GisModule.jsx` | ASHRAE clear-sky integrated hourly over 12 representative days using the existing `solar_position`, scaled by a clearness factor. kWp from roof area, yield, payback. |
| 3 | Tree Plantation Suggestions | Sustainability | done | `backend/engineering.py` (`m14_trees`), `backend/iscodes.py` (`TREE_NORMS`, `TREE_SPECIES`) | Bye-law count and canopy target computed separately, binding one named. Zones from the site layout when present. |
| 4 | Compare Sustainability | Comparison | done | `backend/server.py` (`compare_versions`) | Green score, embodied carbon total and per m², water met by rainwater, trees required added to the metric set. |
| 5 | Compare ROI | Comparison | done | `backend/server.py` (`compare_versions`) | Gross revenue, return on cost, margin, IRR and payback month from `finance.analyse()`, using each scheme's own saved assumptions. |
| 6 | Compare Layouts | Comparison | done | `backend/server.py` (`_scheme_geometry`), `frontend/src/modules/CollaborationModule.jsx` (`PlanView`) | Plot box and tower footprints in plot-local metres, drawn side by side on a shared scale. |
| 7 | Waste Reduction | Quantity/cost | done | `backend/optimise.py` (`steel_waste`, `tile_waste`) | First-fit-decreasing 1D cutting stock over real member lengths from the grid; tile module sweep. Returns the cutting schedule. |
| 8 | Quantity Optimisation | Quantity/cost | done | `backend/optimise.py` (`quantity_optimisation`) | 15-combination grade sweep (M20–M40 × Fe415–Fe550), cheapest that clears the IS 456 exposure minimum. |
| 9 | BOQ Optimisation | Quantity/cost | done | same as #8, surfaced in `BoqModule` | Same sweep; the BOQ surface shows it against the priced bill. |
| 10 | Budget Optimisation | Quantity/cost | done | `backend/optimise.py` (`budget_optimisation`) | Given a target, accumulates compliant levers until the gap closes; reports the shortfall when it cannot. |
| 11 | Cost Optimisation | Quantity/cost | done | same as #10, surfaced in `CostModule` | Same search, entered from the cost tab with the target field. |
| 12 | Material Recommendations | Quantity/cost | done | `backend/optimise.py` (`material_recommendations`) | Cement/walling/flooring alternatives ranked on cost + carbon at a named carbon price, filtered by exposure compliance. |
| 13 | Apartment Mix Optimisation | Planning | done | `backend/planopt.py` (`mix_optimisation`) | Sweeps the type split at constant flats-per-floor, maximising `finance.analyse()` revenue subject to FAR and parking. |
| 14 | Floor Optimisation | Planning | done | `backend/planopt.py` (`floor_optimisation`) | ±24-floor sweep scored on **profit**, not cost per flat — see §3. Names the rule that binds. |
| 15 | Open Space Optimisation | Planning | done | `backend/planopt.py` (`open_space_optimisation`) | Footprint/height sweep at constant floor area and constant flat count, maximising open space. |
| 16 | FAR Optimisation | Planning | done | `backend/planopt.py` (`far_optimisation`) | Headroom against the cap, plus the floor count that consumes it while every other rule still passes. |
| 17 | FSI Optimisation | Planning | done | same, `which="fsi"` | FSI is FAR × the project's FSI factor; same search, own result. |
| 18 | Utility Optimisation | Planning | done | `backend/planopt.py` (`utility_optimisation`) | Treated-water reuse sweep shrinking fresh demand and therefore storage, floored at the fire reserve. |
| 19 | Parking Optimisation | Planning | done | `backend/planopt.py` (`parking_optimisation`) | Minimises weighted built area (basement 1.55 vs podium 1.00) holding the NBC slot count fixed. Stackers offered, never auto-selected. |
| 20 | Beam Layout Suggestions | Structural | done | `backend/takeoff.py` (`beam_layout`), `frontend/src/modules/EngineeringModule.jsx` (`BeamPlan`) | Drawable beam lines over the `m12_grid` output with spans, sections and a continuity rule. SVG framing plan. |
| 21 | Project Q&A | APT | done | `backend/aptcontext.py`, `backend/server.py`, `frontend/src/components/AptPanel.jsx` | Live project state assembled per message; slide-over reachable from every tab. |
| 22 | Civil Engineering Guidance | APT | done | `backend/ai.py` (`PROMPTS["chat"]`) | APT system prompt verbatim; clause registry supplied as context. |
| 23 | Report Explanation | APT | done | `backend/aptcontext.py` | Engineering module outputs, derived values and each output's clause are in context. |
| 24 | Scenario Comparison (chat) | APT | done | `backend/aptcontext.py` (`revision_diff` slot) | Diff accepted and passed through when a prior version exists; prompt mode 6 handles it. |

**24 done, 0 partial, 0 blocked.**

---

## 2. Test and build status

| Gate | Result |
|---|---|
| `pytest` (backend) | **432 passed** |
| `npm run build` (frontend) | **exit 0**, compiled with pre-existing warnings only |
| New tests added | 133 across `finance_test`, `sustainability_test`, `optimise_test`, `planopt_test`, `beamlayout_test`, `apt_test`, `payload_test`, `routes_smoke_test` |

Four pre-existing test files are excluded from the gate and were **not** touched:
`gis_test.py`, `engineering_test.py`, `rbac_v2_test.py`, `backend_test.py`. All four are
live integration tests that hit a remote preview URL
(`https://aptimizer-build.preview.emergentagent.com`) rather than local code, and all four
failed the same way before this work began.

---

## 3. Five decisions that changed an answer

These are the places where the obvious implementation produced a wrong number, and the
tests that now pin the correct one.

**Embodied carbon would have been double.** `takeoff.py:250-254` derives `cement_bags`,
`sand_m3` and `aggregate_m3` *from the concrete volume* via the mix design — they are the
concrete's own constituents, not separate purchases. Verified numerically: the bill's
12,833 cement bags are exactly the 1,724.82 m³ of concrete at the mix design's 372 kg/m³.
Giving concrete a ready-mix coefficient *and* counting cement separately would have counted
the clinker twice. Concrete therefore carries 15 kgCO2e/m³ (batching, transport, placing)
and the constituents carry their own. Pinned by
`test_concrete_carbon_does_not_double_count_its_own_cement`.

**Floor optimisation recommended demolishing the building.** Cost per flat rises
monotonically with height, so minimising it answered "3 floors" and destroyed 36 of 48
flats. The objective is now profit, which is what floor count actually trades: 12 → 14
floors, +8 flats, ₹456M → ₹531M, with parking named as the binding rule. Pinned by
`test_floor_optimiser_maximises_profit_not_cost_per_flat`.

**Every cost optimiser reported a free project.** `quantities()["items"]` carries the
quantity but no rate — rate, wastage and amount are only added later in `boq()`. Reading
rates off the quantity items yielded zero throughout. All optimisers now read from
`_priced()`. Pinned by `test_rates_are_read_from_the_bill_not_the_quantity_items`.

**A route decorator ended up on the wrong function.** The `_scheme_geometry` helper was
inserted immediately above `async def compare_versions`, which put it *between* the
`@api.get(".../versions/compare")` decorator and the function it was meant to decorate.
The route bound to the helper, FastAPI advertised `doc` and `an` as required query
parameters, and `compare_versions` was never registered — a working feature, broken, with
every function-level test still green because they called `_scheme_geometry` directly.
Only the HTTP smoke test caught it. All 66 routes are now audited for the same shape and
none of the others is affected. Pinned by
`test_compare_versions_carries_the_new_metrics_and_geometry`.

**The citation guard flagged correct citations.** The registry stores
`IS 1893 (Part 1):2016`; engineers — and the APT prompt's own example — write
`IS 1893:2016`. The first version marked that unverified. A flag that fires on correct
citations gets ignored, and then the real ones do too. IS codes now match with or without
the part; NBC parts are deliberately *not* collapsed, because the NBC has 12 parts and a
part number is which volume you are in. Lettered annexes (`Annex E`) also failed to parse.
Pinned by four tests including
`test_every_clause_in_the_registry_verifies_against_itself`.

---

## 4. New endpoints

All under `/api`, all requiring an authenticated session.

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/finance/defaults` | — | `FinanceConfig` defaults |
| POST | `/projects/{id}/finance` | `{config: {...}, save: bool}` | `{ok, config, saleable, revenue, cost, profit, break_even, timing, cash_flow[], currency}` |
| POST | `/projects/{id}/ai/finance` | `{config}` (optional) | `{text, model, provider, generated_at}` |
| POST | `/projects/{id}/optimise` | `{target_budget: float}` | `{ok, waste, quantity, budget, materials, currency}` |
| POST | `/projects/{id}/optimise/planning` | — | `{ok, floors, far, fsi, open_space, mix, parking, utilities, currency}` |
| POST | `/projects/{id}/ai/optimise` | `{target_budget}` | AI markdown |
| POST | `/projects/{id}/ai/planning` | — | AI markdown |
| POST | `/projects/{id}/ai/chat` | `{messages: [{role, content}]}` | `{reply, thread, context_chars}` |
| GET | `/projects/{id}/ai/chat` | — | `{thread: []}` |
| DELETE | `/projects/{id}/ai/chat` | — | `{thread: []}` |
| GET | `/projects/{id}/ai/chat/suggestions` | — | `{suggestions: [str]}` |

`tests/routes_smoke_test.py` exercises each of these over HTTP with auth overridden,
asserting status, strict JSON (which rejects `NaN`/`Infinity`), and payload shape.
`tests/payload_test.py` runs every payload through strict JSON on six project shapes —
healthy, no towers, no units, one floor, no plot, single unit type — plus an all-rates-zero
project, since that is what every denominator in the codebase sees thirty seconds after
"new project".

Every optimiser result shares one shape, per constraint 7:

```json
{
  "id": "floors", "title": "Floor optimisation", "feasible": true,
  "current": {"value": 456455748, "unit": "INR", "label": "Profit at 12 floors (48 flats)"},
  "best":    {"value": 531097250, "unit": "INR", "label": "Profit at 14 floors (56 flats)"},
  "delta":   {"value": 74641502, "pct": 16.35, "improves": true, "direction": "higher is better"},
  "changes": [{"lever": "...", "from": "12", "to": "14", "effect": "..."}],
  "options": [...], "notes": [...]
}
```

A chat reply carries its citation verdicts:

```json
{"role": "assistant", "content": "...", "model": "...",
 "verified_citations": ["IS 1893:2016 Cl. 7.6.2"],
 "unconfirmed_clauses": ["IS 456 Cl. 99.99.99"],
 "unverified_citations": ["IS 9999:2099 Cl. 3.2.1"]}
```

---

## 5. APT context budget

Target was well under 10k tokens per message. Achieved **39,347 chars ≈ 9,836 tokens**,
logged per request as `apt.context project=… chars=… approx_tokens=…`.

| Section | chars |
|---|---|
| engineering | 21,785 |
| clause_registry | 4,974 |
| optimisers | 4,950 |
| cost | 2,269 |
| compliance | 2,150 |
| everything else | ~3,200 |

What got it there: dropping empty keys across ~112 engineering outputs (repeated key
*names* cost more than the values), merging `clause`+`clause_ref` into one string, scoping
the clause registry to the 49 clauses this project actually cites, clipping output notes to
90 chars, and reducing each optimiser to its headline plus one lever.

Excluded by design and pinned by `test_context_carries_no_raw_geometry`: vertex arrays,
tower/plot polygons, per-floor room layouts, the full activity list, and the week-by-week
cash flow.

---

## 6. Assumptions taken

47 in total. The ones that would change an answer if set differently:

| Area | Assumption | Value |
|---|---|---|
| Carbon | Concrete coefficient | 15 kgCO2e/m³ — batching/placing only (see §3) |
| Carbon | Cement / steel / brick | 42.5 per bag / 2.0 per kg / 0.28 per brick |
| Carbon | Steel route | Indian mixed primary+secondary, not primary-only (~2.8) |
| Carbon | Benchmark bands | <300 low, 300–450 typical, 450–550 high, >550 very high |
| Solar | Clearness factor | 0.80 flat on ASHRAE clear-sky |
| Solar | Area per kWp / roof usable | 10 m² / 60% |
| Solar | Cost / tariff | ₹50,000 per kWp, ₹8/kWh; no subsidy or export price |
| Trees | Count norm / canopy target | 1 per 80 m² open space / 33% |
| Materials | Carbon price for ranking | **₹1,500/tonne** — decides every material recommendation |
| Waste | Baseline | Naive member-by-member cutting, not the bill's flat allowance |
| Grades | Section scaling | √(strength ratio), preliminary only |
| Floors | Objective | **Profit**, not cost per flat (see §3) |
| Parking | Basement vs podium cost | 1.55 vs 1.00 index |
| Parking | Stackers | 0.55 area factor, ₹250k/bay — offered, never auto-selected |
| Utilities | Storage floor | Never below 50% of sized volume (fire reserve) |
| Beams | Continuity | End bays simply supported, interior continuous |
| APT | Turns sent / stored | 12 / 60 |
| APT | Clause registry scope | Only clauses this project cites (49 of 62) |

Full list with rationale for each: see the assumptions log in the session scratchpad.

---

## 7. Known limits

Stated plainly rather than buried, because each one is a place where the number is
directional rather than authoritative.

- **Solar underestimates high-altitude desert sites.** A flat 0.80 clearness factor
  calibrates to within 12% for Hyderabad, Delhi and Bengaluru but reads ~1,690 kWh/m²/yr
  for Leh, where the real figure exceeds 2,100. There is no altitude or regional clearness
  input.
- **Grade sweep section scaling is preliminary.** √(strength ratio) is the standard
  first-pass approximation, not a design. The notes say so on the result.
- **Tower shapes in the layout comparison are squares.** Towers carry a footprint area, not
  a shape. Where the recorded plot dimensions disagree with the drawn polygon area — the
  sample project records 80×50 against a 15,219 m² polygon — the box is rescaled to the
  true area and the result reports `basis`. Where no tower positions are stored, they are
  spread along the plot and marked indicative rather than drawn stacked at the origin.
- **Budget optimiser savings are additive.** The levers act on different bill lines, so they
  add; overlapping levers would not. Noted on the result.
- **Mix optimisation does not model market absorption.** It will happily recommend an
  all-3BHK building if that maximises revenue within FAR and parking. Whether the market
  takes that many of one type is not in the project data. Noted on the result.
- **Float verification on very large programmes.** Unchanged from earlier work: above
  ~150 activities, per-task spare time is reported as an upper bound and the payload says
  so. Dates and the critical path are exact.
- **No visual verification of the new UI.** The workspace is behind authentication and no
  credentials were used. Every new surface compiles clean and every one has had its data
  contract checked against real backend output, and the endpoints behind them are now
  exercised over HTTP — but no page has been rendered in a browser. The Apt slide-over and
  the beam framing SVG are the two worth a look first.

---

## 8. Configuration

No new environment variables and no new dependencies. Existing AI provider keys
(`GROQ_API_KEY`, `XAI_API_KEY`, `GEMINI_API_KEY`, `EMERGENT_LLM_KEY`, optional
`AI_PROVIDER`) drive APT exactly as they drive the existing report panels; with none set,
the APT panel disables itself with the same message `AiPanel` shows.

New optional project-document fields, all with working defaults:
`finance` (assumption set), `solar` (PV overrides), `apt_thread` (chat history),
`ai.finance`, `ai.optimise`, `ai.planning` (stored AI reports).
