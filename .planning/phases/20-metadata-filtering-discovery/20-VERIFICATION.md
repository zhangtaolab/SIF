---
phase: 20-metadata-filtering-discovery
verified: 2026-11-18T07:08:37Z
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
  - src/sif/mcp/protocol.py
  - src/sif/mcp/tools.py
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
  - tests/unit/mcp/test_tools.py
  - tests/unit/search/test_filters_sql.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/search/test_vector.py
covered_digest: "v4:sha256:e897615046c6db59a994d4ed75468fc0f23c48bf097ccde4743143be58ce9b9c"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 26/26
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 20: Metadata Filtering + Discovery Verification Report

**Phase Goal:** Users and agents can scope searches precisely with metadata filters applied before fusion — qmd-unreleased AST parity plus built-in path/mtime fields, and a discovery tool so agents never guess keys.
**Verified:** 2026-11-18T07:08:37Z
**Status:** passed
**Re-verification:** Yes — against the current codebase after Phases 21-24; the previous report's `covered_digest` no longer matched the covered files.

## Re-verification Note

The prior report (2026-11-15, 26/26) was re-checked property-by-property against the current tree. Two implementation relocations were expected and verified as property-preserving, not regressions:

- The hand-written MCP `handlers.py` schemas were superseded in Phase 22 by the signature-derived tool schemas in `src/sif/mcp/tools.py` (`register_tools`); every search tool signature and the `metadata` tool still declare `filter`, and `_parse_filter_node` still maps `FilterValidationError` to `ToolError`.
- `tests/unit/mcp/test_integration.py` was replaced by `tests/unit/mcp/test_tools.py`; the invalid-filter-is-not-a-protocol-error property is now exercised through the real HTTP app there (`test_tools.py:950-962`), including metadata `filter`/`match` payloads.

No truth regressed. The two search-leg, storage, CLI, and discovery implementations are byte-for-byte the Phase 20 code paths (aside from later-phase docstring/adjacent changes), and all targeted batteries pass on the current tree.

## Goal Achievement

### Observable Truths

