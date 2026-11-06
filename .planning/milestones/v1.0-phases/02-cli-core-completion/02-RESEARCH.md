# Phase 2: CLI Core Completion - Research

**Researched:** 2026-04-15
**Domain:** Python Click CLI, SQLite repositories, model downloading
**Confidence:** HIGH

## Summary

Phase 2 delivers six CLI capabilities: `multi-get` batch retrieval, `ls` virtual file tree, `collection update-cmd` pre-index hooks, `collection include/exclude` default-search toggles, `pull` GGUF model downloading, and `--line-numbers` output formatting. The codebase already uses Click groups with rich console output, repository-pattern database access, and an `OutputFormatter` class for structured formats (JSON, CSV, MD, XML, table, files).

**Primary recommendation:** Extend existing commands in-place, reuse `OutputFormatter` and `rich.tree.Tree`, add `pre_update_cmd` to `Collection` with a safe schema migration, and implement `pull` with `huggingface_hub.hf_hub_download` primary + `modelscope` fallback.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `multi-get` | CLI (Presentation) | Database (Repository) | CLI parses pattern, repositories fetch and filter documents |
| `ls` | CLI (Presentation) | Database (Repository) | CLI builds virtual tree from repository results |
| `collection update-cmd` | CLI (Presentation) | Database (Repository) | CLI stores command string; repository persists it |
| `collection include/exclude` | CLI (Presentation) | Database (Repository) | CLI toggles boolean; repository updates row |
| `pull` | CLI (Presentation) | External services | CLI orchestrates download and local cache |
| `--line-numbers` | CLI (Presentation) | — | Pure formatting concern in command output |
| `index update` hook | CLI (Presentation) | OS (subprocess) | CLI runs shell command before indexing |
| Default-search filtering | Search (Domain) | Database (Repository) | Searchers build SQL with collection ID filter |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Click | 8.3.2 [VERIFIED: `python -c "import click; print(click.__version__)"`] | CLI framework | Already used throughout the codebase |
| rich | 13.x+ | Console tables, trees, progress | Used in all CLI commands |
| sqlite3 (stdlib) | — | Local database | All persistent state lives in SQLite |
| huggingface_hub | 1.3.2 [VERIFIED: `python -c "import huggingface_hub; print(huggingface_hub.__version__)"`] | Download GGUF files from HuggingFace | Industry standard, `hf_hub_download` supports resume/cache |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| modelscope | — | Fallback download for China/regional access | Only when HuggingFace is unreachable (D-10) |
| fnmatch (stdlib) | — | Glob matching for `multi-get` | Already used in `get.py` and `indexing/scanner.py` |
| subprocess (stdlib) | — | Execute `pre_update_cmd` | Required for `update-cmd` hook |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `huggingface_hub` | `urllib` direct URL download | No resume, no cache, no verification |
| `modelscope` | — | Not installed in current env; fallback per D-10 is acceptable |
| `rich.tree.Tree` | Custom string tree builder | `Tree` is already imported and used in `collection ls` |

**Installation:**
```bash
pip install -e ".[dev]"
```

**Version verification:**
```bash
python -c "import click; print(click.__version__)"   # 8.3.2
python -c "import huggingface_hub; print(huggingface_hub.__version__)"  # 1.3.2
```

## Architecture Patterns

### System Architecture Diagram

```
User Input (Click CLI)
       |
       v
Command Handler (src/docsift/cli/commands/*.py)
       |
       +---> Database.init_schema() ---> SchemaManager
       |
       +---> Repository (CollectionRepository / DocumentRepository)
       |           |
       |           v
       |       SQLite (collections, documents, document_chunks)
       |
       +---> subprocess.run()  [for update-cmd hook]
       |
       +---> hf_hub_download() / modelscope.snapshot_download()  [for pull]
       |
       v
OutputFormatter / rich.Console
       |
       v
Terminal Output (table, json, csv, md, xml, files)
```

### Recommended Project Structure

No new top-level packages are required. Changes are localized to existing modules:

```
src/docsift/
├── cli/
│   ├── commands/
│   │   ├── collection.py    # add update-cmd, include, exclude
│   │   ├── get.py           # expand multi-get, add --line-numbers
│   │   ├── search.py        # add --line-numbers, wire --all
│   │   └── index.py         # inject pre_update_cmd hook in update
│   ├── formatters.py        # extend for line-number-aware output
│   └── main.py              # register new top-level ls command
├── core/
│   └── models.py            # add pre_update_cmd to Collection
├── database/
│   ├── schema.py            # safe migration for pre_update_cmd column
│   └── repositories.py      # add list_enabled() for default search
└── models/
    └── download.py          # extend for HF primary + modelscope fallback
```

### Pattern 1: Click Command Registration
**What:** Top-level commands are registered on `cli` in `main.py`; subcommands live in groups (`collection`, `index`, `search`, `get`).
**When to use:** Follow this for `ls` (top-level) and `collection update-cmd` / `include` / `exclude` (group subcommands).
**Example:**
```python
# Source: src/docsift/cli/main.py
from docsift.cli.commands.collection import collection_group
cli.add_command(collection_group)

# In collection.py
@click.group("collection")
def collection_group() -> None:
    """Manage document collections."""
    pass

@collection_group.command("update-cmd")
@click.argument("name")
@click.option("--cmd", "-c", help="Shell command to run before indexing")
def collection_update_cmd(name: str, cmd: str | None) -> None:
    ...
```

### Pattern 2: Database Access in CLI Commands
**What:** Commands receive `index_path` from `ctx.obj`, instantiate `Database`, and use `db.transaction()` or `db.connection` with repositories.
**When to use:** All database-mutating commands must use `db.transaction()`; read-only commands may use `db.connection` directly.
**Example:**
```python
# Source: src/docsift/cli/commands/collection.py
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
```

### Pattern 3: OutputFormatter for Structured Output
**What:** `OutputFormatter` in `formatters.py` dispatches to JSON, CSV, MD, XML, table, or files output.
**When to use:** Extend the formatter or preprocess data before passing it to `formatter.print()` for `--line-numbers` support.
**Example:**
```python
# Source: src/docsift/cli/formatters.py
class OutputFormatter:
    FORMATS = ["table", "json", "csv", "md", "xml", "files"]
    def print(self, data: Any, title: Optional[str] = None) -> None:
        if self.format_type == "json":
            print_json(data, self.console)
        elif self.format_type == "table":
            print_table(data, title, self.console)
        ...
```

### Anti-Patterns to Avoid
- **Creating a new `collection ls` for indexed documents:** D-02 explicitly requires a *top-level* `docsift ls` command. The existing `collection ls` scans the filesystem, not the database.
- **Silently ignoring `search_all`:** The current `search.py` accepts `--all` but never uses it. This must be wired to bypass the `include_by_default` filter.
- **Adding `pre_update_cmd` without schema migration:** SQLite `CREATE TABLE IF NOT EXISTS` will not add the column to existing databases. Use `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` for idempotent migration.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GGUF download from HuggingFace | Custom HTTP client | `huggingface_hub.hf_hub_download` | Resume, cache, etag, token support |
| Console tables/trees | String formatting | `rich.table.Table`, `rich.tree.Tree` | Already in codebase, handles wrapping/colors |
| Glob matching | Custom pattern parser | `fnmatch.fnmatch` | Standard library, used elsewhere in project |
| SQLite schema migration | Drop/recreate tables | `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` | Preserves user data |
| Subprocess execution | `os.system` | `subprocess.run(..., shell=True, capture_output=True, text=True)` | Safe exit-code capture, no shell injection via user strings if validated |

**Key insight:** The project already uses `rich`, `fnmatch`, and `huggingface_hub` (via `SentenceTransformerEmbedder`). Extending these is cheaper and more consistent than introducing new libraries.

## Common Pitfalls

### Pitfall 1: `multi-get` Auto-Detection Ambiguity
**What goes wrong:** An argument like `a?,b` contains both a comma and a glob wildcard, making it simultaneously a list and a glob pattern.
**Why it happens:** D-01 says "if contains commas -> split into list; if contains glob wildcards -> treat as glob; otherwise -> single docid." The priority order is undefined.
**How to avoid:** Define priority: comma detection takes precedence over glob detection. `a?,b` splits into `["a?", "b"]` and each item is treated as a single docid/path.
**Warning signs:** Test cases with overlapping patterns fail unpredictably.

