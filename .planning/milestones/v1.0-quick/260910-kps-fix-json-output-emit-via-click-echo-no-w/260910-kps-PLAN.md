---
phase: 260910-kps-fix-json-output-emit-via-click-echo-no-w
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/cli/commands/search.py
  - src/sif/cli/commands/bench.py
  - tests/unit/cli/test_search.py
  - tests/unit/cli/test_bench.py
autonomous: true
requirements: [CLI-JSON-WRAP]
estimate:
  tokens: 45000
  raw_tokens: 25000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "`sif search search <term> --json` stdout is parseable by strict `json.loads` regardless of terminal width, even when snippet/highlight values exceed the console width (CLI-JSON-WRAP)"
    - "`--csv`, `--md`, `--xml`, and `--files` (and quiet path-list) output from search_cmd/query_cmd/vsearch_cmd contain no Rich-inserted line breaks: every result row and every path is emitted on exactly one line (CLI-JSON-WRAP)"
    - "`sif bench --json` stdout is parseable by strict `json.loads` (CLI-JSON-WRAP)"
    - "Human-facing output is unchanged: Rich tables, yellow warnings, and dim explain lines still render through console.print"
    - "Full quality suite green: ruff check src tests; ruff format --check src tests; pytest"
  artifacts:
    - "src/sif/cli/commands/search.py — all machine-format emitters in search_cmd/vsearch_cmd/query_cmd switched from console.print to click.echo"
    - "src/sif/cli/commands/bench.py — bench --json emitter switched to click.echo"
    - "tests/unit/cli/test_search.py — regression tests asserting strict JSON parse under forced narrow width and single-line --files paths"
    - "tests/unit/cli/test_bench.py — regression test asserting strict JSON parse of bench --json output"
  key_links:
    - "search_cmd/query_cmd/vsearch_cmd output branches -> click.echo(format_results_*) so no Rich word-wrap or markup interpretation touches machine output"
    - "bench_cmd output_json branch -> click.echo(json.dumps(...))"
    - "tests assert the round-trip: mocked SearchResult with >100-char highlight -> CLI --json -> json.loads recovers the identical string"
---

<objective>
Fix the machine-output corruption class of bug in the CLI: every machine-readable emitter (`--json`, `--csv`, `--md`, `--xml`, `--files`/quiet path lists) currently prints through Rich `console.print`, which (a) word-wraps at terminal width and inserts REAL newline characters inside JSON string values — breaking strict `json.loads` with `JSONDecodeError: Invalid control character` — and (b) interprets Rich markup, so document text containing bracket sequences can be silently swallowed (the same hazard STATE.md records for snippet table cells, mitigated there with `rich.markup.escape` but never fixed for machine formats).

Purpose: `--json`/`--csv`/etc. exist for programmatic consumption (scripts, agents, `sif-search` Claude skill, jq pipes); wrapped output makes them unusable at narrow widths.
Output: search.py and bench.py emit machine formats verbatim via `click.echo`; regression tests lock in strict parseability under forced narrow width.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Emit all machine-format CLI output via click.echo, bypassing Rich entirely</name>
  <files>src/sif/cli/commands/search.py, src/sif/cli/commands/bench.py</files>
  <action>
In `src/sif/cli/commands/search.py`, change ONLY the machine-format output branches — leave every human-facing `console.print` (Rich tables, `[yellow]` warnings, `[dim]` explain lines, reranker-notices) exactly as is:

1. `search_cmd` output block (currently lines ~181-217):
   - Path-list branch (`--files` / quiet fallback): replace the `for r in results: console.print(r.path)` loop body with `click.echo(r.path)` — a path longer than the terminal width must never wrap mid-path.
   - `--json`, `--csv`, `--md`, `--xml` branches: replace each `console.print(format_results_*(...))` with `click.echo(format_results_*(...))`, keeping the existing `add_line_numbers_to_results(...)` conditional arguments identical.
2. `vsearch_cmd` output block (~lines 344-355): same two changes — `click.echo(r.path)` in the quiet path-list branch, and `click.echo(format_results_json(...))` for `--json`.
3. `query_cmd` output block (~lines 530-567): same five changes — path-list branch plus `--json`, `--csv`, `--md`, `--xml` branches.
4. In `src/sif/cli/commands/bench.py` (~line 133): replace `console.print(json.dumps(metrics, indent=2))` with `click.echo(json.dumps(metrics, indent=2))`.

