---
phase: 16-bench-expansion-reranker-tuning
plan: "03"
subsystem: search
tags: [benchmark, fixture, sqlite-vec, fts5, cjk, determinism, pytest]

# Dependency graph
requires:
  - phase: 16-bench-expansion-reranker-tuning (Plan 01)
    provides: resolve_corpus_root/result_key path-keyed relevance rule, CATEGORIES/SPLITS/GRADE constants, SearchEvaluator.report -> BenchReport, and the CLI bench seams this pack exercises
provides:
  - tests/support/bench.py — ConceptEmbedder (Embedder protocol) and build_bench_db deterministic in-memory index builder (real SchemaManager + FTS triggers + vec0)
  - Committed synthetic pack at tests/fixtures/bench/ — 150 generated corpus docs + queries.json with 56 graded queries (36 tuning / 20 held-out) across keyword/synonym/multilingual/rival
  - scripts/generate_bench_fixture.py — seeded deterministic generator with a --check drift gate (also flags unexpected files)
  - tests/unit/search/test_bench_fixture.py — protocol, schema, end-to-end, contract, path-safety, retrieval and split-non-interference tests
  - CLI join proof test_cli_bench_committed_pack_nonzero_ndcg pinning bench_cmd on the exact committed fixture path
affects: [16-04 sweep, 16-05 held-out snapshot]

# Actuals (#2632) — same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 34614
  tasks: 3
  commits: 3
plan_head_before: 17093074d83d1e7d1f007b9eccbddeadd6520846
plan_head_after: 2a4382fabef1c58a044bd8d5f455111ff8e2070d

# Tech tracking
tech-stack:
  added: []  # stdlib only: argparse, hashlib, json, math, pathlib, random, sqlite3
  patterns:
    - "Deterministic concept embedder: blake2b-seeded per-token unit vectors, L2-normalized bag sum, CJK runs kept as single tokens"
    - "Direct-to-schema fixture builder (fixed doc ids, FTS via triggers, vec0 rows) shared from tests/support so unit and CLI tests build the identical index"
    - "Generator-owned fixture data with a --check drift gate that also flags unexpected files (corpus is never hand-edited)"

key-files:
  created:
    - tests/support/__init__.py
    - tests/support/bench.py
    - scripts/generate_bench_fixture.py
    - tests/fixtures/bench/queries.json
    - tests/fixtures/bench/corpus/ (150 generated markdown docs)
    - tests/fixtures/bench/README.md
    - tests/unit/search/test_bench_fixture.py
  modified:
    - tests/unit/cli/test_bench.py

key-decisions:
  - "ConceptEmbedder tokens: lowercase, alphanumeric runs plus whole CJK runs — a Chinese phrase is exactly one token for both the embedder and the FTS porter tokenizer (Pitfall 3)"
  - "Relevance keys are corpus-relative (keyword/kw-003.md), never pack-relative; resolve_corpus_root joins the declared corpus_root onto the fixture directory and every result key resolves under it (D-02, Pitfall 4)"
  - "Split assignment is formula-fixed in the generator: first 9 queries per category tune, last 5 hold out — 36/20 with no runtime randomness (D-03)"
  - "Task-1's minimal 4-doc pack proved the wiring end-to-end, then was deleted and replaced by generated output in the same plan (tracer-then-expand at data level)"

patterns-established:
  - "Pattern: committed benchmark data is always generator output; --check is the drift gate and unexpected files are drift too"
  - "Pattern: _settings_mock enumerates the rerank fields (rerank_enabled/candidate_limit/relative_threshold) even though bench does not read them yet — 16-04 turns them on without mock churn"

requirements-completed: [EVAL-02]

coverage:
  - id: D1
    description: "ConceptEmbedder (Embedder protocol, deterministic, CJK-aware) + build_bench_db real-schema deterministic index builder (collection/include_by_default, fixed doc ids, FTS trigger rows, vec0 embeddings per chunk)"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_bench_fixture.py#TestConceptEmbedder/TestBuildBenchDb"
        status: pass
    human_judgment: false
  - id: D2
    description: "Committed synthetic pack: 150 seeded corpus docs across four categories + queries.json with 56 graded queries (36 tuning / 20 held-out, 5 held-out per category), grades 0-3 with 3+2 per query and rival zero-neighbors; byte-identical regeneration with a drift gate"
    requirement: EVAL-02
    verification:
      - kind: other
        ref: "command: python scripts/generate_bench_fixture.py --check (151 files, exit 0; drift probe fired exit 1 and regeneration restored byte-identical)"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_bench_fixture.py#TestFixtureContractCounts/TestFixtureContractSplitsAndCategories/TestFixtureContractGrades"
        status: pass
    human_judgment: false
  - id: D3
    description: "Path-safety and retrieval integrity: every relevance key is a relative POSIX path contained under the declared corpus root naming a committed file; every query (multilingual included) returns >=1 result on the deterministic index; tuning/held-out sets disjoint and exhaustive"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_bench_fixture.py#TestFixtureContractPaths/TestFixtureRetrievalIntegrity/TestFixtureSplitNonInterference"
        status: pass
    human_judgment: false
  - id: D4
    description: "CLI-level join proof: bench_cmd invoked on the EXACT committed tests/fixtures/bench/queries.json (no tmp copy, no explicit root, flag-minimal) exits 0 with non-zero ndcg_at_10 and hit_at_10, proving fixture-declared corpus_root joins relevance and result keys"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_bench.py#test_cli_bench_committed_pack_nonzero_ndcg"
        status: pass
    human_judgment: false

