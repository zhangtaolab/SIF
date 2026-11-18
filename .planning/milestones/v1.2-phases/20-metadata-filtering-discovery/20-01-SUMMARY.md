---
phase: 20-metadata-filtering-discovery
plan: "01"
subsystem: search
tags: [sqlite, fts5, pydantic, metadata-filter, sql-compiler, typed-kv, cli]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "canonical_metadata_json as the single metadata serializer; SearchOptions pagination/offset; idx_documents_mtime"
provides:
  - "FilterNode AST + parse_filter/parse_match with qmd's 17 operators, budgets, and ASCII-only caseInsensitive"
  - "compile_filter/compile_match parameterized SQL compilers (candidates/corpus scopes) + scope count helpers"
  - "document_metadata_values + document_metadata_skips tables and MetadataValueRepository"
  - "typed kv sync inside DocumentRepository.create/.update"
  - "SearchOptions.filter, the BM25 outer-WHERE filter slot, and sif search --filter"
affects: [20-02, 20-03, 20-04, 20-05, 22]

# Actuals (#2632) — chars/4 over the realized diff, same scale as the plan estimate.
actuals:
  tokens: 37181
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Pydantic discriminated union on `operator` + iterative raw-dict budget pre-walk"
    - "Parameterized SQL fragment compilers returning (sql, params) in placeholder order"
    - "Typed kv rows derived from canonical JSON (never the in-memory dict)"
    - "Presence-aware ne/nin (EXISTS + NOT EXISTS); never a bare NOT IN"

key-files:
  created:
    - src/sif/core/filters.py
    - src/sif/search/filters.py
    - src/sif/database/metadata_repository.py
    - tests/unit/core/test_filters.py
    - tests/unit/search/test_filters_sql.py
    - tests/unit/cli/test_search_filter.py
  modified:
    - src/sif/database/schema.py
    - src/sif/database/repositories.py
    - src/sif/core/models.py
    - src/sif/search/bm25.py
    - src/sif/cli/commands/search.py
    - tests/unit/database/test_repositories.py
    - docs/cli-reference.md

key-decisions:
  - "Parity pin: qmd [Unreleased] verified 2026-11-15 (qmd@86d2365); conditions carry `field` (D-18) — the docs commit abfabc5 used `key` and is superseded; record the delta, do not mix eras."
  - "Semantic validation runs against the RAW payload, not the coerced model, so [true, 1] is rejected as mixed before pydantic's lax bool->int coercion hides it."
  - "`all` requires a non-empty homogeneous list (qmd's membership-array rule) even though the plan text said only non-empty; the compiler pins each element's own type."
  - "mtime ISO text normalizes for every value-comparing operator (eq/ne/ordering/in/nin); `type` and `exists` operands are never rewritten (D-12)."
  - "`path` `type` with caseInsensitive is a defined FilterValidationError; `path` `exists` is constant-true/false because the column is NOT NULL."
  - "filterable_metadata currently only shadows path/mtime; the qmd.metadata namespace merge and caps/skip accounting remain 20-02's contract."
  - "Unfiltered BM25 stays byte-identical: the filter suffix is empty for None and params are appended only when a predicate exists."

patterns-established:
  - "Budget walk: iterative raw-dict depth/node/string/array checks before pydantic recursion"
  - "Compiler error path is `filter.<field>.<operator>: ...` for built-in/type rejections"
  - "Recording-connection golden test captures the pre-change statement before editing the searcher"

requirements-completed: [FILT-01, FILT-02, FILT-03, FILT-04]

