# Coding Conventions

**Analysis Date:** 2026-04-14

## Naming Patterns

**Files:**
- Modules use `snake_case`: `chunker.py`, `test_repositories.py`
- Test files prefixed with `test_`: `test_bm25.py`, `test_chunker.py`
- `__init__.py` for package initialization

**Functions/Methods:**
- Use `snake_case` for all functions and methods
- Private helpers use leading underscore: `_create_collections_table()`
- CLI commands use descriptive names: `search_cmd`, `query_cmd`

**Variables:**
- `snake_case` throughout
- Type variables use single uppercase: `T = TypeVar("T")`
- Private instance variables use leading underscore: `self._collections`

**Classes:**
- `PascalCase` for all classes
- Abstract base classes often include `ABC` or are named descriptively: `Repository`, `SearchStrategy`
- Test classes prefixed with `Test`: `TestBM25SearchStrategy`

**Types:**
- Union syntax uses `|` (Python 3.9+): `str | None`, `list[str] | None`
- `Optional[T]` also appears in older code: `Optional[str]`
- Prefer `list[str]` over `List[str]` in newer modules

## Code Style

**Formatting:**
- **Black** with `line-length = 100`
- Target Python 3.9+
- Double quotes for strings, including docstrings

**Linting:**
- **Ruff** with extensive rule set (E, F, W, I, N, D, UP, B, C4, SIM, C90, A, COM, T20, PT, Q, SLF, RET, TID, ARG, FIX, ERA, PL, PERF, RUF)
- Max complexity (mccabe): 10
- Per-file ignores:
  - `tests/**/*` ignores docstring rules (`D`), asserts (`S101`), magic values (`PLR2004`)
  - `src/docsift/cli/*.py` allows print statements (`T20`)
  - `__init__.py` ignores missing package docstrings (`D104`)

**Import Organization:**
- Ruff isort with `combine-as-imports = true`
- Order: stdlib, third-party, first-party (`docsift`)
- Two blank lines after imports

## Docstrings

**Convention:** Google-style docstrings enforced by Ruff (`convention = "google"`)

**Patterns:**
```python
def chunk(self, text: str) -> List[DocumentChunk]:
    """Split text into chunks.
    
    Args:
        text: Text to chunk
        
    Returns:
        List of chunks
    """
    pass
```

**Exceptions:**
- Public modules and packages are NOT required to have docstrings (`D100`, `D104` ignored)
- Imperative mood in first line is NOT enforced (`D401` ignored)
- Docstring section formatting is relaxed (`D406`, `D407`, `D413` ignored)

## Type Annotations

**Strict typing enforced by mypy:**
- `disallow_untyped_defs = true`
- `disallow_incomplete_defs = true`
- `check_untyped_defs = true`
- `strict = true`

**Exceptions:**
- CLI modules (`src/docsift/cli.*`) relax `disallow_untyped_decorators` for Click decorators
- Third-party libraries without stubs are ignored: `click`, `rich`, `sentence_transformers`, `numpy`, `pytest`

## Error Handling

**Patterns:**
- Use exceptions for error flow; no heavy use of Result/Either types
- Click exceptions in CLI: `raise click.ClickException(str(e))`
- Graceful degradation with console messages:
  ```python
  if not index_path.exists():
      console.print("[yellow]No index found...[/yellow]")
      return
  ```
- SQLite operational errors caught for optional features (e.g., `sqlite-vec` availability check)

## Logging

**Framework:** Standard library `logging` via custom utilities in `src/docsift/utils/logging.py`

**Patterns:**
- Get module-level logger: `logger = get_logger(__name__)`
- Logger names are prefixed with `docsift`: `docsift.module_name`
- Root logger `docsift` is configured via `setup_logging()`
- Output goes to `stderr` via `StreamHandler`
- Simple format for INFO/WARNING; detailed format for DEBUG/ERROR

## Import Style

**Absolute imports preferred:**
```python
from docsift.core.models import Collection, Document
from docsift.database.connection import DatabaseConnection
```

**`from __future__ import annotations`** appears at the top of most modules for deferred annotation evaluation.

**Path manipulation in tests:**
```python
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

## Function Design

**Size:** No explicit limit, but mccabe complexity capped at 10

**Parameters:**
- Use dataclasses/option objects for complex parameter groups (e.g., `SearchOptions`)
- CLI options map directly to Click decorators

**Return Values:**
- Always annotated
- Collections returned as `list[T]`
- Optional returns as `T | None`

## Module Design

**Exports:**
- `__all__` defined in package `__init__.py` files (e.g., `src/docsift/__init__.py`)

**Barrel Files:**
- Package `__init__.py` re-exports key public types
- No heavy use of `import *`

## CLI Patterns

**Click groups and commands:**
- Subcommands organized in `src/docsift/cli/commands/`
- Commands registered on a group:
  ```python
  @click.group("search")
  def search_group() -> None:
      """Search commands."""
      pass
  ```
- Shared context object stores `index_path`, `config_path`, `verbose`, `quiet`

---

*Convention analysis: 2026-04-14*
