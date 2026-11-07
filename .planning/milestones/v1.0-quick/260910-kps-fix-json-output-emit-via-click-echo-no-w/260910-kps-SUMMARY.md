---
phase: 260910-kps-fix-json-output-emit-via-click-echo-no-w
plan: 01
subsystem: cli
tags: [cli, json-output, rich, click-echo, machine-format, cli-json-wrap]
requires:
  - "Rich console.print on all machine-format emitters (the bug under fix)"
provides:
  - "Byte-faithful --json/--csv/--md/--xml/--files output from search_cmd/vsearch_cmd/query_cmd and --json from bench_cmd, parseable by strict json.loads at any terminal width"
  - "TestMachineOutputNoWrap regression suite locking the contract under forced COLUMNS=80"
affects:
  - "src/sif/cli/commands/search.py (machine-format branches only)"
  - "src/sif/cli/commands/bench.py (--json branch only)"
  - "sif-search / sif-get Claude skills (downstream consumers of --json; unchanged code, hardened contract)"
tech-stack:
  added: []
  patterns:
    - "click.echo for machine-format CLI output — Rich performs neither word-wrap nor markup interpretation on it; console.print reserved for human-facing tables/warnings/explain"
key-files:
  created: []
  modified:
    - src/sif/cli/commands/search.py
    - src/sif/cli/commands/bench.py
    - tests/unit/cli/test_search.py
    - tests/unit/cli/test_bench.py
decisions:
  - "click.echo over console.print(soft_wrap=True): machine output must be byte-faithful — soft_wrap still routes through Rich markup interpretation (the bracket-swallowing hazard STATE.md records for snippet cells), and echo writes verbatim"
  - "Human-facing output untouched: Rich tables, [yellow] warnings, [dim] explain lines, reranker notices still render through console.print, including the existing escape() on snippet cells"
  - "Tests force env={\"COLUMNS\": \"80\"} on every runner.invoke so width is pinned regardless of developer terminal"
metrics:
  duration: 11min
  completed: "2026-09-10"
status: complete
actuals:
  tokens: 3465    # chars/4 over the realized diff (13860 chars / 4); estimate was 45000 at confidence:low
  tasks: 2
  commits: 2
plan_head_before: 4970411
---

# Quick Task 260910-kps: Machine-format CLI output via click.echo (no Rich wrap/markup) Summary

All machine-readable emitters (`--json`, `--csv`, `--md`, `--xml`, `--files`/quiet path lists) in `search_cmd`, `vsearch_cmd`, `query_cmd`, and `bench_cmd` now emit through `click.echo`, so Rich performs neither word-wrap (which inserted REAL newlines inside JSON string values, breaking strict `json.loads` with `Invalid control character`) nor markup/highlight interpretation (which ANSI-styled and could swallow bracket sequences). Human-facing table output keeps its Rich rendering.

## What Changed Per Task

### Task 1: Emit all machine-format CLI output via click.echo (commit `2f7cbb4`)

- `search_cmd` + `query_cmd` (identical blocks): `--files`/quiet path-list branch loops `click.echo(r.path)`; `--json`/`--csv`/`--md`/`--xml` branches `click.echo(format_results_*(...))` with the existing `add_line_numbers_to_results` conditionals unchanged.
- `vsearch_cmd`: quiet path-list branch → `click.echo(r.path)`; `--json` branch → `click.echo(format_results_json(...))`.
- `bench_cmd`: `--json` branch → `click.echo(json.dumps(metrics, indent=2))`.
- Verified post-change: every remaining `console.print` in both files is human-facing (tables, `[yellow]` warnings, `[dim]` explain lines, reranker notices); machine emitters grep-confirmed absent from console.print.
- Task verification: CLI test files 24 passed; `ruff check` + `ruff format --check` on both files clean.

### Task 2: Regression tests — strict parse under narrow width (commit `4d4bb02`, TDD)