coverage:
  - id: D1
    description: "One typed frontmatter eq filter travels AST -> canonical-JSON kv rows -> parameterized SQL -> BM25 outer WHERE -> sif search --filter on a real index."
    requirement: FILT-03
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search_filter.py#TestFilterEndToEnd::test_eq_filter_returns_only_matching_documents"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search_filter.py#TestFilterEndToEnd::test_typed_rows_written_for_both_documents"
        status: pass
    human_judgment: false
  - id: D2
    description: "The full qmd-parity AST: 17 operators, ASCII-only caseInsensitive, four budgets, ISO/epoch mtime input, restricted match grammar."
    requirement: FILT-01
    verification:
      - kind: unit
        ref: "tests/unit/core/test_filters.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "The full per-operator SQL compiler for both scopes, both built-in fields, and the discovery match grammar, with injection and plan assertions."
    requirement: FILT-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_filters_sql.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Typed kv storage written in the same transaction as the document row, derived from the canonical JSON string."
    requirement: FILT-04
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search_filter.py#TestFilterEndToEnd::test_typed_rows_written_for_both_documents"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_repositories.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "The unfiltered BM25 path issues exactly the pre-change statement and params (byte-identical default)."
    requirement: FILT-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_filters_sql.py#test_unfiltered_statement_byte_identical"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_filters_sql.py#test_scoped_statement_byte_identical"
        status: pass
    human_judgment: false
  - id: D6
    description: "Invalid --filter JSON/AST is a user error naming the filter, never a traceback."
    requirement: FILT-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search_filter.py#TestFilterEndToEnd::test_invalid_filter_is_a_user_error"
        status: pass
    human_judgment: false

duration: 18min
completed: 2026-11-15
status: complete
---

# Phase 20 Plan 01: Typed metadata filter vertical slice and full qmd-parity compiler

**One typed frontmatter filter proved end to end through a new typed kv store, a parameterized SQL compiler, the BM25 outer WHERE, and `sif search --filter`; then expanded to all 17 qmd operators, both reserved built-ins, and the discovery match grammar with the unfiltered path pinned byte-for-byte.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-11-15T11:59:25Z
- **Completed:** 2026-11-15T12:17:43Z
- **Tasks:** 3
- **Files modified:** 13 (6 created)

## Accomplishments
- `sif search search needle --json` returns both notes unfiltered and exactly the `status: active` note under `--filter '{"field":"status","operator":"eq","value":"active"}'`, on an index built by the real CLI/indexing path.
- Typed kv rows (`document_metadata_values`) are written in the document row's transaction from the same canonical JSON string, with the D-07 skip sidecar; `document_metadata_skips` and three partial covering indexes created and dropped correctly.
- The shared AST implements qmd's 17 operators with `field` (D-18), `operands`/`operand` group shape, ASCII-only `caseInsensitive`, numeric-only ordering, ISO→epoch `mtime` input, four budgets enforced before pydantic recursion, and the entry-scope match grammar.
- The compiler emits parameterized SQL for both scopes, presence-aware `ne`/`nin`, per-element `all`, `instr`/BLOB-`substr` text operators, half-open `path` prefixes (plan reports `idx_documents_path`), and `mtime` ranges (`idx_documents_mtime`); injection-shaped operands leave the SQL shape untouched.
- The unfiltered and scoped BM25 statements are byte-identical to the pre-change capture (`4f63835`), proven by a golden recording-connection test taken before `bm25.py` was edited.
- Quality gates green: `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` 0 diagnostics, full `pytest` 2254 passed / 1 skipped at 94.96% coverage (gate 90).

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end eq frontmatter filter** - `f553a7f` (feat)
2. **Task 2: Full qmd-parity AST** - `fde6bfe` (feat)
3. **Task 3: Full per-operator SQL compiler** - `4662ea1` (feat)

**Plan metadata:** the closing docs commit created after this SUMMARY.

