# Phase 02: CLI Core Completion - Pattern Map

**Mapped:** 2026-04-15
**Files analyzed:** 12
**Analogs found:** 12 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/docsift/cli/commands/get.py` | controller | request-response | `src/docsift/cli/commands/get.py` (existing) | exact |
| `src/docsift/cli/commands/collection.py` | controller | request-response | `src/docsift/cli/commands/collection.py` (existing enable/disable) | exact |
| `src/docsift/cli/commands/search.py` | controller | request-response | `src/docsift/cli/commands/search.py` (existing) | exact |
| `src/docsift/cli/commands/index.py` | controller | request-response + subprocess | `src/docsift/cli/commands/index.py` (existing update) | exact |
| `src/docsift/cli/formatters.py` | utility | transform | `src/docsift/cli/formatters.py` (existing OutputFormatter) | exact |
| `src/docsift/cli/main.py` | controller | request-response | `src/docsift/cli/main.py` (existing status/cleanup) | exact |
| `src/docsift/cli/commands/ls.py` (new inline or module) | controller | request-response | `src/docsift/cli/commands/collection.py` `collection_ls` | role-match |
| `src/docsift/cli/commands/pull.py` (new inline or module) | controller | request-response + file-I/O | `src/docsift/cli/commands/index.py` `embed_cmd` (external lib + progress) | role-match |
| `src/docsift/core/models.py` | model | transform | `src/docsift/core/models.py` `Collection` | exact |
| `src/docsift/database/schema.py` | config/migration | transform | `src/docsift/database/schema.py` `SchemaManager` | exact |
| `src/docsift/database/repositories.py` | service | CRUD | `src/docsift/database/repositories.py` `CollectionRepository` | exact |
| `src/docsift/models/download.py` | utility | file-I/O | `src/docsift/models/download.py` `ModelDownloader` | exact |

## Pattern Assignments

### `src/docsift/cli/commands/get.py` (controller, request-response)

**Analog:** `src/docsift/cli/commands/get.py` lines 24-104 (existing `get_cmd`)

**Imports pattern** (lines 1-14):
```python
"""Document retrieval commands."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.syntax import Syntax

from docsift.database.database import Database
from docsift.database.repositories import DocumentRepository

console = Console()
```

**Core pattern: command definition + db access** (lines 24-46):
```python
@get_group.command("get")
@click.argument("path_or_docid")
@click.option("--from-line", "-f", type=int, help="Start from line number")
@click.option("--lines", "-l", type=int, help="Number of lines to show")
@click.pass_context
def get_cmd(...) -> None:
    index_path = ctx.obj["index_path"]
    
    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return
    
    db = Database(index_path)
    db.init_schema()
    
    with db.connection:
        doc_repo = DocumentRepository(db.connection)
        # ... repository usage ...
```

**Error handling pattern** (lines 62-74):
```python
        if not doc:
            # Try as file path
            path = Path(path_or_docid)
            if path.exists():
                try:
                    content = path.read_text()
                    console.print(f"[bold]{path}[/bold]")
                    console.print(content)
                    return
                except Exception as e:
                    raise click.ClickException(f"Cannot read file: {e}")
            
            raise click.ClickException(f"Document not found: {path_or_docid}")
```

**Line-filtering pattern** (lines 86-98):
```python
        # Apply line filtering
        if from_line is not None or lines is not None:
            content_lines = content.split("\n")
            
            start = (from_line or 1) - 1  # Convert to 0-indexed
            start = max(0, start)
            
            if lines is not None:
                end = start + lines
                content_lines = content_lines[start:end]
            else:
                content_lines = content_lines[start:]
            
            content = "\n".join(content_lines)
```

**Stub multi-get pattern to extend** (lines 107-157):
```python
@get_group.command("multi-get")
@click.argument("pattern")
@click.option("--max-bytes", "-b", type=int, default=100000, help="Max bytes per file")
@click.pass_context
def multi_get_cmd(...) -> None:
    ...
    import fnmatch
    ...
    for coll in coll_repo.list_all():
        for doc in doc_repo.list_by_collection(coll.id):
            if fnmatch.fnmatch(doc.path, pattern) or fnmatch.fnmatch(doc.filename, pattern):
                matched_docs.append(doc)
```

---

### `src/docsift/cli/commands/collection.py` (controller, request-response)

**Analog:** `src/docsift/cli/commands/collection.py` lines 211-254 (`collection_enable` / `collection_disable`)

**Imports pattern** (lines 1-17):
```python
"""Collection management commands."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from docsift.core.models import Collection
from docsift.database.database import Database
from docsift.database.repositories import CollectionRepository
from docsift.indexing.scanner import FileScanner

