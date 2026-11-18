---
phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
plan: 02
subsystem: search/evaluation
tags:
  - personal-bench
  - body-snippet
  - overlap-budget
  - hash-split
  - held-out-widening
  - group-suppression
  - query-log-replay

requires:
  - phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
    provides: "Plan 01 tracer: personal_bench sampling/title-leg domain module, evaluate_per_query, sif eval --personal CLI, tests/support/eval.py fixture builder"
provides:
  - "body-snippet leg with per-leg token-Jaccard budget (title exact-term, body <=0.60, replay not synthesized)"
  - "cross-leg dedupe in declared leg order plus per-leg empty/duplicate/overlap rejection counters"
  - "language (en/zh/mixed) and length (short/medium/long, CJK ideograph = one unit) classifiers"
  - "deterministic sha256 50/50 split and ensure_heldout widening from 50 docs toward min(corpus, 250)"
  - "PersonalReport/CorpusSummary/PersonalQueryRecord/GroupMetrics (rank-aligned retrieved_doc_ids + paths)"
  - "suppressed-group reporting that never renders a small group as zero"
  - "query_log replay leg with normalized/sorted/capped queries and the CLI-only bias note"
affects: [18-03, 23]

tech-stack:
  added: []
  patterns:
    - "Per-leg bias budgets: exact-term legs are exempt, paraphrased legs are token-Jaccard bounded, replay is not synthesized"
    - "Per-leg rejection dicts (empty/overlap/duplicate) so a query set never shrinks silently"
    - "sha256(normalized query)[0] < 128 -> tuning else heldout; replay never split"
    - "Widening loads bodies only for newly added documents while re-synthesizing the deterministic prefix"
    - "Report assembled once in the domain; the CLI renders PersonalReport.to_dict() and recomputes nothing"
    - "Groups emitted in declared LEGS x LANGUAGES x LENGTH_BUCKETS order; <10 groups named, never zero rows"
    - "Replay stores normalized query text plus rank-ordered paths only (no content, no snippets)"

key-files:
  created:
    - tests/unit/search/test_personal_bench.py
  modified:
    - src/sif/search/personal_bench.py
    - src/sif/cli/commands/eval.py
    - tests/support/eval.py
    - tests/unit/cli/test_eval.py
    - docs/cli-reference.md

key-decisions:
  - "Title synthesis keeps its own internal dedupe so the title-only surface stays backward-compatible; synthesize_known_item_queries adds cross-leg dedupe in declared leg order (title wins, the body leg is counted)."
  - "Body candidates count length units (ASCII token or CJK ideograph) for the 4-unit floor and 10-unit cap, so a Chinese sentence is not rejected as one FTS token; the query keeps a contiguous CJK run."
  - "ensure_heldout re-synthesizes the whole deterministic prefix after each doubling but loads content only for newly added documents, keeping the metadata-only whole-corpus pass invariant."
  - "group_metrics suppresses only present groups with 1..9 queries; zero-query combinations have no rendered cell, so they are not listed as suppressed."
  - "Plan 01's flat JSON keys remain integer totals of the per-leg rejection dicts, so existing consumers do not move."
  - "Replay is serialized as replay.queries (normalized query -> rank-ordered paths) and its fixed bias note is printed untruncated because the 80-char cell cap hid the CLI-only limitation."
  - "The generator-owned docs/cli-reference.md is regenerated for the updated eval help text; leaving it stale would fail the docs CI diff gate."

requirements-completed: [EVAL-01, EVAL-02]