# Metrics
duration: 14 min
completed: 2026-11-08
status: complete
---

# Phase 16 Plan 03: Bench Fixture Pack Summary

**Deterministic ConceptEmbedder + direct-DB builder, and a committed 150-doc synthetic corpus with 56 graded queries (36 tuning / 20 held-out) regenerated byte-identically by a seeded drift-gated generator — proven retrievable and CLI-joined with non-zero nDCG@10**

## Performance

- **Duration:** 14 min
- **Started:** 2026-11-08T14:14:42Z
- **Completed:** 2026-11-08T14:28:52Z
- **Tasks:** 3 (Task 1 tracer verified end-to-end, then expanded)
- **Files changed:** 157 (150 generated corpus docs among them)

## Accomplishments

- `tests/support/bench.py`: `ConceptEmbedder` implements the Embedder protocol with blake2b-seeded per-token unit vectors (L2-normalized bag sum, whole-CJK-run tokens, fixed unit vector for empty text, token/text caches); `build_bench_db` raises a real SchemaManager in-memory database from the committed corpus — bench collection with `include_by_default=1`, fixed `doc-NNN` ids in sorted path order, FTS rows via the insert triggers, one chunk + one vec0 embedding per document, sqlite-vec absence pytest-skips
- Task 1 proved the slice end-to-end on a minimal 4-doc/2-query pack (tracer: non-zero nDCG, path-keyed rank-1 join), then Task 2 replaced it with the full generated pack
- `scripts/generate_bench_fixture.py`: stdlib-only, `--seed` (default 16), `--out`, `--check`; 150 docs — keyword (40 docs with unique two-syllable codenames and successor mentions), synonym (19 topics x handbook/field-guide paraphrase pairs), multilingual (18 topics x primary/companion with English prose and exact contiguous Chinese runs), rival (18 near-duplicate authoritative/draft pairs); 56 queries = 14 per category, split 9 tuning + 5 held-out per category, grades {3, 2} per query plus graded-0 neighbors for rival, relevance maps capped at 5 entries, `json.dumps(indent=2, sort_keys=True)` + trailing newline
- Drift gate proven both ways: a hand-edit fired `--check` exit 1 naming the drifted path; regeneration restored a byte-identical pack; reruns are byte-identical (verified by hashing two consecutive runs)
- Contract tests: counts (56/36/20, evaluator drops nothing), split/category validity with per-category held-out coverage, grade integrity (int 0-3, 3+2 per query, <=5 entries), path containment (relative POSIX, no `..`, `is_relative_to(root)`, names committed files), retrieval integrity (every query >=1 result, multilingual explicit), split non-interference (disjoint + exhaustive)
- Mutation-proofed: a grade changed to 7 and a deleted held-out split each failed their contract tests; restored pack re-greened everything
- CLI join proof: `bench_cmd` on the literal committed `tests/fixtures/bench/queries.json` with a patched `Database` yielding the deterministic connection, real `SearchPipeline`, `_settings_mock` extended with the rerank fields — exit 0, `ndcg_at_10 > 0`, `hit_at_10 > 0`, no explicit corpus root anywhere

## Task Commits

Each task was committed atomically:

1. **Task 1: Deterministic concept embedder + direct DB builder, proven end-to-end (tracer)** - `7ea3dbb` (feat; tracer verify re-run passed under auto mode -> expanded without checkpoint)
2. **Task 2: Seeded fixture generator and the full committed corpus** - `9fee8c3` (feat; 158 files, includes the intentional deletion of the four minimal-pack docs)
3. **Task 3: Fixture contract and corpus integrity tests** - `2a4382f` (test)

**Plan metadata:** see the docs(16-03) close-out commit (SUMMARY + STATE + ROADMAP + REQUIREMENTS)