console = Console()
```

**Core pattern: toggle boolean via transaction** (lines 211-231):
```python
@collection_group.command("enable")
@click.argument("name")
@click.pass_context
def collection_enable(ctx: click.Context, name: str) -> None:
    """Enable a collection for default searches."""
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
    
    console.print(f"[green]Collection '{name}' enabled[/green]")
```

**Tree rendering pattern** (lines 257-295, `collection_ls`):
```python
        # Build tree
        tree = Tree(f"[bold cyan]{collection.name}[/bold cyan]")
        
        for file_path in sorted(scan_result.files):
            rel_path = file_path.relative_to(collection.path)
            tree.add(str(rel_path))
        
        console.print(tree)
```

---

### `src/docsift/cli/commands/search.py` (controller, request-response)

**Analog:** `src/docsift/cli/commands/search.py` lines 67-166 (`search_cmd`)

**Imports pattern** (lines 1-15):
```python
"""Search commands."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from docsift.core.models import SearchOptions
from docsift.database.database import Database
from docsift.search.bm25 import BM25Searcher
from docsift.search.hybrid import HybridSearcher

console = Console()
```

**Core pattern: resolve collections + search + output** (lines 96-166):
```python
    db = Database(index_path)
    db.init_schema()

    options = SearchOptions(
        limit=limit,
        min_score=min_score,
        include_content=full,
        include_highlights=True,
    )

    if collection:
        with db.connection:
            from docsift.database.repositories import CollectionRepository
            repo = CollectionRepository(db.connection)
            options.collection_ids = []
            for name in collection:
                coll = repo.get_by_name(name)
                if coll:
                    options.collection_ids.append(coll.id)

    with db.connection:
        searcher = BM25Searcher(db.connection)
        results = searcher.search(query, options)

    # Output results
    if output_files:
        for r in results:
            console.print(r.path)
    elif output_json:
        console.print(format_results_json(results))
    ...
```

**Rich table output pattern** (lines 148-161):
```python
        table = Table(title=f'Search Results: "{query}"')
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Score", style="green", justify="right")
        table.add_column("Title", style="yellow")
        table.add_column("Collection", style="blue")

        for r in results:
            table.add_row(
                str(r.rank),
                f"{r.score:.4f}",
                r.title[:50] + "..." if len(r.title) > 50 else r.title,
                r.collection_name,
            )

        console.print(table)
```

**Anti-pattern to fix:** `--all` flag is defined but never used (lines 71, 86). Wire `search_all` into collection resolution.

---

### `src/docsift/cli/commands/index.py` (controller, request-response + subprocess)

**Analog:** `src/docsift/cli/commands/index.py` lines 31-150 (`update_cmd`)

**Imports pattern** (lines 1-22):
```python
"""Index management commands."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from docsift.core.models import Document
from docsift.database.database import Database
from docsift.database.repositories import (
    CollectionRepository,
    DocumentChunkRepository,
    DocumentRepository,
)
from docsift.indexing.chunker import create_chunker
from docsift.indexing.parser import MarkdownParser
from docsift.indexing.scanner import FileScanner

console = Console()
```

**Core pattern: iterate collections, scan, parse, update** (lines 62-145):
```python
        for coll in collections:
            if not coll:
                continue
            
            console.print(f"\n[bold]Updating collection: {coll.name}[/bold]")
            
            scanner = FileScanner()
            scan_result = scanner.scan(
                Path(coll.path),
                pattern=coll.pattern,
                ignore_patterns=coll.ignore_patterns,
            )
            
            # Get existing documents
            existing_docs = {d.path: d for d in doc_repo.list_by_collection(coll.id)}
            scanned_paths = set()
            
            parser = MarkdownParser()
            
            with Progress(...) as progress:
                task = progress.add_task(f"Indexing {coll.name}...", total=scan_result.file_count)
                
                for file_path in scan_result.files:
                    ...
```

**Subprocess execution pattern** (to add for `pre_update_cmd`):
```python
import subprocess

result = subprocess.run(
    cmd,
    shell=True,
    capture_output=True,
    text=True,
)
if result.returncode != 0:
    raise click.ClickException(
        f"Pre-update command failed for '{coll.name}' (exit {result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
    )
