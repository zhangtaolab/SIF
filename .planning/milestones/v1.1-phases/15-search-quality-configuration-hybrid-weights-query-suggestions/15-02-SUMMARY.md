---
phase: 15-search-quality-configuration-hybrid-weights-query-suggestions
plan: 02
subsystem: search
tags: [fts5vocab, suggestion-engine, did-you-mean, difflib, query-history, sqlite, pydantic-settings, docs-generator]

requires:
  - phase: 15-search-quality-configuration-hybrid-weights-query-suggestions
    provides: 15-01 SearchOptions/settings surfaces and the weighted-fusion seam (untouched here)
  - phase: 11-live-index-foundation-concurrent-db-incremental-core
    provides: SQLite FTS5 schema + the short-CRUD-outside-the-flock contract (Phase 11 D-01) query_log writes follow
provides:
  - documents_fts_v — fts5vocab row-mode vocab shadow (schema-managed + engine lazy ensure) enumerating porter stems with doc frequency (D-06)
  - SuggestionEngine — vocab prefix completions, per-word did-you-mean rewrites, history ranking (one engine, three future hosts)
  - query_log table + idx_query_log_created (create_all/drop_all registered) with trim-in-write cap (D-09)
  - QueryLogRepository — add (INSERT+trim) / history (one GROUP BY aggregate) / clear (rowcount)
  - QueryLogEntry aware-UTC dataclass (metadata only, never document content)
  - SIF_QUERY_HISTORY_ENABLED / SIF_QUERY_HISTORY_LIMIT settings, documented via the generator
affects: [15-03, 16-search-quality-bench-sweep]

actuals:
  tokens: 12339 # chars/4 over the realized diff (49,356 diff chars); plan estimate 34,000
  tasks: 3
  commits: 5
  plan_head_before: fe81f13252914cb1293361c3c9655df7b8a15be8
  plan_head_after: 04d0d93a17034313d90bf880d1cb880a6659179d

tech-stack:
  added: [] # zero new runtime dependencies (difflib/bisect/math/sqlite3 stdlib only)
  patterns:
    - "Zero-behavior skeleton in the RED commit (Phase 11 precedent) so a new-module test battery fails on its assertion, never an import error"
    - "Lazy vocab ensure: the same idempotent fts5vocab DDL runs in SchemaManager AND on first engine use (old DBs / MCP connections never run init_schema)"
    - "Retrievability predicate = prefix-range membership via bisect (porter stems both sides through the quoted-prefix form); no Python porter stemmer needed"
    - "First-letter±1 bucket before difflib; explicit (ratio desc, term asc) re-sort so equal-ratio ties resolve in sorted-term order regardless of difflib's nlargest heap order"
    - "History decay in Python over one GROUP BY aggregate: count x 2^(-age_days/14), multi-pass stable sorts for count/last_used/lexical tie-breaks"

key-files:
  created:
    - src/sif/search/suggest.py
    - tests/unit/search/test_suggest.py
    - tests/unit/database/test_query_log_repo.py
  modified:
    - src/sif/database/schema.py
    - src/sif/database/repositories.py
    - src/sif/core/models.py
    - src/sif/config/settings.py
    - scripts/generate_config_ref.py
    - docs/configuration.md
    - tests/unit/database/test_schema.py
    - tests/unit/config/test_settings.py

key-decisions:
  - "Vocab shadow lives in the main schema (temp-schema fts5vocab cannot reference main FTS, Pitfall 8) and is re-ensured lazily by the engine for connections that never ran init_schema"
  - "In-vocab predicate locked to prefix-range membership (bisect, both directions) — over-tolerant by design; revisitable only if UAT shows DYM noise (RESEARCH open question 2 resolved)"
  - "difflib matches are re-sorted by (ratio desc, term asc): get_close_matches uses heapq.nlargest, whose equal-key order is not input order — the truth requires stable sorted-term order"
  - "One uncorrectable out-of-vocab word poisons the whole rewrite (returns []) — every emitted suggestion must have every word retrievable (SC2 by construction)"
  - "History decay half-life 14 days; ranking count x 2^(-age/14) with count desc -> last_used desc -> lexical asc tie-breaks; settings gate is fail-soft ([] on disabled or settings failure)"
  - "query_log writes/read stay short CRUD outside the flock (Phase 11 D-01); created_at is aware UTC (WR-03 cautionary, never naive local)"

