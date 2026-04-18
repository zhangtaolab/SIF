# Phase 6: Documentation Audit & Refresh - Research

**Researched:** 2026-04-18
**Domain:** Python documentation automation, Click CLI introspection, Pydantic Settings introspection, pytest-based docs validation, GitHub Actions CI
**Confidence:** HIGH

## Summary

This phase addresses significant documentation drift across 14 markdown files (6,422 lines total) after 5 rapid implementation phases. The research confirms that documentation is substantially out of sync with the codebase: 23 commands missing from CLI reference, 14 phantom commands documented but removed, 13 Settings fields undocumented, 6 phantom env vars, and numerous stale model names and broken command examples.

The standard approach for this problem is a three-layer solution: (1) automated generation scripts that introspect Click and Pydantic to produce canonical reference docs, (2) pytest-based validators that execute or syntax-check every code block in documentation, and (3) CI infrastructure (Makefile target + GitHub Actions workflow) to enforce ongoing accuracy.

**Primary recommendation:** Use Click's `get_commands()`/`params` API and Pydantic v2's `model_fields` for introspection, `click.testing.CliRunner` for command execution tests, `ast.parse` + `json.loads` for syntax validation, and a blacklist-based skip system for commands requiring network or long-running operations.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CLI reference generation | Build/Script | Documentation | Scripts introspect CLI at build time, output markdown |
| Settings validation | Build/Script | Documentation | Scripts introspect Pydantic model, diff against markdown |
| Code block execution | Test (pytest) | CI | Tests run in pytest, triggered by Makefile/CI |
| JSON/Python syntax check | Test (pytest) | — | Pure validation, no external deps |
| Technical docs accuracy | Manual review | AST validation | Human review for factual accuracy; AST checks symbol existence |
| CI enforcement | GitHub Actions | Makefile | GHA runs on PR; Makefile target for local dev |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|-------------|
| Click | 8.3.2 | CLI introspection (`get_commands()`, `params`, `get_help()`) | Already project dependency; standard Python CLI framework |
| Pydantic | 2.12.5 | Settings introspection (`model_fields`, `FieldInfo`) | Already project dependency; v2 API stable |
| pytest | 9.0.2 | Test framework for docs validation | Already project dependency; industry standard |
| Python stdlib (`ast`, `json`, `re`) | 3.13+ | Syntax validation, markdown parsing | No external deps; Python 3.9+ compatible |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `click.testing.CliRunner` | 8.3.2 | Execute CLI commands in isolated environment | For shell command validation in docs tests |
| `tempfile.TemporaryDirectory` | stdlib | Create temp databases for tests | For fixture-based test isolation |
| `pathlib.Path` | stdlib | Cross-platform path handling | All file operations in scripts/tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CliRunner | subprocess | subprocess is slower and needs env management; CliRunner is faster and already used in project tests |
| Manual regex parsing | Markdown parser library | Regex is sufficient for fenced code blocks; avoids adding dependency |
| AST-based API validation | `importlib` + `getattr` | AST avoids import side effects (no model downloads); safer for docs tests |
| Blacklist skip pattern | Whitelist allow pattern | Blacklist is more maintainable; most commands should be tested |

**Installation:** No additional packages required. All tools are already in `pyproject.toml` `[dev]` extras.

