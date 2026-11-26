# Phase 17 — UI Review

**Audited:** 2026-11-24 (second in-place refresh, re-verified at HEAD `44db94d`; earlier passes: 2026-11-14 original, 2026-11-24 refresh at `b19916f`)
**Baseline:** No UI-SPEC.md exists for this phase. Abstract 6-pillar standards, applied only where a user-facing surface exists.
**Screenshots:** not captured — no frontend and no project dev server. Re-checked at this refresh: ports 3000/5173 were closed (`000`); port 8080 answered but is an unrelated SearXNG instance (`<title>searxng</title>`, meta description "SearXNG — a privacy-respecting, open metasearch engine"), identified and rejected as evidence rather than screenshotted as if it were SIF.
**Interaction captures:** off (`workflow.ui_interaction_capture` is false)

---

## Revision Note (2026-11-24, second refresh at `44db94d`)

**Why:** since the previous refresh (`de586c7`, verified at `b19916f`) gap-closure plan 17-10 restored the 8-cell CI matrix and the every-branch push trigger (`10a9685`), brought the eight-cell wording back in three guides (`a321eaa`), and re-pinned the two CI guard tests. Five non-`.planning` files changed; nothing under `src/` or `scripts/` moved. **Scores are unchanged (7/8 applicable subtotal).** What differs from the previous report:

- **Kept — both carried findings still hold.** The Copywriting WARNING on `SearchOptions` (IN-03, `open`) and the observation on dated test counts (3,234 in the guides against 3,261 collected at HEAD; IN-09, `open`) were re-verified line by line.
- **Dropped — nothing.** No finding in the previous report was fixed by the restore, because the previous report had not reported the CI wording at all.
- **Added, already closed — the CI wording the previous refresh missed.** At `b19916f` the three guides described a six-cell matrix and a `main`-only push trigger, contradicting CONTEXT D-01/D-03 (`17-CONTEXT.md:24`, `:26`) and archived success criterion 1 (`.planning/milestones/v1.2-ROADMAP.md:76`). The previous refresh listed `docs/testing.md` and `docs/development.md` as examined but reported only the count drift. The code review recorded it (WR-02, IN-10, IN-11) and plan 17-10 fixed it. Re-verified at HEAD: the workflow and all twelve wording sites agree, and no six-cell or `main`-only Test-Matrix wording remains in any tracked file outside `.planning/`. Recorded for traceability; not an open defect and no score effect.
- **Corrected — the `--stop` claim was wrong.** The previous report said "`--detach/--stop` on the wrong platform exits non-zero". `--stop` has no platform guard and is a deliberate soft, idempotent notice (`src/sif/cli/commands/watch.py:408-428`). The non-zero refusals are `--detach`, `--install-service`, and `--uninstall-service`.
- **Corrected — the phase-diff census was wrong.** The previous "42 `.py`, 39 `.md`, 3 `.yml`, 2 `.toml`" could not be reproduced by any method or end-commit. The range `e78a7d5^..8e4090d` changes 30 `.py`, 21 `.md`, 2 `.yml`, 1 `.toml`, 1 `.lock`, the `Makefile`, and 4 deleted junk blobs. The conclusion (zero frontend files) is unaffected.
- **Added — one disclosed observation under Experience Design.** `sif watch` accepts `--embed` and `--no-embed` together and embed silently wins (IN-06, `open`). It predates the phase and sits in lines the phase did not touch, so it is attributed and not deducted; the previous "no defects" wording is replaced by a claim scoped to what the phase built.
- **Added — one observation under Copywriting.** No test guards the guides' CI wording (confirmed empirically; see Pillar 1).
- **Scoped — the Rich-escaping positive** now names the index event path only; the same defect class remains open in `sif ls` and `sif collection ls/show` (WR-10), outside this phase.
- **Tightened — line references.** `scripts/windows_smoke.py:33-65` → `:35-36`, `:60-62`; `:35-41` → `:34`, `:45-47`, `:170-171`; `tests/unit/utils/test_daemon.py:603-610` → `:602-612`.

