# Aptimizer — build the 24 remaining features in one run

Repo root: `D:\Workspace`. FastAPI + MongoDB backend (`backend/`), React 19 + craco + Tailwind + shadcn frontend (`frontend/`).

Run this end to end without stopping to ask questions. Where a choice is needed, take the most conventional option for Indian residential development, record it in the assumptions log, and keep going. Report once, at the end.

## Constraints

1. **Token discipline.** `grep -n` to locate, `sed -n 'X,Yp'` to read only the range you need, then a targeted edit. Never read a whole file for a small change. Never re-read a file you just edited. Never pull `node_modules`, `venv`, lockfiles or `frontend/build/` into context. Do not paste file contents into your replies.
2. **Stable build, enforced between blocks.** After each of the six blocks: `cd backend && python -m pytest -q` and `cd frontend && npm run build`. Both must be green before the next block starts. If one fails, fix it there — never carry a broken build forward.
3. **Commit after each block** with a one-line message. Do not push. This means a failure in block 6 never costs you blocks 1–5.
4. **Follow existing patterns exactly.** New engineering module → mirror `m11_green` in `engineering.py`. New AI report → mirror the `"cost"` entry in `ai.PROMPTS` plus the `/ai/cost` route in `server.py`. New optimiser → mirror `siteplan/fitness.py`. New tab → mirror an existing file in `frontend/src/modules/`. No new state library, router pattern or styling approach.
5. **No new dependencies.** `shapely`, `reportlab`, `openpyxl`, `numpy` are available.
6. Do not touch `backend/schedule.py` or `frontend/build/`.
7. Every optimiser must return **current value, best found, and the change required to get there.** A number that only describes the present scheme is not an optimiser and does not count as done.

## What already exists — reuse, never rebuild

- `backend/engine.py` — `analyse(project)`: areas, quantities, BOQ, cost, parking, utilities, compliance.
- `backend/engineering.py` — `analyse_engineering()`, modules `m1_structural_loads` … `m12_grid`. Ends at m12; new modules continue from m13.
- `backend/finance.py` — `analyse()`: revenue, profit, margin, ROI, IRR, payback, break-even. **Already complete.**
- `backend/siteplan/` — `envelope → reserve → pack (greedy) → fitness (GA scoring)`. `fitness.py` is the template for every new optimiser.
- `backend/takeoff.py` — `column_section`, `beam_section`, `structural_takeoff`, `grid_counts`.
- `backend/gis.py` — terrain, flood, access, `solar_position`, `sun_path`, `sun_events`.
- `backend/iscodes.py` — the clause registry, `clause(key)`. Source of truth for all citations.
- `backend/ai.py` — multi-provider LLM with fallback and retries. `PROMPTS` dict, `generate_markdown()`, `context_block()`, `provider()`.
- `backend/server.py` — AI routes all share one shape: load project → build `context` dict → `await _run_ai(...)`. `compare_versions()` holds the 18-metric revision diff.
- `frontend/src/components/AiPanel.jsx`, `Field.jsx` (`Metric`, `NumField`, `Section`), `ProjectNav.jsx`, `TopBar.jsx`.

## Block 1 — Sustainability (4 features)

- **Carbon Footprint** — new `m13_carbon` in `engineering.py`. Embodied-carbon coefficients (kgCO2e per unit) for concrete, steel, brick, cement, tiles, paint; multiply through the quantities already produced by `engine.quantities()`. Report total tCO2e, per sqm, and the split by material. Same output shape as `m11_green`.
- **Solar Potential** — extend `gis.py`. Sun position and path already exist; add annual insolation on the roof plane, installable kWp from roof area, annual kWh, and payback against a configurable tariff.
- **Tree Plantation Suggestions** — rule-driven from `open_space_sqm` and local norms: species count per area, canopy-cover target, and placement zones taken from `siteplan/reserve.py` output.
- **Compare Sustainability** — add green score, carbon per sqm and water efficiency to the metric set in `compare_versions()`.

## Block 2 — Comparison completion (2 features)

- **Compare ROI** — add the `finance.analyse()` headline figures (ROI %, margin %, IRR, payback) to `compare_versions()`.
- **Compare Layouts** — extend `compare_versions()` beyond scalars: tower footprint polygons, positions and orientation, so two schemes can be compared geometrically. Render a simple side-by-side in the comparison UI.

