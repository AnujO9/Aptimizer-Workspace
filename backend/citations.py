"""Resolve IS/NBC citations in model output against the real clause registry.

Models state clause numbers with total confidence and get them wrong often enough that an
unchecked citation is worse than none: a plausible "IS 456 Cl. 26.5.1.1" sends an engineer
to a clause that does not say what they were told it says, and the app's authority is what
made them believe it.

So every citation-shaped string in a reply is extracted and looked up. Three outcomes:
  * resolved   -- the code and clause both appear in iscodes.CLAUSES
  * code_only  -- the standard is real and in the registry, the clause number is not
  * unverified -- neither matches anything the app knows

Deleting the bad ones silently would be worse, not better: the reader would see a clean
answer with a hole in it. They are returned alongside the text so the UI can mark them,
and the reader can see exactly which reference to check before relying on it.
"""
import re
from typing import Any, Dict, List

import iscodes as C

# "IS 456:2000", "IS 875 (Part 3):2015", "NBC Part 4", "Cl. 7.6.2", "Clause 23.2.1",
# "Table 2". Deliberately loose on the standard number and strict on shape -- a false
# positive costs one lookup, a miss ships an unchecked citation.
_STANDARD = re.compile(
    r"\b(?:IS|SP)\s*[:\s]?\s*(\d{2,5})\s*(?:\(\s*Part\s*(\d+)\s*\))?\s*(?::\s*(\d{4}))?",
    re.IGNORECASE)
_NBC = re.compile(r"\bNBC\b[^.,;)\n]{0,40}?Part\s*(\d+)", re.IGNORECASE)
# The designation is usually numeric ("Cl. 7.6.2", "Table 2"), but annexes are
# lettered ("Annex E") and missing those made real registry entries fail their own
# check. The single-letter alternative is case-sensitive via (?-i:) -- under
# IGNORECASE it would otherwise match the "o" in "Table of contents".
_CLAUSE = re.compile(r"\b(?:Cl\.?|Clause|Table|Fig\.?|Figure|Annex(?:ure)?)\s*"
                     r"([A-Z]?[\d]+(?:\.\d+)*[a-z]?|(?-i:[A-Z])\b)", re.IGNORECASE)


def _base(code: str) -> str:
    """'is1893p1' -> 'is1893'. Engineers write "IS 1893:2016" as often as
    "IS 1893 (Part 1):2016", and treating the shorter form as unverifiable would flag
    correct citations -- which discredits the flag itself, and then the ones that matter
    get ignored too.

    IS codes only. An NBC part is not an optional refinement of the standard, it is which
    volume you are in -- collapsing 'nbcp47' to 'nbc' would wave through a part that does
    not exist (the NBC has 12).
    """
    if not code.startswith("is"):
        return code
    return re.sub(r"p\d+$", "", code)


def _registry() -> Dict[str, Any]:
    """Everything the app can vouch for, indexed for lookup.

    Indexed twice: by the exact code and by the code with its part number stripped, so a
    citation that omits the part still resolves against the part the registry holds.
    """
    codes, clauses, pairs = set(), set(), set()
    for entry in C.CLAUSES.values():
        code = _norm_code(entry["code"])
        codes.add(code)
        codes.add(_base(code))
        for cl in _all_clauses(entry.get("clause", "")):
            clauses.add(cl)
            pairs.add((code, cl))
            pairs.add((_base(code), cl))
    for entry in getattr(C, "CODE_LIBRARY", []):
        for field in ("code", "standard", "title"):
            v = entry.get(field)
            if isinstance(v, str):
                for m in _STANDARD.finditer(v):
                    n = _norm_code(m.group(0))
                    codes.add(n)
                    codes.add(_base(n))
    return {"codes": codes, "clauses": clauses, "pairs": pairs}


def _norm_code(text: str) -> str:
    """'IS 875 (Part 3):2015' and 'IS 875 Part 3' both normalise to 'is875p3'."""
    m = _STANDARD.search(text or "")
    if m:
        num, part, _year = m.group(1), m.group(2), m.group(3)
        return f"is{num}" + (f"p{part}" if part else "")
    n = _NBC.search(text or "")
    if n:
        return f"nbcp{n.group(1)}"
    return (text or "").strip().lower().replace(" ", "")


def _norm_clause(text: str) -> str:
    m = _CLAUSE.search(text or "")
    return m.group(1).lower().rstrip(".") if m else ""


def _all_clauses(text: str) -> List[str]:
    """Registry entries often carry two references -- "Table 3 / Annex E", "Cl. 6.4.2 /
    Fig. 2". Indexing only the first makes the second read as unverified."""
    return [m.group(1).lower().rstrip(".") for m in _CLAUSE.finditer(text or "")]


def extract(text: str) -> List[Dict[str, str]]:
    """Every citation-shaped span in the text, with its code and clause parts."""
    found: List[Dict[str, str]] = []
    seen = set()
    # A citation is a standard, optionally followed by a clause within the next stretch of
    # text -- "IS 1893:2016 Cl. 7.6.2" or "NBC Part 3, Cl. 4.2".
    for m in list(_STANDARD.finditer(text or "")) + list(_NBC.finditer(text or "")):
        tail = text[m.end(): m.end() + 60]
        cl = _CLAUSE.search(tail)
        raw = m.group(0).strip()
        if cl and cl.start() < 25:            # close enough to belong to this standard
            raw = (raw + " " + cl.group(0)).strip()
        key = raw.lower()
        if key in seen:
            continue
        seen.add(key)
        found.append({"raw": raw, "code": _norm_code(m.group(0)),
                      "clause": _norm_clause(cl.group(0)) if cl and cl.start() < 25 else ""})
    return found


def verify(text: str) -> Dict[str, Any]:
    """Split the citations in `text` into resolved, code-only and unverified."""
    reg = _registry()
    resolved, code_only, unverified = [], [], []
    for c in extract(text):
        code, base = c["code"], _base(c["code"])
        if c["clause"] and ((code, c["clause"]) in reg["pairs"]
                            or (base, c["clause"]) in reg["pairs"]):
            resolved.append(c["raw"])
        elif code in reg["codes"] or base in reg["codes"]:
            # The standard is real; the clause number is not one the app carries. That is
            # not proof it is wrong -- the registry is not the whole code -- so it is
            # reported as unconfirmed rather than as an error.
            (code_only if c["clause"] else resolved).append(c["raw"])
        else:
            unverified.append(c["raw"])
    return {
        "resolved": resolved,
        "code_only": code_only,
        "unverified": unverified,
        "checked": len(resolved) + len(code_only) + len(unverified),
    }


def registry_context(limit: int = 0) -> List[Dict[str, str]]:
    """The clause entries to hand the model, so it cites from a list rather than memory."""
    # No internal key: it is a lookup name for the app, not something to cite.
    rows = [{"code": v["code"], "clause": v.get("clause", ""),
             "topic": v.get("topic", "")} for v in C.CLAUSES.values()]
    return rows[:limit] if limit else rows
