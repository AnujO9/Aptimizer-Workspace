# Aptimizer — Code Text Retrieval (RAG) for APT and the IS/NBC library

## Why this exists

The backend already has `iscodes.py`: a 62-entry `CLAUSES` registry and a 20-entry
`CODE_LIBRARY`, each holding a code number, a clause number, a topic and a one-line
`key_value`. `citations.py` checks every citation APT emits against that registry and
marks it `resolved` / `code_only` / `unverified`.

That is metadata about clauses. It is not the clauses. So today APT can say
*"IS 456:2000, Cl. 23.2.1 — span/depth ratio"* but cannot say what Cl. 23.2.1 actually
requires, and any question outside the 62 curated entries comes back `unverified`
or is answered from model memory.

This task adds a retrieval layer over the **real clause text**, so that:

- APT answers code questions by quoting retrieved clause text, not from memory
- every answer carries the clause it came from, and the user can expand the source text
- `citations.py` can resolve against the full ingested corpus, not just the 62 entries
- questions the corpus does not cover are refused explicitly rather than confabulated

**Non-goal, and enforce this:** retrieval never computes anything. Loads, mix design,
base shear, BOQ, parking counts stay in `engineering.py` / `takeoff.py` / `parking.py`
exactly as they are. Retrieval tells the engineer *which clause governs*; the arithmetic
stays deterministic Python. Do not route any existing calculation through the model.

## Licensing constraint — read before writing the ingestion script

BIS standards and the NBC are copyrighted. Do **not** commit any code text to the repo
and do not download any from the internet in this task. The corpus directory is supplied
by the operator from their own licensed copies. Add `backend/codes_corpus/` and
`backend/codes_index/` to `.gitignore`. The app must start and behave sensibly when the
corpus directory is empty or absent.

## 1. `backend/codesearch.py` — new module

### Corpus format

Read from `CODES_CORPUS_DIR` (default `backend/codes_corpus/`). Accept `.txt` and `.md`
files, one file per standard, named by the `CODE_LIBRARY` id where possible
(`is456.txt`, `nbc4.txt`, `is1893.txt`). Anything unrecognised gets `code_id: None` and
is still ingested.

### Chunking — clause-level, not token-level

Do not split by character or token count. Split on clause boundaries, because the unit a
reader needs to check is a clause. Reuse the designation patterns already proven in
`citations.py` (`_STANDARD`, `_CLAUSE`) rather than writing new ones — import them or
promote them to module-level public names there.

Each chunk is:

```python
{
  "chunk_id":   "is456#23.2.1",
  "code_id":    "is456",            # CODE_LIBRARY id, or None
  "code":       "IS 456:2000",      # normalised display string
  "code_norm":  "is456",            # citations._norm_code output
  "clause":     "Cl. 23.2.1",
  "heading":    "Control of deflection",
  "text":       "...verbatim clause text...",
  "kind":       "clause" | "table" | "annex",
}
```

Rules:
- A clause shorter than ~200 characters is merged with its parent clause so it carries
  enough context to retrieve on; keep the child's clause number in the metadata.
- A clause longer than ~1500 characters is split at paragraph boundaries into
  `23.2.1 (a)`, `(b)` … parts, each keeping the same `clause` field.
- **Tables are chunked whole, never split.** A load table sliced mid-row is worse than
  absent. Detect a table block, keep its caption in `heading`, and set `kind: "table"`.
- Annexes likewise stay whole where they fit.

### Embeddings

Use the Google client already in `requirements.txt` (`google-genai`), keyed off the
existing `GEMINI_API_KEY`. Follow the provider pattern in `ai.py`: a module-level default
model name overridable by env (`GEMINI_EMBED_MODEL`), the same `AIUnavailable` /
`AIFailed` exceptions, and the same retry-with-backoff behaviour on transient 5xx.
Batch the embedding calls (embed many chunks per request, not one call per chunk).

If no key is configured, embedding is skipped and the module falls back to keyword-only
retrieval — same "disable itself with a reason" behaviour the AI features already have.

### Index storage

No new database. `MONGO_URL` defaults to the bundled self-hosted mongo, which has no
vector index, and the corpus is at most a few tens of thousands of chunks — a NumPy
matrix multiply searches that in milliseconds. `numpy` is already a dependency.

Write to `backend/codes_index/`:
- `vectors.npy` — float32 array, L2-normalised rows
- `chunks.json` — the chunk dicts, same order as the rows
- `manifest.json` — embed model name, dimension, chunk count, source file hashes, built-at

Load lazily on first query and cache in a module global. If the manifest's model or
dimension does not match the current config, refuse to use the index and log why — a
silently mismatched index returns confident nonsense.

### Ingestion entry point

`python -m codesearch build [--corpus DIR] [--out DIR] [--force]`

Idempotent: skip files whose hash is unchanged unless `--force`. Print a summary —
files, chunks, tables, chunks skipped and why.

### Retrieval — hybrid, not vectors alone

`search(query, k=5, code_id=None) -> list[dict]` scoring three signals:

1. **Vector similarity** — cosine against the normalised matrix.
2. **Keyword overlap** — token overlap between the query and `text + heading`, plus the
   existing `iscodes.CODE_KEYWORDS` string for the chunk's `code_id`. This is what makes
   "seismic", "setback", "lpcd" work.
