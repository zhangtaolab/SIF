---
phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
reviewed: 2026-11-25T04:42:46Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - docs/architecture.md
  - docs/benchmarking.md
  - docs/cli-reference.md
  - pyproject.toml
  - scripts/generate_config_ref.py
  - scripts/generate_cli_ref.py
  - src/sif/cli/commands/eval.py
  - src/sif/cli/main.py
  - src/sif/search/benchmark.py
  - src/sif/search/personal_bench.py
  - src/sif/search/suggest.py
  - tests/support/eval.py
  - tests/test_docs.py
  - tests/unit/cli/test_eval.py
  - tests/unit/search/test_personal_bench.py
  - tests/unit/search/test_suggest.py
  - uv.lock
findings:
  critical: 1
  warning: 10
  info: 11
  total: 22
  necessity: 0
status: issues_found
---

# Phase 18: Code Review Report

**Reviewed:** 2026-11-25T04:42:46Z (incremental pass) and 2026-11-14T15:58:58Z (initial audit)
**Depth:** standard
**Files Reviewed:** 17 (16 in the initial audit, 1 more in the incremental pass)
**Status:** issues_found

## Summary

Reviewed the Phase 18 diff (`6a12d90..4600131`): the personal benchmark instrument, its saved-run comparison contract, the `sif eval` CLI, the rapidfuzz did-you-mean swap, the additive `SearchEvaluator.evaluate_per_query`, the generated docs, and the lockfile. The design is unusually careful — deterministic sampling/splitting, per-leg rejection accounting, id-keyed paired grading, fail-loud embed handling, strict JSON on stdout, atomic run writes, and a broad test battery (211 targeted tests and 13 docs tests pass; `ruff check`, `ruff format --check`, and `ty check` pass; `generate_cli_reference()` reproduces the committed `docs/cli-reference.md` byte-for-byte).

The instrument still has honesty and robustness gaps that the tests do not pin. The most consequential: synthesized/replayed queries that begin with the search pipeline's reserved `vec:`/`hyde:` prefixes abort the whole eval (CR-01); the CLI can write saved runs its own loader rejects (`-n 0`/negative, large `-n` file-size overflow, over-cap strings); replay bypasses the global query-history read opt-out; saved runs contain literal document-body phrases despite the "never contains document content" claim; and the noise gate can warrant a defaults change from a single held-out query while displaying a larger noise floor. Several failure paths also escape the CLI's `ClickException` convention as raw tracebacks.

No `<structural_findings>` payload was supplied, so there is no fallow section. The necessity rubric was applied at `standard` depth; no necessity findings were warranted.

## Incremental Re-review (2026-11-25)

**Scope:** the four files that changed since the last commit touching this report (`b817ebb`) and bear on this phase: `pyproject.toml`, `uv.lock` and `tests/test_docs.py`, the three files of `18-VERIFICATION.md`'s `covered_files` that changed, plus `scripts/generate_config_ref.py`, which the docs-generator gate runs. `a13b134c` and `848e6b6a` changed the `torch` requirement of the `embed` and `all` extras from bare `torch` to `torch>=2.11` and regenerated the lockfile. `9d85c9cd` added `--torch-backend=auto` to the strings `test_installation_doc_is_uv_first` requires and added `test_installation_doc_warns_against_cpu_backend_on_macos`; `6b409030` registered `docs/machine-migration.md` in `DOCS_FILES`. `82df76b0` added Intel XPU to the device-selection note that `scripts/generate_config_ref.py` emits. All five are quick-task commits, not Phase 18 work, and no Phase 18 SUMMARY changed. With the workflow's default scoping the resolver found no task commit of this phase among them (`status: degraded`, `source: phase-range`, `reason: no-task-commits-since`), because every Phase 18 task commit predates `b817ebb`; it widened to all 58 non-planning files changed since the archive commit. The scope was therefore set through the workflow's `--files` override, which leaves every other gate in place. Three of the four files are in the 16-file scope above; `scripts/generate_config_ref.py` is new to this report.

**Result: no new finding.** The 22 findings below keep their id, title, severity and text. None cites a file in this delta, and none of the files they cite changed since `b817ebb`, so none was fixed by it and none was re-reviewed. Their rows in `18-REVIEW-DISPOSITION.md` are untouched.

Checked at HEAD `d3a7f2c`:

- **rapidfuzz (QUAL-01).** `pyproject.toml:41` still declares `rapidfuzz>=3.14.5,<4`. `uv.lock:575` carries the same specifier and `uv.lock:507-508` the same fleet, 3.14.5 for Python below 3.11 and 3.14.6 for 3.11 and later. No line naming rapidfuzz appears in the `b817ebb..HEAD` diff of either file.
- **torch floor.** `embed` and `all` carry the same requirement (`pyproject.toml:55`, `:73`), and the four `docsif` `requires-dist` rows in the lockfile carry the matching specifier (`uv.lock:581-584`). The resolved fleet did not move (2.14.1 for Python 3.10, 2.15.0 for 3.11 and later, `+cpu` builds from the explicit CPU index on Linux), so every locked install still satisfies the floor. `uv lock --check --offline` (uv 0.9.8) resolves 106 packages and exits 0. The floor's text guards (`tests/test_ci_workflows.py:139`, `:172`) and `docs/installation.md:133` and `:146` agree with it.
- **Lockfile integrity.** The `uv.lock` diff removes 23 lines and adds 23. Four pairs are the torch specifier. The other 19 pairs are the same two `resolution-markers` strings moved within their fork lists, the same lines on both sides, which changes no resolution.
- **Docs gate (`tests/test_docs.py`).** `pytest tests/test_docs.py` reports 21 passed: the 20 of the original audit plus the new macOS guard. `docs/machine-migration.md` exists and is in the `mkdocs.yml` nav (`:96`), so the new `DOCS_FILES` registration is live rather than skipped. The two strings the delta makes mandatory are present in `docs/installation.md` (`:27`, `:42`), and the first occurrence of each install method is still ordered uv tool, uvx, pip (`:17`, `:61`, `:80`). `ruff check` and `ruff format --check` (ruff 0.15.11) are clean on the file.
- **Configuration generator.** `generate_markdown()` rendered in memory is identical to the committed `docs/configuration.md`, so the generator gate still reproduces the doc byte for byte. The device order the new text states (CUDA, Intel XPU, Apple MPS, CPU) and its caveat that XPU needs an XPU-enabled torch build agree with `_auto_device` (`src/sif/embedding/embedder.py:105-127`).

Not checked here: whether the full suite passes locally; the fixes recorded for CR-01 and WR-01 to WR-10, whose files are unchanged since `b817ebb` and were not re-read; and whether the CPU index really has no macOS wheel for the current torch fleet, which the new guard's docstring asserts and which cannot be verified offline. Necessity was assessed against the rubric and yields no finding. No structural section is included because no structural pre-pass was configured. This pass was performed inline from `gsd-code-reviewer.md` by the orchestrator, because this runtime exposes no Agent tool; no external reviewer evidence was supplied.

## Critical Issues

### CR-01: Reserved-prefix titles/body/replay queries abort the entire eval

**File:** `src/sif/cli/commands/eval.py:579-589`, `:668-681`; `src/sif/search/personal_bench.py:770-812`, `:1101-1102`, `:1993-1998`, `:2020-2024`
**Issue:** `_search_fn` uses the production `SearchPipeline`, whose first action is `_parse_query_prefix` (`src/sif/search/hybrid.py:185-203`). Any eval query that begins with `vec:`, `hyde:`, `lex:`, or `expand:` is routed accordingly instead of being searched literally. In `--bm25-only` mode (and in hybrid mode without a HyDE-capable embedder) a `vec:`/`hyde:` query raises `RuntimeError("Vector search requires an embedder")`/`RuntimeError("HyDE search requires an embedder")`; `_run_fresh`/`_run_compare` convert that to `ClickException("Personal eval failed: ...")`, aborting the complete run.

I reproduced this with the real pipeline on a minimal index: `SearchPipeline(conn, embedder=None).search("vec: embeddings", ...)` and `"hyde: embeddings"` both raise `RuntimeError`; `lex:`/`expand:` do not. This is not hypothetical:
- A document title/H1 such as `vec: embedding notes` or `hyde: retrieval notes` becomes a title query verbatim (`synthesize_title_queries` uses `documents.title` unchanged).
- A later prose sentence can begin with those tokens as a body query.
- Most importantly, `_record_query_history` logs the raw query text (`src/sif/cli/commands/search.py:293`), so a single historical `sif search query "vec: ..."`/`"hyde: ..."` search makes `sif eval --personal --bm25-only` (and any `--compare` over a saved run containing it) fail after synthesis, with a cause unrelated to the personal corpus. The two real-pipeline CLI tests use prefix-free fixture titles, so nothing pins this behavior.

