---
phase: 14-freshness-floor-pre-command-refresh-staleness-marking
reviewed: 2026-11-08T04:22:20Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - docs/cli-reference.md
  - docs/configuration.md
  - scripts/generate_config_ref.py
  - src/sif/cli/commands/search.py
  - src/sif/cli/main.py
  - src/sif/config/settings.py
  - src/sif/core/models.py
  - src/sif/database/repositories.py
  - src/sif/indexing/drift.py
  - src/sif/mcp/backend.py
  - src/sif/search/bm25.py
  - src/sif/search/hybrid.py
  - src/sif/search/staleness.py
  - src/sif/search/vector.py
  - tests/unit/cli/test_index_locking.py
  - tests/unit/cli/test_search.py
  - tests/unit/cli/test_status.py
  - tests/unit/indexing/test_drift.py
  - tests/unit/indexing/test_incremental.py
  - tests/unit/mcp/test_backend.py
  - tests/unit/search/test_bm25.py
  - tests/unit/search/test_staleness.py
  - tests/unit/search/test_vector.py
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
  necessity: 0
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-11-08T04:22:20Z
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

Phase 14 adds three features: (1) a pre-search drift refresh floor in the CLI
search trio (`_pre_search_refresh`, `sif.indexing.drift`), (2) derived
vector-staleness marking in every searcher exit
(`sif.search.staleness`, `vectors_stale` on `SearchResult`), and (3)
staleness presentation (Rich-table annotation, CSV/MD/XML columns/attributes,
the D-13 stderr remedy hint, the status `Vector lag` row, and the MCP
metadata forward). The staleness-marking half (14-02/14-03) is well built:
the derived one-scan formula, display gate, degrade paths, dual-shape
(`_field`) readers, and stderr/stdout separation are all correct and well
tested. The generated docs were verified byte-identical to
`scripts/generate_config_ref.py` output, and ruff passes on all changed
source files.

The pre-search drift floor (14-01), however, has a proven convergence
failure at its core. `detect_drift` is mtime-primary by design, but the
refresh path it feeds (`IncrementalIndexer.update_paths`) never persists a
fresh mtime when the checksum-skip fires, so any touched-but-unchanged file
(a `git checkout` of identical content, an archive extract, a no-op editor
save, rsync without `--times`) is detected as drift on **every** subsequent
search, makes every search acquire the per-database write lock and run a
no-op refresh, and emits a false "refreshed N files (bm25) before search"
notice — forever. This was reproduced end to end against the real code
(CR-01), as was a second, settings-triggered variant of the same loop
(WR-01). The existing test battery only exercises content-edit drift for
convergence; the mtime-touch and predicate-divergence paths are untested,
which is why the suite is green while the behavior is broken.

