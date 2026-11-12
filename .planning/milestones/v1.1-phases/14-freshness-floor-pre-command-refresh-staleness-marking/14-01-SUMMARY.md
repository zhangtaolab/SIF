---
phase: 14-freshness-floor-pre-command-refresh-staleness-marking
plan: 01
subsystem: indexing
tags: [sqlite, fts5, flock, mtime-drift, click, rich, pydantic-settings]

# Dependency graph
requires:
  - phase: 11-live-index-foundation-concurrent-db-incremental-core
    provides: index_lock flock contract (wait-then-run), IncrementalIndexer core, lock_wait_timeout setting
  - phase: 12-sif-watch-foreground-mvp
    provides: update_paths per-path seam (D-06), FileScanner shared predicate, missing-root guard (D-11)
provides:
  - DriftReport / detect_drift / refresh_drifted in src/sif/indexing/drift.py (presentation-free, BM25-only)
  - DocumentRepository.list_stat_by_collection — content-free stored-side stat snapshot
  - Settings fields search_refresh_enabled (SIF_SEARCH_REFRESH_ENABLED, default True) and search_refresh_max_files (SIF_SEARCH_REFRESH_MAX_FILES, default 100, ge=1)
  - _resolve_collections + _pre_search_refresh shared helpers in cli/commands/search.py, wired into the search trio with the stderr notice/warning contract
  - --no-refresh flag on sif search / vsearch / query
  - Generated docs rows for both settings and the three flags
affects: [14-02 (staleness marking reuses the drift-walk culture and stderr contract), 16 (bench latency — must stay bypassed), mcp-server (unchanged by construction)]

# Actuals (#2632) — same estimateTokens scale (chars/4 over the realized diff)
actuals:
  tokens: 16493   # 65,972 diff chars / 4 (plan estimate: 55,000)
  tasks: 2
  commits: 4      # MEASURED: git rev-list --count f061eeb..HEAD

plan_head_before: f061eeb82ed822e91df8b23d6917c801b6ed5978
plan_head_after: 3dede93bae5eb5aa757cab0130e520c60fc1d664

# Tech tracking
tech-stack:
  added: []   # zero new runtime dependencies (locked decision; Package Legitimacy Audit empty)
  patterns:
    - "Silence-first cap decision: total_count==0 returns before the cap is ever consulted (SC2)"
    - "CLI-command-layer-only placement enforced by sole-importer grep (D-01): bench/MCP bypass by construction"
    - "Best-effort check contract: settings/detect/refresh failures warn on stderr and never break search (D-05)"

key-files:
  created:
    - src/sif/indexing/drift.py
    - tests/unit/indexing/test_drift.py
  modified:
    - src/sif/cli/commands/search.py
    - src/sif/config/settings.py
    - src/sif/database/repositories.py
    - scripts/generate_config_ref.py
    - docs/configuration.md
    - docs/cli-reference.md
    - tests/unit/cli/test_search.py
    - tests/unit/cli/test_index_locking.py

key-decisions:
  - "mtime-primary drift compare (research correction to SC1's mtime/size): documents.file_size is frontmatter-stripped body length, never refreshed on update — a size compare would false-positive forever"
  - "Silence-first ordering in _pre_search_refresh: the clean path (count==0) returns before the cap comparison runs"
  - "Settings-construction failure skips the check silently: 'sif search' never touched settings before this check, so invalid unrelated config (e.g. a bad reranker type) must not break BM25 search; query/vsearch surface it at their own embedder touchpoints"
  - "vsearch tests moved from the source-module CollectionRepository patch target to sif.cli.commands.search.CollectionRepository — the shared _resolve_collections uses the search-module binding (test intent unchanged)"
  - "refresh_drifted is the only lock acquisition site; one lock window covers all drifted collections (watcher precedent is per-job because bursts arrive per-collection)"

patterns-established:
  - "Pre-search check contract: read-only walk → count → lock+refresh only when 0 < count <= cap; notices on console_err, -q suppresses, drift never errors"
  - "Deterministic drift tests: os.utime explicit timestamps, content writes, unlink — never sleep(); lock-absence and row-snapshot asserts, never latency"

requirements-completed: [LIVE-10]