**Fix:** Evaluate eval queries literally. Add a literal mode to the pipeline (e.g. `SearchPipeline.search(query, options, parse_prefix=False)` or a private `_search_literal` used by a new helper) and construct the eval's search function with prefix parsing disabled, so known-item and replay text is never reinterpreted. Keep one literal pipeline for known-item and replay. Add tests with a `vec:` title, a `hyde:` body candidate, and a seeded `vec:` history query, asserting the run completes and the query is executed as text.

## Warnings

### WR-01: `-n/--limit` accepts zero and negative values — unbounded retrieval and self-invalid saved runs

**File:** `src/sif/cli/commands/eval.py:773-776`
**Issue:** The option is declared `@click.option("-n", "--limit", default=10, ...)` with no type/range. Click infers `int` and accepts `0` and negatives (verified). `limit` flows straight into `SearchOptions.limit` (`_build_options`, eval.py:116-132), and SQLite treats a negative `LIMIT` as “no limit”: `sif eval --personal --bm25-only -n -1` searches for *all* matches per query (unbounded work and a potentially enormous result set) and `-n 0` measures zero results. Both values are then written into the auto-saved run as `top_k`, which `load_saved_run` rejects (`personal_bench.py:1581`, `minimum=1`). I reproduced `-n 0`: the command exits 0, announces a `run_path`, and `load_saved_run` on that very file fails with `Invalid saved run field 'top_k': must be >= 1, got 0`.
**Fix:**
```python
@click.option("-n", "--limit", default=10, type=click.IntRange(1, 200),
              help="Number of results per query")
```
Choose the maximum so the saved-run caps remain reachable (see WR-02), and always pass only the validated depth into `SearchOptions`.

### WR-02: The saved-run writer never validates what it writes; the CLI can produce runs its own loader refuses

**File:** `src/sif/cli/commands/eval.py:432-456`; `src/sif/search/personal_bench.py:1265-1307`, `:1470-1481`, `:1581`, `:1631-1645`, `:1655-1665`
**Issue:** `_save_run` calls `run_to_saved` and writes the JSON without ever running `validate_saved_run`, and `run_to_saved` copies unbounded values into the envelope. The loader's own contract (top_k >= 1, query <= 10,000 chars, paths <= 4,096 chars, each retrieved array <= 10,000 entries, whole file <= 5 MB) is therefore not a property of the writer's output. Concrete triggers:
- WR-01's `-n 0`/negative → `top_k <= 0`, rejected on load.
- `-n 100` on a 500-query run with realistic ~100-char paths serializes to ~6.2 MB (I constructed the report and measured 6,200,639 bytes > the 5,242,880-byte cap), so `--compare` later refuses the tool's own run.
- A title longer than 10,000 characters (titles are copied verbatim) or a path longer than 4,096 characters produces `query`/`target_path` values the loader rejects.
- `top_k` is validated only with `minimum=1`; there is no maximum, and compare mode uses `saved.top_k` directly as the retrieval depth (`eval.py:662-667`), so a crafted 5 MB run can request arbitrary depth. `MAX_SAVED_RECORDS` likewise bounds memory but not the O(N²) bootstrap work (10,000 queries × 10,000 resamples per gate).

**Fix:** Validate before writing: `validate_saved_run(saved_run_to_dict(run))` inside `_save_run` (translate failure to a clear `ClickException`, or clamp/annotate first). Additionally cap `top_k` at a sane maximum in both `validate_saved_run` and the CLI, cap each `retrieved`/`retrieved_doc_ids` array at `top_k` in `run_to_saved`, and either enforce the 5 MB cap on write with a user-facing message or reduce `MAX_SAVED_RECORDS`/the CLI depth so the cap is reachable. Add a round-trip test that runs the CLI with a non-default depth and asserts the produced file loads.

### WR-03: `RecursionError` from a deeply nested saved-run file escapes as a traceback

