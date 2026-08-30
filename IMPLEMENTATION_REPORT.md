# Aptimizer — editable programme, reports, APT speed, module suggestions

Seven steps in three waves. `pytest` and `npm run build` green between waves; one commit
per step.

> The previous brief's report is preserved as `IMPLEMENTATION_REPORT_24_FEATURES.md`.

---

## Per-step status

| Step | What shipped | Files | Status |
|---|---|---|---|
| 1 | APT speed: intent gate, three context tiers, analysis + context caching | `backend/aptspeed.py` (new), `ai.py`, `server.py` | done |
| 2 | Module-aware suggestions: one generator per workspace module, cached per project version | `backend/aptsuggest.py` (new), `server.py`, `AptPanel.jsx`, `Workspace.jsx` | done |
| 3 | Override data model, inline name editing, drag reordering, task insertion fix | `backend/schedule.py`, `frontend/src/components/TaskRow.jsx` (new), `ProgrammeModule.jsx` | done |
| 4 | Editable start/finish dates as CPM pins, conflict reporting, IS 456 refusal | `backend/schedule.py` (`_forward`, `audit_scheduled_dates`) | done |
| 5 | Editable days, crew and cost with precedence; edit marks, per-row/phase/all reset, persistence | `schedule.py`, `TaskRow.jsx`, `ProgrammeModule.jsx`, `Workspace.jsx`, `server.py` | done |
| 6 | Reports: 12 → 11, five merged, five new, engineering extended, Download-all merged PDF | `backend/reports.py`, `server.py`, `ReportsModule.jsx` | done |
| 7 | SSE streaming chat, fast-model routing for light tiers | `ai.py` (`stream_markdown`), `server.py`, `AptPanel.jsx`, `lib/api.js` | done |

---

## APT timings — before and after

Wall time for the work in front of the model call; no provider invoked.

| Message | Tier | Before | After | Context before | Context after |
|---|---|---:|---:|---:|---:|
| `hi` | none | 366 ms | **0 ms** | 48,475 ch | **0** |
| `what can you do` | none | 371 ms | **0 ms** | 48,475 ch | **0** |
| `how big is this project` | light | 370 ms | **1 ms** | 48,475 ch | **654 ch** |
| `why is the base shear…, per clause` | full | 370 ms | 367 ms | 48,475 ch | 48,475 ch |

Repeat full-tier question on an unchanged project: **370 ms → 1 ms (514×)**.

**The brief's cache target was the wrong target, and profiling said so.** It asked to cache
`analyse()` and `analyse_engineering()`. Measured: `engine.analyse` 1 ms,
`analyse_engineering` 6 ms, `aptcontext.build` **384 ms** — of which **339 ms is the eleven
optimisers** it runs. Caching the two named calls saved about seven milliseconds of a
four-hundred millisecond path. The assembled context is cached as well, on the same key
with the same invalidation, and that is where the 514× comes from. Both caches are in.

A second thing the profiling surfaced: storing the chat thread bumped `updated_at`, which
is the cache key — so chatting invalidated the cache on every message and the cache would
have done nothing at all. The thread now saves without touching `updated_at`.

---

## Assumptions taken

| # | Where the brief left a choice | Value chosen | Why |
|---|---|---|---|
| 1 | Intent classification method | Whole-message regex, no model call | The brief says keywords first; a model call would add a network round trip to save a local one |
| 2 | Chit-chat matching | A *run* of tokens, not one | "ok thanks" and "ok got it" are as common as "ok"; single-token matching classified them as real questions |
| 3 | Full-tier trigger | ~90 domain terms, or any digit | A digit almost always means the user is quoting a number back |
| 4 | Cache key | `project_id:updated_at` | Already maintained, changes exactly when the design does |
| 5 | Cache bound | 32 entries, oldest evicted | A conversation convenience, not a store |
| 6 | Light-tier content | Identity, headline metrics, failing rules, cost, parking | 654 chars against 48,475 — enough for "how big is it", nothing more |
| 7 | Light tier and engineering | Never computed | The expensive half; computing then discarding would be the worst of both |
| 8 | Fast-model routing | Reorders the chain, never replaces it | If the fast model is down the strong one still answers |
| 9 | Suggestions cache | Per project version per module | The panel refetches on every module switch |
| 10 | Suggestion fallback | Top up from the general set below 3 | A thin project must never show a blank empty state |
| 11 | `3d` module suggestions | Reuses the Apartment Planning generator | Same underlying numbers |
| 12 | Override merge semantics | Merge, not replace | Editing crew must not silently discard a date pinned earlier |
| 13 | Clearing a date input | `null` deletes the key | "Unpin" has to be expressible, or a pin can never be removed |
| 14 | Crew edited alone | Days recompute from quantity ÷ (output × crew) | The arithmetic that makes this an engine, not a spreadsheet |
| 15 | Days and crew both edited | Days wins; crew moves labour cost only | The brief's precedence |
| 16 | Days edit feedback | Implied output/day shown under the row | So the user sees the productivity they just assumed |
| 17 | Pin later than earliest start | Honoured, downstream moves | This is how a user models a slip |
| 18 | Pin earlier than dependencies allow | Refused, predecessor and shortfall named | Silent acceptance would be a lie about the plan |
| 19 | Pin across a code-mandated lag | Refused, clause quoted | Decided and not reopened |
| 20 | Second safety audit | New `audit_scheduled_dates` on realised dates | `audit_safety` checks lags and runs before the CPM; a pin is applied to dates |
| 21 | Unparseable date | Warning, generated date kept | Never crash a programme on a typo |
| 22 | Drag ordering | Writes `order` to every task in the phase; display only | Decided and not reopened |
| 23 | New task "Starts after" | Defaults to the last task in the phase | Blank linked it to project start, so it landed among the day-zero tasks |
| 24 | New task position | `order = phaseRows.length` | Lands at the end of its phase, where the form implies |
| 25 | Override persistence | `project.schedule`, added to the allowed patch fields | A snapshot must reproduce the approved programme, not the generated one |
| 26 | Merged report ids | Still resolve to the absorbing report | An old bookmark should land on the numbers, not a 400 |
| 27 | Download-all method | Concatenate with `pypdf` (already installed) | Rebuilding every section inline would leave two definitions to keep in step |
| 28 | One report failing in Download-all | Skipped; the other ten still produced | One bad section should not cost the whole set |
| 29 | Streaming transport | `fetch` + SSE, not `EventSource` | EventSource cannot POST, and the conversation goes up with the request |
| 30 | Streaming retry | None mid-stream; falls back only if nothing was emitted | Restarting mid-answer would rewrite text already on screen |
| 31 | Streaming auth | `authHeaders()` exported for the raw fetch | axios adds the bearer by interceptor; fetch would have 401'd |
| 32 | Citation guard on streams | Runs on the completed text before storing | Tokens arrive unverified — that is what streaming is — but nothing actionable skips the guard |