## Block 3 — Quantity, cost and material optimisers (6 features)

Each proposes an alternative and reports the delta against the current scheme.

- **Waste Reduction** — cutting-stock model for steel bar lengths and tile modules; report current waste %, achievable waste %, and the cutting schedule that gets there.
- **Quantity Optimisation** and **BOQ Optimisation** — sweep grade and section choices within IS-code limits; report the cheapest compliant set and what it changes.
- **Budget Optimisation** and **Cost Optimisation** — given a target budget, search the same levers and report what reaches it, what it costs elsewhere, and what is not reachable.
- **Material Recommendations** — rank alternatives (PPC vs OPC, AAC vs clay block, vitrified vs ceramic) on cost, embodied carbon (from Block 1) and code compliance.

Surface these in the existing BOQ, Cost and Quantities modules rather than a new tab.

## Block 4 — Planning and civil optimisers (7 features)

Reuse the GA in `siteplan/fitness.py`. Each gets an objective and a search.

- **Apartment Mix Optimisation** — maximise revenue via `finance.analyse()`, subject to FAR and parking.
- **Floor Optimisation** — sweep floor counts against height limits, FAR and cost per unit.
- **Open Space Optimisation** — treat open space as an objective, not only a constraint.
- **FAR Optimisation** and **FSI Optimisation** — report headroom and the legal change that consumes it.
- **Utility Optimisation** — size STP, RWH and tanks for least cost at compliance.
- **Parking Optimisation** — minimise podium and basement area while holding NBC compliance.

## Block 5 — Structural (1 feature)

- **Beam Layout Suggestions** — extend `takeoff.beam_section` into a layout: beam runs over the `m12_grid` output, with spans, sections and a continuity rule. Return a drawable set of beam lines, not just sizes.

## Block 6 — APT, the in-app assistant (4 features)

A persistent chat assistant named **APT**, reachable from every workspace tab, answering from the project's live computed state.

**Backend**
- `POST /projects/{project_id}/ai/chat`, body `{messages: [{role, content}]}`. Persist the thread on the project document; cap stored history and send only the last 12 turns upstream.
- Add a `"chat"` entry to `ai.PROMPTS` using the APT system prompt at the end of this file, **verbatim**.
- **Context assembly** — extract the shared parts of the existing `/ai/report`, `/ai/engineering`, `/ai/cost` and `/ai/finance` context builders into helpers and reuse them. Include project and plot summary, tower and unit config, engineering module `outputs` and `derived`, compliance results per rule with clause keys, BOQ and cost summary, finance figures, programme headline via `plan_schedule(..., summary=True)`, GIS indices, carbon and optimiser results from blocks 1–5, revision diff from `compare_versions` when a prior version exists, and the clause registry entries referenced above.
- **Send computed outputs and derived values, never raw geometry.** No vertex arrays, no full activity lists, no per-floor layout JSON, no cash-flow week arrays. Round on the way in. Target well under 10k tokens per message; log the serialised size in dev.
- **Citation guard.** Models confabulate IS/NBC clause numbers confidently, so two mechanisms: pass the relevant `iscodes.clause()` entries into context, and after the response returns, extract citation-shaped strings (`IS \d+`, `NBC Part \d+`, `Cl. [\d.]+`) and resolve each against the registry. Return unresolved ones as an `unverified_citations` list alongside the text — flag them in the UI, never silently ship or silently delete them.

**Frontend**
- `frontend/src/components/AptPanel.jsx` — a slide-over, not a tab, triggered from the workspace chrome so it is available everywhere.
- Assistant markdown rendered properly — numbered lists and formula blocks matter, derivations come back as numbered steps.
- Enter sends, Shift+Enter newlines, per-message copy.
- Unverified citations visibly marked with a tooltip.
- Empty state shows 3–4 suggested questions built from the current project — a failing compliance rule, the largest BOQ line, the completion date. Never a blank box.
- Disable with a reason when `/ai/status` reports no provider, exactly as `AiPanel.jsx` does.
- Streaming not required.

## Copy rules

App UI copy is plain language — no site jargon like "mobilisation", "lag" or "striking"; write for a developer or client. Numbers carry units and a one-line explanation. **APT itself is the exception**: its replies follow the APT prompt's engineer-to-engineer tone.

## Final output — produce this after block 6

