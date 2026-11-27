# Phase 25: Contract Freeze & Feasibility Spike - Pattern Map

**Mapped:** 2026-11-28
**Files analyzed:** 9 created/modified (all evidence artifacts — ZERO product code) + 12 read-only code anchors
**Analogs found:** 9 / 9 artifact files have analogs; all code anchors verified in-repo with line numbers

> **NO-PRODUCT-CODE PHASE.** Nothing under `src/`, `tests/`, `pyproject.toml`, or `uv.lock` may be created or modified (D-16). All "code" this phase produces is throwaway orchestration in gitignored `.planning/tmp/phase-25/` (D-13; `.gitignore:49` ignores `.planning/tmp/`). The only committed outputs are evidence artifacts in the phase directory.

## File Classification

### Committed evidence artifacts (phase directory)

| New File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `.planning/phases/25-.../bench/spike-verdict.json` | evidence/verdict (authoritative) | batch | `.planning/milestones/v1.2-phases/23-harrier-gated-evaluation/bench/harrier-verdict.json` | exact (verdict JSON convention) |
| `.planning/phases/25-.../bench/spike-delta.csv` | evidence/table | batch/transform | Phase 23/24 `bench/*.json` per-query rows + `docs/benchmarking.md` metrics section | role-match (first CSV in series; JSON rows are the analog) |
| `.planning/phases/25-.../bench/anchor-table.json` | evidence/config (query-only anchor map) | transform | `tests/fixtures/bench/queries.json` (committed-JSON-in-repo convention) | role-match |
| `.planning/phases/25-.../25-CONTRACT-FREEZE.md` | evidence/report | file-I/O (hash manifest) | `25-CONTEXT.md` specifics hash table + `docs/benchmarking.md` prose style | role-match (no prior freeze doc exists) |
| `.planning/phases/25-.../25-SPIKE-VERDICT.md` | evidence/verdict (only on no-signal, D-15) | file-I/O | `23-CONTEXT.md` / `24-CONTEXT.md` verdict & keep-default conventions | role-match |
| `.planning/phases/25-.../COVERAGE.md` | evidence/declaration (API coverage) | file-I/O | `docs/benchmarking.md` §Metrics documentation style | partial (new doc kind) |
| SHA-256 manifest file (name = planner discretion, D-10) | evidence/manifest | file-I/O | `25-CONTEXT.md` lines 172-186 hash table (schema to reproduce) | role-match |
| `.planning/STATE.md` (via `gsd_run state.record-session` only) | state | event-driven | `gsd_run state record-session --stopped-at ... --resume-file ...` (RESEARCH.md lines 443-447) | exact (mechanism mandated) |
| `.planning/phases/25-.../25-PATTERNS.md` etc. | (this file, already exists) | — | — | — |

### Throwaway, gitignored, NEVER committed (`.planning/tmp/phase-25/`)

`spike_compat.py`, `spike_delta.py`, `runbook.sh`, `venv-0.3.37/`, `bench-spike.db`, raw logs. **Analogs: none by design (D-13).** Pattern source for their *content* is the Code Anchors section below.

## Pattern Assignments

### `bench/spike-verdict.json` (authoritative verdict)

**Analog:** `.planning/milestones/v1.2-phases/23-harrier-gated-evaluation/bench/harrier-verdict.json` (git-tracked, verified)

Observed top-level keys (Phase 23): `['arms','corpus','decision','default_flip','environment','gates','min_heldout_for_epsilon_win','notes','query_set_fingerprint','replay','rule','version']`. Phase 24 `chunk-sweep.json` adds `schema_version`, `selection_rule`, `selected_arm`, `corpus_label`, `limitation`. Follow both: flat keys, sorted-arm dicts, `decision` + `rule` as literal strings, fingerprint/replay blocks for reproducibility. Recommended Phase-25 shape is in RESEARCH.md lines 425-438 — planner should copy it verbatim into the generation script so all three artifacts (MD/CSV/JSON) are same-source (D-14).