The first five rows are the ROADMAP §Phase 20 success criteria (the contract); the rest are plan-derived truths, deduplicated against the roadmap wording.

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1 | User can filter any CLI search with `--filter <json>` and any MCP query with `filter` — recursive and/or/not + comparison/in/contains/type/exists with qmd semantics verbatim (typed exact match, no coercion, missing keys don't match `ne`/`nin`, budgets enforced) | ✓ VERIFIED | `src/sif/core/filters.py` defines all 17 operators (14 conditions: `eq/ne/gt/gte/lt/lte/in/nin/all/contains/prefix/suffix/type/exists`, 3 groups: `and/or/not`), `FilterValidationError`, and the iterative budgets `MAX_FILTER_DEPTH=8`, `MAX_FILTER_NODES=64`, `MAX_FILTER_STRING=1024`, `MAX_FILTER_ARRAY=128`, `MAX_FILTER_FIELD_BYTES=128`. CLI adapter `src/sif/cli/filter_options.py` delegates to `parse_filter`/`parse_match`; MCP `tools.py:110-121` calls the same `parse_filter`. `tests/unit/core/test_filters.py` passes in the 956-test battery. |
| 2 | User can filter by built-in `path` and `mtime` fields (mtime indexed) — strictly more expressive than qmd's frontmatter-only AST | ✓ VERIFIED | `src/sif/search/filters.py:495` `_path_prefix_sql`; `RESERVED_FIELDS = frozenset({"path","mtime"})` in `metadata_repository.py:39`; `idx_documents_path` and `idx_documents_mtime` created in `schema.py:759/769`; `_built_in_entries` reports both from `documents` columns. Compiler tests (incl. plan assertions) pass. |
| 3 | Filters apply pre-RRF per leg — BM25 outer WHERE of the materialized CTE (never inside it), vector post-KNN JOIN with adaptive over-fetch, a selectivity bound, and an honest "too selective" message; parameterized SQL only (no injection surface, no post-fusion filtering) | ✓ VERIFIED | `bm25.py:106-160`: `compile_filter(..., scope="candidates")` suffix appended in both branches' outer WHERE after `min_score_filter`. `vector.py:154/188-243`: post-KNN JOIN predicate, `pre_count`, `_MAX_FETCH_K=2048` seeding, distinct-document stop, `logger.warning(_TOO_SELECTIVE_MSG, ...)`. `tests/unit/search/test_filters_sql.py::test_injection_values_keep_sql_shape` and the DB-mutation test pass; integration battery passes. |
| 4 | User's existing indexes filter correctly after upgrade — typed frontmatter storage + backfill runs, `qmd.metadata`-namespaced keys filter identically to native keys; numeric values compare as numbers, not strings | ✓ VERIFIED | `SchemaManager._backfill_metadata_values` (`schema.py:317-357`): pure-Python read of stored canonical `documents.metadata`, one transaction per document, marker written last, exceptions propagate. `filterable_metadata` merges `qmd.metadata` over native keys and pops `RESERVED_FIELDS`. `TestMetadataBackfill` (fresh/populated/reopen/interrupted) and typed-value tests pass. |
| 5 | Agent can discover available metadata via a `metadata` tool on CLI + MCP — doc counts, numeric min/median/max, exact remainders; ONE validator shared with the filter surface; invalid filter → ToolError, never a protocol error | ✓ VERIFIED | `sif collection metadata` (`collection.py:441-533`, options `--filter/--match/--key/--min-count/--limit/--value-limit/--json`); MCP tool registered in `tools.py:253-298` and `register_tools` order `query,get,multi_get,status,metadata,lex_search,vec_search`. `_parse_filter_node` maps to `ToolError`; real-HTTP test asserts `body["result"]["isError"] is True` with no `error`. `MetadataValueRepository.discover` supplies exact windows. |
| 6 | Equality is typed and exact: a boolean never matches a numeric operand, `"10"` never matches numeric `10`, and `10` matches `10.0` (both stored as number) | ✓ VERIFIED | `_value_type_of` checks bool before number (`filters.py:108`); `TestTypedExactMatch` in `tests/integration/test_metadata_filtering.py:398` passes. |
| 7 | Equality and ordering are byte/code-point exact on the stored value; `caseInsensitive` folds ASCII only and performs no Unicode normalization | ✓ VERIFIED | `_ascii_lower` explicit A-Z translate table (`filters.py:75`); non-ASCII pair test still present and passing in the AST/compiler batteries. |
| 8 | A filter that admits every document reproduces the unfiltered BM25 page exactly; a filter that matches nothing returns an empty page and never degrades to the unfiltered result set | ✓ VERIFIED | `TestAdmitAllEquivalence` (byte-for-byte ids/ranks/scores) and `TestEmptyMatchSentinel` in `tests/integration/test_metadata_filtering.py:288/380` pass. |
| 9 | The unfiltered BM25 path issues exactly the same statements it issued before this plan (no pre-count, no new query) and emits no new output | ✓ VERIFIED | Module-level goldens `_HEAD_UNFILTERED_SQL/_PARAMS`, `_HEAD_SCOPED_SQL/_PARAMS`; `test_unfiltered_statement_byte_identical`, `test_scoped_statement_byte_identical` pass (`test_filters_sql.py:41-278`). |
| 10 | `path` prefix compiles to a half-open range that EXPLAIN QUERY PLAN resolves through `idx_documents_path`; `mtime` ranges resolve through `idx_documents_mtime` | ✓ VERIFIED | Half-open `prefix`/`prefix + "\U0010ffff"` binding in `_path_prefix_sql`; `TestQueryPlans` index-name assertions pass; both indexes exist in `schema.py`. |
| 11 | `qmd.metadata`-namespaced keys filter identically to native keys, and the namespace wins on collision; a document without the namespace is unaffected | ✓ VERIFIED | `filterable_metadata` (`metadata_repository.py:147-170`) merges the namespace over native keys and drops native collisions; `TestDerivation` namespace tests pass. |
| 12 | A frontmatter key named `path` or `mtime` is shadowed and never appears as a frontmatter key; it is reserved, not a skipped key | ✓ VERIFIED | `RESERVED_FIELDS` popped before classification (`metadata_repository.py:164-165`); `test_reserved_names_are_shadowed_not_skipped` passes; discovery `keys` and `builtIns` remain disjoint. |
| 13 | The backfill is idempotent and resumable: re-running after a complete pass is a no-op; an interrupted pass leaves committed batches intact, writes the marker only after a complete pass, and never serves filtering from a half-populated store | ✓ VERIFIED | Marker gate first, per-document `with self.db:`, marker last, no exception swallowing (`schema.py:341-357`). `TestMetadataBackfill` interruption/resume and zero-duplicate assertions pass (behavioral test exercises the transition). |
| 14 | A ~2 % selectivity filter returns its matching documents (never an empty page) through the vector leg, and a short page is honest rather than padded | ✓ VERIFIED | `TestSelectiveRecall::test_two_percent_filter_returns_rare_documents_on_all_paths` (200 docs, 4 rare; BM25/vector/pipeline) passes; short-page test asserts no warning. |
| 15 | The too-selective warning fires only when the filter's matching count is at least the page target AND the fetch ceiling was exhausted with a short page; never for a genuinely short page or a collection-only search | ✓ VERIFIED | Guard at `vector.py:236-243`; `test_too_selective_notice_fires_once_with_formatted_counts`, `test_short_page_below_page_target_logs_no_notice`, `test_all_matches_found_logs_no_notice` pass. |
| 16 | An empty filter match set returns an empty page on both legs (never the unfiltered set), and a filter admitting every document reproduces the unfiltered page | ✓ VERIFIED | `pre_count == 0` returns `[]` before KNN (`vector.py:199-200`); BM25 outer WHERE yields zero rows; `TestEmptyMatchSentinel` passes. |
| 17 | Both legs receive the same AST before fusion: `filtered-hybrid ⊆ unfiltered-hybrid ∩ filter-set` over a generated corpus | ✓ VERIFIED | `replace(options, ...)` carries `filter` (`hybrid.py:121`, early returns at 418/424); test asserts `bm25_options.filter is node` and `vector_options.filter is node` (`test_hybrid.py:1685-1686`); `TestContainmentInvariant` passes. |
| 18 | An unfiltered, unscoped vector search issues exactly the statements and fetch window it issued before this plan (no pre-count, no warning) | ✓ VERIFIED | `has_join_filter = is_metadata_filtered or bool(collection_ids)`; `test_unfiltered_unscoped_path_issues_only_the_pre_change_statement` (`test_vector.py:634`) passes using `_RecordingConnection`. |
| 19 | Per-chunk mode counts distinct documents for the all-matches test, so duplicate chunks cannot end escalation early | ✓ VERIFIED | Distinct `document_id` set in the found count; `test_per_chunk_mode_sees_every_matching_document` (`test_vector.py:559`, fifth match beyond rank 50) passes. |
| 20 | `--filter <json>` exists on all three CLI result commands with the same grammar/semantics; `get`/`multi-get`/`ls` are untouched; an invalid filter fails as user input before the pre-search refresh with an actionable ClickException | ✓ VERIFIED | Decorators at `search.py:522/723/954`; `filter_node` parsed at 567/770/1057 before `open_initialized_database` at 577/804/1067 and `_pre_search_refresh` at 596/851/1114. `TestFilterOptionMatrix` (invalid JSON/AST, spies never called) passes; `grep '"--filter"' src/sif/cli/commands/` shows only the three search commands plus `collection metadata`. |
| 21 | All three MCP search inputs carry `filter`, and the published tool input schema declares it so MCP tool discovery can see it; an invalid MCP filter returns a tool execution error (`isError=True`) inside a successful JSON-RPC response, never `INVALID_PARAMS` | ✓ VERIFIED (property superseded implementation) | `protocol.py:93/135/162` carry `filter`; `tools.py` query/lex/vec signatures (138/319/359) declare `filter`, and `register_tools` states every signature IS the published input schema (Phase 22 supersession of the hand-written `handlers.py` schema). `test_invalid_filter_is_a_tool_error` (query/lex/vec) and `test_invalid_filter_or_match_is_tool_error` (metadata, incl. `10**400`) pass; the real-HTTP dispatch asserts `"error" not in body` and `body["result"]["isError"] is True`. |
| 22 | Filter composes by AND with `--collection`/`collections`, `--min-score`, `--offset`, `--per-chunk`, and reranking, and both legs receive the same AST; an unfiltered CLI/MCP search keeps `SearchOptions.filter is None` and emits nothing new | ✓ VERIFIED | `filter=filter_node` at `search.py:585/812/1102` and `backend.py:467/603/668`; composition/`filter is None` batteries in `test_search_filter.py`/`test_backend.py` pass. |
| 23 | Discovery reports exact totals: key window + `remainingKeys` == `totalKeys`, and each type's value window + `remainingValues` == its distinct-value count; min/median/max come from typed numeric rows and mixed-type keys split per type | ✓ VERIFIED | `discover` window arithmetic (`metadata_repository.py:531`); `_medians` uses `ROW_NUMBER()/COUNT(*) OVER`; `TestDiscovery` (14 tests) passes. |
| 24 | Discovery never lies: every reported key (frontmatter or built-in) is filterable, every filterable key appears, and a non-indexable key is counted in `skippedKeys` rather than silently dropped or presented as filterable | ✓ VERIFIED | `TestDiscoveryParity` both directions (and nested-key case) passes; `skippedKeys` from `document_metadata_skips` is the only skip surface. |
| 25 | `path` and `mtime` are reported as built-in fields, never frontmatter keys — only in `builtIns` with scope- and filter-aware counts and an `mtime` numeric range, even when a document's frontmatter carries a same-named key | ✓ VERIFIED | `_built_in_entries` (`metadata_repository.py:596-637`) queries `documents.path/mtime` over the region CTE; reserved names are popped from frontmatter keys; `TestCollectionMetadata` and MCP tests assert the same. |
| 26 | When a filter is supplied, all counts are measured against the admitted set and `filteredDocuments` is present; without a filter it is absent. Default ordering is document count desc then key asc; key window 50, value window 10 | ✓ VERIFIED | `result["filteredDocuments"]` only when `filter_predicate is not None` (`metadata_repository.py:509`); `documents DESC, key ASC` ordering and the 50/10 defaults match the generated docs; filtered/unfiltered MCP tests pass. |

**Score:** 26/26 truths verified (0 present, behavior-unverified)

### Prohibitions (must-NOT checks)

All plan `must_haves.prohibitions` were re-checked against current code and executable evidence.

| Plan | Prohibition | Status | Evidence |
| ---- | ----------- | ------ | -------- |
| 20-01 | A filter must never silently widen: missing keys must not satisfy `ne`/`nin`; a non-None filter never compiles to an empty predicate | ✓ VERIFIED | Presence-EXISTS + `NOT EXISTS` compilation (`_presence_inner`, `filters.py:246-359`); `test_ne_is_presence_and_negation`, `test_nin_is_presence_and_negation`, `test_non_none_never_returns_empty` pass. |
| 20-01 | Ordering operators must never compare strings lexicographically | ✓ VERIFIED | Validator requires finite numeric (except `mtime` ISO normalization, `filters.py:599-620`); compiler rejects text/array on ordering; matrix tests pass. |
| 20-01 | `caseInsensitive` must never perform Unicode case folding or normalization | ✓ VERIFIED | `_ascii_lower` translate table; non-ASCII Ä/ä test passes. |
| 20-01 | Filters must never be applied after fusion | ✓ VERIFIED | Predicate in BM25 outer WHERE and vector post-KNN JOIN; both legs receive the AST; identity + containment tests pass. |
| 20-01 | The unfiltered search path must stay byte-identical | ✓ VERIFIED | Pre-change goldens; three byte-identical tests pass. |
| 20-02 | The backfill must never leave filtering enabled against a half-populated store | ✓ VERIFIED | Marker written only after the loop; failure propagates out of `create_all`; interruption test passes. (Read-side defence-in-depth remains open Info IN-05, unchanged.) |
| 20-02 | Typed rows must never be derived from the in-memory metadata dict | ✓ VERIFIED | `typed_rows(canonical_json)` is the only derivation entry; both repository write sites pass the same canonical string (`repositories.py:192/274`). |
| 20-02 | Discovery and filtering must never read metadata with SQLite JSON1 functions | ✓ VERIFIED | Grep for `json_each`/`json_extract` over the phase source paths returns no hits; Python `json.loads` is the only reader. |
| 20-02 | The migration announcement must never be written to stdout | ✓ VERIFIED | `logger.warning` in `_backfill_metadata_values`; `TestMetadataBackfill` asserts clean stdout. |
| 20-03 | Filtering must never happen after fusion | ✓ VERIFIED | Same as 20-01 row; passthrough and pipeline variant tests pass. |
| 20-03 | The too-selective notice must never be written to stdout, the result list, or JSON output | ✓ VERIFIED | `logger.warning` only; `TestNoticeStaysOffStdout` passes. |
| 20-03 | The warning must never fire when the filter genuinely matches fewer documents than requested | ✓ VERIFIED | Guard requires `pre_count >= page_target`; both suppressed branches tested. |
| 20-03 | An empty filter match must never degrade to the unfiltered search | ✓ VERIFIED | `pre_count == 0` returns `[]` before KNN; `TestEmptyMatchSentinel` passes. |
| 20-04 | Filter validation must never surface as a JSON-RPC protocol error | ✓ VERIFIED | `_parse_filter_node` → `ToolError`; real-HTTP test asserts a success envelope with `isError` and no `error` key (`test_tools.py:950-962`). |
| 20-04 | The MCP boundary must never drop a caller-supplied filter | ✓ VERIFIED | `filter_node` threaded to `SearchOptions.filter` in `backend.py`; identity/equality tests pass. |
| 20-04 | Generated documentation must never be hand-edited | ✓ VERIFIED | `docs/cli-reference.md` is generated; `--filter` appears in the `search query`/`search search`/`search vsearch`/`collection metadata` sections; later commits (e.g. `f49458b`, `5f2a523`) are generator regenerations, and the generator diff gate passed in the prior verification with no hand edits since that touch these sections. |
| 20-04 | Diagnostics must never be written to CLI JSON output | ✓ VERIFIED | `test_filtered_json_output_is_clean_json` (strict parse, no notice text) passes. |
| 20-05 | Discovery must never read the metadata blob with SQLite JSON1 functions or any second source of truth | ✓ VERIFIED | Same JSON1 grep is clean; discovery joins `document_metadata_values` + `documents` only. |
| 20-05 | Skipped keys must never be presented as filterable keys | ✓ VERIFIED | `keys` come from the typed store; skips only contribute `skippedKeys`; nested-key parity test passes. |
| 20-05 | Reserved built-ins must never be reported as frontmatter keys | ✓ VERIFIED | `RESERVED_FIELDS` dropped in `filterable_metadata`; `builtIns` computed from columns; reserved-shadowing test passes. |
| 20-05 | Discovery must never be unbounded: no `--all` mode, no unbounded value materialization | ✓ VERIFIED | Fixed key/value windows with exact remainders; `--all` does not exist. (Caller-supplied upper bounds remain open Info IN-03, unchanged.) |
| 20-05 | Metadata and notice text must never be written to stdout outside the requested output mode | ✓ VERIFIED | `--json` prints only the strict envelope; table mode prints table + footers; CLI discovery tests pass. |

### Deferred Items

None. All five roadmap success criteria are achieved; no identified item needs a later milestone phase.

### Known Open Items (Code Review — Info, disposition `open`)

Unchanged non-gaps from `20-REVIEW-DISPOSITION.md`: IN-01 dead constants (hygiene), IN-02 `_collection_predicate([])` sentinel latent, IN-03 unbounded caller windows (DoS hardening), IN-04 compact JSON formatting, IN-05 no read-side half-populated check (defence-in-depth). None blocks a must-have truth or the phase goal.

## Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/sif/core/filters.py` | AST models, `parse_filter`, `parse_match`, `FilterValidationError`, budgets | ✓ VERIFIED | 714 lines; 14 conditions + 3 groups, 5 budget constants, raw-payload validation, mtime ISO normalization, reserved-field parse-time matrix. |
| `src/sif/search/filters.py` | `compile_filter`, `compile_match`, scope counters | ✓ VERIFIED | 814 lines; parameterized fragments for both scopes, presence-aware `ne`/`nin`, `LIMIT 1` candidate probe, half-open `path` prefix, built-in matrix, three count helpers. |
| `src/sif/database/metadata_repository.py` | `filterable_metadata`, `typed_rows`, `TypedRow`, `SkippedKey`, `MetadataValueRepository` | ✓ VERIFIED | 648 lines; namespace merge + reserved shadowing, caps/skip reasons, `replace_from_canonical`/`delete_by_document`/`discover` with exact window arithmetic. |
| `src/sif/database/schema.py` | Metadata DDL, partial indexes, backfill, marker | ✓ VERIFIED | `_create_metadata_tables`, both tables in `drop_all`, `_backfill_metadata_values` with `metadata_values_version` marker; `idx_documents_path`/`idx_documents_mtime`. |
| `src/sif/database/repositories.py` | One canonical string → row + kv rebuild | ✓ VERIFIED | Both `create` (192/217) and `update` (274/293) compute the canonical string once and pass it to `replace_from_canonical`. |
| `src/sif/core/models.py` | `SearchOptions.filter` | ✓ VERIFIED | `filter: FilterNode \| None = None` with the None-is-unfiltered contract comments (348-364). |
| `src/sif/search/bm25.py` | Filter suffix in both outer WHERE slots | ✓ VERIFIED | `compile_filter(..., scope="candidates")` at 106; suffix appended in both branches (138/160); `search_chunks` stays filter-free. |
| `src/sif/search/vector.py` | Filtered pre-count, seeding, corrected escalation, notice | ✓ VERIFIED | `_TOO_SELECTIVE_MSG`, `_MAX_FETCH_K`, `_filtered_fetch_window`, empty-match short circuit, distinct-document target, guard-gated warning. |
| `src/sif/search/hybrid.py` | Contract docstrings (no behavior change) | ✓ VERIFIED | `fetch_options = replace(...)` carries `filter`; docstrings document pre-RRF, early-return windows, per-chunk `chunk_matches`. |
| `src/sif/cli/commands/search.py` | `--filter` on all three commands + shared adapter | ✓ VERIFIED | Decorators at 522/723/954; parse before DB open at 567/770/1057; `_parse_filter_option` delegates to `sif.cli.filter_options`. |
| `src/sif/cli/filter_options.py` | One CLI JSON/AST adapter | ✓ VERIFIED | `parse_filter_option`/`parse_match_option` map JSON and grammar failures to `ClickException`. |
| `src/sif/cli/commands/collection.py` | `collection metadata` with 7 options, table/JSON | ✓ VERIFIED | Built-ins render first with `Source=built-in`; exact remainder/skip footers; JSON prints only the envelope; validation before DB open. |
| `src/sif/mcp/protocol.py` | `filter` on 3 inputs; frozen discovery models | ✓ VERIFIED | 3 `filter` fields (93/135/162); `MetadataInput` (7 inputs), `MetadataOutput` (camelCase incl. `builtIns`), range/value/type/key summaries. |
| `src/sif/mcp/tools.py` (supersedes `handlers.py`) | Query filter path + metadata tool + registry | ✓ VERIFIED | `filter` parameters on query/lex/vec/metadata signatures; `_parse_filter_node` → `ToolError`; `register_tools` registers `metadata` as the fifth tool; signature-derived schema replaces the Phase 20 hand-written `input_schema`. |
| `src/sif/mcp/backend.py` | `hybrid_search(filter_node=...)`, `metadata(...)` | ✓ VERIFIED | `filter=filter_node` in every options build (467/603/668); `metadata` compiles only supplied predicates and returns the raw envelope via `_run_in_db`. |
| `src/sif/utils/json_output.py` | Strict machine JSON | ✓ VERIFIED | `json_dumps_strict` stringifies non-finite floats and serializes with `allow_nan=False`. |
| `docs/cli-reference.md` | Regenerated flag/command docs | ✓ VERIFIED | `--filter` documented in the four relevant sections; generator-owned file, later commits are regenerations. |
| Phase test batteries | AST, compiler, storage, vector, hybrid, CLI, MCP, integration | ✓ VERIFIED | One combined targeted run: 956 passed in 7.13 s; docs tests 20 passed. |

## Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `src/sif/search/bm25.py` | `src/sif/search/filters.py` | `compile_filter(options.filter, alias="d", scope="candidates")` | ✓ WIRED | `bm25.py:106`; params appended between min-score and limit/offset. |
| `src/sif/database/repositories.py` | `src/sif/database/metadata_repository.py` | `MetadataValueRepository.replace_from_canonical(document.id, metadata_json)` | ✓ WIRED | Both create and update write sites. |
| `src/sif/cli/commands/search.py` | `src/sif/core/filters.py` | `_parse_filter_option` → `parse_filter_option` → `parse_filter` | ✓ WIRED | Adapter delegates; both error classes map to `ClickException`. |
| `src/sif/search/filters.py` | `src/sif/database/schema.py` | `document_metadata_values(key, typed columns, document_id, ordinal)` | ✓ WIRED | `_KV_TABLE` and column names match the DDL exactly. |
| `src/sif/database/schema.py` | `src/sif/database/repositories.py` | `IndexMetaRepository.get/set("metadata_values_version")` | ✓ WIRED | Lazy imports inside `_backfill_metadata_values` (no cycle). |
| `src/sif/database/schema.py` | `src/sif/database/metadata_repository.py` | `replace_from_canonical` per document, one short transaction each | ✓ WIRED | Verified by the interruption test. |
| `src/sif/database/metadata_repository.py` | `src/sif/core/models.py` | canonical JSON as the single derivation source | ✓ WIRED | Derivation takes the canonical string; the repository computes it once per write. |
| `src/sif/search/vector.py` | `src/sif/search/filters.py` | `compile_filter(...)` + `count_matching_documents`/`count_documents_in_scope`/`count_vectors_in_scope` | ✓ WIRED | Imports at `vector.py:11-15`; used in `_search_with_vec` and `_filtered_fetch_window`. |
| `src/sif/search/hybrid.py` | `src/sif/search/bm25.py` | `replace(options, limit=limit+offset, offset=0)` carries `options.filter` to both legs | ✓ WIRED | `hybrid.py:121`; identity-asserted in tests (1685-1686). |
| `src/sif/cli/commands/collection.py` | `src/sif/database/metadata_repository.py` | `discover(filter_predicate=compile_filter(...), match_predicate=compile_match(...))` | ✓ WIRED | Compiled fragments passed only when supplied; `None` otherwise. |
| `src/sif/database/metadata_repository.py` | `src/sif/database/schema.py` | `documents.path`/`documents.mtime` aggregates for `builtIns` | ✓ WIRED | `_built_in_entries` and `_mtime_median` query the region CTE. |
| `src/sif/mcp/tools.py` | `src/sif/mcp/backend.py` | `SearchBackend.metadata(...)` → `_run_in_db(callback)` | ✓ WIRED | Handler builds `MetadataInput`, parses filter/match, calls the backend. |
| `src/sif/mcp/protocol.py` | `src/sif/database/metadata_repository.py` | `MetadataOutput(**discovery_dict)` | ✓ WIRED | Handler constructs the model from the raw discover dict; `model_dump(exclude_none=True)` preserves omit semantics. |
| `src/sif/cli/commands/search.py` | `SearchOptions.filter` | `filter=filter_node` in all three commands | ✓ WIRED | Lines 585/812/1102. |
| `src/sif/mcp/backend.py` | `SearchOptions.filter` | `filter=filter_node` in `_search` variants | ✓ WIRED | Lines 467/603/668; BM25-only fallback uses the same options. |
| `src/sif/mcp/tools.py` | `src/sif/core/filters.py` | `parse_filter`/`parse_match` → `ToolError` | ✓ WIRED | `_parse_filter_node` / metadata handler try/except; never reaches protocol error. |

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| BM25 filtered search | `filter_clause` / result rows | Frontmatter → `canonical_metadata_json` → `document_metadata_values` → compiler `EXISTS` probe → FTS outer WHERE | Yes — integration corpus returns exactly the admitted documents; containment/admit-all tests pass | ✓ FLOWING |
| Vector filtered search | `pre_count`, `fetch_k`, KNN rows | Same typed store through `compile_filter` + `count_matching_documents`, post-KNN JOIN | Yes — real-vec0 corpus returns the 4 rare documents and the empty sentinel | ✓ FLOWING |
| Discovery `keys`/counts | `key_rows`, `type_rows`, `value_rows`, `medians` | `document_metadata_values` joined to the region CTE (never JSON1) | Yes — discovery tests assert counts, distinct values, exact `min/median/max` | ✓ FLOWING |
| Discovery `builtIns` | `path`/`mtime` entries | `documents.path`, `documents.mtime` over the same region CTE | Yes — counts and the `mtime` range asserted in CLI/MCP tests | ✓ FLOWING |
| MCP `metadata` envelope | `MetadataOutput` | `MetadataValueRepository.discover` over a real DB via `_run_in_db` | Yes — MCP tests assert exact counts, remainders, and `builtIns` from seeded rows | ✓ FLOWING |

No static return, hardcoded literal, mock-only value, or hollow prop populates a goal-facing output. The two message constants are diagnostic text, not data.

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Phase batteries: AST, compiler, storage, backfill, vector, hybrid, CLI, collection, MCP tools/backend, BM25, integration | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/core/test_filters.py tests/unit/search/test_filters_sql.py tests/unit/cli/test_search_filter.py tests/unit/database/test_metadata_values.py tests/integration/test_metadata_filtering.py tests/unit/search/test_vector.py tests/unit/search/test_hybrid.py tests/unit/cli/test_collection.py tests/unit/mcp/test_backend.py tests/unit/mcp/test_tools.py tests/unit/database/test_schema.py tests/unit/indexing/test_incremental.py tests/unit/search/test_bm25.py tests/unit/cli/test_search.py -q --no-cov` | 956 passed in 7.13 s | ✓ PASS |
| Docs code-block suite | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/test_docs.py -q --no-cov` | 20 passed in 0.98 s | ✓ PASS |
| Debt-marker gate | `grep -n -E "TBD\|FIXME\|XXX"` over all phase source files | No matches | ✓ PASS |
| JSON1 prohibition | `grep -n -E "json_each\|json_extract"` over filter/storage/search modules | No matches | ✓ PASS |

## Probe Execution

Not applicable — no probe script was declared in any PLAN/SUMMARY and `find scripts -path '*/tests/probe-*.sh'` returns nothing. The phase's executable evidence is the pytest batteries above.

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| FILT-01 | 20-01, 20-04 | Recursive JSON AST filter via shared CLI `--filter <json>` and MCP `filter`; typed exact match, no coercion, missing keys don't match `ne`/`nin`, budgets | ✓ SATISFIED | 17-operator AST + budgets (`core/filters.py`); `--filter` on all three CLI commands; `filter` on all three MCP tool signatures; invalid input is `ClickException`/`ToolError`; AST + CLI/MCP batteries pass. |
| FILT-02 | 20-01, 20-03, 20-04 | Built-in `path`/`mtime` (mtime indexed), strictly more expressive than qmd's frontmatter-only AST | ✓ SATISFIED | Reserved-field compiler matrix; `idx_documents_path`/`idx_documents_mtime`; built-ins ride both legs; discovery reports both as `builtIns`. |
| FILT-03 | 20-01, 20-03 | Pre-RRF per leg: BM25 outer WHERE, vector post-KNN JOIN + adaptive over-fetch/selectivity bound/honest message; parameterized SQL only | ✓ SATISFIED | `bm25.py:106-160`; `vector.py:154/188-293`; parameterized compiler + injection tests; containment/2 %/empty-sentinel integration battery passes. |
| FILT-04 | 20-01, 20-02 | Typed frontmatter storage + backfill; `qmd.metadata` namespace migration parity; numeric compare as numbers | ✓ SATISFIED | Two metadata tables with typed CHECKs + partial indexes; synchronous kv writes on both document write paths; resumable marker-gated backfill; namespace/shadowing/caps tests pass. |
| FILT-05 | 20-05 | Discovery tool on CLI + MCP: doc counts, numeric min/median/max, exact remainders; one shared validator; invalid filter → ToolError, never protocol error | ✓ SATISFIED | `MetadataValueRepository.discover`; `sif collection metadata`; registered MCP `metadata` tool with frozen envelope; `TestDiscoveryParity` both directions; real-HTTP invalid-filter test. |

No ORPHANED requirements: all five FILT IDs are declared across the five plans, and `REQUIREMENTS.md` maps exactly those five to Phase 20 (traceability table marks each Complete).

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX` debt markers in any phase-modified source/test/doc file | None | Debt-marker gate clean. |
| — | — | No empty/stub returns or placeholder rendering in the filter, storage, search-leg, CLI, or MCP paths | None | Grep hits for "placeholder" are SQL `?` placeholders and error-message text only. |

Process observation (unchanged): `20-VALIDATION.md` remains a draft with `TBD` task-map rows; it is a planning artifact, not a phase deliverable, and does not affect any must-have.

## Human Verification Required

None. All five roadmap success criteria are programmatically verifiable and were exercised through behavioral tests on the current tree. No visual, real-time, external-service, or subjective UX behavior is part of this phase's contract.

## Gaps Summary

None. All 26 must-have truths are VERIFIED against the current codebase, every required artifact exists and is substantive and wired, every key link is connected, data flows from the real typed store through both search legs and the discovery surfaces, and the phase's prohibitions hold. The two Phase 20 implementation relocations (MCP `handlers.py` → signature-derived `tools.py`; `test_integration.py` → `test_tools.py`) preserve the verified properties. The five `Info` review findings remain open by disposition and are known items, not gaps. Phase goal achieved.

---

_Verified: 2026-11-18T07:08:37Z_
_Verifier: Claude (gsd-verifier)_
