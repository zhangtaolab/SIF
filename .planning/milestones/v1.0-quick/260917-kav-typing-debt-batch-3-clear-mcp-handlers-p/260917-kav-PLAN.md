---
phase: 260917-kav-typing-debt-batch-3-clear-mcp-handlers-p
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/mcp/handlers.py
  - src/sif/cli/commands/search.py
  - src/sif/search/hybrid.py
  - src/sif/database/connection.py
autonomous: true
requirements: [PHASE03-DEFERRED-TYPING]  # phase-03 open deferred item: mypy strict-mode typing debt (~78 errors / 31 files after batches 1-2); batch 3 of N
estimate:
  tokens: 33000
  raw_tokens: 33000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/mcp/handlers.py` exits 0 (all 12 `[misc]` override errors cleared; the `pyproject.toml: note: unused section(s)` NOTE may print under single-file invocation — config-level, expected, NOT in scope; notes do not affect the exit code)"
    - "`env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/cli/commands/search.py` exits 0 (all 11 errors cleared; mypy follows imports into src/sif/search/hybrid.py, so this gate also validates the widened reranker union)"
    - "`env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/database/connection.py` exits 0 (all 9 errors cleared)"
    - "ZERO behavior change: `git diff` across the four files shows ONLY (a) the three ClassVar markers on the ToolHandler base annotations, (b) `results: list[Any]` on the four format helpers + the `from typing import Any` imports, (c) `tuple[str, ...]` on the three Click `collection` params, (d) walrus bindings `(content := getattr(r, \"content\", None))` replacing the bare getattr guards at the three call sites, (e) the Qwen3Reranker TYPE_CHECKING import + widened `reranker:` annotation in hybrid.py, (f) parameterized `tuple[Any, ...] | dict[str, Any]` unions and the typed `row:` local in connection.py. No logic edits, no guard removals, no value changes"
    - "Full-project mypy drops 78 -> 46 (12+11+9 = 32 cleared; full-run attribution matches single-file counts exactly, planner-verified this session). If the count is not exactly 46, diff the error list against baseline before proceeding; the three target files must be at zero regardless"
    - "`env -u FORCE_COLOR NO_COLOR=1 python -m pytest` green (676 passed / 0 failed expected; if exactly 2 order-dependent caplog failures appear in tests/unit/embedding/test_openai_embedder.py they are pre-existing WINDOWS.md #3/#4)"
    - "`ruff check src tests` and `ruff format --check src tests` both clean"
  artifacts:
    - "src/sif/mcp/handlers.py — ToolHandler base declares `name: ClassVar[str]`, `description: ClassVar[str]`, `input_schema: ClassVar[dict[str, Any]]` (ClassVar already imported at line 7; the four subclasses' existing ClassVar declarations stay byte-identical)"
    - "src/sif/cli/commands/search.py — `from typing import Any`; the four format helpers take `list[Any]`; the three `collection` params take `tuple[str, ...]`; the three prepend_line_numbers call sites narrow via walrus"
    - "src/sif/search/hybrid.py — TYPE_CHECKING import gains Qwen3Reranker; SearchPipeline.__init__ reranker param is `LlamaCppReranker | CrossEncoderReranker | Qwen3Reranker | None`"
    - "src/sif/database/connection.py — `from typing import Any`; execute/fetchone/fetchall take `tuple[Any, ...] | dict[str, Any] | None`; executemany takes `list[tuple[Any, ...] | dict[str, Any]]`; fetchone returns via a typed `row: sqlite3.Row | None` local"
  key_links:
    - "ToolHandler base ClassVar declarations <-> the four subclasses' ClassVar overrides (mypy override consistency requires base and subclass to agree on class-vs-instance variable kind; grep-verified no code in src/sif/mcp assigns name/description/input_schema on an instance — server.py reads them as class attributes)"
    - "hybrid.py reranker union <-> create_reranker's declared return from batch 1 (`LlamaCppReranker | CrossEncoderReranker | Qwen3Reranker`); all three rerank() signatures are identical `(self, query: str, results: list[SearchResult], top_k: int = 10) -> list[SearchResult]` (grep-verified), so the hybrid.py:233 call type-checks against the widened union"
    - "walrus `(content := getattr(r, \"content\", None))` truthiness <-> `prepend_line_numbers(content: str)`: the existing guard already rejects None/empty content, so the binding is narrowed to str at the call (mypy resolves getattr with a literal name + default to `str | None`)"
    - "connection.py `tuple[Any, ...] | dict[str, Any]` <-> sqlite3 typeshed's `execute(operation, parameters: Sequence[Any] | dict[str, Any])` and `executemany(operation, seq_of_parameters)`; typeshed's `Cursor.fetchone()` returns Any (row_factory variance), hence the typed local"
---

<objective>
Clear all mypy strict-mode errors in the next three hottest typing-debt files (batch 3 of the phase-03 deferred series, following batch 1 = quick 260917-bo2 and batch 2 = quick 260917-dkf): `src/sif/mcp/handlers.py` (12), `src/sif/cli/commands/search.py` (11), `src/sif/database/connection.py` (9) — 32 total. Full-project count drops 78 -> 46. Zero behavior change — annotations, generics parameterization, walrus narrowing, and one type-level union widening only. The 676-test suite stays green.

Planner-verified error inventory (fresh run this session, `env -u FORCE_COLOR NO_COLOR=1 uv run mypy <file>`; full-project run attributes exactly the same counts to these files — no divergence):

1. `handlers.py` (12, all `[misc]` "Cannot override instance variable with class variable"): base class `ToolHandler` (lines 31-33) declares `name: str` / `description: str` / `input_schema: dict[str, Any]` as bare annotations, which mypy reads as instance variables; all four subclasses override them as `ClassVar` (lines 48/49/53, 91/92/95, 136/137/138, 172/173/174).
2. `search.py` (11 — the batch context estimated 12; fresh count is 11): 4x type-arg bare `list` on the format helpers (44/53/62/81), 3x type-arg bare `tuple` on the Click `collection` params (124/276/421), 3x arg-type `str | None` into `prepend_line_numbers(content: str)` (243/379/594), 1x arg-type at 521 (SearchPipeline reranker param missing Qwen3Reranker).
3. `connection.py` (9): 8x type-arg bare `tuple`/`dict` in the sqlite parameter annotations (63/74/85/95) + 1x no-any-return at 90 (typeshed's `Cursor.fetchone()` returns Any; declared `sqlite3.Row | None`).

Planner-decided fix directions (all patterns probe-verified under `mypy --strict --warn-unreachable` on a scratch file in .planning/tmp/, then deleted):
- **handlers.py — ClassVar on the base.** Semantically right: name/description/input_schema are per-handler constants; every subclass defines them at class level, and grep confirms nothing in src/sif/mcp assigns them per-instance. `ClassVar` is already imported (line 7). A bare annotation and a ClassVar annotation are both annotation-only (neither creates a class attribute at runtime) — zero behavior change.
- **search.py prepend call sites — walrus narrowing, NOT helper widening.** The existing truthiness guard already rejects None/absent content; the typing just needs to carry that into the call. Widening `prepend_line_numbers` to `str | None` would advertise a None path the helper cannot handle (`content.split` on None crashes) — dishonest. `get.py` calls the same helper with already-narrowed str locals and is mypy-clean today — untouched.
- **search.py format helpers — `list[Any]`.** These are duck-typed display helpers: callers pass either `list[SearchResult]` or the `list[dict[str, Any]]` output of `add_line_numbers_to_results`, and the bodies branch via `hasattr(r, "to_dict")` / `hasattr(r, "get")`. A precise `list[SearchResult] | list[dict[str, Any]]` union would break the bodies (attribute access on the union's dict member fails); `list[Any]` documents the duck typing honestly.
- **reranker union — widen in hybrid.py, NOT a shared alias/Protocol.** The widening exactly mirrors create_reranker's declared return (batch 1); a Protocol or core/models.py alias is a larger surface than a typing-debt batch warrants. All three rerank() signatures are identical, so the hybrid.py:233 call site is type-safe against the widened union. TYPE-LEVEL only.
- **connection.py — parameterize to what sqlite3 typeshed actually accepts** (`tuple[Any, ...] | dict[str, Any]`) and a typed `row` local for the one no-any-return. The `if parameters` truthiness at line 67 keeps identical semantics (empty tuple/dict was already falsy).

Verified environment facts (deterministic, planner-tested):
- The `sif.cli.*` mypy override in pyproject.toml relaxes ONLY `disallow_untyped_decorators` (Click decorators); strict generics still apply to search.py — that is exactly why its type-arg errors fire and why the fixes are needed there.
- Single-file mypy exit code is 0 even when the `pyproject.toml: note: unused section(s)` note prints (it is a note, not an error). Do NOT touch pyproject.toml — explicitly out of scope.
- Batch 1-2 conventions apply throughout: per-file gate `env -u FORCE_COLOR NO_COLOR=1 uv run mypy <file>`; no blanket `# type: ignore`; pathspec-only commits; untracked runtime dirs (.gsd/, .planning/state.json, .planning/tmp/, .planning/ui-reviews/) and the pre-staged mypy.ini deletion stay untouched.
- Test coverage: handlers -> tests/unit/mcp (test_integration.py exercises all four handlers); search.py -> tests/unit/cli/test_search.py; connection.py -> tests/unit/db/test_database.py (tests/conftest.py builds DatabaseConnection fixtures). Full suite runs at the end of Task 3.

Purpose: continue chipping the phase-03 deferred mypy debt file-by-file with provable zero behavior change; after this batch ~46 errors in ~28 files remain for later batches or milestone-acceptance.
Output: three mypy-clean files plus one widened type in hybrid.py, green suite, clean ruff, full-project count 78 -> 46, three pathspec-scoped commits.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/quick/260917-bo2-typing-debt-batch-1-clear-search-rerank-/260917-bo2-PLAN.md
@.planning/quick/260917-dkf-typing-debt-batch-2-clear-indexing-watch/260917-dkf-PLAN.md
@src/sif/mcp/handlers.py
@src/sif/cli/commands/search.py
@src/sif/search/hybrid.py
@src/sif/database/connection.py
@pyproject.toml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Declare ToolHandler attributes as ClassVar on the base (12 errors -> 0)</name>
  <files>src/sif/mcp/handlers.py</files>
  <action>
Edits confined to the ToolHandler base class in src/sif/mcp/handlers.py — the ONLY edit site for all 12 errors (the four subclasses are already correct and stay byte-identical):

1. Lines 31-33, change the three bare annotations to ClassVar form (ClassVar is already imported at line 7 from typing): `name: ClassVar[str]`, `description: ClassVar[str]`, `input_schema: ClassVar[dict[str, Any]]`. Do NOT add `= ...` defaults — annotation-only, exactly as today.

2. Touch nothing else: the four subclasses' ClassVar declarations (QueryToolHandler 48-62, GetToolHandler 91-103, MultiGetToolHandler 136-145, StatusToolHandler 172-178), the abstract `handle` signature, and `create_default_tools` stay byte-identical.

Rationale (planner-verified): mypy requires base and subclass to agree on class-vs-instance variable kind; these are per-handler constants (server.py reads `tool.name` / `h.input_schema` as class attributes, grep found no instance assignment anywhere in src/sif/mcp). A bare annotation and a ClassVar annotation both create no runtime attribute — zero behavior change. Probe-verified clean under --strict.

Then run the verification; commit pathspec-only: `git commit -m "fix(260917-kav): declare ToolHandler attrs as ClassVar; handlers.py mypy-clean" -- src/sif/mcp/handlers.py`.
  </action>
  <verify>
    <automated>env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/mcp/handlers.py > /dev/null 2>&1 && env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/mcp -q && ruff check src/sif/mcp/handlers.py && ruff format --check src/sif/mcp/handlers.py</automated>
  </verify>
  <done>mypy on handlers.py exits 0 (the pyproject unused-section NOTE may print — not an error); tests/unit/mcp fully green; ruff check + format clean on the file; diff is exactly the three ClassVar markers on the base annotations; pathspec commit created.</done>
</task>

<task type="auto">
  <name>Task 2: Type search.py generics and content narrowing; widen SearchPipeline reranker union (11 errors -> 0)</name>
  <files>src/sif/cli/commands/search.py, src/sif/search/hybrid.py</files>
  <action>
Edits in src/sif/cli/commands/search.py:

1. Imports: add `from typing import Any` to the stdlib group (after `import json`, blank line before the click block — straight imports first, matching connection.py/embedder.py layout; if ruff isort disagrees, `ruff check --fix src/sif/cli/commands/search.py` settles it, scoped to this file).

2. The four format helpers — `format_results_json` (44), `format_results_csv` (53), `format_results_md` (62), `format_results_xml` (81): `results: list` -> `results: list[Any]`. Rationale: duck-typed helpers taking both `list[SearchResult]` and the `list[dict[str, Any]]` output of `add_line_numbers_to_results`; bodies branch via hasattr, so a precise union would not type-check. Bodies unchanged.

3. The three Click command signatures — `collection: tuple` -> `collection: tuple[str, ...]` in search_cmd (124), vsearch_cmd (276), query_cmd (421). Click `multiple=True` yields a tuple of str.

4. The three prepend_line_numbers call sites (243, 379, 594) — identical shape in all three commands; replace the bare getattr guard with a walrus binding and pass the binding:
   `if line_numbers and (content := getattr(r, "content", None)):` followed by `content = prepend_line_numbers(content)` — the subsequent `if len(content) > _CONTENT_MAX_LEN` truncation and `row.append(content)` stay as-is. The guard evaluates the same expression as today; the binding is narrowed to str at the call (the truthiness check already rejected None/empty). Do NOT widen prepend_line_numbers in src/sif/cli/formatters.py — it cannot handle None and get.py's calls are already clean. Also leave the `any(getattr(r, "content", None) for r in results)` expressions at 231/368/582 untouched (they produce no errors).

Edits in src/sif/search/hybrid.py:

5. TYPE_CHECKING import (line 18): `from sif.search.rerank import CrossEncoderReranker, LlamaCppReranker` -> add `Qwen3Reranker` (alphabetical: CrossEncoderReranker, LlamaCppReranker, Qwen3Reranker).

6. SearchPipeline.__init__ reranker param (line 140): `reranker: LlamaCppReranker | CrossEncoderReranker | None = None` -> `reranker: LlamaCppReranker | CrossEncoderReranker | Qwen3Reranker | None = None`. This mirrors create_reranker's declared return from batch 1; all three rerank() signatures are identical so the call at line 233 type-checks (planner grep-verified). No shared alias/Protocol — minimal union widening, type-level only. `from __future__ import annotations` is already line 3. Touch nothing else in hybrid.py.

Scope guards: full-project mypy still shows ~46+ errors in OTHER files after the per-file gate — expected, batch-3 scope is these two files. Do NOT edit pyproject.toml, formatters.py, or get.py. No blanket ignores.

Then run the verification; commit pathspec-only: `git commit -m "fix(260917-kav): type search.py generics and content narrowing; widen pipeline reranker union" -- src/sif/cli/commands/search.py src/sif/search/hybrid.py`.
  </action>
  <verify>
    <automated>env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/cli/commands/search.py > /dev/null 2>&1 && env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py tests/unit/cli/test_formatters.py -q && ruff check src/sif/cli/commands/search.py src/sif/search/hybrid.py && ruff format --check src/sif/cli/commands/search.py src/sif/search/hybrid.py</automated>
  </verify>
  <done>mypy on search.py exits 0 (follows imports into hybrid.py, validating the widened union; the pyproject unused-section NOTE may print — under single-file invocation of a sif.cli module the sif.cli.* override applies and only relaxes Click decorators, so strict generics remain enforced); tests/unit/cli/test_search.py + test_formatters.py fully green; ruff clean on both files; diff is exactly the typing import, 4 list[Any], 3 tuple[str, ...], 3 walrus narrowings, and the 2 hybrid.py type-level lines; pathspec commit created.</done>
</task>

<task type="auto">
  <name>Task 3: Parameterize connection.py sqlite generics; full-project gate (9 errors -> 0, 78 -> 46)</name>
  <files>src/sif/database/connection.py</files>
  <action>
Edits confined to src/sif/database/connection.py:

1. Imports: add `from typing import Any` to the stdlib group (after `import sqlite3`, before `from collections.abc import Generator` — straight imports first; ruff gate settles placement).

2. `DatabaseConnection.execute` (line 63), `fetchone` (line 85), `fetchall` (line 95) — identical signature edit: `parameters: tuple | dict | None = None` -> `parameters: tuple[Any, ...] | dict[str, Any] | None = None`. This matches what sqlite3 typeshed accepts (`Sequence[Any] | dict[str, Any]`); the `if parameters` truthiness at line 67 keeps identical semantics (empty tuple/dict was already falsy -> no-params branch).

3. `executemany` (line 74): `parameters: list[tuple | dict]` -> `parameters: list[tuple[Any, ...] | dict[str, Any]]`.

4. `fetchone` body (lines 89-90): keep `cursor = conn.execute(query, parameters or ())` as-is, then replace `return cursor.fetchone()` with a typed local: `row: sqlite3.Row | None = cursor.fetchone()` followed by `return row`. Typeshed declares `Cursor.fetchone() -> Any` (row_factory variance); with `row_factory = sqlite3.Row` set at runtime this is exact. Do NOT touch fetchall's `return cursor.fetchall()` (typeshed's `list[Any]` return is accepted; it produces no error today).

5. Touch nothing else: _create_connection, connect/transaction context managers, ConnectionPool, and the sqlite_vec loading stay byte-identical.

Then the full gates per CLAUDE.md: per-file mypy, the FULL quality suite, and the full-project mypy count check (expect exactly 46 errors — 78 minus this batch's 32; attribution planner-verified to match single-file counts). If the full-project count is not exactly 46, diff the current error list against the pre-task baseline before concluding — the three target files must be at zero regardless, and any unexpected NEW error elsewhere must be investigated, not ignored. Commit pathspec-only: `git commit -m "fix(260917-kav): parameterize connection.py sqlite generics; connection.py mypy-clean" -- src/sif/database/connection.py`.
  </action>
  <verify>
    <automated>env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/database/connection.py > /dev/null 2>&1 && env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/db/test_database.py -q && ruff check src tests && ruff format --check src tests && env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q && [ "$(env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif 2>&1 | grep -c 'error:')" -le 46 ] && ! env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif 2>&1 | grep "error:" | grep -q "mcp/handlers.py\|cli/commands/search.py\|database/connection.py"</automated>
  </verify>
  <done>mypy on connection.py exits 0; tests/unit/db/test_database.py green; full pytest suite green (676 passed / 0 failed expected; exactly-2 pre-existing caplog flakers in tests/unit/embedding/test_openai_embedder.py are WINDOWS.md #3/#4 — verify they are exactly those 2); ruff check + format --check clean across src and tests; full-project mypy shows exactly 46 errors (investigate any deviation, never paper over it) with zero in the three target files; diff review confirms the typing import, parameterized unions, and typed row local only — zero behavior change; pathspec commit created.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| none new | Typing-only change: annotations, generics parameterization, walrus narrowing, one type-level union widening. No new inputs, outputs, or call paths. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260917-kav-01 | Tampering | connection.py parameter annotations near SQL execution | low | accept | Annotation-only; the query strings and parameter values passed at runtime are unchanged, and prepared-statement usage is untouched. |
| T-260917-kav-02 | Information disclosure | handlers.py ClassVar annotations on tool metadata | low | accept | name/description/input_schema were already class-level constants at runtime; the edit only corrects the declared variable kind. |
</threat_model>

<verification>
1. Per-file gates (definition of done for the typing work): `env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/mcp/handlers.py` / `src/sif/cli/commands/search.py` / `src/sif/database/connection.py` — each exits 0. The `pyproject.toml: note: unused section(s)` note is acceptable output; any `error:` line is a failure.
2. Full quality suite (CLAUDE.md): `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` (676 passed / 0 failed expected; 2 order-dependent caplog failures in tests/unit/embedding/test_openai_embedder.py are pre-existing WINDOWS.md #3/#4 if they appear), `ruff check src tests`, `ruff format --check src tests`.
3. Full-project count check: `env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif 2>&1 | tail -1` reports 46 errors in ~28 files (78 - 32; investigate any deviation, never paper over it), and no error line references any of the three target files.
4. Zero-behavior-change audit: `git diff HEAD~3 -- src/sif/mcp/handlers.py src/sif/cli/commands/search.py src/sif/search/hybrid.py src/sif/database/connection.py` — every hunk is one of: the three ClassVar markers on the ToolHandler base, `from typing import Any` imports, 4x `list[Any]` helper params, 3x `tuple[str, ...]` Click params, 3x walrus narrowing at the prepend_line_numbers call sites, the Qwen3Reranker TYPE_CHECKING import + widened reranker annotation in hybrid.py, parameterized `tuple[Any, ...] | dict[str, Any]` unions, the typed `row: sqlite3.Row | None` local. No logic edits, no guard removals, no value changes.
5. Commits are pathspec-scoped to the four files only; `git status` still shows the untracked runtime dirs (.gsd/, .planning/state.json, .planning/tmp/, .planning/ui-reviews/) and the pre-staged mypy.ini deletion untouched by this task's commits.
</verification>

<success_criteria>
- All three files mypy strict-clean in this environment (12 + 11 + 9 = 32 errors cleared).
- Full-project mypy 78 -> 46 errors; zero errors remain in handlers.py, search.py, or connection.py.
- Test suite green at baseline; ruff check + format --check clean.
- Zero behavior change proven by diff audit (annotation-only edits, walrus binds the same value the guard already computed, union widening accepts exactly what create_reranker declares).
- Three atomic pathspec commits landed; no unrelated files swept in.
- SUMMARY records deferred-item progress for the next batches (~46 errors remain in ~28 files).
</success_criteria>

<output>
Create `.planning/quick/260917-kav-typing-debt-batch-3-clear-mcp-handlers-p/260917-kav-SUMMARY.md` when done
</output>
