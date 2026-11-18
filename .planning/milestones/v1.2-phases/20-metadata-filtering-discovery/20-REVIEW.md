---
phase: 20-metadata-filtering-discovery
reviewed: 2026-11-15T13:56:34Z
depth: standard
files_reviewed: 31
files_reviewed_list:
  - docs/cli-reference.md
  - src/sif/cli/commands/collection.py
  - src/sif/cli/commands/search.py
  - src/sif/cli/filter_options.py
  - src/sif/core/filters.py
  - src/sif/core/models.py
  - src/sif/database/metadata_repository.py
  - src/sif/database/repositories.py
  - src/sif/database/schema.py
  - src/sif/mcp/backend.py
  - src/sif/mcp/handlers.py
  - src/sif/mcp/protocol.py
  - src/sif/search/bm25.py
  - src/sif/search/filters.py
  - src/sif/search/hybrid.py
  - src/sif/search/vector.py
  - tests/integration/test_metadata_filtering.py
  - tests/support/bench.py
  - tests/unit/cli/test_collection.py
  - tests/unit/cli/test_search_filter.py
  - tests/unit/cli/test_search.py
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
findings:
  critical: 2
  warning: 7
  info: 5
  total: 14
  necessity: 0
status: issues_found
---

# Phase 20: Code Review Report

**Reviewed:** 2026-11-15T13:56:34Z
**Depth:** standard
**Files Reviewed:** 31
**Status:** issues_found

## Summary

Reviewed the full Phase 20 surface — filter AST/validator, SQL compiler, typed kv store and
backfill, both search legs, CLI/MCP surfaces, the discovery aggregate, the generated CLI reference,
and the phase's test batteries — against `20-CONTEXT.md` D-01..D-20. The deliberate contracts
(typed exact match, same-type presence for `ne`/`nin`, substring-any `contains`, numeric-only
ordering, ASCII-only folding, half-open `path` prefixes, the byte-identical unfiltered path,
`qmd.metadata` precedence, frozen camelCase envelope, `noqa` suppressions, generator-owned docs)
were treated as authoritative and are not reported.

Verification performed: `ruff check src tests`, `ruff format --check`, and `ty check src/sif` are
green; 781 phase-related tests run in this environment all pass; `scripts/generate_cli_ref.py` and
`scripts/generate_config_ref.py` reproduce the committed `docs/cli-reference.md` /
`docs/configuration.md` byte-for-byte. The suite's green state does **not** cover the two blockers
below: one class of user input crashes indexing/upgrading (CR-01), and one shipped operator returns
duplicate rows and broken pages on the interpreter this repository's tests run on (CR-02). Both are
reproduced end-to-end against the shipped CLI.

The necessity rubric (`~/.claude/gsd-core/references/necessity-review.md`) was read; no
necessity-category findings were provable from the repository, so `necessity: 0`.

## Narrative Findings (AI reviewer)

No `<structural_findings>` block was supplied by the workflow, so there is no structural section;
every finding below is narrative, from direct code review plus executed reproductions.

## Critical Issues

### CR-01: Typed metadata derivation is not total over JSON numbers — a single document aborts indexing and permanently bricks upgrades