```

---

### `src/docsift/cli/formatters.py` (utility, transform)

**Analog:** `src/docsift/cli/formatters.py` lines 206-245 (`OutputFormatter`)

**Core pattern: format dispatch** (lines 206-240):
```python
class OutputFormatter:
    """Handles output formatting based on format option."""
    
    FORMATS = ["table", "json", "csv", "md", "xml", "files"]
    
    def __init__(self, format_type: str = "table", console: Optional[Console] = None):
        self.format_type = format_type
        self.console = console or Console()
    
    def print(self, data: Any, title: Optional[str] = None) -> None:
        """Print data in the specified format."""
        if self.format_type == "json":
            print_json(data, self.console)
        elif self.format_type == "csv":
            if isinstance(data, list) and data and isinstance(data[0], dict):
                print_csv(data, self.console)
            else:
                print_json(data, self.console)
        elif self.format_type == "md":
            if isinstance(data, list) and data and isinstance(data[0], dict):
                print_markdown(data, title, self.console)
            else:
                print_json(data, self.console)
        elif self.format_type == "xml":
            print_xml(data, title or "root", self.console)
        elif self.format_type == "files":
            if isinstance(data, list):
                print_files(data, self.console)
            else:
                print_json(data, self.console)
        else:  # table
            if isinstance(data, list) and data and isinstance(data[0], dict):
                print_table(data, title, self.console)
            else:
                print_json(data, self.console)
```

**Line-number formatting pattern to add:**
```python
def prepend_line_numbers(content: str) -> str:
    return "\n".join(
        f"{i + 1:4d}: {line}" for i, line in enumerate(content.split("\n"))
    )
```

---

### `src/docsift/cli/main.py` (controller, request-response)

**Analog:** `src/docsift/cli/main.py` lines 69-82 and 85-119

**Command registration pattern** (lines 69-82):
```python
# Import and register subcommands
from docsift.cli.commands.collection import collection_group
from docsift.cli.commands.context import context_group
from docsift.cli.commands.index import index_group
from docsift.cli.commands.search import search_group
from docsift.cli.commands.get import get_group
from docsift.cli.commands.mcp import mcp_group

cli.add_command(collection_group)
cli.add_command(context_group)
cli.add_command(index_group)
cli.add_command(search_group)
cli.add_command(get_group)
cli.add_command(mcp_group)
```

**Top-level command pattern** (lines 85-119, `status_cmd`):
```python
@cli.command("status")
@click.pass_context
def status_cmd(ctx: click.Context) -> None:
    """Show index status."""
    index_path = ctx.obj["index_path"]
    
    if not index_path.exists():
        console.print("[yellow]No index found. Run 'docsift update' to create one.[/yellow]")
        return
    
    try:
        db = Database(index_path)
        db.init_schema()
        stats = db.get_stats()
        ...
    except Exception as e:
        console.print(f"[red]Error reading index: {e}[/red]")
        raise click.ClickException(str(e))
```

---

### `src/docsift/cli/commands/ls.py` (or inline in main.py) (controller, request-response)

**Analog:** `src/docsift/cli/commands/collection.py` lines 257-295 (`collection_ls`)

**Core pattern: build virtual tree from documents** (derived from `collection_ls`):
```python
from rich.tree import Tree

@cli.command("ls")
@click.argument("collection", required=False)
@click.argument("subpath", required=False)
@click.pass_context
def ls_cmd(ctx: click.Context, collection: str | None, subpath: str | None) -> None:
    index_path = ctx.obj["index_path"]
    
    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return
    
    db = Database(index_path)
    db.init_schema()
    
    with db.connection:
        doc_repo = DocumentRepository(db.connection)
        coll_repo = CollectionRepository(db.connection)
        
        if collection:
            collections = [coll_repo.get_by_name(collection)]
            if not collections[0]:
                raise click.ClickException(f"Collection '{collection}' not found")
        else:
            collections = coll_repo.list_all()
        
        for coll in collections:
            if not coll:
                continue
            docs = doc_repo.list_by_collection(coll.id)
            tree = Tree(f"[bold cyan]{coll.name}[/bold cyan]")
            for doc in sorted(docs, key=lambda d: d.path):
                parts = doc.path.strip("/").split("/")
                node = tree
                for part in parts[:-1]:
                    found = next((c for c in node.children if str(c.label) == part), None)
                    node = found if found else node.add(part)
                node.add(parts[-1])
            console.print(tree)
