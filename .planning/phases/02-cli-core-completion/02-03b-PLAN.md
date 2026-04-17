---
phase: 02-cli-core-completion
plan: 03b
type: execute
wave: 3
depends_on:
  - 02-03a-PLAN.md
files_modified:
  - src/docsift/cli/commands/search.py
  - tests/unit/cli/test_search.py
autonomous: true
requirements:
  - CLI-04
must_haves:
  truths:
    - User can include or exclude collections from default queries with `collection include/exclude`
    - Default search respects include_by_default unless `--all` is passed
  artifacts:
    - path: src/docsift/cli/commands/search.py
      provides: --all wired to bypass include_by_default filter
      contains: "search_all"
    - path: tests/unit/cli/test_search.py
      provides: Unit tests for search filtering and --all
      contains: "test_search_respects_include_by_default"
  key_links:
    - from: search.py search_cmd
      to: CollectionRepository.list_enabled
      via: search_all flag controls collection resolution
---

<objective>
Wire `--all` flag into `search`, `query`, and `vsearch` commands so default searches respect `include_by_default`.

Purpose: CLI-04 requires collection participation control in default queries.
Output: Updated search commands and unit tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02-cli-core-completion/02-CONTEXT.md
@.planning/phases/02-cli-core-completion/02-PATTERNS.md
@.planning/phases/02-cli-core-completion/02-RESEARCH.md

<interfaces>
From src/docsift/cli/commands/search.py:
```python
@search_group.command("search")
@click.argument("query")
... various output options ...
def search_cmd(...): ...

def format_results_json(results: list) -> str: ...
def format_results_csv(results: list) -> str: ...
def format_results_md(results: list, query: str) -> str: ...
def format_results_xml(results: list, query: str) -> str: ...
```

Per D-07/D-08: include/exclude are aliases for enable/disable, toggling include_by_default.
Per RESEARCH.md: `--all` is currently a no-op in search.py and must be wired.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Wire --all flag into search, query, and vsearch</name>
  <files>src/docsift/cli/commands/search.py</files>
  <read_first>
    - src/docsift/cli/commands/search.py
    - src/docsift/database/repositories.py
  </read_first>
  <action>
    Modify `src/docsift/cli/commands/search.py`:

    1. In `search_cmd`, after the existing collection resolution block (the `if collection:` block), add:
       ```python
       elif not search_all:
           with db.connection:
               repo = CollectionRepository(db.connection)
               enabled = repo.list_enabled()
               options.collection_ids = [c.id for c in enabled]
       ```

    2. In `query_cmd`, after the existing collection resolution block, add the identical snippet:
       ```python
       elif not search_all:
           with db.connection:
               repo = CollectionRepository(db.connection)
               enabled = repo.list_enabled()
               options.collection_ids = [c.id for c in enabled]
       ```

    3. In `vsearch_cmd`, add a new option after the `--collection` option:
       ```python
       @click.option("--all", "search_all", is_flag=True, help="Search all collections")
       ```
       Add `search_all: bool` to the function signature. After the existing `if collection:` block, add:
       ```python
       elif not search_all:
           with db.connection:
               repo = CollectionRepository(db.connection)
               enabled = repo.list_enabled()
               options.collection_ids = [c.id for c in enabled]
       ```
  </action>
  <verify>
    <automated>python -c "from docsift.cli.commands.search import search_cmd, query_cmd, vsearch_cmd; print('import ok')"</automated>
  </verify>
  <done>search, query, and vsearch all respect include_by_default unless --all is passed.</done>
  <acceptance_criteria>
    - `search_cmd` contains `elif not search_all:` followed by `repo.list_enabled()`
    - `query_cmd` contains `elif not search_all:` followed by `repo.list_enabled()`
    - `vsearch_cmd` has `--all` option and contains `elif not search_all:` followed by `repo.list_enabled()`
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Add unit tests for search filtering</name>
  <files>tests/unit/cli/test_search.py</files>
  <read_first>
    - src/docsift/cli/commands/search.py
    - tests/unit/cli/test_collection_commands.py
  </read_first>
  <action>
    Create `tests/unit/cli/test_search.py` with the following tests using `click.testing.CliRunner` and `unittest.mock`:

    1. `test_search_respects_include_by_default` — Mocks `Database`, `CollectionRepository`, `BM25Searcher`. Creates two collections: one enabled, one disabled. Invokes `search_cmd` with `["foo"]` (no `--all`). Asserts `BM25Searcher.search` was called with `options.collection_ids` containing only the enabled collection ID.
    2. `test_search_all_bypasses_include_by_default` — Same setup. Invokes with `["foo", "--all"]`. Asserts `options.collection_ids` is None (or contains both IDs).
    3. `test_query_respects_include_by_default` — Same pattern for `query_cmd`.
    4. `test_vsearch_respects_include_by_default` — Same pattern for `vsearch_cmd`.
  </action>
  <verify>
    <automated>pytest tests/unit/cli/test_search.py -x</automated>
  </verify>
  <done>All search filtering tests pass.</done>
  <acceptance_criteria>
    - `tests/unit/cli/test_search.py` exists and contains `test_search_respects_include_by_default`
    - `tests/unit/cli/test_search.py` contains `test_search_all_bypasses_include_by_default`
    - `pytest tests/unit/cli/test_search.py -x` exits with code 0
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI input -> repository | Collection name crosses into database queries |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-02 | Tampering | collection include/exclude | accept | Only toggles a boolean flag; no filesystem or network impact |
</threat_model>

<verification>
- `python -m docsift.cli.main search foo` only searches enabled collections
- `python -m docsift.cli.main search foo --all` searches all collections
- `pytest tests/unit/cli/test_search.py -x` passes
</verification>

<success_criteria>
- `docsift search foo` only searches enabled collections; `docsift search foo --all` searches all
- Same `--all` behavior works for `query` and `vsearch`
</success_criteria>

<output>
After completion, create `.planning/phases/02-cli-core-completion/02-03b-SUMMARY.md`
</output>
