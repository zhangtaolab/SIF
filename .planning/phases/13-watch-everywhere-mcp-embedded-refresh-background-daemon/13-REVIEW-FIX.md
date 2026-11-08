---
phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon
fixed_at: 2026-11-08T08:29:10Z
review_path: .planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/13-REVIEW.md
iteration: 2
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 13: Code Review Fix Report

**Fixed at:** 2026-11-08T08:29:10Z
**Source review:** `.planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/13-REVIEW.md`
**Iteration:** 2 (round 3 of fixes — the incremental re-review of the post-round-2
tree found 2 new findings, WR-01 + IN-01; both fixed this round)

**Summary:**
- Findings in REVIEW.md: 9 total (1 critical, 4 warnings, 4 info) in the original
  review; the round-3 incremental re-review re-verified all 9 fixes present and
  reported 2 NEW findings (1 warning, 1 info)
- Fixed in round 1 (fix_scope=critical_warning, commits 9acfd69, e3156da, 8039a3e, 191aa05, cd33b21 + lint 9756321): CR-01, WR-01, WR-02, WR-03, WR-04 — re-verified present again in round 3 (see "Previously Fixed" below); not re-applied, not re-committed
- Fixed in round 2 (fix_scope=all, commits 740b659, 1039c25, b1d7337, 6671ff8 + lint f418ff9): the original IN-01..IN-04
- Findings in scope this round (round 3): 2 (the re-review's WR-01 and IN-01)
- Fixed this round: 2
- Skipped this round: 0

**Mode note:** `workflow.use_worktrees=false`, so all edits and commits were made
directly in the main checkout on branch `dev`.

## Fixed Issues

### WR-01: `write_pid_file` uses a process-shared temp name — concurrent detaches race on the same inode

**Files modified:** `src/sif/utils/daemon.py`, `tests/unit/utils/test_daemon.py`
**Commit:** e1bb7d1
**Applied fix:** The temp artifact is now named per writer —
`.{path.name}.{os.getpid()}.tmp` instead of the fixed `.{path.name}.tmp` — so two
concurrent `sif watch --detach` armings on the same index never share a temp
inode (the module's contract explicitly lets two daemons run simultaneously);
each writer's create/write/rename sequence is independent, `os.replace` still
lands atomically, and the IN-03 symlink hardening is unchanged (temp still mode
0600, still unlinked on failure). New `TestPidFileConcurrentWriters` regression
tests: (1) the rename source name carries the writer PID (patched to a sentinel)
and no `.tmp` litter remains after the write; (2) the exact review interleaving —
writer B performs a FULL write (temp create + payload + its own replace) inside
writer A's rename window via an `os.replace` interleave hook, and both writes
succeed with a well-formed final file (last rename wins, no leaked temps). Both
tests were verified to FAIL against the pre-fix code (stash-and-run check) and
pass after it; daemon suite: 32 passed.

### IN-01: `_service_argv_tail` half-pins the depth — an unpinned BM25 install can still go embed in a divergent service environment

**Files modified:** `src/sif/cli/commands/watch.py`, `tests/unit/cli/test_watch_cmd.py`
**Commit:** f4057f6
**Applied fix:** `_service_argv_tail` now bakes the depth pin unconditionally:
`--embed` when `params.depth == "embed"`, and `--no-embed` for EVERY BM25
install — the plain install (no flags, ambient `bm25`) included. The pin is a
no-op at the BM25 runtime default and only bites when the service's own
environment diverges from what was installed (e.g. a later `launchctl setenv
SIF_WATCH_UPDATE_DEPTH=embed`, which persists for every LaunchAgent), so the
WR-03 invariant holds in full: an installed-BM25 service must never start
computing vectors — the service replays exactly what was installed. Because the
resolved `params.depth` alone now determines the tail, the `settings` /
`no_embed` parameters were dropped from `_service_argv_tail` (and from
`_run_install_service`, whose only other use of them was that call) — they were
the half-pin's inputs and would now be dead arguments (ruff ARG). Tests: the
two depth-matrix unit tests were merged into
`test_argv_tail_pins_the_installed_depth` (embed → `--embed`; bm25 →
`--no-embed`, unconditionally); new CLI-plumbing test
`test_install_plain_bm25_still_bakes_no_embed` proves a plain install (no depth
flags, ambient bm25) bakes `--no-embed` end-to-end through `watch_cmd`; the
WR-03 plumbing test (`test_install_bakes_no_embed_flag_under_ambient_embed_setting`)
is unchanged and still passes — the unconditional pin strictly subsumes it.
watch CLI suite: 35 passed.

(Round 2 below — the four Info findings of the original REVIEW.md; the round-1
CR/WR fixes are listed under Previously Fixed.)

### IN-01: `SIF_LOCK_WAIT_TIMEOUT` missing from the generated configuration reference; multi-field validators annotated on only their first field

**Files modified:** `scripts/generate_config_ref.py`, `docs/configuration.md` (generator-owned — produced by `make docs-generate`, never hand-edited)
**Commit:** 740b659
**Applied fix:** Registered `lock_wait_timeout` in the Database Settings section
of the generator's `SECTIONS` allowlist (the field lives under the "Database
settings" group in `src/sif/config/settings.py:36-41`), and extended
`get_validators` to register EVERY field a `@field_validator` decorator names —
splitting the decorator's argument list on commas and skipping keyword
arguments such as `mode="before"` — instead of recording only the first field.
Regenerated via `make docs-generate`; the docs diff is exactly two lines:
a new `SIF_LOCK_WAIT_TIMEOUT | float | 30.0 | ...` row under Database
Settings, and the `SIF_CACHE_DIR` row gaining `(validated by expand_path)`.
`docs/cli-reference.md` was regenerated and is byte-identical (no CLI change).
Verified the validator map directly (`db_path` and `cache_dir` both map to
`expand_path`; no stray `mode`/`before` keys) and ran `tests/test_docs.py`
(13 passed). Both parts of the finding's Fix section (the SECTIONS
registration, plus the marked-optional validator split) are applied.

### IN-02: Service-manager invocations have no timeout — a wedged launchctl/systemctl hangs the CLI forever

**Files modified:** `src/sif/utils/service.py`, `tests/unit/utils/test_service.py`
**Commit:** 1039c25
**Applied fix:** `_run` now passes `timeout=_RUN_TIMEOUT_SECONDS` (a new
module constant, 30.0) on every manager invocation and maps
`subprocess.TimeoutExpired` to a typed `ServiceCommandError` carrying the
failing argv and "timed out after 30s". Value rationale (documented at the
constant): the daemon module's `ps` probe (`_PS_TIMEOUT_SECONDS = 5.0`) sets
the everything-external-is-bounded precedent, but stopping a service
(`launchctl bootout`, `systemctl disable --now`) legitimately blocks on the
supervised watch process's own bounded shutdown (SIGTERM + flush joins can
take ~20s), so 30s bounds a wedged manager without false-positive-killing a
legitimate stop — matching the 30s the REVIEW.md itself suggested. New tests:
`_run` forwards the timeout kwarg (asserted via a kwargs-capturing runner) and
a timing-out bootstrap surfaces as `ServiceCommandError` naming
`launchctl bootstrap`. All fake runners in the suite already accept
`**kwargs`, so no other call sites needed changes. Test count: 14 passed.