Key conventions to preserve from the analog (harrier-verdict.json lines 2-57): per-arm dicts nest `identity`/`costs` with explicit `schema: 1` and SHA-256 `fingerprint` fields; `environment` records exact versions; `notes` is a list of limitation strings.

### `bench/spike-delta.csv` (paired delta table)

**Analog:** per-query evaluation records in `src/sif/search/benchmark.py:547-577` (`QueryEvaluation` fields: `query, retrieved_keys, retrieved_paths, grades, ndcg_at_10, hit_at_10` — defined at `benchmark.py:217-235`). CSV columns should mirror these plus `anchor_ndcg_at_10`, `delta`, `helped/hurt/unchanged` booleans, `recall_at_10` (computed separately, see Pitfall 5). Row order = fixture order (both `evaluate_per_query` calls iterate `evaluator.query_items` identically — pair by `zip(..., strict=True)`).

### `bench/anchor-table.json` (query-only anchor map, D-05)

**Analog:** `tests/fixtures/bench/queries.json` — flat JSON, top-level `version` key, list-of-records with stable string keys. Anchor table must be derivable from `queries.json` query strings ONLY (abbreviation/synonym/compound rules); the generation script must never open `relevance`, gold titles, or `heldout_defaults.json`. Record its SHA-256 inside `spike-verdict.json` (RESEARCH.md Open Question 2 recommendation).

### `25-CONTRACT-FREEZE.md` + SHA-256 manifest

**Analog:** the verified hash table in `25-CONTEXT.md` lines 174-186 — reproduce that exact 11-file list and two-column format, with a `start` block and an `end` block (D-12). Generation commands (RESEARCH.md Pattern 3, executed and verified):

```bash
shasum -a 256 pyproject.toml uv.lock \
  tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py \
  src/sif/mcp/protocol.py src/sif/mcp/tools.py \
  tests/unit/mcp/goldens/*.json

# CRITICAL: --no-cov or the 90% coverage gate in addopts fails the run
/Users/forrest/GitHub/SIF/.venv/bin/python -m pytest \
  tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py -q --no-cov
# → 13 passed in 0.60 s (measured)

git diff --stat v1.2.5..HEAD -- pyproject.toml uv.lock src/sif/mcp/ tests/unit/mcp/   # expect empty
git status --porcelain   # expect only STATE.md + 3 whitelisted planning docs (D-16)
```

