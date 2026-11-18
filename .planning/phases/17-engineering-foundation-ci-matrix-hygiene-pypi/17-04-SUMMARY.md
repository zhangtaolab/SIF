---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 04
subsystem: infra
tags: [windows, degradation-smoke, hc-yoga, fcntl, posix-fork, systemd, makefile, rich-progress, gbk]

# Dependency graph
requires: ["17-01"]
provides:
  - "POSIX-fork guards on both boundaries of `sif watch --detach`: RuntimeError in daemon.detach, ClickException in _run_detach; neither reaches os.pipe/os.fork"
  - "Windows service refusal in _service_manager before any systemctl/launchctl probe"
  - "scripts/windows_smoke.py: argv-only, model-free CLI degradation smoke with six pure matchers and an 8-step assertion table"
  - "tests/test_windows_smoke_script.py: matcher unit battery proving tracebacks are never accepted and no model-loading command is built"
  - "make windows-smoke: hc exec preflight + uv python install + frozen sync + smoke against D:\\Github\\SIF"
  - "Recorded green yoga run at HEAD 48759e2: 8/8 PASS incl. missing-root Removed: 0"
affects: [17-06, 17-09, 18, 19, 20, 21, 22, 23, 24]

# Actuals (#2632)
actuals:
  tokens: 5655
  tasks: 3
  commits: 3
  plan_head_before: b346700a5b3e196dd225bb729a4804e1bdc192bb
  plan_head_after: 48759e2c532d01d92a0deef08520a58c41115378

tech-stack:
  added: []
  patterns:
    - "Remote degradation smoke: a committed script of pure matchers + an argv-only assertion table, driven by a Makefile target over hc exec, whose evidence is a HEAD line plus per-assertion PASS lines"
    - "Encodability-aware Rich spinner: pick the ASCII line spinner when the console codec cannot encode the default braille frames"

key-files:
  created:
    - scripts/windows_smoke.py
    - tests/test_windows_smoke_script.py
  modified:
    - src/sif/utils/daemon.py
    - src/sif/cli/commands/watch.py
    - src/sif/cli/commands/index.py
    - src/sif/utils/progress.py
    - Makefile
    - tests/unit/utils/test_daemon.py
    - tests/unit/cli/test_watch_cmd.py
    - tests/unit/utils/test_progress.py

key-decisions:
  - "Guarded detach at both boundaries (library RuntimeError + CLI ClickException) so neither a direct daemon.detach call nor the CLI path can reach os.pipe/os.fork on a platform without them"
  - "Placed the win32 service refusal in _service_manager (the shared install/uninstall site) so it fires before the systemctl/launchctl probe and every service flag gets the same Windows message"
  - "Kept the smoke strictly model-free (BM25 `search search`, no query/vsearch/embed/pull) and argv-only with a per-run temp SIF_DB_PATH, per T-17-12/T-17-14"
  - "Recorded evidence only from the re-run at the fix commit 48759e2; the earlier c74e860 run is explicitly not evidence because it exposed the GBK spinner bug"
  - "Fixed the spinner by choosing an encodable spinner name per stream rather than stripping the progress bar, preserving live progress on consoles that can render it"

patterns-established:
  - "Smoke refusal assertions combine three checks: non-zero exit, cause+remedy message matcher, and absence of 'Traceback (most recent call last)'"
  - "Real-platform evidence is recorded as `smoke_head: <sha>` in the phase SUMMARY for later release gates to grep"

requirements-completed: [ENG-02]

coverage:
  - id: D1
    description: "`sif watch --detach` refuses on a platform without os.fork with a POSIX-fork cause + foreground remedy and no traceback"
    requirement: ENG-02
    verification:
      - kind: unit
        ref: "tests/unit/utils/test_daemon.py#test_detach_requires_fork"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_watch_cmd.py#TestDaemonFlagGuards"
        status: pass
      - kind: e2e
        ref: "make windows-smoke on yoga @ 48759e2: PASS watch --detach refusal"
        status: pass
    human_judgment: false
  - id: D2
    description: "`sif watch --install-service`/`--uninstall-service` refuse on win32 with a Windows-specific cause + foreground remedy before any service-manager probe"
    requirement: ENG-02
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_watch_cmd.py#TestServiceFlags"
        status: pass
      - kind: e2e
        ref: "make windows-smoke on yoga @ 48759e2: PASS watch --install-service refusal"
        status: pass
    human_judgment: false
  - id: D3
    description: "Committed smoke script with pure matchers and an argv-only, temp-DB, model-free assertion table"
    requirement: ENG-02
    verification:
      - kind: unit
        ref: "tests/test_windows_smoke_script.py"
        status: pass
      - kind: integration
        ref: "python -m py_compile scripts/windows_smoke.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "`make windows-smoke` drives a clean yoga checkout through the full degradation table and exits 0 at the tested HEAD"
    requirement: ENG-02
    verification:
      - kind: manual_procedural
        ref: "make windows-smoke @ 48759e2c532d01d92a0deef08520a58c41115378 — 8/8 PASS, exit 0"
        status: pass
    human_judgment: false