**Earlier revision (2026-11-24, first refresh at `b19916f`) — still true at HEAD:** dropped the `docs/testing.md` staleness WARNING (page regenerated 2026-11-18; `docs/testing.md:131`, `:142`; `deferred-items.md:14` records `resolved`); added the `SearchOptions` WARNING; credited the WR-01/WR-08 fixes (`b0d45bf`); did not carry the "search models" half of IN-03 (`src/sif/models/document.py:70` defines `DocumentSearchResult`).

---

## Applicability Gate

Phase 17 (Engineering Foundation: CI Matrix + Hygiene + PyPI), including gap-closure plan 17-10, introduced **no frontend surface**. Verified again at HEAD, not assumed:

- The phase diff (`e78a7d5^..8e4090d`, 24 commits) changes 60 paths: 30 `.py`, 21 `.md` (11 under `.planning/`, 10 docs), 2 `.yml`, 1 `.toml`, 1 `.lock`, the `Makefile`, and 4 deleted `MagicMock/mock/*` blobs (`git diff --name-only`). **Zero** `.tsx`, `.jsx`, `.css`, or `.scss`.
- The gap-closure delta (`de586c7..HEAD`, outside `.planning/`) is 5 paths: 1 `.yml`, 3 `.md`, 1 `.py`.
- At HEAD the repository has no `package.json`, `vite.config.*`, `tailwind.config.*`, `postcss.config.*`, or `components.json`, and no `.tsx`/`.jsx`/`.css`/`.scss` outside `htmlcov/` and `.venv/`.
- SIF's HTTP surface is the MCP transport (JSON/SSE), not a rendered UI.
- No `UI-SPEC.md` exists anywhere under `.planning/`.
- None of the ten plans' stated deliverables is a user interface. The phase's only user-facing copy under `src/` is three refusal strings (Pillar 1).

Consequently, **Visuals, Color, Typography, and Spacing have no surface to audit**. They are marked N/A rather than awarded unearned 4/4 scores. Two pillars do have a real user-facing analogue and are scored against it: **Copywriting** (CLI refusal/notice copy and the developer docs this phase edited) and **Experience Design** (CLI interaction and failure states).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | CLI refusal and notice copy is specific cause+remedy and the three CI guides now match the restored workflow; `docs/api-reference.md:225-232` still files the core `SearchOptions` under "Models Module" |
| 2. Visuals | N/A | No rendered UI; the terminal spinner fix is state/rendering robustness, not a visual hierarchy contract |
| 3. Color | N/A | No color system, CSS tokens, or UI surface; `NO_COLOR`/`FORCE_COLOR` handling is test hermeticity, not color design |
| 4. Typography | N/A | No type scale, font sizes/weights, or UI surface |
| 5. Spacing | N/A | No layout, spacing scale, or UI surface |
| 6. Experience Design | 4/4 | Windows degradation refusals are honest, cause+remedy, traceback-free, unit-tested at both boundaries, proven 8/8 on real Windows, and hardened by the phase-review fixes; one pre-existing `sif watch` flag conflict (IN-06) is disclosed below, not deducted |

**Overall: N/A / 24 — this is not a frontend phase.** Applicable-pillar subtotal: **7/8**, unchanged by plan 17-10. A numeric /24 would either inflate four non-existent surfaces to 4/4 or punish them with 1/4; both would misstate the evidence.

---

## Top 3 Priority Fixes

