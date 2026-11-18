---
phase: quick-261111-wha
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/cli/commands/search.py
  - src/sif/cli/commands/bench.py
  - tests/unit/cli/test_search.py
  - tests/unit/cli/test_bench.py
  - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
autonomous: true
requirements:
  - PHASE10-IN-07
must_haves:
  truths:
    - "query_cmd loads the model, prefers an integer embedding_dim from get_model_info(), and makes no embed_single probe when that metadata supplies the dimension"
    - "query_cmd and bench _load_embedder retain exactly one embed_single('probe') fallback when model metadata has no integer dimension; existing error handling and search behavior remain unchanged"
    - "bench _load_embedder initializes its unused BM25-only fallback from settings.embedding_dim and contains no legacy 384 assignment"
    - "Three new regression tests are non-vacuously RED against the pre-fix implementation; two missing-dimension fallback tests characterize the preserved fallback; all 196 baseline search/bench tests plus five new tests pass afterward"
    - "Phase 10 IN-07 is fixed in both ledger representations, the execution-time open count decreases by exactly one, and exact reconstruction proves every other ledger byte unchanged"
  artifacts:
    - src/sif/cli/commands/search.py
    - src/sif/cli/commands/bench.py
    - tests/unit/cli/test_search.py
    - tests/unit/cli/test_bench.py
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
  key_links:
    - "manager.load_model() -> manager.get_model_info().get('embedding_dim') -> SearchPipeline(embedding_dim=...) in query_cmd and BenchHarness.embedding_dim in bench_cmd"
    - "missing or non-integer model-info dimension -> len(manager.embed_single('probe')) fallback; model load failure in bench -> settings.embedding_dim with embedder unavailable"
    - "IN-07 YAML disposition + IN-07 markdown Source cell + dynamic open-count decrement -> one consistent Phase 10 review ledger"
---

<objective>
Close Phase 10 IN-07 only. At planning-time HEAD c8a234b, query_cmd (src/sif/cli/commands/search.py:895-902) eagerly loads the embedder and then pays `len(manager.embed_single("probe"))` solely to construct SearchPipeline; bench _load_embedder (src/sif/cli/commands/bench.py:97-114) repeats that probe and initializes its fallback to the stale magic value 384. The original finding (10-REVIEW.md:195-199) prescribes the probe-free `get_model_info()` approach already used by embed_cmd.

Apply the embed_cmd precedent at src/sif/cli/commands/index.py:234-239 to both sites: after `manager.load_model()`, read `model_dim = manager.get_model_info().get("embedding_dim")`; use it when `isinstance(model_dim, int)`, otherwise retain the single embedding probe as the compatibility fallback. In bench, initialize the pre-load fallback from `settings.embedding_dim` instead of the magic value. Do not add a shared helper: two copies of the established three-line guarded resolution are clearer and smaller than a new public abstraction for this focused refactor.

Purpose: avoid a throwaway, potentially billed remote embedding on every hybrid query and benchmark invocation while preserving compatibility with embedders/mocks whose metadata lacks a usable dimension.
Output: consistent dimension resolution in query and bench, five focused regression/characterization tests, and IN-07 closed with the exact three-edit ledger convention.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
@src/sif/cli/commands/search.py
@src/sif/cli/commands/bench.py
@src/sif/cli/commands/index.py
@src/sif/embedding/manager.py
@tests/unit/cli/test_search.py
@tests/unit/cli/test_bench.py

