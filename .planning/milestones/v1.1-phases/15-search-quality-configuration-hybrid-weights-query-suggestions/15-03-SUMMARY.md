---
phase: 15-search-quality-configuration-hybrid-weights-query-suggestions
plan: 03
subsystem: cli-mcp
tags: [click-cli, mcp, did-you-mean, query-history, suggestions, rich, pydantic, stdout-purity, docs-generator]

requires:
  - phase: 15-search-quality-configuration-hybrid-weights-query-suggestions
    provides: 15-02 SuggestionEngine (prefix_completions / did_you_mean / history_suggestions), query_log + QueryLogRepository, SIF_QUERY_HISTORY_* settings
  - phase: 14-freshness-floor-pre-command-refresh-staleness-marking
    provides: stderr notice culture (console_err) and the fail-soft _pre_search_refresh settings precedent
provides:
  - "sif suggest QUERY — three labeled sections (prefix completions / did you mean / history), --json with exactly the three arrays, --clear-history, missing-index guard, -q"
  - "Zero-result DYM on sif search / vsearch / query — table line on stdout, stderr-only in csv/md/xml/files, conditional JSON object, plain [] when no suggestion"
  - "One fail-soft query_log row per executed CLI search (SIF_QUERY_HISTORY_ENABLED gate; -q still logs; MCP never logs)"
  - "MCP query QueryOutput.suggestions populated explicitly on the zero-result path"
  - "SKILL.md zero-result JSON contract updated for both shapes"
affects: [16-search-quality-bench-sweep, verify-work-15]

actuals:
  tokens: 13372 # chars/4 over the realized diff (53,486 diff chars)
  tasks: 3
  commits: 5
  plan_head_before: a71ef92ec83534dc96bf1f95ae621ab7fd501e6a
  plan_head_after: b90c5686a44de7fe008c94073f0efc8812dfe00c

tech-stack:
  added: [] # zero new runtime dependencies
  patterns:
    - "Host wiring over one engine: every consumer (suggest cmd, three search commands, MCP backend) constructs SuggestionEngine on its already-open connection — no new connection, no duplicated logic"
    - "Conditional zero-result JSON: plain [] preserved unless suggestions exist, then {query, results: [], suggestions} — additive contract change"
    - "Fail-soft post-results hooks: DYM only on empty results; history write wrapped in try/except + logger.warning inside the caller's connection context"
    - "Boundary remap carried on the return value: HybridSearchResults(list[SearchResult]) attaches suggestions so the list contract survives while the handler populates QueryOutput explicitly"

key-files:
  created:
    - src/sif/cli/commands/suggest.py
    - tests/unit/cli/test_suggest.py
  modified:
    - src/sif/cli/main.py
    - src/sif/cli/commands/search.py
    - src/sif/mcp/protocol.py
    - src/sif/mcp/backend.py
    - src/sif/mcp/handlers.py
    - .claude/skills/sif-search/SKILL.md
    - docs/cli-reference.md
    - tests/unit/cli/test_search.py
    - tests/unit/mcp/test_backend.py

key-decisions:
  - "Suggestions ride HybridSearchResults(list[SearchResult]) instead of changing hybrid_search's return type — every existing caller/mock keeps working; the handler reads the attribute with getattr (empty list for plain lists)"
  - "suggest passes the engine's default n=3 to did_you_mean (planner action step) while --limit caps completions and history sections; all three render independently (D-11)"
  - "Table sections are a bold heading plus a borderless table rather than a Rich Table title — CliRunner's 80-column capture wrapped a titled table's header ('Prefix / completions'), breaking ordered-section output"
  - "History writes pass each command's in-scope settings (vsearch/query) and a best-effort get_settings for search (no settings in scope) — unrelated bad config never breaks BM25 (14-01 precedent)"
  - "100 ms product sanity measured, not asserted: 20,000-term synthetic index, sif suggest quant --json = 717.7 ms vs 706.3 ms --help baseline (delta 11.4 ms); core budget remains pinned by 15-02 tests"

patterns-established:
  - "Zero-result mode routing: stdout table line, stderr for machine modes, conditional JSON object — one shared helper set (_print_dym_stdout/_print_dym_stderr/_json_with_suggestions)"
  - "Zero-result-only engine cost (D-05): helpers return [] immediately when results exist"
  - "Executed-search logging is a two-line call site (_record_query_history) guarded by settings and wrapped fail-soft"

requirements-completed: [QUAL-02, QUAL-03, QUAL-04]

