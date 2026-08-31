# Aptimizer — editable programme, reports, APT speed, module suggestions

Repo root: `D:\Workspace`. FastAPI + MongoDB backend (`backend/`), React 19 + craco + Tailwind + shadcn frontend (`frontend/`).

Seven steps in three waves. Run them in order, end to end, without stopping to ask questions. Where a choice is open, take the option this brief names, or the most conventional one, log it, and keep going. Report once at the end.

`Aptimizer_Build_Spec.pdf` in the repo root has the same content with more discussion — this file is self-contained and authoritative, so read the PDF only if something here is ambiguous.

## Standing rules

1. **Token discipline.** `grep -n` to locate, `sed -n 'X,Yp'` to read only the range you need, then a targeted edit. Never read a whole file for a small change. Never re-read a file you just edited. Never pull `node_modules`, `venv`, lockfiles or `frontend/build/` into context. Do not paste file contents into your replies.
2. **Build gate between waves.** After each wave: `cd backend && python -m pytest -q` and `cd frontend && npm run build`. Both green before the next wave starts.
3. **Commit after each step** with a one-line message. Do not push. Seven commits, so a failure late never costs the earlier work.
4. **Follow existing patterns.** No new dependencies. Do not touch `frontend/build/`.
5. **UI copy in plain language.** No site jargon. APT's own replies are the exception — those follow its system prompt's engineer-to-engineer tone.

## Relevant existing code

- `backend/schedule.py` — programme engine. `ScheduleConfig`, `build_activities()`, `apply_task_edits()`, `audit_safety()`, `run_cpm()`, `plan_schedule()`. Durations are derived: `work_days = quantity ÷ (output_per_day × crew)`. IS 456 curing and prop-removal lags are hard minimums.
- `backend/server.py` — `/projects/{id}/schedule`, the AI routes, `/ai/chat`, `/ai/chat/suggestions`, `compare_versions()`, `/reports/{report_type}`.
- `backend/aptcontext.py` — APT context assembly. `backend/citations.py` — citation guard. `backend/ai.py` — providers, `PROMPTS`, `generate_markdown()`, `context_block()`.
- `backend/reports.py` — `REPORT_TITLES` and `build_pdf()`. `backend/engineering.py` — modules m1–m14 including `m13_carbon` and `m14_trees`. `backend/optimise.py`, `backend/planopt.py` — optimisers. `backend/finance.py` — ROI, IRR, break-even.
- `frontend/src/modules/ProgrammeModule.jsx`, `ReportsModule.jsx`; `frontend/src/components/AptPanel.jsx`, `AiPanel.jsx`, `Field.jsx`; `frontend/src/pages/Workspace.jsx` holds the module list.

---

# Wave 1 — APT

## Step 1 — APT speed

Today every message, including "hi", runs `engine.analyse()`, `analyse_engineering()` over fourteen modules, `plan_schedule()` and the optimisers, then sends a maximum-size prompt. The model is not the bottleneck; the work before the model call is.

- **Cache the analysis.** Cache `analyse()` and `analyse_engineering()` per project, keyed on the project's `updated_at`. Recompute only when the project actually changed.
- **Intent gate.** Classify the incoming message before building any context. Greetings, thanks, and "what can you do" answer from a fixed short path with no project context at all.
- **Tiered context.** Three sizes — `none` for chit-chat, `light` (project identity, headline metrics, failing rules) for general questions, `full` only when the message names a module, a number or a clause. Route on keywords first, never with an extra model call.
- `citations.verify()` still runs on every full-tier answer. No optimisation may skip it — a fast answer with an invented IS clause is worse than a slow correct one.
- Report measured time and context size for "hi" versus a full engineering question, before and after.

**Done when:** "hi" answers in under a second with near-zero context; a clause question still answers fully with citations verified.

## Step 2 — Module-aware suggested questions

`GET /ai/chat/suggestions` currently returns the same four questions everywhere.

- Add a `module` parameter. `AptPanel` already knows the active module — pass it through and refetch on change.
- One generator per module, drawing on that module's real computed values the way the existing generator does ("Bricks are the largest line at ₹5.5 Cr, what is driving it?" beats a generic question).
- Fall back to the current general set when a module has nothing notable. Cache per module per project version.