Planning evidence, verified live at HEAD c8a234b:
- Production sites: search.py:896-898 constructs/loads the manager and immediately probes; SearchPipeline consumes `embedding_dim` at line 935 and the already-public `embedder=manager.model` at line 931. bench.py:105 initializes the legacy numeric fallback, lines 107-109 load and probe, and bench.py:644-653 forwards the returned dimension through BenchHarness. Preserve manager loading, both exception handlers, `manager.model`, CachedEmbedder, and all pipeline wiring.
- Precedent and metadata contract: index.py:234-239 uses an integer `get_model_info()` dimension before probing. manager.py:236-253 returns no embedding_dim before load and returns the loaded model's `.dimension` after load. Both target sites already call load_model first, so a real backend normally takes the probe-free branch. Use the same `isinstance(model_dim, int)` guard; an unconfigured MagicMock metadata value therefore falls through to the probe, keeping the existing CLI mocks green without mass fixture edits.
- Test homes: test_search.py already imports CliRunner, MagicMock/patch, SearchResult, query_cmd, and the `_query_settings_mock()` helper. Add a small `TestQueryEmbeddingDimension` class near the other query tests with one local invoke helper that patches Database, CollectionRepository, SearchPipeline, EmbeddingManager.from_settings, and get_settings; return the Click result and SearchPipeline class mock so constructor kwargs are assertable. test_bench.py already imports MagicMock/patch and has `_settings_mock(**overrides)`; add `TestLoadEmbedder` immediately before TestCachedEmbedder and use a function-local `_load_embedder` import matching the neighboring test style.
- Non-vacuous RED design: the query metadata-present test configures dimension 7 and makes embed_single raise AssertionError; current query code calls it and exits 1, while the fixed code exits 0, never calls it, and passes 7 to SearchPipeline. Bench metadata-present currently ignores dimension 7 and probes; bench load-failure currently returns the stale numeric fallback rather than a configured 2048. These three tests fail for the intended behavior before production edits. The two metadata-missing fallback tests pass before and after and are explicitly characterization guards, not claimed as RED.
- Baseline: `python -m pytest tests/unit/cli/test_search.py tests/unit/cli/test_bench.py -q --no-cov` -> 196 passed in 3.30s. This plan adds two query tests and three bench loader tests -> 201 passed in the targeted gate. Coordinator-provided full-suite baseline is 1531 passed / 1 skipped / 95.06% coverage; sibling items may add tests, so final full-suite success is zero failures rather than a hardcoded count.
- Static gate baselines at HEAD: the model-info resolver literal occurs 0 times in each production target; the legacy bench numeric assignment occurs once; each file has one direct probe-only dimension assignment. After the fix, each target has one model-info resolver, bench has zero legacy numeric assignments, and each file retains one probe inside the guarded fallback expression.
- Ledger state at planning time: open 4 / total 22; IN-07 YAML disposition is open at lines 70-73 and its markdown row is `| IN-07 | info | open | - |` at line 119. All siblings wh7/wh8/wh9 share this ledger and may land first. Read execution-time HEAD dynamically; never hardcode 4 or an assumed successor.
- Sibling scope: wh7 owns MCP backend max_lines, wh8 owns MCP sqlite-vec degradation, and wh9 owns the global config option/docs regeneration. None is a logical prerequisite, so depends_on is empty. The common ledger path is declared for coordinator serialization. This plan alone owns search.py, bench.py, test_search.py, and test_bench.py within the catalog.
- Environment and quality: use PATH miniconda `python -m pytest`, never .venv; targeted runs use --no-cov, while the final full run includes coverage. The suite is color-env hermetic. Run ruff check, ruff format --check, and ty check. New tests and code are fully annotated. Generator-owned docs are untouched because no CLI signature/help/config field changes.
- Discovery level 0: this applies an existing in-repo pattern with no dependency, schema, external integration, or architectural change. No RESEARCH.md or locked D-XX decisions apply to this phaseless quick item.
- Scope guard: do not alter manager.py, index.py, search.py's public manager.model access, vsearch's necessary query embedding, CachedEmbedder, SearchPipeline, any sibling-owned file, generator-owned docs, STATE.md, or unrelated findings. Preserve all pre-existing .planning churn; stage and commit only task-scoped paths.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Resolve dimensions from model metadata first, with tested probe and settings fallbacks (IN-07)</name>
  <files>tests/unit/cli/test_search.py, tests/unit/cli/test_bench.py, src/sif/cli/commands/search.py, src/sif/cli/commands/bench.py</files>
  <behavior>
    - Metadata present: query_cmd and bench _load_embedder use the integer model-info dimension and never call embed_single for a probe; SearchPipeline/BenchHarness receives that exact dimension.
    - Metadata absent or non-integer: each site calls embed_single exactly once with `probe` and uses the returned vector length.
    - Bench model construction/load failure: the returned manager/dimension behavior and warning paths stay unchanged except that the neutral dimension is settings.embedding_dim.
    - RED: three tests fail against the current implementation for the intended reasons (query billed probe, bench ignored metadata, bench stale load-failure fallback); GREEN: all five new tests and all 196 baseline targeted tests pass after implementation.
  </behavior>
  <action>
  FIRST add tests only; do not edit production until the RED run is recorded.

  In tests/unit/cli/test_search.py add `TestQueryEmbeddingDimension` with a typed `_invoke` helper modeled on the existing query fixtures. The helper creates a touched tmp_path index, a CollectionRepository mock with no enabled collections, a pipeline mock returning one real SearchResult (avoiding unrelated zero-result suggestion behavior), and patches the five collaborators listed in planning evidence. It invokes `query_cmd` with `["query", "--json"]` using `_query_settings_mock()` and returns the result plus the SearchPipeline class mock. Add `test_model_info_dimension_skips_probe(self, tmp_path: Path) -> None`: use a MagicMock manager whose get_model_info returns `{"loaded": True, "embedding_dim": 7}`, whose embed_single raises AssertionError if called, and whose model attribute is a MagicMock. Assert exit_code 0 with result.output as the assertion message, embed_single.assert_not_called(), and SearchPipeline constructor kwarg embedding_dim == 7. Add `test_missing_model_info_dimension_uses_probe(self, tmp_path: Path) -> None`: metadata is `{"loaded": True}`, embed_single returns a five-element vector, and assertions require exit_code 0, one embed_single call with `probe`, and constructor dimension 5.

  In tests/unit/cli/test_bench.py add `TestLoadEmbedder` before TestCachedEmbedder, with three typed methods and function-local import of _load_embedder. `test_model_info_dimension_skips_probe`: patch bench.EmbeddingManager.from_settings to return a manager reporting integer dimension 7 and an embed_single AssertionError sentinel; call `_load_embedder(_settings_mock(embedding_dim=1024), None)` and assert the same manager, dimension 7, and no probe. `test_missing_model_info_dimension_uses_probe`: metadata lacks the key, embed_single returns five values, and the result is dimension 5 with one `probe` call. `test_load_failure_uses_settings_dimension`: configure `_settings_mock(embedding_dim=2048)`, make from_settings raise ImportError, and assert `(None, 2048)`; this also preserves the BM25-only soft-fail path. Use patch targets `sif.cli.commands.bench.EmbeddingManager.from_settings` so the lookup matches production.

  Run `python -m pytest tests/unit/cli/test_search.py tests/unit/cli/test_bench.py -q --no-cov` now. Confirm exactly the three metadata/load-fallback tests identified above are RED for their intended assertions and the two missing-metadata tests are green characterization guards. Do not proceed on collection errors, unexpected fixture failures, or a green metadata-present probe test.

  THEN make the focused production edits. In query_cmd, immediately after manager.load_model(), resolve model_dim through manager.get_model_info().get("embedding_dim") and assign embedding_dim to model_dim when it is an int, otherwise to the length of one `embed_single("probe")` result. Keep this inside the existing try block so ImportError and general model/probe failures retain their current ClickException messages. In bench _load_embedder, initialize embedding_dim from settings.embedding_dim before the try block, retain manager = None and both warning handlers, and after manager.load_model() apply the identical metadata-first guarded probe expression. Do not change the return signature or soft-fail semantics.

  Do not extract a helper, edit index.py/manager.py, change public manager.model access, alter vsearch's actual query embedding, or rewrite existing mocks. Existing MagicMock managers deliberately fall through to the probe because their unconfigured metadata dimension is not an int. Format only touched files if needed. Commit source and tests together only after all Task 1 gates pass; never stage unrelated .planning churn.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/cli/test_search.py tests/unit/cli/test_bench.py -q --no-cov &amp;&amp; test "$(grep -c 'model_dim = manager.get_model_info().get("embedding_dim")' src/sif/cli/commands/search.py)" = 1 &amp;&amp; test "$(grep -c 'model_dim = manager.get_model_info().get("embedding_dim")' src/sif/cli/commands/bench.py)" = 1 &amp;&amp; ! grep -q 'embedding_dim = 384' src/sif/cli/commands/bench.py &amp;&amp; ruff check src/sif/cli/commands/search.py src/sif/cli/commands/bench.py tests/unit/cli/test_search.py tests/unit/cli/test_bench.py &amp;&amp; ruff format --check src/sif/cli/commands/search.py src/sif/cli/commands/bench.py tests/unit/cli/test_search.py tests/unit/cli/test_bench.py</automated>
  </verify>
  <done>The intended three tests were demonstrably RED before production edits; all 201 targeted tests now pass. Both commands prefer model metadata, both preserve the single missing-metadata probe fallback, bench uses settings.embedding_dim on load failure and has no legacy numeric assignment, public manager.model wiring and all existing error behavior remain intact, and ruff/format pass.</done>