coverage:
  - id: D1
    description: "sif suggest renders the three labeled sections in fixed order; --json carries exactly completions/did_you_mean/history; --clear-history deletes all rows with a post-commit confirmation; QUERY and --clear-history are mutually exclusive; missing index prints the notice and materializes nothing; -q prints no table"
    requirement: QUAL-04
    verification:
      - kind: integration
        ref: "tests/unit/cli/test_suggest.py#TestSuggestSections::test_table_shows_three_labeled_sections_in_fixed_order"
        status: pass
      - kind: integration
        ref: "tests/unit/cli/test_suggest.py#TestSuggestSections::test_json_has_exactly_three_arrays"
        status: pass
      - kind: integration
        ref: "tests/unit/cli/test_suggest.py#TestClearHistory"
        status: pass
      - kind: integration
        ref: "tests/unit/cli/test_suggest.py#TestGuardsAndQuiet"
        status: pass
    human_judgment: false
  - id: D2
    description: "Zero-result DYM on search/vsearch/query: table line after 'No results found.', csv/md/xml/files suggestions on stderr only, conditional JSON object when suggestions exist and plain [] otherwise, -q suppresses the line"
    requirement: QUAL-02
    verification:
      - kind: integration
        ref: "tests/unit/cli/test_search.py#TestZeroResultSuggestions::test_table_mode_shows_dym_after_no_results"
        status: pass
      - kind: integration
        ref: "tests/unit/cli/test_search.py#TestZeroResultSuggestions::test_machine_modes_keep_suggestions_off_stdout"
        status: pass
      - kind: integration
        ref: "tests/unit/cli/test_search.py#TestZeroResultSuggestions::test_zero_result_json_wraps_suggestions_or_keeps_plain_array"
        status: pass
    human_judgment: false
  - id: D3
    description: "Executed CLI searches write one query_log row (query, result count, collections); SIF_QUERY_HISTORY_ENABLED=0 writes nothing; -q still writes; history-write and engine failures never fail the search"
    requirement: QUAL-03
    verification:
      - kind: integration
        ref: "tests/unit/cli/test_search.py#TestQueryHistoryWrite::test_search_writes_one_row_with_results_and_collections"
        status: pass
      - kind: integration
        ref: "tests/unit/cli/test_search.py#TestQueryHistoryWrite::test_history_disabled_writes_nothing"
        status: pass
      - kind: integration
        ref: "tests/unit/cli/test_search.py#TestQueryHistoryWrite::test_history_write_failure_never_fails_search"
        status: pass
      - kind: integration
        ref: "tests/unit/cli/test_search.py#TestQueryHistoryWrite::test_suggestion_failure_never_fails_zero_result_search"
        status: pass
    human_judgment: false
  - id: D4
    description: "MCP query responses carry zero-result suggestions (explicit boundary remap), an empty list when results exist, degrade to empty on engine failure, and never write query_log"
    requirement: QUAL-02
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestZeroResultSuggestions::test_zero_result_query_carries_suggestions"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestZeroResultSuggestions::test_result_present_query_has_empty_suggestions"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestZeroResultSuggestions::test_mcp_query_never_writes_query_log"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestZeroResultSuggestions::test_handler_carries_suggestions_into_query_output"
        status: pass
    human_judgment: false
  - id: D5
    description: "Suggestions documented in SKILL.md (both zero-result JSON shapes); sif suggest entered in the generated cli-reference via make docs-generate; docs gate green and regen idempotent"
    verification:
      - kind: other
        ref: "env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -x --no-cov (13 passed)"
        status: pass
      - kind: other
        ref: "make docs-generate && git diff --exit-code docs/ (clean)"
        status: pass
    human_judgment: false
  - id: D6
    description: "D-14 100 ms product sanity for sif suggest --json (manual measurement, no wall-clock test)"
    verification: []
    human_judgment: true
    rationale: "Deliberately a manual product check (D-14): measured 717.7 ms end-to-end vs a 706.3 ms --help startup baseline on a 20,000-term synthetic index — 11.4 ms of actual work, far inside the 100 ms budget. The engine's core cost stays pinned deterministically by the 15-02 budget test."

duration: 10min
completed: 2026-11-08
status: complete
---

# Phase 15 Plan 03: Query Suggestion Hosts Summary

**`sif suggest`'s three-section table/JSON surface, zero-result did-you-mean across all three CLI searches and the MCP query tool (stdout-pure, conditional JSON object), and fail-soft query-history writes with opt-out and a single clear path — phase gate green at 94.85% coverage.**

## Performance