Freeze anchor is `v1.2.5 (6c25e88d9913)`; record measured commit count (7 at research time — do NOT copy CONTEXT's stale "4"; Pitfall 8).

### `25-SPIKE-VERDICT.md` (no-signal only, D-15)

**Analog:** Phase 23/24 verdict conventions (keep-default is a valid deliverable). Must be accompanied by:

```bash
gsd_run state record-session \
  --stopped-at "Phase 25 no directional signal — hypothesis archived; Phases 26/27 not started; working tree clean" \
  --resume-file /Users/forrest/GitHub/SIF/.planning/phases/25-contract-freeze-feasibility-spike/25-SPIKE-VERDICT.md
```

ROADMAP Phase 25 checkbox stays UNCHECKED on no-signal. Never edit STATE.md/ROADMAP.md directly.

## Code Anchors (READ-ONLY — `<read_first>` targets for spike scripts; never files_modified)

### `src/sif/search/benchmark.py` — all metric math (D-07: reuse, don't hand-roll)

```python
# :53  def recall_at_k(relevance: Sequence[int], total_relevant: int, k: int) -> float
#        — binarized grade>0 / total_relevant; returns 0.0 when total_relevant == 0
# :86  def ndcg_at_k(retrieved: Sequence[int], ideal: Sequence[int], k: int) -> float
#        — exponential gain (2^rel - 1); ideal from FULL judgment set; 0.0-safe
# :99  def hit_at_k(retrieved: Sequence[int], k: int) -> float
# :414 def warrants_default_change(baseline_ndcg, candidate_ndcg, delta=EPSILON) -> bool
#        — Phase 27 gate; FORBIDDEN in Phase 25 (D-08)
# :430 class SearchEvaluator
# :433   def __init__(self, fixture: dict, fixture_path: Path | None = None, corpus_root: Path | None = None)
# :547   def evaluate_per_query(self, search_fn: Callable[[str], list[SearchResult]], k: int = DEFAULT_K) -> list[QueryEvaluation]
```

`evaluate_per_query` body (:560-577) shows the exact pairing path: `result_key(result, self.relevance_key, root)` → `_grades_for` → `ndcg_at_k(retrieved, ideal, k)` per query, in fixture order. Recall is NOT computed there — derive `total_relevant = sum(1 for g in item.grades.values() if g > 0)` yourself (semantics at :609/:672).

### `src/sif/cli/commands/bench.py:325-346` — `_tuning_evaluator` (the tuning-split filter to mirror)

```python
tuning_queries = [item for item in fixture_data["queries"] if item.get("split") == "tuning"]
if not tuning_queries:
    raise click.ClickException("Sweep requires fixtures with split labels; ...")
tuning_fixture = {key: value for key, value in fixture_data.items() if key != "queries"}
tuning_fixture["queries"] = tuning_queries
return SearchEvaluator(tuning_fixture, fixture_path=fixture_path)
```

Filter BEFORE constructing `SearchEvaluator`; carry non-`queries` metadata so `relevance_key: "path"` + `corpus_root: "corpus"` resolve. Yields exactly 36 queries (verified: 56 total = 36 tuning + 20 heldout).

### `src/sif/search/bm25.py` — `BM25Searcher`

Both arms use `BM25Searcher(conn).search(query, SearchOptions)`; the anchor arm only changes the query string (`" ".join(anchors + [query])`). Never raw FTS5 SQL.

### `src/sif/embedding/embedder.py` — generation-proof shape reference (NOT to be reused for the proof)

```python
# :302 class LlamaCppEmbedder(Embedder)
# :345-352  self.model = Llama(model_path=..., n_ctx=..., n_threads=..., n_gpu_layers=...,
#                              embedding=True, verbose=...)   # ← EMBED path; D-02 forbids as generation proof
# :437-469  def create_completion(self, prompt, max_tokens=256, temperature=0.3, stop=None) -> dict
#            returns llama_cpp's openai-style {"choices": [{"text": ...}], "usage": ...} unchanged
# :471-477  revision property → _file_sha256(model_path)  # GGUF SHA-256 precedent
```

Spike script constructs `Llama(model_path=..., n_ctx=2048, verbose=False)` WITHOUT `embedding=True`, then `create_completion(prompt=FIXED_PROMPT, max_tokens=64, temperature=0.0, top_k=1, stop=["\n"])`; non-empty `out["choices"][0]["text"]` = success (D-02). Expect `RuntimeError` containing `unknown model architecture: 'lfm3'` under locked 0.3.35 — catch `Exception`, record `type(e).__name__`, `str(e)`, stderr.

### `src/sif/search/hybrid.py:535-544` — `prefix_map` (proof that `anchor:` does not exist)

```python
prefix_map = {
    "lex:": SearchType.BM25,
    "vec:": SearchType.VECTOR,
    "hyde:": SearchType.HYDE,
    "expand:": SearchType.EXPAND,
}
```

`anchor:` is a LABEL ONLY in spike artifacts; product code must learn no new prefix this phase.

### `src/sif/search/rerank.py:110, :141` — `LlamaCppReranker` also constructs `Llama(...)` (GGUF rerank path named in D-03/D-04 impact assessment)

### `src/sif/mcp/protocol.py:80-104` — frozen `QueryInput` (Pydantic BaseModel)

Fields: `query: str`, `collections`, `limit` (ge=1), `offset` (ge=0), `filter: dict | None`, `per_chunk: bool = False`, `min_score` (ge=0.0), `rrc_k`/`bm25_weight`/`vector_weight` overrides. No `anchor` field may be added (CTR-01).

### `src/sif/mcp/tools.py` — frozen 7 tools

`@mcp.tool` registrations at lines 128 (`query`), 189 (`get`), 220 (`multi_get`), 243 (`status`), 256 (`metadata`), 308 (`lex_search`), 347 (`vec_search`); registration order pinned in `register_tools()` at :392-407.

### `tests/unit/mcp/test_wire_transcripts.py` + `tests/unit/mcp/goldens/*.json` — frozen wire proof

Golden-parametrized test at :190 (`test_wire_transcript_matches_golden`); 5 goldens: `2024-11-05.json`, `2025-03-26.json`, `2025-06-18.json`, `2025-11-25.json`, `2026-07-28.json`. Run as-is with `--no-cov`.

### `tests/unit/mcp/test_packaging.py` — frozen 13-dependency proof

Tests at :52 (`test_runtime_dependency_list_is_frozen_at_thirteen_entries`), :57, :65. Run as-is; proves CTR-02 without new guards.

### `tests/fixtures/bench/queries.json` — the only query source (D-06)

Verified structure: top-level `['corpus_root','queries','relevance_key','version']`; `relevance_key: "path"`, `corpus_root: "corpus"`; 56 queries (36 `split:"tuning"`, 20 `split:"heldout"` — heldout MUST NOT be read); per-query shape `{"category","query","relevance":{corpus-relative-path: grade},"split"}`. Artifact records `heldout_read: false`.

### `pyproject.toml` / `uv.lock` / `.gitignore`

`uv.lock` pins `llama-cpp-python==0.3.35` (PyPI sdist); `pyproject.toml` carries the 13-runtime-dep list, the pytest `addopts` coverage flags (source of the `--no-cov` trap), and `fail_under=90`. All three hash-frozen start+end (D-12); `.gitignore:49` = `.planning/tmp/`.

## Shared Patterns

### Reproducibility block (apply to spike-verdict.json + CONTRACT-FREEZE.md)
**Source:** Phase 23 `replay`/`query_set_fingerprint` keys; `embedder.py:471-477` `_file_sha256` precedent. Every artifact records: fixed seed (even if `rng_used: false`), fixture SHA-256, anchor-table SHA-256, script SHA-256, environment versions.

### Zero-mutation guarantee (apply to every plan task)
**Source:** RESEARCH.md Pattern 3. Start/end `shasum` over the 11-file manifest; both pytest files green with `--no-cov`; `git status --porcelain` explained per D-16 (3 whitelisted untracked planning docs: `.planning/.continue-here.md`, `.planning/HANDOFF.json`, `.planning/v1.3-ui-anchor-milestone-research.md`); any diff in `src/`, `tests/`, `pyproject.toml`, `uv.lock` = phase failure.

### Scratch confinement (apply to all throwaway scripts)
**Source:** `.gitignore:49`. All outputs under `/Users/forrest/GitHub/SIF/.planning/tmp/phase-25/`; `SIF_DB_PATH` always pointed at the scratch DB; subprocess + argument-list invocation for the untrusted GGUF load; never string-format shell commands (ASVS V5/V12).

## No Analog Found

| File | Role | Reason |
|---|---|---|
| `bench/spike-delta.csv` (CSV format itself) | evidence | No prior `.csv` bench artifact exists (23/24 are JSON-only); JSON row schema from `QueryEvaluation` is the pattern source |
| `COVERAGE.md` | evidence | New doc kind; use `docs/benchmarking.md` §Metrics (`docs/benchmarking.md:72-101`) prose style |
| `.planning/tmp/phase-25/*` scripts | throwaway | No analog by design (D-13); content patterns come from Code Anchors above + RESEARCH.md Patterns 1-2 |

## Metadata

**Analog search scope:** `.planning/milestones/v1.2-phases/*/bench/`, `docs/`, `src/sif/{search,embedding,mcp,cli}`, `tests/{unit/mcp,fixtures/bench}`
**Tracked-source gate:** all named analogs verified via `git ls-files` (non-empty)
**Pattern extraction date:** 2026-11-28
