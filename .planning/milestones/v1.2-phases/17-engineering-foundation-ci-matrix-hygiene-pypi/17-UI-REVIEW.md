# Phase 17 — UI Review

**Audited:** 2026-11-24 (refresh of the 2026-11-14 audit, re-verified at HEAD `b19916f`)
**Baseline:** No UI-SPEC.md exists for this phase. Abstract 6-pillar standards, applied only where a user-facing surface exists.
**Screenshots:** not captured — no frontend and no project dev server. Ports 3000/5173 were closed (`000`); port 8080 answered but is an unrelated SearXNG instance (`<title>searxng</title>`, `searxng` meta description), rejected as evidence rather than screenshotted as if it were SIF.
**Interaction captures:** off (`workflow.ui_interaction_capture` is false)

---

## Revision Note (2026-11-24)

Refreshed in place. Score totals are unchanged; what changed is the evidence behind them.

- **Dropped — the `docs/testing.md` staleness WARNING no longer holds.** The page was regenerated on 2026-11-18. It now reports 3,234 collected tests (not 1,629), lists neither `tests/factories.py` nor `tests/unit/test_search.py` in the layout tree, and mentions the factory module only as removed (`docs/testing.md:142`), with `tests/test_hygiene.py` pinning its absence (`docs/testing.md:131`). `deferred-items.md` records the item as **resolved**. `grep` finds no `sample_search_options`, `sample_search_result(s)`, `SearchOptionsFactory`, or `SearchResultFactory` in the guide.
- **Added — one Copywriting WARNING that survived the docs regeneration:** `docs/api-reference.md` still files `SearchOptions` (imported from `sif.core.models`) under `## Models Module`. This is finding IN-03 of `17-REVIEW.md`, still `open` in `17-REVIEW-DISPOSITION.md`.
- **Added — two Experience Design positives not credited before:** Rich-markup escaping on index event rendering (WR-01) and the `permission_denied` stop path (WR-08), both fixed in `b0d45bfa`.
- **Refreshed — all line references.** Post-phase commits (`b0d45bfa`, `446b4247`) moved the guards; stale line numbers were corrected rather than carried.
- **Not carried — the "search models" half of IN-03.** `sif/models/document.py:70` defines `DocumentSearchResult`, so `docs/architecture.md:57` and `:751` describing `models/` as holding search schemas is accurate at HEAD. Only the api-reference placement is wrong.

---

## Applicability Gate

Phase 17 (Engineering Foundation: CI Matrix + Hygiene + PyPI) introduced **no frontend surface**. Verified again at HEAD, not assumed:

- The phase diff (`e78a7d5^..8e4090dc`) changes 42 `.py`, 39 `.md`, 3 `.yml`, 2 `.toml`, 1 `.lock`, the `Makefile`, and removes tracked junk (4 `MagicMock/mock/*` blobs). **Zero** `.tsx`, `.jsx`, `.css`, or `.scss`.
- At HEAD the repository has no `package.json`, `vite.config.*`, `tailwind.config.*`, `postcss.config.*`, or `components.json`, and no `.tsx`/`.jsx`/`.css`/`.scss` outside `htmlcov/` and `.venv/`.
- SIF's HTTP surface is the MCP transport (JSON/SSE), not a rendered UI.
- No `UI-SPEC.md` exists anywhere under `.planning/`.

Consequently, **Visuals, Color, Typography, and Spacing have no surface to audit**. They are marked N/A rather than awarded unearned 4/4 scores. Two pillars do have a real user-facing analogue and are scored against it: **Copywriting** (CLI refusal/notice copy and the developer docs this phase edited) and **Experience Design** (CLI interaction and failure states).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | CLI refusal and notice copy is specific cause+remedy; `docs/api-reference.md:225-232` still files the core `SearchOptions` under "Models Module" |
| 2. Visuals | N/A | No rendered UI; the terminal spinner fix is state/rendering robustness, not a visual hierarchy contract |
| 3. Color | N/A | No color system, CSS tokens, or UI surface; `NO_COLOR`/`FORCE_COLOR` handling is test hermeticity, not color design |
| 4. Typography | N/A | No type scale, font sizes/weights, or UI surface |
| 5. Spacing | N/A | No layout, spacing scale, or UI surface |
| 6. Experience Design | 4/4 | Windows degradation refusals are honest, cause+remedy, traceback-free, unit-tested at both boundaries, proven 8/8 on real Windows, and hardened further by the phase-review fixes |

**Overall: N/A / 24 — this is not a frontend phase.** Applicable-pillar subtotal: **7/8**. A numeric /24 would either inflate four non-existent surfaces to 4/4 or punish them with 1/4; both would misstate the evidence.

---

## Top 3 Priority Fixes

