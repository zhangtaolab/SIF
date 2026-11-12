---
phase: 16-bench-expansion-reranker-tuning
plan: "02"
subsystem: search
tags: [rerank, click, pydantic-settings, candidate-limit, relative-threshold, docs-generation]

# Dependency graph
requires:
  - phase: 15-search-quality-configuration-hybrid-weights-query-suggestions
    provides: query_cmd flag > SIF_ setting > default precedence pattern (RESEARCH Pattern 3) the -C default change copies
provides:
  - Settings.rerank_enabled (default False), SIF_RERANK_ENABLED channel, and the query_cmd --rerank flag (D-12 gate checked before create_reranker)
  - Settings.rerank_candidate_limit (5-50) / rerank_relative_threshold ((0,1]) validated by Pydantic at settings load (T-16-09)
  - resolve_candidate_limit(explicit, settings) shared clamp (explicit > setting > 20 for non-int, clamped into 5..50) — imported by BOTH search.py and (16-04) bench.py
  - -C/--candidate-limit default None resolving via the shared resolver; Click range stays 1..200 (A3 waiver in code)
  - _query_settings_mock(**overrides) CLI test helper enumerating every query_cmd settings read
affects: [16-04 sweep/bench, 16-06 rerank runtime scoring, 16-05 snapshot]

# Actuals (#2632) — same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 6255
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []  # no new dependencies; stdlib + pydantic/click only
  patterns:
    - "Zero-cost-by-construction gates: check the enable flag BEFORE the factory call, never inside it (D-12)"
    - "Enforce range bounds where a value becomes a request (resolver), not only at the flag declaration"
    - "RED commits carry zero-behavior skeletons (fields without bounds, resolver without clamp) so targets fail on assertions, never import errors"
    - "_query_settings_mock(**overrides) shared explicit-mock helper (Pitfall 10 wrong-reason-pass guard)"

key-files:
  created: []
  modified:
    - src/sif/config/settings.py
    - src/sif/cli/commands/search.py
    - scripts/generate_config_ref.py
    - docs/configuration.md
    - docs/cli-reference.md
    - tests/unit/config/test_settings.py
    - tests/unit/cli/test_search.py

key-decisions:
  - "rerank gate = --rerank OR SIF_RERANK_ENABLED, checked before create_reranker — the off path never constructs a model (D-12)"
  - "-C retained with default None; resolve_candidate_limit = explicit > setting > 20 (non-int falls back), always clamped 5..50; Click range stays 1..200, A3 waiver recorded beside the option"
  - "rerank_enabled doc description avoids 'sif search query;' — the docs bare-command gate exempts 'query' only when followed by whitespace"

patterns-established:
  - "Pattern: enabled-path tests must override rerank_enabled=True on their settings mocks or the D-12 gate makes their create_reranker side-effects unreachable"
  - "Pattern: settings-mock enumeration via one module-level helper with overrides; wide-open MagicMock() stays reserved for the explicit leak-guard test"

requirements-completed: [QUAL-05]

coverage:
  - id: D1
    description: "Rerank explicit opt-in: SIF_RERANK_ENABLED (default false) + --rerank flag; off path constructs no reranker and passes reranker=None to SearchPipeline; ImportError soft-fail and ValueError->ClickException preserved"
    requirement: QUAL-05
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestRerankOptIn/test_off_by_default_constructs_no_reranker/test_rerank_flag_constructs_reranker_once/test_enabled_setting_constructs_without_flag/test_env_setting_enables_rerank + test_query_optional_reranker_import_error_warns + test_factory_value_error_becomes_click_exception"
        status: pass
      - kind: unit
        ref: "tests/unit/config/test_settings.py#test_rerank_disabled_by_default/test_rerank_enabled_via_env"
        status: pass
    human_judgment: false
  - id: D2
    description: "Validated cap/threshold settings: rerank_candidate_limit accepts 5/50 and rejects 4/51; rerank_relative_threshold accepts 0.5/1.0 and rejects 0.0/1.1, each named in the ValidationError (T-16-09 mitigation)"
    requirement: QUAL-05
    verification:
      - kind: unit
        ref: "tests/unit/config/test_settings.py#test_rerank_candidate_limit_accepts_boundaries/test_rerank_candidate_limit_rejects_out_of_range/test_rerank_relative_threshold_accepts_boundaries/test_rerank_relative_threshold_rejects_out_of_range"
        status: pass
    human_judgment: false
  - id: D3
    description: "resolve_candidate_limit shared clamp + settings-resolving -C: omitted resolves from SIF_RERANK_CANDIDATE_LIMIT (pinned at non-default 33), explicit -C wins, -C 200 -> 50 and -C 1 -> 5 while the Click range stays 1..200, MagicMock cap resolves to int 20"
    requirement: QUAL-05
    verification:
      - kind: unit
        ref: "tests/unit/config/test_settings.py#test_resolve_candidate_limit_* + tests/unit/cli/test_search.py#TestCandidateLimitResolution"
        status: pass
    human_judgment: false
  - id: D4
    description: "Generated docs: configuration.md rows + validation rules + env example for the three SIF_RERANK_* settings; cli-reference.md --rerank row and the settings-resolving -C default; make docs-generate leaves a clean diff"
    verification:
      - kind: other
        ref: "command: make docs-generate && git diff --exit-code docs/configuration.md docs/cli-reference.md"
        status: pass
    human_judgment: false