## Files Created/Modified
- `src/sif/core/filters.py` (new) — 17-operator discriminated union, budgets, semantic validation, mtime normalization, `parse_filter`/`parse_match`, `FilterValidationError`.
- `src/sif/search/filters.py` (new) — `compile_filter`/`compile_match`, scope probes, typed text/ordering/membership primitives, `count_matching_documents`, `count_documents_in_scope`, `count_vectors_in_scope`.
- `src/sif/database/metadata_repository.py` (new) — `TypedRow`, `SkippedKey`, `filterable_metadata`, `typed_rows`, `MetadataValueRepository.replace_from_canonical`/`delete_by_document`.
- `src/sif/database/schema.py` — `_create_metadata_tables()` after `documents`, both tables in `drop_all`.
- `src/sif/database/repositories.py` — one canonical string per create/update feeds both the row and the kv rebuild.
- `src/sif/core/models.py` — `SearchOptions.filter: FilterNode | None = None`.
- `src/sif/search/bm25.py` — `compile_filter(options.filter)` slotted after `min_score_filter` in both branches; `search_chunks` stays filter-free (documented).
- `src/sif/cli/commands/search.py` — `--filter` on `search_cmd` plus `_parse_filter_option` (parse/validate before opening the database).
- `tests/unit/cli/test_search_filter.py` (new) — tracer e2e, empty-match, invalid-filter, direct-DB kv assertions.
- `tests/unit/core/test_filters.py` (new) — node shapes, operator semantics, budgets, mtime, match grammar (84 tests).
- `tests/unit/search/test_filters_sql.py` (new) — pre-change golden statements, per-operator SQL/params, case folding, match compiler, built-in matrix, param order, injection, EXPLAIN plans, execution semantics (112 tests).
- `tests/unit/database/test_repositories.py` — fixture creates both metadata tables in production order.
- `docs/cli-reference.md` — regenerated via `make docs-generate` for `--filter` (generator-owned).