coverage:
  - id: D1
    description: "Drift detection module: DriftReport, detect_drift (mtime-primary walk, missing-root guard, resolve-before-compare), refresh_drifted (flock-wrapped BM25 burst)"
    requirement: LIVE-10
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_drift.py#TestDetectDrift.test_touch_drift_detected_via_os_utime"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_drift.py#TestDetectDrift.test_missing_root_skips_collection_without_phantom_deletion"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_drift.py#TestRefreshDrifted.test_refresh_updates_content_and_converges_mtime"
        status: pass
    human_judgment: false
  - id: D2
    description: "DocumentRepository.list_stat_by_collection — SELECT path, mtime snapshot that never loads content"
    requirement: LIVE-10
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_drift.py#TestDetectDrift.test_clean_collection_yields_empty_report (exercises the stored-side snapshot)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Settings: search_refresh_enabled (default True) + search_refresh_max_files (default 100, ge=1)"
    requirement: LIVE-10
    verification:
      - kind: other
        ref: "python -c \"from sif.config.settings import Settings; s = Settings(); assert s.search_refresh_enabled is True and s.search_refresh_max_files == 100\""
        status: pass
    human_judgment: false
  - id: D4
    description: "search_cmd end-to-end: modified/new/deleted content found with no watch running; one stderr notice; second search silent; clean search lockless+silent+writeless; --json stdout purity (SC1/SC2, D-07)"
    requirement: LIVE-10
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPreSearchRefresh.test_search_finds_modified_content_and_notifies_on_stderr"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPreSearchRefresh.test_clean_search_is_lockless_silent_and_writeless"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPreSearchRefresh.test_json_stdout_stays_clean_with_refresh_notice_on_stderr"
        status: pass
    human_judgment: false
  - id: D5
    description: "Trio completion + opt-outs: vsearch/query run the same check; --no-refresh on all three; SIF_SEARCH_REFRESH_ENABLED=0 skips detection; -q suppresses notice and over-cap warning while refresh still runs"
    requirement: LIVE-10
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPreSearchRefresh.test_vsearch_refreshes_drifted_file_before_search"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPreSearchRefresh.test_query_refreshes_drifted_file_before_search"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPreSearchRefresh.test_no_refresh_flag_skips_check_on_all_trio_commands"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPreSearchRefresh.test_setting_disabled_skips_detection_entirely"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPreSearchRefresh.test_quiet_suppresses_notice_but_refresh_still_happens"
        status: pass
    human_judgment: false
  - id: D6
    description: "Cap boundary (D-05/D-06): count==cap refreshes, count>cap skips with the 'sif index update' warning, exit 0 with stale hits, no lock file, and no candidate parsing over cap"
    requirement: LIVE-10
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPreSearchRefresh.test_over_cap_drift_skips_refresh_and_warns"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPreSearchRefresh.test_cap_boundary_count_equal_to_cap_refreshes"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPreSearchRefresh.test_over_cap_never_parses_candidates"
        status: pass
    human_judgment: false
  - id: D7
    description: "Flock coexistence (D-03): under-cap drift vs a parent-held flock waits out lock_wait_timeout then refreshes anyway; a clean search performs zero lock acquisitions"
    requirement: LIVE-10
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_index_locking.py#TestPreSearchRefreshCoexistence.test_search_refresh_waits_out_held_lock_then_proceeds"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_index_locking.py#TestPreSearchRefreshCoexistence.test_clean_search_never_enters_index_lock"
        status: pass
    human_judgment: false
  - id: D8
    description: "Generated docs: both SIF_SEARCH_REFRESH_* rows in configuration.md, --no-refresh on all three commands in cli-reference.md (regenerated via make docs-generate, drift-gated)"
    requirement: LIVE-10
    verification:
      - kind: other
        ref: "grep counts: SIF_SEARCH_REFRESH_MAX_FILES=1, SIF_SEARCH_REFRESH_ENABLED=1 in docs/configuration.md; --no-refresh=3 in docs/cli-reference.md"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py (13 passed)"
        status: pass
    human_judgment: false

# Metrics
duration: 24min
completed: 2026-11-08
status: complete
---

# Phase 14 Plan 01: Pre-Command Drift Refresh Floor Summary

**Stat-walk drift detection (mtime vs documents) + capped BM25-only refresh in the search trio's command layer — `sif search` now finds post-index edits with no watch running, and a clean index pays zero writes, zero locks, zero notices.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-11-08T03:06:34Z
- **Completed:** 2026-11-08T03:31:16Z
- **Tasks:** 2 (both TDD: RED → GREEN)
- **Files modified:** 10

## TDD Gate Compliance

Both tasks executed test-first; the RED commits carry an importable zero-behavior skeleton so failures are assertion failures, never import errors (11-01 culture).

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 1 (tracer: search_cmd e2e) | `526e400` — 8/10 drift battery + 3/4 CLI tests failed on planned assertions (empty skeleton report; missing stderr notice) | `bde4b8c` — all green | — (see note) |
| 2 (trio + cap + opt-outs + coexistence + docs) | `a732376` — 5 fail on planned assertions (`--no-refresh` absent, vsearch/query unwired); cap/opt-out/coexistence passed as regression pins (Task 1 landed the final warning wording, as the plan allows) | `3dede93` — all green + docs + full-suite gate | — (see note) |

