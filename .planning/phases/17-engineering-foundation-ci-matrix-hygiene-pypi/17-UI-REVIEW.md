# Phase 17 — UI Review

**Audited:** 2026-11-14
**Baseline:** No UI-SPEC.md exists for this phase. Abstract 6-pillar standards, applied only where a user-facing surface exists.
**Screenshots:** not captured — no frontend and no project dev server. Ports 3000/5173 were closed; port 8080 answered but is an unrelated SearXNG instance (`server: granian`, `<title>searxng</title>`), rejected as evidence rather than screenshotted as if it were SIF.
**Interaction captures:** off (`workflow.ui_interaction_capture` is false)

---

## Applicability Gate

Phase 17 (Engineering Foundation: CI Matrix + Hygiene + PyPI) introduced **no frontend surface**. Verified, not assumed:

- The phase diff (`e78a7d5^..HEAD`, 66 files) contains only Python source/tests, Markdown, GitHub Actions YAML, Makefile, `pyproject.toml`, `uv.lock`, and deleted junk paths.
- The repository has no `package.json`, Vite/Tailwind/PostCSS config, `.tsx`/`.jsx`, or authored `.css`/`.scss`. The only HTML/CSS found is generated coverage output under `htmlcov/` and dependency files under `.venv/`.
- SIF's HTTP surface is the MCP transport (FastAPI JSON/SSE), not a rendered UI.
- No `UI-SPEC.md` exists in the phase or milestone.

Consequently, **Visuals, Color, Typography, and Spacing have no surface to audit**. They are marked N/A rather than awarded unearned 4/4 scores. Two pillars do have a real user-facing analogue and are scored against it: **Copywriting** (CLI refusal/error copy and the developer docs this phase edited) and **Experience Design** (CLI interaction and failure states).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | CLI refusal messages are specific cause+remedy copy; `docs/testing.md` still describes deleted test helpers and a stale suite count |
| 2. Visuals | N/A | No rendered UI; the terminal spinner fix is state/rendering robustness, not a visual hierarchy contract |
| 3. Color | N/A | No color system, CSS tokens, or UI surface; `NO_COLOR`/`FORCE_COLOR` handling is test hermeticity, not color design |
| 4. Typography | N/A | No type scale, font sizes/weights, or UI surface |
| 5. Spacing | N/A | No layout, spacing scale, or UI surface |
| 6. Experience Design | 4/4 | Windows degradation refusals are honest, cause+remedy, traceback-free, unit-tested at both boundaries, and proven 8/8 on real Windows; a genuine GBK console crash was found and fixed |

**Overall: N/A / 24 — this is not a frontend phase.** Applicable-pillar subtotal: **7/8**. A numeric /24 would either inflate four non-existent surfaces to 4/4 or punish them with 1/4; both would misstate the evidence.

---

## Top 3 Priority Fixes

1. **WARNING — `docs/testing.md` still documents deleted test assets and a stale suite count** — a contributor following the test guide is sent to `tests/factories.py`, `tests/unit/test_search.py`, `sample_search_options`/`sample_search_result(s)`, and `SearchOptionsFactory`/`SearchResultFactory`, none of which exist after Phase 17; the page also claims 1629 tests while HEAD collects 1670 (1669 passed, 1 skipped). **Fix:** update the test-layout tree, fixtures table, factories section, and count on `docs/testing.md`; optionally add these removed names to the `tests/test_hygiene.py` docs absence list so the staleness cannot recur.
2. **None applicable — Visuals/Color/Typography/Spacing** — there is no rendered UI, no design system, and no UI-SPEC in this phase. Do not manufacture UI work to fill this template.
3. **None applicable — Experience Design** — the CLI interaction surface scored 4/4 with no defects; the only accepted limitation (Windows smoke is manual/on-demand) is a locked product decision (D-07), not a defect.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Positives (specific, actionable CLI copy):**
- `src/sif/utils/daemon.py:236-240` — library boundary refuses with cause and remedy: `"detached mode requires POSIX fork (os.fork); use the foreground watch on Windows"`. It fires before `os.pipe()`/`os.fork()`.
- `src/sif/cli/commands/watch.py:357-366` — CLI boundary raises `--detach requires POSIX fork support and is not available on Windows; run `sif watch` in the foreground instead.`
- `src/sif/cli/commands/watch.py:431-437` — the win32 service path refuses with `the watch service is not supported on Windows; run `sif watch` in the foreground instead`, before any `systemctl`/`launchctl` probe.
- `scripts/windows_smoke.py:50-59` — matchers require both the constraint and the remedy, and `looks_like_traceback()` rejects leaked tracebacks, so vague or crash-only copy would fail the smoke.
- No generic labels (`Submit`, `Click Here`, `went wrong`, `try again`, `error occurred`) were found in the phase-touched CLI modules.