```

---

### `src/docsift/cli/commands/pull.py` (or inline in main.py) (controller, request-response + file-I/O)

**Analog:** `src/docsift/cli/commands/index.py` lines 153-275 (`embed_cmd` — external library loading + progress) and `src/docsift/models/download.py`

**Core pattern: external library with graceful fallback** (from `embed_cmd` lines 173-194):
```python
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        console.print("[red]sentence-transformers not installed.[/red]")
        return
    
    try:
        embedder = SentenceTransformer(model_name)
    except Exception as e:
        console.print(f"[red]Failed to load embedding model: {e}[/red]")
        return
```

**Download pattern from `models/download.py`** (lines 44-94):
```python
    def download(self, model_id: str, revision: Optional[str] = None, force: bool = False) -> Path:
        try:
            from modelscope import snapshot_download
        except ImportError:
            logger.error("modelscope not installed. Install with: pip install modelscope")
            raise
        
        model_hash = hashlib.md5(model_id.encode()).hexdigest()[:8]
        model_cache_dir = self.cache_dir / model_hash
        
        if not force and model_cache_dir.exists():
            if any(model_cache_dir.iterdir()):
                return model_cache_dir
        
        download_kwargs = {"model_id": model_id, "cache_dir": str(self.cache_dir)}
        if revision:
            download_kwargs["revision"] = revision
        
        model_path = snapshot_download(**download_kwargs)
        return Path(model_path)
```

**Pull command structure to implement**:
```python
@cli.command("pull")
@click.argument("model_spec")
@click.option("--cache-dir", type=click.Path(), help="Custom cache directory")
@click.pass_context
def pull_cmd(ctx: click.Context, model_spec: str, cache_dir: str | None) -> None:
    from pathlib import Path
    from huggingface_hub import hf_hub_download
    
    target_cache = Path(cache_dir).expanduser().resolve() if cache_dir else Path.home() / ".docsift" / "models"
    target_cache.mkdir(parents=True, exist_ok=True)
    
    # Parse owner/repo/filename.gguf
    parts = model_spec.split("/")
    if len(parts) >= 3:
        repo_id = "/".join(parts[:-1])
        filename = parts[-1]
    else:
        raise click.ClickException("Model spec must be owner/repo/filename.gguf")
    
    try:
        path = hf_hub_download(repo_id=repo_id, filename=filename, cache_dir=str(target_cache))
        downloaded = Path(path)
    except Exception as hf_err:
        # ModelScope fallback
        try:
            from modelscope import snapshot_download
            model_path = snapshot_download(repo_id, cache_dir=str(target_cache))
            downloaded = Path(model_path) / filename
        except ImportError:
            raise click.ClickException(f"HuggingFace failed: {hf_err}. ModelScope not installed.")
        except Exception as ms_err:
            raise click.ClickException(f"Download failed: HF={hf_err}, MS={ms_err}")
    
    if not downloaded.exists() or downloaded.stat().st_size == 0:
        raise click.ClickException("Downloaded file is missing or empty.")
    
    console.print(f"[green]Downloaded to {downloaded}[/green]")
```

---

### `src/docsift/core/models.py` (model, transform)

**Analog:** `src/docsift/core/models.py` lines 29-78 (`Collection`)

**Dataclass pattern with to_dict/from_dict** (lines 29-78):
```python
@dataclass
class Collection:
    """A document collection."""
    name: str
    path: str
    pattern: str = "**/*.md"
    ignore_patterns: List[str] = field(default_factory=list)
    include_by_default: bool = True
    description: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    document_count: int = 0
    chunk_count: int = 0
    last_indexed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            ...
            "last_indexed_at": self.last_indexed_at.isoformat() if self.last_indexed_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Collection:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            ...
        )
```

**Addition:** Insert `pre_update_cmd: Optional[str] = None` after `description` and include it in `to_dict` / `from_dict`.

---

### `src/docsift/database/schema.py` (config/migration, transform)

**Analog:** `src/docsift/database/schema.py` lines 9-43 (`SchemaManager._create_collections_table`)

**Schema creation pattern** (lines 26-43):
```python
    def _create_collections_table(self) -> None:
        """Create collections table."""
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

**Safe migration pattern to add** (derived from RESEARCH.md):
```python
    def _add_column_if_missing(self, table: str, column: str, dtype: str) -> None:
        cursor = self.db.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if column not in columns:
            self.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {dtype}")

    def _create_collections_table(self) -> None:
        ...  # existing CREATE TABLE
        self._add_column_if_missing("collections", "pre_update_cmd", "TEXT")
```

