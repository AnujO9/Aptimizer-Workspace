# Aptimizer — Plan of action

Seven steps, three waves. Each step is one Claude Code session with a copy-paste prompt below.
Full detail for every step is in `Aptimizer_Build_Spec.pdf` — the prompts reference it by section.

Standing rules for every session:
- `grep -n` to locate, `sed -n 'X,Yp'` to read only what you need, targeted edits. Never read a whole file for a small change; never re-read a file you just edited; never pull `node_modules`, `venv`, lockfiles or `frontend/build/` into context.
- Finish with `cd backend && python -m pytest -q` and `cd frontend && npm run build` both green. Commit once, do not push.
- Follow existing patterns. No new dependencies. Do not touch `frontend/build/`.

---

## Wave 1 — Make APT feel like a product (ship this week)

Smallest changes, biggest perceived difference. Nothing here touches the programme table, so it
carries no risk to the scheduling engine.

### Step 1 — APT speed
**Prompt:**
> Read `Aptimizer_Build_Spec.pdf` Part C. Implement fixes 1, 2 and 3 only — analysis caching keyed on the project's `updated_at`, an intent gate so greetings and small talk skip project context entirely, and three context tiers (none / light / full) routed on keywords before any model call. Do not implement streaming or model routing yet. `citations.verify()` must still run on every full-tier answer. Measure and report: time and context size for "hi" versus a full engineering question, before and after.

**Done when:** "hi" answers in under a second with near-zero context; a clause question still answers fully with citations verified.

### Step 2 — Module-aware suggested questions
**Prompt:**
> Read `Aptimizer_Build_Spec.pdf` Part D. Add a `module` parameter to `GET /ai/chat/suggestions` and build one suggestion generator per module using the table in D2, drawing on each module's real computed values the way the existing generator does. `AptPanel` already knows the active module — pass it through and refetch on change. Fall back to the current general set when a module has nothing notable. Cache per module per project version.

**Done when:** switching modules changes the questions; no module shows another module's questions.

---

## Wave 2 — The editable programme table (the main body of work)

Steps 3–5 are one continuous piece of work on the same component and data model. Ship them
together — a half-editable table is more confusing than a read-only one.

### Step 3 — Editable task names and reordering
**Prompt:**
> Read `Aptimizer_Build_Spec.pdf` Part A, sections A1–A4. Add the `task_overrides` object to the schedule config exactly as specified in A2. Implement inline task-name editing and drag-to-reorder within a phase, writing `name` and `order` overrides. Add the note under the table explaining that row order is display order, not schedule order. Also apply the A4 fix: default the Add-task "Starts after" dropdown to the last task in the chosen phase instead of blank, keeping the blank option labelled "Project start", and insert a newly added task at the position the user dropped it rather than letting date-ties decide.

**Done when:** names persist across a re-plan; dragging reorders within a phase only; a new task lands where the user put it.

### Step 4 — Editable start and finish dates
**Prompt:**
> Read `Aptimizer_Build_Spec.pdf` Part A, section A5. Replace the start and finish cells with date inputs using the same `<Input type="date">` control as the programme start/finish fields. A set date pins the task as a scheduling constraint; clearing it unpins and restores the generated date. Show a pin marker on pinned rows. Downstream tasks must move when a task is pinned later. If a pinned date is earlier than dependencies allow, show the conflict on the row naming the blocking predecessor and the shortfall in days. IS 456 curing and prop-removal lags must be enforced against user-entered dates exactly as `audit_safety()` enforces them against generated ones — refuse and explain, never accept silently.

**Done when:** pinning a date moves downstream work; an impossible pin is refused with the blocking predecessor named; no pin can violate an IS 456 lag.

### Step 5 — Editable days, crew and cost
**Prompt:**
> Read `Aptimizer_Build_Spec.pdf` Part A, sections A6–A7. Make the Days, Crew and Cost cells editable, writing to `task_overrides`. Apply the precedence rule exactly as stated: a pinned date beats an edited Days value, which beats an edited Crew value, which beats the generated figure. Editing Crew alone must recompute Days from quantity ÷ (output × crew); editing Days alone must override that derivation and show the implied output rate as a hint. Cost overrides roll up to phase and project totals and the cash-flow curve but must not touch the BOQ. Add the precedence legend, per-row and per-phase reset, an edited-cell marker, an edit count in the section header, and "Reset all edits". Overrides must persist with the project and travel with a saved version.

**Done when:** the legend matches actual behaviour; edited cells are visually marked; reset restores generated values; a saved version carries the edits.

---

## Wave 3 — Reports and polish

### Step 6 — Reports consolidation
Independent of everything above; can run in parallel with Wave 2 if you have the capacity.

**Prompt:**
> Read `Aptimizer_Build_Spec.pdf` Part B. Consolidate to the eleven reports in B3. Merge Utility into Water & Sanitation, Quantity into BOQ, and Accessibility into Compliance. Add the five missing reports: Construction Programme, Feasibility & ROI, Site Analysis, Sustainability (green rating + embodied carbon m13 + plantation plan m14 + solar potential), and Optimisation Findings. Extend the IS/NBC Engineering Summary to include m13 and m14. Fold Setbacks & Controls into Compliance and Apartment Planning into the Executive Summary. Add a "Download all" that produces one merged PDF with a contents page. Update `REPORT_TITLES`, `build_pdf()` and the `REPORTS` list in `ReportsModule.jsx` together so nothing is orphaned.

**Done when:** eleven reports, every module represented, Download-all produces one merged PDF.

### Step 7 — Streaming and model routing
**Prompt:**
> Read `Aptimizer_Build_Spec.pdf` Part C, fixes 4 and 5. Stream the chat response with server-sent events and render tokens as they arrive in `AptPanel.jsx`. Route light-tier questions to the fast model in the existing fallback chain, keeping the strong model for derivations and clause work. The citation guard must still run on the completed text before the message is stored.

**Done when:** first word appears in under a second on a full-context question.

---

## Order rationale

Wave 1 first because it is small, self-contained and the most visible — APT stops feeling broken.
Wave 2 second because it is the largest and riskiest change, and it touches the one part of the
system with a genuine safety constraint. Step 6 is independent and can slot in anywhere. Step 7 is
last because streaming is polish that only pays off once the server-side work in Step 1 has already
cut the latency underneath it.

## Two decisions to make before Step 3

1. **Drag semantics.** As specified, dragging changes display order only — dependencies still decide
   the dates. If you want dragging to actually re-link what a task waits for, that is a much larger
   feature and needs its own design. Decide now, because it changes Step 3's scope.
2. **Cost override and the BOQ.** As specified, cost edits move programme totals but never the BOQ,
   and the existing variance line reports the gap. If you want them reconciled instead, that is a
   separate piece of work in the cost module.