**REFACTOR note:** the Task 1 → Task 2 extraction of the inline check into `_pre_search_refresh` is a behavior-preserving refactor, but it is inseparable from Task 2's new behavior (vsearch/query call sites require the helper to exist), so it landed inside `3dede93` rather than as a standalone `refactor(14-01)` commit. No other refactor-worthy cleanup existed; `ruff check`/`format`/`ty` stayed green throughout.

**Tracer feedback gate (auto mode):** verify re-run end-to-end after Task 1 — 10/10 drift battery, 4/4 CLI refresh tests, settings defaults probe — all green; expanded to Task 2.

## Accomplishments

- `sif search`, `sif vsearch`, and `sif query` stat-walk the collections being searched and BM25-refresh drifted files (modified/new/deleted) before constructing the searcher — "always works even without watch" (SC1), with the check placed so `sif bench` and the MCP server bypass it by construction (D-01, proven by `git grep -l "sif.indexing.drift" -- src/sif` → search.py only)
- Clean index = read-only walk: no lock file, no notice, no writes — proven structurally (SC2), including a recording-lock spy showing zero acquisitions
- Over-cap drift (> SIF_SEARCH_REFRESH_MAX_FILES) skips refresh entirely, warns on stderr naming the count and the `sif index update` remedy, and search still exits 0 with stale-index hits (D-05/D-06); count-first proven — IncrementalIndexer is never even constructed over cap
- Under-cap refresh coexists with a held flock: waits out `lock_wait_timeout` (0.2s deadline, lower-bound assert only) then runs anyway (D-03, 11-D02 wait-then-run)
- Opt-outs at three levels: `SIF_SEARCH_REFRESH_ENABLED=0` (skips detection entirely), `--no-refresh` on each command, `-q` (suppresses notice/warning; refresh still happens)
- stdout stays clean for `--json`/`--csv` piping: notices ride `console_err` (verified by parsing `result.stdout` as pure JSON while the notice sits in stderr) — protects the sif-search/sif-get skill consumers

## Task Commits

Each task was committed atomically (TDD: test → feat):

1. **Task 1 RED: failing drift battery + e2e tests + skeleton** — `526e400` (test)
2. **Task 1 GREEN: drift module + settings + repo stat + search_cmd wiring** — `bde4b8c` (feat)
3. **Task 2 RED: trio/cap/opt-out/coexistence battery** — `a732376` (test)
4. **Task 2 GREEN: shared helper + trio + flags + docs + full gate** — `3dede93` (feat)

## Files Created/Modified

- `src/sif/indexing/drift.py` (NEW) — presentation-free drift core: DriftReport, detect_drift (mtime-primary walk, 12-D11 missing-root guard, resolve-before-compare), refresh_drifted (one index_lock window → IncrementalIndexer.update_paths per collection)
- `src/sif/cli/commands/search.py` — `_resolve_collections` (trio semantics preserved) + `_pre_search_refresh` (silence-first cap, stderr contract, best-effort failure handling); wired into all three commands after resolution, before searcher/pipeline construction; `--no-refresh` flags
- `src/sif/config/settings.py` — `search_refresh_enabled`, `search_refresh_max_files`
- `src/sif/database/repositories.py` — `list_stat_by_collection` (`SELECT path, mtime` — never loads content)
- `scripts/generate_config_ref.py` — both fields registered under "Search Settings"
- `docs/configuration.md`, `docs/cli-reference.md` — regenerated via `make docs-generate` (generator-owned)
- `tests/unit/indexing/test_drift.py` (NEW) — 10-test deterministic battery
- `tests/unit/cli/test_search.py` — `TestPreSearchRefresh` (17 tests incl. parametrized trio flag test)
- `tests/unit/cli/test_index_locking.py` — `TestPreSearchRefreshCoexistence` + `_recording_drift_lock` spy

## Decisions Made