</task>

<task type="auto">
  <name>Task 2: Close only IN-07 in the Phase 10 disposition ledger (execution-time robust)</name>
  <files>.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md</files>
  <action>
  After Task 1 and the final quality gates pass, make exactly three scoped edits in .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md:

  1. In the IN-07 YAML finding block only, change `disposition: open` to `disposition: fixed`; preserve its id, severity, and title.
  2. Read N from the unique aggregate `open: N` line in execution-time `git show HEAD:<ledger>` and replace it with N-1. Siblings wh7/wh8/wh9 may already have closed records; never hardcode the planning-time count. Leave total 22 and the recorded timestamp unchanged.
  3. Replace the IN-07 open markdown row with `| IN-07 | info | fixed | quick 261111-wha (query_cmd and bench _load_embedder prefer get_model_info embedding_dim with probe fallback; bench load failure uses settings.embedding_dim; probe-avoidance regression tests red-to-green) |`.

  Preserve every other YAML block, row, ordering, explanatory paragraph, sibling closure, and trailing newline byte-for-byte. Do not add Status-resolved lines, edit the historical review or STATE.md, or stage unrelated planning churn. Run the reconstruction gate before committing only this ledger path; on any divergence beyond these three edits, halt and surface it rather than forcing the closure.
  </action>
  <verify>
    <automated>python -I -c "import re, subprocess; from pathlib import Path; path = '.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md'; before = subprocess.check_output(['git', 'show', 'HEAD:' + path], text=True); yaml_old = '  - id: IN-07\n    severity: info\n    disposition: open\n'; yaml_new = yaml_old.replace('disposition: open', 'disposition: fixed'); row_old = '| IN-07 | info | open | - |'; row_new = '| IN-07 | info | fixed | quick 261111-wha (query_cmd and bench _load_embedder prefer get_model_info embedding_dim with probe fallback; bench load failure uses settings.embedding_dim; probe-avoidance regression tests red-to-green) |'; counts = re.findall(r'^open: (\d+)$', before, re.M); assert before.count(yaml_old) == 1 and before.count(row_old) == 1 and len(counts) == 1, 'IN-07/open anchors not unique at execution-time HEAD'; n = int(counts[0]); expected = before.replace(yaml_old, yaml_new, 1).replace(row_old, row_new, 1).replace('\nopen: %d\n' % n, '\nopen: %d\n' % (n - 1), 1); assert expected != before; assert '\ntotal: 22\n' in expected; assert Path(path).read_text(encoding='utf-8') == expected, 'ledger differs from exact three-edit reconstruction of execution-time HEAD'; print('IN-07-fixed; open %d->%d; all-other-ledger-content-byte-identical' % (n, n - 1))"</automated>
  </verify>
  <done>IN-07 is fixed in YAML and markdown, its Source cell names quick 261111-wha, the open count is exactly one below execution-time HEAD with total still 22, and byte-equality reconstruction proves no other ledger content changed; no Status-resolved line or unrelated file is committed.</done>