`TestMachineOutputNoWrap` added to `tests/unit/cli/test_search.py` (following the file's established MagicMock + patch scaffold; `env={"COLUMNS": "80"}` on every invoke), plus one test in `tests/unit/cli/test_bench.py` (patching `sif.cli.commands.bench.SearchEvaluator` to return a metrics dict with a 120-char spaced string value):

- `test_search_json_parses_at_narrow_width` — search_cmd `--json` with a 120-char highlight: `json.loads(result.output)` succeeds and `data[0]["highlights"][0]` equals the exact input string.
- `test_query_json_parses_at_narrow_width` — query_cmd `--json` (pipeline mock) with a 120-char snippet: strict parse + exact `data[0]["snippet"]` round-trip.
- `test_search_files_long_path_single_line` — `--files` with a 145-char space-bearing path: the full path is one element of `result.output.splitlines()`.
- `test_search_csv_rows_single_line` — `--csv` with 128-char title + 145-char path: header line exact, and the single data row equals the exact expected `"1","0.9500","title","path","notes"` string (rank digit first, quoted path unbroken within one line).
- `test_bench_json_parses_at_narrow_width` — bench `--json`: strict parse and exact long-value round-trip.

**RED evidence (pre-fix, Task 1 reverse-applied via `git apply -R` of the committed diff):** all 5 failed — Rich wrapped the long values, inserting a real newline inside the JSON string literal (`json.JSONDecodeError`). **GREEN:** fix re-applied via `git apply`, 29 passed in the two files.

## Test Results

- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` — **667 passed, 0 failed, 20 warnings**
- `ruff check src tests` — All checks passed
- `ruff format --check src tests` — 131 files already formatted (test_search.py reformatted once before commit)

Count delta vs the recorded 646-passed/11-skipped baseline is environmental, not a code effect: this shell's miniconda Python has sqlite-vec installed and the docs files present, so the suite's 5 conditional skips (`sqlite-vec not available` ×3, `configuration.md`/`cli-reference.md` not found ×2) do not trigger, plus tests added since that count was recorded. An output-call swap cannot change skip conditions.

## Truths Verification

- `--json` strict-parse at narrow width with over-width highlight/snippet values: locked by Test 1/2/5 (RED→GREEN proven). ✔
- `--csv`/`--md`/`--xml`/`--files` single-line rows/paths: `--files` and `--csv` locked by Test 3/4; `--md`/`--xml` emit through the same replaced branches (`click.echo(format_results_*)`), no separate code path remains. ✔
- Human-facing output unchanged: zero edits outside the machine branches; remaining console.print calls enumerated above. ✔
- Full quality suite green. ✔

## Deviations from Plan

**1. [Process] Task 1 commit initially swept in a pre-staged unrelated deletion**

- **Found during:** Task 1 commit.
- **Issue:** `mypy.ini` was staged for deletion before this task started (pre-existing index state); the first commit included it (3 files).
- **Fix:** `git reset --soft HEAD~1`, then re-committed with an explicit pathspec (`git commit -- <task files>`), yielding `2f7cbb4` with exactly the two task files. The user's staging state was preserved (`mypy.ini` remains staged-deleted, untouched).
- **Files modified:** none beyond task scope.

**2. [Environment] `FORCE_COLOR=0` prefix insufficient in the agent harness**

- **Issue:** The Orca terminal harness exports `FORCE_COLOR=3`; Rich treats ANY non-empty `FORCE_COLOR` (including `"0"`) as force-terminal (rich/console.py: `environ.get("FORCE_COLOR")` truthiness), emitting ANSI inside CliRunner captures. This broke two otherwise-green baseline tests (`test_bench_json_output`, `test_query_with_explain`) via ReprHighlighter ANSI splitting tokens.
- **Fix:** ran all pytest invocations as `env -u FORCE_COLOR NO_COLOR=1` (value fully unset), matching the pattern the 260905-sxc executor already used. Notably, the bench ANSI corruption is the same bug class Task 1 fixes — post-fix, `test_bench_json_output` passes even under forced color because click.echo does not style.

## Known Stubs

None — no placeholder logic introduced; pure emitter swap plus tests.

## Threat Flags

None. The change removes the T-kps-01 tampering vector (Rich mutating machine bytes in transit); no new network/auth/file/schema surface.

## Self-Check: PASSED

All 5 modified/created files exist on disk; both task commits (`2f7cbb4`, `4d4bb02`) present in history; commit count measured from `plan_head_before` (4970411) = 2, matching `actuals.commits`.
