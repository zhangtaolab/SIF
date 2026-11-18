# Phase 18: Quality Instrument (Personal Bench + rapidfuzz DYM) - Research

**Researched:** 2026-11-14
**Domain:** Label-free personal-corpus IR evaluation (known-item synthesis, deterministic splits, paired bootstrap) and a rapidfuzz did-you-mean swap
**Confidence:** HIGH on the code seams and rapidfuzz behavior (read + measured this session); MEDIUM on the statistical/report design (standard methods, discretionary thresholds); LOW on unmeasured cross-machine performance.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Personal query synthesis (EVAL-01)
- **D-01:** **Three query legs by default** — title/H1, body snippet, and query_log replay. Title/body legs are known-item synthesis; replay is a separate leg with its own semantics. — **Reversibility:** reversible — leg composition is a report/query-set change.
- **D-02:** **query_log replay measures stability/regression, not absolute quality** — replay each logged query and compare its top-k against a baseline snapshot (rank overlap/consistency). No pseudo-relevance labels; the CLI-only replay bias (MCP queries are not logged, Phase 15 D-08) is documented in the report. — **Reversibility:** costly — the replay leg's meaning is a stored-run comparison contract.
- **D-03:** **Deterministic hash sampling with caps** — sample documents by content hash: minimum 50 queries, maximum 500, proportional to corpus size; the same corpus yields the same query set across runs. — **Reversibility:** reversible.
- **D-04:** **Known-item labels reuse the legacy binary fixture schema** — the target document is grade 1, all other documents grade 0; no synthetic graded labels. nDCG@10 therefore behaves as a rank-sensitive known-item metric and the report says so. — **Reversibility:** reversible — label semantics are documented with the run.

#### Bias controls and reporting (EVAL-02)
- **D-05:** **Paraphrase overlap budget = token Jaccard ≤ 0.60** — measure between the query and the target document's title plus opening text; reject queries over budget, and report the rejection count and the per-leg budget. — **Reversibility:** costly — changing the budget changes the query set, so saved runs are not directly comparable across a threshold change.
- **D-06:** **Hash split = 50/50 tuning/held-out, held-out ≥ 25** — split by query-text hash so it is stable across runs; if the held-out pool would fall below 25, widen sampling rather than shrink the gate. — **Reversibility:** costly — the split defines which runs can support a defaults decision.
- **D-07:** **Noise gate = paired bootstrap 95% CI + mean Δ ≥ 0.01** — compute per-query paired deltas between two arms, bootstrap the mean delta, and declare a winner only when the CI excludes 0 and the mean delta reaches the 0.01 tie rule. Report the 1/N per-query noise floor and each group's N. — **Reversibility:** reversible — analysis method.
- **D-08:** **Full-dimensional report with small-group suppression** — report per leg × per language × per category; suppress groups with fewer than 10 queries and list the suppressed group names so an empty cell is never mistaken for a zero. — **Reversibility:** reversible.

#### `sif eval` command and data (EVAL-01)
- **D-09:** **New `sif eval` command group with `--personal`** — `sif bench` stays the committed synthetic-fixture instrument; `sif eval --personal` is the personal-corpus entry point, matching the roadmap's literal command. — **Reversibility:** costly — a public CLI surface is a compatibility commitment once shipped.
- **D-10:** **Auto-save the synthesized query set to the cache directory** — write query/path/split/leg/language/grade only (never document content) under `~/.cache/sif/eval/`; `--no-save` opts out. Saved runs are the comparison substrate. — **Reversibility:** reversible.
- **D-11:** **Thresholds and retrieval mode** — require at least 50 indexed documents and 50 synthesized queries; default to hybrid retrieval (the embed extra). If the embed extra is unavailable, fail with a `pip install docsif[embed]` remedy hint; `--bm25-only` is the explicit degradation path. — **Reversibility:** reversible.
- **D-12:** **Comparison entry point = `--compare <saved-run.json>`** — load a prior run, validate that its corpus fingerprint matches, and report paired deltas + bootstrap CI; every run auto-saves. A mismatched corpus refuses the comparison with a clear message. — **Reversibility:** reversible — the saved-run format can evolve with a version field.
- **D-13:** **`rapidfuzz>=3.14.5,<4` is a hard runtime dependency; no difflib fallback** — a missing import is a broken install and raises a clear error. This is the v1.2-locked second dependency. — **Reversibility:** reversible — code can return to difflib, but the packaging change is already locked for v1.2.

#### rapidfuzz DYM (QUAL-01)
- **D-14:** **Full-vocabulary `rapidfuzz.fuzz.ratio` (Indel 0–100), no first-letter bucket** — replace `difflib.get_close_matches` over the ±1-letter bucket; start at cutoff 75 and re-measure on the bench vocabulary, pinning the chosen cutoff with the ≤10 ms core-function budget. — **Reversibility:** reversible.
- **D-15:** **Deterministic tie-break = score desc → term lexicographic asc → document frequency desc** — preserves the current difflib sorted-term determinism while keeping high-frequency terms competitive. — **Reversibility:** reversible.
- **D-16:** **Cutoff is an internal constant, not a setting or CLI flag** — the bench evidence pins it; tests guard both the constant and the behavior. No new user-facing knob. — **Reversibility:** reversible — exposing it later is additive.
- **D-17:** **Preserve the probe/hit contracts and untouched sections** — every emitted suggestion must still return ≥1 hit; `_probe` stays fail-soft; prefix completions and history ranking are unchanged. The 100 ms `sif suggest` budget remains the end-to-end guard. — **Reversibility:** reversible.

### Claude's Discretion
- Personal-eval **category axis**: query-length buckets (`short` ≤2 tokens, `medium` 3–5, `long` ≥6), orthogonal to leg and language; revisit if research finds a better axis.
- Language classification: CJK codepoint ratio (`en` / `zh` / `mixed`), with the exact threshold pinned by tests.
- Saved-run JSON schema and version field; the corpus fingerprint algorithm (content hash over paths + sizes/checksums).
- Replay baseline snapshot shape (top-k document paths + ranks) and how “no baseline” is reported.
- Hybrid-default embedder selection (configured model or `ConceptEmbedder` in tests), and the exact `--bm25-only` report flag.
- rapidfuzz scorer call shape (`process.extract` vs `cdist`), early-exit strategy for very large vocabularies, and the measured cutoff within the 70–80 range.
- Exact `sif eval --personal` table columns and JSON field names, following the `bench` output conventions.
- Whether `sif eval` also exposes a fixture mode for the committed synthetic corpus (alias) or stays personal-only in this phase.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-01 | User can measure search quality on their own corpus via `sif eval --personal` (known-item synthesis through the legacy fixture schema + `SearchEvaluator` reuse + query_log replay with documented CLI-only bias). | Concrete synthesis/sampling/replay design below; verified `documents`/`query_log` schemas; verified legacy fixture parse path in `SearchEvaluator`; CLI group pattern and docs-generator interaction identified. |
| EVAL-02 | User can trust the personal bench's bias controls (paraphrase overlap budget; per-leg × per-language × per-category reports; hash-split tuning/held-out; paired deltas + noise gate). | Token-Jaccard enforcement design (with the title-leg ambiguity flagged); deterministic sha256 split recipe; per-query evaluation extension; seeded percentile-bootstrap algorithm and gate arithmetic; suppression rule and report shape. |
| QUAL-01 | User gets faster, higher-recall did-you-mean suggestions (rapidfuzz measured swap dropping first-letter bucketing; ≤10 ms budget; cutoff deliberately re-measured on the 0–100 Indel scale; tie-break/probe contracts preserved). | Measured rapidfuzz 3.14.5 behavior and speed at 73k terms; first-letter-typo recall 0.070 (bucket) → 1.000 (full vocab at 75); exact `process.extract` API/return shape; verified probe/hit code paths to preserve; package/wheel verification. |
</phase_requirements>

## Summary