</task>

</tasks>

<verification>
Source coverage audit (one quick-batch finding; no research artifact or locked D-XX decisions):

| SOURCE | ID | Item | Task | Status |
|--------|----|------|------|--------|
| GOAL | quick-261111-wha | Close IN-07: metadata-first query/bench dimension resolution, guarded probe fallback, settings-based bench fallback, non-vacuous tests, exact ledger closure | 1-2 | COVERED |
| REQ | PHASE10-IN-07 | Apply embed_cmd's get_model_info precedent in query_cmd; remove bench's stale magic fallback; preserve BM25-only behavior | 1 | COVERED |
| CONTEXT | orchestrator notes | TDD RED first; public manager.model preserved; missing metadata needs fallback; shared helper optional; PATH pytest; full quality gates; execution-time dynamic ledger count and byte-equality gate; no Status-resolved lines | 1-2 | COVERED |
| CONTEXT | sibling exclusions | WR-07 (wh7), WR-08 (wh8), IN-05 (wh9), all other findings and generator-owned docs | - | EXCLUDED BY BATCH/FINDING SCOPE; ledger overlap declared and serialized by coordinator |

No package install, schema change, external API integration, or phase-scoped capability checkpoint applies. No files are deleted.

Final gates from the checkout root:
1. `python -m pytest tests/unit/cli/test_search.py tests/unit/cli/test_bench.py -q --no-cov` -> 201 passed (196 baseline + five new).
2. `ruff check src tests`
3. `ruff format --check src tests`
4. `ty check src/sif`
5. `python -m pytest` with the coverage gate (PATH Python, not .venv).
6. Review the scoped diff: only the five files_modified paths carry edits; production changes are confined to the two dimension-resolution blocks, and tests contain only the new query and bench regression classes. Commits exclude all pre-existing .planning churn; SUMMARY/STATE handling belongs to the orchestrator.
</verification>

<success_criteria>
- Hybrid query and benchmark model loading no longer incur a probe embedding when model metadata provides an integer dimension; the exact metadata dimension reaches SearchPipeline/BenchHarness.
- Missing metadata still uses one explicit probe, bench load failure uses settings.embedding_dim, and existing soft-fail/error behavior remains unchanged.
- Three regression tests proved the old defects RED before implementation; two fallback characterization tests and all existing targeted tests remain green; full ruff, format, ty, and pytest gates pass.
- IN-07 alone is closed, the ledger count decrements dynamically from execution-time HEAD, and byte-equality proves every other record unchanged.
</success_criteria>

<output>
Create `.planning/quick/261111-wha-close-phase-10-in-07-embedding-dim-resolution-consistency-me/261111-wha-SUMMARY.md` with `status: complete` in frontmatter. Record the closed finding as Phase 10 IN-07, the three RED and two characterization test outcomes, the metadata-first/fallback behavior at both production sites, the 196-to-201 targeted test transition, full quality-gate results, and the execution-time ledger open-count transition. Note that no shared helper was introduced and manager.model/index.py were left unchanged. Do not commit planning artifacts or STATE.md; the orchestrator handles docs/state commits.
</output>
