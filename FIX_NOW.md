# Aptimizer — five corrections

Repo root: `D:\Workspace`. FastAPI + MongoDB backend (`backend/`), React 19 + craco + Tailwind + shadcn frontend (`frontend/`).

Five fixes. Run in order, end to end. Where a choice is open, take the option named here, log it, and keep going. Report once at the end.

## Standing rules

1. **Token discipline.** `grep -n` to locate, `sed -n 'X,Yp'` to read only the range you need, then a targeted edit. Never read a whole file for a small change. Never re-read a file you just edited. Never pull `node_modules`, `venv`, lockfiles or `frontend/build/` into context. Do not paste file contents into replies.
2. **Build gate.** After each fix: `cd backend && python -m pytest -q` and `cd frontend && npm run build`. Both green before moving on.
3. **Commit after each fix**, one line each. Do not push.
4. Follow existing patterns. No new dependencies. Do not touch `frontend/build/`.

---

## Fix 1 — Setbacks appear in two places and can disagree

**The problem, precisely.** Setbacks are editable in two modules under the Site group:

- `frontend/src/modules/PlotModule.jsx` holds local state `setbacks = {default, front, rear, side}` (around line 28), renders editable `NumField`s for each (around line 180), and sends those values to the site-layout envelope call. **These are the values the layout engine actually uses.**
- `frontend/src/modules/DevControlsModule.jsx` has a "Setbacks" section plus "Recommended controls", derived from plot area and road width via `backend/siteplan/devcontrols.py` (`front_setback_for_plot`, `open_space_for_height`, `max_height_from_road`, `recommend`).

So a user can set a value in Setbacks & Controls, see a different value in Plot & Site, and get an envelope built from the second one. That is a correctness bug, not just duplication.

**The fix — one owner, one stored value.**

- Setbacks become a **single stored field on the project document**, not local component state. Both modules read the same value.
- **Setbacks & Controls owns editing.** It knows the statutory minimums, so it shows, for each edge: the statutory minimum from `devcontrols.py`, the applied value, and a validation error when the applied value is below the minimum.
- **Plot & Site displays them read-only** in the envelope section — the numbers used to build the envelope shown as plain values with a "Edit in Setbacks & Controls" link. Remove the editable `NumField`s from `PlotModule`.
- The envelope call keeps taking setbacks as input; it just reads them from the project document instead of local state.
- Migration: on load, if the project has no stored setbacks, seed from the current `PlotModule` defaults so existing projects do not change behaviour.

**Done when:** setbacks are editable in exactly one place, the envelope always uses that value, and a value below the statutory minimum is rejected with the governing rule named.

---

## Fix 2 — FAR / FSI calculation is opaque

**The problem.** The Engineering and Plot modules show FAR and FSI as bare numbers. A user cannot see what went into them, why the two differ, or how far they are from the permissible limit.

**The fix — show the derivation, not just the result.** Wherever FAR/FSI is displayed, add an expandable calculation panel showing, in order:

1. **Formula**, stated symbolically: `FAR = total built-up area ÷ plot area`.
2. **Inputs**, each with its own value and unit: plot area, gross built-up area, and per-tower built-up contribution.
3. **Deductions**, itemised — every area excluded from the FSI count (parking, service floors, stilts, refuge areas, whatever `engine.area_metrics()` actually excludes), each with its value and the reason it is excluded.
4. **Substitution**, arithmetic shown: `FAR = 24,500 ÷ 8,000 = 3.06`.
5. **Permissible vs achieved**, with headroom in both ratio and m², and the governing control named.
6. **FAR vs FSI** — state plainly which is which in this app. In most Indian practice they are the same ratio; if this app computes them differently, the panel must show exactly where the two calculations diverge. If they are identical, say so and consider showing one figure with both labels rather than two numbers that look like they should differ.

Read `engine.area_metrics()` and report what it actually does before writing the panel — the panel must reflect the real computation, never a plausible-looking one. If FAR and FSI are currently computed identically, say so in your final report.

**Done when:** a user can trace the displayed FAR from plot area and built-up area through every deduction to the final ratio, and see how much headroom remains.

---

## Fix 3 — Reports listed in menu order

**The fix.** Reorder the reports list in `frontend/src/modules/ReportsModule.jsx` to follow the module group order in `frontend/src/pages/Workspace.jsx`, with a group heading above each block:

- **Site** — Site Analysis (GIS), Plot & Setbacks
- **Design** — Apartment Planning, Parking
- **Engineering** — IS/NBC Engineering Summary, Structural Design Basis, Water & Sanitation, Fire & Life Safety, Sustainability
- **Cost & Programme** — BOQ & Quantities, Cost & Feasibility, Construction Programme
- **Deliver** — Compliance, Executive Summary

Group headings use the same labels as the navigation, so the reports page reads as a mirror of the menu. Executive Summary sits last under Deliver as the roll-up of everything above it.