| Module | Questions to generate |
|---|---|
| Plot & Site | buildable vs plot area · setback on a named edge · unused FAR |
| Setbacks & Controls | which control binds height · effect of a wider access road · limit with least headroom |
| GIS Intelligence | flood risk meaning for foundations · best-sun edge · slope effect on excavation |
| Apartment Planning | why this carpet ratio · units if the plate grows 5% · unit type earning most per m² |
| Parking | why the requirement is this number · where the shortfall is · NBC clause setting the ECS rate |
| Calculations | which input drives the result · step-by-step derivation · applicable tolerance |
| IS/NBC Engineering | base shear derivation · why this foundation type · what drives embodied carbon |
| BOQ & Quantities | largest line and why · how steel was derived · where waste concentrates |
| Cost Estimation | what cost per flat is made of · head that moved most · biggest saving |
| Programme | what is on the critical path · why the floor cycle cannot compress · phase with most float |
| Feasibility & ROI | break-even sale rate · what drives IRR · effect of a six-month delay on payback |
| Compliance | why a rule fails · smallest change that passes · governing clause |
| Reports | which report has the client summary · what is in the engineering summary · how current the numbers are |
| Versions & Team | what changed between revisions · which change moved cost most · did compliance improve |

**Done when:** switching modules changes the questions; no module shows another module's questions.

---

# Wave 2 — Editable phase breakdown

Everything in the table stays as it is — same phases, same columns, same generated values. The change is that the user can override any of it and the programme re-plans around what they entered.

## Step 3 — Data model, editable names, reordering, task insertion

**Data model.** Add `task_overrides` to the schedule config, keyed by activity id:

```
task_overrides: {
  "t0_col_3": {
    "name": "Floor 3 columns — revised",
    "work_days": 6,
    "crew": 8,
    "cost": 284000,
    "start": "2026-11-04",    // pins the start
    "finish": "2026-11-12",   // pins the finish
    "order": 2
  }
}
```

Every field is optional; absent means "use the generated value". The generator still runs normally and overrides are applied on top of its output. This matters: if the user edits only the crew, days must still recompute from the quantity, or the edit silently breaks the arithmetic that makes this tool different from MS Project.

**Name editing.** Click the task text to edit inline; blur or Enter saves to `task_overrides[id].name`, Escape cancels. Keep the generated name underneath so a reset can restore it.

**Reordering.** Drag handle on the left of each task row, drag within its phase only. Dropping writes an `order` integer to every task in that phase. **Reordering is display order, not schedule order** — dependencies decide when work happens, so dragging a row does not move dates. Show a one-line note under the table saying exactly that, or users will drag rows and wonder why nothing changed.

**Task insertion — the current behaviour and the fix.** The Add-task form's "Starts after" dropdown, left blank, links the new task to the project-start milestone (`Dep(after or "start")` in `apply_task_edits()`). Its earliest start is then the project start date, the same as other day-zero tasks. The table sorts each phase by start date with a stable sort, and user-added tasks are appended after generated ones, so a new task lands last among tasks sharing that date. That is why adding "Survey" to Pre-construction placed it third, after Project start and Mobilisation.

Fix both halves: default the "Starts after" dropdown to the last task in the chosen phase instead of blank, keeping the blank option available and labelled "Project start"; and insert the new row at the position the user dropped it, writing an `order` value like any other reorder, rather than letting date-ties decide.

**Done when:** names persist across a re-plan; dragging reorders within a phase only; a new task lands where the user put it.

## Step 4 — Editable start and finish dates

Replace the two date cells with date inputs carrying a calendar button — the same `<Input type="date">` already used for the programme start and finish fields.

- Setting a date **pins** the task: CPM treats it as a constraint, not a computed value. Clearing unpins and the generated date returns.
- Pinned rows show a pin marker so it is obvious which dates are the user's.
- Pinning a task later moves everything downstream, exactly as a real delay would. That is the point — this is how the user models slippage the generated plan cannot know about.
- If a pinned date is earlier than dependencies allow, do not silently accept it: show the conflict on the row, naming the blocking predecessor and the shortfall in days.
- **IS 456 curing and prop-removal lags are non-negotiable.** A pin that would strike props early must be refused with a reason. `audit_safety()` already enforces this for generated lags; it must enforce it for user-entered dates too.