coverage:
  - id: D1
    description: "Three query legs exist with distinct semantics: title (exact-term, unbudgeted), body (token Jaccard <=0.60 against title + first 200 chars), replay (stability only, never synthesized)"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestOverlapBudget"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestBodyCandidate"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestDedupe"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestTwoLegDefault::test_default_run_evaluates_title_and_body_queries"
        status: pass
    human_judgment: false
  - id: D2
    description: "Deterministic sha256 50/50 split; held-out widening starts at 50 documents and doubles toward min(corpus, 250) until 50 accepted and 25 held-out; impossible floor at the cap raises a counted ValueError translated to a ClickException"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestSplit"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestEnsureHeldout"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestTwoLegDefault::test_held_out_widening_reaches_the_floor_and_evaluates_outside_docs"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestTwoLegDefault::test_impossible_held_out_floor_exits_one_with_counts"
        status: pass
    human_judgment: false
  - id: D3
    description: "Per-leg x per-language x per-length-bucket report with <10 suppression and named suppressed groups; groups never render as zero"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestGroups"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestTwoLegDefault::test_small_group_is_suppressed_and_named_in_json_and_table"
        status: pass
    human_judgment: false
  - id: D4
    description: "PersonalReport carries mode/retrieval/top_k/corpus(documents,sampled,fingerprint,widened)/model/records; to_dict keeps every Plan 01 key and adds top_k/splits/groups/suppressed/replay; records store rank-aligned retrieved_doc_ids and retrieved_paths"
    requirement: EVAL-01
    verification:
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestPersonalReport"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestPersonalEvalCli::test_personal_json_is_strict_and_shaped"
        status: pass
    human_judgment: false
  - id: D5
    description: "query_log replay leg: normalized/deduped/sorted and capped at 500; empty history is available:false without failing; one search per unique query with rank-ordered paths; CLI-only bias note in table and JSON; replay never enters known-item metrics/splits/groups"
    requirement: EVAL-01
    verification:
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestReplay"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestReplayCli"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-11-14
status: complete
plan_head_before: 90ee0206896cc8587eb3d2d1a7088f75d0f518d8
plan_head_after: 12c8014a29f5664911db8229faa328ff2d31766e
actuals:
  tokens: 25160
  tasks: 3
  commits: 3
---

# Phase 18 Plan 02: Personal Bench Body Leg, Bias Controls, and Replay Summary

**`sif eval --personal` now synthesizes title and body-snippet known-item queries with a per-leg 0.60 Jaccard budget, splits them deterministically into 50/50 tuning/held-out (widening the sample to meet the 25 held-out floor), reports every leg x language x length group with <10 suppression, and adds a normalized query_log replay leg labeled stability-not-quality with its CLI-only bias.**

## Performance

- **Duration:** 13 min (12m36s measured to the final task commit; metadata commit follows)
- **Started:** 2026-11-14T14:47:53Z
- **Completed:** 2026-11-14T15:00:29Z
- **Tasks:** 3 completed
- **Files modified:** 6 (1 created, 5 modified)
- **Estimate vs actual:** plan estimated 60,000 tokens; realized diff measured at 25,160 tokens (chars/4 over the `-U0` diff of src/scripts/tests/docs), 3 commits.

## Accomplishments

- Body-snippet leg: `strip_markup` removes fenced/inline code, URLs, links, HTML comments, ATX headings, and emphasis; `body_candidate` picks one later prose sentence (deterministic first match past the 200-char opening), caps at 10 length units, and rejects below 4. CJK ideographs count one unit each, so Chinese candidates are not collapsed into one FTS token.
- Per-leg overlap budget enforced by construction: title queries are `budget=None`/`exact_term=True` with zero overlap rejections; body queries reject `> 0.60` token Jaccard against the target title plus first 200 chars (exactly 0.60 accepted, pinned by constructed 3/5 and 4/6 sets). Empty, overlap, and duplicate rejections are counted per leg.
- Cross-leg dedupe is deterministic regardless of input order: declared leg order (title before body) keeps the first record and increments the losing leg's duplicate count; two runs over the same docs yield identical query lists and counts.
- Deterministic split and widening: `assign_split` is `sha256(NFC/casefold/collapsed query)[0] < 128 -> tuning else heldout`; `ensure_heldout` starts from the first 50 documents in `(sha256, path, id)` order, doubles the prefix toward `min(corpus, 250)` while accepted < 50 OR held-out < 25, loads bodies only for newly added documents, and raises a counted ValueError naming accepted/tuning/held-out/rejections only at the cap. A 60-document fixture with 24 held-out queries in its initial slice widens to 60 (34 held-out) and evaluates documents outside the initial slice.
- Report contract: `PersonalReport.to_dict()` keeps every Plan 01 key (`mode`, `retrieval`, `corpus.documents/sampled/fingerprint`, `queries.accepted/rejected_empty/rejected_duplicate`, `metrics`, `notes`, `model`) and additively emits `top_k`, `queries.by_leg`, `splits`, `groups`, `suppressed`, and `replay`. `records[]` carry rank-aligned `retrieved_doc_ids`/`retrieved_paths` (one string per retrieved rank, `""` when absent) — Plan 03's grading identity.
- Groups: only count >= 10 rows are emitted in declared LEGS x LANGUAGES x LENGTH_BUCKETS order; 1–9-query groups are omitted and named (`leg=.../language=.../length=...`). A CLI fixture with 9 Chinese titles proves the zh/medium group is suppressed and named in both JSON and table.
- Replay leg: `load_replay_queries` reads `QueryLogRepository.history()`, normalizes/dedupes/sorts lexicographically (never SQL row order), drops empties, and caps at 500. `replay_leg` runs one search per unique query, stores rank-ordered paths only, and always reports `available`, `num_queries`, `baseline_available: false`, and the bias note. An empty `query_log` exits 0; replay changes no known-item metric, split, or group (asserted byte-equal).
- CLI: the default run evaluates title+body over the widened sample; the table renders summary, per-leg budget/rejection counts, groups, suppressed names, replay counts and the full CLI-only bias note; `--json` is strict JSON.