**WARNING — stale developer-facing copy in `docs/testing.md`:**
- `docs/testing.md:4` claims “1629 tests in total (1628 passing and 1 opt-in skip)”; the phase-end tree collects 1670 tests with 1669 passed and 1 skipped (`.planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-VALIDATION.md:26`).
- `docs/testing.md:81` lists `factories.py # Test data factories`; `tests/factories.py` was deleted in plan 17-01.
- `docs/testing.md:99` lists `tests/unit/test_search.py`; deleted in plan 17-01.
- `docs/testing.md:138` documents `sample_search_options`, `sample_search_result(s)`; those fixtures were removed from `tests/conftest.py` in plan 17-01.
- `docs/testing.md:146-162` documents `SearchOptionsFactory`/`SearchResultFactory` and `from tests.factories import ...`; both left with `tests/factories.py`.
- This was consciously logged in `deferred-items.md:5-13` as outside plan 17-08's enumerated literal sweep. That makes it a known, non-blocking debt rather than an unexpected regression — but it is still real user-facing copy at phase completion, so the score is 3/4 rather than 4/4.

### Pillar 2: Visuals (N/A)

No rendered UI, component hierarchy, icon-only controls, or aria-label surface exists in this phase. The one terminal-output change — the encodability-aware spinner (`src/sif/utils/progress.py:20-38`) — is behavior and failure robustness, scored under Experience Design. No UI finding is invented here.

### Pillar 3: Color (N/A)

No CSS custom properties, Tailwind classes, theme tokens, or rendered color surface were introduced or modified. `NO_COLOR`/`FORCE_COLOR` appear only in test/CI hermeticity (`env -u FORCE_COLOR NO_COLOR=1`) and do not constitute a color design contract.

### Pillar 4: Typography (N/A)

No font sizes, weights, or type-scale classes exist; the project is a Python CLI/library with Markdown docs.

### Pillar 5: Spacing (N/A)

No layout, spacing scale, padding/margin/gap classes, or visual composition surface exists.

### Pillar 6: Experience Design (4/4)

State coverage and failure behavior on the CLI surface are strong and proven:

- **Error states at both boundaries:** the library `detach()` guard (`src/sif/utils/daemon.py:236-240`) prevents a raw `AttributeError`, and the CLI guard (`src/sif/cli/commands/watch.py:357-366`) prevents the user from ever reaching fork work. The win32 service refusal lives in the shared `_service_manager` site (`watch.py:431-437`), so install and uninstall both get the same message before a service-manager probe.
- **Tests pin the interaction contract, not just the exception:** `tests/unit/utils/test_daemon.py:523-533` asserts the message names POSIX fork, `os.fork`, and the foreground remedy; `tests/unit/cli/test_watch_cmd.py:368-371` and `:505-508` assert non-zero exit, the cause+remedy text, and `"Traceback" not in output`.
- **Data-preserving degradation:** the missing-root `index update` path reports `Removed: 0` plus the all-documents-preserved warning, verified by `scripts/windows_smoke.py` matchers and the recorded 8/8 PASS yoga run at HEAD `48759e2` (`17-04-SUMMARY.md:131-158`). The fcntl warning is likewise asserted verbatim.
- **A real interaction bug was found and fixed:** the first yoga run exposed a `UnicodeEncodeError` on GBK consoles when the index spinner rendered braille frames, turning a successful command into a traceback. `src/sif/utils/progress.py:20-38` now selects an ASCII `line` spinner when the stream cannot encode the default frames; `src/sif/cli/commands/index.py:92-97` and the watch reconcile path use it. Tests cover UTF-8, GBK, ASCII, unknown-encoding, and no-encoding streams (`tests/unit/utils/test_progress.py:115-131`).
- **No destructive-action gap:** the smoke's post-delete assertion proves a missing collection root preserves all documents instead of mass-deleting.
- **Accepted limitation, not a defect:** `make windows-smoke` is manual/on-demand by decision D-07 (yoga is a user machine). The unit-level guards and `tests/test_windows_smoke_script.py` keep the matcher contract honest between runs.

---

## Registry Safety

Skipped — `components.json` is absent (shadcn not initialized) and no third-party UI registry exists. No Registry Safety section is warranted.

---

## Files Audited

**Directly examined (source, docs, config):**
- `src/sif/utils/daemon.py`
- `src/sif/cli/commands/watch.py`
- `src/sif/utils/progress.py`
- `src/sif/cli/commands/index.py`
- `src/sif/search/rerank.py` (via commit `f6092f8`)
- `scripts/windows_smoke.py`
- `tests/unit/utils/test_daemon.py`
- `tests/unit/cli/test_watch_cmd.py`
- `tests/unit/utils/test_progress.py`
- `docs/testing.md`
- `Makefile`
- `pyproject.toml` (as referenced by plans/summaries)
- `.github/workflows/test-matrix.yml` and `.github/workflows/publish.yml` (as referenced)
- `README.md`, `docs/changelog.md`, `.github/workflows/docs.yml`

**Phase artifacts reviewed in full:**
- `17-CONTEXT.md`
- `17-01-PLAN.md` … `17-09-PLAN.md` (all nine)
- `17-01-SUMMARY.md` … `17-09-SUMMARY.md` (all nine)
- `deferred-items.md`, `17-VALIDATION.md` (supporting evidence)

**Frontend-surface scan (negative evidence):**
- No `package.json`, `vite.config.*`, `tailwind.config.*`, `postcss.config.*`, `.tsx`, `.jsx`, authored `.css`, or `.scss` outside `htmlcov/` and `.venv/`.
- No `UI-SPEC.md` anywhere under `.planning/`.
- No `components.json`.

**Project skills loaded:** `.claude/skills/sif-get/SKILL.md`, `.claude/skills/sif-search/SKILL.md` (no UI implications).
