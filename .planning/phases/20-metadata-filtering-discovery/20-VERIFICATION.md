---
phase: 20-metadata-filtering-discovery
verified: 2026-11-15T14:27:36Z
status: passed
score: 26/26 must-haves verified
covered_files:
  - .planning/phases/20-metadata-filtering-discovery/20-01-PLAN.md
  - .planning/phases/20-metadata-filtering-discovery/20-01-SUMMARY.md
  - .planning/phases/20-metadata-filtering-discovery/20-02-PLAN.md
  - .planning/phases/20-metadata-filtering-discovery/20-02-SUMMARY.md
  - .planning/phases/20-metadata-filtering-discovery/20-03-PLAN.md
  - .planning/phases/20-metadata-filtering-discovery/20-03-SUMMARY.md
  - .planning/phases/20-metadata-filtering-discovery/20-04-PLAN.md
  - .planning/phases/20-metadata-filtering-discovery/20-04-SUMMARY.md
  - .planning/phases/20-metadata-filtering-discovery/20-05-PLAN.md
  - .planning/phases/20-metadata-filtering-discovery/20-05-SUMMARY.md
  - docs/cli-reference.md
  - src/sif/cli/commands/collection.py
  - src/sif/cli/commands/search.py
  - src/sif/cli/filter_options.py
  - src/sif/core/filters.py
  - src/sif/core/models.py
  - src/sif/database/metadata_repository.py
  - src/sif/database/repositories.py
  - src/sif/database/schema.py
  - src/sif/indexing/incremental.py
  - src/sif/mcp/backend.py
  - src/sif/mcp/handlers.py
  - src/sif/mcp/protocol.py
  - src/sif/search/bm25.py
  - src/sif/search/filters.py
  - src/sif/search/hybrid.py
  - src/sif/search/vector.py
  - src/sif/utils/json_output.py
  - tests/integration/test_metadata_filtering.py
  - tests/support/bench.py
  - tests/unit/cli/test_collection.py
  - tests/unit/cli/test_search.py
  - tests/unit/cli/test_search_filter.py
  - tests/unit/core/test_filters.py
  - tests/unit/database/test_metadata_values.py
  - tests/unit/database/test_repositories.py
  - tests/unit/database/test_schema.py
  - tests/unit/indexing/test_incremental.py
  - tests/unit/mcp/test_backend.py
  - tests/unit/mcp/test_integration.py
  - tests/unit/search/test_filters_sql.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/search/test_vector.py
covered_digest: "v4:sha256:bc58f10f1f215db14316be3590948feac138a09579bd98ab0c2b8b46a0a88bf6"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 20: Metadata Filtering + Discovery Verification Report

**Phase Goal:** Users and agents can scope searches precisely with metadata filters applied before fusion — qmd-unreleased AST parity plus built-in path/mtime fields, and a discovery tool so agents never guess keys.
**Verified:** 2026-11-15T14:27:36Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

