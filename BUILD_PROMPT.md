# Aptimizer — Complete the 28 remaining AI features

## Context
Repo root: `D:\Workspace`. Stack: FastAPI + MongoDB backend (`backend/`), React 19 + CRA/craco + Tailwind + shadcn frontend (`frontend/`).

Key files — read ONLY what a phase needs:
- `backend/engine.py` — areas, quantities, BOQ, cost, utilities, compliance. Entry: `analyse(project)`.
- `backend/engineering.py` — numbered modules `m1_structural_loads` … `m12_grid`, aggregated by `analyse_engineering()`. Each returns `{id, title, codes, outputs[], derived{}, recommendation{}}` via the `out()` / `check()` helpers.
- `backend/siteplan/` — layout pipeline: `envelope → reserve → pack (greedy) → fitness (GA scoring)`. `fitness.py` is the template for any new optimiser.
- `backend/ai.py` — multi-provider LLM with retries. `PROMPTS = {...}` dict + `generate_markdown()`. Add a key here to add an AI report type.
- `backend/server.py` — all routes on `@api`. AI routes follow one shape: load project → build a `context` dict → `await _run_ai(kind, context, store_at=..., project_id=..., user=..., activity=...)`.
- `backend/schedule.py` — CPM programme engine (already complete, do not touch).
- `frontend/src/modules/*.jsx` — one module per workspace tab. `AiPanel.jsx` renders any AI endpoint. `Field.jsx` exports `Metric`, `NumField`, `Section`.

## Hard constraints
1. **Token discipline.** Never read a whole file to make a small change. Use `grep -n` to locate, then `sed -n 'START,ENDp'` to read only that range, then a targeted edit. Never re-read a file you just edited. Never dump `node_modules`, `venv`, lockfiles, or build output into context.
2. **Stable build above all.** After every phase: `cd backend && python -m pytest -q` and `cd frontend && npm run build`. If either fails, fix before starting the next phase. Never leave the repo in a non-building state.
3. **Follow existing patterns exactly.** A new engineering module mirrors `m11_green`. A new AI report mirrors the `cost` entry in `PROMPTS` plus the `/ai/cost` route. A new frontend tab mirrors an existing module file. Do not introduce a new state library, router pattern, or styling approach.
4. **No new heavy dependencies.** `shapely`, `reportlab`, `openpyxl`, `numpy` are available. If a phase seems to need a new package, use stdlib or ask first.
5. **Commit per phase** with a one-line message. Do not push.
6. Do not touch `frontend/build/` (gitignored) or `backend/schedule.py`.

## Work order — 6 phases, in this sequence

### Phase 1 — Financial layer (unlocks 5 features)
Nothing financial exists today; everything else in this phase depends on it.
- New `backend/finance.py`: inputs for sale rate per sqft by unit type, other income, sales absorption curve, finance cost, marketing %, approval cost. Derive: gross revenue, total project cost (reuse `engine.analyse()['cost']`), gross/net profit, margin %, ROI %, IRR (simple bisection on NPV), payback period, break-even units and break-even sale rate.
- Route `POST /projects/{id}/finance` and store on the project document.
- Add `"finance"` to `ai.PROMPTS` and route `POST /projects/{id}/ai/finance` for the narrative.
- New `frontend/src/modules/FinanceModule.jsx` with inputs, metric strip, a break-even readout and an `AiPanel`. Register the tab wherever the other modules are registered.
- Delivers: ROI Analysis, Profit Forecast, Project Feasibility, Break-even Analysis.

### Phase 2 — APT, the in-app assistant (unlocks 4 features)
A persistent chat assistant named **APT**, available from every workspace tab. Not a generic
wrapper — it answers from this project's live computed state and cites real clauses.

**Backend**
- `POST /projects/{id}/ai/chat` taking `{messages: [{role, content}]}`. Persist the thread on the
  project document so it survives reload. Cap stored history; send only the last N turns upstream.
- Add a `"chat"` entry to `ai.PROMPTS` using the APT system prompt at the end of this file, verbatim.
- **Context assembly** — build a compact `context` dict per message. Reuse the existing builders in
  `server.py` (`/ai/report`, `/ai/engineering`, `/ai/cost` blocks); extract shared helpers rather than
  duplicating. Include: project + plot summary, tower/unit config, `analyse_engineering()` module
  outputs and `derived` values, GIS indices, compliance results with per-rule pass/fail, BOQ
  summary, programme headline (`plan_schedule(..., summary=True)`), and — once Phases 1/3/4/5 land —
  finance, carbon and optimiser outputs. Send **computed outputs and derived values, not raw
  geometry**: no vertex arrays, no full activity lists, no per-floor layout JSON. Serialise numbers
  rounded. Target well under 10k tokens of context per message; log the size in dev so it can be
  watched.
- **Revision diff**: when the project has a previous version, include the output of the existing
  `compare_versions` logic so "what changed" questions work. Do not recompute it in the chat path.