- mtime-primary compare (Pitfall 1 correction) — documented in the drift module docstring; stat-based derivation intent preserved
- Silence-first cap ordering: `total_count == 0` returns before the cap is consulted (cleaner SC2 semantics and keeps zero-drift invocations off the cap comparison)
- Settings-construction failure inside the check is a silent debug-skip, not a warning: `sif search` never touched settings before this check, so unrelated bad config must not degrade it; query/vsearch surface the same error at their own embedder touchpoints exactly as before
- One lock window for the whole multi-collection burst (simpler than watch's per-job shape; the drift set is already cap-bounded)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Silence-first reorder + config-failure skip in `_pre_search_refresh`**
- **Found during:** Task 2 (GREEN)
- **Issue:** With the check wired into vsearch/query, existing mocked-settings tests hit `int > MagicMock` on the cap comparison even with zero drift, and a raw `ValidationError` from `get_settings()` would have crashed `sif search` on unrelated bad config (a regression — search_cmd never touched settings before)
- **Fix:** `total_count == 0` returns before the cap is consulted; `get_settings()` gets its own try/except that debug-logs and skips the check (query/vsearch still surface config errors cleanly at their embedder touchpoints)
- **Files modified:** src/sif/cli/commands/search.py
- **Verification:** full test_search.py + test_index_locking.py green; full suite 1191 passed
- **Committed in:** 3dede93

**2. [Rule 3 - Blocking] vsearch test patch targets moved to the search module (7 sites)**
- **Found during:** Task 2 (GREEN)
- **Issue:** vsearch_cmd previously imported `CollectionRepository` locally from the source module, and its tests patched `sif.database.repositories.CollectionRepository`; the shared `_resolve_collections` uses search.py's module-level binding, so those patches stopped intercepting resolution (empty collection_ids; `json.loads(MagicMock)` in `_row_to_collection`)
- **Fix:** Switched the 7 vsearch-driving patches to `sif.cli.commands.search.CollectionRepository` — the same target the search/query tests already use; test intent (filtering/closure behavior) unchanged
- **Files modified:** tests/unit/cli/test_search.py
- **Verification:** 110/110 in the two files; full suite green
- **Committed in:** 3dede93

**3. [Rule 1 - Test-authoring corrections during RED (no production impact)**
- **Found during:** Task 1/2 RED runs
- **Issue:** (a) CliRunner under click >=8.2 mixes stderr into `result.output`, so the JSON-purity test must parse `result.stdout`; (b) Rich soft-wraps the over-cap warning at console width, so the wording is asserted against whitespace-normalized stderr; (c) one case-sensitivity typo in a stored-content assertion
- **Fix:** Test-side only; no production change
- **Verification:** targeted batteries green
- **Committed in:** 526e400 / a732376

---

**Total deviations:** 3 auto-fixed (1 bug, 1 blocking, 1 test-authoring)
**Impact on plan:** All fixes keep the plan's contracts intact (D-05 drift-never-errors actually got stronger). No scope creep.

## Plan-Directed Advisory Notes (recorded per the plan's output spec)

1. **SC1 "mtime/size check" is implemented mtime-only:** `documents.file_size` is frontmatter-stripped body byte length and is never refreshed on update (RESEARCH Pitfall 1), so a size compare would false-positive forever. The stat-based derivation intent is preserved — content changes always move mtime. Documented in the drift module docstring.
2. **Plan 14-02's staleness display gate:** markers fire only when the index has ≥1 embedding — a deliberate reading of D-09, blessed by RESEARCH Open Question 2 (either reading satisfies QUAL-06's letter); see the 14-02 objective.

## Known Edge (accepted research assumption A4, not a defect)

A file touched-but-unchanged (mtime moved, content identical) counts as drift, and `update_paths`' checksum-skip does not persist the new mtime — so touch-only drift re-parses (and re-notices) on every search until the content actually changes. Converging it would require persisting mtime inside the Phase 11 checksum-skip contract (a shared-core change out of this plan's scope). Content edits — the real drift case — converge on the first refresh (asserted by `test_refresh_updates_content_and_converges_mtime` and the silent-second-search e2e test).

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- LIVE-10 floor complete: all three search commands refresh drift under the cap with the full opt-out/coexistence contract; ready for 14-02 (staleness marking), which reuses this stderr-notice culture and the D-13 remedy-hint pattern
- bench (Phase 16) and the MCP server remain provably bypassed (sole-importer grep)
- Full quality suite green at `plan_head_after`: 1191 passed @ 94.39% coverage (fail_under=90), ruff/format/ty green, docs drift gate green

## Self-Check: PASSED

- All 10 key-files exist on disk (created + modified lists verified via `[ -f ]`)
- All 4 task commits are ancestors of HEAD (`git merge-base --is-ancestor`)
- LIVE-10 marked ready by `requirements.ready-ids` (no sibling plan declares it)

---
*Phase: 14-freshness-floor-pre-command-refresh-staleness-marking*
*Completed: 2026-11-08*
