---
phase: 260905-kmv-fix-g-04-2-reranker-load-crash
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/search/rerank.py
  - src/sif/cli/commands/search.py
  - tests/unit/search/test_rerank.py
  - tests/unit/cli/test_search.py
autonomous: true
requirements: [G-04-2]
estimate:
  tokens: 60000
  raw_tokens: 40000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "With Qwen/Qwen3-Reranker-0.6B downloaded from ModelScope (real model files at the download ROOT plus aux subdir 1_LogitScore/ holding only a 57-byte config without model_type), the reranker loads from the download root and `sif search query <terms> --explain` completes, showing reranker_score alongside bm25_score/vector_score/rrf_score (G-04-2)"
    - "A RuntimeError raised by the reranker inside pipeline.search surfaces in query_cmd as a one-line click.ClickException `Error: ...` message with exit code 1 — the raw multi-line traceback is gone (G-04-2)"
    - "Non-RuntimeError exceptions from pipeline.search still propagate uncaught — the CLI wrap stays narrow"
    - "Model-dir resolution never returns None for a genuinely downloaded model: config-based check first, weights-file fallback second, download root as final fallback"
    - "Full quality suite green: ruff check src tests; ruff format --check src tests; env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q"
  artifacts:
    - "src/sif/search/rerank.py — module-level _resolve_model_dir(downloaded: Path) -> Path resolver; both Qwen3Reranker.load() and CrossEncoderReranker.load() route through it"
    - "src/sif/cli/commands/search.py — query_cmd wraps the pipeline.search call's RuntimeError into click.ClickException(str(e)) from e"
    - "tests/unit/search/test_rerank.py — new file, resolver regression tests against a tmp_path mock of the ModelScope layout"
    - "tests/unit/cli/test_search.py — new test class for the pipeline RuntimeError -> ClickException path"
  key_links:
    - "Qwen3Reranker.load() model_id resolution -> _resolve_model_dir(downloaded) -> AutoTokenizer/AutoModelForCausalLM.from_pretrained(local_path)"
    - "CrossEncoderReranker.load() ModelScope branch -> _resolve_model_dir(downloaded) -> CrossEncoder(local_path)"
    - "SearchPipeline reranker failure (RuntimeError) -> query_cmd except RuntimeError -> click.ClickException -> CliRunner/terminal one-line Error output"
---

<objective>
Fix UAT gap G-04-2 (04-UAT.md, severity blocker): after a successful 1.11GB ModelScope download of the default reranker Qwen/Qwen3-Reranker-0.6B, `sif search query --explain` crashes with RuntimeError before any results render, and the failure reaches the user as a raw 60-line traceback instead of a ClickException.

Purpose: UAT test 2 (real-model reranking quality, SC 1) is blocked on this crash. Root cause (verified, recorded in 04-UAT.md Gaps G-04-2 — do not re-diagnose): `Qwen3Reranker.load()` in src/sif/search/rerank.py resolves `local_path = subdirs[0]` of the ModelScope download directory; that repo ships its real model files at the download ROOT (config.json with model_type qwen3, model.safetensors, tokenizer.json, ...) plus an aux subdir `1_LogitScore/` containing only a 57-byte config.json without model_type, so subdirs[0] picks the aux dir and AutoTokenizer falls back to BertTokenizer with vocab_file=None and raises TypeError, which SearchPipeline wraps as RuntimeError. The identical subdirs[0] heuristic also exists in `CrossEncoderReranker.load()`. Secondary: `query_cmd` in src/sif/cli/commands/search.py calls `pipeline.search(query, options)` bare, so the RuntimeError propagates as a traceback, violating the CLAUDE.md CLI error convention.

