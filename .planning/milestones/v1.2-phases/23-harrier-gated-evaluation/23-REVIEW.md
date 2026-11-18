---
phase: 23-harrier-gated-evaluation
reviewed: 2026-11-16T14:59:03Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - .gitignore
  - docs/benchmarking.md
  - docs/cli-reference.md
  - scripts/harrier_eval.py
  - src/sif/cli/commands/eval.py
  - src/sif/search/embedder_verdict.py
  - src/sif/search/personal_bench.py
  - tests/support/eval.py
  - tests/unit/cli/test_eval.py
  - tests/unit/scripts/__init__.py
  - tests/unit/scripts/test_harrier_eval.py
  - tests/unit/search/test_embedder_verdict.py
  - tests/unit/search/test_personal_bench.py
findings:
  critical: 2
  warning: 6
  info: 6
  total: 14
  necessity: 0
status: issues_found
---

# Phase 23: Code Review Report

**Reviewed:** 2026-11-16T14:59:03Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Reviewed the full phase-23 scope at standard depth: the two-sided verdict rule and its gate arithmetic, the language-aware widening in `personal_bench.py`, the repeatable `--require-language` CLI surface, the two-arm runbook (`scripts/harrier_eval.py`) including env isolation, identity gates, JSON parsing, resume state, artifact writing, and cleanup guards, plus the supporting tests, docs, and `.gitignore`.

The verdict policy itself checks out. The strict `1/N` floor, the inclusive `-0.01` language floor, the N>=101 epsilon-win rationale, CI/tie handling, and the `insufficient-evidence` priority are internally consistent, and the committed artifact's `rule` block matches the documented `keep-qwen3` rejection reasons exactly. The committed `bench/harrier-verdict.json` was scanned: it contains no query text, saved-run records, or absolute personal paths (`scope_labels` are basenames; `environment.platform` has no host/user path; `default_flip.artifact` is a relative path). The `.gitignore` addition correctly covers the runbook's `.planning/tmp/` scratch root. `docs/cli-reference.md` matches the CLI help text/decorator surface and appears generator-produced; no hand-edit evidence was found.

The two blocking issues are operational/evidence-integrity defects in the runbook: the cleanup guard does not reject the home directory as a scratch *root* (data-loss risk), and the verdict stage can return a stale artifact because the insufficient-evidence path marks the artifact stage complete. There are also real resume-state gaps (non-idempotent collection creation, content changes not invalidating scope), a materially incorrect held-out leg table in `docs/benchmarking.md`, and a schema drift between the artifact writer and the committed artifact (`default_flip`).

Targeted tests were run: 77 passed in `tests/unit/scripts/test_harrier_eval.py` + `tests/unit/search/test_embedder_verdict.py`, 4 passed in the `--require-language` CLI selection, and 16 passed in the language/widening selection of `test_personal_bench.py`. The global pytest coverage gate fails only because these were subset runs.

No `<structural_findings>` block was provided, so there is no fallow section. The necessity rubric (`~/.claude/gsd-core/references/necessity-review.md`) was read and applied; no qualifying necessity findings were identified (the cleanup/path checks are a real trust-boundary guard, and the payload/validation checks defend real external data).

## Narrative Findings (AI reviewer)

### Critical Issues

#### CR-01: Cleanup guard accepts the home directory as a scratch root — data loss risk

**Severity:** BLOCKER
**File:** `scripts/harrier_eval.py:922-932` (`assert_within_scratch`), `scripts/harrier_eval.py:935-957` (`cleanup_arms`)
**Issue:** `assert_within_scratch` rejects a *target* equal to the home directory, but never rejects a *root* equal to the home directory. `run_stage_machine` resolves `--scratch-root`, creates `saved-runs/`, writes `run-state.json`, and passes `<root>/qwen3.db` / `<root>/harrier.db` to the CLI; `cleanup_arms` then resolves each candidate (`qwen3.db`, `harrier.db`, their `-wal`/`-shm`/`.lock` sidecars, and `saved-runs/qwen3.json`) and unlinks it. With `--scratch-root ~` (or a symlink resolving to home), every candidate is nested under `.resolve()`d home, so the guard passes and unrelated user files such as `~/qwen3.db` or `~/saved-runs/qwen3.json` can be deleted or overwritten. Demonstrated: `assert_within_scratch(Path.home() / "qwen3.db", Path.home())` returns the target. The test suite only covers `assert_within_scratch(home, home)` (`tests/unit/scripts/test_harrier_eval.py:918-922`), not a nested target under a home root.
**Fix:**
```python
def assert_within_scratch(path: Path, scratch_root: Path) -> Path:
    target = Path(path).resolve()
    root = Path(scratch_root).resolve()
    if root in {Path("/"), Path.home()}:
        raise ValueError(f"refusing to use {root} as a scratch root")
    if target in {Path("/"), Path.home()}:
        raise ValueError("refusing to operate on the filesystem root or home directory")
    if target != root and not target.is_relative_to(root):
        raise ValueError(f"refusing path outside the scratch root: {target}")
    return target
```
Also call `assert_within_scratch(scratch_root, scratch_root)` (or an equivalent root-only check) in `main`/`run_stage_machine` before `mkdir`, and add a test asserting `assert_within_scratch(home / "qwen3.db", home)` raises.