### Pitfall 2: `--all` Flag Is Currently a No-Op
**What goes wrong:** `search.py` defines `@click.option("--all", "search_all", is_flag=True, help="Search all collections")` on both `search` and `query`, but `search_all` is never referenced in the function body [VERIFIED: grep of `src/docsift/cli/commands/search.py`].
**Why it happens:** The flag was stubbed but not implemented.
**How to avoid:** Wire `search_all` into collection resolution logic. When `search_all=False` and no `--collection` is given, resolve `collection_ids` to only enabled collections via a new `CollectionRepository.list_enabled()` method.
**Warning signs:** `docsift search foo` returns results from excluded collections.

### Pitfall 3: Existing CLI Unit Tests Reference Non-Existent Commands
**What goes wrong:** `tests/unit/cli/test_collection_commands.py` imports `collection_create`, `collection_delete`, `collection_add_path`, `collection_remove_path`, but the real commands are `collection_add`, `collection_remove`, etc. Similar mismatches exist in `test_index_commands.py` and `test_search_commands.py` [VERIFIED: file reads].
**Why it happens:** Tests were written as stubs against a different CLI design.
**How to avoid:** Do not assume existing CLI tests pass. The planner should include a task to fix or replace stub tests before adding new ones.
**Warning signs:** `pytest tests/unit/cli/` fails on import.

### Pitfall 4: `sqlite_vec` and `python-frontmatter` Missing in Current Environment
**What goes wrong:** The current Python environment cannot import `sqlite_vec` or `frontmatter`, so `pytest` and `python -m docsift.cli.main` fail immediately.
**Why it happens:** Dependencies are declared in `pyproject.toml` but not installed in the active venv [VERIFIED: `python -c "import sqlite_vec"` fails; `pyproject.toml` lists them].
**How to avoid:** Any plan that runs tests must first ensure `pip install -e ".[dev]"` succeeds, or tests must be run in an environment where dependencies are present.
**Warning signs:** `ModuleNotFoundError` on every test run.

### Pitfall 5: `get` Already Has `--from-line` and `--lines`
**What goes wrong:** `--line-numbers` could be confused with the existing line-filtering options.
**Why it happens:** Both concepts involve "lines."
**How to avoid:** `--line-numbers` is a display flag (prepends `N: ` to each line) and does NOT filter content. Keep it separate from `--from-line` and `--lines`.
**Warning signs:** Users report that `--line-numbers` truncates output.

## Code Examples

### Safe Schema Migration for `pre_update_cmd`
```python
# Source: pattern derived from src/docsift/database/schema.py
class SchemaManager:
    def _create_collections_table(self) -> None:
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                ...
            )
        """)
        self._add_column_if_missing("collections", "pre_update_cmd", "TEXT")

    def _add_column_if_missing(self, table: str, column: str, dtype: str) -> None:
        cursor = self.db.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if column not in columns:
            self.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {dtype}")
```

### `multi-get` Auto-Detection
```python
# Source: derived from src/docsift/cli/commands/get.py + D-01
import fnmatch

def resolve_multi_get(pattern: str, doc_repo, coll_repo):
    if "," in pattern:
        ids = [p.strip() for p in pattern.split(",") if p.strip()]
        return [doc_repo.get_by_id(i) or doc_repo.get_by_path(i, ...) for i in ids]
    elif "*" in pattern or "?" in pattern:
        matched = []
        for coll in coll_repo.list_all():
            for doc in doc_repo.list_by_collection(coll.id):
                if fnmatch.fnmatch(doc.path, pattern) or fnmatch.fnmatch(doc.filename, pattern):
                    matched.append(doc)
        return matched
    else:
        # single docid or path
        doc = doc_repo.get_by_id(pattern)
        return [doc] if doc else []
```

### Building a Virtual File Tree with `rich.tree.Tree`
```python
# Source: derived from src/docsift/cli/commands/collection.py (collection_ls)
from rich.tree import Tree

tree = Tree(f"[bold cyan]{collection.name}[/bold cyan]")
for doc in sorted(docs, key=lambda d: d.path):
    parts = doc.path.strip("/").split("/")
    node = tree
    for part in parts[:-1]:
        found = next((c for c in node.children if str(c.label) == part), None)
        node = found if found else node.add(part)
    node.add(parts[-1])
console.print(tree)
```