Output: a model-dir resolver that prefers a directory containing a real model config (download root before aux subdirs), wired into both reranker load paths; query_cmd converts pipeline RuntimeError into click.ClickException; regression tests for the ModelScope layout and the CLI error path.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@/Users/forrest/GitHub/SIF/CLAUDE.md
@/Users/forrest/GitHub/SIF/.planning/phases/04-advanced-search-pipeline/04-UAT.md
@/Users/forrest/GitHub/SIF/src/sif/search/rerank.py
@/Users/forrest/GitHub/SIF/src/sif/cli/commands/search.py
@/Users/forrest/GitHub/SIF/src/sif/models/download.py
@/Users/forrest/GitHub/SIF/tests/unit/cli/test_search.py
@/Users/forrest/GitHub/SIF/tests/unit/search/test_term_match.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Model-dir resolver in rerank.py + regression tests</name>
  <files>src/sif/search/rerank.py, tests/unit/search/test_rerank.py</files>
  <behavior>
    - Test 1 (G-04-2 primary layout): tmp_path mock of the ModelScope download — root holds config.json with a model_type key (e.g. {"model_type": "qwen3"}) plus sibling files, and an aux subdir 1_LogitScore/ holds only a config.json without model_type ({"true_token_id": 9693, "false_token_id": 2152}); _resolve_model_dir returns the download ROOT.
    - Test 2 (qualification beats order): root has no model config; subdirs 1_LogitScore/ (non-qualifying config) and 2_Weights/ (config.json with model_type) both exist; _resolve_model_dir returns 2_Weights even though 1_LogitScore sorts first.
    - Test 3 (weights fallback): no config.json with model_type anywhere; root has model.safetensors and an empty aux subdir; _resolve_model_dir returns the root.
    - Test 4 (final fallback): an empty download dir resolves to the root itself — the helper always returns a Path, never None.
    - Test 5 (defensive parsing): a root config.json containing invalid JSON text does not raise and does not qualify; resolution falls through to the next rule.
  </behavior>
  <action>
    RED first: create tests/unit/search/test_rerank.py with the five tests above, importing the helper as `from sif.search.rerank import _resolve_model_dir`; plain pytest class style matching tests/unit/search/test_term_match.py (class per concern, docstrings citing G-04-2, tmp_path fixtures writing the config.json / model.safetensors placeholder files). Run it — it must fail on import (helper does not exist yet).
    GREEN: add `import json` to the stdlib imports of src/sif/search/rerank.py, then add a module-level helper `_resolve_model_dir(downloaded: Path) -> Path` next to `_sort_and_build_results`, fully type-annotated (strict mode, line length 100):
    - Candidates in deterministic order: the download root first, then each immediate subdirectory sorted by name.
    - Pass 1 (config-based): return the first candidate whose config.json exists, parses via json.load into a dict, and contains the key "model_type" — guard OSError and json.JSONDecodeError plus non-dict parse results so a corrupt or aux config simply does not qualify (this is what disqualifies 1_LogitScore, whose 57-byte config holds only true/false token ids).
    - Pass 2 (weights fallback): return the first candidate containing at least one *.safetensors or *.bin file (glob + any()).
    - Final fallback: return the download root unchanged.
    Then wire both call sites through it: in Qwen3Reranker.load() (currently around lines 259-260) and in CrossEncoderReranker.load() (currently around lines 165-167 — the same subdirs[0] heuristic and the same crash class for sentence-transformers rerankers fetched from ModelScope), replace the subdirs-scan lines with a single call assigning str(_resolve_model_dir(downloaded)). Keep the surrounding control flow (ModelScope download branch, logging, quiet/suppress_output handling) untouched; change nothing else in the file. Per G-04-2 missing item 1: download root is preferred before aux subdirs.
  </action>
  <verify>
    <automated>env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_rerank.py -q</automated>
  </verify>
  <done>All five resolver tests pass: root-with-aux-subdir resolves to root, the qualifying subdir wins over sorted order, weights fallback works, an empty dir returns the root (never None), and malformed JSON config is skipped without raising. Both Qwen3Reranker.load() and CrossEncoderReranker.load() resolve local_path via _resolve_model_dir; grep confirms no remaining `subdirs[0]` heuristic in src/sif/search/rerank.py.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: query_cmd wraps pipeline RuntimeError as ClickException + CLI test</name>
  <files>src/sif/cli/commands/search.py, tests/unit/cli/test_search.py</files>
  <behavior>
    - Test 1: with SearchPipeline mocked so pipeline.search raises RuntimeError("Reranking failed: boom"), invoking query_cmd via CliRunner exits with code 1, the output contains "Error:" and "Reranking failed", and result.exception is not a RuntimeError instance.
    - Test 2 (narrowness guard): with pipeline.search raising ValueError, the ValueError propagates uncaught (result.exception is that ValueError) — proving the except clause catches only RuntimeError.
  </behavior>
  <action>
    RED first: add a test class TestQueryPipelineErrorHandling to tests/unit/cli/test_search.py following the existing CliRunner + patch scaffold used by TestSnippetDisplay (patch sif.cli.commands.search.Database, sif.cli.commands.search.CollectionRepository, sif.cli.commands.search.SearchPipeline, sif.embedding.manager.EmbeddingManager.from_settings, and sif.config.settings.get_settings with reranker_model_name=None and reranker_model_path=None; index_path as MagicMock(exists=lambda: True)); set mock_pipeline.search.side_effect per test. Run it — Test 1 must fail before the fix (traceback escapes, exit_code reflects the uncaught exception path).
    GREEN: in src/sif/cli/commands/search.py query_cmd, wrap ONLY the `results = pipeline.search(query, options)` statement (currently around line 524, inside the `with db.connection:` block) in a try/except that catches RuntimeError and raises click.ClickException(str(e)) from e — mirroring the existing embedder-load ClickException pattern a few lines above (currently around lines 494-497). Keep the call inside the with-block; do not widen the except to other exception types; do not touch the output-rendering branches below. Per G-04-2 missing item 3 (CLAUDE.md CLI error convention).
  </action>
  <verify>
    <automated>env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -q</automated>
  </verify>
  <done>A reranker RuntimeError from pipeline.search renders as a one-line click Error message with exit code 1 and no escaped traceback; ValueError still propagates uncaught; all pre-existing tests in tests/unit/cli/test_search.py still pass; the wrap covers the pipeline.search call only.</done>