3. **Designation match** — if the query contains a standard or clause designation
   (`_STANDARD` / `_CLAUSE` from `citations.py`), boost chunks whose `code_norm` and
   `clause` match. Exact-identifier queries are exactly what semantic search is worst at,
   and engineers type them constantly ("IS 1893 Cl. 7.6.2", "Zone IV").

Combine by normalising each score to 0–1 and taking a weighted sum (start at 0.55 vector
/ 0.25 keyword / 0.20 designation; put the weights in module constants with a comment
saying they are tunable, not derived). Return chunks with their component scores so the
weighting can be debugged from the API response.

With no vectors available, run on signals 2 and 3 alone and mark the result
`degraded: true`.

Apply a relevance floor. Below it, return an empty list — an empty list is what makes the
"I don't have that clause" path possible, and that path is the whole point.

## 2. `backend/server.py` — new endpoints

Follow the existing `@api` router conventions, auth and error shapes exactly.

**`POST /api/codes/ask`** — body `{question, project_id?, code_id?}`

1. `codesearch.search(question, k=6, code_id=code_id)`
2. If empty → return `{answered: false, reason: "no matching clause in the loaded code corpus", sources: []}`. Do not fall through to an unretrieved model answer.
3. Otherwise build a prompt with the retrieved chunks as the only permitted source:
   - system: answer **only** from the supplied extracts; cite the code and clause for
     every statement; if the extracts do not settle the question, say so; never compute
     a design value, point to the module that does
   - if `project_id` is given, append `aptcontext.build(...)` so the answer can be
     grounded in that project's live figures
4. Run it through the existing `ai.py` provider chain — do not add a second AI path.
5. Run the reply through `citations.resolve(...)` as the APT endpoint already does.
6. Return `{answered, answer, sources: [{chunk_id, code, clause, heading, text, score}],
   verified_citations, unverified_citations, degraded}`.

**`GET /api/codes/search?q=&code_id=&k=`** — raw retrieval, no model. Same source shape.
Useful for the library UI and for debugging retrieval independently of generation.

**`GET /api/codes/index`** — manifest plus `{available: bool, reason?}` so the frontend
can show the feature as unavailable with a reason instead of failing.

## 3. Wire retrieval into APT

In the existing APT chat endpoint (`server.py` around the `/api/apt` handler), before
calling the model: run `codesearch.search(user_message, k=4)` and, when it returns hits,
add them to the context block as `code_extracts`. Extend `aptcontext.build()` to accept
and serialise them, keeping the module's stated rules — computed outputs only, rounded on
the way in. Cap the injected extract text (~4000 characters total) and note the cap in a
comment.

This is the payoff: APT stops citing clause numbers from memory and starts quoting the
clause it was handed.

## 4. Strengthen `citations.py`

Extend `_registry()` to also index `(code_norm, clause)` pairs from the built chunk index
when one is loaded, so a correct citation to a real clause outside the 62 curated entries
resolves instead of being flagged. Keep the current behaviour unchanged when no index
exists. Do not weaken any existing check — a flag that fires on correct citations is the
failure mode the module's own docstring warns about.

## 5. Frontend

Minimal. Extend the existing code library view fed by `/api/iscodes` with a search box
that calls `/api/codes/search`, and render each hit as code + clause + heading with the
text collapsed behind a disclosure. In APT's message rendering, where verified citations
are already marked, make a citation that came from a retrieved chunk expandable to show
the source text. Use the existing components and styling; add no new dependencies.

## 6. Tests — `backend/tests/test_codesearch.py`

Use a small fixture corpus of invented clause text committed under
`backend/tests/fixtures/codes_corpus/` (invented, so nothing copyrighted is committed),
and stub the embedding call so tests need no API key.

Cover:
- chunking splits on clause boundaries and keeps a fixture table intact in one chunk
- a short sub-clause is merged into its parent, an over-long clause is split at paragraphs
- designation queries ("IS 456 Cl. 7.1") rank the exact clause first
- semantic queries retrieve a relevant clause with no keyword overlap (stubbed vectors)
- keyword-only mode returns results and sets `degraded: true` with no key configured
- below-floor queries return an empty list, and `/api/codes/ask` returns `answered: false`
- a missing/empty corpus dir leaves the app importable and the endpoints returning
  `available: false` rather than raising
- a manifest with a mismatched embed model is refused

Run the existing suite and keep it green.

## Deliverables

- `backend/codesearch.py`
- endpoints in `backend/server.py`
- `code_extracts` support in `backend/aptcontext.py`
- index-aware `_registry()` in `backend/citations.py`
- frontend search box + expandable citation sources
- `backend/tests/test_codesearch.py` and fixtures
- `.gitignore` entries for `backend/codes_corpus/` and `backend/codes_index/`
- `.env.example`: `GEMINI_EMBED_MODEL`, `CODES_CORPUS_DIR`, `CODES_INDEX_DIR`, commented
- a short `CODES_RAG.md`: how to place a corpus, run the build, and what happens without one

Match the existing code style — module docstrings that explain *why* a decision was made,
the way `citations.py` and `aptcontext.py` do. Do not add dependencies beyond what
`requirements.txt` already has.