- **Duration:** 10 min (10:37:53Z → 10:48:00Z)
- **Started:** 2026-11-08T10:37:53Z
- **Completed:** 2026-11-08T10:48:00Z
- **Tasks:** 3 (1 tracer TDD + 1 TDD + 1 auto)
- **Files modified:** 11 (9 planned hand-edited + 1 regen side-effect + 1 handler file required by Task 3's action; 2 new — command module + test battery)

## Accomplishments

- `sif suggest QUERY` ships the D-11 three-section surface: prefix completions, did-you-mean rewrites, and history, each independently top-N and labeled; `--json` emits exactly `{completions, did_you_mean, history}` (D-12 — no other formats); `--clear-history` is the single D-10 clear (mutually exclusive with QUERY, confirmation printed after commit); a missing index never materializes a DB; `-q` prints no table and suggest writes no history row
- Zero-result recovery now exists on every CLI search: `sif search`/`vsearch`/`query` compute DYM only when results are empty (D-05), render the line after "No results found." in table mode, route it to stderr only in `--csv`/`--md`/`--xml`/`--files` (stdout purity preserved), and in `--json` emit the conditional object `{"query", "results": [], "suggestions"}` — while a zero-result query whose words all retrieve still emits plain `[]`, so the documented skill contract survives
- Every executed CLI search writes one fail-soft `query_log` row (query, result count, collection names): `SIF_QUERY_HISTORY_ENABLED=0` skips the write entirely, `-q` still logs, and both a raising repository and an exploding suggestion engine leave the search at exit 0 (Pitfall 10); MCP queries never write
- MCP `query` responses gain `suggestions` on the zero-result path; the boundary remap is explicit (`HybridSearchResults` attaches the list, `QueryToolHandler` reads it into `QueryOutput`), so an unlisted field cannot be silently dropped
- `.claude/skills/sif-search/SKILL.md` documents both zero-result JSON shapes; `docs/cli-reference.md` regenerated by `make docs-generate`
- Phase gate green: full suite 1333 passed / 1 skipped @ 94.85% coverage (fail_under=90), ruff + format + ty green, docs gate 13 passed, regen idempotent

## Task Commits

Each task was committed atomically (TDD tasks carry RED + GREEN commits):

1. **Task 1 RED: failing suggest battery** - `8e52fc0` (test)
2. **Task 1 GREEN: suggest command + registration + docs regen** - `b77e355` (feat)
3. **Task 2 RED: failing zero-result DYM + history battery** - `a2725c7` (test)
4. **Task 2 GREEN: zero-result hooks + history writes + SKILL.md** - `28faa08` (feat)
5. **Task 3: MCP zero-result suggestions + phase gate** - `b90c568` (feat)

**Plan metadata:** (this SUMMARY commit)

_Note: both TDD tasks produced two commits (test → feat); no REFACTOR commit was needed._

## TDD Gate Compliance

| Plan | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| 15-03 Task 1 (tracer) | `8e52fc0` ✓ | `b77e355` ✓ | — (not needed) | Pass |
| 15-03 Task 2 | `a2725c7` ✓ | `28faa08` ✓ | — (not needed) | Pass |

Both RED phases committed an importable zero-behavior skeleton (Task 1) or the failing battery against absent hooks (Task 2), so the target test failed on its planned assertion, never an import error. Evidence was captured as JUnit XML (`pytest --junitxml`) and validated with `gsd_run check tdd-red-evidence` → `RED_EVIDENCE_OK`:

- Task 1: target `test_table_shows_three_labeled_sections_in_fixed_order` failed because the skeleton emitted empty output (8 of 9 planned-behavior tests failed; the `-q` suppression negative passed vacuously).
- Task 2: target `test_table_mode_shows_dym_after_no_results` failed on `'Did you mean: quantum machin' in 'No results found.\n'` (14 of 16 failed; disabled-history and `-q` negatives passed vacuously).

The Task 1 tracer feedback gate re-ran the exact `<verify>` chain after GREEN (9 passed; `make docs-generate` then `git diff --exit-code docs/cli-reference.md` clean) before Task 2 expanded.

## Files Created/Modified

- `src/sif/cli/commands/suggest.py` — `suggest_cmd` (table/`--json`/`--clear-history`/guard/quiet), `_collect`, `_clear_history`, escaped section rendering
- `src/sif/cli/main.py` — import + `cli.add_command(suggest_cmd)`
- `src/sif/cli/commands/search.py` — `_zero_result_suggestions`, `_record_query_history`, DYM/stdout-stderr/JSON helpers; hooks wired into search/vsearch/query (WR-02 untouched)
- `src/sif/mcp/protocol.py` — `QueryOutput.suggestions: list[str]`
- `src/sif/mcp/backend.py` — `HybridSearchResults` + `_with_suggestions`; explicit zero-result population on both empty paths
- `src/sif/mcp/handlers.py` — explicit `suggestions` remap into `QueryOutput`
- `.claude/skills/sif-search/SKILL.md` — zero-result `[]` vs suggestions-object contract
- `docs/cli-reference.md` — generator output for `sif suggest` (never hand-edited)
- `tests/unit/cli/test_suggest.py` — real-DB CliRunner battery (9 tests)
- `tests/unit/cli/test_search.py` — `TestZeroResultSuggestions` + `TestQueryHistoryWrite` (16 tests)
- `tests/unit/mcp/test_backend.py` — `TestZeroResultSuggestions` (5 tests)

## Decisions Made

- Suggestions ride a `HybridSearchResults(list[SearchResult])` subclass rather than changing `hybrid_search`'s return type: every caller (and existing mock returning `[]`) keeps working, while the handler reads the attribute with `getattr(..., [])`
- `did_you_mean` keeps the engine's default `n=3` in `suggest`; `--limit` caps the completions and history sections (plan action step 3, D-11 independent sections)
- Section labels are bold headings above borderless tables — a titled Rich table wrapped "Prefix completions" across lines in CliRunner's 80-column capture
- History writes use the command's in-scope settings (vsearch/query) and a best-effort `get_settings()` for `search`, which has none in scope — the 14-01 fail-soft settings precedent
- MCP zero-result suggestions are a flat list (RESEARCH A6) and never written to `query_log` (D-08)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] MCP handler serialization (`src/sif/mcp/handlers.py`)**
- **Found during:** Task 3
- **Issue:** The plan's `files_modified` frontmatter omits `src/sif/mcp/handlers.py`, but Task 3's own action step 3 requires adapting the query handler to serialize the field. Without it `QueryOutput.suggestions` would be silently dropped at the hand-written output composition.
- **Fix:** `QueryOutput(results=results, suggestions=getattr(results, "suggestions", []))` with an explicit boundary-remap comment
- **Files modified:** src/sif/mcp/handlers.py
- **Verification:** `test_handler_carries_suggestions_into_query_output` asserts the serialized payload carries `["quantum machin"]`
- **Committed in:** b90c568