The first five rows are the ROADMAP §Phase 20 success criteria (the contract); the rest are plan-derived truths, deduplicated against the roadmap wording.

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1 | User can filter any CLI search with `--filter <json>` and any MCP query with `filter` — recursive and/or/not + comparison/in/contains/type/exists with qmd semantics verbatim (typed exact match, no coercion, missing keys don't match `ne`/`nin`, budgets enforced) | ✓ VERIFIED | `src/sif/core/filters.py` implements all 17 operators (`Eq`..`Not`), `FilterValidationError`, iterative budget pre-walk (depth 8 / 64 nodes / 1024-char string / 128-element array); 50 tests in `tests/unit/core/test_filters.py`. Independent CLI run: `eq`, `in`, `contains`, `caseInsensitive`, `ne`/`nin` presence semantics all behaved as specified. MCP handler uses the same `parse_filter` (`src/sif/mcp/handlers.py:97`, `:279`). |
| 2 | User can filter by built-in `path` and `mtime` fields (mtime indexed) — strictly more expressive than qmd's frontmatter-only AST | ✓ VERIFIED | `path`/`mtime` resolve to `documents` columns in `src/sif/search/filters.py:593-600`; independent `EXPLAIN QUERY PLAN` on a populated DB: `SEARCH d USING COVERING INDEX idx_documents_path (path>? AND path<?)` and `SEARCH d USING COVERING INDEX idx_documents_mtime (mtime>?)`. Manual CLI `mtime gte "2020-01-01"` and `path prefix`/`contains` worked. `idx_documents_mtime` is created in `schema.py:636`. |
| 3 | Filters apply pre-RRF per leg — BM25 outer WHERE of the materialized CTE (never inside it), vector post-KNN JOIN with adaptive over-fetch, a selectivity bound, and an honest "too selective" message; parameterized SQL only (no injection surface, no post-fusion filtering) | ✓ VERIFIED | `bm25.py:106-160` appends the predicate after `{min_score_filter}` in both branches' outer WHERE; `vector.py:129-230` appends it to the post-KNN JOIN WHERE, pre-counts, seeds `fetch_k`, stops on distinct-doc target/ceiling/whole-table, and warns via `logger.warning` only. Integration battery (`tests/integration/test_metadata_filtering.py`, 15 tests) proves containment, 2 % recall, composition, empty sentinel. Manual injection-shaped operand left the DB intact and returned `[]`; compiler tests assert SQL shape unchanged under `'`, `;`, `--`, `%`. |
| 4 | User's existing indexes filter correctly after upgrade — typed frontmatter storage + backfill runs, `qmd.metadata`-namespaced keys filter identically to native keys; numeric values compare as numbers, not strings | ✓ VERIFIED | Independently simulated a pre-Phase-20 index (deleted all typed rows + the marker): the next CLI search emitted one stderr warning, wrote `metadata_values_version=1`, rebuilt 11 typed rows, and the filter returned the right document. Manual `qmd.metadata` note filtered by `status=namespaced` (1 hit) while `status=native-loses` returned 0 (namespace wins). Manual `priority eq 10` matched the int/float documents; `eq "10"` matched none. |
| 5 | Agent can discover available metadata via a `metadata` tool on CLI + MCP — doc counts, numeric min/median/max, exact remainders; ONE validator shared with the filter surface; invalid filter → ToolError, never a protocol error | ✓ VERIFIED | `sif collection metadata --json` manual envelope: `documents`, `totalKeys`, `remainingKeys`, `skippedKeys`, `builtIns`, `keys` (and `filteredDocuments` only under `--filter`); numeric range `{'min': 10.0, 'median': 20.0, 'max': 30.0}`. MCP `MetadataToolHandler` registered as the fifth tool (`handlers.py:243-316`), schema declares all seven inputs; `TestInvalidFilterIsNotAProtocolError` and `test_invalid_match_is_not_a_protocol_error` assert a successful JSON-RPC envelope with `result.isError == true`. |
| 6 | Equality is typed and exact: a boolean never matches a numeric operand, `"10"` never matches numeric `10`, and `10` matches `10.0` (both stored as number) | ✓ VERIFIED | `tests/integration/test_metadata_filtering.py::TestTypedExactMatch`; compiler `_value_type_of` checks bool before number; manual CLI `priority eq 10` → active note, `priority eq "10"` → none. |
| 7 | Equality and ordering are byte/code-point exact on the stored value; `caseInsensitive` folds ASCII only and performs no Unicode normalization | ✓ VERIFIED | `_ascii_lower` uses an explicit A-Z translate table; SQLite `lower()` wraps the compared column only under the flag. `test_no_lower_without_flag` and `test_non_ascii_case_pair_does_not_match` (Ä/ä) pin it. Manual `status eq "ACTIVE" caseInsensitive:true` matched `active`. |
| 8 | A filter that admits every document reproduces the unfiltered BM25 page exactly; a filter that matches nothing returns an empty page and never degrades to the unfiltered result set | ✓ VERIFIED | Manual CLI: `exists status=true` returned the same five paths as unfiltered; `eq status=nope` returned `[]`. Integration `TestAdmitAllEquivalence` compares ids/ranks/scores for hybrid. |
| 9 | The unfiltered BM25 path issues exactly the same statements it issued before this plan (no pre-count, no new query) and emits no new output | ✓ VERIFIED | Module-level goldens `_HEAD_UNFILTERED_SQL/_PARAMS` and `_HEAD_SCOPED_SQL/_PARAMS` in `tests/unit/search/test_filters_sql.py:41-85`, captured pre-change; `test_unfiltered_statement_byte_identical`, `test_scoped_statement_byte_identical`, `test_no_filter_emits_no_extra_statement` pass. |
| 10 | `path` prefix compiles to a half-open range that EXPLAIN QUERY PLAN resolves through `idx_documents_path`; `mtime` ranges resolve through `idx_documents_mtime` | ✓ VERIFIED | `_path_prefix_sql` binds `prefix` and `prefix + "\U0010ffff"`; `TestQueryPlans` asserts both index names; independent plan check printed both indexes (see truth 2). |
| 11 | `qmd.metadata`-namespaced keys filter identically to native keys, and the namespace wins on collision; a document without the namespace is unaffected | ✓ VERIFIED | `filterable_metadata` merges `qmd.metadata` over native keys, drops native collisions; `TestDerivation::test_namespace_wins_on_collision_and_merges_native_keys` / `test_document_without_namespace_is_unaffected`; manual CLI confirmed. |
| 12 | A frontmatter key named `path` or `mtime` is shadowed and never appears as a frontmatter key; it is reserved, not a skipped key | ✓ VERIFIED | `filterable_metadata` pops both names before classification; `test_reserved_names_are_shadowed_not_skipped`; manual corpus note with `path`/`mtime` frontmatter produced no such `keys` entries and no skip row, while both `builtIns` appeared. |
| 13 | The backfill is idempotent and resumable: re-running after a complete pass is a no-op; an interrupted pass leaves committed batches intact, writes the marker only after a complete pass, and never serves filtering from a half-populated store | ✓ VERIFIED | `SchemaManager._backfill_metadata_values` (schema.py:277-316) uses per-document `with self.db:`, writes the marker last, and does not catch exceptions. `TestMetadataBackfill` covers fresh/populated/reopen/interrupted-resume (snapshot equality, zero duplicates). Manual interrupted-equivalent simulation rebuilt correctly. |
| 14 | A ~2 % selectivity filter returns its matching documents (never an empty page) through the vector leg, and a short page is honest rather than padded | ✓ VERIFIED | `TestSelectiveRecall::test_two_percent_filter_returns_rare_documents_on_all_paths` (200 docs, 4 rare) asserts BM25, vector, and pipeline all return exactly the 4; `test_short_page_below_page_target_logs_no_notice` asserts 4 results with no warning. |
| 15 | The too-selective warning fires only when the filter's matching count is at least the page target AND the fetch ceiling was exhausted with a short page; never for a genuinely short page or a collection-only search | ✓ VERIFIED | The four-clause guard at `vector.py:212-218`; `test_too_selective_notice_fires_once_with_formatted_counts` asserts exactly one message with `3 of 10 matching documents reached, 10 requested`; `test_short_page_below_page_target_logs_no_notice`, `test_all_matches_found_logs_no_notice`, and the collection-only test pin the suppressed branches. |
| 16 | An empty filter match set returns an empty page on both legs (never the unfiltered set), and a filter admitting every document reproduces the unfiltered page | ✓ VERIFIED | `pre_count == 0` returns `[]` before any KNN (`vector.py:175-177`); BM25 outer WHERE yields zero rows. `TestEmptyMatchSentinel` covers all commands and both legs; manual CLI returned `[]`. |
| 17 | Both legs receive the same AST before fusion: `filtered-hybrid ⊆ unfiltered-hybrid ∩ filter-set` over a generated corpus | ✓ VERIFIED | `HybridSearcher.search` passes the identical `SearchOptions` (with `.filter`) to both legs via `replace` (`hybrid.py:91-104`); `TestFilterPassthrough::test_both_legs_receive_the_same_ast_object` asserts identity; integration `TestContainmentInvariant` parametrizes several filters. |
| 18 | An unfiltered, unscoped vector search issues exactly the statements and fetch window it issued before this plan (no pre-count, no warning) | ✓ VERIFIED | `test_unfiltered_unscoped_path_issues_only_the_pre_change_statement` records statements via `_RecordingConnection`; the `has_join_filter` branch is skipped when `filter is None` and no collection scope. |
| 19 | Per-chunk mode counts distinct documents for the all-matches test, so duplicate chunks cannot end escalation early | ✓ VERIFIED | `found = len({row["document_id"] for row in rows})` from raw rows (`vector.py:189`); `test_per_chunk_mode_sees_every_matching_document` places the fifth match at global rank 51 and asserts it is returned. |
| 20 | `--filter <json>` exists on all three CLI result commands with the same grammar/semantics; `get`/`multi-get`/`ls` are untouched; an invalid filter fails as user input before the pre-search refresh with an actionable ClickException | ✓ VERIFIED | `--filter` decorators at `search.py:481/680/884`; parse runs before `open_initialized_database` (`:526/727/987`); `grep '"--filter"' src/sif/cli/commands/` shows only the three search commands plus `collection metadata`. `TestFilterOptionMatrix` asserts the flag, the JSON/grammar errors, and that `_pre_search_refresh`/DB-open spies are never called; manual `path lt` printed `Error: filter.lt: "lt" does not support ordering on a text built-in; field 'path'` with exit 1. |
| 21 | All three MCP search inputs carry `filter`, the query handler's hand-written `input_schema` declares it, and an invalid MCP filter returns `ToolsCallResult(isError=True)` inside a successful JSON-RPC response, never `INVALID_PARAMS` | ✓ VERIFIED | `protocol.py:253/292/316` declare `filter: dict[str, Any] \| None`; `handlers.py:72` declares `"filter": {"type": "object"}`; `TestInvalidFilterIsNotAProtocolError` dispatches through the real `MCPServer` and asserts `response.error is None`, `result["isError"] is True`, and no `error` key. |
| 22 | Filter composes by AND with `--collection`/`collections`, `--min-score`, `--offset`, `--per-chunk`, and reranking, and both legs receive the same AST; an unfiltered CLI/MCP search keeps `SearchOptions.filter is None` and emits nothing new | ✓ VERIFIED | `TestFilterComposition` asserts the `SearchOptions` carries collection/offset/min-score/filter per command; `TestNoFilterRegression` asserts `filter is None` on all three commands; `test_pipeline_propagates_filter_to_every_variant_and_enriches_once` covers pipeline variants. |
| 23 | Discovery reports exact totals: key window + `remainingKeys` == `totalKeys`, and each type's value window + `remainingValues` == its distinct-value count; min/median/max come from typed numeric rows and mixed-type keys split per type | ✓ VERIFIED | `TestDiscovery` (14 tests) covers odd/even medians, array elements each counting, documents-not-values counts, boundary remainders, `min_count`, mixed-type splits. Manual output: `totalKeys=3, remainingKeys=0`; priority range `10/20/30` computed by `ROW_NUMBER() OVER ... COUNT(*) OVER` with integer-division positions. |
| 24 | Discovery never lies: every reported key (frontmatter or built-in) is filterable, every filterable key appears, and a non-indexable key is counted in `skippedKeys` rather than silently dropped or presented as filterable | ✓ VERIFIED | `TestDiscoveryParity` proves both directions (`reported ⇒ filterable`, `filterable ⇒ reported`) plus the nested-key case and the built-ins' own filterability, without sqlite-vec. Manual corpus: nested key counted in `skippedKeys=1`, absent from `keys`, and its document still matched on `status`. |
| 25 | `path` and `mtime` are reported as built-in fields, never frontmatter keys — only in `builtIns` with scope- and filter-aware counts and an `mtime` numeric range, even when a document's frontmatter carries a same-named key | ✓ VERIFIED | `_built_in_entries` queries `documents.path/mtime` over the region CTE, never the typed store; manual JSON `builtIns` order `['path','mtime']`, counts narrowed to 1 under `--filter`, and the shadowed-frontmatter note produced no `keys` entries. `TestCollectionMetadata` and MCP tests assert the same. |
| 26 | When a filter is supplied, all counts are measured against the admitted set and `filteredDocuments` is present; without a filter it is absent. Default ordering is document count desc then key asc; key window 50, value window 10 | ✓ VERIFIED | `discover` adds `filteredDocuments` only when `filter_predicate is not None`, computes builtIn counts over the same region, and orders `documents DESC, key ASC` (`sort="count"`). Manual no-filter JSON omitted `filteredDocuments`; filtered JSON set it to 1 and narrowed every count. CLI/MCP defaults match the generated docs (`limit=50`, `value_limit=10`). |

**Score:** 26/26 truths verified (0 present, behavior-unverified)

### Prohibitions (must-NOT checks)

All plan `must_haves.prohibitions` were checked against code and executable evidence; `verification_notes` describe the implementing constraint, and each is corroborated by a named test or a direct run.

| Plan | Prohibition | Status | Evidence |
| ---- | ----------- | ------ | -------- |
| 20-01 | A filter must never silently widen: missing keys must not satisfy `ne`/`nin`; a non-None filter never compiles to an empty predicate | ✓ VERIFIED | `_kv_ne`/`_kv_membership` compile presence-EXISTS + `NOT EXISTS`; `test_ne_is_presence_and_negation`, `test_nin_is_presence_and_negation`, `test_non_none_never_returns_empty`; manual `priority ne 10` excluded keys-absent documents. |
| 20-01 | Ordering operators must never compare strings lexicographically | ✓ VERIFIED | Validator requires finite numeric (except `mtime` ISO); compiler rejects text/array on ordering; `test_ordering_compares_numbers`, `TestBuiltInFieldMatrix` rejections. |
| 20-01 | `caseInsensitive` must never perform Unicode case folding or normalization | ✓ VERIFIED | `_ascii_lower` translate table + SQLite `lower()`; `test_non_ascii_case_pair_does_not_match`. |
| 20-01 | Filters must never be applied after fusion | ✓ VERIFIED | Predicate in BM25 outer WHERE and vector post-KNN JOIN; both legs receive the AST through `replace`; identity + containment tests. |
| 20-01 | The unfiltered search path must stay byte-identical | ✓ VERIFIED | Pre-change goldens + three byte-identical tests (truth 9). |
| 20-02 | The backfill must never leave filtering enabled against a half-populated store | ✓ VERIFIED | Per-document transactions, marker last, exceptions propagate out of `create_all`; `TestMetadataBackfill` interruption case. (Read-side defence-in-depth is the open Info item IN-05, not a violation of this call-site contract.) |
| 20-02 | Typed rows must never be derived from the in-memory metadata dict | ✓ VERIFIED | `typed_rows(canonical_json)` is the only derivation entry; both repository write sites pass the same canonical string; date-valued-key parity test. |
| 20-02 | Discovery and filtering must never read metadata with SQLite JSON1 functions | ✓ VERIFIED | Repo-wide grep for `json_each`/`json_extract` over the phase source paths returns nothing; Python `json.loads` is the only reader. |
| 20-02 | The migration announcement must never be written to stdout | ✓ VERIFIED | `logger.warning`; `TestMetadataBackfill` asserts `capsys.out == ""`; manual run showed the notice on stderr while `--json` stdout parsed cleanly. |
| 20-03 | Filtering must never happen after fusion | ✓ VERIFIED | Same as 20-01 row; `TestFilterPassthrough` and pipeline variant test. |
| 20-03 | The too-selective notice must never be written to stdout, the result list, or JSON output | ✓ VERIFIED | `logger.warning` only; `TestNoticeStaysOffStdout`; manual `--json` parse clean. |
| 20-03 | The warning must never fire when the filter genuinely matches fewer documents than requested | ✓ VERIFIED | Guard requires `pre_count >= page_target`; both suppressed branches tested. |
| 20-03 | An empty filter match must never degrade to the unfiltered search | ✓ VERIFIED | `pre_count == 0` returns `[]` before KNN; `TestEmptyMatchSentinel`; manual CLI `[]`. |
| 20-04 | Filter validation must never surface as a JSON-RPC protocol error | ✓ VERIFIED | Real-server dispatch test asserts success envelope + `isError`, no `error` key. |
| 20-04 | The MCP boundary must never drop a caller-supplied filter | ✓ VERIFIED | `filter_node` threaded to `SearchOptions.filter`; identity/equality tests; BM25 fallback receives the same options. |
| 20-04 | Generated documentation must never be hand-edited | ✓ VERIFIED | `make docs-generate` exited 0 and `git diff --exit-code docs/cli-reference.md docs/configuration.md` was clean. |
| 20-04 | Diagnostics must never be written to CLI JSON output | ✓ VERIFIED | `TestFilterOptionMatrix::test_filtered_json_output_is_clean_json` parses stdout and asserts no notice text. |
| 20-05 | Discovery must never read the metadata blob with SQLite JSON1 functions or any second source of truth | ✓ VERIFIED | Same grep; discovery joins `document_metadata_values` + `documents` only. |
| 20-05 | Skipped keys must never be presented as filterable keys | ✓ VERIFIED | `discover` reads `keys` from the typed store; skips only contribute `skippedKeys`; nested-key test proves no key entry and a filter miss. |
| 20-05 | Reserved built-ins must never be reported as frontmatter keys | ✓ VERIFIED | `filterable_metadata` drops `path`/`mtime`; `builtIns` computed from columns; manual shadowed-frontmatter run. |
| 20-05 | Discovery must never be unbounded: no `--all` mode, no unbounded value materialization | ✓ VERIFIED | Fixed key/value windows with exact remainders and batched page-only aggregates; no `--all` option exists. (Caller-supplied upper bounds are the open Info item IN-03, recorded below.) |
| 20-05 | Metadata and notice text must never be written to stdout outside the requested output mode | ✓ VERIFIED | `--json` prints only the envelope; table mode prints only table + remainder/skip footers; manual run confirmed. |

### Deferred Items

None. All five roadmap success criteria are achieved; no identified item needs a later milestone phase.

### Known Open Items (Code Review — Info, disposition `open`)

These five `Info` findings are recorded in `20-REVIEW-DISPOSITION.md` as `open` and are known, not gaps (per the phase brief). None blocks a must-have truth or the phase goal.

| ID | Finding | Impact assessment |
| -- | ------- | ----------------- |
| IN-01 | Two operator-set constants are dead code | Hygiene only; membership/group dispatch uses explicit `isinstance`/`in` checks that are exercised by tests. |
| IN-02 | `_collection_predicate([])` treats the exclude-all sentinel as "no scope" | Latent only: every current caller guards `[]`, and BM25/vector `search()` short-circuit before the compiler sees it. Stopgap tests pass. |
| IN-03 | Discovery window sizes have no upper bound | DoS hardening only; defaults are bounded (50/10), exact remainders make truncation legible, and no unbounded mode is exposed. |
| IN-04 | `collection metadata --json` uses compact JSON without `ensure_ascii=False` | Formatting only; the envelope is correct and strict; non-ASCII values are escaped `\uXXXX`, still valid JSON. |
| IN-05 | The half-populated-store rule has no read-side check | Defence-in-depth only; every production CLI/MCP read opens through `db.init_schema()` → `create_all()` → the gated backfill, and the backfill fails closed. |

## Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/sif/core/filters.py` | AST models, `parse_filter`, `parse_match`, `FilterValidationError`, budgets | ✓ VERIFIED | 714 lines; 19 classes (17 operators + base/condition), 5 budget constants, raw-payload semantic validation, mtime ISO normalization, reserved-field parse-time matrix. Imported by CLI, MCP, compiler, tests. |
| `src/sif/search/filters.py` | `compile_filter`, `compile_match`, scope counters | ✓ VERIFIED | 814 lines; parameterized fragments for both scopes, presence-aware `ne`/`nin`, `LIMIT 1` candidate probe (CR-02), half-open `path` prefix, built-in matrix, `compile_match`, three count helpers. Wired from `bm25.py`, `vector.py`, CLI discovery, MCP backend. |
| `src/sif/database/metadata_repository.py` | `filterable_metadata`, `typed_rows`, `TypedRow`, `SkippedKey`, `MetadataValueRepository` | ✓ VERIFIED | 648 lines; namespace merge + reserved shadowing, all caps/skip reasons, total numeric handling (CR-01), empty-array skip (WR-05), `replace_from_canonical`/`delete_by_document`/`discover` with exact window arithmetic. |
| `src/sif/database/schema.py` | Metadata DDL, three partial indexes, backfill, marker | ✓ VERIFIED | `_create_metadata_tables` at `create_all` position after documents; both tables in `drop_all`; `_backfill_metadata_values` with `metadata_values_version` marker and per-document transactions. |
| `src/sif/database/repositories.py` | One canonical string → row + kv rebuild | ✓ VERIFIED | `DocumentRepository.create` (151-176) and `.update` (233-252) each compute `canonical_metadata_json` once and pass it to both the row statement and `replace_from_canonical`. |
| `src/sif/core/models.py` | `SearchOptions.filter` | ✓ VERIFIED | `filter: FilterNode \| None = None` beside the collection sentinel, with the None-is-unfiltered contract comments. |
| `src/sif/search/bm25.py` | Filter suffix in both outer WHERE slots | ✓ VERIFIED | `compile_filter(..., scope="candidates")` at 106; suffix appended in both branches; `search_chunks` stays filter-free and documented. |
| `src/sif/search/vector.py` | Filtered pre-count, seeding, corrected escalation, notice | ✓ VERIFIED | `_TOO_SELECTIVE_MSG`, `_filtered_fetch_window`, empty-match short circuit, two-path stop condition, distinct-document target, guard-gated logger warning. |
| `src/sif/search/hybrid.py` | Contract docstrings (no behavior change) | ✓ VERIFIED | `fetch_options = replace(...)` already carries `filter`; docstrings document pre-RRF, early-return windows, per-chunk `chunk_matches`. |
| `src/sif/cli/commands/search.py` | `--filter` on all three commands + shared adapter | ✓ VERIFIED | Decorators at 481/680/884; parse before DB open; `_parse_filter_option` delegates to `sif.cli.filter_options.parse_filter_option`. |
| `src/sif/cli/filter_options.py` | One CLI JSON/AST adapter | ✓ VERIFIED | 44 lines; `parse_filter_option`/`parse_match_option` map JSON and grammar failures to `ClickException`. |
| `src/sif/cli/commands/collection.py` | `collection metadata` with 7 options, table/JSON | ✓ VERIFIED | Built-ins render first with `Source=built-in`; exact remainder footers; non-zero `skippedKeys` footer (WR-07); JSON emits only the envelope; validation before DB open. |
| `src/sif/mcp/protocol.py` | `filter` on 3 inputs; frozen discovery models | ✓ VERIFIED | 3 `filter` fields; `MetadataInput` (7 inputs), `MetadataOutput` (camelCase incl. `builtIns`), range/value/type/key summaries. |
| `src/sif/mcp/handlers.py` | Query filter path + `MetadataToolHandler` + registry | ✓ VERIFIED | `filter` property in query schema; controlled `isError` on `FilterValidationError`; `MetadataToolHandler` registered as fifth tool in `create_default_tools`. |
| `src/sif/mcp/backend.py` | `hybrid_search(filter_node=...)`, `metadata(...)` | ✓ VERIFIED | `options.filter = filter_node` in the shared options build; `metadata` compiles only supplied predicates, resolves collection names, returns the raw envelope via `_run_in_db`. |
| `src/sif/utils/json_output.py` | Strict machine JSON | ✓ VERIFIED | `json_dumps_strict` stringifies non-finite floats and serializes with `allow_nan=False` (WR-06). |
| `docs/cli-reference.md` | Regenerated flag/command docs | ✓ VERIFIED | `--filter` appears in the `search query`, `search search`, `search vsearch`, and `collection metadata` sections; generator diff gate clean. |
| Phase test batteries | AST, compiler, storage, vector, hybrid, CLI, MCP, integration | ✓ VERIFIED | 325 + 271 + 309 targeted tests passed independently; full suite 2482 passed, 1 skipped, 95.35 % coverage. |

## Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `src/sif/search/bm25.py` | `src/sif/search/filters.py` | `compile_filter(options.filter, alias="d", scope="candidates")` | ✓ WIRED | `bm25.py:106`; params appended between min-score and limit/offset. |
| `src/sif/database/repositories.py` | `src/sif/database/metadata_repository.py` | `MetadataValueRepository.replace_from_canonical(document.id, metadata_json)` | ✓ WIRED | Both create and update write sites. |
| `src/sif/cli/commands/search.py` | `src/sif/core/filters.py` | `_parse_filter_option` → `parse_filter_option` → `parse_filter` | ✓ WIRED | Adapter delegates; both errors map to `ClickException`. |
| `src/sif/search/filters.py` | `src/sif/database/schema.py` | `document_metadata_values(key, typed columns, document_id, ordinal)` | ✓ WIRED | `_KV_TABLE` and column names match the actual DDL exactly. |
| `src/sif/database/schema.py` | `src/sif/database/repositories.py` | `IndexMetaRepository.get/set("metadata_values_version")` | ✓ WIRED | Lazy imports inside `_backfill_metadata_values` (no cycle). |
| `src/sif/database/schema.py` | `src/sif/database/metadata_repository.py` | `replace_from_canonical` per document, one short transaction each | ✓ WIRED | Verified by interruption test and manual backfill. |
| `src/sif/database/metadata_repository.py` | `src/sif/core/models.py` | canonical JSON as the single derivation source | ✓ WIRED | Derivation takes the canonical string; the repository computes it once per write; date-valued parity test. |
| `src/sif/search/vector.py` | `src/sif/search/filters.py` | `compile_filter(...)` + `count_matching_documents`/`count_documents_in_scope`/`count_vectors_in_scope` | ✓ WIRED | Imports at `vector.py:11`; used in `_search_with_vec` and `_filtered_fetch_window`. |
| `src/sif/search/hybrid.py` | `src/sif/search/bm25.py` | `replace(options, limit=limit+offset, offset=0)` carries `options.filter` to both legs | ✓ WIRED | `hybrid.py:91-104`; identity-asserted in tests. |
| `src/sif/cli/commands/collection.py` | `src/sif/database/metadata_repository.py` | `discover(filter_predicate=compile_filter(...), match_predicate=compile_match(...))` | ✓ WIRED | Compiled fragments passed only when supplied; `None` otherwise. |
| `src/sif/database/metadata_repository.py` | `src/sif/database/schema.py` | `documents.path`/`documents.mtime` aggregates for `builtIns` | ✓ WIRED | `_built_in_entries` and `_mtime_median` query the region CTE. |
| `src/sif/mcp/handlers.py` | `src/sif/mcp/backend.py` | `SearchBackend.metadata(...)` → `_run_in_db(callback)` | ✓ WIRED | Handler builds `MetadataInput`, parses filter/match, calls backend. |
| `src/sif/mcp/protocol.py` | `src/sif/database/metadata_repository.py` | `MetadataOutput(**discovery_dict)` | ✓ WIRED | Handler constructs the model from the raw discover dict; `model_dump(exclude_none=True)` preserves omit semantics. |
| `src/sif/cli/commands/search.py` | `SearchOptions.filter` | `filter=filter_node` in all three commands | ✓ WIRED | Lines 544/772/1032. |
| `src/sif/mcp/backend.py` | `SearchOptions.filter` | `filter=filter_node` in `_search` | ✓ WIRED | `backend.py:191`; BM25-only fallback uses the same options. |
| `src/sif/mcp/handlers.py` | `src/sif/core/filters.py` | `parse_filter`/`parse_match` → `ToolsCallResult(isError=True)` | ✓ WIRED | Handler-local try/except; never reaches protocol error. |

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| BM25 filtered search | `filter_clause` / result rows | Frontmatter → `canonical_metadata_json` → `document_metadata_values` → compiler `EXISTS` probe → FTS outer WHERE | Yes — manual CLI returned exactly the frontmatter-matching document; `in` over a 2-element array returned each document once | ✓ FLOWING |
| Vector filtered search | `pre_count`, `filter_k`, KNN rows | Same typed store through `compile_filter` + `count_matching_documents`, post-KNN JOIN | Yes — integration real-vec0 corpus returns the 4 rare documents and the empty sentinel | ✓ FLOWING |
| Discovery `keys`/counts | `key_rows`, `type_rows`, `value_rows`, `medians` | `document_metadata_values` joined to the region CTE (never JSON1) | Yes — manual output showed 3 frontmatter keys, document counts, distinct values, exact `10.0/20.0/30.0` range | ✓ FLOWING |
| Discovery `builtIns` | `path`/`mtime` entries | `documents.path`, `documents.mtime` over the same region CTE | Yes — manual counts `4`, filter-narrowed `1`, `mtime` range present | ✓ FLOWING |
| MCP `metadata` envelope | `MetadataOutput` | `MetadataValueRepository.discover` over a real DB via `_run_in_db` | Yes — unit/MCP tests assert exact counts, remainders, and `builtIns` from seeded rows | ✓ FLOWING |

No static return, hardcoded literal, mock-only value, or hollow prop populates a goal-facing output. The two message constants (`_TOO_SELECTIVE_MSG`) are diagnostic text, not data.

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Phase unit batteries (AST, compiler, CLI, storage) | `pytest tests/unit/core/test_filters.py tests/unit/search/test_filters_sql.py tests/unit/cli/test_search_filter.py tests/unit/database/test_metadata_values.py -q --no-cov` | 325 passed | ✓ PASS |
| Integration + vector/hybrid/collection/MCP batteries | `pytest tests/integration/test_metadata_filtering.py tests/unit/search/test_vector.py tests/unit/search/test_hybrid.py tests/unit/cli/test_collection.py tests/unit/mcp/test_backend.py tests/unit/mcp/test_integration.py -q --no-cov` | 271 passed | ✓ PASS |
| Schema/backfill, incremental freshness, BM25 regression, docs | `pytest tests/unit/database/test_schema.py tests/unit/indexing/test_incremental.py tests/unit/search/test_bm25.py tests/unit/search/test_collection_filter.py tests/unit/cli/test_search.py tests/test_docs.py -q --no-cov` | 309 passed | ✓ PASS |
| Full suite with configured coverage gate | `env -u FORCE_COLOR NO_COLOR=1 pytest -q` | 2482 passed, 1 skipped; 95.35 % coverage (gate 90) | ✓ PASS |
| Lint / format / types | `ruff check src tests`; `ruff format --check src tests`; `ty check src/sif` | All checks passed; 208 files formatted; 0 diagnostics | ✓ PASS |
| Generator-owned docs diff | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | exit 0, no diff | ✓ PASS |
| CLI eq/in/empty/invalid/mtime/path filter matrix on a real index | `sif search search needle --filter ... --json` (six runs) | active-only, deduped `in`, `[]` empty, ClickException for `path lt`, 4 mtime hits, `nested.md` for path prefix | ✓ PASS |
| Typed semantics | `priority eq 10`, `priority eq "10"`, `priority ne 10`, `priority nin [10,20]`, `tags contains lph`, `status eq ACTIVE` | int matches, string matches nothing, missing keys excluded from `ne`/`nin`, substring-any works, ASCII fold works | ✓ PASS |
| Upgrade/backfill | Delete all typed rows + marker, then run a filtered search | one stderr warning, marker `1`, 11 rows rebuilt, correct filtered result | ✓ PASS |
| `qmd.metadata` precedence | Namespaced note with colliding native `status` | `status=namespaced` → 1 hit; `status=native-loses` → 0 | ✓ PASS |
| Discovery CLI envelope + built-ins + shadowing | `collection metadata --json / --filter / --match /` table mode | exact envelope; `filteredDocuments` only with filter; `builtIns` path/mtime; match narrows keys only; skip footer; built-ins table first | ✓ PASS |
| Index use | `EXPLAIN QUERY PLAN` for path prefix and mtime range on a populated DB | `idx_documents_path` and `idx_documents_mtime` SEARCH rows | ✓ PASS |
| Strict JSON under hostile numerics | Index a note with a 400-digit int, `.inf`, `.nan`; then `collection metadata --json` | index exit 0; huge int skipped `cap_number`; `inf`/`nan` stringified; strict JSON parse OK | ✓ PASS |
| Injection-shaped operand | `--filter '{"field":"status","operator":"eq","value":"active'; DROP TABLE documents; --%"}'` | `[]`, exit 0, documents table intact | ✓ PASS |
| Budgets through the CLI | 9-deep AST; 129-element `in` list | `filter exceeds the maximum nesting depth of 8`; `filter exceeds the maximum array operand length of 128` | ✓ PASS |

## Probe Execution

Not applicable — no probe script was declared in any PLAN/SUMMARY and `find scripts -path '*/tests/probe-*.sh'` returned nothing. The phase's executable evidence is the pytest batteries and the direct CLI/DB checks above.

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| FILT-01 | 20-01, 20-04 | Recursive JSON AST filter via shared CLI `--filter <json>` and MCP `filter`; typed exact match, no coercion, missing keys don't match `ne`/`nin`, budgets | ✓ SATISFIED | 17-operator AST + budgets (`core/filters.py`); `--filter` on all three CLI commands; `filter` on all three MCP inputs + query schema; invalid input is `ClickException`/`isError`; 50 AST tests + CLI/MCP batteries + manual runs. |
| FILT-02 | 20-01, 20-03, 20-04 | Built-in `path`/`mtime` (mtime indexed), strictly more expressive than qmd's frontmatter-only AST | ✓ SATISFIED | Reserved-field compiler matrix; `idx_documents_path`/`idx_documents_mtime` plan assertions; built-ins ride both legs (`TestComposition::test_built_in_mtime_and_path_filters_ride_the_vector_leg`); discovery reports both as `builtIns`. |
| FILT-03 | 20-01, 20-03 | Pre-RRF per leg: BM25 outer WHERE, vector post-KNN JOIN + adaptive over-fetch/selectivity bound/honest message; parameterized SQL only | ✓ SATISFIED | `bm25.py:106-160`; `vector.py:129-230`; corrected measured escalation bug; parameterized compiler + injection tests; integration containment/2 %/empty-sentinel battery. |
| FILT-04 | 20-01, 20-02 | Typed frontmatter storage + backfill; `qmd.metadata` namespace migration parity; numeric compare as numbers | ✓ SATISFIED | Two metadata tables with typed CHECKs + partial indexes; synchronous kv writes on both document write paths; resumable marker-gated backfill; namespace/shadowing/caps; manual upgrade simulation and numeric semantics. |
| FILT-05 | 20-05 | Discovery tool on CLI + MCP: doc counts, numeric min/median/max, exact remainders; one shared validator; invalid filter → ToolError, never protocol error | ✓ SATISFIED | `MetadataValueRepository.discover`; `sif collection metadata`; registered MCP `metadata` tool with frozen envelope; `TestDiscoveryParity` both directions; MCP invalid-filter tests through the real server. |

No ORPHANED requirements: all five FILT IDs are declared across the five plans, and `REQUIREMENTS.md` maps exactly those five to Phase 20 (traceability table marks each Complete).

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX` debt markers in any phase-modified source/test/doc file | None | Debt-marker gate clean. |
| — | — | No empty/stub returns or placeholder rendering in the filter, storage, search-leg, CLI, or MCP paths | None | `grep` hits for "placeholder" are SQL `?` placeholders and error-message text only. |

Process observation (not a codebase gap): `.planning/phases/20-metadata-filtering-discovery/20-VALIDATION.md` remains a draft with `TBD` task-map rows; it predates execution and was superseded by each PLAN's `<verify>` blocks and the executed batteries. It is a planning artifact, not a phase deliverable, and does not affect any must-have.

## Human Verification Required

None. All five roadmap success criteria are programmatically verifiable and were exercised directly or through behavioral tests. No visual, real-time, external-service, or subjective UX behavior is part of this phase's contract; MCP client-era interoperability is Phase 22 scope.

## Gaps Summary

None. All 26 must-have truths are VERIFIED, every required artifact exists and is substantive and wired, every key link is connected, data flows from the real typed store through both search legs and the discovery surfaces, and the phase's prohibitions hold. The five `Info` review findings remain open by disposition and are recorded above as known items, not gaps. Phase goal achieved.

---

_Verified: 2026-11-15T14:27:36Z_
_Verifier: Claude (gsd-verifier)_