# Metrics
duration: 18 min
completed: 2026-11-08
status: complete
---

# Phase 16 Plan 02: Rerank Opt-In Configuration Summary

**SIF_RERANK_ENABLED (default false) + --rerank make rerank explicit; SIF_RERANK_CANDIDATE_LIMIT (5-50) and SIF_RERANK_RELATIVE_THRESHOLD ((0,1]) are Pydantic-validated; the shipped -C flag resolves through the shared `resolve_candidate_limit` clamp**

## Performance

- **Duration:** 18 min
- **Started:** 2026-11-08T13:46:49Z
- **Completed:** 2026-11-08T14:05:18Z
- **Tasks:** 3 (Task 2 executed as TDD: RED -> GREEN, REFACTOR not needed)
- **Files modified:** 7

## Accomplishments

- D-12 explicit opt-in end-to-end: `Settings.rerank_enabled` defaults False; `query_cmd` computes `rerank_requested = rerank or settings.rerank_enabled` BEFORE `create_reranker`, so the skip-rerank fast path constructs no model, loads no weights, and imports no optional backend — `SearchPipeline` receives `reranker=None`
- The existing ImportError soft-fail (yellow install hint) and the ValueError -> `click.ClickException` mapping are preserved verbatim, now fed by mocks with `rerank_enabled=True` (with False the gate would make both side-effects unreachable)
- D-10/D-11 validated settings: `rerank_candidate_limit` (`ge=RERANK_CANDIDATE_LIMIT_MIN, le=RERANK_CANDIDATE_LIMIT_MAX` = 5/50 module constants) and `rerank_relative_threshold` (`gt=0, le=1`) reject out-of-range values at settings load naming the field (T-16-09)
- `resolve_candidate_limit(explicit, settings)`: explicit flag wins, else the setting, non-int falls back to 20 (a MagicMock cap cannot leak into the plain `SearchOptions` dataclass), always clamped into 5..50 — so `-C 200` puts 50 (never 200) into `SearchOptions` while the flag's shipped Click range stays 1..200 (A3 waiver recorded in a comment beside the option)
- All ~17 explicit settings mocks in test_search.py consolidated onto a `_query_settings_mock(**overrides)` helper enumerating every query_cmd settings read (model, reranker name/path, rerank_enabled, rerank_candidate_limit, rerank_relative_threshold, model_dump)
- Generator-registered docs: configuration.md (three rows, two validation rules, three env-example lines) and cli-reference.md (`--rerank` row, `-C` default None with the clamped-to-5-50 help) — clean diff proven after commit

## Task Commits

Each task was committed atomically:

1. **Task 1: Explicit rerank opt-in end-to-end (tracer)** - `04feed5` (feat; tracer verify re-run passed under auto mode -> expanded without checkpoint)
2. **Task 2 RED: failing cap/threshold tests + resolution skeletons** - `bfd10b7` (test; JUnit RED evidence classified RED_EVIDENCE_OK)
3. **Task 2 GREEN: validated bounds + clamped resolver + -C resolution** - `a1cf36c` (feat; REFACTOR skipped — no cleanup needed, so no third commit)
4. **Task 3: generated config and CLI docs** - `08b9c70` (docs; includes the Rule 3 description fix)

**Plan metadata:** see the docs(16-02) close-out commit (SUMMARY + STATE + ROADMAP + REQUIREMENTS)

## Files Created/Modified

- `src/sif/config/settings.py` - rerank_enabled / rerank_candidate_limit / rerank_relative_threshold fields, RERANK_CANDIDATE_LIMIT_MIN/MAX constants, resolve_candidate_limit
- `src/sif/cli/commands/search.py` - --rerank flag, rerank param, gate before create_reranker, -C default None + resolver wiring + A3 waiver comment
- `scripts/generate_config_ref.py` - SECTIONS/env-example/validation-rule registration for the three fields
- `docs/configuration.md`, `docs/cli-reference.md` - regenerated (never hand-edited)
- `tests/unit/config/test_settings.py` - 12 new tests: defaults, boundaries, env rejections, resolver unit behavior
- `tests/unit/cli/test_search.py` - _query_settings_mock helper, 17-site mock consolidation, TestRerankOptIn (4) + TestCandidateLimitResolution (4) new tests