## Task Commits

Each task was committed atomically (normal hooks, no `--no-verify`):

1. **Task 1: Body-snippet leg, per-leg overlap budget, cross-leg dedupe, classification** - `eee35ee` (feat)
2. **Task 2: Deterministic hash split, held-out widening, and suppressed group report** - `96c93cd` (feat)
3. **Task 3: query_log replay leg with CLI-only bias disclosure** - `12c8014` (feat)

**Plan metadata:** `docs(18-02): complete personal bench bias-control plan` (the commit following this SUMMARY)

## Files Created/Modified

- `src/sif/search/personal_bench.py` - Task 1–3 domain surface: `_TOKEN_RE`/`token_set`/`jaccard`, `strip_markup`, `body_candidate`, `load_sampled_content`, `synthesize_body_queries`, `apply_overlap_budget`, `classify_language`, `length_bucket`, `synthesize_known_item_queries`, `INITIAL_SAMPLE_DOCUMENTS`, `assign_split`, `split_queries`, `ensure_heldout`, `MAX_REPLAY_QUERIES`/`REPLAY_BIAS_NOTE`, `load_replay_queries`, `replay_leg`, `GroupMetrics`/`group_metrics`, `PersonalQueryRecord`/`build_query_records`, `CorpusSummary`, `ReplayResult`, `PersonalReport`/`build_personal_report`.
- `src/sif/cli/commands/eval.py` - widened two-leg runner, replay wiring, summary/per-leg/groups/suppressed/replay rendering; renders only `report.to_dict()`.
- `tests/support/eval.py` - bodies long enough for body candidates (candidate sentence past 200 chars) and a `bodies=` override for split-control fixtures.
- `tests/unit/search/test_personal_bench.py` (new) - EVAL-01/EVAL-02 domain battery (43 tests): strip/body candidate, budget boundaries, dedupe determinism, classification thresholds, split, widening (including content-load counts), suppression/order, report identity, replay, minimum guard.
- `tests/unit/cli/test_eval.py` - updated Plan 01 expectations for the two-leg default; new widening, suppressed-group, two-leg, and replay tests (29 tests).
- `docs/cli-reference.md` - regenerated by the generator for the updated `sif eval` help text.

## Decisions Made

- Title synthesis keeps internal dedupe so the Plan 01 title-only surface stays backward-compatible; the orchestrator adds cross-leg dedupe in declared leg order.
- Body-candidate floors/caps count length units (ASCII token or CJK ideograph) rather than raw FTS tokens, aligning the 4-token floor with the pinned CJK length-unit rule; the emitted query keeps a contiguous CJK run.
- `ensure_heldout` re-synthesizes the entire deterministic prefix per doubling but loads content only for newly added ids — the metadata-only whole-corpus pass invariant holds.
- `group_metrics` suppresses only present groups with 1–9 queries; zero-query combinations have no rendered cell and are not listed.
- Plan 01 flat rejection keys remain integer totals (`sum(dict.values())`), so existing JSON consumers do not move.
- `ReplayResult.top_k_paths` serializes as `replay.queries`; the fixed bias note is printed untruncated (the 80-char cell cap previously hid the CLI-only half).
- The generator-owned `docs/cli-reference.md` is regenerated alongside the help-text change to keep the docs CI diff gate clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Minimal CLI adaptation in Task 1 despite "do not touch the CLI"**
- **Found during:** Task 1 (domain rewrite)
- **Issue:** `SynthesisResult` rejection counts became per-leg dicts as specified, which would have broken `_personal_payload` (JSON values) and `require_minimum_queries` (arithmetic) — the CLI tests would fail and the tree would not be green at the task boundary.
- **Fix:** `_personal_payload` emits `sum(...values())` for the Plan 01 flat integer keys; `require_minimum_queries` sums the dicts. The CLI flow itself remained title-only until Task 2 as planned.
- **Files modified:** `src/sif/cli/commands/eval.py`, `src/sif/search/personal_bench.py`
- **Verification:** Plan 01's 22 CLI tests stayed green after Task 1.
- **Committed in:** `eee35ee` (Task 1 commit)