**Done when:** report order matches menu order group for group, with headings.

---

## Fix 4 — Reports must contain all computed detail, per tower

**The problem.** Reports summarise where they should itemise. A per-tower project shows blended totals, so a reader cannot see which tower drives which number.

**The fix.** Every report that covers a multi-tower quantity gains a per-tower breakdown table, not just a project total:

- **Structural** — per tower: floors, height, footprint, plate area, column grid, governing load, base shear, foundation type and size.
- **BOQ & Quantities** — per tower: concrete, steel, brick, tile, paint quantities and their cost contribution, with the project total as a footer row.
- **Cost & Feasibility** — per tower: cost, cost per m², cost per unit, saleable area, revenue contribution.
- **Construction Programme** — per tower: start, finish, duration, floor cycle, and which tower sits on the critical path.
- **Water & Sanitation** — per tower: population, demand, tank sizing.
- **Compliance** — per tower where a rule is evaluated per tower (height, setback, coverage).
- **Sustainability** — per tower: embodied carbon and its share of the project total.

Rules that apply to all of these:

- Every table states its **units in the header**, never in the cells.
- Every derived figure carries the **formula or source** in a footnote — the reader must be able to reproduce it.
- Where a figure comes from a code clause, cite the clause.
- Totals rows must actually equal the sum of their parts. If a total is not the sum (a shared cost apportioned, say), label it and explain why in one line.

**Done when:** every multi-tower figure in every report is broken down per tower with units and a traceable derivation.

---

## Fix 5 — Cost does not change when the programme is compressed

**This is a real bug, and here is exactly where it lives.**

In `backend/schedule.py`:

```
def duration_days(quantity, output_per_day, crew):
    rate = output_per_day * max(crew, 1)
    return max(1, ceil(quantity / rate))

# inside add():
wd = duration_days(qty, out, crew)
labour_cost = wd * crew * wage[...]
```

Substituting: `labour_cost ≈ (qty / (out × crew)) × crew × wage = (qty / out) × wage`.

**The crew term cancels.** Doubling the crew halves the days and doubles the headcount, so labour cost lands on the same number. Material cost is `qty × rate` and does not move either. That is why pulling the finish date earlier — which makes `solve_for_target()` add labour — leaves the budget unchanged. The model currently says acceleration is free, which is wrong in the direction that matters commercially.

**The fix — a real time-cost curve.** Cost must rise when the programme is compressed *and* when it is extended. Implement three mechanisms:

**(a) Productivity derating on compression.** Output per head falls as more crews work the same front — congestion, shared hoists, shared pour fronts. Apply an efficiency factor to output when the crew multiplier exceeds 1:

```
effective_output = output_per_day × efficiency(multiplier)
```

with `efficiency` decreasing as the multiplier rises (1.0 at 1×, roughly 0.85 at 2×, roughly 0.72 at 3×). Days are then computed from the derated output, so doubling the crew no longer halves the duration and labour cost rises. Put the curve in one named constant table with a comment explaining it, so it can be tuned.

**(b) Acceleration premium on wages.** Compression beyond the natural duration means overtime and shift work. Apply a wage premium that scales with the multiplier — for example 0% at 1×, rising to 25–35% at the labour ceiling. Report it as a separate cost line called "Acceleration premium" so the user sees what speed cost them.

**(c) Time-related preliminaries on extension.** A longer programme costs more even with no extra labour — site establishment, supervision, plant hire, temporary works and finance all run per month. Add a monthly preliminaries rate applied over the programme duration, so pushing the finish date later raises cost too. `engine.py` already has an overhead and profit concept — reuse its rate structure rather than inventing a parallel one.

**The resulting behaviour, which you must verify:** cost is at its minimum near the naturally derived duration and rises in both directions — steeply when compressed (premium plus lost productivity), gently when extended (preliminaries). Add a test asserting exactly that: a compressed target costs more than the baseline, an extended one costs more than the baseline, and the baseline is the cheapest of the three.

**Surface it in the UI.** In the Programme module, when a target finish date is set, show the cost delta against the baseline programme alongside the existing crew-change summary — "finishing 45 days earlier adds ₹62 L: ₹38 L acceleration premium, ₹24 L lost productivity". The user is being asked to trade money for time and must be able to see the price.

**Done when:** moving the finish date earlier increases cost, moving it later increases cost, the baseline is cheapest, the breakdown is visible in the UI, and a test locks the behaviour in.

---

## Final output

1. Write `IMPLEMENTATION_REPORT.md` at the repo root: what changed per fix, files touched, every assumption with the value chosen (especially the efficiency curve, premium and preliminaries rates in Fix 5), what `engine.area_metrics()` actually computes for FAR and FSI, test and build status, anything deferred.
2. Reply in chat with a condensed version under 15 lines. No essays, no restating this brief, no pasted file contents.