## Files Created/Modified

- `tests/support/__init__.py` / `tests/support/bench.py` - shared deterministic embedder + in-memory index builder (imported by both unit and CLI tests)
- `scripts/generate_bench_fixture.py` - seeded generator + `--check` drift gate (also flags unexpected corpus files)
- `tests/fixtures/bench/queries.json` - 56 graded queries, `corpus_root: "corpus"`, `relevance_key: "path"`, fixed tuning/held-out splits
- `tests/fixtures/bench/corpus/{keyword,synonym,multilingual,rival}/*.md` - 150 synthetic generated docs (keyword 40 / synonym 38 / multilingual 36 / rival 36)
- `tests/fixtures/bench/README.md` - synthetic-only rule, regeneration, drift gate, categories, grading scale, tuning/held-out contract
- `tests/unit/search/test_bench_fixture.py` - 22 tests: embedder protocol/determinism, builder schema/FTS/vec0, end-to-end reports, contract/path/retrieval/split suites
- `tests/unit/cli/test_bench.py` - `_settings_mock` rerank fields + `test_cli_bench_committed_pack_nonzero_ndcg`

## Decisions Made

- Multilingual design: every Chinese phrase appears in docs as an exact contiguous run surrounded by non-CJK characters, and queries reuse that exact run (with the English phrase) — BM25's AND-of-quoted-prefix-terms matches the primary doc while the companion shares the run through the vector leg (research Pitfall 3)
- Synonym queries deliberately share only the topic headword with their docs (docs use canonical vocabulary, queries use paraphrase synonyms) so the category measures paraphrase pressure on the vector leg, not exact-term overlap
- `build_bench_db` stores resolved absolute document paths and a sha256 checksum of the file text with a fixed mtime (1.0), keeping the index byte-reproducible despite varying checkout mtimes
- The generator's `--check` treats unexpected `*.md` files under `corpus/` as drift, so hand-added docs cannot silently join the pack

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task-1 end-to-end tests generalized to the full pack during Task 2**
- **Found during:** Task 2 (pack replacement)
- **Issue:** Task 1 committed end-to-end tests pinned to the minimal pack (`num_queries == 2`, `"zephyr telemetry"`, `keyword/alpha.md`); the plan's Task 2 replaces that pack, which would leave the committed suite red between Tasks 2 and 3
- **Fix:** Both end-to-end tests now derive their expectations from the committed fixture itself (query count from the file; the path-key test targets the first query's grade-3 key), keeping them valid through Task 3's contract layer
- **Files modified:** tests/unit/search/test_bench_fixture.py
- **Verification:** 11 tests green immediately after pack replacement; 36 green after Task 3
- **Committed in:** 9fee8c3

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Sequencing adjustment required by the plan's own green-suite gates; end-state contracts unchanged, no scope creep.

## Issues Encountered

None beyond the deviation above. Two authoring-time bugs in the generator (relevance keys initially carrying a `corpus/` prefix; a duplicated syllable) were caught by self-review before the first generation run and never reached a commit.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 16-04 (sweep) can consume the pack directly: `load_fixture_queries` + `build_bench_db` give the deterministic index; tuning/held-out filtering is proven disjoint; the sweep reads tuning only per D-03/D-08
- 16-05 (held-out snapshot) gets a stable instrument: regeneration is byte-identical, so snapshot drift can only come from code, never the pack
- `_settings_mock` already carries `rerank_enabled/rerank_candidate_limit/rerank_relative_threshold`, so 16-04's bench rerank states need no mock churn
- The pack contains no real-KB content (D-01); README documents the rule and the regeneration workflow

## Verification Results

- `python scripts/generate_bench_fixture.py --check` — OK, 151 files, exit 0 (drift probe separately fired exit 1 and regeneration restored byte-identical output)
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_bench_fixture.py tests/unit/cli/test_bench.py -x --no-cov` — 36 passed
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` (full suite) — 1430 passed, 1 skipped, coverage 94.91% (fail_under=90 gate green)
- `ruff check src tests && ruff format --check src tests` — clean (generator script additionally linted clean under the same rules)
- `ty check src/sif` — 0 diagnostics (no src/ files touched this plan)
- Mutation proofs: grade 7 -> TestFixtureContractGrades failed; deleted held-out split -> split/category tests failed; restored pack green

## Self-Check: PASSED

All seven created/modified key files exist on disk (plus 150 generated corpus docs counted); all three task commits (7ea3dbb, 9fee8c3, 2a4382f) are ancestors of HEAD; commit count measured from the plan ledger (base 17093074) is 3, matching the Task Commits section.
