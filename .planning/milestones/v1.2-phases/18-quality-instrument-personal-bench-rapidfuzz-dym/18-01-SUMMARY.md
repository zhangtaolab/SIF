---
phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
plan: 01
subsystem: search/evaluation
tags:
  - personal-bench
  - known-item
  - ndcg
  - deterministic-sampling
  - click-cli
  - docs-generator

requires:
  - phase: 16-bench-expansion-reranker-tuning
    provides: "SearchEvaluator report()/graded metrics, legacy {\"queries\": [{\"query\", \"relevant_docids\"}]} fixture schema, nDCG/Hit metric math"
  - phase: 15-search-quality-configuration-hybrid-weights-query-suggestions
    provides: "CLI measurement command conventions, Settings fusion knobs (rrf_k/bm25_weight/vector_weight), EmbeddingManager loading precedent"
provides:
  - "`sif eval --personal`: title/H1 known-item evaluation on the user's own index, as a Rich table and strict JSON"
  - "SearchEvaluator.evaluate_per_query() + frozen QueryEvaluation (additive; bench output byte-identical)"
  - "personal_bench domain module: metadata-only corpus scan, sha256 deterministic sampling, title synthesis with rejection tally, legacy fixture builder, corpus fingerprint"
  - "CLI docs generator leaf-group support (a subcommand-less Click group now renders a reference section)"
affects: [18-02, 18-03]

tech-stack:
  added: []
  patterns:
    - "Whole-corpus passes select metadata columns only and iterate the cursor (no fetchall, no bodies)"
    - "Deterministic sampling via sha256(path + NUL + checksum) with path then id as explicit tie-breaks"
    - "Known-item labels reuse the legacy binary fixture schema instead of inventing a new label format"
    - "Additive evaluator surface: new per-query API while report()/to_dict() stay byte-identical"
    - "Measurement commands fail loudly with a remedy; soft-fail is reserved for diagnostic commands"
    - "Click leaf groups are rendered by the docs generator instead of silently dropped"

key-files:
  created:
    - src/sif/search/personal_bench.py
    - src/sif/cli/commands/eval.py
    - tests/support/eval.py
    - tests/unit/cli/test_eval.py
  modified:
    - src/sif/search/benchmark.py
    - src/sif/cli/main.py
    - scripts/generate_cli_ref.py
    - tests/test_docs.py
    - docs/cli-reference.md

key-decisions:
  - "Title leg is exact-term by construction: one query per sampled document, no overlap budget, target grade 1 through the legacy fixture schema (D-01/D-04)."
  - "Empty titles are rejected and counted; normalized (NFC + casefold + collapsed whitespace) duplicate titles keep the first in deterministic sample order and count each later collision."
  - "Sample order is (sha256(path\\0checksum) digest, path, id) ascending; the id is the final tie-break so a path shared by two collections has a unique stable position."
  - "Corpus fingerprint is a truncated sha256 over sorted path/checksum/file_size lines over ALL in-scope metadata before sampling; mtime is excluded."
  - "Hybrid is the default and fails loudly with the `pip install \"docsif[embed]\"` + `--bm25-only` remedy; `--bm25-only` never constructs EmbeddingManager; openai/modelscope providers are disclosed on stderr."
  - "evaluate_per_query is strictly additive: report() and BenchReport.to_dict() keys/values are unchanged, so `sif bench` output does not move."
  - "The docs generator treats a subcommand-less Click group as a leaf, and `eval` is grouped under Other Commands."

requirements-completed: [EVAL-01]

coverage:
  - id: D1
    description: "`sif eval --personal` measures title/H1 known-item queries on a real >=50-document index and renders a table plus strict JSON"
    requirement: EVAL-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestPersonalEvalCli::test_personal_run_renders_table"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestPersonalEvalCli::test_personal_json_is_strict_and_shaped"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestPersonalEvalCli::test_two_runs_emit_the_identical_query_order"
        status: pass
    human_judgment: false
  - id: D2
    description: "SearchEvaluator.evaluate_per_query/QueryEvaluation is additive and bench output is unchanged"
    requirement: EVAL-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestEvaluatePerQuery"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_bench.py"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_benchmark.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Threshold, degradation, collision, disclosure, and markup-escaping rules are loud, counted, and test-pinned"
    requirement: EVAL-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestPersonalEvalEdges"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestDisclosureAndMarkup"
        status: pass
    human_judgment: false
  - id: D4
    description: "Generated CLI reference contains a `### sif eval` section with its option table; docs drift gate is clean"
    requirement: EVAL-01
    verification:
      - kind: integration
        ref: "make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-11-14