1. **WARNING — `docs/api-reference.md` misattributes a core dataclass to `sif.models`** — a reader looking for `SearchOptions` in the Models Module page is told `from sif.core.models import SearchOptions` two lines under a `## Models Module` heading, so a Phase 17 deletion (`src/sif/models/search.py`) left the reference page disagreeing with the package layout; contributors grep the wrong module. **Fix:** move the `SearchOptions` block (`docs/api-reference.md:227-266`) under a `## Core Module` heading (the same class is already shown correctly at `:761`), and re-run the doc generator so its Models Module section lists only `sif.models` classes.
2. **OBSERVATION — dated test counts have drifted 27 tests since the page was written** — `docs/testing.md:4`, `:202`, and `docs/development.md:305` say 3,234 collected; HEAD collects **3,261** (`pytest --collect-only -q`), and `17-VALIDATION.md:26` records 3,261 collected / 3,260 passed / 1 skipped. Both pages date or hedge the number, so this is drift from later work on this branch, not a false claim about the phase. **Fix (optional):** regenerate the docs, or replace the literal with the command that prints it.
3. **OBSERVATION — nothing in `pytest` guards the CI wording in the three guides** — the guards pin the workflow's shape, not the prose describing it, so a docs-only edit could make the guides disagree with `test-matrix.yml` again without a red build (see Pillar 1 for the check that was run). **Fix (optional):** add a small text guard alongside `tests/test_ci_workflows.py` that fails on six-cell or `main`-only Test-Matrix wording in `docs/contributing.md`, `docs/development.md`, and `docs/testing.md`, or accept the gap and leave it recorded (`17-VALIDATION.md:119`).

No fix is proposed for Visuals/Color/Typography/Spacing: there is no rendered UI or design system in this phase, and manufacturing UI work to fill this template would be wrong.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Positives (specific, actionable CLI copy — re-verified at HEAD; unchanged since `b19916f`):**

- `src/sif/utils/daemon.py:253-258` — the library boundary refuses with cause and remedy: `detached mode requires POSIX fork (os.fork); use the foreground watch on Windows`. It fires before `os.pipe()`/`os.fork()`.
- `src/sif/cli/commands/watch.py:359-366` — the CLI boundary raises `--detach requires POSIX fork support and is not available on Windows; run `sif watch` in the foreground instead.`
- `src/sif/cli/commands/watch.py:438-442` — the win32 service path refuses with `the watch service is not supported on Windows; run `sif watch` in the foreground instead`, before any `systemctl`/`launchctl` probe. Both service commands reach it (`:476` install, `:501` uninstall), so they share one message.
- `src/sif/cli/commands/watch.py:421-426` — a cross-user PID produces `Watch daemon (PID N) belongs to another user; not stopped. Run as its owner to stop it.` instead of a `PermissionError` traceback (WR-08).
- `scripts/windows_smoke.py:35-36` — matchers require both the constraint and the remedy (`_DETACH_REFUSAL_PARTS`, `_SERVICE_REFUSAL_PARTS`); `:60-62` `looks_like_traceback()` rejects leaked tracebacks, so vague or crash-only copy would fail the smoke.
- These three refusal strings are the only user-facing copy the phase added under `src/`: its diff over `src/sif/cli`, `src/sif/utils`, and `src/sif/mcp` touches four files and adds no other message.
- No generic labels (`Submit`, `Click Here`, `went wrong`, `try again`, `error occurred`) were found in `src/sif/cli` or `src/sif/utils`.

**Re-verified after plan 17-10 — the CI guides agree with the workflow:**