patterns-established:
  - "Suggestion engine degradation contract: every sqlite3.OperationalError path (read-only DB, missing vocab/query_log) returns empty with logger.warning — never raises through a search command"
  - "RED evidence via pytest --junitxml (a supported report format) when the native runner prints pytest-style output: record {command, exitCode, output, targetTest, targetFile, expected, actual, semanticAssessment} -> RED_EVIDENCE_OK"

requirements-completed: [QUAL-02, QUAL-03, QUAL-04]

coverage:
  - id: D1
    description: "documents_fts_v fts5vocab row-mode vocab shadow: created by create_all, enumerates real porter stems with doc counts, dropped by drop_all"
    requirement: QUAL-02
    verification:
      - kind: unit
        ref: "tests/unit/database/test_schema.py#TestVocabShadowTable::test_create_all_creates_vocab_table_enumerating_stems"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_schema.py#TestVocabShadowTable::test_drop_all_removes_vocab_table"
        status: pass
    human_judgment: false
  - id: D2
    description: "SuggestionEngine prefix completions: min length 2, case-insensitive bisect scan, df-then-lexical ranking, every completion hits as a real BM25 query, empty/missing/read-only degradation"
    requirement: QUAL-04
    verification:
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestPrefixCompletions::test_completions_are_real_queryable_stems"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestPrefixCompletions::test_completions_rank_by_doc_frequency_then_lexical"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestVocabDegradation"
        status: pass
    human_judgment: false
  - id: D3
    description: "DYM per-word rewrites: full rewritten queries, in-vocab words kept, bucketed difflib with cutoff 0.75, no forced DYM, SC2 pin (every suggestion returns >=1 hit), 66k-term budget with deterministic bucket assertion"
    requirement: QUAL-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestDidYouMean::test_rewrites_full_query_per_out_of_vocab_word"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestDidYouMean::test_every_suggestion_hits_as_query"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestCoreBudget::test_bucketed_dym_under_budget_on_60k_vocab"
        status: pass
    human_judgment: false
  - id: D4
    description: "query_log storage: QueryLogEntry aware-UTC metadata, schema + index registration, add persists, trim-in-write boundary keeps exactly N with the oldest gone, clear returns rowcount"
    requirement: QUAL-03
    verification:
      - kind: unit
        ref: "tests/unit/database/test_query_log_repo.py#TestAddPersistence::test_add_persists_row_with_aware_utc_stamp"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_query_log_repo.py#TestTrimInWrite::test_inserting_beyond_keep_leaves_exactly_keep_oldest_gone"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_query_log_repo.py#TestClear::test_clear_deletes_all_rows_and_reports_count"
        status: pass
    human_judgment: false
  - id: D5
    description: "History ranking: one GROUP BY aggregate, count x recency decay ordering, case-insensitive prefix filter, cold start empty, D-10 read gate (disabled or settings failure -> []), missing table degrades"
    requirement: QUAL-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestHistory::test_history_ranks_frequency_times_recency"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestHistory::test_history_read_gate_disabled_returns_empty"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestHistory::test_history_settings_failure_returns_empty"
        status: pass
    human_judgment: false
  - id: D6
    description: "SIF_QUERY_HISTORY_ENABLED / SIF_QUERY_HISTORY_LIMIT settings (default True / 500 ge=1), registered in the docs generator SECTIONS, docs/configuration.md regenerated and idempotent"
    requirement: QUAL-03
    verification:
      - kind: unit
        ref: "tests/unit/config/test_settings.py#test_query_history_limit_rejects_zero_naming_the_field"
        status: pass
      - kind: other
        ref: "make docs-generate && git diff --exit-code docs/configuration.md (idempotent regen; SIF_QUERY_HISTORY_ENABLED / SIF_QUERY_HISTORY_LIMIT present)"
        status: pass
      - kind: other
        ref: "env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -x --no-cov (13 passed)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-11-08