---

## Reports: the final eleven

Executive Summary · Site Analysis · Compliance · IS/NBC Engineering Summary · Structural
Design Basis · Water & Sanitation · Fire & Life Safety · Sustainability & Carbon · BOQ &
Quantities (PDF + Excel) · Cost & Feasibility · Construction Programme.

Merged, with the numbers carried into the survivor: Utility → Water, Quantity → BOQ,
Accessibility → Compliance, Setbacks & Controls → Compliance, Parking → Executive Summary.
New: Site Analysis, Sustainability, Cost & Feasibility (feasibility half), Construction
Programme. Extended: the engineering summary now carries m13 carbon and m14 plantation.

Download-all produces a single 22-page PDF behind a generated contents page with real page
numbers.

---

## Test and build status

| Gate | Result |
|---|---|
| `pytest` | **546 passed** (473 before this brief) |
| `npm run build` | exit 0, pre-existing `exhaustive-deps` warnings only |
| New tests | 114 across `aptspeed_test` (41), `overrides_test` (20), `reports_test` (36), `stream_test` (13), plus 4 route tests |

Excluded from the gate and untouched, as before: `gis_test.py`, `engineering_test.py`,
`rbac_v2_test.py`, `backend_test.py` — all four hit a remote preview URL rather than local
code, and all four failed the same way before this work.

Tests worth naming, because they hold decisions rather than behaviour:

- `test_a_pin_that_would_strike_props_early_is_refused` — the one instruction the engine
  must never follow.
- `test_the_date_audit_catches_a_violation_the_forward_pass_missed` — belt and braces on
  the same rule, via a hand-forced violation.
- `test_editing_crew_alone_recomputes_days_from_the_quantity` — if this fails, the tool is
  lying about productivity.
- `test_chat_route_verifies_citations_on_every_generated_answer` — reads the route source
  to prove no tier skips the guard.
- `test_a_merged_id_still_resolves` — merging removed documents, not numbers.

---

## A bug the second HTTP test module found

Adding `stream_test.py` broke `routes_smoke_test.py` — thirteen errors, all
`RuntimeError: Event loop is closed`, and only when the two ran together. `server.db` is a
motor client created at import; motor binds an event loop the first time it is used and
keeps it. Each module had its own `TestClient`, so the first module's loop closed on exit
and left motor holding a corpse.

Fixed with one session-scoped client in `tests/conftest.py` that every HTTP test shares,
plus a `mongo` fixture using sync pymongo for setup (calling motor synchronously returns an
un-awaited coroutine, inserts nothing, and every request then 404s on an id that was never
real). Verified in the exact order that used to fail, and serially.

Worth recording because the failure only appears with two HTTP test modules in one process:
individually both files passed, which is the shape of bug that gets committed.

---

## Deferred, with the reason

**Only the provider call in streaming is unverified.** No AI key is configured here, so
`stream_markdown` has never run against a real provider, and the "first word in under a
second" target cannot be measured. Everything between the provider and the browser now is
tested, with a stubbed provider: delta ordering and reassembly, the done event and the
model it names, thread storage, both failure paths (a stream that dies before any token
falls back; one that dies mid-answer reports rather than restarting and rewriting text the
reader has seen), the SSE headers, and tier-to-model routing. Most importantly
`test_the_citation_guard_runs_on_the_streamed_answer` proves the guard runs on streamed
text, which was the one rule that could not be allowed to slip.

**No visual verification of any UI in this brief.** The workspace is behind authentication
and no credentials were used. The editable task table, drag reordering, pin markers, the
streaming panel and the Download-all button all compile and their data contracts are
checked against real backend output, but none has been rendered in a browser. The editable
table is the largest UI change here and the one to look at first.

**Drag-and-drop uses the native HTML5 API**, not a library, per the no-new-dependencies
rule. It works with a mouse; it is not touch-accessible and has no keyboard equivalent.
Worth revisiting if the programme table is used on a tablet.

**Optimisation Findings — resolved, not deferred.** The brief lists it under "Add" but
then fixes the final set at eleven without it. Both halves now hold: the content ships as a
section inside Cost & Feasibility (current, best found, change required, per optimiser),
which is where optimiser findings belong, and the document count stays at eleven.
