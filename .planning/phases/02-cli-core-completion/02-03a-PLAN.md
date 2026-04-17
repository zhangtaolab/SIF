---
phase: 02-cli-core-completion
plan: 03a
type: execute
wave: 2
depends_on:
  - 02-02-PLAN.md
files_modified:
  - src/docsift/core/models.py
  - src/docsift/database/schema.py
  - src/docsift/database/repositories.py
  - src/docsift/cli/commands/collection.py
  - src/docsift/cli/commands/index.py
  - tests/unit/cli/test_collection.py
autonomous: true
requirements:
  - CLI-03
  - CLI-04
must_haves:
  truths:
    - User can set a pre-index shell command per collection with `collection update-cmd`
    - User can clear a pre-index shell command with `collection update-cmd <name> --clear`
    - The pre-index command runs before `index update` and fails fast on non-zero exit
  artifacts:
    - path: src/docsift/core/models.py
      provides: Collection.pre_update_cmd field
      contains: "pre_update_cmd: Optional[str] = None"
    - path: src/docsift/database/schema.py
      provides: Safe migration for pre_update_cmd column
      contains: "_add_column_if_missing"
    - path: src/docsift/database/repositories.py
      provides: pre_update_cmd persistence
      contains: "def list_enabled"
    - path: src/docsift/cli/commands/collection.py
      provides: update-cmd command
      contains: "collection_update_cmd"
    - path: src/docsift/cli/commands/index.py
      provides: pre_update_cmd hook in index update
      contains: "subprocess.run"
    - path: tests/unit/cli/test_collection.py
      provides: Unit tests for update-cmd and index hook
      contains: "test_collection_update_cmd_set"
  key_links:
    - from: index.py update_cmd
      to: Collection.pre_update_cmd
      via: subprocess.run with shell=True, fail fast on non-zero exit
---

<objective>
Implement `collection update-cmd` for pre-index shell commands and inject the hook into `index update`.

Purpose: CLI-03 requires collection management for indexing workflows with pre-update shell commands.
Output: Updated models, schema migration, repository methods, CLI commands, and tests.
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
From src/docsift/core/models.py:
```python
@dataclass
class Collection:
    name: str
    path: str
    pattern: str = "**/*.md"
    ignore_patterns: List[str] = field(default_factory=list)
    include_by_default: bool = True
    description: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ...
```

From src/docsift/database/schema.py:
```python
class SchemaManager:
    def _create_collections_table(self) -> None:
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                path TEXT NOT NULL,
                pattern TEXT DEFAULT '**/*.md',
                ignore_patterns TEXT DEFAULT '[]',
                include_by_default INTEGER DEFAULT 1,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_indexed_at TEXT,
                document_count INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0
            )
        """)
```

From src/docsift/database/repositories.py:
```python
class CollectionRepository:
    def create(self, collection: Collection) -> Collection: ...
    def update(self, collection: Collection) -> Collection: ...
    def _row_to_collection(self, row: sqlite3.Row) -> Collection: ...
```

From src/docsift/cli/commands/collection.py:
```python
@collection_group.command("enable")
def collection_enable(ctx: click.Context, name: str) -> None:
    collection.include_by_default = True
    repo.update(collection)
```