---

**Total deviations:** 1 auto-fixed (1 missing critical, required by the task's own action; not a functional change)
**Impact on plan:** No scope creep — the file edit is the plan's stated integration point, only its frontmatter list was incomplete.

## Issues Encountered

- **RED Task 2 fail-soft test shape:** the `SuggestionEngine` failure test could not patch the symbol before GREEN existed (AttributeError at patch time). The classifier's target test still failed on its planned assertion, so RED was valid; noted in the evidence record as an expected pre-GREEN shape.
- **Rich table title wrapping:** a `Table(title="Prefix completions")` in an 80-column CliRunner capture wrapped the title across two lines and broke the ordered-section assertion; switched to a bold heading + borderless table (same visible labeling).
- **MCP test Settings:** `Settings(reranker_model_name=None)` fails Pydantic validation (field is `str`, default `""`); the hermetic fixture uses defaults instead.
- **Docs-only pytest coverage floor:** `pytest tests/test_docs.py -x` exits non-zero on the global `fail_under=90` for a docs-only subset (known v1.0 decision); verified with `--no-cov` (13 passed). The full-suite run keeps the permanent gate.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 15 is complete (3/3 plans): SC1 golden still passing, SC2 zero-result DYM live in every interface, SC3 history recorded/opt-out/clear, SC4 suggest three sections with the 11.4 ms measured product cost
- Ready for `/gsd-verify-work 15`; UAT expectations from earlier waves apply — stem display ("quantum machin"), index-global suggestions under collection filters, and run-level CJK completions are documented UX notes, not defects
- Phase 16's sweep can construct `SearchOptions` with arbitrary weights (15-01 bridge); suggestion/history surfaces need no further work
- WR-02 remains an open pre-existing finding — this plan touched only the post-results paths and the zero-result branches

## Self-Check: PASSED

- Files: `src/sif/cli/commands/suggest.py`, `tests/unit/cli/test_suggest.py` present; all 11 modified/new files in `git diff name-only a71ef92..HEAD`
- Commits: 8e52fc0, b77e355, a2725c7, 28faa08, b90c568 all ancestors of HEAD (`git rev-list --count a71ef92..HEAD` = 5 before this metadata commit)
- Gates: full suite 1333 passed / 1 skipped @ 94.85% coverage (fail_under=90); ruff check + format green; ty green; CLI battery 162 passed; searcher+MCP battery 330 passed; docs gate 13 passed (`--no-cov`); `make docs-generate` + `git diff --exit-code docs/` clean
- RED gates: `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK` for both TDD tasks (JUnit evidence retained under `.planning/tmp/15-03-task{1,2}-red.*`)
- Manual budget (D-14): 20,000-term synthetic index — `sif suggest quant --json` 717.7 ms vs 706.3 ms `--help` baseline = 11.4 ms

---
*Phase: 15-search-quality-configuration-hybrid-weights-query-suggestions*
*Completed: 2026-11-08*