**File:** `src/sif/search/personal_bench.py:1666-1675`; `src/sif/cli/commands/eval.py:506-513`
**Issue:** `load_saved_run` catches `(OSError, ValueError)` around `json.loads`, but Python's JSON decoder raises `RecursionError` for deeply nested input (e.g. 100,000 nested arrays in a 200 KB file — well under the 5 MB cap). I reproduced the escape: `load_saved_run` on `"[" * 100000 + "]" * 100000` raises `RecursionError`, not `ValueError`. `_load_saved` catches only `ValueError`, so the CLI prints a raw traceback. This contradicts T-18-07's “all defects → `ValueError` → `ClickException`” claim for untrusted saved-run input.
**Fix:** Catch `RecursionError` alongside `(OSError, ValueError)` and convert it to a field-naming `ValueError` (“nested too deeply”), or pre-check the nesting depth before decoding. Add a test with a legal-size deeply nested file.

### WR-04: The replay leg bypasses the `SIF_QUERY_HISTORY_ENABLED=0` read opt-out

**File:** `src/sif/cli/commands/eval.py:585`; `src/sif/search/personal_bench.py:770-782`
**Issue:** The setting is documented as disabling “both the write and the read side globally” (`src/sif/config/settings.py:249-256`), and `SuggestionEngine.history_suggestions` honors it (`suggest.py:228-230`). The fresh eval path calls `load_replay_queries(db.connection)` unconditionally, so a user who disabled query history still has their stored `query_log` text read, evaluated, echoed in `--json`, and written into every auto-saved run (plus embedded by a remote provider in hybrid mode). No test covers the disabled setting.
**Fix:** In `_run_fresh`, gate the replay leg on `settings.query_history_enabled` (which the CLI already holds); when disabled, return an unavailable `ReplayResult` and add a note (“Replay skipped: SIF_QUERY_HISTORY_ENABLED=0”) instead of reading the table. Compare mode may keep using the saved file's replay snapshot, since that text came from the user-supplied file rather than a fresh log read. Add a CLI test with the setting off and pre-seeded rows.

### WR-05: Saved runs contain literal document-body text, contradicting the “never contains document content” guarantee

**File:** `src/sif/search/personal_bench.py:1285-1298` (query copied from the body-leg record), `:883-904`, `:653-679`; `docs/benchmarking.md:171`; `.planning/phases/18-.../18-SECURITY.md` T-18-04
**Issue:** The body leg synthesizes a query as a normalized 4–10-unit excerpt of the document body (`body_candidate`/`_candidate_text`), and `run_to_saved` copies that text into `queries[].query`. Every auto-saved run therefore contains verbatim (casefolded, punctuation-stripped) document phrases. I reproduced it against the 60-document fixture: the saved file contains `"query": "document body 022 discusses local search quality retrieval metrics deterministic"`. The docs promise the run “never contains document content, snippets, or embeddings”, and T-18-04 (high) claims body text is rejected — but `_SAVED_FORBIDDEN_KEYS` only rejects keys literally named `content`/`snippet`; the `query` field carries the excerpt. The tests give false assurance: `test_saved_file_contains_no_document_body_text` (`tests/unit/search/test_personal_bench.py:1035-1044`) uses synthetic queries and asserts the capitalized `"Document body"`; the CLI test (`tests/unit/cli/test_eval.py:958-961`) does the same while the stored body query is casefolded.
**Fix:** Make the claim honest — and make the security register/docs say body-leg query text is a short excerpt of the sampled document (and is sent to a remote provider when hybrid). If that excerpt is unacceptable, store a reproducible locator (document id + selected sentence index/hash) and re-synthesize deterministically at compare time instead of storing the text. Update both tests to assert the real property (e.g. that the body-leg query text is present and is an excerpt, or that no full body/snippet is present) rather than a casing that cannot match.

### WR-06: The noise gate can warrant a defaults change from one query, below its own displayed noise floor