- `.github/workflows/test-matrix.yml:5-6` declares `push: branches: ['**']` and a bare `pull_request:`; `:22-24` is `os` × `python-version` with no `exclude` (8 cells); `:20` `fail-fast: false`; `:13` `cancel-in-progress: true`. This matches decisions D-01, D-03, and D-04 (`17-CONTEXT.md:24`, `:26`, `:27`).
- Twelve wording sites were read against the workflow's actual steps: `docs/contributing.md:365`, `:400`, `:402`, `:405`, `:407`; `docs/development.md:609`, `:732`, `:751`, `:769-770`; `docs/testing.md:130`, `:212`, `:214`. Sync and test commands, the 30-minute per-cell timeout, and the `contents: read` permission all agree.
- The two guards were re-pinned to derive what they protect: `tests/test_ci_workflows.py:190` rebuilds the 2 × 4 product from the declared lists and rejects `exclude`/`include`/`if`/`continue-on-error` in the test job (`:31`); `:284` pins the `['**']` push trigger, a bare `pull_request:`, and the absence of `tags:`.
- A scan of tracked files outside `.planning/` finds no six-cell or `main`-only Test-Matrix wording. The only `branches: [main]` hit is `.github/workflows/docs.yml:14`, which is correct for the separate Docs Validation workflow.
- `docs/changelog.md` is silent on both the reduction and the restoration, so it makes no false claim (plan 17-10's scope gate allowed only its five files).

**WARNING — reference docs misattribute `SearchOptions` to `sif.models`:**

- `docs/api-reference.md:225` opens `## Models Module`; `:227` adds `### Search Options`; `:229-232` then shows `#### Class: SearchOptions` with `from sif.core.models import SearchOptions`. The block runs to `:266`; the next heading, `### Collection Models`, is at `:268`.
- `sif.models` does not export `SearchOptions`; it is defined at `src/sif/core/models.py:348`. The sibling entries in that section (`CollectionCreate`/`CollectionUpdate`/`CollectionResponse`) are genuinely `sif.models` classes, so the section reads as authoritative and is wrong only for this one class.
- Source of the defect: plan 17-01 deleted `src/sif/models/search.py`, and the reference page's Models Module section was never re-partitioned. Tracked as IN-03 from the 2026-11-14 review, still `open` in `17-REVIEW-DISPOSITION.md:131`; the 2026-11-24 review body does not re-state it (`17-REVIEW.md:87`).
- Scored 3/4 rather than 4/4 on this alone: it is one concrete, verifiable user-facing inaccuracy in docs this phase edited, and the rest of the copy checked out.

**Observations (not deducted):**

- Test counts in `docs/testing.md:4`, `:202` and `docs/development.md:305` are 3,234 against 3,261 collected at HEAD. Both are dated (`macOS, 2026-11-18`) or hedged (`at the time of writing`), so they were true when written. Tracked as IN-09 (`17-REVIEW.md:156-161`, `open`).
- `docs/architecture.md:57` and `:751` still say `models/` holds "search schemas"/"search models". Checked: `src/sif/models/document.py:70` defines `DocumentSearchResult`, so the prose is accurate at HEAD, not residual.
- **The CI wording has no regression guard.** The four-module battery (`tests/test_ci_workflows.py`, `test_docs.py`, `test_hygiene.py`, `test_release_metadata.py`) was run on a `git archive HEAD` export: **66 passed, 1 skipped**. After a doc-only edit restoring six-cell wording in all three guides it still reported **66 passed, 1 skipped**. The same harness does catch a workflow regression: re-adding the two `exclude` entries fails `test_matrix_declares_eight_cells` (**1 failed, 17 passed**). So the workflow shape is protected and the prose describing it is not; `17-VALIDATION.md:119` records the same.
- Phase records are not yet re-derived from the restored tree: `17-VERIFICATION.md:120` still shows truth 11 as failed against the six-cell workflow (`status: gaps_found`, `:4`), and the WR-02, IN-10, and IN-11 rows are still `open` in `17-REVIEW-DISPOSITION.md`. These are planning records, not user-facing docs; they are listed so nobody reads them as contradicting the guides. `17-10-SUMMARY.md:263` records the verifier re-run as open.

### Pillar 2: Visuals (N/A)

No rendered UI, component hierarchy, icon-only controls, or aria-label surface exists in this phase. The one terminal-output change — the encodability-aware spinner (`src/sif/utils/progress.py:20-38`) — is behavior and failure robustness, scored under Experience Design. No UI finding is invented here.

### Pillar 3: Color (N/A)

No CSS custom properties, Tailwind classes, theme tokens, or rendered color surface were introduced or modified. `NO_COLOR`/`FORCE_COLOR` appear only in test/CI hermeticity (`env -u FORCE_COLOR NO_COLOR=1`) and do not constitute a color design contract. Rich color tags (`[yellow]`, `[dim]`, `[red]`) are inline CLI status styling with no palette or 60/30/10 distribution to audit.

### Pillar 4: Typography (N/A)

No font sizes, weights, or type-scale classes exist; the project is a Python CLI/library with Markdown docs.

### Pillar 5: Spacing (N/A)

No layout, spacing scale, padding/margin/gap classes, or visual composition surface exists.

### Pillar 6: Experience Design (4/4)

State coverage and failure behavior on the CLI surface the phase built are strong and proven:

- **Error states at both boundaries:** the library `detach()` guard (`src/sif/utils/daemon.py:253-258`) replaces a raw `AttributeError`, and the CLI guard (`src/sif/cli/commands/watch.py:359-366`) keeps the user from ever reaching fork work. The win32 service refusal lives in the shared `_service_manager` site (`watch.py:438-442`), so install and uninstall both get the same message before a service-manager probe.
- **Tests pin the interaction contract, not just the exception:** `tests/unit/utils/test_daemon.py:602-612` asserts the message names POSIX fork and the foreground remedy; `tests/unit/cli/test_watch_cmd.py:395` asserts the CLI refusal text. The whole audited guard subset is green at HEAD — `pytest --no-cov` over `test_daemon.py`, `test_watch_cmd.py`, `test_progress.py`, `test_windows_smoke_script.py`, `test_hygiene.py`, `test_release_metadata.py`, `test_ci_workflows.py` → **145 passed**.
- **Failure is reported, never silently absorbed:** a handshake timeout SIGKILLs the detached session before reporting (`src/sif/utils/daemon.py:245-246`), and `--detach`, `--install-service`, and `--uninstall-service` on the wrong platform exit non-zero with the cause and the remedy rather than a "maybe detached". `--stop` is different by design: it has no platform guard and resolves to a soft, idempotent notice (`watch.py:408-428`), which is the stop-idempotence contract rather than a refusal.
- **Data-preserving degradation:** the missing-root `index update` path reports `Removed: 0` plus the all-documents-preserved warning (`scripts/windows_smoke.py:34`, asserted at `:170-171`), verified by the smoke matchers (`:203`, `:233`, `:238`) and the recorded 8/8 PASS yoga run at HEAD `48759e2` (`17-04-SUMMARY.md:136-153`).
- **A real interaction bug was found and fixed:** the first yoga run exposed a `UnicodeEncodeError` on GBK consoles when the index spinner rendered braille frames, turning a successful command into a traceback. `src/sif/utils/progress.py:20-38` now selects the ASCII `line` spinner when the stream cannot encode the default frames; `src/sif/cli/commands/index.py:114` uses it. Tests cover UTF-8, GBK, ASCII, unknown-encoding, and no-encoding streams (`tests/unit/utils/test_progress.py:115-132`).
- **Index event rendering no longer corrupts or crashes on user data:** index event payloads (filenames) are Rich-escaped before printing (`src/sif/cli/commands/index.py:188`, `:192`, `:194`), so a bracketed filename is preserved and a stray closing tag cannot raise `MarkupError` (WR-01). This is scoped to the index event path: the same defect class is still open in `sif ls` and `sif collection ls/show` (`src/sif/cli/commands/ls.py:67`, `:74`; WR-10, `open`), code that is not part of this phase's deliverable.
- **No destructive-action gap:** the smoke's post-delete assertion proves a missing collection root preserves all documents instead of mass-deleting.
- **Accepted limitation, not a defect:** `make windows-smoke` is manual/on-demand by decision D-07 (`17-CONTEXT.md:32`; yoga is a user machine). The unit-level guards and `tests/test_windows_smoke_script.py` keep the matcher contract honest between runs.

**Observation — disclosed, not deducted (IN-06, `open`):** `_effective_depth` (`src/sif/cli/commands/watch.py:253-264`) resolves `--embed` first, and both flags are independent `is_flag` options (`:546-555`), so `sif watch --embed --no-embed` is accepted and embed silently wins. `tests/unit/cli/test_watch_cmd.py:262-275` pins the single-flag and default cases but not the both-flags case. It is not deducted because it predates the phase: the phase's four hunks in `watch.py` (`@@ -56,0 +57`, `@@ -195 +196`, `@@ -357,0 +359,8`, `@@ -417 +426,11`) do not touch it, and the logic is identical at `e78a7d5^`. It is listed because the previous report described the CLI surface as having no defects, which is true only of what the phase built. A reader who scores the whole `sif watch` command rather than the phase's delivery would put this pillar at 3/4 (subtotal 6/8).

**No Experience Design change from plan 17-10:** it touched a CI workflow, a guard test, and three guides; none is an interactive surface.

---

## Registry Safety

Skipped — `components.json` is absent (shadcn not initialized) and no third-party UI registry exists. No Registry Safety section is warranted.

---

## Files Audited

**Audit path:** the `gsd-ui-auditor` role was executed inline from `~/.zcode/agents/gsd-ui-auditor.md`; this runtime exposes no Agent tool.

**Directly examined at HEAD `44db94d` (source, tests, config, docs):**

- `src/sif/utils/daemon.py`
- `src/sif/cli/commands/watch.py`
- `src/sif/utils/progress.py`
- `src/sif/cli/commands/index.py`
- `src/sif/cli/commands/ls.py` (WR-10 cross-check only)
- `src/sif/models/__init__.py`, `src/sif/models/document.py`, `src/sif/core/models.py` (to test the "search schemas" and `SearchOptions` claims)
- `scripts/windows_smoke.py`
- `tests/unit/utils/test_daemon.py`
- `tests/unit/cli/test_watch_cmd.py`
- `tests/unit/utils/test_progress.py`
- `tests/test_ci_workflows.py` (re-pin diff and HEAD state)
- `.github/workflows/test-matrix.yml` (full), trigger blocks of `docs.yml` and `publish.yml`
- `docs/testing.md`, `docs/contributing.md`, `docs/development.md` (CI sections in full)
- `docs/api-reference.md`, `docs/architecture.md` (cited sections)
- `docs/installation.md`, `docs/models.md`, `docs/changelog.md`, `README.md`, `DESIGN.md` (phase-introduced statements only)

**Phase artifacts reviewed:**

- `17-CONTEXT.md` (decisions D-01, D-03, D-04, D-06, D-07)
- `17-10-PLAN.md` (objective, both tasks, verification gates) and `17-10-SUMMARY.md` (full)
- `17-04-SUMMARY.md` (recorded yoga run); the stated deliverable of each of `17-01-SUMMARY.md` … `17-09-SUMMARY.md`
- `17-REVIEW.md` (narrative findings) and `17-REVIEW-DISPOSITION.md` (full)
- `17-VALIDATION.md`, `17-VERIFICATION.md` (matrix and test-count rows), `deferred-items.md`
- `.planning/milestones/v1.2-ROADMAP.md` § "Phase 17" (success criteria)

The nine earlier plans and summaries were not re-read in full for this refresh: none of the files they delivered changed since the first refresh, and the phase diff itself was used as the primary source for what they shipped.

**Frontend-surface scan (negative evidence):**

- No `package.json`, `vite.config.*`, `tailwind.config.*`, `postcss.config.*`, `components.json`, `.tsx`, `.jsx`, `.css`, or `.scss` outside `htmlcov/` and `.venv/`.
- No `UI-SPEC.md` anywhere under `.planning/`.
- No project dev server: 3000 and 5173 closed; 8080 is an unrelated SearXNG.

**Commands run:** `pytest` from PATH (9.1.1) with `env -u FORCE_COLOR NO_COLOR=1`.

- `pytest --collect-only -q` → 3,261 collected, no collection errors.
- The 7-file guard subset above with `--no-cov` → 145 passed.
- The four-module battery on a `git archive HEAD` export → 66 passed, 1 skipped; unchanged after a doc-only six-cell regression; guard module alone 18 passed on the restored workflow and 1 failed, 17 passed with the two `exclude` entries re-added. The export was deleted afterwards.
- `.planning/ui-reviews/.gitignore` was re-verified as complete before any capture attempt (the gate wrote nothing); no captures were made, so nothing was stored.
