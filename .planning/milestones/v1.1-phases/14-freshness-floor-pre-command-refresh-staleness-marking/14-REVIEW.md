---
phase: 14-freshness-floor-pre-command-refresh-staleness-marking
reviewed: 2026-11-08T05:08:05Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/sif/cli/commands/search.py
  - src/sif/indexing/incremental.py
  - tests/unit/cli/test_search.py
  - tests/unit/indexing/test_drift.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
  necessity: 0
status: issues_found
---

# Phase 14: Code Review Report (Incremental Re-Review)

**Reviewed:** 2026-11-08T05:08:05Z
**Depth:** standard
**Files Reviewed:** 4 (delta since `e7b0761`, carrying the CR-01 / WR-01 / WR-02 fixes)
**Status:** issues_found

## Summary

Incremental re-review of the four files changed since the prior review commit
`e7b0761`, per `.planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-REVIEW-FIX.md`.
All three directed fixes were verified against the current source and are
correct:

- **CR-01 (fixed, verified):** `_process_file`'s checksum-skip branch now
  persists a moved mtime in a targeted single-column
  `UPDATE documents SET mtime = ?` (`incremental.py:296-302`). The parser
  supplies `stat.st_mtime` as a float (`parser.py:47-48`), so `detect_drift`'s
  bit-exact compare converges after one refresh; the FTS `documents_fts_update`
  trigger fires on the UPDATE with identical content (`schema.py:248-255`), a
  net no-op, so no index desync. Unit and CLI regression tests
  (`test_refresh_converges_touch_only_drift`,
  `test_touch_only_drift_converges_across_searches`) prove convergence and the
  lock-free second search.
- **WR-01 prior (fixed, verified):** `update_paths` now removes a STORED
  document whose path fails the shared `scanner.matches` predicate
  (`incremental.py:227-230`), mirroring `_sweep_removed` / `sif index update`;
  `get_by_path(path, collection_id)` exists with that exact signature
  (`repositories.py:174`), and both regression tests prove same-regime
  convergence.
- **WR-02 prior (fixed, verified):** `_pre_search_refresh` consumes the
  `IncrementalResult` and `_refresh_notice` names actual outcomes
  (`search.py:127-137, 191-199`); the new wording is pinned by tests.

The fixes also hold up adversarially: the mtime write bypasses the repository
deliberately (documented — a whole-row update could smuggle frontmatter
through the skip), and the predicate-exclusion removal cannot fire on another
collection's paths (`get_by_path` is collection-scoped).

What remains: **one new Warning** in the same non-convergence family the
directed fixes addressed — a drifted file that *fails to parse* (invalid
UTF-8, permission change) never converges AND its error is swallowed
completely on the pre-search path, so every search re-locks, re-fails
silently, and prints a misleading "refreshed 0 files (bm25) before search"
notice forever (WR-01 below). The carried **WR-04** (raw RuntimeError
traceback when sqlite-vec is absent, `vsearch`/`query`) was re-verified
against the current `search.py` and is still unfixed (WR-02 below), as are
the two carried Infos (duplicate `quiet` recomputation, silent unknown `-c`
names).

Out-of-scope carried finding **WR-03** (LLM-cache `expires_at` written as
naive local time and compared against aware-UTC ISO strings,
`repositories.py:550` write, `:529-532`/`:568-570` compares) was re-verified
against current source and is still present; `repositories.py` is outside
this round's file list, so it stays tracked in the disposition ledger rather
than as a numbered finding here.