**File:** `src/sif/search/personal_bench.py:1714-1769` (`winner`/`regression` decision), `:2074-2077` (`warrants_default_change`)
**Issue:** `noise_floor = 1/N` is computed and displayed, but the decision uses only `CI excludes zero AND round(mean_delta, 6) >= EPSILON`. `sufficient` is `True` for any non-empty series. Consequences I verified: `noise_gate([0.0], [0.01])` → `winner=True`, `noise_floor=1.0`; N=25 (the fresh held-out floor) → `noise_floor=0.04 > 0.01` while `winner=True`. A saved run with a single held-out record therefore sets `warrants_default_change=True`; the suite actually pins this (`test_unique_path_is_the_only_fallback`, `tests/unit/search/test_personal_bench.py:1703-1731`, ends with `assert comparison.warrants_default_change is True` on a one-record held-out split). The docs say the floor “exposes” such a win as noise, but the instrument still warrants the change.
**Fix:** Make the decision consistent with the displayed floor: require `N >= SUPPRESS_BELOW` for a non-empty `winner`/`warrants_default_change` (keep smaller gates visible as `sufficient: false` diagnostics), or require `mean_delta > noise_floor` in addition to `EPSILON`. Keep the 1/N display. Update the one-record test to expect no warrant and add boundary tests at N=9/10 and mean_delta == noise_floor.

### WR-07: `retrieval: "hybrid"` is reported without verifying the index has any vectors

