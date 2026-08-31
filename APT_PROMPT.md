# Build APT — the in-app assistant for Aptimizer

Repo root: `D:\Workspace`. FastAPI + MongoDB backend (`backend/`), React 19 + craco + Tailwind + shadcn frontend (`frontend/`).

Build one feature: a persistent chat assistant named **APT**, reachable from every workspace tab, that answers from the current project's live computed state and cites real IS/NBC clauses.

## Constraints

1. **Token discipline.** `grep -n` to locate, `sed -n 'X,Yp'` to read only the range you need, then a targeted edit. Never read a whole file for a small change. Never re-read a file you just edited. Never pull `node_modules`, `venv`, lockfiles or `frontend/build/` into context.
2. **Stable build.** Finish with `cd backend && python -m pytest -q` and `cd frontend && npm run build` both green. Commit once at the end, do not push.
3. **Follow existing patterns.** The AI route shape is already established — see `/ai/cost` and `/ai/finance` in `server.py`. The frontend AI pattern is `components/AiPanel.jsx`. Do not introduce a new state library, router pattern or styling approach.
4. **No new dependencies.**

## What already exists — reuse, do not rebuild

- `backend/ai.py` — multi-provider LLM (Gemini / Grok / Groq / Emergent) with model fallback and retries. `PROMPTS = {...}` holds one system prompt per report kind; `generate_markdown()` runs a call; `context_block()` serialises a context dict to fenced JSON, capped at `MAX_CONTEXT_CHARS`. `provider()` backs `/ai/status`.
- `backend/server.py` — existing AI routes: `/ai/compliance`, `/ai/report`, `/ai/cost`, `/ai/engineering`, `/ai/finance`, and `GET /ai/compare`. All share one shape: load project → build a `context` dict → `await _run_ai(kind, context, store_at=..., project_id=..., user=..., activity=...)`.
- `backend/engine.py` — `analyse(project)` returns areas, quantities, BOQ, cost, parking, utilities, compliance.
- `backend/engineering.py` — `analyse_engineering(project, base)` returns 12 modules (`m1_structural_loads` … `m12_grid`), each with `outputs`, `derived`, `recommendation`, `code_refs`.
- `backend/finance.py` — `analyse()` returns revenue, profit, margin, ROI, IRR, payback, break-even.
- `backend/schedule.py` — `plan_schedule(project, analysis, overrides, summary=True)` returns programme headline figures cheaply.
- `backend/gis.py` — site indices, terrain, flood, access, sun path.
- `backend/iscodes.py` — **the clause registry**, `clause(key)`. This is the source of truth for citations.
- `compare_versions()` in `server.py` — 18-metric before/after between two saved revisions.
- `frontend/src/components/AiPanel.jsx` — how an AI endpoint is wired, including how it disables itself with a reason when no provider is configured.

Carbon, solar yield, waste and the optimiser features do **not** exist yet. Build APT's context assembly so a missing section is simply absent, not an error — those will be added later.

## Backend

**Route.** `POST /projects/{project_id}/ai/chat`, body `{messages: [{role, content}]}`. Persist the thread on the project document. Cap stored history; send only the last N turns upstream (start with 12).

**System prompt.** Add a `"chat"` entry to `ai.PROMPTS` using the APT prompt at the end of this file, verbatim.

**Context assembly.** Build a compact `context` dict per message. Extract the shared parts of the existing `/ai/report`, `/ai/engineering`, `/ai/cost` and `/ai/finance` context builders into helpers and reuse them — do not duplicate that code. Include:

- project identity, plot summary, tower and unit configuration
- `analyse_engineering()` module `outputs` and `derived` values
- compliance results, per rule, with pass/fail and the clause key
- BOQ summary and cost breakdown
- finance figures from `finance.analyse()`
- programme headline from `plan_schedule(..., summary=True)`
- GIS indices
- revision diff from `compare_versions` when a previous version exists — reuse it, do not recompute
- the clause registry entries referenced anywhere in the above

**Send computed outputs and derived values, never raw geometry.** No vertex arrays, no full activity lists, no per-floor layout JSON, no cash-flow week arrays. Round numbers on the way in. Target well under 10k tokens per message and log the serialised size in dev so it can be watched.

**Citation guard — the most important part of this build.** An LLM will confabulate IS/NBC clause numbers confidently. Two mechanisms:

1. Pass the relevant `iscodes.clause()` entries into context and instruct APT to cite only from those (already in the system prompt).
2. After the response returns, extract citation-shaped strings (`IS \d+`, `NBC Part \d+`, `Cl. [\d.]+`) and resolve each against the registry. Any that does not resolve gets flagged inline in the returned payload as unverified — do not silently ship it, and do not delete it either. Return the list of unverified citations alongside the text so the UI can mark them.

## Frontend

`frontend/src/components/AptPanel.jsx` — a slide-over panel, not a tab, so APT is available from every module.

- Trigger button in the workspace chrome (`ProjectNav.jsx` or `TopBar.jsx`), visible on every tab.
- Message list with the assistant's markdown rendered — numbered lists and formula blocks matter, since derivations come back as numbered steps.
- Input with Enter to send, Shift+Enter for newline. Per-message copy button.
- Unverified citations rendered with a visible marker and a tooltip explaining it could not be matched to the clause registry.
- An empty panel shows 3–4 suggested questions generated from the current project state — a failing compliance rule, the largest BOQ line, the completion date. Never a blank box.
- When `/ai/status` reports no provider, disable with the reason, exactly as `AiPanel.jsx` does.
- Streaming is not required.

## Done when

- `POST /ai/chat` returns a grounded answer against a real project, and the thread survives a page reload.
- A question about a failing compliance rule returns the correct clause, and a deliberately unanswerable clause question returns an admission rather than an invented citation.
- Context payload size is logged and sits under budget.
- pytest green, `npm run build` green, APT reachable from every tab.

Report at the end in under 10 lines: what shipped, files touched, test and build status, anything deferred.

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
construction programme, feasibility and ROI figures, and the diff between the
current and previous revision if one exists. Some sections may be absent for a
given project — if data you need is not present, say so rather than assuming a
value.

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

Changes from the original text: the context paragraph now matches what the app actually computes today and tells APT to say so when a section is missing, and the citation rule binds it to the supplied clause registry rather than its own memory. Everything else is unchanged.