Per D-04/D-05/D-06: pre_update_cmd is stored on Collection, runs before index update, fails fast on error.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Set up Collection model, schema, and repository for pre_update_cmd</name>
  <files>src/docsift/core/models.py, src/docsift/database/schema.py, src/docsift/database/repositories.py</files>
  <read_first>
    - src/docsift/core/models.py
    - src/docsift/database/schema.py
    - src/docsift/database/repositories.py
  </read_first>
  <action>
    1. In `src/docsift/core/models.py`, add `pre_update_cmd: Optional[str] = None` immediately after the `description: Optional[str] = None` field in the `Collection` dataclass. Include it in `to_dict()` as `"pre_update_cmd": self.pre_update_cmd` and in `from_dict()` as `pre_update_cmd=data.get("pre_update_cmd")`.

    2. In `src/docsift/database/schema.py`, add a private method `_add_column_if_missing(self, table: str, column: str, dtype: str) -> None` to `SchemaManager` that runs `PRAGMA table_info({table})`, checks if `column` is in the result, and if not executes `ALTER TABLE {table} ADD COLUMN {column} {dtype}`. Then call `self._add_column_if_missing("collections", "pre_update_cmd", "TEXT")` at the end of `_create_collections_table()`.

    3. In `src/docsift/database/repositories.py`:
       - In `CollectionRepository.create()`, add `pre_update_cmd` to the INSERT column list and bind values. The parameter tuple should include `collection.pre_update_cmd` as the 12th value (after `chunk_count`).
       - In `CollectionRepository.update()`, add `pre_update_cmd = ?` to the UPDATE SET list and include `collection.pre_update_cmd` in the parameter tuple (before `WHERE id = ?`).
       - In `CollectionRepository._row_to_collection()`, pass `pre_update_cmd=row["pre_update_cmd"]` to the `Collection(...)` constructor.
       - Add a new method `list_enabled(self) -> List[Collection]` that executes `SELECT * FROM collections WHERE include_by_default = 1 ORDER BY name` and returns `[self._row_to_collection(row) for row in cursor.fetchall()]`.
  </action>
  <verify>
    <automated>python -c "from docsift.core.models import Collection; c = Collection(name='x', path='/tmp', pre_update_cmd='echo hi'); print(c.pre_update_cmd)"</automated>
  </verify>
  <done>Collection accepts pre_update_cmd, schema manager can add the column idempotently, and repository supports pre_update_cmd persistence and list_enabled.</done>
  <acceptance_criteria>
    - `src/docsift/core/models.py` contains `pre_update_cmd: Optional[str] = None`
    - `src/docsift/core/models.py` `to_dict()` contains `"pre_update_cmd": self.pre_update_cmd`
    - `src/docsift/core/models.py` `from_dict()` contains `pre_update_cmd=data.get("pre_update_cmd")`
    - `src/docsift/database/schema.py` contains `def _add_column_if_missing`
    - `src/docsift/database/schema.py` `_create_collections_table` ends with `_add_column_if_missing("collections", "pre_update_cmd", "TEXT")`
    - `CollectionRepository.create` SQL contains `pre_update_cmd`
    - `CollectionRepository.update` SQL contains `pre_update_cmd = ?`
    - `CollectionRepository._row_to_collection` passes `pre_update_cmd=row["pre_update_cmd"]`
    - `CollectionRepository` contains `def list_enabled(self) -> List[Collection]:`
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Add collection update-cmd, include, exclude commands</name>
  <files>src/docsift/cli/commands/collection.py</files>
  <read_first>
    - src/docsift/cli/commands/collection.py
    - src/docsift/core/models.py
  </read_first>
  <action>
    Modify `src/docsift/cli/commands/collection.py` to add three new commands after the existing `collection_disable` command:

    1. `collection update-cmd`:
       ```python
       @collection_group.command("update-cmd")
       @click.argument("name")
       @click.option("--cmd", "-c", help="Shell command to run before indexing")
       @click.option("--clear", is_flag=True, help="Clear the pre-update command")
       @click.pass_context
       def collection_update_cmd(ctx: click.Context, name: str, cmd: str | None, clear: bool) -> None:
           """Set or clear a pre-index shell command for a collection."""
           index_path = ctx.obj["index_path"]
           db = Database(index_path)
           db.init_schema()
           with db.transaction() as conn:
               repo = CollectionRepository(conn)
               collection = repo.get_by_name(name)
               if not collection:
                   raise click.ClickException(f"Collection '{name}' not found")
               if clear:
                   collection.pre_update_cmd = None
               elif cmd is not None:
                   collection.pre_update_cmd = cmd
               else:
                   raise click.ClickException("Provide --cmd or --clear")
               repo.update(collection)
           if clear:
               console.print(f"[green]Cleared pre-update command for '{name}'[/green]")
           else:
               console.print(f"[green]Set pre-update command for '{name}': {cmd}[/green]")
       ```

    2. `collection include`:
       ```python
       @collection_group.command("include")
       @click.argument("name")
       @click.pass_context
       def collection_include(ctx: click.Context, name: str) -> None:
           """Include a collection in default searches."""
           index_path = ctx.obj["index_path"]
           db = Database(index_path)
           db.init_schema()
           with db.transaction() as conn:
               repo = CollectionRepository(conn)
               collection = repo.get_by_name(name)
               if not collection:
                   raise click.ClickException(f"Collection '{name}' not found")
               collection.include_by_default = True
               repo.update(collection)
           console.print(f"[green]Collection '{name}' included in default searches[/green]")
       ```

    3. `collection exclude`:
       ```python
       @collection_group.command("exclude")
       @click.argument("name")
       @click.pass_context
       def collection_exclude(ctx: click.Context, name: str) -> None:
           """Exclude a collection from default searches."""
           index_path = ctx.obj["index_path"]
           db = Database(index_path)
           db.init_schema()
           with db.transaction() as conn:
               repo = CollectionRepository(conn)
               collection = repo.get_by_name(name)
               if not collection:
                   raise click.ClickException(f"Collection '{name}' not found")
               collection.include_by_default = False
               repo.update(collection)
           console.print(f"[green]Collection '{name}' excluded from default searches[/green]")
       ```
  </action>
  <verify>
    <automated>python -m docsift.cli.main collection update-cmd --help && python -m docsift.cli.main collection include --help && python -m docsift.cli.main collection exclude --help</automated>
  </verify>
  <done>All three new collection subcommands are registered and show help.</done>
  <acceptance_criteria>
    - `src/docsift/cli/commands/collection.py` contains `@collection_group.command("update-cmd")`
    - `src/docsift/cli/commands/collection.py` contains `@collection_group.command("include")`
    - `src/docsift/cli/commands/collection.py` contains `@collection_group.command("exclude")`
    - `python -m docsift.cli.main collection update-cmd --help` exits 0
    - `python -m docsift.cli.main collection include --help` exits 0
    - `python -m docsift.cli.main collection exclude --help` exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Inject pre_update_cmd hook into index update</name>
  <files>src/docsift/cli/commands/index.py</files>
  <read_first>
    - src/docsift/cli/commands/index.py
    - src/docsift/cli/commands/collection.py
  </read_first>
  <action>
    Modify `src/docsift/cli/commands/index.py` in the `update_cmd` function. Immediately after the line `console.print(f"\n[bold]Updating collection: {coll.name}[/bold]")` and before the scanner is created, add:

    ```python
            if coll.pre_update_cmd:
                console.print(f"  Running pre-update command: {coll.pre_update_cmd}")
                import subprocess
                result = subprocess.run(
                    coll.pre_update_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    raise click.ClickException(
                        f"Pre-update command failed for '{coll.name}' (exit {result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
                    )
    ```

    Do NOT change any other logic in the update loop.
  </action>
  <verify>
    <automated>python -c "from docsift.cli.commands.index import update_cmd; print('import ok')"</automated>
  </verify>
  <done>index update contains the pre_update_cmd subprocess hook with fail-fast behavior.</done>
  <acceptance_criteria>
    - `src/docsift/cli/commands/index.py` contains `subprocess.run(coll.pre_update_cmd, shell=True, capture_output=True, text=True)`
    - `src/docsift/cli/commands/index.py` contains `raise click.ClickException` when `result.returncode != 0`
    - The subprocess block appears inside the `for coll in collections:` loop before `scanner.scan`
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Add unit tests for collection and index changes</name>
  <files>tests/unit/cli/test_collection.py</files>
  <read_first>
    - src/docsift/cli/commands/collection.py
    - src/docsift/cli/commands/index.py
    - tests/unit/cli/test_collection_commands.py
  </read_first>
  <action>
    Create `tests/unit/cli/test_collection.py` with the following tests using `click.testing.CliRunner` and `unittest.mock`:

    1. `test_collection_update_cmd_set` — Mocks `Database` and `CollectionRepository`. Invokes `collection_update_cmd` with `["notes", "--cmd", "git pull"]`. Asserts exit code 0, output contains "Set pre-update command", and `collection.pre_update_cmd == "git pull"`.
    2. `test_collection_update_cmd_clear` — Same mocks. Sets `collection.pre_update_cmd = "git pull"` initially. Invokes with `["notes", "--clear"]`. Asserts exit code 0 and `collection.pre_update_cmd is None` after update.
    3. `test_collection_update_cmd_missing_collection` — Mocks `repo.get_by_name` to return None. Invokes with `["missing", "--cmd", "git pull"]`. Asserts exit code != 0 and output contains "not found".
    4. `test_collection_include` — Mocks repos. Sets `include_by_default = False`. Invokes `collection_include` with `["notes"]`. Asserts it becomes True and output contains "included".
    5. `test_collection_exclude` — Mocks repos. Sets `include_by_default = True`. Invokes `collection_exclude` with `["notes"]`. Asserts it becomes False and output contains "excluded".
    6. `test_index_update_runs_pre_update_cmd` — Mocks `Database`, `CollectionRepository`, `DocumentRepository`, `FileScanner`, `MarkdownParser`, and `subprocess.run`. Creates a collection with `pre_update_cmd = "echo hello"`. Invokes `update_cmd`. Asserts `subprocess.run` was called with `"echo hello"` and output contains "Running pre-update command".
    7. `test_index_update_fails_fast_on_pre_update_cmd_error` — Same mocks but `subprocess.run` returns `MagicMock(returncode=1, stderr="failed")`. Invokes `update_cmd`. Asserts exit code != 0 and output contains "Pre-update command failed".
  </action>
  <verify>
    <automated>pytest tests/unit/cli/test_collection.py -x</automated>
  </verify>
  <done>All collection and index hook tests pass.</done>
  <acceptance_criteria>
    - `tests/unit/cli/test_collection.py` exists and contains `test_collection_update_cmd_set`
    - `tests/unit/cli/test_collection.py` contains `test_index_update_runs_pre_update_cmd`
    - `tests/unit/cli/test_collection.py` contains `test_index_update_fails_fast_on_pre_update_cmd_error`
    - `pytest tests/unit/cli/test_collection.py -x` exits with code 0
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI input -> subprocess | User-provided shell command crosses into OS execution |
| CLI input -> repository | Collection name crosses into database queries |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-01 | Tampering/Elevation | collection update-cmd | mitigate | Command runs with user's privileges via `subprocess.run(..., shell=True)`; documented as trusted-user input only |
| T-02-03 | Tampering | index update hook | mitigate | Fail fast on non-zero exit; capture and display stderr/stdout so user sees failure reason |
| T-02-02 | Tampering | collection include/exclude | accept | Only toggles a boolean flag; no filesystem or network impact |
</threat_model>

<verification>
- `python -m docsift.cli.main collection update-cmd --help` shows the command
- `python -m docsift.cli.main collection include --help` shows the command
- `python -m docsift.cli.main collection exclude --help` shows the command
- `pytest tests/unit/cli/test_collection.py -x` passes
</verification>

<success_criteria>
- `docsift collection update-cmd notes --cmd "git pull"` stores the command
- `docsift collection update-cmd notes --clear` removes the command
- `docsift index update notes` runs the pre-update command and stops on failure
- `docsift collection include notes` and `docsift collection exclude notes` toggle default search participation
</success_criteria>

<output>
After completion, create `.planning/phases/02-cli-core-completion/02-03a-SUMMARY.md`
</output>