**Done when:** pinning moves downstream work; an impossible pin is refused with the blocking predecessor named; no pin can violate an IS 456 lag.

## Step 5 — Editable days, crew and cost

| Column | On edit | What recomputes |
|---|---|---|
| Days | Overrides the derived duration | All downstream dates. Show the implied output rate as a hint so the user sees the productivity they just assumed. |
| Crew | Changes people on that task only | Days recompute from quantity ÷ (output × crew) — unless Days was also overridden, in which case Days wins and only labour cost moves. |
| Cost | Overrides the computed cost | Phase cost, project total and the cash-flow curve. The BOQ is **not** touched; the existing variance line reports the gap. |

**Precedence, applied everywhere:** a pinned date beats an edited Days value, which beats an edited Crew value, which beats the generated figure. Show this as a one-line legend under the table.

Also: mark edited cells subtly (left border or dot); show an edit count in the section header with a reset beside it; add per-row reset, per-phase reset and "Reset all edits"; persist overrides with the project so a saved version carries them and a revision comparison reflects them. Nothing renders blank — the override layer starts empty and generated values show throughout.

**Done when:** the legend matches actual behaviour; edited cells are marked; reset restores generated values; a saved version carries the edits.

---

# Wave 3 — Reports and polish

## Step 6 — Reports consolidation

Twelve PDF reports exist plus a BOQ Excel workbook. Six modules produce nothing downloadable at all — that is the real gap.

**Merge:** Utility Report into Water & Sanitation (same numbers). Quantity Report into BOQ (quantities are the unpriced half). Accessibility into Compliance. Fold Setbacks & Controls into Compliance and Apartment Planning into the Executive Summary.

**Add:** Construction Programme (phase table, critical path, floor cycle, IS 456 safety basis, cash-flow S-curve, resource histogram) · Feasibility & ROI (revenue, cost, margin, ROI, IRR, payback, break-even, monthly cash flow) · Site Analysis (terrain, flood, access, sun path, suitability) · Sustainability (green rating, embodied carbon m13, plantation plan m14, solar potential) · Optimisation Findings (current vs best vs change required, across all optimisers).

**Extend:** the IS/NBC Engineering Summary to include m13 and m14.

**Final set — 11 reports:** Executive Summary · Site Analysis · Compliance · IS/NBC Engineering Summary · Structural Design Basis · Water & Sanitation · Fire & Life Safety · Sustainability · BOQ & Quantities (PDF + Excel) · Cost & Feasibility · Construction Programme.

Add a **Download all** producing one merged PDF with a contents page. Update `REPORT_TITLES`, `build_pdf()` and the `REPORTS` list in `ReportsModule.jsx` together so nothing is orphaned.

**Done when:** eleven reports, every module represented, Download-all produces one merged PDF.

## Step 7 — Streaming and model routing

- Stream the chat response with server-sent events; render tokens as they arrive in `AptPanel.jsx`.
- Route light-tier questions to the fast model in the existing fallback chain; keep the strong model for derivations and clause work.
- The citation guard still runs on the completed text before the message is stored.

**Done when:** first word appears in under a second on a full-context question.

---

# Decisions already made — do not reopen

1. **Drag changes display order only.** Dependencies still set dates. Do not attempt to re-link dependencies from a drag.
2. **Cost overrides do not touch the BOQ.** The variance line reports the gap.
3. **IS 456 lags outrank every user input**, including a pinned date.

# Final output

1. Write `IMPLEMENTATION_REPORT.md` at the repo root: what shipped per step, files touched, every assumption taken with the value chosen, before/after APT timings, test and build status, and anything deferred with the reason.
2. Reply in chat with a condensed version — per-step status, assumptions, timings, build status, deferred items. Under 15 lines. No essays, no restating this brief, no pasted file contents.