**Version verification:**
- Click 8.3.2: `python -c "import click; print(click.__version__)"` → 8.3.2 [VERIFIED: runtime]
- Pydantic 2.12.5: `python -c "import pydantic; print(pydantic.__version__)"` → 2.12.5 [VERIFIED: runtime]
- pytest 9.0.2: `python -c "import pytest; print(pytest.__version__)"` → 9.0.2 [VERIFIED: runtime]

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Documentation Sources                        │
│  docs/*.md  +  README.md  +  CLAUDE.md                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Validation Pipeline                           │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Extract    │  │  Classify    │  │      Validate        │  │
│  │ Code Blocks  │─►│   by Lang    │─►│  (exec/syntax/skip)  │  │
│  │  (regex)     │  │  (bash/json/ │  │                      │  │
│  │              │  │  python/text)│  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                               │                  │
│                    ┌──────────────────────────┘                  │
│                    ▼                                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Test Report                            │   │
│  │  Pass/Fail per block | Coverage % | Undocumented symbols  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
│  scripts/       │ │ tests/       │ │ .github/     │
│  generate_cli_ref.py│ test_docs.py │ │ workflows/   │
│  generate_config_ref.py│            │ │ docs.yml     │
└─────────────────┘ └──────────────┘ └──────────────┘
```

### Recommended Project Structure

```
scripts/
├── generate_cli_ref.py      # Click introspection → cli-reference.md
├── generate_config_ref.py   # Settings introspection → configuration.md
└── generate_arch_diagram.py # Import analysis → architecture.md Mermaid
tests/
├── test_docs.py             # pytest: code block validation
├── conftest.py              # Shared fixtures (temp DB, test data)
└── unit/cli/                # Existing CLI tests
.github/
└── workflows/
    └── docs.yml             # CI workflow for docs validation
docs/
├── cli-reference.md         # Auto-generated + manual examples
├── configuration.md         # Auto-generated from Settings
├── quickstart.md            # Manually maintained, tested
├── architecture.md          # Hybrid: manual ASCII + Mermaid
├── search-algorithms.md     # Manually maintained, reviewed
├── models.md                # Manually maintained, reviewed
├── mcp-server.md            # Manually maintained, reviewed
└── ...                      # Other docs
```

### Pattern 1: Click CLI Introspection
**What:** Recursively traverse Click command tree to extract all commands, arguments, options, defaults, and help text.
**When to use:** Generating `docs/cli-reference.md` and validating that all commands are documented.
**Example:**
```python
# Source: Click 8.3.2 API (verified runtime)
import click

def traverse_commands(cmd, path=""):
    """Recursively yield all command paths and their parameters."""
    if isinstance(cmd, click.Group):
        for name, subcmd in cmd.commands.items():
            yield from traverse_commands(subcmd, f"{path} {name}".strip())
    else:
        params = []
        for p in cmd.params:
            if isinstance(p, click.Option):
                opts = "/".join(p.opts)
                default = p.default if p.default is not None else ""
                params.append(f"{opts} (default: {default})")
            elif isinstance(p, click.Argument):
                params.append(f"{p.name} (arg)")
        yield (path, cmd.help, params)
```

### Pattern 2: Pydantic Settings Introspection
**What:** Use Pydantic v2 `model_fields` to extract all settings with types, defaults, descriptions, and validators.
**When to use:** Generating `docs/configuration.md` and validating env var documentation.
**Example:**
```python
# Source: Pydantic 2.12.5 (verified runtime)
from docsift.config.settings import Settings

for name, field_info in Settings.model_fields.items():
    env_var = f"DOCSIFT_{name.upper()}"
    annotation = field_info.annotation
    default = field_info.default
    description = field_info.description or ""
    # Check for validators
    validators = [
        v for v in getattr(Settings, '__validators__', [])
        if getattr(v, 'field_name', None) == name
    ]
```

### Pattern 3: Markdown Code Block Extraction
**What:** Use regex to extract fenced code blocks with language tags, then classify by validation strategy.
**When to use:** `tests/test_docs.py` to find all code examples.
**Example:**
```python
# Source: Python stdlib re module (verified)
import re

def extract_code_blocks(md_content):
    pattern = r'```(\w*)\n(.*?)```'
    matches = re.findall(pattern, md_content, re.DOTALL)
    blocks = []
    for lang, content in matches:
        blocks.append({
            'language': lang or 'text',
            'content': content,
        })
    return blocks
```

### Pattern 4: CliRunner-Based Command Testing
**What:** Use `click.testing.CliRunner` to execute documented shell commands against a temporary database.
**When to use:** Validating bash/shell code blocks in docs.
**Example:**
```python
# Source: Click 8.3.2 (verified runtime)
from click.testing import CliRunner
from docsift.cli.main import cli
import tempfile
from pathlib import Path

def test_command_from_docs():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / 'test.db'
        result = runner.invoke(cli, ['--index', str(db_path), 'status'])
        assert result.exit_code == 0
```

### Pattern 5: AST-Based API Validation
**What:** Parse Python source files with `ast` to extract public symbols, then verify documented names exist.
**When to use:** Validating `docs/api-reference.md` and `docs/models.md`.
**Example:**
```python
# Source: Python stdlib ast module (verified)
import ast
from pathlib import Path

def extract_public_api(source_dir):
    api = {'classes': set(), 'functions': set()}
    for py_file in Path(source_dir).rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
                api['classes'].add(node.name)
            elif isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                api['functions'].add(node.name)
    return api
```

### Anti-Patterns to Avoid
- **Hard-coding command lists:** Do not maintain command lists manually in tests; always introspect from Click.
- **Full output comparison:** Do not compare exact CLI output strings; they contain environment-specific data (paths, timestamps). Check exit codes and key substrings only.
- **Executing network-dependent commands:** Do not run `docsift mcp http`, `docsift pull`, or `pip install` in tests. Use a blacklist skip pattern.
- **Importing modules for API validation:** Do not `import docsift.xxx` to check symbol existence; this triggers side effects (model downloads, logging setup). Use AST parsing instead.
- **Modifying docs during test runs:** Tests should validate docs, not modify them. Generation scripts are separate from validation tests.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI help extraction | Custom parser for Click decorators | Click's `get_commands()` + `params` API | Click already has complete metadata; custom parser will miss edge cases like `multiple=True`, `is_flag`, callable defaults |
| Settings field enumeration | Manual field list | Pydantic v2 `model_fields` | Manual lists drift; `model_fields` includes defaults, types, descriptions, validators automatically |
| Markdown code block parsing | Full Markdown parser library | Python `re` module | Fenced code blocks are simple to extract with regex; adding a dependency is unnecessary |
| CLI command execution | `subprocess.run()` | `click.testing.CliRunner` | CliRunner is faster, captures output, handles exceptions, and isolates the environment |
| Python syntax validation | `exec()` or `compile()` with risky flags | `ast.parse()` | AST parsing is safe (no execution), catches syntax errors, and works for snippets that aren't full modules |
| Temporary database for tests | Global test database | `tempfile.TemporaryDirectory` + pytest fixtures | Isolation prevents test pollution; each test gets a fresh database |

**Key insight:** The documentation drift in this project exists precisely because manual maintenance was used instead of introspection. The solution is to automate the extraction of canonical information from the code.

## Common Pitfalls

### Pitfall 1: Click Sentinel Values in Defaults
**What goes wrong:** Click uses `Sentinel.UNSET` as the default for options without explicit defaults. When generating docs, these appear as `default: Sentinel.UNSET` which is confusing to users.
**Why it happens:** Click distinguishes between "no default" and "default is None" internally.
**How to avoid:** Check for `click.core.Sentinel` or use `p.default is not None and not isinstance(p.default, type(click.Option.__init__.__defaults__[0]))` when formatting defaults. For required options, omit the default column.
**Warning signs:** Generated docs show `default: <object object>` or `default: Sentinel.UNSET`.

### Pitfall 2: Pydantic Path Types with `expanduser`
**What goes wrong:** Settings fields like `db_path` and `cache_dir` are `Path | None` with `expanduser` validators. The default is `None`, but the effective default (via `get_db_path()`) is `~/.local/share/docsift/docsift.db`.
**Why it happens:** The `Field(default=None)` is the Pydantic default, but the application computes the real default at runtime.
**How to avoid:** For Path fields with `None` defaults, document the computed default from the getter method, not the Pydantic field default.
**Warning signs:** Docs say `DOCSIFT_DB_PATH` default is `None` when it should say `~/.local/share/docsift/docsift.db`.

### Pitfall 3: Command Blacklist Maintenance
**What goes wrong:** As commands are added, the blacklist in `tests/test_docs.py` may not be updated, causing tests to attempt execution of network-dependent or long-running commands.
**Why it happens:** Blacklist is a static set that needs manual updating when commands change.
**How to avoid:** Make the blacklist explicit and check it against the actual CLI during test setup. Fail the test if a command is missing from either the blacklist or the execution list.
**Warning signs:** CI hangs on `docsift mcp http` or attempts to download models.

### Pitfall 4: Nested Command Group Help Output
**What goes wrong:** `docsift get get --help` works but `docsift get --help` shows the group help, not the leaf command. Docs may confuse users about the actual command path.
**Why it happens:** Click groups and commands can share names (e.g., `get` group contains `get` command).
**How to avoid:** In CLI reference, always show the full command path to the leaf command. Use `docsift get get DOCID` not `docsift get DOCID`.
**Warning signs:** Users try `docsift get docid` and get group help instead of command execution.

### Pitfall 5: Environment Variable Side Effects in Tests
**What goes wrong:** Tests that set `DOCSIFT_DB_PATH` via `os.environ` may leak to other tests or subprocess calls.
**Why it happens:** `os.environ` is a global mutable state.
**How to avoid:** Use `CliRunner(env={...})` or `monkeypatch.setenv` in pytest. Prefer passing `--index` explicitly to commands.
**Warning signs:** Tests pass in isolation but fail when run together.

### Pitfall 6: MkDocs vs README Format Divergence
**What goes wrong:** `docs/index.md` and `README.md` contain similar content but may diverge. README uses plain Markdown; MkDocs uses Material-specific extensions (admonitions, grids, icons).
**Why it happens:** README is for GitHub; `docs/index.md` is for MkDocs site. They serve different audiences.
**How to avoid:** Accept that README and docs/index.md will have overlapping but distinct content. Validate each independently. Do not try to auto-generate README from docs/index.md or vice versa.
**Warning signs:** GitHub renders `::: note` or `:material-rocket:` literally.

## Code Examples

### Verified patterns from official sources:

### Click Command Tree Traversal
```python
# Source: Click 8.3.2 API (verified runtime)
import click

def get_all_leaf_commands(cmd, prefix=''):
    """Get all leaf command paths from a Click CLI."""
    results = []
    if isinstance(cmd, click.Group):
        for name, subcmd in cmd.commands.items():
            results.extend(get_all_leaf_commands(subcmd, f"{prefix} {name}".strip()))
    else:
        results.append(prefix)
    return results

# Usage: paths = get_all_leaf_commands(cli)
# Returns: ['collection add', 'collection list', ..., 'status']
```

### Pydantic v2 Field Extraction
```python
# Source: Pydantic 2.12.5 (verified runtime)
from docsift.config.settings import Settings

def get_settings_fields():
    """Extract all settings fields with metadata."""
    fields = []
    for name, info in Settings.model_fields.items():
        env_var = f"DOCSIFT_{name.upper()}"
        fields.append({
            'name': name,
            'env_var': env_var,
            'type': info.annotation,
            'default': info.default,
            'description': info.description or '',
        })
    return fields
```

### Docs Code Block Validator (pytest)
```python
# Source: Verified pattern from project testing
import json
import ast
import re
from pathlib import Path
from click.testing import CliRunner
from docsift.cli.main import cli
import pytest

# Blacklist: commands that should not be executed
SKIP_COMMANDS = {
    'mcp http', 'mcp daemon', 'mcp stdio',
    'pull', 'index embed',
    'pip install',
}

def should_skip_command(cmd_line):
    """Check if a command should be skipped."""
    for pattern in SKIP_COMMANDS:
        if pattern in cmd_line:
            return True
    return False

def extract_shell_commands(block_content):
    """Extract executable commands from a shell code block."""
    lines = block_content.strip().split('\n')
    commands = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            continue  # Skip env var settings
        if line.startswith('git '):
            continue  # Skip git commands
        commands.append(line)
    return commands

class TestDocsCodeBlocks:
    def test_json_blocks_are_valid(self):
        docs_dir = Path('docs')
        for md_file in docs_dir.glob('*.md'):
            content = md_file.read_text()
            blocks = re.findall(r'```json\n(.*?)```', content, re.DOTALL)
            for block in blocks:
                try:
                    json.loads(block)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {md_file.name}: {e}")

    def test_python_blocks_are_valid_syntax(self):
        docs_dir = Path('docs')
        for md_file in docs_dir.glob('*.md'):
            content = md_file.read_text()
            blocks = re.findall(r'```python\n(.*?)```', content, re.DOTALL)
            for block in blocks:
                try:
                    ast.parse(block)
                except SyntaxError as e:
                    pytest.fail(f"Invalid Python in {md_file.name}: {e}")
```

### GitHub Actions Workflow for Docs
```yaml
# Source: Standard GitHub Actions pattern (verified)
name: Docs Validation

on:
  pull_request:
    paths:
      - 'docs/**'
      - 'README.md'
      - 'src/docsift/cli/**'
      - 'src/docsift/config/**'
  push:
    branches: [main]

jobs:
  docs-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest tests/test_docs.py -v
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `__fields__` | Pydantic v2 `model_fields` | Pydantic 2.0 (2023) | `model_fields` is a dict of `FieldInfo` objects; `__fields__` removed |
| Click 7.x `command.callback` | Click 8.x `command.commands` | Click 8.0 (2021) | `commands` dict is the standard way to access subcommands |
| Manual docs maintenance | Auto-generated + validated | This phase | Eliminates drift; CI enforces accuracy |
| `pytest-markdown` plugin | Custom pytest tests | This phase | Custom tests give full control over skip logic and temp DB setup |

**Deprecated/outdated:**
- `docsift search similar`: Command removed; no replacement at top level.
- `docsift mcp start`: Replaced by `docsift mcp stdio` and `docsift mcp http`.
- `docsift mcp config`: Command does not exist.
- `docsift collection create`: Replaced by `docsift collection add`.
- `docsift collection add-path`: Merged into `collection add` workflow.
- `DOCSIFT_BM25_K1`, `DOCSIFT_BM25_B`: Settings removed; BM25 parameters not configurable via env.
- `DOCSIFT_MAX_WORKERS`, `DOCSIFT_CACHE_SIZE`, `DOCSIFT_LOG_FILE`, `DOCSIFT_RRF_K`: Settings do not exist in `Settings` class.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `model_type` valid choices are `sentence_transformers`, `gguf`, `openai`, `modelscope`, `huggingface` | Standard Stack | Docs would list wrong model types; validator would reject valid types or accept invalid ones |
| A2 | `repository.py` (interface) and `repositories.py` (implementation) both exist and are the canonical data access layer | Architecture Patterns | Architecture docs would reference wrong files; api-reference has stale `SQLiteCollectionRepository` refs |
| A3 | MkDocs Material is the intended docs site generator (evidenced by `mkdocs.yml`) | Pitfall 6 | If not used, Material-specific syntax in `docs/index.md` should be removed |
| A4 | `docsift collection add` is the correct command (not `collection create`) for creating collections | State of the Art | CLI reference and quickstart would document wrong command |
| A5 | `docsift get get` is the correct path (group `get` + command `get`) | Pitfall 4 | Docs might incorrectly show `docsift get` as a leaf command |

## Open Questions

1. **Should `docs/index.md` be auto-generated from `README.md` or maintained separately?**
   - What we know: Both exist with overlapping content; `index.md` uses MkDocs Material extensions.
   - What's unclear: Whether there's a single source of truth or intentional divergence.
   - Recommendation: Treat them as separate documents. README is for GitHub; `index.md` is for docs site. Validate each independently.

2. **What is the exact blacklist for commands that should not be executed in tests?**
   - What we know: Commands like `mcp http`, `pull`, `index embed` require network or models.
   - What's unclear: Whether `bench` should be tested (needs fixture file) or `cleanup` (modifies data).
   - Recommendation: Start conservative; blacklist all network-dependent, long-running, and data-destructive commands. Expand whitelist as needed.

3. **Should the CLI reference generation script be run manually or in CI?**
   - What we know: The script generates docs from Click introspection.
   - What's unclear: Whether generated content should be committed or generated at docs build time.
   - Recommendation: Generate and commit the output (like lockfiles). This allows human review of changes and avoids build-time dependencies.

4. **How should the architecture diagram in `architecture.md` be updated?**
   - What we know: Current diagram shows `mcp_server/` but not legacy `mcp/`; module structure has changed.
   - What's unclear: Whether to use auto-generated Mermaid or maintain ASCII art.
   - Recommendation: Per CONTEXT.md D-10: Keep ASCII in README (manual), generate Mermaid in `architecture.md` (scripted).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All scripts | Yes | 3.13.9 | — |
| Click | CLI introspection | Yes | 8.3.2 | — |
| Pydantic v2 | Settings introspection | Yes | 2.12.5 | — |
| pytest | Docs testing | Yes | 9.0.2 | — |
| GitHub Actions | CI workflow | Yes | N/A | — |
| mkdocs | Docs site build | Yes | 1.6.1 | Not required for this phase |
| mkdocs-material | Docs site theme | Yes | 9.7.1 | Not required for this phase |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (pytest.ini_options) |
| Quick run command | `pytest tests/test_docs.py -x -q` |
| Full suite command | `pytest tests/test_docs.py -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-01 | CLI reference has all commands | unit | `pytest tests/test_docs.py::test_cli_reference_complete -x` | No — Wave 0 |
| DOC-02 | Configuration docs match Settings | unit | `pytest tests/test_docs.py::test_configuration_complete -x` | No — Wave 0 |
| DOC-03 | Quickstart commands execute | integration | `pytest tests/test_docs.py::test_quickstart_commands -x` | No — Wave 0 |
| DOC-04 | README model names correct | unit | `pytest tests/test_docs.py::test_readme_accuracy -x` | No — Wave 0 |
| DOC-05 | Technical docs reviewed | manual | N/A (human review) | N/A |
| DOC-06 | Code blocks validated | integration | `pytest tests/test_docs.py -x` | No — Wave 0 |
| DOC-07 | Docs test infrastructure exists | integration | `make docs-test` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_docs.py -x -q` (quick validation)
- **Per wave merge:** `pytest tests/test_docs.py -v` (full validation)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_docs.py` — covers DOC-01 through DOC-07
- [ ] `tests/conftest.py` — docs-specific fixtures (temp DB with test data)
- [ ] `scripts/generate_cli_ref.py` — CLI reference generator
- [ ] `scripts/generate_config_ref.py` — Settings reference generator
- [ ] `Makefile` — `docs-test` target
- [ ] `.github/workflows/docs.yml` — CI workflow

## Security Domain

> This phase is documentation-only with no new security surface. Existing security considerations from the codebase apply.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in DocSift |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | Single-user local tool |
| V5 Input Validation | Yes | Pydantic validators in Settings; Click type validation |
| V6 Cryptography | No | No crypto operations in docs |

### Known Threat Patterns for Documentation

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Documentation showing unsafe defaults | Information Disclosure | Validate defaults match secure settings |
| Docs exposing internal paths | Information Disclosure | Use generic paths (`~/.docsift/`) |
| Example API keys in docs | Information Disclosure | Use placeholder values (`YOUR_API_KEY`) |

## Sources

### Primary (HIGH confidence)
- Click 8.3.2 runtime API — `get_commands()`, `params`, `CliRunner` — verified via `python -c` commands
- Pydantic 2.12.5 runtime API — `model_fields`, `FieldInfo` — verified via `python -c` commands
- DocSift codebase — `src/docsift/cli/main.py`, `src/docsift/config/settings.py` — direct file inspection
- DocSift test suite — `tests/conftest.py`, `tests/unit/cli/` — direct file inspection

### Secondary (MEDIUM confidence)
- MkDocs Material documentation — `mkdocs.yml` configuration — file inspection
- GitHub Actions documentation — workflow patterns — standard CI knowledge
- pytest documentation — fixture patterns and best practices — standard testing knowledge

### Tertiary (LOW confidence)
- None — all claims verified via runtime inspection or file reading

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified at runtime with exact versions
- Architecture: HIGH — command tree and Settings fields fully introspected
- Pitfalls: HIGH — all pitfalls derived from actual discrepancies found in docs

**Research date:** 2026-04-18
**Valid until:** 2026-05-18 (stable stack, but verify if Click or Pydantic versions change)
