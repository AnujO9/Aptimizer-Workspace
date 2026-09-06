# Calculation Reference — Corrections

Four corrections to *Aptimizer Calculation Reference*, found by checking the document
against the code it transcribes, which is the check page 1 asks a reader to make.

**None of them is a wrong number.** 82 constants across pages 3–15 and every formula
spot-checked — Rankine, `P_service = P_u/1.5`, `B = √A_req + 0.05`, the IS 10262 coarse
aggregate adjustment, the three Sa/g branches, the cost adder sequence, the S-curve and IRR
bounds — match the source exactly. Two things that looked like defects are not: `math.sin`
is fed `math.radians(soil["phi"])`, and the `min(…, 2.5)` cap on the design spectrum is
defensive and can never bind, because the hyperbolic branch begins exactly at 2.5.

What follows is the wording to paste in.

---

## 1. Page 4, Module 2 — the fundamental period is understated

The document gives the two expressions separately. The code returns the **shorter of the
two** for infilled and wall systems, which is the path that runs by default —
`frame_type` defaults to `brick_infill`. A reader hand-checking base shear against the
document would use the wrong period.

**Replace both rows with three:**

| Quantity | Formula as implemented | Note |
|---|---|---|
| Fundamental period, bare frame | `Ta = 0.075 H^0.75` | IS 1893 Cl. 7.6.2(a). Used as given only when `frame_type` is `bare_frame`. |
| Fundamental period, infilled frame | `Ta = min(0.075 H^0.75, 0.09 H / sqrt(d))` | Cl. 7.6.2(b); `d` = base dimension, taken as `sqrt(footprint)`. The shorter period governs, because a shorter period gives the larger design base shear. **This is the default path.** |
| Fundamental period, wall system | `Ta = min(0.075 H^0.75, 0.09 H / sqrt(d))` | Cl. 7.6.2(d) is not implemented — see Known Simplifications. The output labels this result "wall system approximation". |

*Source: `iscodes.seismic_period`.*

---

## 2. Page 16 — a simplification is missing

The code declares this one in its own docstring and labels it in the returned result, but
page 16 does not list it. It belongs there, because it is precisely the class of thing that
page exists to declare before an examiner finds it.

**Add:**

> **Shear-wall fundamental period.** IS 1893 Cl. 7.6.2(d) gives the period of a shear wall
> system in terms of the wall area `Aw`. The platform does not model shear wall geometry,
> so it substitutes the infilled-frame expression and reports the result as a wall system
> approximation. The substitution is not guaranteed to be conservative for a wall-dominant
> building; check the period before relying on the base shear it produces.

---

## 3. Page 5, Module 3 — `q` is undefined

The Rankine row uses `q` without saying what it is. It is not the SBC, and the definition
is not something a reader would reconstruct.

**Replace the Note column of "Minimum depth (Rankine)" with:**

> Minimum 0.5 m. `q = min(SBC, 4 × column load / (bay_x × bay_y))` — the lesser of the
> soil's safe bearing capacity and the pressure the column grid imposes. `φ` is converted
> to radians before use.

*Source: `engineering.m3_foundation`.*

---

## 4. Pages 7 and 10 — the fire figures are now version-keyed

Since the code-version work, the three NBC fire constants are no longer unconditional.
They are keyed on the project's `code_version`, which defaults to `nbc2016`. The document's
figures remain correct **for that default** — but it no longer says so, and that
qualification is the entire point of the change.

### Page 7, "Constants used"

| Constant | Value | Source |
|---|---|---|
| High-rise trigger | 15 m *(NBC 2016)* | NBC Part 4. Held in `FIRE_WATER_BY_VERSION`, not as a literal — this is the value SP 7:2026 is most reported to move. |
| Fire reserve in sump | 25 000 L above the trigger *(NBC 2016)* | NBC Part 4. Under `sp7_2026` this is `UNREAD` and no reserve is added to the sump. |
| Static fire storage | 50 000 L above the trigger *(NBC 2016)* | NBC Part 4 Table 7. Same version key. |

### Page 7, "Sump volume" row

**Note becomes:**

> `V_sump = Q + fire reserve`. The reserve is 25 000 L above the high-rise trigger under
> NBC 2016. When the active code version has not been read, nothing is added and the output
> says so rather than reporting a sump as though the reserve were zero.

### Page 10, "Static water" row

**Note becomes:**

> NBC Table 7, under NBC 2016. Under SP 7:2026 the module refuses to check rather than
> reporting a figure.

### Page 10, "Constants used" — add a row

| Constant | Value | Source |
|---|---|---|
| `code_version` | `nbc2016` (default) | `FIRE_BY_VERSION`. Under `sp7_2026` all ten fire thresholds are `UNREAD`, the module returns `unchecked` with no score, and it names the values it could not read. |

---

## One thing to recount

Page 1 states "14 modules, 106 formulas and 72 constants". The constant count has moved
with the version tables. Recount it from the source rather than adjusting it by hand —
that number is the sort of thing this document exists to keep honest.
