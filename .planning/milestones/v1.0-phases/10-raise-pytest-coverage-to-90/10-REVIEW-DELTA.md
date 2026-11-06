---
phase: 10-raise-pytest-coverage-to-90
reviewed: 2026-11-06T16:42:58Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - tests/unit/cli/test_get.py
  - Makefile
  - .github/workflows/docs.yml
findings:
  critical: 1
  warning: 2
  info: 4
  total: 7
  necessity: 0
status: issues_found
delta_base: 39e19f2
---

# Phase 10: Delta Code Review Report (incremental re-review)

**Reviewed:** 2026-11-06T16:42:58Z
**Depth:** standard
**Files Reviewed:** 3 (delta base 39e19f2; the other 31 delta files were formally reviewed this session under the phase 05/06/07 code reviews)
**Status:** issues_found

## Summary

Scope was the three delta files no prior review covered: the get/multi-get test
file (new `TestMarkupLiteralContent` class + `test_disk_fallback_honors_line_options`),
and the `--no-cov` addition to `make docs-test` and the docs CI workflow.

**Verified sound (no finding):**

- The `--no-cov` changes (Makefile:69, docs.yml:32) are correct *and load-bearing*,
  not cosmetic: `pyproject.toml:207` puts `--cov=src/sif --cov-report=...` in
  `addopts`, and `fail_under = 90` (pyproject.toml:210) landed in this phase
  (3867b87). Without `--no-cov`, a docs-only pytest run inherits coverage from
  `addopts`, measures a few percent of `src/sif`, and fails the run under the 90%
  gate — plus clobbers `.coverage`/`htmlcov/`/`coverage.xml` from a full run.
  `pytest-cov` is in the `dev` extras (pyproject.toml:45), so `--no-cov` resolves
  in both the Makefile and CI contexts.
- All 27 tests in `tests/unit/cli/test_get.py` pass (run with `--no-cov`, cache
  disabled). The new disk-fallback and markup-literal tests assert the right
  things for the surfaces they cover.
- The old mock tests' asymmetric patch targets
  (`sif.cli.commands.get.DocumentRepository` vs
  `sif.database.repositories.CollectionRepository`) are **correct**, not a bug:
  `get.py` imports `DocumentRepository` at module level (get.py:13) but
  `CollectionRepository` function-locally (get.py:66, 173), so the module-attribute
  patch is the one that intercepts the call-time import.
- `.stderr` assertions (test_get.py:203, 220) are valid on the installed
  Click 8.3.2 (streams separated since 8.2).
- `instance._connection` access in `TestDatabaseClosure` is sanctioned by the
  project's ruff `per-file-ignores` (`SLF001` off for `tests/**`), and
  `Database.close()` (database.py:73-77) does null `_connection`, so the closure
  assertion is meaningful.

**Key concern:** the new `TestMarkupLiteralContent` class locks in only *one* of
the markup-injection surfaces in the function under test. The CR-01 fix
(`markup=False` on content) leaves the header interpolations — `doc.title`,
`doc.filename`, `doc.path` — piped through markup-enabled `console.print`, and
those fields are ordinary user data (frontmatter title, first heading, filename
stem). Reproduced crashes and silent output corruption on both `get` and
`multi-get` — see CR-01. This is the same defect class phase 04's review
reproduced for the search tables (04-REVIEW.md:37) and is not dispositioned in
any phase 05/06/07 REVIEW-DISPOSITION.

Necessity was assessed per the standard-depth rubric; no necessity findings
(zero findings guard against states provable unreachable — the `--no-cov` flags
do real work, `COLUMNS=200` guards a real wrap-induced flake, and the
`TrackingDatabase` accumulator is cleared before every read).

## Narrative Findings (AI reviewer)

### CR-01: CR-01 regression tests cover only content — markup-hostile titles/paths still crash `get`/`multi-get` or silently corrupt output