#### CR-02: Verdict stage can return a stale artifact after a full run

**Severity:** BLOCKER
**File:** `scripts/harrier_eval.py:1269-1272` (`_run_verdict_stage` early return), `scripts/harrier_eval.py:1351-1355` (insufficient path marks `artifact`), `scripts/harrier_eval.py:1031-1048` (`_run_adequacy_stage`)
**Issue:** `_run_verdict_stage` returns any existing `ARTIFACT_PATH` as soon as `stage_done(state, "artifact")` is true, without checking that the artifact was produced by the current comparison or that the comparison/query-set inputs still exist. The inadequate path also calls `_complete_stage(..., "verdict")` and `_complete_stage(..., "artifact")` after writing an `insufficient-evidence` artifact. On a same-scope resume where the arm-A DB has been re-indexed externally so `preflight_adequacy` becomes adequate, the run does the full embed/eval and then prints/commits the old `insufficient-evidence` artifact; the same short-circuit can also return a stale `keep-qwen3`/`adopt-harrier` artifact after inputs change. This directly contradicts the plan's stated behavior that an inadequate preflight "is recorded but never marked complete, so a resumed full run re-checks adequacy before spending the embed budget." Demonstrated directly: calling `_run_verdict_stage` with an `artifact` marker and a missing comparison/saved-run path returns `{'decision': 'insufficient-evidence', 'stale': True}` instead of failing.
**Fix:** Do not mark `verdict`/`artifact` complete on the insufficient path (use a distinct `short`/`insufficient` stage marker instead, or leave the artifact unmarked). In `_run_verdict_stage`, only take the early return when the stored verdict detail records the same query-set fingerprint and corpus fingerprint as the current inputs; otherwise recompute. Add a regression test for the inadequate→adequate transition with a re-indexed arm DB.

### Warnings

#### WR-01: Non-idempotent `collection add` breaks documented resume and scope changes

**Severity:** WARNING
**File:** `scripts/harrier_eval.py:1015-1028`, `scripts/harrier_eval.py:1146-1173`, `scripts/harrier_eval.py:1326-1358`; `src/sif/cli/commands/collection.py:56-58`; `tests/unit/scripts/test_harrier_eval.py:729-766`
**Issue:** `collection add` raises `Collection '<name>' already exists`, and the stage marker is written only after all commands succeed. If `collection_add_1` succeeds but a later command in the same stage fails (bad second root, `index update` error, transient disk/lock), rerunning `_run_index_stage` starts again at `collection_add_1` and fails permanently. Likewise, a changed `--corpus` set gets a fresh scope key but the old scratch DBs are not cleared, so re-indexing into them fails on the first duplicate `phase23-1` collection. The test that claims a changed scope "rebuilds the baseline arm" uses a no-op `run_command`, so it never exercises the real CLI or the duplicate-collection failure.
**Fix:** Clear/recreate run-owned arm DBs when the scope changes (or on a fresh state), and make collection creation idempotent (treat an existing `phase23-*` collection as success, or remove it first). Add a DB-backed test that a partially completed index stage can resume.

#### WR-02: Resume scope key ignores corpus content changes

**Severity:** WARNING
**File:** `scripts/harrier_eval.py:417-434` (`scope_state`/`scope_key`), `scripts/harrier_eval.py:1015-1028`, `scripts/harrier_eval.py:1146-1173`
**Issue:** `scope_key` hashes only resolved corpus root paths plus the label, and index stages are skipped on resume. Editing files or adding documents under the same roots silently reuses the old arm indexes (and, once the verdict/artifact stages are complete, the old artifact). The docs/plan say a changed corpus invalidates prior markers; a content change without a root change does not. The corpus fingerprint is computed only at `arm_b_index`, after the arm-A index stage has already been skipped, so it cannot invalidate the run.
**Fix:** Persist the corpus fingerprint at arm-A index completion and invalidate down-stream markers when a recomputed fingerprint differs; or always run `index update` (cheap) on resume and compare against the stored fingerprint. Add a test that changes a document under the same root and asserts the stages are invalidated.

#### WR-03: Docs "Held-out leg" table mixes all-split and held-out gate values

