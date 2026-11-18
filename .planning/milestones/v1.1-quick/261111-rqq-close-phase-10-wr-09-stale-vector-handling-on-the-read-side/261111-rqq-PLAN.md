---
phase: quick-261111-rqq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/cli/main.py
  - src/sif/database/repositories.py
  - tests/unit/cli/test_main.py
  - tests/unit/database/test_repositories.py
  - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
autonomous: true
requirements:
  - PHASE10-WR-09
estimate:
  tokens: 20000
  raw_tokens: 20000
  tasks: 2
  confidence: low
must_haves:
  truths:
    - "sif cleanup removes llm_cache rows whose expiry instant has passed, including legacy naive-local ISO rows written by the old LLMCacheRepository.set, on hosts east AND west of UTC — comparison is by parsed datetime, never lexicographic string order"
    - "LLMCacheRepository.set stores expires_at as an aware-UTC ISO string (datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(), +00:00 suffix) so new rows carry an unambiguous instant"
    - "cleanup_cmd delegates cache expiry to LLMCacheRepository(conn).clear_expired() inside its existing transaction; orphaned-chunk/embedding cleanup, console output lines, confirmation prompt, and error handling are unchanged"
    - "The five new regression tests are red against the planning baseline (HEAD 802c08c) and green after the fix; all 29 existing tests in the three touched test files pass unmodified"
    - "Phase 10 WR-09 is recorded as fixed in both ledger representations, the open count is decremented by exactly 1 from its execution-time value, and every other finding record remains byte-identical"
  artifacts:
    - src/sif/cli/main.py
    - src/sif/database/repositories.py
    - tests/unit/cli/test_main.py
    - tests/unit/database/test_repositories.py
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
  key_links:
    - "cleanup_cmd -> LLMCacheRepository(conn).clear_expired() on the same transaction connection -> parse-and-compare datetime predicate -> parameterized DELETE by id (no second SQL dialect for the same rule)"
    - "LLMCacheRepository.set aware-UTC write -> clear_expired fromisoformat parse -> naive legacy strings interpreted as system-local via astimezone(timezone.utc) (the exact semantics of the old datetime.fromtimestamp writer)"
    - "WR-09 YAML disposition + WR-09 markdown row + execution-time open-count decrement -> one consistent review ledger with no unrelated edits"
---

<objective>
Close Phase 10 WR-09 only: `cleanup` compares naive-local ISO timestamps against aware-UTC ISO strings lexicographically. The original finding (10-REVIEW.md, "WR-09") names two production sites and one reuse:

1. Read side — `cleanup_cmd` in `src/sif/cli/main.py` (finding cited lines 181-189; live at HEAD 802c08c: lines 254-264) deletes expired `llm_cache` rows with an inline `DELETE ... WHERE expires_at <= ?` bound to `datetime.now(timezone.utc).isoformat()`, re-implementing `LLMCacheRepository.clear_expired()` inline.
2. Write side — `LLMCacheRepository.set` in `src/sif/database/repositories.py` (finding cited 531-536; live: line 551) stores `expires_at` as `datetime.fromtimestamp(expires_at).isoformat()` — a NAIVE LOCAL-time string with no offset suffix.
3. The finding's fix: "Parse and compare as datetimes, reusing the repository method" (`cache_removed = LLMCacheRepository(conn).clear_expired()`) "and fix the write side to store `datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()`".

Live defect reproduction at planning time (HEAD 802c08c, real in-memory SQLite with the production llm_cache DDL, TZ forced to Asia/Shanghai via time.tzset): a legacy naive-local row for an instant 1 hour in the past stored as `2026-11-11T19:07:12.958061` while aware now was `2026-11-11T12:07:12.958061+00:00` — the current lexicographic DELETE returned rowcount 0 (expired row KEPT, exactly the reported east-of-UTC retention bug). The post-fix predicate (`datetime.fromisoformat(value).astimezone(timezone.utc) <= now`, naive presumed system-local) selects precisely that row for deletion. The old writer's string has no `+00:00` suffix; the finding's new writer form produces `2026-11-11T11:07:12.958061+00:00` for the same instant. The regression contract is non-vacuous.