Phase 18 has two halves that share one property: they must be measured before they are trusted. The personal bench synthesizes known-item queries from the user's own indexed documents (title/H1 and body-snippet legs), reuses the legacy binary fixture schema and `SearchEvaluator` metrics, adds a `query_log` replay leg that measures stability against a saved snapshot, and wraps the result in bias controls: a token-Jaccard overlap budget, deterministic sha256 sampling and 50/50 tuning/held-out splitting, per-leg × per-language × length-bucket reporting with small-group suppression, and a paired-bootstrap noise gate against a corpus-fingerprint-matched saved run. The DYM half replaces the difflib ±1-first-letter bucket with a full-vocabulary `rapidfuzz.fuzz.ratio` scan at a re-measured cutoff.

The code seams are favorable. `SearchEvaluator` already parses legacy binary fixtures (`relevant_docids` → grade 1) and computes nDCG/Hit from one result list per query; the only missing piece is a per-query evaluation surface so the personal bench can group scores after the fact. `documents` stores `id/path/title/content/checksum/file_size`, which is everything synthesis and fingerprinting need, and `query_log` stores `query/result_count/collections/created_at` with an existing `GROUP BY` aggregate. The `sif bench` CLI already establishes the table + `--json` convention, embedder loading, and `CachedEmbedder` query memoization that `sif eval` should mirror.

The measured rapidfuzz evidence is decisive: at 73k vocab terms on this machine, `process.extract(..., scorer=fuzz.ratio, limit=3, score_cutoff=75)` costs ~1.7–1.9 ms/query vs ~5.9 ms for the current bucket and ~51 ms for full-vocab difflib; first-letter typos that the bucket recalls at 7.0% are recalled at 100% by the full scan at cutoff 75 (81.3% at 80; cutoff 70 buys no additional recall but admits ~15% more candidates than 75). Cutoffs 70/75/80 were measured on the committed bench vocabulary (422 porter stems) and a synthetic 73k-term vocabulary. The chosen constant should be 75.0.

**Primary recommendation:** build `src/sif/search/personal_bench.py` as a pure, deterministic domain module (sampling → synthesis → overlap filter → legacy fixture → per-query metrics → split/groups → seeded bootstrap → saved-run schema), add an additive `SearchEvaluator.evaluate_per_query()` method that leaves `sif bench` output byte-identical, implement `sif eval` as a `click.Group(invoke_without_command=True)` with `--personal` (and extend the CLI doc generator to render leaf groups), and swap `_close_matches` to `process.extract(..., scorer=fuzz.ratio, limit=n, score_cutoff=75.0)` while leaving `_probe`/`_hits`/`_retrievable` untouched.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Corpus sampling, `sha256` fingerprint, query synthesis, overlap filtering | Domain (`src/sif/search/personal_bench.py`) | Database (read `documents`) | Pure deterministic functions, unit-testable without Click/Rich. |
| Known-item relevance + nDCG/Hit | Domain (`src/sif/search/benchmark.py`) | — | Reuse existing metric functions and fixture parser; never duplicate the math. |
| Per-query evaluation surface | Domain (`SearchEvaluator`) | — | Additive method; `report()` and `sif bench` output stay unchanged. |
| Paired bootstrap / noise gate | Domain (`personal_bench.py`) | — | Seeded `random.Random`; no SciPy dependency. |
| query_log replay source | Database (`QueryLogRepository.history()`) | Domain | Existing one-query aggregate; no new table. |
| Saved-run persistence | Infrastructure (filesystem via `Settings.get_cache_dir()`) | CLI | Local JSON under the cache dir; no DB migration, no document content. |
| `sif eval --personal` orchestration/output | CLI (`src/sif/cli/commands/eval.py`) | Domain | Mirrors `bench.py` table/`--json`, stderr warnings, stdout purity. |
| DYM scoring | Search (`src/sif/search/suggest.py`) | — | Replace `_close_matches` internals only; contracts preserved. |
| Dependency/packaging | Build config (`pyproject.toml` + `uv.lock`) | — | Hard runtime dep; CI installs with `uv sync --frozen`. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `rapidfuzz` `[WARNING: flagged as suspicious — verify before using.]` | `>=3.14.5,<4` (py3.10 resolves 3.14.5; py3.11+ resolves 3.14.6) | Full-vocabulary DYM scoring | MIT; C++ Indel kernels; 82 wheels covering cp310–cp314 on the CI matrix; the v1.2-locked second runtime dependency [CITED: pypi.org/pypi/rapidfuzz/3.14.5/json] [CITED: github.com/rapidfuzz/RapidFuzz/releases]. The warning is the seam's metadata-absence `SUS` verdict, not a red flag (see audit below). |
| Python stdlib `hashlib` | 3.10+ | Deterministic sampling, split, corpus fingerprint | `hashlib.sha256` is stable across processes/platforms; builtin `hash()` is salted (`PYTHONHASHSEED`) and must never be used. |
| Python stdlib `random.Random` | 3.10+ | Seeded percentile bootstrap | Mersenne Twister sequence is stable across Python versions; no SciPy/NumPy RNG dependency. |