Necessity (#4100) was assessed per
`$HOME/.claude/gsd-core/references/necessity-review.md` (read successfully).
One candidate re-evaluated — `refresh_drifted`'s zero-count early return
(`drift.py:136-137`) remains unreachable through its only production caller
but is a documented public-seam contract exercised directly by
`test_refresh_creates_the_lock_file_only_when_working` (test-seam negative
space). The new delta (`_refresh_notice`, the mtime persist guard, the
excluded-path removal) guards reachable states. No necessity findings.

No `<structural_findings>` or `<external_reviewer_evidence>` blocks were
provided for this review.

## Warnings

### WR-01: Parse-failed drifted files never converge and their errors are silently swallowed — every search re-locks, re-fails, and prints "refreshed 0 files (bm25) before search" forever

**File:** `src/sif/indexing/incremental.py:279-283` (root cause), `src/sif/indexing/drift.py:139-150` (silent host), `src/sif/cli/commands/search.py:190-199` (misleading notice)
**Issue:** CR-01's fix persists a moved mtime only on the *checksum-skip* branch. A drifted file whose parse raises — `MarkdownParser.parse` does `file_path.read_text(encoding="utf-8")` with no guard (`parser.py:44`), so a note re-saved in a non-UTF-8 encoding, a `chmod 000` file, or a vanished-mid-refresh path — takes the `except Exception → "skipped"` branch (`incremental.py:280-283`): nothing is written, the mtime is not converged, and the file is re-detected as drift on every subsequent search. This is the same eternal lock+notice loop shape CR-01 addressed, with a remaining root.

It is also *invisible*: `_process_file` reports parse errors only via
`self._notify(progress, f"error ...")` — no `logger` call — and the pre-search
host passes no callback (`drift.py:146`, unlike the watcher at
`watcher.py:782` which does), so `_notify` no-ops. The user then sees the
WR-02-fixed but here deceptive notice "refreshed 0 files (bm25) before
search" on every search while an unparseable file keeps
`detect_drift > 0` forever; each search acquires the `index_lock` and opens a
write transaction for zero effect, and N such files silently consume the
`search_refresh_max_files` budget toward the over-cap warning.

Reproduction shape (same harness as CR-01): index `a.md`, corrupt it to
invalid UTF-8 (mtime moves) → drift 1 → refresh → parse raises →
`IncrementalResult(unchanged=1)`/`(unchanged=0)` with nothing persisted →
drift stays 1 on every later search.

**Fix:** Make parse failures counted and visible end to end, so the loop
becomes an actionable warning instead of a silent no-op (deliberately do NOT
persist the mtime here — the stored content is genuinely stale and must stay
drift-visible):

```python
# 1. incremental.py — count the failure instead of folding it into "skipped"
@dataclass
class IncrementalResult:
    ...
    failed: int = 0

# _process_file parse-except branch:
except Exception as e:
    logger.warning("Error parsing %s: %s", file_path, e)   # no longer silent
    self._notify(progress, f"error Error parsing {file_path}: {e}")
    return "error"
# update_paths/update_collection: elif outcome == "error": failed += 1

# 2. search.py — surface it in the notice and warn when anything failed
def _refresh_notice(result: IncrementalResult) -> str:
    parts = [f"refreshed {result.added + result.updated} files"]
    if result.removed:
        parts.append(f"removed {result.removed}")
    if result.failed:
        parts.append(f"{result.failed} failed to parse")
    return f"{', '.join(parts)} (bm25) before search"

# _pre_search_refresh, after the notice:
if result.failed and not quiet:
    console_err.print(
        f"[yellow]{result.failed} drifted file(s) failed to parse; "
        "run 'sif index update' to see the error[/yellow]",
    )
```

Add a regression test: index `a.md`, rewrite it as invalid UTF-8 (`write_bytes(b"\xff\xfe...")`),
assert the first search warns (not silence), and that the drift count/notice
shape matches the chosen contract.

### WR-02: `vsearch`/`query` crash with a raw RuntimeError traceback when sqlite-vec is absent (ClickException convention violated) — carried, re-verified unfixed

**File:** `src/sif/cli/commands/search.py:574-576` (vsearch), `:768-776` (query — `SearchPipeline` construction outside the `try` at `:777-780`)
**Issue:** `VectorSearcher.__init__` raises `RuntimeError("sqlite-vec extension is not available...")` by design (`vector.py:20-24`, documented in CLAUDE.md). In `vsearch_cmd` the construction at line 575 has no guard at all, and in `query_cmd` the `SearchPipeline(...)` construction at lines 769-776 sits **outside** the `try: pipeline.search(...) except RuntimeError → ClickException` block — `SearchPipeline.__init__` → `HybridSearcher.__init__` → `VectorSearcher` (`hybrid.py:147, 38`). On a machine without the optional sqlite-vec extension, `sif search vsearch` and `sif search query` die with a full traceback instead of the project's user-facing error convention ("CLI commands raise `click.ClickException(str(e))`", CLAUDE.md). Pre-existing, not introduced by this delta; the fix directive left it out of scope, and the current code is unchanged.
**Fix:** In `vsearch_cmd`, wrap the construction:

```python
try:
    searcher = VectorSearcher(db.connection, len(query_embedding))
except RuntimeError as e:
    raise click.ClickException(str(e)) from e
```

In `query_cmd`, move the `SearchPipeline(...)` construction (lines 769-776)
inside the existing `try` block so constructor failures take the same
`RuntimeError → ClickException` path as `pipeline.search`.

## Info

### IN-01: Duplicated mid-function `quiet` recomputation in all three trio commands — carried, re-verified

**File:** `src/sif/cli/commands/search.py:398` (search_cmd; entry at `:356`), `:578` (vsearch_cmd; entry at `:510`), `:783` (query_cmd; entry at `:680`)
**Issue:** `quiet = quiet or ctx.obj.get("quiet", False)` is computed at each command's entry and then recomputed verbatim immediately before the output branches. Nothing mutates `ctx.obj` in between, so the second assignment is dead recomputation that only suggests the value might have changed. (Prior review cited search/query; the same pattern exists in `vsearch_cmd`.)
**Fix:** Delete lines 398, 578, and 783 — the entry-point computations at 356/510/680 already cover both CLI `-q` and group `--quiet`.

### IN-02: Unknown `-c` collection names are silently dropped; an all-unknown `-c` list yields "No results found" with no diagnostic — carried, re-verified

**File:** `src/sif/cli/commands/search.py:100-124` (`_resolve_collections`, silent skip at `:116-121`)
**Issue:** `_resolve_collections` skips names `get_by_name` cannot resolve (docstring: "unknown names silently skipped — today's behavior", intentionally preserved by D-04). When every given name is unknown, `collections == []` → `options.collection_ids == []` trips the exclude-all sentinel and the search returns zero results — indistinguishable from a genuine empty result. A typo like `-c nostes` produces a silent dead end (and a silent no-drift refresh scope).
**Fix:** Keep the trio semantics but emit one stderr notice listing unresolved names, gated on `not quiet` like the other D-07 notices:

```python
if coll:
    resolved: list[Collection] = []
    for name in collection:
        coll_obj = repo.get_by_name(name)
        if coll_obj:
            resolved.append(coll_obj)
        elif not quiet:
            console_err.print(f"[yellow]no collection named {name!r}; skipped[/yellow]")
    return resolved
```

---

_Reviewed: 2026-11-08T05:08:05Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
