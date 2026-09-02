# Code clause retrieval

APT and the code library can answer from the **actual text** of the standards you are
licensed to hold, instead of from model memory. You supply the text; the backend chunks
it clause by clause, builds a local index, and retrieves against it.

**What this is not: retrieval never computes.** Loads, mix design, base shear, BOQ and
parking counts stay where they are — `engineering.py`, `takeoff.py`, `parking.py` —
unchanged and deterministic. Retrieval tells you *which clause governs*; the arithmetic
stays Python. If an answer ever contains a design value that came out of the model rather
than out of a calculator module, that is a bug, not a feature.

---

## 1. Licensing — read this first

BIS standards and the National Building Code are copyrighted. Nothing is downloaded and
nothing ships with the repo. The corpus is **your own licensed copy**, placed by you, on
your deployment.

`backend/codes_corpus/` and `backend/codes_index/` are both gitignored — the corpus
because it is the copyrighted text, the index because it is derived from it and carries
the same text in another shape. Do not remove those entries, and do not commit either
directory.

## 2. Placing a corpus

One plain `.txt` or `.md` file per standard, under `backend/codes_corpus/`. Name each
file by its `CODE_LIBRARY` id so hits carry the right code metadata and `code_id`
filtering works:

```
backend/codes_corpus/is456.txt
backend/codes_corpus/is1893.txt
backend/codes_corpus/is875_3.txt
backend/codes_corpus/nbc4.md
```

Valid ids are the ones in `backend/iscodes.py`: `is456`, `is875_1`, `is875_2`,
`is875_3`, `is1893`, `is13920`, `is1172`, `is10262`, `is6403`, `is1904`, `is3764`,
`is3861`, `is3534`, `nbc3`, `nbc4`, `nbc8`, `nbc9`, `griha`.

An unrecognised filename is **still ingested** — it just gets `code_id: None`, so it is
searchable but cannot be filtered by code and carries no library metadata. Prefer the
known ids.

## 3. What the text should look like

Plain text, one clause per boundary line, headings on their own line:

```
23.2.1 Control of deflection
The vertical deflection limits may generally be assumed to be satisfied ...

Table 2 Grades of Concrete
Group        Grade designation      Characteristic strength
...

ANNEX E  STRUCTURAL DESIGN (SHEAR)
```

Chunking is **clause-level, not token-level**, because the unit an engineer has to check
is a clause. A fixed-size window would cut a requirement in half and retrieve the wrong
half. Consequences of that choice:

- A short sub-clause (under ~200 characters) is folded into its parent so it has enough
  context to retrieve on; the child's designation is kept in `merged`.
- An over-long clause (over ~1500 characters) is split at paragraph boundaries into
  `(a)`, `(b)` parts that all keep the parent clause number.
- **Tables are never split.** A load table sliced mid-row is worse than no table at all.
  The caption becomes the chunk heading.
- Annexes stay whole where they fit.

Clean OCR before you ingest. Garbage clause numbering is the one input that degrades
retrieval quietly rather than loudly.

## 4. Building the index

```bash
cd backend && python -m codesearch build
```

Flags: `--corpus DIR` and `--out DIR` to override `CODES_CORPUS_DIR` /
`CODES_INDEX_DIR`, and `--force` to rebuild everything.

The build is **idempotent on file hash** — a file whose content has not changed since the
last build is skipped. Add one standard, rerun, and only that standard is re-embedded.
`--force` is for when you changed the embed model or suspect a bad index.

The summary tells you files ingested, chunks produced, how many were tables, and what was
skipped and why. A file that produced zero chunks almost always means the clause numbering
did not survive whatever produced the text file — check it before assuming the build is
broken.

Output lands in `backend/codes_index/`: `vectors.npy`, `chunks.json`, `manifest.json`.

## 5. Without a corpus, and without a key

**No corpus** (directory absent or empty): the endpoints return `available: false` with a
reason. APT behaves exactly as it does today. Nothing raises, nothing is logged as an
error, no other feature notices.

**No `GEMINI_API_KEY`**: the build skips embedding and retrieval runs keyword-only. Every
hit comes back with `degraded: true`, and the UI should say so. Exact lookups ("IS 1893
Cl. 7.6.2", "Zone IV") work as well as they ever did; paraphrased questions are weaker.
The relevance floor means the same thing in both modes — the weights are renormalised —
so degraded mode still returns nothing rather than returning junk.

## 6. Endpoints

- `POST /api/codes/ask` — question in, retrieved-and-cited answer out. Refuses with
  `answered: false` when nothing clears the floor, instead of guessing.
- `GET /api/codes/search` — raw retrieval, no model. For the library UI and for debugging
  retrieval independently of generation.
- `GET /api/codes/index` — manifest plus `available` / `reason`, so the UI can show the
  feature as unavailable with an explanation instead of failing.

## 7. Changing the embedding model

Set `GEMINI_EMBED_MODEL` in `.env`, then rebuild:

```bash
cd backend && python -m codesearch build --force
```

The manifest records the model and dimension the vectors were built with. If that does
not match the current config, the index is **refused and the reason logged** — the module
falls back to keyword-only rather than searching new-model query vectors against
old-model document vectors. Those comparisons do not error; they return plausible,
confidently wrong clauses, which is the worst failure this feature can have. A refused
index is a rebuild you have not run yet.