**Severity:** WARNING
**File:** `docs/benchmarking.md:291-294`
**Issue:** The table is labeled "Held-out leg" but its N/delta/CI/1-N values come from `gates.legs` (all splits), while the title baseline/current means come from `gates.leg_splits.title.heldout`; the body row is entirely the all-split gate. The committed artifact says held-out title is n=26, `0.844285 → 0.866380`, mean delta `+0.022095`, CI `[-0.010072, +0.065790]`, floor `0.038462`; held-out body is n=30, `0.766928 → 0.765382`, mean delta `-0.001545`, CI `[-0.067319, +0.061951]`, floor `0.033333`. The docs report title n=49, `+0.016584`, CI `[-0.010426, +0.049977]`, floor `0.020408` (all-split title stats) and body n=50, `+0.007841`, etc. (all-split body stats). The adjacent held-out leg×language rows sum to 26 title / 30 body, contradicting the table and making the evidence internally inconsistent.
**Fix:** Replace the table with the held-out leg gate values above (or relabel it "All-split leg" and use the all-split means, e.g. title `0.856635 → 0.873219`), and add a separate held-out leg table so the Ns agree with the leg×language table.

#### WR-04: Artifact writer cannot reproduce the committed artifact; a rerun drops `default_flip`

**Severity:** WARNING
**File:** `scripts/harrier_eval.py:864-914` (`build_artifact`), `scripts/harrier_eval.py:917-919` (`write_artifact`), `scripts/harrier_eval.py:1304-1311`
**Issue:** The builder emits exactly 11 keys (`version`, `decision`, `rule`, `arms`, `corpus`, `query_set_fingerprint`, `gates`, `replay`, `environment`, `min_heldout_for_epsilon_win`, `notes`), and `test_key_order_and_verbatim_gate_leaves` pins that list. The committed artifact also contains a `default_flip` block added by plans 23-05/23-06 (including `zero_delta_proof: {status: "not-applicable"}`). A fresh-clone rerun (state absent) rewrites the committed artifact and silently drops that block; `write_artifact` also unconditionally overwrites the committed evidence even when the corpus/decision changed, and a default `--corpus` run would overwrite the `keep-qwen3` evidence with `insufficient-evidence`.
**Fix:** Add an optional `default_flip` field to `build_artifact` and emit it (updating the key-order test), and preserve any existing block when rewriting or write to a scratch path and promote explicitly. Guard overwriting the committed artifact when the corpus fingerprint/decision differs, or require an explicit `--artifact`/`--force`.

#### WR-05: Inherited SIF fusion settings change the measured pipeline and are not recorded

**Severity:** WARNING
**File:** `scripts/harrier_eval.py:148-173` (`build_arm_env`), `scripts/harrier_eval.py:243-249` (`_env_summary`); `src/sif/cli/commands/eval.py:129-145`, `src/sif/cli/commands/eval.py:756-861`
**Issue:** Each arm env is a copy of `os.environ` with only `REMOVED_ENV` removed and `PINNED_ENV` pinned. The eval reads `settings.rrf_k`, `bm25_weight`, `vector_weight`, and `resolve_candidate_limit`, so inherited `SIF_RRF_K`, `SIF_BM25_WEIGHT`, `SIF_VECTOR_WEIGHT`, `SIF_CANDIDATE_LIMIT`, etc. silently change both arms' ranking. The comparison stays symmetric, but neither `_env_summary` nor `collect_environment`/the artifact records these settings, so the artifact cannot prove what configuration was measured.
**Fix:** Pin the eval-relevant fusion/candidate settings to declared defaults in `build_arm_env` and/or record the effective `Settings` values in the arm env summary and artifact `environment`.

#### WR-06: Malformed comparison/payload JSON escapes as a traceback

**Severity:** WARNING
**File:** `scripts/harrier_eval.py:1203-1223` (`_gates_from_comparison`), `scripts/harrier_eval.py:1101-1128` (`_run_eval_stage`), `scripts/harrier_eval.py:1483-1488` (`main` exception tuple)
**Issue:** `_gates_from_comparison` indexes required keys (`comparison["splits"]`, `["legs"]`, `["leg_splits"]`, `["groups"]`, `["suppressed"]`, `["top_k"]`), and `_run_eval_stage` calls `.get` on the parsed payload. A truncated/hand-edited comparison file or a non-object JSON stdout raises `KeyError`/`TypeError`/`AttributeError`; `main` catches only `OSError`, `RuntimeError`, `ValueError`, `sqlite3.Error`, so these escape as an uncaught traceback instead of the named `FAIL` line. `parse_json_stdout` validates JSON syntax, not object shape.
**Fix:** Validate `isinstance(..., Mapping)` and required keys in `_gates_from_comparison`/`_run_eval_stage`, raising `RuntimeError("... malformed comparison payload ...")`, and add `KeyError`/`TypeError`/`AttributeError` to `main`'s handler (or wrap the payload readers). Add tests with `{}`, `{"splits": {}}`, and a non-object payload.