**File:** `tests/unit/cli/test_get.py:241-308` (coverage gap); root cause `src/sif/cli/commands/get.py:98, 110-112, 234` (fix location, outside this review's 3-file scope but inside the phase delta)
**Issue:** The new `TestMarkupLiteralContent` class docstring claims "document
content prints raw, never as Rich markup", but every document in its fixture
uses a benign title/path (`hostile.md`, title `Hostile`) with hostile *content*
only. The CR-01 fix (`markup=False`, get.py:102/140/237) protects the content
field alone; the header lines still interpolate user data into markup-enabled
prints:

- get.py:110 — `console.print(f"[bold cyan]{doc.title or doc.filename}[/bold cyan]")`
- get.py:111-112 — `Path: {doc.path}` / `Collection: {doc.collection_id}` in `[dim]` wrappers
- get.py:98 — disk-fallback header `console.print(f"[bold]{path}[/bold]")` (path is the raw CLI argument)
- get.py:234 — multi-get header `console.print(f"[bold cyan]=== {doc.path} ===[/bold cyan]")`

These fields are ordinary user data: titles come from frontmatter metadata, the
first heading, or the filename stem (parser.py:60-64, 100, 158; indexer.py:187).
Reproduced against the current CLI (Click 8.3.2 / current rich):

| Input | Result |
|---|---|
| `get`, title `Hostile [/bold] title` | exit 1 — `MarkupError: closing tag '[/bold]' at position 19 doesn't match any open tag` |
| `get`, title `see [link](https://example.com)` | exit 0, output `see (https://example.com)` — link text silently consumed |
| `get`, title `None`, filename `note [draft].md` | exit 0, header prints `note .md` — `[draft]` silently consumed |
| `multi-get`, path `note [/bold] draft.md` | exit 1 — `MarkupError: closing tag '[/bold]' at position 87 doesn't match any open tag` |
| `multi-get`, path `note [link] x.md` | exit 0, header prints `note  x.md` — `[link]` silently consumed |

Why blocker: a note whose title or filename contains bracket sequences —
realistic in a knowledge base full of markdown notation — crashes a core read
path with a traceback or silently alters displayed data. The phase's new tests
present CR-01 as closed while the identical defect class persists one field
over in the very function under test, which is false regression coverage.
**Fix:** escape data, keep styling markup — in `src/sif/cli/commands/get.py`:

```python
from rich.markup import escape

# single-get indexed path (get.py:110-112)
console.print(f"[bold cyan]{escape(doc.title or doc.filename)}[/bold cyan]")
console.print(f"[dim]Path: {escape(doc.path)}[/dim]")
console.print(f"[dim]Collection: {escape(doc.collection_id)}[/dim]")

# disk-fallback header (get.py:98)
console.print(f"[bold]{escape(str(path))}[/bold]")

# multi-get header (get.py:234)
console.print(f"[bold cyan]=== {escape(doc.path)} ===[/bold cyan]")
```

Then extend `markup_documents` with a hostile-title document
(`title="[/bold]"`) and a bracketed filename, asserting `exit_code == 0` and
literal `[/bold]` / `[draft]` in the header lines, so the regression suite
covers the full defect class it claims to lock.

## Warnings

### WR-01: docs CI job has no `timeout-minutes`

**File:** `.github/workflows/docs.yml:17-18`
**Issue:** The `docs-test` job declares `runs-on: ubuntu-latest` with no
job-level `timeout-minutes`. A hung `pip install` or pytest run holds the
runner until GitHub's 6-hour default expires. Pre-existing (not introduced by
this delta), but this file has had no prior review.
**Fix:** Add `timeout-minutes: 15` under `docs-test:` — the suite runs in
well under a minute.

### WR-02: docs CI installs unpinned dependencies — generator drift can flip the diff gate

**File:** `.github/workflows/docs.yml:28-29`
**Issue:** `pip install --upgrade pip` + `pip install -e ".[dev]"` with no lock
or constraints: every dependency in the dev extras is a floor (`click>=8.0.0`,
`rich>=13.0.0`, ...), so CI resolves fresh versions on every run. The job's
final gate is `git diff --exit-code docs/cli-reference.md
docs/configuration.md` against output generated by those unpinned tools — a
future click/rich major that changes help rendering will make the gate fail on
an unrelated Tuesday, and a silent behavior change in the generators could
theoretically pass against stale docs. Pre-existing; flagged per the CI/CD
rubric ("pip install with no lock or pinned requirements").
**Fix:** Add a constraints file (or pinned requirements) for the tools that
affect generation, e.g. `pip install -e ".[dev]" -c constraints.txt` with
`click==8.3.*` / `rich==13.*` pins.

## Info

### IN-01: `TestMarkupLiteralContent._invoke` is a byte-identical override of the inherited helper

**File:** `tests/unit/cli/test_get.py:278-284`
**Issue:** `TestMarkupLiteralContent` extends `RealDatabaseTestCase`, which
already defines the exact same `_invoke` (test_get.py:117-123). The override is
dead duplication introduced in this delta.
**Fix:** Delete lines 278-284; the inherited method is identical.

### IN-02: `markup_documents` fixture near-duplicates `indexed_documents`

**File:** `tests/unit/cli/test_get.py:244-276`
**Issue:** The new fixture repeats the ~30-line structure of
`indexed_documents` (test_get.py:42-74) with only ids/paths/contents
differing. Three copies of this shape now exist if `alias_documents` is
counted; a schema change to the setup will need three edits.
**Fix:** Parameterize — e.g. a factory fixture
`make_indexed(notes_dirname, documents) -> Path` that the three fixtures call
with their document lists.

### IN-03: `clean-all` missing from `.PHONY`

**File:** `Makefile:4` (target defined at `Makefile:146`)
**Issue:** Every other target in the Makefile is declared `.PHONY`, but
`clean-all` is not. If a file or directory named `clean-all` ever exists in
the repo root, `make clean-all` will consider the target up to date and skip
the recipe. Pre-existing, outside this delta.
**Fix:** Add `clean-all` to the `.PHONY` list on line 4.

### IN-04: docs workflow has no `permissions` block

**File:** `.github/workflows/docs.yml:16`
**Issue:** The workflow only checks out code and runs pytest; the default
`GITHUB_TOKEN` permissions (potentially read/write, depending on org settings)
are broader than needed. Least-privilege hardening. Pre-existing.
**Fix:** Add at the workflow level:

```yaml
permissions:
  contents: read
```

---

_Reviewed: 2026-11-06T16:42:58Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard (delta re-review, base 39e19f2)_