**File:** `src/sif/cli/commands/eval.py:570-572`, `:645-647`; evidence `src/sif/search/hybrid.py:59-72`
**Issue:** `retrieval` is derived from the `--bm25-only` flag, not from index state. With the default hybrid path and an index built by `sif index update` but not `sif index embed`, `HybridSearcher.search` finds zero vector results and silently returns the BM25 list, while the report (and the saved run's `retrieval`) says `hybrid`. I verified an empty `document_embeddings` table returns BM25 results with no error or warning. Compare mode has the same issue: a saved hybrid run is compared against a current arm labelled hybrid that is effectively BM25. The table/JSON therefore misstate what was measured.
**Fix:** When not `--bm25-only`, check that the scoped index has at least one embedding (a cheap `SELECT 1 FROM document_embeddings LIMIT 1` or the existing staleness/`embedded_document_ids` helper). If none, either fail with the `sif index embed` remedy (consistent with D-11's fail-loud default) or record a loud note/field (`vector_coverage: 0`) and print it on stderr. Add a CLI test on a non-embedded index.

### WR-08: The overlap budget is blind to CJK title echoes

**File:** `src/sif/search/personal_bench.py:98`, `:523-533`, `:907-933`
**Issue:** `token_set` keeps each contiguous CJK run as one token, and `apply_overlap_budget` computes Jaccard over those whole runs. A body candidate that is a verbatim prefix of the title is therefore a completely different set element: zero overlap. I reproduced title `如何配置混合搜索引擎的权重` with body candidate `如何配置混合搜索引擎` (a 10-character literal prefix) being kept with `rejected_overlap={}`. The zh language bucket is reported, so this weakens the stated bias control exactly where it is most needed; there is no zh budget test.
**Fix:** Compute the budget similarity with CJK-aware units (e.g. overlapping character bigrams/trigrams for CJK runs, or a character-level Jaccard between the normalized query and the title/opening) while keeping whole-run tokenization for FTS matching. Add a test asserting a CJK title-prefix body candidate is rejected and that a genuinely paraphrased CJK sentence is kept.

### WR-09: Several failure paths escape the CLI's `ClickException` contract as raw tracebacks

**File:** `src/sif/cli/commands/eval.py:566-569`, `:716-718`, `:446`, `:160-161`
**Issue:** The shared DB boundary explicitly covers construction/schema init only, “never the command body” (`src/sif/cli/error_handling.py`), and the new eval body leaves several foreseeable failures outside a handler:
- `ensure_heldout` is wrapped only in `except ValueError`; an `sqlite3.OperationalError` from `load_sampled_content` (locked/corrupt index) propagates.
- `_resolve_collection_ids` and `load_document_metadata` run with no handler (`run_personal`).
- `Settings.get_cache_dir()` — which creates the platform cache directory (`settings.py:402-411`) — is called outside `_save_run`'s `try` (`eval.py:446`), so a read-only/unwritable cache root raises `OSError` past the command's `ClickException` wrapper. `--no-save` avoids it, but the default path fails with a traceback.
- The embedder identity probe (`manager.get_model_info()` / `embed_single("probe")`, `eval.py:160-161`) is outside `_load_embedder`'s try; a model whose metadata has no usable dimension and whose probe raises produces a traceback instead of the promised remedy-bearing error.

**Fix:** Extend the translation boundaries: wrap the collection/metadata/synthesis section in `except (sqlite3.Error, OSError) as e: raise ClickException(...)` (plus the existing `ValueError`), move the cache-dir resolution inside `_save_run`'s `try`, and move the model-identity resolution inside `_load_embedder`'s handler. Add tests that monkeypatch an `sqlite3.OperationalError` on metadata load and an `OSError` from `get_cache_dir`.

### WR-10: The remote-provider disclosure omits replay history (and title/body provenance)

**File:** `src/sif/cli/commands/eval.py:167-172`, `:605-611`; `:585`; evidence `src/sif/search/hybrid.py:64-65`
**Issue:** The stderr notice and the report note say only “synthesized query text is sent to the configured provider”. The replay leg runs each normalized `query_log` entry through the same hybrid pipeline, which embeds it with the configured model, so logged user search history is also sent to a remote `openai`/`modelscope` provider. Titles and body excerpts (document-derived text) are sent as well. A user relying on the notice to keep history local while allowing synthesized titles is misinformed. T-18-15 names only synthesized text.
**Fix:** Broaden both messages to name the actual data crossing: document titles, body-sentence excerpts, and logged replay queries. Keep `--bm25-only` as the local path, and consider mentioning it in the report notes as well (the note already exists; just make it accurate).

## Info

### IN-01: Docs claim the model-identity mismatch is recorded in the comparison JSON; only stderr carries it

**File:** `docs/benchmarking.md:180`; `src/sif/search/personal_bench.py:477-510`
**Issue:** The doc says the retrieval-mode difference “and a model-identity mismatch” are recorded in the comparison JSON. `ComparisonReport.to_dict()` has no model/saved-model fields and no `model_mismatch` key; only `_print_comparison_warnings` (stderr) reports it.
**Fix:** Either add `model_mismatch` (and the saved/current model identities) to `ComparisonReport.to_dict()`, or correct the doc to say it is a stderr warning only.

### IN-02: Docs say suppressed group names go to stderr; the fresh table prints them to stdout

**File:** `docs/benchmarking.md:192`; `src/sif/cli/commands/eval.py:425-427`
**Issue:** In the fresh table path, `_render_personal` prints `Suppressed groups ...` via `console.print` (stdout). Only compare mode routes the names to `console_err`. The blanket doc sentence is inaccurate for the fresh path (JSON consumers are unaffected).
**Fix:** Route the fresh suppressed names to `console_err` for consistency (and to keep stdout for the report), or scope the doc statement to compare mode.

### IN-03: The saved-run path is not markup-escaped on stderr

**File:** `src/sif/cli/commands/eval.py:455`
**Issue:** `console_err.print(f"[dim]Saved run: {path}[/dim]")` interpolates a config-derived path into Rich markup without `_cell`/`escape`. A `SIF_CACHE_DIR` containing `[/bold]` raises `MarkupError` after the run is already written (I reproduced the exception), and bracket text is swallowed as styling. T-18-01's truncate-then-escape convention applies to user/config-derived cells.
**Fix:** `console_err.print(f"[dim]Saved run: {escape(str(path))}[/dim]", soft_wrap=True)` (or use `_cell`).

### IN-04: Dead/phantom code in the new modules

**File:** `src/sif/cli/commands/eval.py:58`; `src/sif/search/personal_bench.py:58`, `:64`, `:1069-1088`
**Issue:** `logger` in `eval.py` is never used. `MAX_QUERIES = 500` is never referenced: the documented 500-query cap exists only structurally (250 sampled docs × 2 legs), so raising `MAX_SAMPLE_DOCUMENTS` would silently break the stated cap. `RUN_SCHEMA_VERSION = 1` is unused (superseded by `SAVED_RUN_VERSION`), so no report-schema version is actually enforced. `require_minimum_queries` has no production caller (`ensure_heldout` owns the floor check); it is exercised only by tests. Ruff does not flag module-level assignments, so these survive the quality gates.
**Fix:** Remove the unused logger/constants/helper, or wire them to their stated purpose (enforce `MAX_QUERIES` after synthesis; use `RUN_SCHEMA_VERSION` in the report envelope or delete it).

### IN-05: The document-frequency tie-break in `_close_matches` is unreachable

**File:** `src/sif/search/suggest.py:283`; docstrings `:269-272`; `docs/architecture.md:674`
**Issue:** The sort key includes `-self._df.get(match[0], 0)` after the term key, but `documents_fts_v` in row mode yields one row per distinct term (verified: 3 rows / 3 distinct terms on a fixture with repeated terms), so the term key already breaks every score tie and the df key never changes the order. The docstring and architecture doc claim a real “score -> term -> document frequency” ordering that cannot be observed.
**Fix:** Drop the df key and correct both claims (or state that df is loaded for prefix ranking only). Add a test only if the order is meant to be load-bearing.

### IN-06: User-facing report text references an internal planning artifact

**File:** `src/sif/cli/commands/eval.py:597-598`
**Issue:** The note shown in tables/JSON says “Replay stability against a saved baseline is computed by --compare (Plan 03)”. “Plan 03” is a planning artifact reference with no meaning to CLI users.
**Fix:** Drop “(Plan 03)” from the note.

### IN-07: `prefix_completions(prefix, n=0)` returns one completion

**File:** `src/sif/search/suggest.py:108-116`
**Issue:** The loop appends the first match and only then tests `len(matches) >= n`, so `n=0` (and negative `n`) returns one term despite the “up to n” contract. I verified `prefix_completions("qu", 0) == ["quantum"]`. The CLI's `IntRange(1, 50)` hides it, but the method is a public API.
**Fix:** `if n <= 0: return []` before the scan (and guard `_close_matches`/`history_suggestions` similarly if they are public contracts).

### IN-08: Replay stability can be computed from a tiny subset and is displayed without N

**File:** `src/sif/cli/commands/eval.py:337-348`; `src/sif/search/personal_bench.py:1841-1866`
**Issue:** `replay_stability` joins only queries present on both sides and returns `available=True` for any non-empty join; `_comparison_context_table` prints the Jaccard/top-1 values without `num_queries`. A run whose saved replay snapshot barely overlaps the current results (e.g. one shared query) renders “Jaccard@10 1.0000” as if it were corpus-wide stability. The JSON carries `num_queries`, but the human table does not, and no warning fires for a partial join.
**Fix:** Show the shared count in the table (e.g. `Jaccard@10 (N=…)`), and warn/suppress when the joined count is below the same `SUPPRESS_BELOW` floor used for groups.

### IN-09: Architecture layering claim is stale after `personal_bench.py`

**File:** `docs/architecture.md:626`, `:630`; `src/sif/search/personal_bench.py:2`, `:35-36`
**Issue:** The architecture doc says `search/` reaches into `database/` only for the suggestion query-log repository. The new `personal_bench.py` imports `QueryLogRepository`, takes raw `sqlite3.Connection`s, and executes SQL in `load_document_metadata`/`load_sampled_content`/`resolve_saved_targets`; its module docstring still calls itself a “Pure domain module”. The project CLAUDE.md permits direct SQL in `search/`, so the code is consistent with the convention — the doc is not.
**Fix:** Update the architecture dependency sentence and the module docstring to describe the new storage dependency (read-only metadata/content and query-log reads).

### IN-10: Test battery gaps leave the stated edges unpinned

**File:** `tests/unit/cli/test_eval.py`, `tests/unit/search/test_personal_bench.py`, `tests/unit/search/test_suggest.py`
**Issue:** The suite is broad, but several of the phase's own claimed edges have no test: `-n 0`/negative (WR-01) and saved-run write/load round-trips at non-default depths or long paths (WR-02); deep JSON (WR-03); history-disabled replay (WR-04); prefix-bearing title/body/replay queries (CR-01); CJK overlap (WR-08); and hybrid runs on a non-embedded index (WR-07). The body-content test asserts the wrong casing (WR-05), and the one-record held-out test pins the small-N warrant (WR-06). The real-pipeline CLI tests use only prefix-free fixture titles, so the pipeline interaction is never exercised.
**Fix:** Add the targeted tests named in each finding; they are cheap and each corresponds to a reproduced defect or a stated contract.

### IN-11: `load_document_metadata` claims it cannot materialize the corpus, but it does

**File:** `src/sif/search/personal_bench.py:731-742`
**Issue:** The comment says the cursor “is iterated row by row (never `fetchall()`) so the whole-corpus pass cannot materialize the corpus in one list of rows”, but the function returns a list comprehension over the cursor — every row becomes a `DocumentRecord` in memory. The real protection is the metadata-only column list (no `content`), not lazy iteration. The security register's wording inherits the same overstatement.
**Fix:** Correct the comment/docstring to say the pass materializes metadata only and never bodies; drop the “cannot materialize” claim.

---

_Reviewed: 2026-11-14T15:58:58Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