**File:** `src/sif/database/metadata_repository.py:94-100` (also `src/sif/core/models.py:44-50`, `src/sif/database/schema.py:277-316`, `src/sif/indexing/incremental.py:488`)
**Issue:** `_scalar_type` (79-91) accepts any Python `int`, and `_typed_row` (94-100) converts it with `float(value)`. `json.loads`/`json.dumps` preserve arbitrary-precision integers and (with `json.dumps`' default `allow_nan=True`) write bare `NaN`/`Infinity` literals, so a frontmatter value that is a 400-digit integer, `.nan`, or `.inf` reaches the typed derivation. Three verified failure modes:

1. **Huge integer — indexing aborts.** `float(10**400)` raises `OverflowError`, which is not among `_process_file`'s caught `(sqlite3.Error, TypeError)` (`incremental.py:488`). Reproduced on a real collection: two notes, one with `big: 999…` (400 digits) → `sif index update` exits 1 with a raw `OverflowError: int too large to convert to float` and the whole pass stops (zero documents stored in the repro because the failing file sorts first; later-sorting files would leave a partially updated index). This breaks Phase 14 D-04's per-file error isolation.
2. **Huge integer — upgrade bricks every command.** A pre-Phase-20 index already storing such a blob fails inside `SchemaManager._backfill_metadata_values`; the marker is never written, so every subsequent `create_all` fails. `OverflowError` is not mapped by `open_initialized_database` (`src/sif/cli/error_handling.py:46-52`), so `sif status`, `sif search`, and even `sif index update` (the repair path, which also opens through `open_initialized_database`) exit 1 with a traceback.
3. **NaN — upgrade bricks every command with a misleading remedy.** `json.dumps` stores `NaN`; `typed_rows` reparses it to `float("nan")`; SQLite binds NaN as NULL, so the `document_metadata_values` CHECK fails. `IntegrityError` escapes the backfill and is mapped by `open_initialized_database` to *"Cannot open index database … the database file may be corrupted"* — permanently, with no CLI remedy short of deleting the index (verified end-to-end).

**Fix:**
- Make the derivation total, matching D-07's per-key skip convention: in `_scalar_type`/`_typed_row`, reject non-finite floats and ints outside the double range with a bounded skip reason (e.g. `SKIP_NON_FINITE` / `SKIP_CAP_NUMBER`) instead of raising.
- Make `canonical_metadata_json` emit standard JSON (`allow_nan=False`, stringifying non-finite values on the fallback path) so `NaN`/`Infinity` never enter `documents.metadata`.
- Harden the backfill so a single undecomposable document cannot make every future open fail (record a skip, or fail before committing any rows with a remedy-bearing message). Add the huge-int and NaN shapes to `tests/unit/database/test_schema.py` and `tests/unit/indexing/test_incremental.py`.

### CR-02: `in` filters with 2+ operands duplicate result rows, corrupt pagination, and double-count RRF scores

**File:** `src/sif/search/filters.py:186-192` (`_wrap`), `225-243` (`_in_inner`), `src/sif/search/bm25.py:106-108`, `src/sif/search/vector.py:129-130`
**Issue:** The candidates-scope compiler emits a correlated `EXISTS (SELECT 1 FROM document_metadata_values mv WHERE mv.document_id = d.id AND …)` whose inner predicate for `in` is `mv.key = ? AND mv.value_type = ? AND <typed column> IN (?, ?)`. On SQLite 3.51.0 as built by conda (Python 3.13.9, the interpreter this repository's test suite runs on), the optimizer's semijoin handling returns one outer row per matching kv row — standard `EXISTS` must emit the outer row once. Reproduced end-to-end with the shipped CLI on a real index (`multi.md` has `tags: [alpha, beta]`, `single.md` has `tags: [beta]`):

```
sif search search needle --filter '{"field":"tags","operator":"in","value":["alpha","beta"]}' --json
→ multi.md rank 1, multi.md rank 2, single.md rank 3
sif search search needle … --limit 1 --offset 1 --json
→ multi.md   (the duplicate consumes the page slot)
```

The same shape duplicates for numeric and boolean array-valued keys (verified), and on the vector leg: default mode inflates `chunk_matches` (2 for one chunk), `--per-chunk` returns the identical chunk twice. `RRFFusion.fuse` (`src/sif/search/rrf.py:99-131`) enumerates the duplicated leg rows, so the duplicated document's fusion score is double-counted (measured 0.032522 vs 0.016393) and later ranks shift. `count_matching_documents` uses the corpus-scope `IN (SELECT document_id …)` form and stays correct (returns 2), so the D-08 pre-count disagrees with the leg's row count.

Scope is precise: `eq`, `ne`, `nin`, `all`, `exists`, `prefix`, `suffix`, scalar/OR `contains`, the reserved `path`/`mtime` built-ins, and `caseInsensitive` comparisons (which compare `lower(...)` and cannot use the index) do not reproduce. The same SQL returns correct results on Homebrew SQLite 3.54.1 and Apple's 3.51.0, so the trigger is a build-specific SQLite optimizer defect — but it fires on the project's own runtime, and the compiled shape need not depend on optimizer correctness.

**Fix:**
- Append `LIMIT 1` to the candidates-scope probe in `_wrap` (`search/filters.py:186-192`). It is semantics-preserving (an `EXISTS` needs one row), verified to remove the duplication, and cheap.
- Add a regression test that executes an `in` filter over a multi-valued key and asserts the exact ordered document list. The existing `TestFilterExecutionSemantics._matching_ids` (`tests/unit/search/test_filters_sql.py:949-957`) compares **sets**, and the `_SIMPLE_CASES` tests assert SQL strings only, so duplicates are invisible to the whole battery. The CLI/integration batteries use `eq`/`gte`/`prefix`, never `in`.
- Consider the same `LIMIT 1` in the discovery `NOT EXISTS` probes for symmetry.

## Warnings

### WR-01: Unbounded integer operands make the validator raise `OverflowError`, escaping the documented error contract

**File:** `src/sif/core/filters.py:313-315` (callers `339-346`, `349-358`, `323-336`), `src/sif/cli/filter_options.py:31-34`, `src/sif/mcp/handlers.py:96-102`
**Issue:** `_is_number` calls `math.isfinite(value)` on a raw `json.loads` int; an integer outside the double range raises `OverflowError` instead of returning False. `parse_filter` therefore raises a non-`FilterValidationError` on a well-formed JSON payload. Reproduced: `sif search search needle --filter '{"field":"priority","operator":"gt","value":<400 nines>}'` and `sif collection metadata --filter <same>` both exit 1 with an uncaught `OverflowError` and no user-facing message (`_parse_option` catches only `FilterValidationError`). MCP handlers catch the same narrow type, so the server's catch-all turns it into a generic `Error: int too large…` rather than the D-17-shaped message.
**Fix:** Make the finite test total — e.g. `if isinstance(value, int): return -(1 << 53) <= value <= (1 << 53)` before `math.isfinite`, or wrap it and return False on `OverflowError`. Add a huge-int operand to the budget battery and document a numeric operand bound in D-13's list.

### WR-02: Compile-time filter rejections bypass the `ClickException` boundary, so reserved-field mistakes print tracebacks

**File:** `src/sif/core/filters.py:457-479`, `src/sif/search/filters.py:518-563`, `src/sif/cli/commands/search.py:526/727/987`, `src/sif/cli/commands/collection.py:505-512`
**Issue:** `_validate_semantics` dispatches by operator only and never special-cases the reserved fields, so several well-formed payloads parse successfully and are rejected only by the compiler: `path` with `gt/gte/lt/lte`, `all`, a numeric `eq/ne/in/nin`, or `type`+`caseInsensitive`; `mtime` with `contains/prefix/suffix/all` or `caseInsensitive`. The CLI only maps parse failures to `click.ClickException`, and compilation happens inside the search call (BM25/vector) or inside the DB-open block (`collection metadata`). Reproduced: `--filter '{"field":"path","operator":"lt","value":5}'` (and `path eq 5`, `path all`, `path type … caseInsensitive`, `mtime prefix`, `mtime all`) on all three search commands exits 1 with an uncaught `FilterValidationError` and empty output — a traceback on the real CLI — instead of D-17's `filter.<field>.<operator>: …` message.
**Fix:** Make reserved-field compatibility a parse-time rule in `_validate_semantics` (one taxonomy for CLI/MCP/discovery), or compile the AST once in `filter_options` (discarding the fragment) before any DB open. Add a matrix test asserting the CLI message for every rejected built-in form and `isError` with the same text over MCP.

### WR-03: Explicit `caseInsensitive: false` is treated as enabled and rejected

**File:** `src/sif/core/filters.py:433-446`
**Issue:** `_check_case_insensitive` returns only when the flag is `None`; an explicit `false` falls through to the string-operand requirement. Verified: `{"field":"priority","operator":"eq","value":1,"caseInsensitive":false}` and the same on `mtime` raise `filter.eq: caseInsensitive requires a string or string-list operand`. An agent that emits schema-complete filters cannot filter numeric or `mtime` fields at all. `false` is semantically identical to absent.
**Fix:** Change the guard to `if not flag: return` (then `if not isinstance(value, str) and not (list-of-strings): raise`). Add a positive test for explicit `false` on a numeric and an `mtime` condition.

### WR-04: String elements of arrays bypass the 1024-character cap

**File:** `src/sif/database/metadata_repository.py:136-146` (`_classify_array`), `149-166` (`_classify_value`)
**Issue:** `_classify_value` applies `MAX_STRING_CHARS` only to scalar strings (161-162); `_classify_array` checks homogeneity and element count but never element length. Verified: `typed_rows('{"tags":["<5000 chars>","<5000 chars>"]}')` stores two 5000-character typed rows with no skip. This contradicts D-07's "string ≤ 1024 chars" and the 20-02 summary's claim that the full cap set is implemented; the oversized values become filterable and are exposed by discovery (bounded only by the 64 KB frontmatter cap).
**Fix:** In `_classify_array`, skip the key as `SKIP_CAP_STRING` when any element's length exceeds `MAX_STRING_CHARS` (per-key skip semantics, consistent with D-07). Add the case to `test_skip_reasons`.

### WR-05: Empty arrays are silently dropped — no rows, no skip, invisible to `exists` and discovery

**File:** `src/sif/database/metadata_repository.py:138-139`, `149-166`
**Issue:** `_classify_array([])` returns `([], None)`, so `tags: []` produces no typed rows and no `document_metadata_skips` row. Verified: `typed_rows('{"tags":[]}') == ([], [])`. Consequences: `exists: true` is false for a key that is present; `type` is false; discovery omits the key from `keys`/`totalKeys`; and `skippedKeys` does not count it — which violates D-07's "discovery reports the skipped-key count so silence is impossible" and D-16's "every filterable key must appear". `tags: []` is a common note-template value, and the `_classify_value` docstring (155-157) claims the value is filterable, which is false. Note: `20-02-SUMMARY.md:152` records "empty arrays produce neither rows nor skips", so the contract needs a human decision rather than a silent fix.
**Fix:** Record an `empty_array` skip row (keeps the "no fake value rows" rule and makes discovery able to report it), or add a presence-only row representation; update the docstring and add the case to `TestDerivation` and `TestDiscovery`.

### WR-06: Non-finite numbers reach `--json` and MCP output as invalid JSON

**File:** `src/sif/database/metadata_repository.py:283-290`, `539-572`; `src/sif/cli/commands/collection.py:523-525`; `src/sif/mcp/handlers.py:295-303`
**Issue:** `.inf` frontmatter is stored as `float("inf")` and flows into the discovery `range`/median and the `mtime` built-in. Both `collection metadata --json` and the MCP `metadata` tool serialize with `json.dumps`, whose default `allow_nan=True` emits bare `Infinity`/`NaN` — invalid per RFC 8259. Verified end-to-end: an index containing `v: .inf` makes `sif collection metadata --json` emit `"min": Infinity` and fail a strict JSON parse; the MCP tool's text content has the same shape, as does the `get` tool's `metadata` dict for a stored `NaN`. This breaks the frozen Phase 22 envelope's claim to be machine-consumable for any corpus with `.inf`/`.nan` frontmatter.
**Fix:** Exclude non-finite numbers at derivation time (see CR-01), and serialize with `allow_nan=False` (mapping non-finite to `null` or a string) so machine output stays strict JSON. Add a test that parses the output with `parse_constant` raising.

### WR-07: The default `collection metadata` table never reports `skippedKeys`

**File:** `src/sif/cli/commands/collection.py:397-428`
**Issue:** `_render_metadata_table` renders the built-in rows, frontmatter rows, and the remaining-key footer, but `skippedKeys` is only present in `--json` output. D-07 requires discovery to report the skipped-key count "so silence is impossible", and the table is the default human-facing surface — a corpus whose keys were all skipped (nested/mixed/over-cap) looks identical to a corpus with no frontmatter.
**Fix:** Print a footer line when `result["skippedKeys"]` is non-zero (e.g. `... N keys skipped as non-indexable`). Extend `TestCollectionMetadata` with a table-mode assertion (today only the JSON test asserts `skippedKeys`).

## Info

### IN-01: Two operator-set constants are dead code

**File:** `src/sif/core/filters.py:60-61`
**Issue:** `_GROUP_OPERATORS` and `_MEMBERSHIP_OPERATORS` are defined but never referenced anywhere in `src/` or `tests/` (verified by grep); membership/group dispatch uses explicit `isinstance`/`in` checks. They only add drift risk for the 17-operator contract.
**Fix:** Delete both constants, or use them in `_validate_semantics`/the compiler so the operator taxonomy has one source.

### IN-02: `_collection_predicate` treats the exclude-all sentinel as "no scope"

**File:** `src/sif/search/filters.py:729-736`
**Issue:** `_collection_predicate([])` returns `("", [])` (unfiltered), while the parallel `metadata_repository._collection_clause` (223-235) correctly renders `AND 0 = 1`. Every current caller (`count_matching_documents`, `count_documents_in_scope`, `count_vectors_in_scope`) guards `[]` first, so the sentinel contract holds today, but a future direct caller would silently widen scope to the whole corpus.
**Fix:** Render `AND 0 = 1` for `[]` (matching the documented `SearchOptions.collection_ids` sentinel) and drop the caller-side guards, so there is exactly one representation of exclude-all.

### IN-03: Discovery window sizes have no upper bound

**File:** `src/sif/mcp/protocol.py:413-416`, `src/sif/cli/commands/collection.py:459-470`, `src/sif/database/metadata_repository.py:454-461`
**Issue:** `limit` and `value_limit` are lower-bounded only. A single MCP request with `limit = 10**9, value_limit = 10**9` materializes every key and every distinct value (the aggregate queries are batched to the page's keys, but the page itself is unbounded). The 20-05 summary's T-20-18 claim that "no unbounded mode exists" covers only the defaults.
**Fix:** Add a documented maximum (e.g. `le=1000`) to both the MCP model and the Click ranges, or cap the server-side page and report the truncation through the existing exact remainders.

### IN-04: `collection metadata --json` diverges from the established JSON output convention

**File:** `src/sif/cli/commands/collection.py:523-525`
**Issue:** The command prints compact `json.dumps(result)` without `ensure_ascii=False`, while the other `--json` surfaces use `format_results_json` (`indent=2, ensure_ascii=False`, `src/sif/cli/commands/search.py:101-107`). D-14 says JSON follows the existing output conventions; the compact form also escapes non-ASCII metadata values as `\uXXXX`.
**Fix:** Reuse the shared JSON formatter (pretty-printed, `ensure_ascii=False`), keeping the envelope unchanged.

### IN-05: The half-populated-store rule has no read-side check

**File:** `src/sif/database/schema.py:277-316`, `src/sif/search/filters.py:739-787`
**Issue:** D-06's hard rule ("filtering must never be enabled against a half-populated store") is enforced only by `create_all` raising on a failed backfill. No search or discovery path verifies `index_meta.metadata_values_version`, and the pushdown/pre-count helpers assume the typed store is complete. Any host that opens the database without running `create_all` (a future read-only path, a migration tool, a test seam) would silently under-return instead of failing closed.
**Fix:** Assert the marker once at the query boundary (e.g. in `compile_filter`'s callers or `MetadataValueRepository` construction) and raise a remedy-bearing error when it is absent, turning the invariant into defense in depth rather than a property of one call site.

---

_Reviewed: 2026-11-15T13:56:34Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