1. **WARNING — `docs/api-reference.md` misattributes a core dataclass to `sif.models`** — a reader looking for `SearchOptions` in the Models Module page is told `from sif.core.models import SearchOptions` two lines under a `## Models Module` heading, so a Phase 17 deletion (`sif/models/search.py`) left the reference page disagreeing with the package layout; contributors grep the wrong module. **Fix:** move the `SearchOptions` block (`docs/api-reference.md:227-266`) under a `## Core Module` heading (the same class is already shown correctly at `:761`), and re-run the doc generator so its Models Module section lists only `sif.models` classes.
2. **OBSERVATION — dated test counts have drifted 27 tests since the page was written** — `docs/testing.md:4`, `:202`, and `docs/development.md:305` say 3,234 collected; HEAD collects **3,261** (`pytest --collect-only -q`), and `17-VALIDATION.md` records 3,261 collected / 3,260 passed / 1 skipped. Both pages date or hedge the number, so this is drift from later phases on this branch, not a false claim about the phase. **Fix (optional):** regenerate the docs, or replace the literal with the command that prints it.
3. **None applicable — Visuals/Color/Typography/Spacing and Experience Design** — there is no rendered UI or design system in this phase, and the CLI interaction surface scored 4/4 with no defects. Do not manufacture UI work to fill this template.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Positives (specific, actionable CLI copy — re-verified at HEAD):**

- `src/sif/utils/daemon.py:253-258` — the library boundary refuses with cause and remedy: `detached mode requires POSIX fork (os.fork); use the foreground watch on Windows`. It fires before `os.pipe()`/`os.fork()`.
- `src/sif/cli/commands/watch.py:359-366` — the CLI boundary raises `--detach requires POSIX fork support and is not available on Windows; run `sif watch` in the foreground instead.`
- `src/sif/cli/commands/watch.py:438-442` — the win32 service path refuses with `the watch service is not supported on Windows; run `sif watch` in the foreground instead`, before any `systemctl`/`launchctl` probe.
- `src/sif/cli/commands/watch.py:421-426` — a cross-user PID produces `Watch daemon (PID N) belongs to another user; not stopped. Run as its owner to stop it.` instead of a `PermissionError` traceback (WR-08).
- `scripts/windows_smoke.py:33-65` — matchers require both the constraint and the remedy (`_DETACH_REFUSAL_PARTS`, `_SERVICE_REFUSAL_PARTS`), and `looks_like_traceback()` rejects leaked tracebacks, so vague or crash-only copy would fail the smoke.
- No generic labels (`Submit`, `Click Here`, `went wrong`, `try again`, `error occurred`) were found in `src/sif/cli` or `src/sif/utils`.

**WARNING — reference docs misattribute `SearchOptions` to `sif.models`:**

- `docs/api-reference.md:225` opens `## Models Module`; `:227` adds `### Search Options`; `:229-232` then shows `#### Class: SearchOptions` with `from sif.core.models import SearchOptions`.
- `sif.models` does not export `SearchOptions`; `sif.core.models` does. The sibling entries in that section (`CollectionCreate`/`CollectionUpdate`/`CollectionResponse`) are genuinely `sif.models` classes, so the section reads as authoritative and is wrong only for this one class.
- Source of the defect: plan 17-01 deleted `src/sif/models/search.py`, and the reference page's Models Module section was never re-partitioned. Logged as IN-03 in `17-REVIEW.md` and still `open` in `17-REVIEW-DISPOSITION.md`.
- Scored 3/4 rather than 4/4 on this alone: it is one concrete, verifiable user-facing inaccuracy in docs this phase edited, and the rest of the copy checked out.

**Observations (not deducted):**

- Test counts in `docs/testing.md:4`, `:202` and `docs/development.md:305` are 3,234 against 3,261 collected at HEAD. Both are dated (`macOS, 2026-11-18`) or hedged (`at the time of writing`), so they were true when written.
- `docs/architecture.md:57` and `:751` still say `models/` holds "search schemas"/"search models". Checked: `src/sif/models/document.py:70` defines `DocumentSearchResult`, so the prose is accurate at HEAD, not residual.

### Pillar 2: Visuals (N/A)

No rendered UI, component hierarchy, icon-only controls, or aria-label surface exists in this phase. The one terminal-output change — the encodability-aware spinner (`src/sif/utils/progress.py:20-38`) — is behavior and failure robustness, scored under Experience Design. No UI finding is invented here.

### Pillar 3: Color (N/A)

No CSS custom properties, Tailwind classes, theme tokens, or rendered color surface were introduced or modified. `NO_COLOR`/`FORCE_COLOR` appear only in test/CI hermeticity (`env -u FORCE_COLOR NO_COLOR=1`) and do not constitute a color design contract. Rich color tags (`[yellow]`, `[dim]`, `[red]`) are inline CLI status styling with no palette or 60/30/10 distribution to audit.

### Pillar 4: Typography (N/A)

