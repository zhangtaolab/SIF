---
phase: 14-freshness-floor-pre-command-refresh-staleness-marking
plan: 03
subsystem: cli
tags: [click, rich, csv, xml, markdown, staleness, stderr-contract, pytest]

# Dependency graph
requires:
  - phase: 14-freshness-floor-pre-command-refresh-staleness-marking/14-01
    provides: console_err stderr contract, -q quiet gating culture, mock/real-DB CliRunner scaffolds
  - phase: 14-freshness-floor-pre-command-refresh-staleness-marking/14-02
    provides: SearchResult.vectors_stale riding to_dict() (already in --json), display-gate semantics
provides:
  - Staleness marker on every CLI output surface — Rich table dim inline annotation (no new column), CSV vectors_stale column, Markdown inline annotation, XML vectors_stale attribute, JSON via to_dict()
  - _title_cell shared table helper (escaped title + fixed dim annotation) across search/vsearch/query tables
  - _warn_stale_results shared helper — one stderr remedy hint after results, -q-gated, wired at all three command output tails
  - 16-test staleness format + remedy-hint battery in tests/unit/cli/test_search.py
affects: [sif-search/sif-get skills (stdout purity preserved), MCP clients (unchanged — no CLI change), future output formats (must carry the marker per D-12)]

# Actuals (#2632) — same estimateTokens scale (chars/4 over the realized diff)
actuals:
  tokens: 6205    # 24,819 diff chars / 4 over src+tests (plan estimate: 28,000)
  tasks: 2
  commits: 4      # MEASURED: git rev-list --count c9c5a76..HEAD

plan_head_before: c9c5a760fda00706eca73ddf714144b3f55527e7
plan_head_after: 6aeda91aef7b1ecfd85a48139e0d96b2796bb081

# Tech tracking
tech-stack:
  added: []   # zero new runtime dependencies (locked decision; Package Legitimacy Audit empty)
  patterns:
    - "Dual-shape marker rendering: every explicit renderer (table/CSV/MD/XML) reads vectors_stale via the existing _field(r, ...) reader, so SearchResult rows and --line-numbers dict rows render identically"
    - "Constant-string annotation discipline (T-14-06): the marker text is a fixed literal — Rich markup written unescaped beside an escape()d title; XML attribute is a boolean literal; no document-derived text crosses into markup"

key-files:
  created: []
  modified:
    - src/sif/cli/commands/search.py
    - tests/unit/cli/test_search.py

key-decisions:
  - "One shared _title_cell helper serves all three command tables: the annotation is a constant string appended after the escape()d title, so search/vsearch/query render the marker uniformly and a truncated title still annotates"
  - "Hint wiring sits at each command's output tail (after the full if/elif/else chain) rather than inside a formatter: the hint must fire for every output mode including --files, and the no-results early return naturally skips it (zero results means zero stale)"
  - "stdout-purity assertions use hint-specific fragments ('have stale vectors', 'run 'sif index embed'') — the D-12 table annotation legitimately contains 'stale vectors' on stdout, so the phrase alone cannot prove hint leakage"
  - "Format battery asserts against result.stdout: click >=8.2 mixes the stderr hint into .output (the 14-01 JSON-purity lesson generalized to every machine format)"

patterns-established:
  - "Per-format staleness contract: adding a result flag means touching table/CSV/MD/XML explicitly while JSON rides to_dict() — one crafted stale result must be visible in all five"
  - "Post-results remedy hint: one shared wording literal on console_err, -q-gated, count from the dual-shape reader"

requirements-completed: [QUAL-06]