</task>

<task type="auto">
  <name>Task 3: Full quality suite gate</name>
  <files>src/sif/search/rerank.py, src/sif/cli/commands/search.py, tests/unit/search/test_rerank.py, tests/unit/cli/test_search.py</files>
  <action>
    Run the full CLAUDE.md quality suite and fix any fallout confined to the four files this plan touched — ruff line-length/format violations in the new helper and tests, missing type annotations (disallow_untyped_defs), import-order issues (json must sit in the stdlib group), or mccabe complexity. Behavior changes and edits to unrelated files are out of scope. Use the FORCE_COLOR-unset pytest invocation: rich emits ANSI when forced and breaks plain-output assertions in this harness (pre-existing, environmental).
  </action>
  <verify>
    <automated>ruff check src tests && ruff format --check src tests && env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q</automated>
  </verify>
  <done>ruff check and ruff format --check are clean over src and tests; the full suite passes (baseline was 608 passed / 11 skipped / 0 failed after quick task 260905-hc3 — expect 615 passed / 11 skipped / 0 failed with the 7 new tests) with zero failures.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ModelScope repo contents -> local path resolution | Remote-controlled file layout (config.json presence/content in root vs subdirs) influences which local directory the resolver picks |
| reranker exception message -> CLI output | RuntimeError text from the ML stack crosses into user-facing ClickException output |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260905k-01 | Tampering | rerank._resolve_model_dir | low | mitigate | json.load guarded against OSError and JSONDecodeError; non-dict parse results rejected — a corrupt or adversarial config.json cannot crash resolution or hijack qualification; candidate order is deterministic (root first, then sorted subdirs) so path selection is reproducible |
| T-260905k-02 | Information Disclosure | search.query_cmd ClickException | low | accept | str(e) of a RuntimeError surfaced as a one-line Error follows the existing CLI convention already used for embedder-load failures in the same command; no stack traces or internal paths beyond what the convention already prints |
</threat_model>

<verification>
1. Task-level automated checks all pass (see each task's verify).
2. Full suite: `ruff check src tests && ruff format --check src tests && env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` — zero failures, zero lint violations.
3. Structure check (no signature drift): `create_reranker`, `Qwen3Reranker.load`, `CrossEncoderReranker.load`, and `LlamaCppReranker.load` keep their public signatures; the only src/sif/search/rerank.py changes are the added json import, the new module-level `_resolve_model_dir`, and the two local_path assignments; the only src/sif/cli/commands/search.py change is the try/except around the pipeline.search call in query_cmd (grep the file for other commands' pipeline calls — vsearch_cmd/search_cmd use different searchers and are out of scope).
4. UAT re-verification (out of scope for this quick plan, done via /gsd-verify-work 04 resume): re-run UAT test 2 with the already-downloaded Qwen/Qwen3-Reranker-0.6B — `sif search query <terms> --explain` renders results with reranker_score instead of crashing; then flip G-04-2 to resolved in 04-UAT.md.
</verification>

<success_criteria>
- G-04-2 missing item 1 delivered: model-dir resolution prefers a directory containing a real model config (config.json with model_type), download root before aux subdirs, with weights-file and root fallbacks so resolution never fails on a downloaded model.
- G-04-2 missing item 2 delivered: regression test reproducing the ModelScope layout (root model files + 1_LogitScore aux subdir) and asserting root resolution.
- G-04-2 missing item 3 delivered: query_cmd wraps pipeline.search RuntimeError into click.ClickException per the CLI error convention, narrow to RuntimeError only.
- Both reranker classes (Qwen3 and CrossEncoder) route ModelScope path resolution through the shared resolver.
- Full quality suite green per CLAUDE.md.
</success_criteria>

<output>
Create `.planning/quick/260905-kmv-fix-g-04-2-reranker-load-crash-model-dir/260905-kmv-SUMMARY.md` when done
</output>