Legacy-row semantics wrinkle (decided): fixing the write side does NOT rewrite existing rows. Legacy naive strings are local-time encodings, so the read side must interpret naive values as system-local time — `datetime.fromisoformat(...).astimezone(timezone.utc)` does exactly that (Python presumes the system timezone for naive values), matching the old writer's `datetime.fromtimestamp` semantics. Aware values pass through unchanged. Unparseable `expires_at` values are skipped (row retained): cleanup must neither destroy nor crash on a row it cannot interpret; NULL expiries stay exempt as today.

Purpose: make cache expiry correct by instant on every host timezone, with one datetime-comparison implementation shared by the CLI and the repository.
Output: corrected write side and clear_expired in repositories.py, delegation in cleanup_cmd, five real-SQLite regression tests (red-to-green), and WR-09 marked fixed without disturbing any other review item.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
@src/sif/cli/main.py
@src/sif/database/repositories.py
@tests/unit/cli/test_main.py
@tests/unit/database/test_repositories.py

Planning evidence (all grounded live at HEAD 802c08c):
- Read side: `src/sif/cli/main.py:254-264` — inside `with db.transaction() as conn:`, after the orphaned-chunk and orphaned-embedding DELETEs, a function-local `from datetime import datetime, timezone  # noqa: PLC0415` (line 255) feeds the inline lexicographic DELETE (257-263) and `cache_removed = cursor.rowcount` (264). `datetime`/`timezone` appear NOWHERE else in main.py (grep-verified: only lines 255 and 262), so the local import is deleted outright with the block. The three console lines (266-269), the confirmation option, the missing-index early return, and the try/except ClickException wrapper stay byte-identical.
- Write side: `src/sif/database/repositories.py:548-551` — `expires_at = datetime.now(timezone.utc).timestamp() + ttl_seconds` then `expires_at = datetime.fromtimestamp(expires_at).isoformat()` (naive local). `datetime, timezone` are already module-level imports (line 7). `created_at` (line 565) is already aware-UTC — do not touch it.
- `clear_expired` (repositories.py:570-576) currently has the SAME lexicographic defect as the inline CLI SQL — the finding's "parse and compare as datetimes, reusing the repository method" therefore requires fixing clear_expired itself, not just delegating to it. `LLMCacheRepository.get` (526-537) shares the defect class but is NOT named by WR-09 — it stays byte-identical (scope discipline; a get-side fix would be a separate finding).
- Connections: both call paths set `row_factory = sqlite3.Row` — production `create_connection` (factory.py:63) and the test_repositories.py `db` fixture (line 35) — so `row["id"]` / `row["expires_at"]` access is safe in clear_expired.
- Consumers: grep shows NO production caller of `LLMCacheRepository.set/get/clear_expired` outside the repository itself and the new cleanup delegation — the write-side format change cannot break any other command.
- Tests: `tests/unit/cli/test_main.py` `TestCleanupRealDatabase` (lines 141-193) uses `RealDatabaseTestCase` helpers `_invoke` (CliRunner, `--index <tmp>`, input "y\n" for confirm, COLUMNS=200) and `_seed_document`/`_seed_cleanup_rows` (real repositories + raw INSERT with PRAGMA foreign_keys relaxation). The existing `_seed_cleanup_rows` seeds AWARE-UTC expiries (`now ± timedelta(days=1)` with tz-aware now) — its assertions hold before AND after the fix; do not modify it. `tests/unit/database/test_repositories.py` has the module-level `db` fixture (real in-memory SQLite, production DDL via `SchemaManager._create_llm_cache_table()` etc.) and `test_llm_cache_hit_expiry_replacement_and_clear` (lines 465-483, inside TestRepositoryCoverage) which exercises set/get/clear_expired with aware-UTC strings — it must pass unmodified. `tests/unit/cli/test_database_lifecycle.py::test_cleanup_closes_database` patches `main_mod.Database` with a tracking subclass and must keep passing (delegation does not change Database ownership).
- Baseline grounded at planning time: `python -m pytest tests/unit/cli/test_main.py tests/unit/database/test_repositories.py tests/unit/cli/test_database_lifecycle.py -q --no-cov` → 29 passed in 0.88s at HEAD 802c08c; all five task-scoped files clean against HEAD.
- Timezone control for tests: the suite has no existing tzset precedent. The east-of-UTC regression needs a deterministic non-UTC local zone: a fixture sets `TZ=Asia/Shanghai` (fixed UTC+8, no DST) via monkeypatch.setenv and calls `time.tzset()`, restoring the prior TZ and calling `time.tzset()` again in teardown (process-global state — restoration is mandatory). `time.tzset` is Unix-only; guard the TZ-dependent tests with `pytest.mark.skipif(not hasattr(time, "tzset"), reason="tzset unavailable")` (execution hosts are macOS/Linux, where they run). The aware-UTC write-format and preservation tests need no TZ forcing and run everywhere. CliRunner executes in-process, so the forced TZ applies to cleanup_cmd too.
- NAMING COLLISION (do not confuse): main.py's `_get_default_db_path` docstring and `TestDefaultDbPathConfigError` in test_main.py reference "REVIEW WR-09" — that is the PHASE 11 settings-guard finding, a different review. This task closes the PHASE 10 WR-09 timestamp finding only; the settings guard and its tests stay byte-identical.
- Sibling overlap (batch 261111-rqo): item rqs (WR-01) also edits `src/sif/database/repositories.py`, but its region is `DocumentRepository.delete_by_collection` (~line 250, embedding purge) — DISJOINT from this plan's `LLMCacheRepository.set`/`clear_expired` region (lines 539-576). The file is still declared in files_modified so the scheduler serializes the overlap. Items rqp/rqq/rqs share the disposition ledger; ledger edits are execution-time-robust (Task 2) and the file is declared for the same reason. No logical prerequisite exists on any sibling — depends_on is empty.
- Ledger closure convention (verified against the live ledger and prior closure commits 68f4101/1ac9f24/15343bb): exactly three scoped edits — YAML `disposition: open` → `fixed` inside the WR-09 block, aggregate `open:` decrement by 1, and the WR-09 markdown row replacement with a Source cell naming quick 261111-rqq. NO `**Status:** resolved` lines in this ledger. The open count at planning time is 16, but siblings rqp/rqs may close their records first — Task 2 reads the CURRENT count at execution time and never hardcodes 16 or 15.
- Test environment: PATH python/pytest (miniconda base), NOT .venv (no torch). Targeted runs need `--no-cov` (coverage fail_under=90); the full-suite gate runs WITH coverage. The suite is color-env-hermetic (commit 6522663) — plain `python -m pytest` works.
- Discovery level 0: a local datetime-comparison correction inside two existing files, using each test file's established real-SQLite pattern; no new dependency, external integration, or schema change (llm_cache DDL untouched).
- Scope guard: WR-01/02/07/08 and every IN/CR finding stay untouched; `LLMCacheRepository.get`, the Phase 11 settings guard, generator-owned docs (docs/cli-reference.md, docs/configuration.md — never hand-edit; no signature/option/help change here, so no regeneration), and skills are out of scope. The working tree carries pre-existing uncommitted `.planning/` churn (config.json, state.json, agent-history.json, PATTERNS files, research cache, tmp/, 16-REVIEW iter2 files) — never stage, commit, or revert any of it; commits touch only task-scoped paths.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Pin and correct WR-09 stale-vector cache expiry (write side + read side, red-to-green)</name>
  <files>src/sif/database/repositories.py, src/sif/cli/main.py, tests/unit/database/test_repositories.py, tests/unit/cli/test_main.py</files>
  <behavior>
    - Under TZ=Asia/Shanghai, a legacy naive-local expires_at row encoding an instant 1 hour in the past is deleted by clear_expired (baseline keeps it: lexicographic order puts the local wall time ahead of the aware-UTC now string); a legacy naive-local row encoding an instant 1 hour in the future survives.
    - Under TZ=Asia/Shanghai, set(ttl_seconds=3600) stores an expires_at string ending "+00:00" whose parsed instant equals now-UTC + 3600s within a 5-second tolerance (baseline stores a naive local string: no offset suffix and a wall time 8 hours off).
    - Aware-UTC expired rows are deleted and aware-UTC fresh rows survive (passes before and after — preservation leg for the new format).
    - NULL and unparseable expires_at rows are retained and clear_expired returns 0 for a table containing only such rows (passes before and after — preservation).
    - CLI: under TZ=Asia/Shanghai, `sif cleanup` against a seeded index prints "Removed 1 expired cache entries", deletes the legacy naive-local expired row, keeps the fresh legacy row and the seeded document/chunk (baseline prints "Removed 0 expired cache entries" and keeps the expired row).
    - Preservation: all 29 existing tests in test_main.py, test_repositories.py, and test_database_lifecycle.py pass unmodified, including test_llm_cache_hit_expiry_replacement_and_clear, test_cleanup_preserves_valid_rows_and_removes_only_orphans, and test_cleanup_closes_database.
  </behavior>
  <action>
  FIRST change tests only. In tests/unit/database/test_repositories.py add `import time` to the stdlib imports and a module-level fixture `east_of_utc` (next to the existing `db` fixture): read the current TZ via os.environ.get("TZ") (add `import os`), monkeypatch.setenv("TZ", "Asia/Shanghai"), call time.tzset(), yield, then restore the prior TZ (setenv if it existed, delenv if it did not) and call time.tzset() again in a finally block. Then add a new class `TestLLMCacheExpiryWR09` using the existing `db` fixture with four tests: (1) `test_set_stores_aware_utc_expiry` — no TZ guard needed for the suffix leg but run it under east_of_utc for the instant leg: repo.set("model", "hash", "prompt", "response", ttl_seconds=3600); read expires_at via db.execute SELECT; assert it endswith "+00:00"; assert abs(datetime.fromisoformat(value) - (datetime.now(timezone.utc) + timedelta(seconds=3600))) < timedelta(seconds=5) (add timedelta to the datetime import). (2) `test_clear_expired_removes_legacy_naive_local_expired_row` — marked skipif(not hasattr(time, "tzset")), uses east_of_utc: compute expired_instant = (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() and fresh_instant = (now + 1h).timestamp(); insert two rows via direct parameterized INSERT into llm_cache (id 'legacy-expired'/'legacy-fresh', model_name 'm', distinct prompt_hash, prompt 'p', response 'r', created_at now-UTC isoformat) with expires_at = datetime.fromtimestamp(instant).isoformat() — the exact naive-local form the old writer produced; assert repo.clear_expired() == 1; assert the expired id is gone and the fresh id survives (SELECT COUNT). (3) `test_clear_expired_aware_utc_rows` — portable, no TZ fixture: insert an aware-UTC expired row ((now - 1h).isoformat()) and an aware-UTC fresh row ((now + 1h).isoformat()); assert clear_expired() == 1 and the fresh row survives. (4) `test_clear_expired_retains_null_and_unparseable` — portable: insert one row with expires_at NULL and one with expires_at 'not-a-timestamp'; assert clear_expired() == 0 and both rows survive. In tests/unit/cli/test_main.py add the same `east_of_utc` fixture pattern inside `RealDatabaseTestCase` (or module level — match the file's style; add `import os`, `import time` and timedelta is already imported) and one test to `TestCleanupRealDatabase`: (5) `test_cleanup_removes_legacy_naive_local_expired_cache` — skipif tzset guard, east_of_utc: call self._seed_document(db_path); then with Database(db_path) as db, db.transaction() as conn insert the same two legacy naive-local rows as test 2 (expired 1h ago, fresh 1h ahead — construct via datetime.fromtimestamp of the UTC instants); result = self._invoke(db_path, "cleanup", confirm=True); assert exit 0, "Removed 1 expired cache entries" in result.output; open a plain sqlite3 connection and assert the expired id count is 0, the fresh id count is 1, and document-1/chunk-1 still exist. Do NOT modify any existing test, fixture, or helper in either file. Run both files plus test_database_lifecycle.py before any production edit and confirm tests 1, 2, and 5 fail on their assertions (baseline: naive write format; lexicographic retention of the expired legacy row; CLI reports 0 removed) while tests 3 and 4 and all 29 existing tests pass — failures must be assertion failures, never collection or setup errors.

  THEN modify production. In src/sif/database/repositories.py: (a) in `set`, change ONLY line 551 to pass the timezone: `datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()` — the finding's exact write-side fix; leave the ttl guard, the timestamp arithmetic, created_at, and the INSERT byte-identical. (b) Rewrite `clear_expired` to parse and compare as datetimes: bind now = datetime.now(timezone.utc); SELECT id, expires_at FROM llm_cache WHERE expires_at IS NOT NULL; for each row parse datetime.fromisoformat(row["expires_at"]) inside try/except ValueError — on ValueError skip the row (retain it; comment: cleanup never deletes a row whose expiry it cannot interpret); normalize with .astimezone(timezone.utc) (naive values are presumed system-local — the exact semantics of the legacy writer; aware values convert losslessly) and collect row["id"] when the normalized instant <= now; if the expired-id list is empty return 0; otherwise DELETE FROM llm_cache WHERE id IN (...) with one "?" placeholder per id joined by commas (values always parameterized — the placeholder string is the only interpolated part) and return cursor.rowcount. Keep the signature `def clear_expired(self) -> int` and update the docstring to name the WR-09 datetime comparison and the legacy naive-local interpretation. Do NOT touch `get`, `set`'s other lines, or any other repository class — WR-01's purge region (DocumentRepository.delete_by_collection, ~line 250) belongs to sibling item rqs and stays byte-identical.

  In src/sif/cli/main.py: add `from sif.database.repositories import LLMCacheRepository` at module level directly after the existing `from sif.database.database import Database` import (line 16) — no circular-import risk (repositories imports only core.models and utils.paths). In cleanup_cmd replace the entire expired-cache block (lines 254-264: the comment, the function-local datetime import with its noqa, the inline DELETE, and the rowcount binding) with the comment `# Clean up expired LLM cache (WR-09: datetime comparison in the repository)` and `cache_removed = LLMCacheRepository(conn).clear_expired()` — same transaction connection, same variable name, so the three console lines and everything else in cleanup_cmd stay byte-identical. The function-local datetime import is removed, not relocated (grep-verified: no other datetime/timezone use in main.py).

  Run ruff format on the four task files only if the format check complains. Do not edit LLMCacheRepository.get, the _get_default_db_path settings guard or TestDefaultDbPathConfigError (Phase 11's different WR-09), src/sif/cli/commands/collection.py or index.py (WR-01, sibling rqs), src/sif/cli/commands/get.py (IN-08, sibling rqp), src/sif/mcp/backend.py (WR-07/08), schema.py, generator-owned docs, or skills.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/database/test_repositories.py tests/unit/cli/test_main.py tests/unit/cli/test_database_lifecycle.py -q --no-cov &amp;&amp; ruff check src/sif/database/repositories.py src/sif/cli/main.py tests/unit/database/test_repositories.py tests/unit/cli/test_main.py &amp;&amp; ruff format --check src/sif/database/repositories.py src/sif/cli/main.py tests/unit/database/test_repositories.py tests/unit/cli/test_main.py</automated>
  </verify>
  <done>Tests 1, 2, and 5 failed on assertions before the production edits and all 34 tests (29 existing + 5 new) now pass; set stores aware-UTC +00:00 expiries; clear_expired deletes by parsed instant including legacy naive-local rows interpreted as system-local, retains NULL/unparseable/fresh rows; cleanup_cmd delegates to the repository on the same transaction with unchanged output lines; get, the settings guard, WR-01's purge region, and all existing tests are byte-identical/unmodified; ruff and formatting pass.</done>
</task>

<task type="auto">
  <name>Task 2: Close only WR-09 in the Phase 10 disposition ledger (execution-time-robust)</name>
  <files>.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md</files>
  <action>
  After Task 1 passes, make exactly three scoped updates in .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md. SHARED-LEDGER RULE: siblings rqp (IN-08) and rqs (WR-01) close records in this same file and may run before this item — read the CURRENT `open:` count from the file at execution time and decrement THAT value by 1; never hardcode the planning-time count (16) or any assumed successor as a replacement literal.

  1. In the WR-09 YAML finding block only, change `disposition: open` to `disposition: fixed`; preserve its id, severity, and title.
  2. Change the aggregate `open: N` line to `open: N-1` where N is the value read from the current file; leave `total: 22` and the original `recorded` timestamp unchanged.
  3. Replace the WR-09 markdown row `| WR-09 | warning | open | - |` with `| WR-09 | warning | fixed | quick 261111-rqq (cleanup delegates to LLMCacheRepository.clear_expired with parsed-datetime comparison; cache expiry written as aware-UTC; legacy naive-local rows interpreted as system-local; regression tests) |`.

  Preserve every other YAML block, markdown row, ordering, explanatory paragraph, and trailing newline byte-for-byte — including any closures siblings already landed. Do not introduce any `**Status:**` line (that format belongs to other ledger types). Do not edit the historical 10-REVIEW.md, other review ledgers, or STATE.md; the orchestrator owns quick-task state updates. Run the verification gate BEFORE committing the ledger edit; if the gate fails because the working ledger diverges from execution-time HEAD for reasons other than this task's three edits, halt and surface the divergence — never force the edit.
  </action>
  <verify>
    <automated>python -I -c "import re, subprocess; from pathlib import Path; path = '.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md'; before = subprocess.check_output(['git', 'show', 'HEAD:' + path], text=True); m = re.search(r'^open: (\d+)$', before, re.M); assert m, 'open count line missing'; n = int(m.group(1)); yaml_anchor = '  - id: WR-09\n    severity: warning\n    disposition: open\n'; row = '| WR-09 | warning | open | - |'; new_row = '| WR-09 | warning | fixed | quick 261111-rqq (cleanup delegates to LLMCacheRepository.clear_expired with parsed-datetime comparison; cache expiry written as aware-UTC; legacy naive-local rows interpreted as system-local; regression tests) |'; assert before.count(yaml_anchor) == 1 and before.count(row) == 1 and len(re.findall(r'^open: \d+$', before, re.M)) == 1, 'anchors not unique at execution-time HEAD'; expected = before.replace(yaml_anchor, yaml_anchor.replace('disposition: open', 'disposition: fixed'), 1).replace('\nopen: %d\n' % n, '\nopen: %d\n' % (n - 1), 1).replace(row, new_row, 1); assert expected != before; assert Path(path).read_text(encoding='utf-8') == expected, 'ledger differs from exact three-edit reconstruction of execution-time HEAD'; print('WR-09-fixed; open %d->%d; all-other-ledger-content-byte-identical' % (n, n - 1))"</automated>
  </verify>
  <done>WR-09 is fixed in YAML and the table, the open count is exactly one less than its execution-time value with total still 22, the Source cell names quick 261111-rqq, and the exact baseline reconstruction against execution-time `git show HEAD:<ledger>` proves no other ledger content changed (sibling closures included).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Stored llm_cache.expires_at text (legacy naive-local + new aware-UTC) -> expiry predicate in clear_expired/cleanup | Persisted timestamp strings of two formats cross into a deletion decision; the defect made expiry depend on string format and host timezone instead of the actual instant (integrity: expired cache entries retained and served past TTL; maintenance: cleanup silently ineffective) |

No new network, package, authentication, or external-service boundary is introduced.

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-rqq-01 | Tampering | src/sif/database/repositories.py LLMCacheRepository.set/clear_expired; src/sif/cli/main.py cleanup_cmd | low | mitigate | Write aware-UTC instants (+00:00) and compare parsed datetimes with naive legacy values interpreted as system-local, so expiry is correct on every host timezone; retain NULL/unparseable rows rather than deleting on ambiguity; pin all contracts with real-SQLite regression tests including a forced east-of-UTC zone |
| T-rqq-SC | Tampering | package installs | low | accept | No package-manager install, dependency, or lockfile task exists; the package legitimacy gate is not applicable |
</threat_model>

<verification>
Source coverage audit (quick-batch item selects exactly one finding; no RESEARCH artifact or locked D-XX decisions exist):

| SOURCE | ID | Item | Task | Status |
|--------|----|------|------|--------|
| GOAL | quick-261111-rqq | Close Phase 10 WR-09: stale-vector handling read side (main.py) + write side (repositories.py), regression tests + three-edit ledger closure | 1-2 | COVERED |
| REQ | PHASE10-WR-09 | Parse-and-compare datetimes reusing clear_expired; aware-UTC write side; legacy naive-row semantics; red-to-green real-SQLite tests; ledger closure | 1-2 | COVERED |
| CONTEXT | orchestrator notes | Shared-ledger execution-time decrement + execution-time HEAD reconstruction gate; repositories.py overlap with rqs declared (regions disjoint); PATH pytest --no-cov targeted; full quality suite; generator-owned docs untouched; pre-existing .planning/ churn preserved | 1-2 | COVERED |
| CONTEXT | excluded backlog | WR-01/07/08, IN-08 (siblings rqp/rqs), all other IN/CR items; LLMCacheRepository.get (same defect class, not named by WR-09); Phase 11 settings-guard WR-09 (different review) | 1-2 | EXCLUDED BY FINDING SCOPE, not silently omitted; boundaries pinned by the diff gate below |

No external API integration or core-assumption generalization is in scope (quick mode: phase-scoped detectors have no phase input and are skipped). No Payload/Prisma/Drizzle/Supabase/TypeORM schema file is touched (llm_cache DDL unchanged), so no schema-push task applies.

Final gates, run from the checkout root after both tasks:
1. `python -m pytest tests/unit/database/test_repositories.py tests/unit/cli/test_main.py tests/unit/cli/test_database_lifecycle.py -q --no-cov`
2. `ruff check src tests`
3. `ruff format --check src tests`
4. `python -m pytest` (full run includes the coverage gate; PATH pytest, not .venv)
5. `git diff --exit-code -- src/sif/cli/commands/collection.py src/sif/cli/commands/index.py src/sif/cli/commands/get.py src/sif/mcp/backend.py src/sif/database/schema.py docs/cli-reference.md docs/configuration.md` proves sibling findings' files, the schema, and generator-owned docs stayed untouched.
6. Review the scoped diff: only the five files_modified paths carry task edits; within repositories.py the delta is confined to set's line 551 and clear_expired (get and delete_by_collection byte-identical); within main.py the delta is the module-level import plus the cleanup cache block. Commits touch only task-scoped paths and never stage the pre-existing `.planning/` churn. Planning SUMMARY/STATE artifacts are handled separately by the orchestrator.
</verification>

<success_criteria>
- The three defect-pinning tests (aware-UTC write format, legacy naive-local clear_expired, CLI legacy-row cleanup) are demonstrably red before the production edits under the forced east-of-UTC zone and green afterward; the two preservation tests and all 29 existing tests pass throughout.
- The only production changes: set's fromtimestamp gains tz=timezone.utc; clear_expired becomes a parse-and-compare datetime predicate with parameterized id deletion; cleanup_cmd delegates to LLMCacheRepository(conn).clear_expired() with the inline SQL and local datetime import removed. get, the settings guard, WR-01's purge region, and all other commands remain byte-identical.
- WR-09 alone becomes fixed, the ledger open count decrements by exactly 1 from its execution-time value, and exact reconstruction against execution-time HEAD proves every other review record (including sibling closures) unchanged.
- Full ruff, format, and pytest quality suite passes (plain PATH python -m pytest; the suite is color-env-hermetic).
</success_criteria>

<output>
Create `.planning/quick/261111-rqq-close-phase-10-wr-09-stale-vector-handling-on-the-read-side/261111-rqq-SUMMARY.md` with `status: complete` in SUMMARY frontmatter when done. Record the closed finding as Phase 10 WR-09, the live reproduction evidence (lexicographic DELETE rowcount 0 vs datetime predicate deleting the expired legacy row under TZ=Asia/Shanghai at HEAD 802c08c), the legacy naive-local interpretation decision (astimezone presumes system-local, matching the old writer), the explicit get()/Phase 11-WR-09/WR-01 boundaries, the red-to-green regression evidence, and the execution-time ledger open-count transition. Do not commit planning artifacts or STATE.md; the orchestrator handles the docs/state commit.
</output>