### IN-03: `write_pid_file` follows a pre-planted symlink (hardening parity with `service._write_artifact`)

**Files modified:** `src/sif/utils/daemon.py`, `tests/unit/utils/test_daemon.py`
**Commit:** b1d7337
**Applied fix:** `write_pid_file` now writes the JSON payload to
`.<name>.tmp` (mode 0600, same open flags as before) and `os.replace`s it onto
the PID path — the exact write-temp-then-rename shape of
`service._write_artifact` (T-13-11). Rename does not follow symlinks, so a
pre-planted `<db>.watch.pid` symlink is atomically replaced with the real file
instead of redirecting the write and later removal to an arbitrary path; the
temp file is unlinked on any failure. New regression test: with a symlinked
PID file pointing at a victim file, the write replaces the symlink itself
(`is_symlink()` False), the victim's content is untouched, and the new regular
file round-trips through `read_pid_file`. The existing round-trip test
(content + mode 0600) still passes unchanged. Test count: 30 passed.

### IN-04: `SESSION_MAX_AGE` is dead — sessions never expire by age

**Files modified:** `src/sif/mcp/transports/http.py`
**Commit:** 6671ff8
**Applied fix:** Grep across src/tests/docs/scripts confirmed
`SESSION_MAX_AGE = 3600` is referenced only at its definition — eviction is
count-only (`SESSION_MAX_COUNT` LRU), so the constant implies an expiry
behavior that does not exist. Removed the constant (the remedy the round's
directive chose among the REVIEW.md's two options). The `created` /
`last_accessed` session-dict bookkeeping was deliberately RETAINED: it is
written on every request and its shape is asserted by
`tests/unit/mcp/test_transports_http.py` (lines 235, 243), so it is live
observable metadata rather than a dead constant; implementing age-based
expiry instead would have been a behavior change beyond this finding's scope.
Zero remaining references repo-wide; transport tests: 27 passed.

### Lint cleanup (post-gate)

**Files modified:** `tests/unit/utils/test_daemon.py`
**Commit:** f418ff9
**Applied fix:** `ruff format` collapse of the new IN-03 test's signature to
one line (99 chars), surfaced by the full-suite gate after the per-finding
commits. Behavior-neutral; the daemon suite re-passed (30) after the reformat.

## Previously Fixed (prior round — verified still present this round)

Each was spot-checked in the current tree by grepping for its signature change
before this round's work began; none were re-edited or re-committed.

- **CR-01** (commit 9acfd69): `mcp_watch_lifespan` is a lifespan factory —
  `def mcp_watch_lifespan(db_path: str) -> Callable[[Any], Any]` at
  `src/sif/mcp/watch_host.py:190`.
- **WR-01** (commit e3156da): `worker_joined()` exists on `FileWatcher`
  (`watcher.py:478`) and gates the shutdown checkpoint in both hosts
  (`watch.py:112`, `watch_host.py:181`).
- **WR-02** (commit 8039a3e): the missing-root disappear branch stops/joins
  the debouncer with `_JOIN_TIMEOUT_SECONDS` parity (`watcher.py:450-476`).
- **WR-03** (commit 191aa05): `_service_argv_tail` takes `settings` +
  `no_embed` and bakes `--no-embed` when the ambient setting is embed
  (`watch.py:428,450`).
- **WR-04** (commit cd33b21): `_kill_detached_group` SIGKILLs the detached
  session on handshake timeout (`daemon.py:212,325`) with the honest
  terminated-with-remedy error message (`daemon.py:345`).

## Verification

Per-fix: Tier 1 (re-read / git-diff of every modified section) + Tier 2
(`ast.parse` syntax checks on each edited Python file; targeted pytest runs —
docs 13, service 14, daemon 30, http transports 27 — all green before each
commit).

**Full quality gate (after all fixes, run in the MAIN CHECKOUT — no worktree
was created, `workflow.use_worktrees=false`; numbers are reproducible from
this tree):**

- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` — **1164 passed, 1 skipped**
  (skip is the pre-existing opt-in `SIF_TEST_LIVE_LAUNCHD` live launchd proof),
  coverage 94.58% (fail_under=90 met)
- `ruff check src tests` — All checks passed
- `ruff format --check src tests` — 172 files already formatted
- `ty check src/sif` — All checks passed

The full gate was re-run on the final tree (after the f418ff9 whitespace-only
reformat) so the numbers above describe exactly the tree at HEAD.

**Round 3 gate (WR-01 + IN-01; also run in the MAIN CHECKOUT, numbers
reproducible from this tree):**

- Per-fix: Tier 1 (re-read of every modified section) + Tier 2 (`ast.parse`
  on each edited Python file; scoped pytest runs — daemon 32, watch CLI 35,
  service + real-subprocess daemon e2e 19 — all green before each commit).
  Both new daemon regression tests were additionally proven to fail against
  the pre-fix code via a stash-and-run check.
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` — **1233 passed, 1 skipped**
  (the pre-existing opt-in `SIF_TEST_LIVE_LAUNCHD` live launchd proof),
  coverage 94.55% (fail_under=90 met)
- `ruff check src tests` — All checks passed
- `ruff format --check src tests` — 176 files already formatted
- `ty check src/sif` — All checks passed

## Skipped Issues

None in either round — all in-scope findings were fixed. Round 3: both of the
re-review's new findings (WR-01, IN-01) were fixed as described above.

---

_Fixed: 2026-11-08T08:29:10Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