## Decisions Made
- **Parity pin:** qmd `[Unreleased]` verified 2026-11-15 against `qmd@86d2365`; the AST uses `field` (D-18). The older docs commit `abfabc5` used `key` and is superseded — recorded here so the delta is explicit and the era is not mixed.
- **Raw-payload semantics:** validation reads raw operand types so `[true, 1]` is rejected as mixed; pydantic's lax `bool→int` coercion cannot hide it.
- **`all` homogeneity:** `all` requires a non-empty homogeneous scalar list (qmd's membership-array rule). The plan text said only "non-empty"; homogeneity prevents untyped element drift.
- **`mtime` normalization scope:** ISO strings normalize on eq/ne/ordering/in/nin; `type` (`"number"`) and `exists` (bool) operands are never rewritten.
- **Built-in edge outcomes:** `path` `type` + `caseInsensitive` and every `mtime` `caseInsensitive` raise `FilterValidationError`; `exists` on either built-in is constant true/false because both columns are `NOT NULL`.
- **20-02 boundary:** `filterable_metadata` shadows `path`/`mtime` only; the `qmd.metadata` namespace merge, caps, and skip-reason expansion remain plan 20-02's contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Regenerated generator-owned CLI docs for the new flag**
- **Found during:** Task 1 (CLI surface)
- **Issue:** Adding `--filter` without regenerating `docs/cli-reference.md` fails the generator diff gate (`tests/test_docs.py`).
- **Fix:** Ran `make docs-generate`; the regenerated file also corrected pre-existing `--limit` type drift (integer → integer range) introduced by the earlier `click.IntRange` change.
- **Files modified:** `docs/cli-reference.md`
- **Verification:** `pytest tests/test_docs.py` 13 passed; a second `make docs-generate` leaves a clean diff.
- **Committed in:** `f553a7f`

**2. [Rule 1 - Bug] Filter suffix was missing its `AND` keyword**
- **Found during:** Task 1 (end-to-end CLI test)
- **Issue:** Appending the compiled predicate after `{min_score_filter}` rendered `WHERE 1 = 1 <predicate>`, a SQLite syntax error (`near "EXISTS"`).
- **Fix:** `filter_suffix = f" AND {filter_clause}"`; the empty-filter case still renders the byte-identical default.
- **Files modified:** `src/sif/search/bm25.py`
- **Verification:** `TestFilterEndToEnd` 4 passed; both golden statement tests still pass.
- **Committed in:** `f553a7f`

**3. [Rule 1 - Bug] `nin` double negation inverted membership**
- **Found during:** Task 3 (compiler smoke verification)
- **Issue:** The negative half used `NOT EXISTS (... value NOT IN (...))` — semantically "every value is in the list" — instead of `NOT EXISTS (... value IN (...))`, so `nin` matched the wrong documents.
- **Fix:** The excluded probe now uses the positive `IN` form wrapped in `NOT EXISTS` / `NOT IN`; pinned by execution tests (`ne`/`nin` match sets) and exact SQL assertions.
- **Files modified:** `src/sif/search/filters.py`, `tests/unit/search/test_filters_sql.py`
- **Verification:** `TestFilterExecutionSemantics::test_typed_equality_and_negation` passes; 112 compiler tests pass.
- **Committed in:** `4662ea1`

**4. [Rule 3 - Blocking] Golden test node id was not addressable at module level**
- **Found during:** Task 1 (tracer feedback gate)
- **Issue:** The plan verifies `tests/unit/search/test_filters_sql.py::test_unfiltered_statement_byte_identical`; a class-scoped test made pytest report "no tests ran", which the plan's `fails_when` treats as a failure.
- **Fix:** Moved the golden tests to module level (the file's docstring records why).
- **Files modified:** `tests/unit/search/test_filters_sql.py`
- **Verification:** The exact node id runs one passing test.
- **Committed in:** `f553a7f` (amended)

**5. [Rule 3 - Blocking] `DocumentRepository` fixture lacked the metadata tables**
- **Found during:** Task 1 (planned fixture repair, confirmed by the suite)
- **Issue:** The unconditional kv sync would raise `no such table: document_metadata_values` in `tests/unit/database/test_repositories.py`.
- **Fix:** Fixture calls `manager._create_metadata_tables()` immediately after `_create_documents_table()`, mirroring `create_all()`.
- **Files modified:** `tests/unit/database/test_repositories.py`
- **Verification:** 31 tests in that file pass unchanged.
- **Committed in:** `f553a7f`

---

**Total deviations:** 5 handled (2 bugs, 1 missing critical, 2 blocking) — all correctness/contract work, no scope creep.
**Impact on plan:** No plan objective changed. The `nin` fix and the `AND` fix were required for the plan's stated semantics; the docs regeneration was mandated by the project's generator-owned-docs gate.

## Issues Encountered
- Pydantic coerces `[True, 1]` to `[1, 1]` inside the value union; the raw-payload semantic pass was introduced to keep mixed-type membership rejection meaningful.
- `ty` rejects narrowing a mutable pydantic field override (`operator: str` → `Literal["eq"]`), so the base `Condition` deliberately does not declare `operator`; error helpers read it via `getattr`.

## Threat Model Compliance
- **T-20-01 (tampering):** only aliases, table/column names, and `?, ` lists are interpolated; the injection regression proves the SQL string is identical under `'`, `;`, `--`, `%`, and that execution causes no side effects.
- **T-20-02 (DoS):** iterative raw-dict budget walk (depth 8, 64 nodes, 1024-char strings, 128-element arrays) fires before pydantic recursion; a 900-deep payload reports the depth budget.
- **T-20-03 (derivation tampering):** nested/null/mixed arrays are skipped per key with a sidecar reason; the document still indexes.
- **T-20-04 (filter dropped):** `None` is the only unfiltered signal; an empty match set returns an empty page on the CLI (tested) and the compiler never returns an empty fragment for a non-`None` AST.

## Known Stubs
None. `search_chunks` intentionally stays filter-free (no production caller) and is documented in its docstring.

## Threat Flags
None — the shipped surface is fully covered by the plan's threat register.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- **Ready for 20-02:** the kv tables, `typed_rows`, and the write-path sync are in place. 20-02 must add the `qmd.metadata` namespace merge, per-key caps/skip reasons, and the `index_meta.metadata_values_version` backfill; `filterable_metadata` is the extension point.
- **Ready for 20-03:** `count_matching_documents`/`count_documents_in_scope`/`count_vectors_in_scope` exist for the vector pre-count, and the compiler's corpus/candidates split is measured (`idx_documents_path`, `idx_documents_mtime`, `idx_metadata_*_lookup`).
- **Ready for 20-04/20-05:** `compile_match` backs the discovery `--match`; the CLI validator (`_parse_filter_option`) is the shared error-mapping template for vsearch/query/MCP.
- **Carry-forward:** qmd's AST is still `[Unreleased]`; re-verify the field name/operator list before Phase 22 freezes the MCP schema.

---
*Phase: 20-metadata-filtering-discovery*
*Completed: 2026-11-15*

## Self-Check: PASSED