No font sizes, weights, or type-scale classes exist; the project is a Python CLI/library with Markdown docs.

### Pillar 5: Spacing (N/A)

No layout, spacing scale, padding/margin/gap classes, or visual composition surface exists.

### Pillar 6: Experience Design (4/4)

State coverage and failure behavior on the CLI surface are strong and proven:

- **Error states at both boundaries:** the library `detach()` guard (`src/sif/utils/daemon.py:253-258`) replaces a raw `AttributeError`, and the CLI guard (`src/sif/cli/commands/watch.py:359-366`) keeps the user from ever reaching fork work. The win32 service refusal lives in the shared `_service_manager` site (`watch.py:438-442`), so install and uninstall both get the same message before a service-manager probe.
- **Tests pin the interaction contract, not just the exception:** `tests/unit/utils/test_daemon.py:603-610` asserts the message names POSIX fork and the foreground remedy; `tests/unit/cli/test_watch_cmd.py:395` asserts the CLI refusal text. The whole audited guard subset is green at HEAD — `pytest --no-cov` over `test_daemon.py`, `test_watch_cmd.py`, `test_progress.py`, `test_windows_smoke_script.py`, `test_hygiene.py`, `test_release_metadata.py`, `test_ci_workflows.py` → **145 passed**.
- **Failure is reported, never silently absorbed:** a handshake timeout SIGKILLs the detached session before reporting, and `--detach/--stop` on the wrong platform exits non-zero with the cause and the remedy rather than a "maybe detached".
- **Data-preserving degradation:** the missing-root `index update` path reports `Removed: 0` plus the all-documents-preserved warning (`scripts/windows_smoke.py:35-41`), verified by the smoke matchers and the recorded 8/8 PASS yoga run at HEAD `48759e2` (`17-04-SUMMARY.md:131-158`). The fcntl warning is asserted verbatim.
- **A real interaction bug was found and fixed:** the first yoga run exposed a `UnicodeEncodeError` on GBK consoles when the index spinner rendered braille frames, turning a successful command into a traceback. `src/sif/utils/progress.py:20-38` now selects the ASCII `line` spinner when the stream cannot encode the default frames; `src/sif/cli/commands/index.py:114` uses it. Tests cover UTF-8, GBK, ASCII, unknown-encoding, and no-encoding streams (`tests/unit/utils/test_progress.py:115-131`).
- **Rendering no longer corrupts or crashes on user data:** index event payloads (filenames) are Rich-escaped before printing (`src/sif/cli/commands/index.py:188,192,194`), so a bracketed filename is preserved and a stray closing tag cannot raise `MarkupError` (WR-01).
- **No destructive-action gap:** the smoke's post-delete assertion proves a missing collection root preserves all documents instead of mass-deleting.
- **Accepted limitation, not a defect:** `make windows-smoke` is manual/on-demand by decision D-07 (`17-CONTEXT.md:32`; yoga is a user machine). The unit-level guards and `tests/test_windows_smoke_script.py` keep the matcher contract honest between runs.

---

## Registry Safety

Skipped — `components.json` is absent (shadcn not initialized) and no third-party UI registry exists. No Registry Safety section is warranted.

---

## Files Audited

**Directly examined at HEAD `b19916f` (source, docs, config):**

- `src/sif/utils/daemon.py`
- `src/sif/cli/commands/watch.py`
- `src/sif/utils/progress.py`
- `src/sif/cli/commands/index.py`
- `src/sif/models/__init__.py`, `src/sif/models/document.py` (to test the "search schemas" claim)
- `scripts/windows_smoke.py`
- `tests/unit/utils/test_daemon.py`
- `tests/unit/cli/test_watch_cmd.py`
- `tests/unit/utils/test_progress.py`
- `docs/testing.md`
- `docs/api-reference.md`
- `docs/architecture.md`
- `docs/development.md`

**Phase artifacts reviewed:**

- `17-CONTEXT.md` (locked decisions D-05/D-06/D-07, D-08)
- `17-01-SUMMARY.md` … `17-09-SUMMARY.md` (all nine)
- `17-VALIDATION.md` (re-validated 2026-11-24), `17-REVIEW.md` + `17-REVIEW-DISPOSITION.md`, `deferred-items.md`

**Frontend-surface scan (negative evidence):**

- No `package.json`, `vite.config.*`, `tailwind.config.*`, `postcss.config.*`, `components.json`, `.tsx`, `.jsx`, authored `.css`, or `.scss` outside `htmlcov/` and `.venv/`.
- No `UI-SPEC.md` anywhere under `.planning/`.
- No dev server: 3000 and 5173 closed; 8080 is an unrelated SearXNG.

**Commands run:** `pytest --collect-only -q` (3,261 collected), and the 7-file guard subset above (145 passed). `.planning/ui-reviews/.gitignore` was re-verified as complete before any capture attempt; no captures were made, so nothing was stored.
