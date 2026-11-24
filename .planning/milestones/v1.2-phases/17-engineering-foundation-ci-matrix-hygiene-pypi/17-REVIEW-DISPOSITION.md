---
phase: 17
review: 17-REVIEW.md
titles: json
findings:
  - id: IN-12
    severity: info
    disposition: open
    title: "Eight-cell guard pins the declared axes but not that the cells run on `matrix.os` and `matrix.python-version`"
  - id: WR-10
    severity: warning
    disposition: open
    title: "User-controlled values reach Rich markup unescaped in `sif ls` and `sif collection ls/show` — silent text loss and `MarkupError` tracebacks"
  - id: WR-11
    severity: warning
    disposition: open
    title: "`sif ls` splits raw document paths, so the tree is flat on Windows"
  - id: WR-12
    severity: warning
    disposition: open
    title: "Impossible-state guard — the `if not coll: continue` branch in `sif ls` is unreachable"
  - id: IN-07
    severity: info
    disposition: open
    title: "`symlink_or_skip` converts every `OSError` into a skip, hiding broken test setup"
  - id: IN-08
    severity: info
    disposition: open
    title: "`l2_normalize` docstring states the zero/non-finite rule twice"
  - id: IN-09
    severity: info
    disposition: open
    title: "`docs/testing.md` reports a collected-test total that is stale at HEAD"
  - id: IN-10
    severity: info
    disposition: fixed
    title: "The six-cell guard pins the exclusions but not the OS list or the cell count"
  - id: IN-11
    severity: info
    disposition: fixed
    title: "Phase 17 success criterion 1 no longer holds literally at HEAD (post-phase CI reduction)"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Windows smoke has no platform guard — an accidental POSIX run installs a persistent launchd/systemd service and forks a daemon"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Shared progress renderer passes user data through Rich markup unescaped — silent text loss and `MarkupError` crashes"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "CI documentation states the opposite of the workflow this phase added"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Docs still describe test infrastructure deleted by this phase"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "`examples/quickstart.py` is broken at runtime and prints commands that do not exist"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "Documented local quality gates fail on a clean checkout"
  - id: WR-06
    severity: warning
    disposition: open
    title: "Publish jobs have no job-level `timeout-minutes`"
  - id: WR-07
    severity: warning
    disposition: open
    title: "Publish workflow has no concurrency guard"
  - id: WR-08
    severity: warning
    disposition: fixed
    title: "`sif watch --stop` can crash with `PermissionError` instead of failing closed"
  - id: WR-09
    severity: warning
    disposition: open
    title: "Impossible-state guard — unreachable `if not coll: continue` in both index commands"
  - id: IN-01
    severity: info
    disposition: open
    title: "New CI guards assert text, not the properties their names claim"
  - id: IN-02
    severity: info
    disposition: open
    title: "The documentation command guard is blind to most top-level commands and lists a nonexistent group"
  - id: IN-03
    severity: info
    disposition: open
    title: "Stale counts and a stale \"search models\" claim remain in the docs"
  - id: IN-04
    severity: info
    disposition: open
    title: "Release-path inputs are not reproducible or hard-pinned"
  - id: IN-05
    severity: info
    disposition: open
    title: "No automated gate ties the published tag to a green Test Matrix run"
  - id: IN-06
    severity: info
    disposition: open
    title: "`--embed` and `--no-embed` together are accepted; embed silently wins"
open: 17
total: 25
recorded: 2026-11-24T14:42:07.948Z
---

# Phase 17: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| IN-12 | info | open | - |
| WR-10 | warning | open | - (not in the current review) |
| WR-11 | warning | open | - (not in the current review) |
| WR-12 | warning | open | - (not in the current review) |
| IN-07 | info | open | - (not in the current review) |
| IN-08 | info | open | - (not in the current review) |
| IN-09 | info | open | - (not in the current review) |
| IN-10 | info | fixed | fix 10a9685 (guard derives the 2 x 4 product from both lists and rejects skip keys; verified by mutation at 1984c45) (not in the current review) |
| IN-11 | info | fixed | fix 10a9685 (workflow byte-identical to the phase original; declaration half only, the runs-green half is pending in 17-VALIDATION Manual-Only row 7) (not in the current review) |
| CR-01 | critical | fixed | fix b0d45bf (not in the current review) |
| WR-01 | warning | fixed | fix b0d45bf (not in the current review) |
| WR-02 | warning | fixed | fix 42e1acd, e539795 (contradictory CI sentences removed 2026-11-17); a321eaa re-aligned cell and trigger wording; the suggested DOCS_FILES guard was not added (not in the current review) |
| WR-03 | warning | open | - (not in the current review) |
| WR-04 | warning | fixed | fix b0d45bf (not in the current review) |
| WR-05 | warning | fixed | fix b0d45bf (not in the current review) |
| WR-06 | warning | open | - (not in the current review) |
| WR-07 | warning | open | - (not in the current review) |
| WR-08 | warning | fixed | fix b0d45bf (not in the current review) |
| WR-09 | warning | open | - (not in the current review) |
| IN-01 | info | open | - (not in the current review) |
| IN-02 | info | open | - (not in the current review) |
| IN-03 | info | open | - (not in the current review) |
| IN-04 | info | open | - (not in the current review) |
| IN-05 | info | open | - (not in the current review) |
| IN-06 | info | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
