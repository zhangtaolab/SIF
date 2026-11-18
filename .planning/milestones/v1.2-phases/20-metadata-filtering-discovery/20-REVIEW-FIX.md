---
phase: 20-metadata-filtering-discovery
fixed_at: 2026-11-15T14:18:00Z
review_path: .planning/phases/20-metadata-filtering-discovery/20-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 20: Code Review Fix Report

**Fixed at:** 2026-11-15T14:18:00Z
**Source review:** `.planning/phases/20-metadata-filtering-discovery/20-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (CR-01, CR-02, WR-01..WR-07)
- Fixed: 9
- Skipped: 0
- Info findings IN-01..IN-05 were deliberately left untouched per the fix scope.

## Fixed Issues

### CR-01: Typed metadata derivation is total over JSON numbers

**Status:** fixed
**Files modified:**
- `src/sif/database/metadata_repository.py:60-70,109-123,169-210,254-255`
  - New bounded reasons `non_finite`, `cap_number`, `invalid_json`.
  - `_number_skip_reason` converts `float(value)` overflow and non-finite values
    into per-key skips instead of raising.
  - `_classify_array` / `_classify_scalar` apply the check to scalars and array
    elements; `typed_rows` catches non-JSON blobs and records one document-level
    `invalid_json` skip (key `<metadata>`), so a single undecomposable stored
    blob can never abort the backfill and brick every future open.
- `src/sif/core/models.py:37,59`
  - `_canonicalize_metadata` stringifies non-finite floats (`"nan"`, `"inf"`,
    `"-inf"`) and `canonical_metadata_json` now passes `allow_nan=False`, so
    `documents.metadata` is always RFC 8259 JSON.
- `src/sif/indexing/incremental.py:488`
  - `_process_file`'s per-file isolation catch now includes `OverflowError`
    (defense in depth; derivation itself no longer raises it).

**Regression tests (fail pre-fix):**
- `tests/unit/database/test_metadata_values.py:302` — huge int / bare `NaN` /
  `Infinity` skip that key; `:324` unparseable blob records one skip;
  `:331` canonical serializer emits strict JSON strings.
- `tests/unit/database/test_schema.py:861` — pre-Phase-20 huge-int and bare-NaN
  blobs complete the backfill, write the marker, and re-open as a no-op;
  `:912` unparseable blob completes the pass.
- `tests/unit/indexing/test_incremental.py:295` — a 400-digit integer and
  `.nan` frontmatter index as per-key skip/string without aborting the pass.

**Commit:** `fe2db38`

### CR-02: `in` filters duplicate result rows

**Status:** fixed
**Files modified:**
- `src/sif/search/filters.py:202-219` — every candidates-scope `EXISTS` /
  `NOT EXISTS` probe now ends in `LIMIT 1`. Semantics-preserving for an
  existence probe, and it removes the SQLite 3.51.0 semijoin duplication. The
  corpus-scope `IN (SELECT document_id ...)` form is deliberately unchanged
  (limiting it would truncate the set).

**Regression tests (fail pre-fix):**
- `tests/unit/search/test_filters_sql.py:990` — `in` over string and numeric
  multi-valued keys asserts the exact ORDERED document list (`["d1", "d2"]`),
  not a set; the review's reproduction returns `d1` twice pre-fix on this
  environment's SQLite 3.51.0.
- `tests/unit/search/test_filters_sql.py:1011` — probe-shape assertion:
  candidates scope ends in `LIMIT 1`, corpus scope never contains it.
- The `_probe()` expectation helper now includes `LIMIT 1`, so every existing
  compiled-SQL case asserts the bounded shape.

**Commit:** `0558aab`

### WR-01: Unbounded integer operands raise `OverflowError`

**Status:** fixed
**Files modified:**
- `src/sif/core/filters.py:319` — `_is_number` is total: `math.isfinite` is
  wrapped and `OverflowError` returns false, so `parse_filter` raises only
  `FilterValidationError`.
- `src/sif/search/filters.py:95-115,167-190` — compiler defense-in-depth
  (`_is_finite_number`, `_value_type_of`, `_require_number`,
  `_require_number_list`) is total for directly constructed ASTs.
- Numeric-validity rule documented in the code: an operand must be a finite
  JSON number representable as a double. (No CONTEXT decision conflict: D-13
  budgets are unchanged; this is a validity rule, consistent with its spirit.)

**Regression tests (fail pre-fix):**
- `tests/unit/core/test_filters.py:293` — `eq`/`gt`/`in`/`nin`/`all` with
  `10**400` raise `FilterValidationError`, not `OverflowError`.
- `tests/unit/search/test_filters_sql.py:452` — directly constructed AST with a
  huge integer is rejected by the compiler.
- `tests/unit/cli/test_search_filter.py:226` — all three search commands exit
  through the ClickException boundary with `filter.gt`, before any DB open.
- `tests/unit/cli/test_collection.py:1078` — `collection metadata` rejects it
  before creating the database.
- `tests/unit/mcp/test_backend.py:1546` (payload entry; test at `:1549`) — MCP
  returns a controlled `isError` result.

**Commit:** `32bd7a7`

### WR-02: Compile-time filter rejections bypass `ClickException`

**Status:** fixed (requires human verification of the message taxonomy)
**Files modified:**
- `src/sif/core/filters.py:70-71,472-560,595` — reserved-field compatibility is
  now a parse-time rule: `_is_text_operand`, `_is_mtime_operand`,
  `_check_path_field`, `_check_mtime_field`, dispatched by `_check_reserved_field`
  from `_validate_semantics`. The SQL compiler keeps its defensive checks for
  already-constructed ASTs.
- Taxonomy note: the parse path is the established `filter.<operator path>`
  (e.g. `filter.lt: "lt" does not support ordering ...; field 'path'`); the
  message names the field. This matches the existing D-17 tests rather than the
  compiler's `filter.<field>.<operator>` path string.

**Regression tests (fail pre-fix):**
- `tests/unit/core/test_filters.py:412` — 14 rejected built-in forms are
  parse-time errors with the operator path and field in the message.
- `tests/unit/search/test_filters_sql.py:790` — the mtime ISO +
  `caseInsensitive` pairing is rejected during parse (previously compiled first).
- `tests/unit/cli/test_search_filter.py:249` — matrix over the 8 rejected forms
  × all three search commands: exit non-zero, message present, no DB open, no
  refresh.
- `tests/unit/cli/test_collection.py:1064` — matrix over 5 forms: message
  present and the database file is never created.
- `tests/unit/mcp/test_backend.py:1580` — the same 8 forms return
  `ToolsCallResult(isError=True)` with the same text.

**Commit:** `524d70f`

### WR-03: Explicit `caseInsensitive: false` treated as enabled

**Status:** fixed
**Files modified:**
- `src/sif/core/filters.py:450` — the guard is now `if not flag: return`, so
  `false` and absent are identical; only a truthy flag imposes the
  string-operand requirement.

**Regression tests (fail pre-fix):**
- `tests/unit/core/test_filters.py:280` — explicit `false` parses on a numeric
  condition, an `mtime` numeric condition, an ISO `mtime` condition, and a
  `path type` condition.

**Commit:** `a3af5ec`

### WR-04: String elements of arrays bypass the 1024-char cap

**Status:** fixed
**Files modified:**
- `src/sif/database/metadata_repository.py:169-186` — `_classify_array` skips
  the key as `cap_string` when any string element exceeds
  `MAX_STRING_CHARS` (per-key skip, D-07).

**Regression tests (fail pre-fix):**
- `tests/unit/database/test_metadata_values.py:218-219` —
  `test_skip_reasons` gains single- and mixed-element over-cap array cases
  (test defined at `:223`).
- `tests/unit/database/test_metadata_values.py:280` — an element exactly at the
  1024-character boundary is still stored.

**Commit:** `8075839`

### WR-05: Empty arrays silently dropped

**Status:** fixed (deliberate contract decision)
**Contract decision:** recording an `empty_array` skip row. `tags: []` keeps
the "no fake value rows" rule (so `exists`/`type` never see a phantom value), but
it now writes one `document_metadata_skips` row, so discovery's `skippedKeys`
and the table footer report it. This is the D-07-consistent choice: skip
accounting lives in the sidecar and silence is impossible. It does not add a
value row and does not make the key filterable, so D-16 ("every filterable key
must appear") is unchanged — the key is present but non-indexable, exactly the
category D-07 defines.

**Files modified:**
- `src/sif/database/metadata_repository.py:60,169-172` — new
  `SKIP_EMPTY_ARRAY = "empty_array"`; `_classify_array([])` returns the skip.
  Module/function docstrings updated.

**Regression tests (fail pre-fix):**
- `tests/unit/database/test_metadata_values.py:273` — derivation returns
  `SkippedKey("tags", "empty_array")` while other keys still derive.
- `tests/unit/database/test_metadata_values.py:623` — discovery reports
  `skippedKeys == 1` and omits the key from `keys`.

**Commit:** `c18ace7`

### WR-06: Non-finite numbers reach `--json`/MCP as invalid JSON

**Status:** fixed
**Files modified:**
- `src/sif/utils/json_output.py` (new) — `json_safe` recursively stringifies
  non-finite floats (`"nan"`/`"inf"`/`"-inf"`, matching the canonical metadata
  form) and `json_dumps_strict` serializes with `allow_nan=False`.
- `src/sif/cli/commands/collection.py:20,531` — `collection metadata --json`
  uses the strict serializer.
- `src/sif/mcp/handlers.py:22,127,172,208,237,300` — all five tool payloads
  (query, get, multi_get, status, metadata) use it, covering the `get` tool's
  stored-metadata dictionary and the discovery ranges.
- CR-01 already excludes non-finite values at derivation time and stringifies
  them at write time; the serializer is the defense-in-depth layer for legacy
  blobs (never rewritten by the backfill) and the `mtime` built-in column.

**Regression tests (fail pre-fix; both parse with `parse_constant` raising):**
- `tests/unit/cli/test_collection.py:951` — a document with metadata
  `{"v": inf}` and an infinite `mtime` produces a strict-JSON discovery
  envelope; the metadata value is the string `"inf"` and the built-in range is
  stringified.
- `tests/unit/mcp/test_integration.py:441` — the `get` tool serializes stored
  `inf`/`nan` metadata as `"inf"`/`"nan"` in strict JSON.

**Commit:** `4595707`

### WR-07: Default `collection metadata` table omits `skippedKeys`

**Status:** fixed
**Files modified:**
- `src/sif/cli/commands/collection.py:427-435` — `_render_metadata_table`
  prints `... N key(s) skipped as non-indexable` when `skippedKeys` is non-zero
  (proper singular/plural), satisfying D-07 on the default human surface.

**Regression tests (fail pre-fix):**
- `tests/unit/cli/test_collection.py:912` — a nested frontmatter key renders the
  footer; the key itself never appears.
- `tests/unit/cli/test_collection.py:898` — the existing table test also asserts
  the footer is absent when nothing was skipped.

**Commit:** `4a4d44f`

## Verification

- Environment: `workflow.use_worktrees=false` in `.planning/config.json`, so all
  edits, tests, and commits ran in the **main checkout** at
  `/Users/forrest/GitHub/SIF` (branch `dev`), not an isolated worktree. Results
  are reproducible from this tree.
- Each finding's targeted tests were run after the fix, and each new regression
  test was re-run against the pre-fix source (file swap or path-scoped stash)
  to confirm it fails there. All nine failed pre-fix (CR-01's suite failed at
  import because the new skip-reason constants did not exist; behavior-level
  failures were also confirmed for the other findings).
- The byte-identical unfiltered/scoped BM25 golden statements still pass
  (`tests/unit/search/test_filters_sql.py::test_unfiltered_statement_byte_identical`,
  `::test_scoped_statement_byte_identical`); `compile_filter(None)` is untouched.
- Full quality gate (final, in this order):
  - `ruff check src tests` — pass
  - `ruff format --check src tests` — 208 files already formatted
  - `ty check src/sif` — pass
  - `env -u FORCE_COLOR NO_COLOR=1 pytest` — **2482 passed, 1 skipped**, coverage
    **95.35%** (gate 90%), 21 warnings
- No CLI command, flag, or Settings field was added, so the generator-owned
  `docs/cli-reference.md` / `docs/configuration.md` are unchanged.
- Locked contracts were preserved: typed exact match (no coercion), substring-any
  `contains`, numeric-only ordering, ASCII-only folding, half-open `path`
  prefixes, `qmd.metadata` namespace-wins in the derived view, the frozen
  discovery envelope names, and the excluded-all sentinel.

## Notes / follow-ups not in scope

- IN-01..IN-05 were not fixed (Info tier). `_GROUP_OPERATORS` and
  `_MEMBERSHIP_OPERATORS` remain untouched.
- The synthetic document-level skip key for unparseable blobs is `<metadata>`;
  it is counted by `skippedKeys` and never listed as a filterable key.
- The pre-existing stash entry `stash@{0}` (WIP on `6c8f408`, containing
  `.planning/STATE.md`, `.planning/config.json`, `src/sif/cli/commands/get.py`,
  `src/sif/mcp/backend.py`) predates this run and was left untouched. The
  pre-existing modification to `.planning/config.json` was also left untouched.

---

_Fixed: 2026-11-15T14:18:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