## Decisions Made

- The reranker_model_name/reranker_model_path truthiness guard is fully replaced by rerank_requested (flag OR setting): when rerank IS requested, create_reranker dispatches on model_type regardless of which name field is set — matches the plan's key_link "flag OR setting -> create_reranker (never called on the off path)"
- TestCandidateLimitResolution pins the omitted-flag resolution at the non-default 33 so it cannot pass via a literal flag default (Pitfall 10; mirrors 16-01's non-default-baseline lesson)
- The wide-open `MagicMock()` settings leak-guard test patches create_reranker: a bare MagicMock's rerank_enabled is truthy, so the gate opens there — which is itself the leak scenario the test pins

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] rerank_enabled description rephrased for the docs gate**
- **Found during:** Task 3 (docs regeneration)
- **Issue:** The plan-verbatim description "Enable reranking on `sif search query`; the default..." trips `tests/test_docs.py::test_no_bare_search_command`: its regex exempts the word `query` only when followed by whitespace, and `query`;` / ``query` `` never are — the generated configuration.md row failed the gate
- **Fix:** Rephrased to "Enable reranking on the sif search query command (the default keeps the zero-cost skip-rerank fast path; pass --rerank or set 1 to enable)" — meaning preserved, `query` now followed by whitespace, with a phrasing note comment in settings.py
- **Files modified:** src/sif/config/settings.py, docs/configuration.md (regenerated)
- **Verification:** tests/test_docs.py 13 passed; `make docs-generate && git diff --exit-code` clean
- **Committed in:** 08b9c70

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Wording-only adjustment the repo's own docs gate requires; no behavioral or scope change.

## Issues Encountered

None beyond the deviation above. Task 2's RED failed for exactly the intended reasons (DID-NOT-RAISE on 4/51/0.0/1.1; clamp 200 != 50; flag default 20 used instead of settings 33; -C 200 unclamped) and GREEN passed first try.

## TDD Gate Compliance

Task 2 (tdd="true") executed RED -> GREEN with REFACTOR skipped (no cleanup needed):
- RED `bfd10b7` (test) precedes GREEN `a1cf36c` (feat) in ancestry order; no gate violations
- RED evidence: `.planning/tmp/tdd-red-16-02.json` (JUnit XML embedded, 7 planned assertion failures, exit 1) validated by `gsd_run check tdd-red-evidence` as RED_EVIDENCE_OK with target `test_resolve_candidate_limit_clamps_explicit_into_bounds`; semantic assessment recorded in the evidence file and above
- RED carries zero-behavior skeletons (fields without bounds, resolver without clamp, CLI untouched) so every failure is a target assertion, never an import error (Phase 11 house pattern)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave-2 consumer 16-06 (runtime scoring) reads `settings.rerank_relative_threshold` in `create_reranker` and `rerank_enabled` semantics are settled; its reranker construction path is now opt-in-only
- Wave-3 consumer 16-04 imports `resolve_candidate_limit` from `sif.config.settings` for bench's -C (the plan's stated contract); the clamp constants are module-public
- The bench rerank on/off states (D-12) can drive `--rerank` on bench without touching query_cmd
- docs/configuration.md and docs/cli-reference.md are current; any later Settings/CLI change must re-run `make docs-generate`

## Verification Results

- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -k "rerank" -x --no-cov` — 8 passed (tracer gate re-run)
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/config/test_settings.py -k "rerank" -x --no-cov` — 4 passed (tracer gate re-run)
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/config/test_settings.py -k "rerank" -x --no-cov && ... test_search.py -k "candidate_limit or rerank" -x --no-cov` — 12 + 11 passed (Task 2 verify)
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py tests/unit/config/test_settings.py -x --no-cov` — 195 passed
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` (full suite) — 1405 passed, 1 skipped, coverage 94.89% (fail_under=90 gate green)
- `make docs-generate && git diff --exit-code docs/configuration.md docs/cli-reference.md` — clean (Task 3 verify, re-run after commit)
- `ruff check src tests && ruff format --check src tests` — clean; `ty check src/sif` — 0 diagnostics
- Flag contract introspected: -C default None with IntRange(1, 200); --rerank is_flag with the plan-verbatim help

## Self-Check: PASSED

All seven modified files exist on disk and carry this plan's changes; all four task commits (04feed5, bfd10b7, a1cf36c, 08b9c70) are ancestors of HEAD; commit count measured from the plan ledger (base 6b2a055) is 4, matching the Task Commits section.