coverage:
  - id: D1
    description: "Every output format renders the marker from one crafted stale result: Rich table dim annotation (search+query bodies, no new column), CSV vectors_stale column (true/false), MD '(stale vectors)' title annotation, XML vectors_stale attribute — each in both SearchResult and --line-numbers dict shapes; JSON carries the key in both shapes (no formatter change)"
    requirement: QUAL-06
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_table_marks_stale_result_not_fresh"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_query_table_marks_stale_result"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_json_carries_vectors_stale"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_json_line_numbers_dict_shape_preserves_key"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_csv_column_carries_true_and_false"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_csv_line_numbers_dict_shape_renders_marker"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_md_annotation_on_stale_title_only"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_md_line_numbers_dict_shape_renders_marker"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_xml_attribute_true_false_and_parseable"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_xml_line_numbers_dict_shape_renders_marker"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-13 remedy hint: exactly one stderr line after results naming the stale count and the 'sif index embed' remedy; never stdout; -q suppresses while --json still renders; zero stale results means no hint; fires from all three trio commands"
    requirement: QUAL-06
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_remedy_hint_one_stderr_line_names_count"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_remedy_hint_json_stdout_stays_clean"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_quiet_suppresses_hint_but_json_renders"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_zero_stale_results_no_hint"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_remedy_hint_fires_for_query_cmd"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestStalenessFormatMarker::test_remedy_hint_fires_for_vsearch_cmd"
        status: pass
    human_judgment: false
  - id: D3
    description: "Phase acceptance gate (SC1-SC3 together): six-file phase battery (drift + staleness core + presentation), docs drift gate, ruff/format/ty, and the bare full-suite pytest with coverage fail_under=90"
    requirement: QUAL-06
    verification:
      - kind: other
        ref: "six-file battery: 171 passed (tests/unit/indexing/test_drift.py, tests/unit/cli/test_search.py, tests/unit/cli/test_index_locking.py, tests/unit/search/test_staleness.py, tests/unit/mcp/test_backend.py, tests/unit/cli/test_status.py)"
        status: pass
      - kind: other
        ref: "env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -x --no-cov && ruff check src tests && ruff format --check src tests && ty check src/sif"
        status: pass
      - kind: other
        ref: "env -u FORCE_COLOR NO_COLOR=1 python -m pytest — 1224 passed, 1 skipped, 94.43% coverage (fail_under=90)"
        status: pass
    human_judgment: false

# Metrics
duration: 13min
completed: 2026-11-08
status: complete
---

# Phase 14 Plan 03: Staleness Presentation (Format Battery + Remedy Hint) Summary

**The staleness marker renders on all five CLI output surfaces — dim `(stale vectors)` table annotation (no new column), CSV `vectors_stale` column, Markdown annotation, XML boolean attribute, JSON via `to_dict()` — plus the one-line stderr `sif index embed` remedy hint, so no format silently drops the signal (D-12/D-13, SC3).**

## Performance

- **Duration:** 13 min
- **Started:** 2026-11-08T03:56:02Z
- **Completed:** 2026-11-08T04:08:37Z
- **Tasks:** 2 (both TDD: RED → GREEN)
- **Files modified:** 2 (exactly the plan's files_modified)

## TDD Gate Compliance

Both tasks executed test-first; production symbols already existed (formatters, command bodies), so every RED failure is a clean assertion failure — no skeletons needed.

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 1 (five-format marker battery) | `a46f93c` — 8 fail on planned assertions (missing table annotation, CSV column, MD annotation, XML attribute; both row shapes); 2 JSON tests pass as pins (to_dict carried the key since 14-02) | `688f94a` — 10/10 battery + 115/115 file | — (see note) |
| 2 (remedy hint + phase gate) | `98d56e1` — 4 fail on planned assertions (hint absent for search/query/vsearch + JSON stdout purity); 2 suppression tests pass as pins (must STAY true once the hint lands) | `6aeda91` — 16/16 battery + phase acceptance gate green | — (see note) |

**REFACTOR note:** no refactor-worthy cleanup existed — the three table bodies now share `_title_cell` (introduced in Task 1 GREEN as part of the feature, not a post-hoc refactor), and the hint is one shared helper from the start. `ruff check`/`format`/`ty` stayed green throughout, so no `refactor(14-03)` commit was warranted.

## Accomplishments

- One crafted stale result is visibly marked in every format — table (dim inline annotation beside the escaped title, no new column), CSV (`vectors_stale` true/false column), Markdown (`(stale vectors)` on the title line), XML (`vectors_stale="{true|false}"` fixed-literal attribute) — each proven in both the SearchResult and `--line-numbers` dict shapes through the dual-shape `_field` reader; JSON needed no formatter change (`to_dict()` has carried the key since 14-02) and both shapes are pinned by tests
- The D-13 remedy hint fires exactly once on stderr after results (`N results have stale vectors — run 'sif index embed' to refresh`), names the stale count, never touches stdout, is suppressed by `-q` while `--json` still renders, stays silent with zero stale results, and is wired identically at all three command output tails (search/vsearch/query)
- SC3's floor proven and exceeded: table AND JSON plus CSV/MD/XML — no format drops the signal (D-12)
- Phase acceptance gate (SC1-SC3 together): six-file phase battery 171 passed, docs gate 13 passed, ruff/format/ty green, bare full suite 1224 passed @ 94.43% coverage (fail_under=90)

## Task Commits

Each task was committed atomically (TDD: test → feat):

1. **Task 1 RED: failing staleness format battery** — `a46f93c` (test)
2. **Task 1 GREEN: marker in all five formats** — `688f94a` (feat)
3. **Task 2 RED: failing remedy-hint battery** — `98d56e1` (test)
4. **Task 2 GREEN: stderr hint + phase gate** — `6aeda91` (feat)

## Files Created/Modified

- `src/sif/cli/commands/search.py` — `_title_cell` (escaped title + fixed dim annotation; shared by the three command tables), CSV `vectors_stale` column, MD title-line annotation, XML fixed boolean attribute, `_warn_stale_results` helper + three output-tail call sites; `run 'sif index embed' to refresh` wording appears exactly once
- `tests/unit/cli/test_search.py` — `TestStalenessFormatMarker`: 16 tests (10 format battery incl. both row shapes, 6 remedy-hint tests); 4 pinned existing format assertions updated for the new CSV/XML shape

## Decisions Made

- One shared `_title_cell` helper for all three table bodies instead of per-command markup: uniform rendering, and the annotation survives title truncation because it is appended after the truncated-escaped title
- Hint call placed after each command's full output chain (not inside a formatter): it must fire for every output mode including `--files`, and the table branch's no-results early return naturally skips it
- vsearch table got the same `_title_cell` marker for D-12 uniformity even though a real vsearch hit can never be stale (its vector was purged — CONTEXT specifics); the test drives it through a mocked searcher, which the plan permits (the prohibition was against constructing stale hits through a *real* vsearch)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test-authoring] Crafted rows needed content for the --line-numbers dict shape**
- **Found during:** Task 1 (RED)
- **Issue:** `add_line_numbers_to_results` derives `line_numbers` from content; rows without content produce `""`, so the dict-shape JSON test's `line_numbers != ""` assertion failed for an unplanned reason
- **Fix:** The `_result` factory carries `content="line one\nline two"`; all format tests unaffected (CSV/MD/XML never render content)
- **Files modified:** tests/unit/cli/test_search.py
- **Verification:** battery went from 9 fail / 1 pass to the planned 8 fail / 2 pass, all failures on missing-marker assertions
- **Committed in:** a46f93c