status: complete
---

# Phase 15 Plan 02: Suggestion Engine Core (QUAL-02/03/04) Summary

**FTS5 vocab shadow + SuggestionEngine (prefix completions, per-word DYM rewrites with an SC2 pin, frequency×recency history) + capped aware-UTC query_log storage — the one engine three hosts wire in 15-03.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-11-08T10:15:38Z
- **Completed:** 2026-11-08T10:36:00Z
- **Tasks:** 3 (1 tracer TDD + 1 TDD + 1 auto)
- **Files modified:** 11 (8 planned + 2 test additions + 1 settings-test deviation)

## Accomplishments

- Tracer slice proven end-to-end: `documents_fts_v` (fts5vocab row mode) is created by `create_all` and lazily re-ensured by the engine for old DBs; prefix completions return real porter stems that every one of them hits when re-run as a BM25 query (SC2's structural guarantee, pinned against the real searcher)
- `SuggestionEngine.did_you_mean` rewrites full queries per out-of-vocab word (in-vocab words kept as typed), using a first-letter±1 bucket before `difflib.get_close_matches(n=3, cutoff=0.75)`; every emitted suggestion returns ≥1 hit; no forced DYM when all words retrieve; uncorrectable words yield no suggestion
- Deterministic budget proof: 66k-term synthetic vocab, full core < 1.0 s, spied difflib bucket < 10% of the vocabulary (no wall-clock races)
- `query_log` storage with aware-UTC stamps, trim-in-write cap (never exceeds `keep`), one GROUP BY aggregate, and a single clear path — local metadata only, never document content
- `history_suggestions` ranks count × 2^(−age_days/14) with deterministic tie-breaks; D-10 read gate is fail-soft (disabled setting / settings failure / missing table → `[]`)
- Settings + docs through the generator only: `SIF_QUERY_HISTORY_ENABLED` / `SIF_QUERY_HISTORY_LIMIT` documented, regen idempotent, docs gate green

## Task Commits

Each task was committed atomically (TDD tasks carry RED + GREEN commits):

1. **Task 1 RED: failing vocab/prefix battery** - `44f46fb` (test)
2. **Task 1 GREEN: vocab shadow + engine prefix completions** - `7f10b10` (feat)
3. **Task 2 RED: failing DYM battery** - `79d09c0` (test)
4. **Task 2 GREEN: per-word DYM rewrites (bucketed difflib)** - `2c7108b` (feat)
5. **Task 3: query_log storage + history ranking + settings + docs** - `04d0d93` (feat)

**Plan metadata:** (recorded at completion)

_Note: TDD tasks produced two commits each (test → feat); no REFACTOR commit was needed._

## TDD Gate Compliance

| Plan | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| 15-02 Task 1 (tracer) | `44f46fb` ✓ | `7f10b10` ✓ | — (not needed) | Pass |
| 15-02 Task 2 | `79d09c0` ✓ | `2c7108b` ✓ | — (not needed) | Pass |

Both RED phases committed an importable zero-behavior skeleton with the failing battery (Phase 11 pattern), so the target failed on its planned assertion, never an import error. Evidence was captured as JUnit XML (`pytest --junitxml`) and validated with `gsd_run check tdd-red-evidence`:

- Task 1: `RED_EVIDENCE_OK`, target `test_completions_are_real_queryable_stems` failed on `assert completions` (skeleton returned `[]`); 33 tests, 4 planned-behavior failures, 29 passes. Semantic assessment: target executed and failed on the planned assertion; no fixture/load/syntax faults, no unexpected green on a planned-positive behavior.
- Task 2: `RED_EVIDENCE_OK`, target `test_rewrites_full_query_per_out_of_vocab_word` failed on `[] == ["quantum machin"]`; 16 tests, 5 planned-behavior failures. Negative cases (no-DYM-when-retrieves, uncorrectable, empty) pass at RED as expected for a `[]`-returning skeleton.

The Task 1 tracer feedback gate re-ran the exact `<verify>` end-to-end after GREEN (33 passed) before Task 2 expanded. No RED or GREEN commit is missing.

## Files Created/Modified

- `src/sif/search/suggest.py` — `SuggestionEngine` (lazy vocab ensure/load, `prefix_completions`, `did_you_mean`, `history_suggestions`) + `_rank_history`/`_ratio` helpers; all OperationalError paths degrade to empty
- `src/sif/database/schema.py` — `documents_fts_v` DDL in `_create_fts_tables`; `_create_query_log_table` (table + descending index); create_all/drop_all registration
- `src/sif/database/repositories.py` — `QueryLogRepository.add/history/clear` (parameterized, trim-in-write, rowcount)
- `src/sif/core/models.py` — `QueryLogEntry` (aware-UTC `created_at`, `collections` list, `to_dict`)
- `src/sif/config/settings.py` — `query_history_enabled` (True), `query_history_limit` (500, ge=1)
- `scripts/generate_config_ref.py` — both fields registered in the Search Settings SECTIONS entry
- `docs/configuration.md` — generator output only (never hand-edited)
- `tests/unit/search/test_suggest.py` — prefix/DYM/degradation/budget/history batteries
- `tests/unit/database/test_query_log_repo.py` — schema registration, persistence, trim boundary, aggregate, clear on real SQL
- `tests/unit/database/test_schema.py` — vocab shadow table creation/stem enumeration/drop isolation
- `tests/unit/config/test_settings.py` — history settings defaults/env reach/validation (deviation addition)

## Decisions Made

- Vocab shadow is main-schema and re-ensured lazily by the engine (temp-schema fts5vocab cannot reference main FTS; MCP connections never run `init_schema`)
- In-vocab predicate locked to prefix-range membership (bisect, both directions), per the plan's resolved open question — over-tolerant by design, revisitable only if UAT shows noise
- difflib matches re-sorted by (ratio desc, term asc): `get_close_matches` uses `heapq.nlargest`, whose equal-key order is not the input order — the plan's stable sorted-term-order truth is enforced explicitly
- An out-of-vocab word with no close match returns `[]` for the whole query — emitted suggestions must have every word retrievable (SC2 by construction)
- History half-life 14 days; ranking via multi-pass stable sorts (score desc → count desc → last_used desc → lexical asc); settings gate fail-soft

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restored the all-retrievable → `[]` guard in `did_you_mean`**
- **Found during:** Task 2 GREEN (first implementation pass)
- **Issue:** The first implementation appended kept tokens for an all-retrievable query but never returned `[]`, emitting the input query itself as a "suggestion" (caught by `test_no_dym_when_every_word_retrieves`: `['quantum machines'] == []` failed)
- **Fix:** Track the slot plan; when every slot is a kept token, return `[]` (D-07 — never a forced suggestion). Extracted into `_dym_slots` for the complexity gate
- **Files modified:** src/sif/search/suggest.py
- **Verification:** TestHistory/DYM battery green (16 passed)
- **Committed in:** 2c7108b

**2. [Rule 1 - Bug] Stabilized difflib equal-ratio tie order**
- **Found during:** Task 2 GREEN (variant-depth test)
- **Issue:** `difflib.get_close_matches` ranks with `heapq.nlargest`, so equal-ratio matches (`corner`/`cornet` vs `cornex`, both 10/12) came back in heap order (`['cornet', 'corner']`) rather than the sorted-term order the plan's truth requires
- **Fix:** After the difflib call, re-sort matches by `(ratio desc, term asc)` via a `_ratio` helper — ratio order is preserved; only ties are stabilized, independent of interpreter internals
- **Files modified:** src/sif/search/suggest.py
- **Verification:** `test_variant_depth_follows_close_match_order` + determinism test green
- **Committed in:** 2c7108b

**3. [Rule 2 - Missing critical] Settings validation tests added to tests/unit/config/test_settings.py**
- **Found during:** Task 3 test authoring
- **Issue:** The plan's acceptance criteria require `query_history_limit` ge=1 and the enabled default, but its file list has no natural home for direct Settings-level assertions (the engine tests prove the read gate, not the Pydantic field constraints in isolation)
- **Fix:** Added defaults/env/validation tests in the established settings-test module (same treatment 15-01 gave its fusion fields)
- **Files modified:** tests/unit/config/test_settings.py
- **Verification:** 3 new tests pass; full module green
- **Committed in:** 04d0d93

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 missing critical test coverage)
**Impact on plan:** All fixes were required for the plan's own truths (D-07 no-forced-DYM, deterministic tie order, settings validation). No scope creep — zero new runtime dependencies, no new surfaces beyond the artifacts table.