- **Clause citations must be real.** `backend/iscodes.py` already holds the clause registry
  (`clause(key)`). Pass the relevant clause entries into context and instruct APT to cite only from
  those. Add a post-response check: extract citation-shaped strings from the reply, and if one does
  not resolve in the registry, append a visible "unverified citation" note rather than shipping it
  silently. This is the single most important correctness guard in this phase.

**Frontend**
- `frontend/src/components/AptPanel.jsx` — slide-over panel, message list, input, per-message copy.
  Streaming not required. Reachable from a persistent button in the workspace chrome
  (`ProjectNav.jsx` / `TopBar.jsx`), not buried in one tab.
- Render assistant markdown (lists and code/formula blocks matter — derivations are numbered lists).
- Show suggested opening questions drawn from the current project state, e.g. a failing compliance
  rule or the largest BOQ line, so an empty panel is not a blank box.
- Disable with a reason when `/ai/status` reports no provider, matching how `AiPanel.jsx` does it.

Delivers: Project Q&A, Civil Engineering Guidance, Report Explanation, Scenario Comparison (chat).

### Phase 3 — Sustainability completion (unlocks 3 + 1)
- Embodied carbon: coefficient table (kgCO2e per unit) for concrete, steel, brick, cement, tiles, paint. Multiply through the existing BOQ quantities in `engine.quantities()`. Add as `m13_carbon` in `engineering.py`, same output shape as `m11_green`.
- Solar potential: extend `gis.py` — it already has `solar_position`, `sun_path`, `sun_events`. Add annual insolation on the roof plane and a PV yield estimate (kWp installable from roof area, kWh/yr, payback against tariff).
- Tree plantation: rule-driven suggestion from `open_space_sqm` and local norms — species count per area, canopy target, placement zones from `siteplan/reserve.py` output.
- Add Green score, carbon and water to the metric set in `compare_versions` in `server.py`.
- Delivers: Carbon Footprint, Solar Potential, Tree Plantation Suggestions, Compare Sustainability.

### Phase 4 — Quantity & cost optimisers (unlocks 5)
Each is a real optimiser, not a calculator: propose an alternative and report the delta against the current scheme.
- Waste Reduction: cutting-stock/offcut model for steel bars and tiles; report % waste and a reduced-waste option.
- Quantity Optimisation + BOQ Optimisation: sweep grade/section/spec choices within IS-code limits, report cheapest compliant set.
- Budget Optimisation + Cost Optimisation: given a target budget, search the same levers and report what hits it and what it costs elsewhere.
- Material Recommendations: rank alternatives (PPC vs OPC, AAC vs clay block, etc.) on cost, carbon and code compliance.
- Delivers: Waste Reduction, Quantity Optimisation, BOQ Optimisation, Budget Optimisation, Cost Optimisation, Material Recommendations.

### Phase 5 — Planning & civil optimisers (unlocks 7)
Reuse the GA in `siteplan/fitness.py`. Add an objective + search per item; each returns the current value, the best found, and the change required.
- Apartment Mix Optimisation — maximise revenue (needs Phase 1) or unit count subject to FAR and parking.
- Floor Optimisation — sweep floor counts against height limits, FAR and cost per unit.
- Open Space Optimisation — treat open space as an objective, not just a constraint.
- FAR / FSI Optimisation — report headroom and the change that consumes it legally.
- Utility Optimisation — size STP/RWH/tank to minimise cost at compliance.
- Parking Optimisation — minimise podium/basement area at NBC compliance.
- Delivers those 7.

### Phase 6 — Structural + comparison completion (unlocks 3)
- Beam Layout Suggestions: extend `takeoff.beam_section` into a layout — beam runs on the `m12_grid` output, with spans, sections and a simple continuity rule.
- Compare Layouts: add geometry to `compare_versions` — footprint polygons, tower positions, orientation — not just scalar metrics.
- Compare ROI: add the Phase 1 finance metrics to the compare metric set.
- Delivers: Beam Layout Suggestions, Compare Layouts, Compare ROI.

## Definition of done per phase
- Backend: pytest green, new logic covered by at least one test in `backend/tests/`.
- Frontend: `npm run build` green, no new console errors, new UI reachable from the workspace nav.
- All user-facing copy in plain language — no jargon like "mobilisation", "lag", "striking". Write for a developer or client, not a site engineer. **Exception: APT itself** — its replies follow the APT system prompt's tone (engineer-to-engineer, technical). This applies to app UI copy, not to APT's answers.
- Numbers shown with units and a one-line explanation of what they mean.

## Reporting
After each phase, reply with: what shipped, files touched, test/build status, and anything deferred. Keep it under 10 lines. No essays, no restating this brief.


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
revision if one exists.

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

Two lines were added to the user's original text: the context list now names the modules built in
Phases 1, 3, 4 and 5, and the citation rule now binds APT to the supplied clause registry rather
than its own memory. Everything else is unchanged.