### Supporting (already in the project — do not add)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | locked by `uv.lock` (CI 9.0.3; local 9.1.1) | Test battery | All tests; use `--no-cov` for fast targeted runs. |
| `click` | `>=8.0.0` | `sif eval` group and options | Mirror `bench_cmd`/`suggest_cmd` conventions. |
| `rich` | `>=13.0.0` | Table rendering, stderr warnings | Tables on stdout; warnings on `Console(stderr=True)`. |
| `sqlite-vec` | `>=0.1.9` | Hybrid retrieval in the personal bench | DB-backed tests skip when unavailable, as `build_bench_db` does. |
| `pydantic` / `pydantic-settings` | `>=2.0.0` | `Settings`, cache-dir resolution | Use `get_cache_dir()`; no new settings (D-16). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `process.extract(..., scorer=fuzz.ratio)` | `process.cdist([token], terms, scorer=fuzz.ratio)` | Measured 3.5 ms/query vs 1.7 ms; returns a NumPy matrix needing argpartition + mapping. Use `extract`. |
| `process.extract` | A Python loop over `fuzz.ratio` | Measured 12.2 ms/query at 73k; higher call overhead and manual top-k. |
| `fuzz.ratio` (Indel) | `fuzz.WRatio` (STACK.md's sketch) | D-14 locks `fuzz.ratio`; WRatio mixes partial/token scorers and changes the rank order and cutoff meaning. Use the locked Indel scorer. |
| Custom bootstrap | `scipy.stats.bootstrap` | SciPy is not a dependency and the v1.2 scope allows exactly two new runtime deps. A ~20-line percentile bootstrap over per-query deltas is standard and deterministic. |

**Installation:**
```bash
# pyproject change, then lock — never `pip install` into the project env by hand
uv lock
uv sync --frozen --extra dev --extra embed
```

**Version verification:** `pip index versions rapidfuzz` returned `3.14.6` as latest and `3.14.5` available [VERIFIED: local `pip index versions`, 2026-11-14]. PyPI's 3.14.5 JSON reports `requires_python: >=3.10`, upload time 2026-04-07, MIT, and 82 wheels (cp310–cp314; macOS x86_64/arm64; manylinux/musllinux; win32/win_amd64/win_arm64) [CITED: pypi.org/pypi/rapidfuzz/3.14.5/json]. The 3.14.6 release notes say "dropped support for Python 3.10" [CITED: github.com/rapidfuzz/RapidFuzz/releases], which is exactly why the range must start at 3.14.5 and why CI must tolerate both resolved versions.

### Verified in-repo contract values (do not re-derive)

```python
# src/sif/search/benchmark.py:21-33 (read this session)
CATEGORIES: tuple[str, ...] = ("keyword", "synonym", "multilingual", "rival")
SPLITS: tuple[str, ...] = ("tuning", "heldout")
LEGACY_K_VALUES: tuple[int, ...] = (1, 5, 10)
GRADE_MIN = 0
GRADE_MAX = 3
DEFAULT_K = 10
EPSILON = 0.01
```

```sql
-- src/sif/database/schema.py:61-75 (read this session)
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL,
    path TEXT NOT NULL,
    filename TEXT NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    checksum TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    mtime REAL NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    ...
)

-- src/sif/database/schema.py:158-166 (read this session)
CREATE TABLE IF NOT EXISTS query_log (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    result_count INTEGER NOT NULL DEFAULT 0,
    collections TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
)
```

```python
# src/sif/database/repositories.py:690-692 (read this session)
"SELECT query, COUNT(*), MAX(created_at) FROM query_log GROUP BY query"

# src/sif/config/settings.py:258-263 (read this session)
query_history_limit: int = Field(
    default=500,
    ge=1,
    description="Most-recent query_log rows kept; on insert overflow the "
    "oldest rows are deleted in the same write (trim-in-write)",
)
```

The `CATEGORIES` tuple is a fixed four-value axis: the personal bench's leg/language/length groups must be carried outside `SearchEvaluator`'s category field (or the evaluator must gain a separate grouping surface), because `_parse_graded_item` rejects any category outside `CATEGORIES` [VERIFIED: src/sif/search/benchmark.py:486-498]. The legacy schema (D-04) avoids that constraint entirely.

## Package Legitimacy Audit

> This phase installs one external package. The seam returned `SUS` with `exists: null`, `publishedAt: null`, `weeklyDownloads: null`, `repoUrl: null` — i.e. the seam's registry lookup returned no metadata (`unknown-age`, `unknown-downloads`, `no-repository`), not a red-flag signal. Authoritative PyPI JSON and the official docs were checked independently.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `rapidfuzz` | PyPI | Release 3.14.5 uploaded 2026-04-07; long release history (100+ versions visible in `pip index versions`) [CITED: pypi.org/pypi/rapidfuzz/3.14.5/json] | Seam: unknown; public project widely used (not independently measured here) | github.com/rapidfuzz/RapidFuzz [CITED: pypi.org project URLs] | `SUS` (metadata-absence only) | Flagged — the planner should add a lightweight `checkpoint:human-verify` before install and cite CONTEXT D-13 (the user already locked this package for v1.2) |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** `rapidfuzz` — but the verdict is an artifact of the seam failing to read registry metadata; PyPI JSON confirms the version, `requires_python`, license, wheel matrix, and repository URL. The project's own v1.2 decision (D-13, ROADMAP, PROJECT.md) is the user approval; the checkpoint is a formality, not a new decision. Tag package facts in plans as `[CITED: ...]`, not `[VERIFIED: registry check]`, because the seam did not return `OK`.

## Architecture Patterns

### System Architecture Diagram

```
                     ┌─────────────────────────────────────────────────────────────┐
                     │                    sif eval --personal                       │
                     └─────────────────────────────────────────────────────────────┘
                                            │
              ┌─────────────────────────────┼──────────────────────────────┐
              ▼                             ▼                              ▼
   documents (id,path,title,          query_log (query,count,        Settings.get_cache_dir()
    content,checksum,file_size)        last_used)                     /eval/*.json
              │                             │                              ▲
              ▼                             │                              │
   eligibility filter (>=50 docs)           │                              │
              │                             │                              │
              ▼                             │                              │
   sha256 deterministic sample              │                              │
   (min 50 / max 500 queries)               │                              │
              │                             │                              │
      ┌───────┴────────┐                    │                              │
      ▼                ▼                    │                              │
 title/H1 leg     body-snippet leg          │                              │
 (exact-term)     (prose sentence,          │                              │
      │           later than opening)       │                              │
      │                │                    │                              │
      └───────┬────────┘                    │                              │
              ▼                             │                              │
   overlap budget (Jaccard <=0.60)          │                              │
   + dedupe + language + length bucket      │                              │
              │                             │                              │
              ▼                             ▼                              │
   legacy fixture {"queries":[{query,     replay each logged query        │
   relevant_docids:[target]}]}            through SearchPipeline           │
              │                             │                              │
              ▼                             ▼                              │
   SearchEvaluator.evaluate_per_query   top-k path snapshot ───────────────┤
              │                             │                              │
              ▼                             ▼                              │
   per-query nDCG/Hit (target=1)    Jaccard@10 / top-1 vs saved baseline   │
              │                             │                              │
              ▼                             │                              │
   group: leg x language x length      paired deltas (tuning/heldout)      │
   suppress count<10                   seeded bootstrap 95% CI             │
              │                             │                              │
              └──────────────┬──────────────┘                              │
                             ▼                                             │
                  report (table or --json) ────────────────────────────────┘
```

### Recommended Project Structure

```
src/sif/
├── search/
│   ├── personal_bench.py     # NEW: sampling, synthesis, overlap, split,
│   │                         #      groups, bootstrap, saved-run schema
│   ├── benchmark.py          # EXTEND: evaluate_per_query() only (additive)
│   └── suggest.py            # CHANGE: _close_matches -> rapidfuzz
├── cli/commands/
│   ├── eval.py               # NEW: click group + personal runner + rendering
│   └── bench.py              # reuse patterns; no output-contract change
└── cli/main.py               # register eval_group

tests/
├── support/eval.py           # NEW: tmp-DB builder + query_log seeding helper
├── unit/search/test_personal_bench.py
├── unit/cli/test_eval.py
└── unit/search/test_suggest.py   # UPDATE for rapidfuzz
```

### Pattern 1: Personal bench pipeline (pure domain module)
**What:** one function per stage, each deterministic and independently testable:
`load_candidates(conn, collection_ids)` → `sample_candidates(docs, min_q, max_q)` → `synthesize_queries(docs)` → `apply_overlap_budget(queries)` → `assign_splits(queries)` → `evaluate_queries(evaluator, search_fn)` → `build_report(records)`.
**When to use:** always; the CLI only orchestrates and renders.
**Why:** keeps the instrument testable without a real index/embedder and prevents report formatting from contaminating the measurement logic.

### Pattern 2: Deterministic hash sampling and splitting
**What:** hash a stable identity with `hashlib.sha256`; sort by the digest; split by a digest threshold. Never use `hash()`.
**When to use:** document sampling (D-03) and query-text splits (D-06).
**Example:**
```python
import hashlib
import unicodedata

def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())

def split_for(query: str) -> str:
    digest = hashlib.sha256(_normalize(query).encode("utf-8")).digest()
    return "tuning" if digest[0] < 128 else "heldout"  # stable 50/50
```
**Note:** NFC normalization before hashing matters on macOS, where filenames and pasted text can be NFD — without it, the "same" query can hash differently across platforms.

### Pattern 3: Per-query evaluation surface (additive to `SearchEvaluator`)
**What:** add `evaluate_per_query(search_fn, k=DEFAULT_K) -> list[QueryEvaluation]` that runs the same one-search-per-query loop `report()` already runs, returning `(query, retrieved_keys, grades, ndcg_at_10, hit_at_10)` per item. Refactor `report()` to consume it if convenient, but keep every existing field and `to_dict()` key identical.
**When to use:** personal bench grouping and paired comparison. `sif bench` keeps using `report()`; its JSON must not gain a `per_query` key.
**Why:** the personal bench needs per-query deltas; the fixture parser and metric functions are already correct and should not be reimplemented.

### Pattern 4: Seeded percentile bootstrap noise gate
**What:** paired deltas `d_i = current_i - baseline_i`; resample indices with replacement B=10,000 times; mean each resample; take 2.5/97.5 percentiles with `benchmark.percentile` (p in 0–100).
**When to use:** every `--compare` run and every group with N≥10.
**Example:**
```python
import random

from sif.search.benchmark import percentile

def paired_bootstrap(
    deltas: list[float], resamples: int = 10_000, seed: int = 0
) -> tuple[float, float, float]:
    rng = random.Random(seed)
    n = len(deltas)
    means = [
        sum(deltas[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(resamples)
    ]
    return sum(deltas) / n, percentile(means, 2.5), percentile(means, 97.5)
```
`benchmark.percentile` uses linear interpolation between closest ranks (p in 0–100) [VERIFIED: src/sif/search/benchmark.py:104-112], so the CI matches the house percentile semantics already used for latency.
**Decision rule:** winner only if `ci_low > 0 or ci_high < 0`, **and** `round(mean_delta, 6) >= 0.01` for an improvement (mirror `warrants_default_change`'s rounded-delta arithmetic). Report helped/hurt/unchanged counts and `1/N`.

### Pattern 5: Saved-run comparison contract
**What:** a versioned JSON file under `<cache_dir>/eval/` that stores enough to recompute both arms: per-query `query`, `target_path`, `target_doc_id`, `leg`, `language`, `length_bucket`, `split`, `grade` (always 1), and `retrieved: [paths in rank order]`. It never stores document content.
**When to use:** every personal run unless `--no-save`; `--compare` loads the prior file.
**Why this shape:** with the target path and the saved retrieved path list, the baseline arm's nDCG is recomputable without re-running old code; pairing is exact; replay stability uses the same top-k lists. D-10's "query/path/split/leg/language/grade only (never document content)" is satisfied — retrieved paths are not content.
**Comparison algorithm:** validate version/schema → compute current corpus fingerprint → refuse on mismatch → run **the saved run's query set** (not a freshly synthesized one) through the current pipeline → recompute baseline nDCG from saved `retrieved` → paired deltas + bootstrap → replay vs saved replay snapshot.

### Pattern 6: rapidfuzz DYM swap
**What:** replace only `_close_matches`:
```python
from rapidfuzz import fuzz, process

_DYM_CUTOFF = 75.0  # internal constant (D-16); measured on the bench vocab

def _close_matches(self, token: str, n: int = 3) -> list[str]:
    if not token or not self._terms:
        return []
    matches = process.extract(
        token,
        self._terms,
        scorer=fuzz.ratio,
        limit=n,
        score_cutoff=_DYM_CUTOFF,
    )
    # process.extract is best-first; equal scores keep choice-index order,
    # and self._terms is sorted, so ties are lexical asc (D-15). The explicit
    # sort keeps the df tie-break visible and stable.
    matches.sort(key=lambda m: (-m[1], m[0], -self._df.get(m[0], 0)))
    return [term for term, _score, _index in matches]
```
**When to use:** every out-of-vocab token in `_dym_slots`.
**Why:** `process.extract` returns `(choice, score, index)`, best-first, ties by index; `score_cutoff` drops scores below 75 for a similarity scorer; the full scan removes the first-letter recall hole. Measured ~1.7–1.9 ms/query at 73k terms.

### Pattern 7: `sif eval` as a leaf Click group + docs generator fix
**What:** `@click.group("eval", invoke_without_command=True)` with options on the group; `ctx.invoked_subcommand is None` runs the personal action and requires `--personal` (UsageError otherwise). Register in `main.py`.
**Critical interaction:** `scripts/generate_cli_ref.py::traverse_commands` currently recurses any `click.Group` and returns only leaves; a group with no subcommands contributes nothing, so `sif eval` would have no generated section. Fix:
```python
if isinstance(cmd, click.Group) and cmd.commands:
    for name, subcmd in cmd.commands.items():
        results.extend(traverse_commands(subcmd, f"{path} {name}".strip()))
else:
    results.append((path, cmd))
```
Add `("eval", "Other Commands")` to `GROUP_ORDER` (or a new "Evaluation Commands" section), run `make docs-generate`, and commit `docs/cli-reference.md`.
**Test seam:** `tests/test_docs.py::_verify_sif_command` keeps only tokens found in `_SUBCOMMANDS`; add `"eval": []` so a docs example validates as `sif eval --help`.

### Anti-Patterns to Avoid
- **Re-synthesizing for `--compare`:** a changed synthesizer makes the "paired" arms use different queries and manufactures a delta. Use the saved run's query set.
- **Applying the 0.60 overlap budget to the title leg:** a title query is verbatim the title, so its Jaccard against "title plus opening text" is ~1.0 and every title query would be rejected. Treat the title leg as the exact-term category and make budgets per-leg (see A1/Open Question 1).
- **Storing document content in saved runs:** violates D-10 and the privacy rule; store paths/ids only.
- **Using `hash()` for sampling/splitting:** salted per process; the "same corpus" would yield different query sets across runs.
- **Passing only `score_cutoff` and forgetting `scorer=fuzz.ratio`:** `process.extract` defaults to `WRatio`, silently changing the algorithm and the cutoff meaning.
- **Asserting exact rapidfuzz scores in tests:** py3.10 resolves 3.14.5, py3.11+ resolves 3.14.6; assert membership/order and use `pytest.approx` only where a score is displayed.
- **Treating a suppressed group as zero:** emit an explicit `suppressed: true`/null record and list the group name.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| nDCG/Hit/precision/recall/percentile | New metric implementations | `sif.search.benchmark` functions (`ndcg_at_k`, `hit_at_k`, `percentile`, `warrants_default_change`) | Already tested and pinned by Phase 16; duplicate math drifts. |
| Fixture parsing/validation | A personal-only relevance model | `SearchEvaluator` legacy `{"queries", "relevant_docids"}` path | D-04 locks this schema; the parser already enforces one-schema-per-fixture [VERIFIED: src/sif/search/benchmark.py:453-484]. |
| Edit-distance similarity | A Python Levenshtein/Indel loop | `rapidfuzz.fuzz.ratio` / `process.extract` | Measured 12.2 ms/query for the Python loop vs 1.7 ms for `extract`. |
| Stability hashing | Builtin `hash()` or indexing | `hashlib.sha256` over normalized text | Only hashlib is stable across runs/machines. |
| Bootstrap | SciPy/NumPy RNG stack | `random.Random(seed)` + `benchmark.percentile` | No new dependency; deterministic; the algorithm is ~20 lines. |
| JSON schema validation | Ad-hoc truthiness checks only | Explicit type/range/version validation with caps | Saved runs are untrusted input; Pydantic is available but explicit checks keep bool/int and NaN handling honest. |

**Key insight:** the only genuinely new algorithms in this phase are sampling/synthesis and the paired bootstrap; everything numeric already exists in `benchmark.py`. Reuse it and spend the complexity budget on the comparison contract and determinism.

## Common Pitfalls

### Pitfall 1: The title-leg overlap contradiction (D-05 vs D-01/D-04)
**What goes wrong:** applying `token Jaccard ≤ 0.60` against "title plus opening text" to a title/H1-derived query rejects essentially every title query (Jaccard ≈ 1.0), so the exact-term leg silently disappears.
**Why it happens:** D-05 says "per-leg budget" but defines one budget; D-01/D-04 make the title leg verbatim title text.
**How to avoid:** make budgets per leg: title = exempt (or 1.0, reported as "exact-term leg, not budgeted"), body = 0.60 against title + first ~200 chars, replay = no synthesis (no budget). Report the applied budget and rejection counts per leg. This is a user-visible interpretation — flag it in discuss/plan (A1/Open Question 1).
**Warning signs:** title rejection count equals title query count; the report has no title-leg rows.

### Pitfall 2: Saved-run comparison that is not actually paired
**What goes wrong:** `--compare` re-synthesizes queries under the current code; the two arms answer different query sets, and the "delta" mixes a query-set change with a ranking change.
**Why it happens:** the synthesized set is deterministic for a fixed corpus, but any synthesis-code change (or an eligibility change) moves it.
**How to avoid:** on `--compare`, evaluate exactly the loaded run's query records; do not re-sample. New synthesis happens only on a fresh run.
**Warning signs:** comparison report shows a different query count than the baseline; deltas whose per-query joins are missing.

### Pitfall 3: Small-N noise presented as precision
**What goes wrong:** one query contributes ~1/N to mean nDCG (at N≈71, ~0.014), larger than the 0.01 tie rule; a "win" of 0.01 on 50 queries is inside noise.
**Why it happens:** the instrument prints four-decimal metrics and a delta without intervals.
**How to avoid:** always print N, `1/N`, the bootstrap CI, and helped/hurt/unchanged counts; gate on both CI-excludes-zero and mean Δ≥0.01; suppress groups with N<10 and name them.
**Warning signs:** a report with a winner but no CI; group rows with count 0 or 1.

### Pitfall 4: The first-letter bucket's recall hole is the real QUAL-01 win
**What goes wrong:** the temptation is to attribute "higher recall" to the new cutoff. The measured evidence says otherwise: the bucket recalls 7.0% of first-letter typos at k=3; the full scan at 75 recalls 100%; cutoff 70 buys no more recall than 75.
**Why it happens:** `_close_matches` builds `bucket = [term for term in self._terms if abs(ord(term[0]) - first) <= 1]` [VERIFIED: src/sif/search/suggest.py:264-266], so a typo whose first letter is ≥2 codepoints away never enters difflib.
**How to avoid:** test a first-letter typo explicitly (`xuantum` → `quantum`, measured Indel 85.7), add a full-vocabulary spy assertion, and report the bucket-vs-full recall measurement in the SUMMARY.
**Warning signs:** the DYM tests still monkeypatch `difflib.get_close_matches`; the new test only checks same-first-letter typos.

### Pitfall 5: `process.extract` API/return-shape mistakes
**What goes wrong:** treating the return as `difflib.get_close_matches`'s list of strings, forgetting the explicit `scorer=fuzz.ratio` (default is `WRatio`), or assuming `limit=n` guarantees n results.
**Why it happens:** the two libraries' APIs look interchangeable but are not.
**How to avoid:** unpack `(choice, score, index)`; pass `scorer=fuzz.ratio` and `score_cutoff=75.0`; treat `limit` as a cap after cutoff.
**Warning signs:** `ValueError: too many values to unpack`; DYM results ordered differently than the old tests expect; suggestions from a different scorer.

### Pitfall 6: Cutoff boundary float behavior
**What goes wrong:** `resturant` → `restaur` scores exactly 75.0 on both difflib (0.75) and rapidfuzz (75.0); a change to `>` or an off-by-epsilon cutoff drops it. Measured: `fuzz.ratio("resturant", "restaur")` returns `75.0` exactly and `process.extract` keeps it at `score_cutoff=75` [VERIFIED: local measurement, rapidfuzz 3.14.5].
**Why it happens:** the cutoff semantics are `>=` for a similarity scorer, and Indel normalization by `len1+len2` lands on a round number here.
**How to avoid:** pin the boundary in a test; use `float(75)`; do not add an epsilon; document the pair in the phase SUMMARY.
**Warning signs:** the existing `resturant → restaur` test starts failing at exactly the chosen constant.

### Pitfall 7: Python 3.10 vs 3.11+ dependency resolution
**What goes wrong:** CI runs 3.10–3.13 and uses `uv sync --frozen`; rapidfuzz 3.14.6 dropped 3.10. A lock that only contains 3.14.6 breaks the 3.10 cells; a test asserting the exact version breaks the others.
**Why it happens:** `requires-python` splits the resolution fleet (Phase 17 already documented this pattern for torch/httpx2).
**How to avoid:** pin `>=3.14.5,<4`, run `uv lock`, commit it, and let markers resolve 3.14.5 on 3.10 / 3.14.6 on 3.11+. Do not assert exact transitive versions.
**Warning signs:** `uv sync --frozen` fails on the 3.10 jobs; `uv.lock` lacks a cp310-compatible rapidfuzz entry.

### Pitfall 8: Documentation is a CI gate, and the generator drops leaf groups
**What goes wrong:** adding `eval` to `main.py` without regenerating `docs/cli-reference.md` fails the docs workflow (`git diff --exit-code`). Worse, `traverse_commands` returns only leaves, so a `click.Group` with no subcommands produces no section at all [VERIFIED: scripts/generate_cli_ref.py:90-102].
**Why it happens:** the generator was written for populated groups.
**How to avoid:** fix `traverse_commands` to treat an empty group as a leaf, add the eval group to `GROUP_ORDER`, run `make docs-generate`, and update `tests/test_docs.py::_SUBCOMMANDS` with `"eval": []`.
**Warning signs:** `docs/cli-reference.md` shows `eval` in the tree but has no options table; docs CI fails on a clean tree.

### Pitfall 9: Cross-platform determinism of sampling/splitting
**What goes wrong:** the same corpus yields different query sets/splits on macOS vs Linux because of Unicode normalization or salted hashing.
**Why it happens:** macOS filenames may be NFD; `hash()` is salted.
**How to avoid:** `unicodedata.normalize("NFC", ...)` before hashing/tokenizing; `hashlib.sha256`; sort with explicit keys; never use set iteration order for output.
**Warning signs:** a saved run's fingerprint matches but its query set differs; split counts differ per machine.

### Pitfall 10: Memory and privacy in corpus scanning
**What goes wrong:** `fetchall()` of `documents.content` loads the whole KB; or a saved run accidentally stores content.
**Why it happens:** the simplest SQL selects all columns and materializes rows.
**How to avoid:** iterate the cursor, select only `id, path, title, content, checksum, file_size`, release content after synthesizing, and validate that saved-run records contain no content field. Document that query strings are personal data stored locally only.
**Warning signs:** eval memory grows with corpus size; JSON files contain note bodies.

### Pitfall 11: CJK tokenization limits
**What goes wrong:** the FTS porter tokenizer treats a contiguous CJK run as one term; vocab-based DYM is meaningless for Chinese, and a per-language report can look empty or artificially easy.
**Why it happens:** verified in PITFALLS.md (SQLite 3.51.0): `如何配置混合搜索引擎的权重` is one vocab term; `MATCH '配置'` returns 0.
**How to avoid:** report per language; construct ZH title/body queries as exact contiguous runs (known-item behavior) and state that ZH lexical recall is bounded by the tokenizer, not the embedder; do not claim a ZH DYM improvement. For length buckets, count each CJK ideograph as one unit so a 12-character Chinese query is not "short".
**Warning signs:** the `zh` cell is empty or all-1.0; a Chinese typo gets no suggestion.

## Code Examples

### Verified existing seam: legacy fixture parsing (reuse, don't rewrite)
```python
# Source: src/sif/search/benchmark.py:480-483 (read this session)
# Legacy items: relevance maps docid -> grade 1; no category
# or split, so they never feed the per-category breakdown.
grades = {str(docid): 1 for docid in item["relevant_docids"]}
self.query_items.append(QueryItem(query=str(item["query"]), grades=grades))
```
The personal bench can therefore build `{"relevance_key": "docid", "queries": [{"query": q, "relevant_docids": [target_doc_id]}]}` and get rank-sensitive known-item nDCG@10 with no new label format.

### Verified existing seam: DYM contracts to preserve
```python
# Source: src/sif/search/suggest.py:124-152 (read this session)
def _probe(self, fts_query: str) -> bool:
    try:
        row = self.db.execute(
            "SELECT 1 FROM documents_fts WHERE documents_fts MATCH ? LIMIT 1",
            (fts_query,),
        ).fetchone()
    except sqlite3.OperationalError:
        logger.warning("suggestion probe unavailable; treating as no match", exc_info=True)
        return False
    return row is not None

def _hits(self, variant: str) -> bool:
    return self._probe(BM25Searcher(self.db)._build_fts_query(variant))
```
Every emitted DYM variant still flows through `_hits`; the rapidfuzz swap changes only how candidate terms are found.

### rapidfuzz full-vocab replacement (measured shape)
```python
# Source: rapidfuzz official API docs + local measurement with rapidfuzz 3.14.5
from rapidfuzz import fuzz, process

_DYM_CUTOFF = 75.0

def close_matches(terms_sorted: list[str], token: str, n: int = 3) -> list[str]:
    matches = process.extract(
        token, terms_sorted, scorer=fuzz.ratio, limit=n, score_cutoff=_DYM_CUTOFF
    )
    matches.sort(key=lambda m: (-m[1], m[0]))
    return [term for term, _score, _index in matches]
```
Measured on this machine (macOS arm64, Python 3.13.9, rapidfuzz 3.14.5):
| Operation | Time per query | Vocab |
|-----------|----------------|-------|
| `process.extract` full vocab, cutoff 75 | 1.70 ms | 72,999 terms |
| `process.extract` full vocab, no cutoff | 1.92 ms | 72,999 terms |
| `process.cdist` full vocab | 3.53 ms | 72,999 terms |
| Direct `fuzz.ratio` Python loop | 12.24 ms | 72,999 terms |
| Current difflib first-letter bucket | 5.93 ms | 72,999 terms |
| difflib full vocab | 51.26 ms | 72,999 terms |

### Cutoff re-measurement evidence (measured this session)
Typos generated deterministically from the vocabulary (internal transposition/substitution for the first table; first-letter substitution for the second):
| Vocab | Cutoff 70 recall@3 | Cutoff 75 recall@3 | Cutoff 80 recall@3 | Bucket (difflib 0.75) recall@3 |
|-------|--------------------|--------------------|--------------------|-------------------------------|
| Committed bench corpus (422 porter stems) | 0.965 (1.27 suggestions/query) | 0.965 (1.10) | 0.789 (0.84) | 0.965 (same-first-letter typos) |
| Synthetic 73k terms | 1.000 (1.47) | 1.000 (1.00) | 1.000 (1.00) | 1.000 (same-first-letter typos) |
| Committed bench corpus, **first-letter typos** | 1.000 | 1.000 | 0.813 | **0.070** |

The 0.070 vs 1.000 row is the QUAL-01 recall fix; the cutoff choice is 75 because 80 loses recall and 70 only adds candidates.

### Deterministic sample + split
```python
def sample_key(path: str, checksum: str) -> bytes:
    return hashlib.sha256(f"{path}\0{checksum}".encode("utf-8")).digest()

# sampled = sorted(docs, key=lambda d: (sample_key(d.path, d.checksum), d.path))[:n_docs]
```
Prefix the query split with NFC + casefold + whitespace collapse as in Pattern 2.

### CLI group skeleton
```python
@click.group("eval", invoke_without_command=True)
@click.option("--personal", is_flag=True, help="Measure quality on the indexed personal corpus")
@click.option("--compare", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--no-save", is_flag=True, help="Do not write the synthesized run to the cache dir")
@click.option("--bm25-only", is_flag=True, help="Explicitly skip the embedder (hybrid is the default)")
@click.option("-n", "--limit", default=10, help="Results per query")
@click.option("-c", "--collection", multiple=True, help="Collection to evaluate")
@click.option("--all", "search_all", is_flag=True, help="Evaluate all collections")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def eval_group(
    ctx: click.Context,
    personal: bool,
    compare: Path | None,
    no_save: bool,
    bm25_only: bool,
    limit: int,
    collection: tuple[str, ...],
    search_all: bool,
    output_json: bool,
) -> None:
    if ctx.invoked_subcommand is None:
        if not personal:
            raise click.UsageError("--personal is required (or pass a subcommand)")
        run_personal(ctx, compare, no_save, bm25_only, limit, collection, search_all, output_json)
```
Per Click's docs, group options are parsed before the subcommand and `ctx.invoked_subcommand` is `None` when no subcommand is given [CITED: click.palletsprojects.com/en/stable/commands-and-groups/].

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Committed synthetic fixture only (`sif bench`) | Personal known-item bench (`sif eval --personal`) + committed fixture | v1.2 Phase 18 | The fixture remains the defaults gate; the personal bench is a third instrument for local decisions. |
| Runtime-random or fixture-fixed splits | Deterministic sha256 query-text split, 50/50 with held-out ≥25 | Phase 18 (D-06) | The same corpus yields the same split across runs; saved runs are comparable. |
| Point-estimate deltas | Paired bootstrap 95% CI + 0.01 tie rule + 1/N floor | Phase 18 (D-07) | Small-N "wins" are visibly inside noise. |
| difflib + first-letter bucket | rapidfuzz `fuzz.ratio` full-vocab Indel | Phase 18 (D-14) | ~1.7 ms/query at 73k; first-letter recall 7% → 100%. |
| Graded synthetic labels | Binary known-item labels (target=1, others=0) | Phase 18 (D-04) | nDCG becomes a rank-sensitive hit metric; the report must say so. |

**Deprecated/outdated:**
- `difflib.get_close_matches` in `suggest.py` and the `_ratio` helper: remove with the swap.
- The `TestCoreBudget` difflib spy: rewrite against `process.extract` / full-vocabulary choice count.

## Assumptions Log

> Claims tagged `[ASSUMED]` or decisions the planner must confirm before locking.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The title leg is exempt from the 0.60 overlap budget; budgets are per-leg (title exact-term, body 0.60) | Pitfall 1; synthesis design | Applying 0.60 to titles rejects the entire title leg; the report loses its exact-term signal. |
| A2 | `process.extract` over a pre-sorted `self._terms` is the intended call shape; index tie-break equals lexical asc; the df tie-break is unreachable for distinct terms | Pattern 6 | If df must influence selection, `limit=n` must be widened and re-ranked; otherwise the documented tie-break is only nominal. |
| A3 | `SearchEvaluator` can gain `evaluate_per_query()` without changing `sif bench` output | Pattern 3 | A `to_dict()` change would break Phase 16 snapshot/JSON contracts. |
| A4 | Saved runs may store retrieved top-k paths in addition to D-10's query fields (never content) | Pattern 5 | Without retrieved lists, `--compare` cannot recompute the baseline arm; storing content would violate privacy/D-10. |
| A5 | `--compare` evaluates the saved run's query set, not a freshly synthesized one | Pattern 5; Pitfall 2 | Re-synthesis breaks pairing and manufactures deltas. |
| A6 | Replay queries are not assigned tuning/held-out splits and never gate default changes | Replay design | Treating replay as a tuning signal would violate D-02's stability-not-quality contract. |
| A7 | ~1.7 ms/query at 73k terms measured here generalizes to CI within the ≤10 ms budget | Standard stack; QUAL-01 | A slow/fallback build (no C extension) could exceed 10 ms; tests use a generous wall bound and record the measured p50. |
| A8 | Cutoff 75.0 is the measured choice (70 adds candidates, 80 loses recall) | Pattern 6 | A different vocabulary could shift the precision/recall optimum; the constant is pinned with evidence and a test. |
| A9 | Language thresholds `zh ≥ 0.5`, `en < 0.1`, CJK-per-character length units | Synthesis design | Discretionary; tests must pin whichever thresholds the planner chooses. |
| A10 | A leaf-group fix in the docs generator is acceptable scope for `sif eval` | Pattern 7 | Without it the new command has no generated CLI reference section. |
| A11 | Corpus fingerprint = sha256 over sorted `path\0checksum\0file_size`, truncated; mtime excluded | Pattern 5 | Including mtime would refuse comparisons after touch-only changes; excluding checksum would miss content edits. |
| A12 | DB-backed tests can use `ConceptEmbedder` + `build_bench_db`-style fixtures without a model download | Validation | A real-model dependency would make CI slow/flaky; the embed extra is present but not needed for unit tests. |

## Open Questions (RESOLVED)

All twelve questions are resolved by the phase plans; each item records the decision inline.

1. **Title-leg overlap budget (highest priority).** D-05's single 0.60 budget is incompatible with a verbatim title query.
   - What we know: the title leg is the exact-term category (PITFALLS Pitfall 4 explicitly recommends keeping exact-term and paraphrased categories distinct).
   - What's unclear: whether the user intended "per-leg budget" to mean per-leg *values* (title exempt) or the same 0.60 applied per leg.
   - Recommendation: title = exempt and reported as exact-term; body = 0.60 vs title + first 200 chars; replay = no synthesis. Record the applied budgets in the report and SUMMARY. Confirm in plan/discuss if the planner wants to re-litigate.
   - **Resolved (18-02):** per-leg budgets — title is exact-term/unbudgeted (`budget=None`, `exact_term=True`, overlap rejections always 0), body uses token Jaccard ≤0.60 against title + first 200 chars, replay synthesizes nothing; all three rejection counts are reported per leg.
2. **Sampling arithmetic.** D-03 says "minimum 50 queries, maximum 500, proportional to corpus size."
   - Recommendation: sample `n_docs = min(eligible_docs, 250)` docs (floor 25 once ≥50 docs exist), generate one title + one body query each → 50–500 queries; if accepted queries fall below 50 after rejection, widen the sample up to the corpus; if still short, fail with an explicit message.
   - **Resolved (18-01/18-02):** the known-item run starts from `INITIAL_SAMPLE_DOCUMENTS = 50` documents (strictly smaller than the cap whenever the corpus exceeds 50 docs) in deterministic `(sha256, path, id)` order, and `ensure_heldout` doubles the slice toward `min(eligible, MAX_SAMPLE_DOCUMENTS=250)` while accepted queries < 50 OR held-out < 25; `run_personal` invokes the widening before evaluation. Only a floor still unmet at the cap raises a counted `ValueError`. The whole-corpus pass is metadata-only; bodies load for the sampled subset only.
3. **Saved-run fields.** D-10 says "query/path/split/leg/language/grade only."
   - Recommendation: also store `target_doc_id` and `retrieved` (top-k paths), because `--compare` needs them; never store content. Version the schema (`version: 1`) and validate on load.
   - **Resolved (18-03):** saved runs store `target_doc_id` plus rank-ordered `retrieved` paths in addition to D-10's fields, version 1, full envelope + record validation, never content.
4. **`--compare` query set.** Recommendation: use the saved run's exact query set and re-run it against the current engine; fresh synthesis only on a non-compare run.
   - **Resolved (18-03):** `--compare` evaluates exactly the saved query set in saved order; no re-synthesis, overlap filter, or split reassignment.
5. **Embedder identity on comparison.** Phase 21 adds a persisted identity; Phase 18 can record `model_name`, `model_type`, and `dimension` in the saved run.
   - Recommendation: record and warn on mismatch; refuse only on corpus-fingerprint mismatch (D-12). Refusing on model identity now would block legitimate same-model re-runs before Phase 21 exists.
   - **Resolved (18-01/18-03):** the run records `model_name`/`model_type`/`dimension`; a comparison mismatch warns on stderr, and only the corpus fingerprint refuses.
6. **Missing index / insufficient corpus exit behavior.** `sif bench` prints a notice and returns 0; `sif eval --personal` has explicit 50-doc/50-query thresholds.
   - Recommendation: ClickException (exit 1) with "No index found. Run 'sif index update' first." and an explicit count on insufficient corpus — a measurement command should fail loudly.
   - **Resolved (18-01/18-02):** missing index and insufficient counts exit 1 with named counts and the `sif index update` remedy; the measurement command fails loudly.
7. **Replay leg with no history.** Recommendation: report `available: false` with the CLI-only bias note and exit 0; never fail the whole run.
   - **Resolved (18-02):** an empty `query_log` yields `replay.available: false`, a zero count, and the CLI-only bias note; the run still exits 0.
8. **Personal bench latency reporting.** Recommendation: skip warm-up/latency (not a requirement); one search per query. If added later, reuse `measure_query_times`.
   - **Resolved (18-01):** no latency reporting; one search per query and no clock parameter in `evaluate_per_query`.
9. **Body snippet shape.** Recommendation: strip fenced code/URLs/markdown, choose a deterministic prose sentence from later than the opening, take up to ~10 tokens, reject if <4 tokens or if it fails the overlap budget; count rejections.
   - **Resolved (18-02):** deterministic later-prose sentence, markup/URL/code stripped, at most 10 tokens, reject <4 tokens, then the 0.60 Jaccard budget; rejections counted per leg.
10. **Duplicate queries.** Recommendation: normalize and dedupe; if the same query targets different documents, keep the first in deterministic order and count a rejection (avoids ambiguous known-item labels).
    - **Resolved (18-01/18-02):** NFC + casefold + whitespace normalization; declared leg order (title before body); first record kept, each later collision counted as a duplicate.
11. **Cutoff measurement artifact.** Recommendation: keep the measurement as a unit test (generated typo recall at 75) plus the SUMMARY evidence table; no new CLI knob and no extra script unless the planner wants reproducibility outside tests.
    - **Resolved (18-04):** `_DYM_CUTOFF = 75.0` is an internal constant pinned by recall/boundary/determinism tests; the 70/75/80 evidence table and measured p50 are recorded in `18-04-SUMMARY.md`; no setting, flag, or script.
12. **`sif eval` fixture alias.** Recommendation: stay personal-only in Phase 18; the group leaves room for a future fixture subcommand/flag.
    - **Resolved (18-01/18-03):** personal-only in Phase 18; the `eval` group shape leaves room for an additive fixture subcommand later.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | Runtime, tests | ✓ | 3.13.9 local; CI 3.10–3.13 | — |
| `uv` | Lock/sync, CI `--frozen` | ✓ | 0.13.7 | `pip install -e` for ad-hoc dev only |
| `pytest` | Tests | ✓ | 9.1.1 local; CI lock 9.0.3 | — |
| `ruff` | Lint/format gate | ✓ | 0.15.11 | — |
| `ty` | Type gate | ✓ | 0.0.97 | — |
| `sqlite-vec` | Hybrid/vector tests | ✓ | 0.1.9 | DB-backed tests skip (existing discipline) |
| `sentence-transformers` / `torch` | Embed extra, manual real-model run | ✓ | 5.4.1 / 2.7.1 | `--bm25-only` explicit path; tests use `ConceptEmbedder` |
| `rapidfuzz` | DYM runtime | ✗ in the project env (only a temp probe install) | 3.14.5 measured | None by design (D-13); `uv lock` + `uv sync` installs it |

**Missing dependencies with no fallback:**
- `rapidfuzz` until the lock is updated — this is a planned install step, not a blocker.

**Missing dependencies with fallback:**
- Real embedding model / downloaded weights — unit tests use `ConceptEmbedder`; a real-model personal run is a manual, local-only verification.

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json`; this section is required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (CI-locked 9.0.3; local 9.1.1), pytest-cov, pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`, `fail_under = 90` |
| Quick run command | `pytest tests/unit/search/test_personal_bench.py tests/unit/cli/test_eval.py tests/unit/search/test_suggest.py -x --no-cov` |
| Full suite command | `pytest` (with coverage; CI runs `env -u FORCE_COLOR NO_COLOR=1 uv run --frozen pytest`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVAL-01 | Title/H1 and body-snippet synthesis is deterministic and label-free | unit | `pytest tests/unit/search/test_personal_bench.py -x --no-cov` | ❌ Wave 0 |
| EVAL-01 | Legacy fixture + `SearchEvaluator` known-item metrics (target=1, others=0) | unit | `pytest tests/unit/search/test_personal_bench.py::TestKnownItemFixture -x --no-cov` | ❌ Wave 0 |
| EVAL-01 | query_log replay leg: rows replayed, no-baseline recorded, baseline stability computed, CLI-only bias present | unit | `pytest tests/unit/search/test_personal_bench.py::TestReplay -x --no-cov` | ❌ Wave 0 |
| EVAL-01 | `sif eval --personal` table + `--json`, saved path, `--no-save`, thresholds, embed remedy, `--bm25-only` | cli | `pytest tests/unit/cli/test_eval.py -x --no-cov` | ❌ Wave 0 |
| EVAL-02 | Token-Jaccard ≤0.60 enforcement per leg; rejection counts reported | unit | `pytest tests/unit/search/test_personal_bench.py::TestOverlapBudget -x --no-cov` | ❌ Wave 0 |
| EVAL-02 | Per-leg × per-language × length-bucket groups; <10 suppression + names | unit | `pytest tests/unit/search/test_personal_bench.py::TestGroups -x --no-cov` | ❌ Wave 0 |
| EVAL-02 | sha256 50/50 split stable; held-out ≥25; widen sampling | unit | `pytest tests/unit/search/test_personal_bench.py::TestSplit -x --no-cov` | ❌ Wave 0 |
| EVAL-02 | Paired deltas, seeded bootstrap CI, 0.01 gate, 1/N floor, helped/hurt/unchanged | unit | `pytest tests/unit/search/test_personal_bench.py::TestNoiseGate -x --no-cov` | ❌ Wave 0 |
| EVAL-02 | Corpus fingerprint + `--compare` mismatch refusal + saved-run validation | unit + cli | `pytest tests/unit/search/test_personal_bench.py::TestSavedRun tests/unit/cli/test_eval.py -x --no-cov` | ❌ Wave 0 |
| QUAL-01 | Full-vocabulary rapidfuzz scan; no first-letter bucket; first-letter typo recall | unit | `pytest tests/unit/search/test_suggest.py::TestDidYouMean tests/unit/search/test_suggest.py::TestCoreBudget -x --no-cov` | ✅ update |
| QUAL-01 | Cutoff 75 boundary + below-cutoff behavior + deterministic tie-break | unit | `pytest tests/unit/search/test_suggest.py -x --no-cov` | ✅ update |
| QUAL-01 | Probe/hit contracts and prefix/history sections unchanged | unit + cli | `pytest tests/unit/search/test_suggest.py tests/unit/cli/test_suggest.py -x --no-cov` | ✅ existing |
| QUAL-01 | ≤10 ms core budget with generous CI headroom; measured p50 recorded | unit + manual | `pytest tests/unit/search/test_suggest.py::TestCoreBudget -x --no-cov` (manual evidence in SUMMARY) | ✅ update |
| ALL | Lint/format/type/docs gates | static | `ruff check src tests && ruff format --check src tests && ty check src/sif` | ✅ |
| ALL | Generated docs are current | docs | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | ✅ after changes |
| ALL | Committed bench fixture untouched | drift | `python scripts/generate_bench_fixture.py --check` | ✅ |

### Sampling Rate
- **Per task commit:** the quick run command above plus `ruff check`/`ruff format --check` on touched files.
- **Per wave merge:** `pytest` full suite (coverage ≥90) and `ty check src/sif`.
- **Phase gate:** full suite green, docs generation diff clean, `generate_bench_fixture.py --check` clean, and the measured DYM/cutoff evidence recorded in the SUMMARY.

### Wave 0 Gaps
- [ ] `tests/support/eval.py` — personal corpus DB builder (documents with title/content/checksum) + query_log seeding + a hermetic cache dir.
- [ ] `tests/unit/search/test_personal_bench.py` — covers EVAL-01/EVAL-02 domain behavior.
- [ ] `tests/unit/cli/test_eval.py` — covers the CLI surface and saved-run path.
- [ ] `tests/unit/search/test_suggest.py` — rewrite the difflib spy/budget test; add first-letter recall and cutoff-boundary tests.
- [ ] `docs/cli-reference.md` — regenerate after adding the `eval` group (and any generator fix).
- [ ] `uv.lock` — regenerate after adding `rapidfuzz`.

## Security Domain

> `security_enforcement` is enabled (absent from config = enabled).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local CLI, no accounts. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | No multi-user boundary; cache dir is user-owned. |
| V5 Input Validation | yes | Saved-run JSON: explicit schema/version/type/range checks, size and record caps, reject NaN/Infinity, never open paths from the file; CLI options validated by Click types. |
| V6 Cryptography | yes (minimal) | `hashlib.sha256` for fingerprints/splits; no secrets, no hand-rolled crypto. |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious saved-run JSON (huge arrays, wrong types, NaN) | Denial of Service / Tampering | Cap file size and record counts; validate every field; reject non-finite numbers; fail with `ClickException`, never a traceback. |
| Rich markup injection from query text/paths in table output | Spoofing | `rich.markup.escape()` before printing user/vocab-derived cells (existing convention). |
| SQL injection via replay/synthesis text | Tampering | Reuse `BM25Searcher._build_fts_query` and parameterized SQL; never interpolate query text into SQL. |
| Path traversal from saved paths | Information Disclosure | Never open a path read from the saved run; treat it as an opaque comparison key. |
| Personal query leakage | Information Disclosure | Saved runs live under the user cache dir, never in the repo; no upload; document local-only; tests use tmp paths. |
| Unbounded workload (B×N bootstrap, 500+500 queries) | Denial of Service | Caps at 500 synthesized + 500 replay; B=10,000; reject >10,000-query comparison files. |

## Sources

### Primary (HIGH confidence)
- In-repo source read this session: `src/sif/search/benchmark.py` (full), `src/sif/search/suggest.py` (full), `src/sif/cli/commands/bench.py` (full), `src/sif/database/schema.py:58-76,149-170`, `src/sif/database/repositories.py:645-698`, `src/sif/config/settings.py:402-411`, `src/sif/cli/commands/search.py:254-300`, `src/sif/mcp/backend.py:195-207`, `scripts/generate_cli_ref.py:90-102`, `pyproject.toml:29-41`, `.github/workflows/docs.yml:32-42`, `.github/workflows/test-matrix.yml`.
- Local measurements with `rapidfuzz==3.14.5` (macOS arm64, Python 3.13.9): `fuzz.ratio` score table, `process.extract`/`cdist`/Python-loop/difflib timings at 72,999 terms, cutoff 70/75/80 recall on the committed bench vocabulary (422 porter stems) and a synthetic 73k vocabulary, first-letter-typo recall 0.070 vs 1.000, exact 75.0 boundary.
- `pip index versions rapidfuzz` (3.14.6 latest, 3.14.5 available); PyPI JSON for 3.14.5 (`requires_python >=3.10`, MIT, 82 wheels, uploaded 2026-04-07).

### Secondary (MEDIUM confidence)
- rapidfuzz docs: `fuzz.ratio` normalized Indel 0–100 and `process.extract` signature/tie semantics — https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html, https://rapidfuzz.github.io/RapidFuzz/Usage/process.html
- Click commands-and-groups (nested groups, `invoke_without_command`, option parsing) — https://click.palletsprojects.com/en/stable/commands-and-groups/
- Project research: `.planning/research/STACK.md` §(b) rapidfuzz, `.planning/research/PITFALLS.md` Pitfalls 4/6/8 and the rapidfuzz/CJK rows, `.planning/research/SUMMARY.md` Phase 2.

### Tertiary (LOW confidence)
- Known-item synthesis literature (Azzopardi, de Rijke, Balog SIGIR 2006/2007) and pseudo-desktop personal-search work; the TU Delft synthetic-vs-real ranking agreement figures are cited via PITFALLS.md, not re-fetched.
- Paired bootstrap guidance (Smucker et al. CIKM 2007; Efron & Tibshirani 1993) as summarized by a secondary teaching source; the percentile algorithm is standard and independently straightforward.
- Query-log replay stability practice (Jaccard@k + top-1 stability vs a baseline snapshot) from operational tooling write-ups; Jaccard ignores order, so pair it with top-1/rank metrics.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — rapidfuzz version, wheels, API, and performance verified from PyPI/docs/local measurement; the package-legitimacy seam returned SUS only for missing metadata.
- Architecture: HIGH — every integration seam was read this session; the main open design item is the title-leg overlap interpretation (A1).
- Pitfalls: MEDIUM-HIGH — the code-level and measurement pitfalls are verified; the statistical/report thresholds are standard but discretionary.
- Cross-machine performance: MEDIUM/LOW — the 1.7 ms measurement is one machine; CI tests use generous bounds and the SUMMARY records evidence.

**Research date:** 2026-11-14
**Valid until:** 2026-12-14 (30 days; rapidfuzz and the surrounding stack are stable). Re-check the rapidfuzz cutoff measurement if the vocabulary scale or rapidfuzz minor version changes materially.