# Metrics
duration: 30min
completed: 2026-11-14
status: complete
---

# Phase 17 Plan 04: Windows Degradation Guards + hc Yoga Smoke Summary

**Honest Windows degradation proven on real Windows: fork/systemd refusals with cause+remedy, an 8/8 PASS yoga smoke at HEAD 48759e2, and no traceback on any refusal path**

## Performance

- **Duration:** ~30 min active (overnight pause between the failing first smoke and the fix re-run)
- **Started:** 2026-11-13T09:22:38Z
- **Completed:** 2026-11-14T01:26:02Z
- **Tasks:** 3
- **Files modified:** 10 (2 created, 8 modified)

## Accomplishments

- `sif watch --detach` can no longer reach `os.pipe`/`os.fork` on Windows: `daemon.detach` raises `RuntimeError` and the CLI raises `ClickException`, both naming POSIX fork and the foreground-watch remedy.
- `sif watch --install-service`/`--uninstall-service` refuse on win32 before the systemctl/launchctl probe, with a Windows-specific message naming the foreground alternative.
- `scripts/windows_smoke.py` codifies the degradation contract as an 8-step argv-only, model-free table with unit-tested pure matchers that reject raw tracebacks.
- `make windows-smoke` runs the preflight, `uv python install`, frozen sync, and the smoke over `hc exec` against `D:\Github\SIF`.
- The real yoga run exposed a genuine GBK console bug in the index spinner (Rule 1 fix, commit 48759e2); the re-run at that fix commit is 8/8 PASS.

## Recorded Yoga Evidence (Task 3)

Full output of `make windows-smoke` from the repo root, run against a clean yoga checkout:

```
hc exec --on yoga --timeout 120 --cwd 'D:\Github\SIF' git rev-parse HEAD
48759e2c532d01d92a0deef08520a58c41115378
hc exec --on yoga --timeout 120 --cwd 'D:\Github\SIF' git status --porcelain
hc exec --on yoga --timeout 600 --cwd 'D:\Github\SIF' uv python install 3.12
Python 3.12 is already installed
hc exec --on yoga --timeout 600 --cwd 'D:\Github\SIF' uv sync --frozen --extra dev
Checked 36 packages in 81ms
hc exec --on yoga --timeout 600 --cwd 'D:\Github\SIF' uv run --frozen python scripts/windows_smoke.py
HEAD 48759e2c532d01d92a0deef08520a58c41115378
PASS version
PASS collection add
PASS index update (flock warning)
PASS BM25 search json
PASS status
PASS index update (missing root preserved)
PASS watch --detach refusal
PASS watch --install-service refusal
PASS all assertions; tested HEAD 48759e2c532d01d92a0deef08520a58c41115378
```

Exit code: 0. No model download occurred; no raw traceback appeared.

smoke_head: 48759e2c532d01d92a0deef08520a58c41115378

## Task Commits

Each task was committed atomically:

1. **Task 1: Guard watch detach and service paths for Windows** - `8b116b5` (feat)
2. **Task 2: Add the Windows degradation smoke and its yoga target** - `c74e860` (feat)
3. **Task 3: Run the degradation smoke on yoga and record the evidence** - no code commit; recorded evidence is this section (3rd commit is the Rule 1 fix below)