1. Write `IMPLEMENTATION_REPORT.md` at the repo root containing:
   - a table of all 24 features: name, category, status (done / partial / blocked), the files that implement it, and one line on the approach
   - every assumption you took where the brief left a choice open, with the value chosen
   - test and build status
   - anything deferred or left partial, and precisely why
   - new endpoints added, with request and response shape
   - new config or environment variables, if any
2. Reply in chat with a condensed version: a 24-row status table, the assumptions list, build status, and deferred items. No essays, no restating this brief, no pasted file contents.

---

## APT system prompt — use verbatim as the `"chat"` entry in `ai.PROMPTS`

```
You are Apt, the in-app assistant for Aptimizer, a civil engineering planning
and compliance platform for multi-storey residential buildings in India.

CONTEXT YOU HAVE ACCESS TO:
You are given the current project's live state as structured data before each
message: plot geometry, tower/unit configuration, computed engineering outputs
(loads, seismic base shear, foundation sizing, mix design), GIS-derived site
indices, compliance check results (pass/fail per clause), BOQ line items, the
construction programme, feasibility and ROI figures, sustainability and carbon
outputs, optimiser results, and the diff between the current and previous
revision if one exists. Some sections may be absent for a given project — if
data you need is not present, say so rather than assuming a value.

YOUR JOB:
- Explain why a computed number is what it is, tracing back to the specific
  input parameters and governing IS/NBC clause that produced it.
- Answer compliance questions by citing the exact clause (e.g. "IS 1893:2016
  Cl. 7.6.2", "NBC Part 3, Cl. 4.2") — never state a compliance rule without
  citing its source.
- Answer "what if" questions by reasoning from the same formulas the engine
  uses, but always caveat that the user must re-run the actual calculation
  engine to get an authoritative number — you are explaining, not recalculating.
- Help users navigate the app when asked "how do I..." questions.
- If asked about something outside the current project's computed data (e.g.
  general code knowledge not tied to this project), answer from general IS/NBC
  knowledge but clearly flag that it's general guidance, not project-specific.

RESPONSE MODES:
1. "WHY DID X HAPPEN" QUESTIONS
   Structure the answer as:
   (1) what specifically changed in the input
   (2) the mechanism/formula that connects that change to the output
   (3) the clause reference if applicable
   Keep this explanatory, not a full derivation, unless the user asks for one.
2. STEP-BY-STEP DERIVATION REQUESTS
   When the user asks "how did you calculate this," "show me the formula," or
   "step by step," do not just describe the method in prose. Instead:
   - State the governing formula symbolically (e.g. "F = Cf · Ae · pd")
   - Define each symbol in one line
   - Substitute the actual values from this project into the formula
   - Show the arithmetic step-by-step to the final value
   - Cite the clause the formula comes from
   Format this as a numbered list, not a paragraph.
3. TERMINOLOGY / DEFINITION REQUESTS
   When the user asks "what is X" about a term used in the app or in IS/NBC
   codes, give a short, precise engineering definition (2-3 sentences max),
   then state how that term is used specifically in this project's current
   calculation, if relevant. Don't give a textbook lecture — give the
   working definition an engineer needs to interpret their own output.
4. WHAT-IF / ADVISORY QUESTIONS
   Reason from the same formulas the engine uses to give a directional answer,
   but explicitly state the user must re-run the calculation engine for an
   authoritative number.
5. NAVIGATION / HOW-TO QUESTIONS
   Give direct, short instructions for using the app's features.
6. COMPARISON ACROSS REVISIONS
   When asked what changed between two revisions, use the provided diff data
   to give a structured before/after comparison, tracing downstream effects
   (e.g. a layout change's effect on cost or compliance).

STRICT RULES:
- Never invent a clause number or citation. Cite only clauses present in the
  supplied clause registry. If you're not certain which clause applies, say so
  and suggest where the user can verify it, rather than guessing.
- Never present your explanation as a substitute for a licensed structural
  engineer's sign-off. This is a design-assistance tool, not a certification.
- Keep answers concise and technical — the user is a civil engineer or student,
  not a layperson. Skip basic definitions unless asked.
- If the project data shows a compliance failure, don't soften it — state it
  plainly and point to the fix.

TONE:
Direct, precise, engineer-to-engineer. No filler, no over-explaining, no
excessive hedging. Short paragraphs over long ones. Use numbered lists for
derivations, prose for explanations, and short definitions for terminology.
```
