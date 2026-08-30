# Aptimizer — five corrections

Five fixes, one commit each, `pytest` and `npm run build` green between every one.

> Earlier reports are preserved as `IMPLEMENTATION_REPORT_24_FEATURES.md` and in git history.

---

## Fix 1 — Setbacks had two owners

**Files:** `backend/siteplan/devcontrols.py`, `siteplan/__init__.py`, `server.py`,
`tests/setbacks_test.py`, `frontend/src/modules/PlotModule.jsx`, `DevControlsModule.jsx`,
`pages/Workspace.jsx`

`project.dev_controls.setbacks` is now the single stored value. Setbacks & Controls owns
editing and shows the statutory minimum per edge with a validation error naming the
governing rule and clause. Plot & Site shows them read-only with a link to the owner.

**A second bug found on the way in.** `dev_controls` was in neither the server's allowed
patch fields nor the frontend's `EDITABLE` list — so the screen that *owned* setbacks never
actually saved them. Every edit was silently discarded on reload. Both lists now carry it.

**`setback_minimums()` / `validate_setbacks()`** are new in `devcontrols.py` and exported
from `siteplan`, so the screen that validates and the engine that builds the envelope read
the same number. New route `GET /projects/{id}/setbacks`.

**Finding worth acting on:** the shipped defaults (front 9, rear 4.5, side 4.5, default 6)
are **below the NBC minimum for the sample project** — a 36 m building on 15,219 m² needs
12 m of open space on every edge. Enabling validation surfaces that rather than hiding it;
`test_the_shipped_defaults_do_not_clear_the_minimum_for_a_tall_block` pins it deliberately.

---

## Fix 2 — What `engine.area_metrics()` actually computes

Read before writing anything, as instructed. Three findings, all in the panel:

| | |
|---|---|
| **FAR** | `builtup / plot_area` — `engine.py:115` |
| **FSI** | `far × config.fsi_factor`, and **`fsi_factor` defaults to 1.0** (`defaults.py:130`) |
| **Are they different?** | **No.** Identical by default. FSI is a *multiplier on FAR*, not a different area basis. They diverge only if someone changes the factor. |
| **Deductions** | **There are none.** Not one. |

That last point is the one worth stating plainly: parking (2,400 m² on the sample) and
society amenities (630 m²) are excluded from FAR **by never being added to `builtup`**, not
by a deduction step. There is no deduction schedule to itemise, so the panel lists what is
*not counted* and says so explicitly rather than inventing an itemised deduction list that
does not exist. If an authority requires an explicit deduction schedule, it is not modelled.

Built-up itself is `(carpet + balcony) × (1 + wall_thickness_factor) + service_core`, per
floor × floors. The common-area loading that produces *super* built-up is **not** in it,
which is why super built-up is larger and is not what FAR is measured on.

**Files:** `backend/engine.py` (`far_derivation()`), `tests/far_test.py`,
`frontend/src/components/FarPanel.jsx`, `modules/CalculationsModule.jsx`

Panel shows: formula → inputs with sources → per-tower contribution → what is not counted
and why → the arithmetic → permissible vs achieved with headroom in ratio and m² → a plain
statement about FAR vs FSI. Thirteen tests check it reconciles to the reported number.

**Deviation:** mounted in Calculations only, not Plot & Site. Plot's FAR is
`layout_metrics.achieved_far` — the site-layout engine's own figure, a different
computation — so this panel would have explained the wrong number there.

---

## Fix 3 — Reports in menu order

**Files:** `frontend/src/modules/ReportsModule.jsx`

Grouped Site / Design / Engineering / Cost & Programme / Deliver, using the navigation's
own labels, Executive Summary last.

**Deviation:** the brief's grouping names three reports that no longer exist — Plot &
Setbacks, Apartment Planning, Parking were merged away in the previous brief. Rather than
resurrect them or show empty headings, each affected group carries one line saying where
its numbers went (setbacks → Compliance; planning and parking → Executive Summary). The
BOQ Excel workbook moved beside the BOQ report it duplicates.

---

## Fix 4 — Per-tower detail in every report

**Files:** `backend/reports.py`, `tests/pertower_test.py`

Seven reports gained per-tower tables: Structural, BOQ, Cost & Feasibility, Programme,
Water, Compliance, Sustainability. Units in headers only, derivation in a footnote, clauses
cited (IS 875, IS 1893 Cl. 7.6, IS 1172, NBC Part 4 Cl. 4.3).

**The distinction that matters, and it is labelled everywhere it applies:** loads, column
sizes and base shear *are* computed per tower and say so. The BOQ, cost, water and carbon
rows are **apportioned** from a project-wide calculation by built-up share — they show
where a project total lands, not an independent per-tower estimate. A reader who assumed
otherwise would compare towers that were never separately costed. Four tests assert the
apportioned tables carry that caveat and the structural one does not.

Totals reconcile: five tests check rows sum to their totals.

---

## Fix 5 — Acceleration was free

Confirmed the bug before fixing it: **3× crew pulled the finish 164 days earlier for +1.8%
cost.** The crew term cancels exactly, as the brief describes.