---

### `src/docsift/database/repositories.py` (service, CRUD)

**Analog:** `src/docsift/database/repositories.py` lines 19-129 (`CollectionRepository`)

**CRUD pattern** (lines 25-71):
```python
class CollectionRepository:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
    
    def create(self, collection: Collection) -> Collection:
        self.db.execute("""
            INSERT INTO collections (
                id, name, path, pattern, ignore_patterns, include_by_default,
                description, created_at, updated_at, document_count, chunk_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (...))
        return collection
    
    def list_all(self) -> List[Collection]:
        cursor = self.db.execute("SELECT * FROM collections ORDER BY name")
        return [self._row_to_collection(row) for row in cursor.fetchall()]
```

**Update pattern** (lines 73-98):
```python
    def update(self, collection: Collection) -> Collection:
        collection.updated_at = datetime.utcnow()
        self.db.execute("""
            UPDATE collections SET
                name = ?, path = ?, pattern = ?, ignore_patterns = ?,
                include_by_default = ?, description = ?, updated_at = ?,
                document_count = ?, chunk_count = ?, last_indexed_at = ?
            WHERE id = ?
        """, (...))
        return collection
```

**Row conversion pattern** (lines 116-129):
```python
    def _row_to_collection(self, row: sqlite3.Row) -> Collection:
        return Collection(
            id=row["id"],
            name=row["name"],
            path=row["path"],
            pattern=row["pattern"],
            ignore_patterns=json.loads(row["ignore_patterns"]),
            include_by_default=bool(row["include_by_default"]),
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_indexed_at=datetime.fromisoformat(row["last_indexed_at"]) if row["last_indexed_at"] else None,
        )
```

**New method to add** (`list_enabled`):
```python
    def list_enabled(self) -> List[Collection]:
        cursor = self.db.execute(
            "SELECT * FROM collections WHERE include_by_default = 1 ORDER BY name"
        )
        return [self._row_to_collection(row) for row in cursor.fetchall()]
```

**Note:** `create`, `update`, and `_row_to_collection` must include `pre_update_cmd` field.

---

## Shared Patterns

### Authentication
Not applicable — no auth in this CLI tool.

### Error Handling
**Source:** `src/docsift/cli/commands/collection.py` lines 83-88
**Apply to:** All controller files
```python
    with db.transaction() as conn:
        repo = CollectionRepository(conn)
        collection = repo.get_by_name(name)
        if not collection:
            raise click.ClickException(f"Collection '{name}' not found")
```

### Database Access
**Source:** `src/docsift/database/database.py` lines 60-74
**Apply to:** All CLI commands that touch the database
```python
    db = Database(index_path)
    db.init_schema()
    
    with db.transaction() as conn:
        # mutations
    
    with db.connection:
        # reads
```

### Output Formatting
**Source:** `src/docsift/cli/formatters.py` lines 206-240
**Apply to:** `get`, `multi-get`, `search`, `query`, `vsearch`, `ls`
Use `OutputFormatter` or its helper functions. For `--line-numbers`, preprocess `content` before passing to formatter or directly to `console.print`.

### Click Option Conventions
**Source:** `src/docsift/cli/commands/search.py` lines 67-79
**Apply to:** Search/get commands needing structured output
```python
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--csv", "output_csv", is_flag=True, help="Output as CSV")
@click.option("--md", "output_md", is_flag=True, help="Output as Markdown")
@click.option("--xml", "output_xml", is_flag=True, help="Output as XML")
@click.option("--files", "output_files", is_flag=True, help="Output file paths only")
```

### Test Patterns
**Source:** `tests/unit/cli/test_collection_commands.py` (stub tests with wrong imports)
**Apply to:** New tests should use `CliRunner` from `click.testing` and mock repositories where possible.

**Anti-pattern to avoid:** Existing stub tests import non-existent commands like `collection_create`, `collection_delete`, `index_add`, `search_query`. New tests should reference actual command names (`collection_add`, `collection_remove`, `search_cmd`, `query_cmd`, etc.).

## No Analog Found

None — all files have close matches in the codebase.

## Metadata

**Analog search scope:** `src/docsift/cli/commands/`, `src/docsift/cli/`, `src/docsift/core/`, `src/docsift/database/`, `src/docsift/models/`, `tests/unit/cli/`
**Files scanned:** 20+
**Pattern extraction date:** 2026-04-15