## Issues Encountered

- **DYM test-shape wording vs the locked predicate:** the plan's Task 2 behavior bullet illustrates `"quantum machin"` over a corpus containing "quantum machine", but under the plan's own locked prefix-range predicate (and porter stems) `machin` already retrieves — it is not a DYM candidate. The acceptance criterion ("returns `[]` when every token's prefix range hits the vocab") is authoritative, so the D-07-shape test uses a genuinely non-retrievable typo (`"quantum machien"` → `"quantum machin"`, stem display per RESEARCH A1). Behavior matches the criteria; only the illustrative example differed.
- **Docs-only pytest run and the coverage floor:** `pytest tests/test_docs.py -x` exits non-zero on the global `fail_under=90` coverage floor (29.72% on a docs-only subset) even with all 13 tests passing — the known v1.0 decision (`--no-cov` for docs-only suites, CI-aligned). Verified with `--no-cov`: 13 passed; the full-suite run keeps the permanent coverage gate (94.61%).
- **RED report format:** pytest's native console output is not a classifier-supported report format, so RED evidence was captured as JUnit XML via pytest's built-in `--junitxml` (a supported adapter) — records persisted under `.planning/tmp/15-02-task{,1,2}-red.{xml,json}`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 15-03 can wire three hosts against one engine: zero-result hooks on `sif search`/`vsearch`/`query`, the `sif suggest` command (prefix + DYM + history, `--json`, `--clear-history`), and the MCP query response — `prefix_completions(prefix, n=5)`, `did_you_mean(query, n=3)` and `history_suggestions(prefix="", n=5)` all carry defaults, and `QueryLogRepository.add(entry, keep)` is ready for the write hook
- Engine degradation is uniform: no host needs its own try/except around suggestions (all OperationalError and settings failures return empty lists)
- `SIF_QUERY_HISTORY_ENABLED` / `SIF_QUERY_HISTORY_LIMIT` are live settings; docs regenerate cleanly through the generator
- Stem display is the shipped UX (RESEARCH A1) — surface for UAT expectation setting; surface-form mapping remains a v2 candidate

## Self-Check: PASSED

- Files: `src/sif/search/suggest.py`, `tests/unit/search/test_suggest.py`, `tests/unit/database/test_query_log_repo.py` and all 8 modified files present on disk (git diff name-only vs base verified: 11 files, 1051 insertions)
- Commits: 44f46fb, 7f10b10, 79d09c0, 2c7108b, 04d0d93 all ancestors of HEAD (`git rev-list fe81f13..HEAD` = 5)
- Gates: full suite 1303 passed / 1 skipped @ 94.61% coverage (fail_under=90); ruff check + format green; ty green; engine+repo+schema battery 53 passed; docs gate 13 passed (`--no-cov`); `make docs-generate` + `git diff --exit-code docs/configuration.md` clean
- RED gates: `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK` for both TDD tasks (junit evidence records retained)

---
*Phase: 15-search-quality-configuration-hybrid-weights-query-suggestions*
*Completed: 2026-11-08*