**2. [Rule 3 - Blocking] Regenerated the generator-owned CLI reference**
- **Found during:** Final plan verification
- **Issue:** The task required updated `sif eval` help text, which feeds `docs/cli-reference.md`; the docs CI gate runs `git diff --exit-code` after regenerating, so leaving it stale fails the gate.
- **Fix:** Ran `python scripts/generate_cli_ref.py` and committed the regenerated section (description only; no new options).
- **Files modified:** `docs/cli-reference.md`
- **Verification:** `python scripts/generate_cli_ref.py && git diff --exit-code docs/cli-reference.md docs/configuration.md` is clean.
- **Committed in:** `12c8014` (Task 3 commit)

**3. [Rule 2 - Missing critical verification] Pinned the remaining Plan 01 domain guard and the conn-loading path**
- **Found during:** Final plan verification
- **Issue:** `require_minimum_queries` is no longer called by the CLI (ensure_heldout owns the floor) and `synthesize_known_item_queries(conn=...)` was only exercised indirectly, leaving the Plan 01 API and the bounded-content-load contract unpinned.
- **Fix:** Added `TestMinimumGuard` (raise/pass with counted breakdown) and `TestOrchestratorContentLoading` (bodies load only for the given records).
- **Files modified:** `tests/unit/search/test_personal_bench.py`
- **Verification:** targeted suite 72 passed; full suite 1746 passed, 1 skipped at 95.09% coverage.
- **Committed in:** `12c8014` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 missing critical verification).
**Impact on plan:** No functional scope change. The CLI touch was the minimum needed to keep the interface change atomic; the docs regeneration keeps the CI gate honest.

## Issues Encountered

- Plan 01's `< 50 accepted` test assumed a title-only run; with the body leg it could no longer trip. Rewritten to fail both legs (11 empty titles + 60 empty bodies → 49 accepted) so the counted floor is still proven end to end.
- The default 60-document fixture now evaluates the initial 50-document slice (100 queries: 50 title + 50 body, 47 held-out), not all 60 documents; Plan 01 assertions for `corpus.sampled` and `queries.accepted` were updated accordingly.
- The empty-title and duplicate-title edge tests needed exactly 50 documents so the special documents are always in the initial slice; at 60 documents the absolute tmp path changes the sha256 sample order and made membership path-dependent.
- The table's 80-character cell truncation hid the "CLI-biased" half of the replay note; the fixed module constant is now printed in full (escaped, not truncated).
- CJK body candidates initially failed the 4-token floor (a whole run is one FTS token); switched the floor/cap to length units while keeping the emitted query as a contiguous run.

## User Setup Required

None - no external service configuration required. No package was installed (rapidfuzz remains Phase 18 Plan 04's blocking checkpoint).

## Threat Surface Scan

No new security-relevant surface beyond the plan's threat model. Mitigations verified: T-18-04 replay stores query text and rank-ordered paths only (tests assert no `content` key and no document body in stdout/JSON); T-18-05 caps hold (10-token body candidates, 500 replay queries, bodies only for the sampled subset, chunked `IN (?)` SELECTs — the whole-corpus pass remains metadata-only); T-18-06 group names come from fixed enums and query/model-derived cells are escaped; T-18-SC — no dependency install in this plan.

## Next Phase Readiness

- Plan 18-03 can build `run_to_saved` from `PersonalReport.records` (query/target id/path/leg/language/length/split/metrics plus rank-aligned `retrieved_doc_ids`/`retrieved_paths`), `PersonalReport.corpus`, `top_k`, `model`, and `ReplayResult.top_k_paths`; `to_dict()` already carries every saved-run input additively.
- Plan 18-03 must still add `--compare`/`--no-save`, saved-run validation, the paired bootstrap gate, and the comparison renderer; no Plan 02 contract needs to change.
- No blockers. Final gates: full pytest 1746 passed / 1 skipped at 95.09% coverage (fail_under 90), `ruff check` + `ruff format --check`, `ty check src/sif`, docs generation diff clean, and `python scripts/generate_bench_fixture.py --check` clean.

## Self-Check: PASSED

- FOUND: src/sif/search/personal_bench.py
- FOUND: src/sif/cli/commands/eval.py
- FOUND: tests/support/eval.py
- FOUND: tests/unit/search/test_personal_bench.py
- FOUND: tests/unit/cli/test_eval.py
- FOUND: docs/cli-reference.md
- FOUND: eee35ee (Task 1)
- FOUND: 96c93cd (Task 2)
- FOUND: 12c8014 (Task 3)

---
*Phase: 18-quality-instrument-personal-bench-rapidfuzz-dym*
*Completed: 2026-11-14*