### `pull` with HuggingFace Primary + ModelScope Fallback
```python
# Source: derived from src/docsift/models/download.py + huggingface_hub docs
from pathlib import Path
from huggingface_hub import hf_hub_download

def pull_gguf(model_id: str, filename: str, cache_dir: Path) -> Path:
    try:
        path = hf_hub_download(repo_id=model_id, filename=filename, cache_dir=str(cache_dir))
        return Path(path)
    except Exception as e:
        logger.warning(f"HuggingFace failed: {e}")
        # fallback to modelscope if available
        try:
            from modelscope import snapshot_download
            model_path = snapshot_download(model_id, cache_dir=str(cache_dir))
            return Path(model_path) / filename
        except ImportError:
            raise click.ClickException("ModelScope not installed and HuggingFace failed.")
```

### Default-Search Collection Filtering
```python
# Source: derived from src/docsift/database/repositories.py
class CollectionRepository:
    def list_enabled(self) -> List[Collection]:
        cursor = self.db.execute(
            "SELECT * FROM collections WHERE include_by_default = 1 ORDER BY name"
        )
        return [self._row_to_collection(row) for row in cursor.fetchall()]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `collection create/delete/add-path/remove-path` (stub design) | `collection add/remove/ls` (implemented) | Pre-Phase 2 | Tests and docs reference the old stub names |
| `search query` as subcommand | `query` as top-level group command | Pre-Phase 2 | E2E tests use wrong command path |
| `--all` no-op | `--all` wired to bypass `include_by_default` filter | Phase 2 | Fixes semantic gap in search CLI |

**Deprecated/outdated:**
- `sqlite_repository.py`: Removed in Phase 1 (D-02). All DB access goes through `repositories.py`.
- Vector search Python fallback: Removed in Phase 1 (D-03). `VectorSearcher` now fails fast with `RuntimeError`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `modelscope` can be used as a fallback for GGUF downloads with `snapshot_download` | Standard Stack / pull Command | If ModelScope does not host the requested GGUF, fallback fails; user must provide direct URL |
| A2 | `search_all=False` (no `--all` flag) should restrict default queries to `include_by_default=True` collections | Architecture Patterns | If user expects all collections to be searched by default, this changes behavior; D-07/D-08 imply this is the intended semantics |
| A3 | `pre_update_cmd` should be executed with `shell=True` so users can use pipes, redirects, and shell builtins | Code Examples | If security is a concern, `shell=False` with `shlex.split` is safer but breaks complex commands like `rsync -a remote:notes/ local/notes/` |

## Open Questions (RESOLVED)

1. **RESOLVED: Should `pull` accept full URLs or only `owner/repo/filename.gguf` identifiers?**
   - Decision: Support `owner/repo/filename.gguf` as the primary interface. If the argument starts with `http://` or `https://`, fall back to `urllib` direct download.

2. **RESOLVED: What should happen to `search_all` in `vsearch`?**
   - Decision: For consistency, `vsearch` gains `--all` and respects `include_by_default` when no `--collection` is given.

3. **RESOLVED: How should line numbers be formatted in table output?**
   - Decision: Use `f"{i+1:4d}: {line}"` for readability. This is within Claude's discretion per CONTEXT.md.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.12 | — |
| Click | CLI framework | ✓ | 8.3.2 | — |
| rich | Console output | ✓ | 13.x+ | — |
| huggingface_hub | `pull` command | ✓ | 1.3.2 | — |
| sqlite-vec | Database/vector search | ✗ | — | Install from `pyproject.toml` |
| python-frontmatter | Markdown parser | ✗ | — | Install from `pyproject.toml` |
| modelscope | `pull` fallback | ✗ | — | Skip fallback, warn user |
| pytest | Test runner | ✓ | 9.0.2 | — |

**Missing dependencies with no fallback:**
- `sqlite-vec` and `python-frontmatter` block running the full test suite in the current environment. They are declared in `pyproject.toml` and must be installed before `pytest` or `python -m docsift` will work.