**2. [Rule 1 - Planned-shape update] Four pinned existing format assertions updated**
- **Found during:** Task 1 (GREEN)
- **Issue:** Four pre-existing tests pin the exact CSV header/rows and XML element shape — `test_search_line_numbers_csv` (header + rows), `TestMachineOutputNoWrap` CSV test (header + row), `test_csv_escapes_content_fields` (DictReader dict), `test_search_line_numbers_xml` (element open tag). The new column/attribute is the plan's own acceptance criterion (`collection,vectors_stale` header), so these are planned behavior changes, not regressions
- **Fix:** Each expected shape gained the `"false"` column value / `vectors_stale="false"` attribute (fixture rows default to a fresh result)
- **Files modified:** tests/unit/cli/test_search.py
- **Verification:** 115/115 in the file
- **Committed in:** 688f94a

**3. [Rule 1 - Test-authoring] stdout-stream and hint-fragment assertions during Task 2 GREEN**
- **Found during:** Task 2 (GREEN)
- **Issue:** (a) The CSV battery read `result.output`, which click >=8.2 mixes the new stderr hint into — the exact-list assertion gained a phantom hint line; (b) the stdout-purity assertion `"stale vectors" not in result.stdout` is over-broad: the D-12 table annotation legitimately contains that phrase on stdout
- **Fix:** (a) All battery assertions read `result.stdout` (14-01's JSON-purity lesson generalized); (b) purity asserts hint-specific fragments (`have stale vectors`, `run 'sif index embed'`)
- **Files modified:** tests/unit/cli/test_search.py
- **Verification:** 16/16 battery, 121/121 file, full suite green
- **Committed in:** 6aeda91

---

**Total deviations:** 3 auto-fixed (all Rule 1 test-authoring / planned-shape updates; zero production bugs)
**Impact on plan:** All fixes keep the plan's contracts intact — stdout purity actually got a sharper test. No scope creep.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 14 complete (all 3 plans): SC1/SC2 (drift floor, 14-01), SC3 computation half (staleness core + status + MCP, 14-02), SC3 presentation half (this plan) — the full freshness floor is in
- stdout stays clean for the sif-search/sif-get skill consumers (`sif -q search ... --json`) — every notice, warning, and hint rides stderr
- Full quality suite green at `plan_head_after`: 1224 passed, 1 skipped @ 94.43% coverage (fail_under=90); ruff/format/ty green; docs drift gate green
- Next: phase verification (`/gsd-verify-work 14`), then Phase 15 planning (search quality track)

## Self-Check: PASSED

- Both key-files modified exist and carry the changes (grep: CSV header `collection,vectors_stale` at search.py:210; hint wording exactly once)
- All 4 task commits are ancestors of HEAD (`git merge-base --is-ancestor`)
- QUAL-06 shared-ID gate satisfied: 14-03 is the last plan declaring it (14-01 declared LIVE-10; 14-02 and 14-03 declare QUAL-06, both SUMMARYs now exist)

---
*Phase: 14-freshness-floor-pre-command-refresh-staleness-marking*
*Completed: 2026-11-08*