status: complete
plan_head_before: 661dde113c964b817d2b452cd6bc328d05fe41aa
plan_head_after: bbaf3ce5e56e362e318f4e729e3f6937012cd53c
actuals:
  tokens: 13779
  tasks: 3
  commits: 4
---

# Phase 18 Plan 01: Personal Eval Title-Leg Tracer Summary

**`sif eval --personal` synthesizes one title/H1 known-item query per deterministically sampled document and reports nDCG@10/Hit@10 on the user's own index as a table or strict JSON, with an additive per-query evaluator API and a generator-owned CLI reference section.**

## Performance

- **Duration:** 8 min (7m37s measured to the final code commit; metadata commit follows)
- **Started:** 2026-11-14T14:33:16Z
- **Completed:** 2026-11-14T14:40:53Z
- **Tasks:** 3 completed
- **Files modified:** 9 (4 created, 5 modified)
- **Estimate vs actual:** plan estimated 60,000 tokens; realized diff measured at 13,779 tokens (chars/4 over the `-U0` diff of src/scripts/tests/docs), 4 commits.

## Accomplishments

- End-to-end tracer proven on a real file-backed 60-document tmp index (real SchemaManager schema, FTS triggers, vec0 embeddings via `ConceptEmbedder`): `sif eval --personal` exits 0 and renders Document/Sampled/Queries/NDCG@10/Hit@10/rejection rows; `--json` strict-parses with integer counts and `metrics.num_queries == queries.accepted`.
- `SearchEvaluator.evaluate_per_query()` and frozen `QueryEvaluation` added without touching `report()` or `BenchReport.to_dict()`; the pinned flat-key set and values are asserted unchanged and all 71 existing bench tests still pass.
- Determinism pinned: sampling is stable under input reordering and shared-path documents get distinct stable positions; two CLI runs over the same DB emit the identical 60-query order.
- Whole-corpus pass is metadata-only: the SELECT names `id, path, title, checksum, file_size` and never `content`; bodies never reach output (asserted absent from stdout/JSON).
- Measured edge behavior (D-11, EVAL-01 edges): <50 documents and <50 accepted queries exit 1 with counts and the `sif index update` remedy; a missing embed backend exits 1 with the exact `pip install "docsif[embed]"` + `--bm25-only` remedy; `--bm25-only` never constructs `EmbeddingManager`; empty titles and normalized duplicate titles are counted and never emitted.
- Privacy/disclosure (T-18-15): openai/modelscope model types print a stderr notice that synthesized query text reaches the provider and name `--bm25-only`; the report names the provider/model identity in JSON and the table footer; `--bm25-only` prints no disclosure.
- Docs seam: `traverse_commands` now treats a subcommand-less group as a leaf, `eval` is grouped under Other Commands, and `docs/cli-reference.md` gains the generated `### sif eval` section with all six options. The docs drift gate is clean.

## Task Commits

Each task was committed atomically (normal hooks, no `--no-verify`):

1. **Task 1: End-to-end `sif eval --personal` title-leg path** - `715b270` (feat)
2. **Task 2: Threshold, degradation, and collision rules pinned by CLI tests** - `c7f6b55` (test)
3. **Task 3: Docs generator leaf-group fix, eval section, generated docs gate** - `77ab436` (docs)
4. **Rule 2 verification gap: provider disclosure + markup escaping tests** - `bbaf3ce` (test)

**Plan metadata:** `docs(18-01): complete personal eval title-leg plan` (the commit following this SUMMARY)

## Files Created/Modified

- `src/sif/search/personal_bench.py` (new) - pure domain module: constants, `DocumentRecord`, `SynthesizedQuery`, `SynthesisResult`, `normalize_text`, `load_document_metadata`, `sample_documents`, `dedupe_queries`, `synthesize_title_queries`, `build_legacy_fixture`, `corpus_fingerprint`, `require_minimum_queries`, `evaluate_known_items`.
- `src/sif/cli/commands/eval.py` (new) - `eval_group` (six options, `invoke_without_command`), `run_personal`, `_resolve_collection_ids`, `_build_options`, `_load_embedder`, `_personal_payload`, `_render_personal`.
- `tests/support/eval.py` (new) - `build_personal_db` (real on-disk index, 60 curated docs, embeddings) and `seed_query_log`.
- `tests/unit/cli/test_eval.py` (new) - evaluator additivity, sampling determinism/metadata-only, tracer table/JSON, query-order determinism, threshold/degradation/collision, disclosure/markup tests (22 tests).
- `src/sif/search/benchmark.py` - `QueryEvaluation` + `SearchEvaluator.evaluate_per_query` (additive only).
- `src/sif/cli/main.py` - `eval_group` import and registration.
- `scripts/generate_cli_ref.py` - leaf-group traversal fix and `("eval", "Other Commands")` grouping.
- `tests/test_docs.py` - `"eval": []` subcommand entry.
- `docs/cli-reference.md` - regenerated by the generator (tree line + `### sif eval` section).