**Files:** `backend/schedule.py`, `tests/timecost_test.py`,
`frontend/src/modules/ProgrammeModule.jsx`

Three mechanisms, each a named tunable table:

| Mechanism | Value | Basis |
|---|---|---|
| **(a) `CREW_EFFICIENCY`** | 1.0 @ 1× · 0.92 @ 1.5× · **0.85 @ 2×** · 0.78 @ 2.5× · **0.72 @ 3×** | Congestion figures used in delay-and-disruption analysis; linearly interpolated, flat outside |
| **(b) `WAGE_PREMIUM`** | 0% @ 1× · 12% @ 1.5× · 20% @ 2× · 27% @ 2.5× · **32% @ 3×** | Overtime and shift working; inside the brief's 25–35% at the ceiling |
| **(c) Preliminaries** | `engine.DEFAULT_COST_ADDERS["preliminaries_pct"]` (3%) of works cost ÷ **natural** duration | Reuses the engine's rate rather than inventing a parallel one |

**Measured result — the curve is U-shaped:**

| | Finish | Duration | Total | vs baseline |
|---|---|---|---:|---:|
| Compressed −90 d | 2026-12-11 | 11.2 mo | ₹46,529,545 | **+1.1%** |
| **Baseline** | 2027-03-11 | 14.2 mo | **₹46,038,642** | — |
| Extended +120 d | 2027-03-11 | 18.1 mo | ₹46,632,665 | **+1.3%** |

Extension charges preliminaries to the **committed** date: the work finishes when it
finishes, but site establishment, supervision and plant stay on hire until handover.

**A bug inside the fix, caught by its own test.** The monthly preliminaries rate was
divided by the *actual* duration, so it self-cancelled and preliminaries came out identical
at every programme length — reintroducing the exact bug one level up. The rate is now
divided by the **natural** duration, always computed.
`test_the_monthly_rate_does_not_self_cancel` locks it.

**UI:** the Programme banner now shows, beside the crew changes, e.g. *"Finishing 90 days
earlier adds ₹4.9 L: ₹6.0 L overtime premium, ₹27.2 L lost output per head from crowding
the same work front."*

---

## Assumptions

| # | Choice | Value | Why |
|---|---|---|---|
| 1 | Setback seed | front 9, rear 4.5, side 4.5, default 6 | Exactly what PlotModule held, so existing projects are unchanged |
| 2 | Front minimum | max(plot-size rule, height rule) | Each sets a floor; the binding one is the higher |
| 3 | Validation behaviour | Report, do not block | Rejecting the save would trap a project that is already non-compliant |
| 4 | FAR panel location | Calculations only | Plot's FAR is the layout engine's, a different computation |
| 5 | "Deductions" wording | "Not counted in FAR" | There is no deduction step; calling it one would be fiction |
| 6 | Empty report groups | One line saying where the numbers went | An unexplained gap reads as something missing |
| 7 | Per-tower BOQ/cost/water/carbon | Apportioned by built-up share, labelled | Those are project-wide calculations; no per-tower version exists |
| 8 | Per-tower saleable/revenue | Genuinely per tower | Each tower has its own super built-up area |
| 9 | Floor cycle per tower | Same for all | Set by the slab cycle and IS 456 minimums, which do not vary by tower |
| 10 | Crew efficiency curve | 0.85 @ 2×, 0.72 @ 3× | Standard congestion range; named constant so it can be tuned |
| 11 | Wage premium curve | 32% at the 3× ceiling | Brief's 25–35% |
| 12 | Preliminaries rate | Engine's 3%, ÷ natural duration | Reuse over a parallel rate; natural duration prevents self-cancelling |
| 13 | Extension cost mechanism | Preliminaries billed to the committed date | The site is not demobilised until handover |
| 14 | Baseline for the UI delta | Same start date, no target, no multipliers | Fetched once per project, not on every re-plan |

---

## Test and build status

| Gate | Result |
|---|---|
| `pytest` | **621 passed** (605 before Fix 5, 546 at the start of this brief) |
| `npm run build` | exit 0, pre-existing `exhaustive-deps` warnings only |
| New tests | 75 — `setbacks_test` (12), `far_test` (13), `pertower_test` (34), `timecost_test` (16) |

Excluded and untouched as before: `gis_test.py`, `engineering_test.py`, `rbac_v2_test.py`,
`backend_test.py` — all four hit a remote preview URL rather than local code.

---

## Deferred

**No UI rendered in a browser.** The workspace is behind authentication and no credentials
were used. Every surface compiles and its data contract is checked against real backend
output, but the setback validation errors, the FAR panel, the grouped reports page and the
cost-delta banner have not been seen rendered. The FAR panel is the largest new UI here.

**Setback validation reports but does not block.** A project already below the minimum —
which the shipped defaults are — would otherwise be unsaveable. The error names the rule
and the shortfall; acting on it is the user's call.

**Per-tower carbon per m² is identical across towers**, because the apportionment is by
built-up area and the model does not track specification per tower. Stated in the report
footnote rather than hidden.

**Efficiency and premium curves are unvalidated against site data.** They are standard
published ranges, named in one place each for tuning. The shape of the curve is what the
tests lock, not the specific percentages.