Necessity (#4100) was assessed per `$HOME/.claude/gsd-core/references/necessity-review.md`
(read successfully). One candidate was evaluated — `refresh_drifted`'s
zero-count early return is unreachable through its only production caller
(`_pre_search_refresh` proves `0 < total_count <= cap` first), but the guard
is a deliberate contract on a public module seam exercised directly by
`tests/unit/indexing/test_drift.py` ("the defensive guard must not lock"),
which lands in the rubric's test-seam negative space. No necessity findings.

No `<structural_findings>` or `<external_reviewer_evidence>` blocks were
provided for this review.

## Critical Issues

### CR-01: mtime-only drift never converges — every search re-locks, re-refreshes a no-op, and prints a false notice, forever

**File:** `src/sif/indexing/drift.py:99-115` (detection), `src/sif/indexing/incremental.py:272-276` (root cause), `src/sif/cli/commands/search.py:166-187` (loop driver)
**Issue:** `detect_drift` is deliberately mtime-primary (`stored.get(key) != mtime`, bit-exact float compare), but the only writer that can re-converge the stored mtime — `IncrementalIndexer._process_file` — returns early on the checksum-skip path (`existing.checksum == parsed.checksum and not force` → `"skipped"`) **without persisting the fresh mtime**. A file whose content is unchanged but whose mtime moved is therefore permanently drifted: refresh runs, decides "unchanged", stores nothing, and the next search detects the same drift again.

Reproduced against the real modules (index → `os.utime(doc, (1700000000, 1700000000))` → refresh):

```
drift after touch:   1
refresh result:      IncrementalResult(added=0, updated=0, removed=0, unchanged=1)
drift after refresh: 1          <- non-convergence
stored mtime: 1794111535.59 ... disk mtime: 1700000000.0
```

Consequences for every `sif search` / `vsearch` / `query` without
`--no-refresh` once any touched-but-unchanged file exists:

1. The "clean search pays nothing" invariant (SC2, and the D-03 comment in
   `search.py:550-553`: "when watch already handled everything, the
   stat-decides walk finds zero drift") is permanently violated.
2. Every search acquires the per-database `index_lock` and opens a write
   transaction (`refresh_drifted` → `update_paths`) for zero effect —
   read commands now contend with real index writers on every invocation.
3. The stderr notice "refreshed 1 files (bm25) before search" is printed on
   every search despite nothing being refreshed (see WR-02).
4. Enough touched files silently consume the `search_refresh_max_files`
   budget: a branch switch that restores identical content can push every
   future search into the over-cap warning path until the user runs
   `sif index update`.

The convergence tests only cover the content-edit path
(`test_refresh_updates_content_and_converges_mtime`,
`test_search_finds_modified_content_and_notifies_on_stderr` — both rewrite
content); `test_touch_drift_detected_via_os_utime` tests detection only,
never refresh convergence, which is why this passes CI.
**Fix:** Persist the fresh mtime when the checksum-skip fires, so the stat
walk's own convergence input is maintained:

```python
# src/sif/indexing/incremental.py, _process_file, skip branch
if existing:
    if existing.checksum == parsed.checksum and not force:
        # Drift-compare convergence (Phase 14 LIVE-10): detect_drift is
        # mtime-primary, so the skip must still converge a moved mtime,
        # or every pre-search refresh re-detects this file forever.
        if existing.mtime != parsed.mtime:
            with self._conn:
                self._conn.execute(
                    "UPDATE documents SET mtime = ? WHERE id = ?",
                    (parsed.mtime, existing.id),
                )
        self._notify(progress, f"unchanged {file_path.name}")
        return "skipped"
```

Add a regression test mirroring `test_touch_drift_detected_via_os_utime`:
touch with `os.utime`, run `refresh_drifted`, assert a second `detect_drift`
reports zero.

## Warnings

### WR-01: Drift refresh silently skips stored documents the shared predicate excludes — divergence from `sif index update` produces a second permanent drift loop

**File:** `src/sif/indexing/drift.py:113-115`, `src/sif/indexing/incremental.py:209-218` (vs. `_sweep_removed` at `src/sif/indexing/incremental.py:318-329`)
**Issue:** `detect_drift` counts every stored-but-unseen path as deleted drift. But `update_paths` first gates each path through `scanner.matches(...)` and `continue`s past paths the shared predicate excludes — without removing the stored document. A stored document that a later configuration change excludes (e.g. setting `SIF_WATCH_IGNORE_PATTERNS`, which `_combined_ignore_patterns` applies to the scan predicate retroactively, or any pattern/ignore divergence) is therefore detected as drift on every search, skipped by the refresh, and never removed — the same non-converging lock+notice loop as CR-01 with a different root. Full `sif index update` *would* remove it (`_sweep_removed` has no predicate gate), so the two write paths disagree about removal semantics.

Reproduced (index 2 files, then set `watch_ignore_patterns=["secret*"]`):

```
drift count:         1
refresh result:      IncrementalResult(added=0, updated=0, removed=0, unchanged=0)
drift after refresh: 1          <- loop proven
```
**Fix:** In `update_paths`, when a stored document exists at a path that fails `scanner.matches`, remove it (mirroring `_sweep_removed` / `sif index update` semantics) instead of silently skipping; alternatively, make `detect_drift` stop counting stored paths the predicate excludes — but then document that pre-search refresh and full update intentionally diverge.

### WR-02: "refreshed N files" notice reports the pre-refresh drift count and discards the actual refresh result

**File:** `src/sif/cli/commands/search.py:177-187`
**Issue:** The notice interpolates `report.total_count`, but `refresh_drifted` returns an `IncrementalResult` that is thrown away. The printed number is wrong whenever refresh outcomes diverge from the drift count: a deleted file is announced as "refreshed" (it was removed), a checksum-skipped file is announced as refreshed (nothing was written), and in both CR-01/WR-01 loops the notice claims work that never happens on every single search. The D-06 cap-boundary test's expected string ("refreshed 3 files") only holds because content edits all update.
**Fix:**

```python
result = refresh_drifted(
    index_path, db.connection, {c.id: c for c in collections}, report,
    lock_timeout=settings.lock_wait_timeout,
)
if not quiet:
    done = result.added + result.updated + result.removed
    console_err.print(f"[dim]refreshed {done} files (bm25) before search[/dim]")
```

### WR-03: LLM cache TTL written as naive local time, compared against aware-UTC ISO strings — TTL semantics broken in every non-UTC timezone

**File:** `src/sif/database/repositories.py:547-550` (write), `:529-533` and `:569-574` (compares)
**Issue:** `LLMCacheRepository.set` computes `expires_at = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + ttl)` — `fromtimestamp` without `tz` yields a **naive local-time** datetime — while `get`/`clear_expired` compare it lexicographically against `datetime.now(timezone.utc).isoformat()` (aware, `+00:00`-suffixed). Demonstrated on this machine (UTC+8): written `2026-11-08T13:18:57.403688` vs compare-now `2026-11-08T04:18:57.403830+00:00`. East of UTC, a `ttl_seconds=3600` entry reads as unexpired for ~8 extra hours (stale cache served); west of UTC, entries can read as expired the moment they are written (cache useless). Lexicographic comparison across naive/aware ISO forms is ill-defined in general. Pre-existing (this phase's diff to the file only added `list_stat_by_collection`), but it is a real correctness bug in a reviewed file.
**Fix:**

```python
expires_at = datetime.fromtimestamp(
    datetime.now(timezone.utc).timestamp() + ttl_seconds, tz=timezone.utc
).isoformat()
```

### WR-04: `vsearch`/`query` crash with a raw RuntimeError traceback when sqlite-vec is absent (ClickException convention violated)

**File:** `src/sif/cli/commands/search.py:562-564` (vsearch), `:756-759` (query — `SearchPipeline` construction)
**Issue:** `VectorSearcher.__init__` raises `RuntimeError("sqlite-vec extension is not available...")` by design (documented in CLAUDE.md). In `vsearch_cmd` the construction at line 563 has no guard at all, and in `query_cmd` the `SearchPipeline(...)` construction at line 757 sits **outside** the `try: pipeline.search ... except RuntimeError → ClickException` block at lines 765-768 — the pipeline constructor builds a `VectorSearcher` via `HybridSearcher`. On a machine without sqlite-vec (the extension is optional; vec0 schema creation is conditional), `sif search vsearch` and `sif search query` die with a full pydantic-free traceback instead of the project's user-facing error convention ("CLI commands raise `click.ClickException(str(e))` for user-facing errors", CLAUDE.md). Pre-existing, not introduced by this phase.
**Fix:** In `vsearch_cmd`, wrap `VectorSearcher(...)` construction in `try/except RuntimeError → raise click.ClickException(str(e))`. In `query_cmd`, move the `SearchPipeline(...)` construction inside the existing `try` block (or give it its own guard) so constructor failures surface as clean one-line errors.

## Info

### IN-01: Duplicated mid-function `quiet` recomputation in `search_cmd` and `query_cmd`

**File:** `src/sif/cli/commands/search.py:386` (search_cmd, also `:771` query_cmd)
**Issue:** `quiet = quiet or ctx.obj.get("quiet", False)` is computed at function entry (lines 344/668) and then recomputed verbatim before the output branches. Nothing mutates `ctx.obj` in between, so the second assignment is dead recomputation that only suggests the value might have changed.
**Fix:** Delete lines 386 and 771 (the entry-point computation at 344/668 already covers both CLI `-q` and group `--quiet`).

### IN-02: Unknown `-c` collection names are silently dropped; an all-unknown `-c` list yields "No results found" with no diagnostic

**File:** `src/sif/cli/commands/search.py:113-123`
**Issue:** `_resolve_collections` skips names `get_by_name` cannot resolve (docstring: "unknown names silently skipped — today's behavior", intentionally preserved by D-04). When every given name is unknown, `collections == []` trips the exclude-all sentinel and the search returns zero results — indistinguishable from a genuine empty result. A typo like `-c nostes` produces a silent dead end.
**Fix:** Keep the trio semantics but emit one stderr notice listing unresolved names (`console_err.print(f"[yellow]no collection named {name!r}; skipped[/yellow]")`), gated on `not quiet` like the other D-07 notices.

---

_Reviewed: 2026-11-08T04:22:20Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