## Decisions Made

- Title leg is exact-term: no overlap budget is applied (research Pitfall 1); the target is the only grade-1 doc, so nDCG@10 is rank-sensitive.
- The rejection tally lives in a frozen `SynthesisResult` returned by `synthesize_title_queries`, composed from `dedupe_queries`, so the CLI never recomputes counts and no query set shrinks silently.
- `sample_documents` defaults to `MAX_SAMPLE_DOCUMENTS = 250`; the `< 50 accepted` failure is the plan-01 threshold guard (widening/searching the corpus is Plan 02's `ensure_heldout`).
- `require_minimum_queries` raises `ValueError` in the domain; `run_personal` translates it to a `ClickException` with the accepted/rejected breakdown.
- `_load_embedder` orders the embedder load after the corpus and accepted-query checks so a too-small corpus fails with the corpus remedy, not a model error.
- The table renders only counts/metrics plus the model identity; config-derived model strings are truncated then `rich.markup.escape`d (T-18-01).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical verification] Provider disclosure and markup escaping were unpinned by tests**
- **Found during:** Final plan verification (after Task 3)
- **Issue:** Two Task 1 acceptance behaviors — the T-18-15 remote-provider stderr disclosure and T-18-01 literal rendering of bracket text — had no explicit test even though the implementation existed.
- **Fix:** Added `TestDisclosureAndMarkup`: openai/modelscope prints the stderr notice naming `--bm25-only` and the report names the provider; `--bm25-only` prints none; a `[bold]evil[/bold]` model name renders literally.
- **Files modified:** `tests/unit/cli/test_eval.py`
- **Verification:** targeted suite 22 passed; full suite 1696 passed, 1 skipped.
- **Committed in:** `bbaf3ce`

---

**Total deviations:** 1 auto-fixed (Rule 2).
**Impact on plan:** No functional scope change; the addition closes an acceptance-verification gap for the plan's own threat mitigations.

## Issues Encountered

- Task 2's edge branches (missing index, <50 docs, embed remedy, `--bm25-only`, empty/duplicate rejection, accepted-query threshold) were already implemented as part of Task 1's tracer action. Task 2 therefore landed as test-pinning only; the plan's final state matches its action text.
- The first disclosure test wrongly asserted that "remote-capable" could not appear on stdout. The plan intentionally names the provider in the report notes as well as stderr; the test was corrected to parse stdout as JSON and assert the note there.

## User Setup Required

None - no external service configuration required.

## Threat Surface Scan

No new security-relevant surface beyond the plan's threat model. Mitigations verified: metadata-only scan without `fetchall()` (T-18-02), parameterized/`CollectionRepository` scope resolution (T-18-03), stderr-only remote-provider disclosure with the local alternative named (T-18-15), and truncate-then-escape for config-derived table text (T-18-01). No document content is stored, uploaded, or printed.

## Next Phase Readiness

- Plan 18-02 can extend `personal_bench.py` with `load_sampled_content` / body and replay legs; `DocumentRecord.content`, `SynthesisResult`, `evaluate_known_items`, `corpus_fingerprint`, and the CLI seams are in place.
- Plan 18-03 can add saved runs/`--compare` using `QueryEvaluation.retrieved_paths` and the corpus fingerprint.
- No blockers. Final gates: full pytest 1696 passed / 1 skipped at 95.01% coverage (fail_under 90), `ruff check` + `ruff format --check`, `ty check src/sif`, `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md`, and `python scripts/generate_bench_fixture.py --check` all green.

## Self-Check: PASSED

- FOUND: src/sif/search/personal_bench.py
- FOUND: src/sif/cli/commands/eval.py
- FOUND: tests/support/eval.py
- FOUND: tests/unit/cli/test_eval.py
- FOUND: docs/cli-reference.md
- FOUND: 715b270 (Task 1)
- FOUND: c7f6b55 (Task 2)
- FOUND: 77ab436 (Task 3)
- FOUND: bbaf3ce (Rule 2 verification gap)

---
*Phase: 18-quality-instrument-personal-bench-rapidfuzz-dym*
*Completed: 2026-11-14*