**Missing dependencies with fallback:**
- `modelscope` is optional. If not installed, `pull` should attempt HuggingFace and fail with a clear message if that also fails.

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json`.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (pytest settings inferred) |
| Quick run command | `pytest tests/unit/cli/test_commands.py -x` (to be created) |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-01 | `multi-get` splits comma args, matches globs, retrieves single doc | unit | `pytest tests/unit/cli/test_commands.py::test_multi_get -x` | ❌ Wave 0 |
| CLI-02 | `ls` renders indexed docs as virtual tree | unit | `pytest tests/unit/cli/test_commands.py::test_ls_tree -x` | ❌ Wave 0 |
| CLI-03 | `collection update-cmd` stores and clears shell command | unit | `pytest tests/unit/cli/test_commands.py::test_collection_update_cmd -x` | ❌ Wave 0 |
| CLI-03 | `index update` runs `pre_update_cmd` and fails fast on error | integration | `pytest tests/integration/test_index_update_hook.py -x` | ❌ Wave 0 |
| CLI-04 | `collection include/exclude` toggles `include_by_default` | unit | `pytest tests/unit/cli/test_commands.py::test_collection_include_exclude -x` | ❌ Wave 0 |
| CLI-04 | Default search excludes disabled collections unless `--all` | unit | `pytest tests/unit/cli/test_commands.py::test_search_respects_include_by_default -x` | ❌ Wave 0 |
| CLI-05 | `pull` downloads and verifies GGUF file | unit (mocked network) | `pytest tests/unit/cli/test_commands.py::test_pull_download -x` | ❌ Wave 0 |
| CLI-08 | `--line-numbers` appears on `get`, `multi-get`, `search`, `query`, `vsearch` | unit | `pytest tests/unit/cli/test_commands.py::test_line_numbers_flag -x` | ❌ Wave 0 |
| CLI-08 | `--line-numbers` prepends line numbers in all output formats | unit | `pytest tests/unit/cli/test_commands.py::test_line_numbers_output -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/cli/test_commands.py -x`
- **Per wave merge:** `pytest tests/unit/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/cli/test_commands.py` — comprehensive CLI command tests (replaces stub tests)
- [ ] `tests/integration/test_index_update_hook.py` — integration test for `pre_update_cmd` execution
- [ ] Dependency install: `pip install -e ".[dev]"` — required before any pytest run

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | Click validates types and choices; no additional library needed |
| V6 Cryptography | no | No custom crypto in this phase |
| V12 File Upload | yes (model download) | `huggingface_hub` handles HTTPS/TLS; verify file size and non-empty after download (D-11) |

### Known Threat Patterns for Click + subprocess

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Command injection via `pre_update_cmd` | Tampering/Elevation | `subprocess.run(cmd, shell=True, ...)` — document that this runs with user's privileges; do not accept commands from untrusted sources |
| Path traversal via `pull` cache dir | Tampering | Use `Path(cache_dir).expanduser().resolve()` and validate parent directory |
| Unverified download (MITM) | Spoofing | `huggingface_hub` uses HTTPS and etag validation by default |

## Sources

### Primary (HIGH confidence)
- Codebase files: `src/docsift/cli/commands/*.py`, `src/docsift/cli/formatters.py`, `src/docsift/core/models.py`, `src/docsift/database/repositories.py`, `src/docsift/database/schema.py`, `src/docsift/models/download.py`
- `huggingface_hub` API: `python -c "from huggingface_hub import hf_hub_download; import inspect; print(inspect.signature(hf_hub_download))"`
- Click version: `python -c "import click; print(click.__version__)"`

### Secondary (MEDIUM confidence)
- `pyproject.toml` dependency declarations
- `02-CONTEXT.md` user decisions (D-01 through D-13)

### Tertiary (LOW confidence)
- ModelScope fallback behavior: `modelscope` is not installed in the current environment; fallback logic is based on the existing `ModelDownloader` class and general knowledge of the ModelScope API.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified versions and existing usage
- Architecture: HIGH — derived directly from existing code patterns
- Pitfalls: HIGH — verified by reading actual source and running quick checks

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable stack)