### Info

#### IN-01: Saved-run path is interpolated into Rich markup unescaped

**Severity:** INFO
**File:** `src/sif/cli/commands/eval.py:615`
**Issue:** `console_err.print(f"[dim]Saved run: {path}[/dim]")` interpolates a config-derived path (`SIF_CACHE_DIR`) into Rich markup. A path containing a closing tag such as `[/bold]` raises `rich.errors.MarkupError` after a successful run, crashing the command. This violates the T-18-01 convention used by `_cell` elsewhere in the same module. This line predates Phase 23 but is in the reviewed file.
**Fix:** Escape the path (`_cell(str(path))` or `escape(str(path))` before interpolation) and add a test using a cache dir containing markup characters.

#### IN-02: Identity gate does not check the model revision

**Severity:** INFO
**File:** `scripts/harrier_eval.py:313-350`
**Issue:** `verify_arm_identity` checks `source`, dimension, model name/type, and prompts, but never `revision`, although plan 23-03 states the gate matches the expected "model/type/prompt/revision" and threat T-23-10 records the resolved revision. A pre-seeded scratch DB carrying a different revision of the same Harrier repo passes the per-arm gate; the artifact records the actual revision, so this is auditable but not gated. Mid-run revision moves are caught by the subprocess stored-vs-loaded identity check, which is the main mitigation.
**Fix:** Add a pinned expected revision (constant or CLI) and compare it for Harrier, or explicitly document revision as record-only and assert it is non-null for the Harrier arm.

#### IN-03: `scripts/harrier_eval.py` is not ruff-clean or ruff-formatted

**Severity:** INFO
**File:** `scripts/harrier_eval.py`
**Issue:** `ruff check scripts/harrier_eval.py` reports 17 findings, including `C901` (`verify_arm_identity` complexity 14 > 10), `PLR0912`, five `PLR0913`, seven `T201` prints, `PERF203`, `PLR0911`, and an unused `# noqa: BLE001` (`RUF100`). `ruff format --check` would reformat it. All six other scripts in `scripts/` are clean. The documented quality suite (`ruff check src tests`) excludes `scripts/`, so CI does not catch this, but it violates the repo's max-complexity 10 and formatting conventions.
**Fix:** Run `ruff format scripts/harrier_eval.py`; refactor `verify_arm_identity`/the stage helpers or add targeted `# noqa` directives with justification; remove the unused noqa or enable `BLE001` intentionally.

#### IN-04: Benchmarking docs do not mention `require-language`

**Severity:** INFO
**File:** `docs/benchmarking.md:159-161`
**Issue:** The personal-bench widening paragraph describes only the accepted-query and held-out floors. The new language-aware widening and the repeatable `--require-language` flag are documented only in the generated `docs/cli-reference.md`; a reader of the benchmarking guide will not know the flag exists.
**Fix:** Add a sentence naming `--require-language`, the per-language `SUPPRESS_BELOW` (10) held-out floor, and the cap/`HeldoutFloorError` behavior.

#### IN-05: Stale zero-delta-proof sentence after the `keep-qwen3` verdict

**Severity:** INFO
**File:** `docs/benchmarking.md:278`
**Issue:** The text says the Qwen3 saved run is retained "for plan 23-06's explicit-Qwen3 zero-delta proof", but the committed artifact records `default_flip.zero_delta_proof: {status: "not-applicable"}` because the verdict did not authorize a change. The runbook's default `keep_arms=False` also deletes `saved-runs/qwen3.json`, so "retained" is only true with `--keep-arms`.
**Fix:** State that the proof is not applicable, reference the artifact's `default_flip.zero_delta_proof`, and mention `--keep-arms` when the run is retained for audit.

#### IN-06: Cleanup leaves the Harrier saved run and comparison JSON behind

**Severity:** INFO
**File:** `scripts/harrier_eval.py:935-957`
**Issue:** `cleanup_arms` (and the `--keep-arms` help text "Keep the scratch arm DBs and saved runs") removes only `saved-runs/qwen3.json`; `saved-runs/harrier.json` and `saved-runs/harrier-comparison.json` (which contain query text, target/retrieved paths) remain after a non-`--keep-arms` verdict. `run-state.json` also remains. The files are under the gitignored scratch root, but cleanup is incomplete relative to its help.
**Fix:** Delete `harrier.json` and `harrier-comparison.json` as well (keeping `run-state.json` only if resume after cleanup is intended), or narrow the help text to "baseline saved run".

---

_Reviewed: 2026-11-16T14:59:03Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