**Rule 1 fix (found by Task 3's first smoke run):** `48759e2` (fix) — keeps the index spinner encodable on legacy Windows consoles.

_Plan metadata commit is created after this SUMMARY is written._

## Files Created/Modified

- `scripts/windows_smoke.py` — argv-only degradation smoke: HEAD preflight + dirty-tree refusal, temp `SIF_DB_PATH`, 8-step assertion table, six pure matchers.
- `tests/test_windows_smoke_script.py` — matcher positive/negative battery incl. a raw `AttributeError` detach traceback and a bare service traceback; asserts every built argv is a list of strings and no query/vsearch/embed/pull appears.
- `src/sif/utils/daemon.py` — `detach()` raises `RuntimeError` before `os.pipe` when `os.fork` is absent.
- `src/sif/cli/commands/watch.py` — `_run_detach` POSIX-fork guard; `_service_manager` win32 refusal; ASCII-spinner wiring for watch reconcile.
- `src/sif/utils/progress.py` — `spinner_name()` selects rich's ASCII `line` spinner when the stream cannot encode braille frames.
- `src/sif/cli/commands/index.py` — index update uses the encodability-aware spinner.
- `Makefile` — `windows-smoke` target, `YOGA_DIR`/`YOGA_PYTHON`, help line, `.PHONY`.
- `tests/unit/utils/test_daemon.py` — `test_detach_requires_fork`.
- `tests/unit/cli/test_watch_cmd.py` — detach-refusal and win32 service-refusal CLI tests.
- `tests/unit/utils/test_progress.py` — spinner encodability tests.

## Decisions Made

- Detach is guarded at both the library and CLI boundaries; either path alone would leave the other reachable.
- The Windows service refusal lives in `_service_manager` (shared by install and uninstall) so it precedes every service-manager probe.
- The smoke uses BM25-only `search search` and a per-run temporary database, honoring the plan prohibition on touching the user's index or downloading a model.
- Evidence is taken only from a clean checkout at the fix commit; the c74e860 run stands as the bug-finding run, not as proof.
- The spinner fix chooses an ASCII spinner per stream instead of disabling progress, so capable consoles keep live progress.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed UnicodeEncodeError in the index spinner on GBK consoles**
- **Found during:** Task 3 (first yoga smoke run at c74e860)
- **Issue:** A missing collection root leaves the progress task unfinished, so rich's final live frame rendered braille spinner glyphs and crashed with `UnicodeEncodeError` on yoga's GBK console instead of printing `Removed: 0`. The smoke's `index update (missing root preserved)` assertion failed for a real product reason, not a smoke bug.
- **Fix:** Added `spinner_name()` in `src/sif/utils/progress.py` to choose rich's ASCII `line` spinner when the output stream cannot encode the default braille frames; used it in `index update`, `watch` reconcile, and `RichProgressTracker`.
- **Files modified:** `src/sif/utils/progress.py`, `src/sif/cli/commands/index.py`, `src/sif/cli/commands/watch.py`, `tests/unit/utils/test_progress.py`
- **Verification:** new spinner-encodability unit tests; re-ran `make windows-smoke` on a clean yoga checkout at the fix commit — 8/8 PASS, including `PASS index update (missing root preserved)`.
- **Committed in:** `48759e2`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The fix was required for the plan's own missing-root assertion to be honest on a real GBK Windows console; no scope creep and no assertion was weakened.

## Issues Encountered

- The first smoke run (at c74e860) failed the missing-root assertion with a traceback on yoga. This was the product bug fixed by 48759e2, not a stale-checkout or smoke-logic problem. The prior run is not recorded as evidence.
- The plan required a human step to sync yoga; that precondition was satisfied before the re-run (`git status --porcelain` empty, HEAD equal to local HEAD).

## User Setup Required

None — yoga already has uv 0.13.1 and Python 3.12 installed; the target uses the committed frozen lock. Future `make windows-smoke` runs remain manual/on-demand per D-07.

## Next Phase Readiness

- ENG-02 is proven at the CLI surface; plan 17-06's pre-tag gate can grep `smoke_head: 48759e2c532d01d92a0deef08520a58c41115378` from this SUMMARY.
- Full Windows parity (daemon/service/flock) remains deferred to v2 (WIN-F1); this smoke is evidence of honest degradation, not support.
- Full suite green: 1651 passed, 1 skipped, 95.07% coverage (fail_under=90); `ruff check src tests scripts` and `ruff format --check src tests scripts` clean.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Completed: 2026-11-14*

## Self-Check: PASSED

- All four created/modified key files exist on disk.
- All three plan commits (`8b116b5`, `c74e860`, `48759e2`) are ancestors of HEAD.
- The machine-readable `smoke_head:` evidence line is present exactly once.