Why `click.echo` and not `console.print(..., soft_wrap=True)`: `click.echo` writes the string verbatim to stdout, so Rich performs neither word-wrap (the proven JSON-breaking path) nor markup interpretation (the bracket-swallowing hazard already acknowledged for this codebase in STATE.md's Phase 04-06 escape decision). Machine output must be byte-faithful. `click` is already imported in both files. Human table output keeps its Rich rendering, including the existing `escape(...)` on snippet cells.
  </action>
  <verify>
    <automated>cd /Users/forrest/GitHub/SIF && NO_COLOR=1 FORCE_COLOR=0 python -m pytest tests/unit/cli/test_search.py tests/unit/cli/test_bench.py -q && ruff check src/sif/cli/commands/search.py src/sif/cli/commands/bench.py && ruff format --check src/sif/cli/commands/search.py src/sif/cli/commands/bench.py</automated>
  </verify>
  <done>
All machine-format branches in search_cmd, vsearch_cmd, query_cmd, and bench_cmd route through click.echo; no machine-format path in these files goes through console.print; human-facing table/warning/explain output untouched; existing CLI tests and lint pass.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Regression tests — strict JSON parse under narrow width, single-line paths and rows</name>
  <files>tests/unit/cli/test_search.py, tests/unit/cli/test_bench.py</files>
  <behavior>
    - Test 1 (search_cmd --json): mocked BM25Searcher returns one SearchResult whose first highlight is a ~120-char string containing spaces; invoke with `["query", "--json"]` and `env={"COLUMNS": "80"}` on CliRunner; `json.loads(result.output)` must succeed and `data[0]["highlights"][0]` must equal the exact input string.
    - Test 2 (query_cmd --json): same assertion via query_cmd using the file's existing pipeline-mock pattern (`_make_pipeline_mock`), with a ~120-char snippet/highlight value and `env={"COLUMNS": "80"}`.
    - Test 3 (search_cmd --files): one result with a path longer than 100 chars; invoke with `--files` and `env={"COLUMNS": "80"}`; the full path appears intact as one element of `result.output.splitlines()`.
    - Test 4 (search_cmd --csv): long title/path; every non-header output line starts with the expected rank digit and the quoted path appears within a single line (no wrap inside the row).
    - Test 5 (bench --json): mocked evaluator metrics include one key whose string value exceeds 80 chars with spaces; invoke bench with `--json` and `env={"COLUMNS": "80"}`; `json.loads(result.output)` succeeds.
    - All tests must FAIL against the pre-fix code (Rich wraps the long value, strict parse raises) and PASS after Task 1.
  </behavior>
  <action>
Add a `TestMachineOutputNoWrap` class to `tests/unit/cli/test_search.py` following the file's established mocking style (MagicMock + `patch("sif.cli.commands.search.Database", ...)`, `patch("...CollectionRepository", ...)`, `patch("...BM25Searcher", ...)` for search_cmd; the existing `_make_pipeline_mock`/SearchPipeline patching for query_cmd — see `test_search_line_numbers_json` and `test_query_line_numbers_flag` for the exact invocation shape, including `obj={"index_path": MagicMock(exists=lambda: True)}`). Pass `env={"COLUMNS": "80"}` to every `runner.invoke` so the width is forced regardless of the developer's terminal. Build the long fixture strings as e.g. `"lorem ipsum "` * 10 (spaces are required so Rich word-wraps pre-fix). Write the tests first, confirm they fail on the pre-fix emitters (Task 1 not yet applied — run them against a stashed/unstashed state as appropriate), then confirm green after Task 1. Add the bench test to `tests/unit/cli/test_bench.py` using that file's existing bench_cmd mock pattern. Keep ruff line-length 100 and module import order per project style.
  </action>
  <verify>
    <automated>cd /Users/forrest/GitHub/SIF && NO_COLOR=1 FORCE_COLOR=0 python -m pytest tests/unit/cli/test_search.py tests/unit/cli/test_bench.py -q && NO_COLOR=1 FORCE_COLOR=0 python -m pytest -q</automated>
  </verify>
  <done>
New regression tests pass post-fix, fail pre-fix; strict `json.loads` round-trips the exact long highlight string for search_cmd and query_cmd `--json`; `--files` long path is one unbroken line; bench `--json` strict-parses; full suite green with zero regressions (baseline 646 passed, 11 skipped).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI stdout -> scripts/agents/jq | Machine-format output is consumed verbatim by downstream parsers; any mutation (wrap, markup swallow) corrupts the contract |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-kps-01 | Tampering | console.print on JSON/CSV paths (Rich mutates bytes in transit) | medium | mitigate | Task 1: click.echo emits verbatim, bypassing wrap and markup |
| T-kps-02 | Tampering | Piped machine output consumed by shell/eval-like consumers | low | accept | Output is data, not executed; width-dependent corruption removed by T-kps-01 fix; no injection surface added |
</threat_model>

<verification>
- `NO_COLOR=1 FORCE_COLOR=0 python -m pytest tests/unit/cli/test_search.py tests/unit/cli/test_bench.py -q` green
- `NO_COLOR=1 FORCE_COLOR=0 python -m pytest -q` full suite green (646+ passed, 0 failed)
- `ruff check src tests` and `ruff format --check src tests` clean
- Live spot-check (optional, human): `sif search search <term> --json | python -m json.tool` on a real index succeeds at a narrow terminal
</verification>

<success_criteria>
- `--json` output from search/vsearch/query/bench is byte-faithful: strict `json.loads` succeeds independent of terminal width (CLI-JSON-WRAP)
- `--csv`/`--md`/`--xml`/`--files` emit one unbroken line per record/path (CLI-JSON-WRAP)
- Human-facing table output rendering unchanged
- Regression tests lock the contract under forced COLUMNS=80
</success_criteria>

<output>
Create `.planning/quick/260910-kps-fix-json-output-emit-via-click-echo-no-w/260910-kps-SUMMARY.md` when done
</output>
