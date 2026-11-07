# Phase 6: Documentation Audit & Refresh - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

All project documentation accurately reflects the current CLI commands, API, and configuration. Every code example in docs is syntax-checked or executed and verified to work. A docs testing infrastructure is established for ongoing maintenance.

This phase delivers:
- Updated CLI reference (`docs/cli-reference.md`) with complete Click-derived documentation
- Updated configuration guide (`docs/configuration.md`) matching the `Settings` class
- Updated quickstart (`docs/quickstart.md`) with working command examples
- Updated README with correct default models and realistic roadmap
- Updated technical docs (`mcp-server.md`, `search-algorithms.md`, `architecture.md`, `models.md`)
- Automated docs testing infrastructure: pytest tests, Makefile target, GitHub Actions workflow

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**7 requirements are locked.** See `06-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `06-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- All markdown files in `docs/` directory and root directory (`README.md`, `CLAUDE.md`, etc.)
- Automated CLI reference generation script (extracts from Click `--help`)
- Automated Settings introspection script (validates configuration.md against `Settings` class)
- pytest-based docs code block validator (`tests/test_docs.py`)
- Makefile target (`make docs-test`)
- GitHub Actions CI workflow for docs validation
- Manual review and fixes for `mcp-server.md`, `search-algorithms.md`, `architecture.md`, `models.md`
- Fixes to code examples in quickstart, README, and other docs

**Out of scope (from SPEC.md):**
- PyPI package publication
- Rewriting or refactoring CLI command implementations
- Creating new CLI commands
- Adding new Settings fields solely for docs generation
- Rewriting `CLAUDE.md`
- Web UI, plugin system, or other backlog features
</spec_lock>

<decisions>
## Implementation Decisions

### CLI Reference Generation
- **D-01:** Python script traverses Click command tree to generate CLI reference documentation
  - Script location: `scripts/generate_cli_ref.py`
  - Uses Click's `get_help()` / `get_commands()` API to recursively traverse all command groups
  - Handles nested command groups: `collection`, `context`, `mcp`, `search`, `index`, `get`
  - Format: mixed — command overview in tables, detailed parameters from `--help` output
- **D-02:** Script also extracts example code from Click command docstrings or code comments
  - Workflow examples (e.g., "Setting up a new collection") are auto-extracted where available
  - Fallback to human-written examples for commands without docstring examples

### Code Block Classification & Validation
- **D-03:** Classification based on fence language tags
  - `bash` / `shell` → executable or command existence validation
  - `json` → syntax validation (json.loads)
  - `python` → syntax validation (compile/ast.parse)
  - `text` / no tag → skip (display-only output examples)
- **D-04:** Blacklist for commands that should not be executed
  - Commands like `mcp start`, `pip install docsift`, `docsift mcp daemon` are skipped
  - Blacklist maintained in `tests/test_docs.py` as a set of command patterns
- **D-05:** Selective output validation for JSON/structured output
  - JSON output validated against expected schema (contains expected keys)
  - Not a full output comparison (avoids environment-specific failures like paths/timestamps)

### Docs Test Execution Environment
- **D-06:** pytest fixture creates temporary database with minimal test data
  - Uses `tmp_path` fixture for temporary SQLite database
  - Inserts one test collection with 2-3 documents for search validation
  - No external network access required
- **D-07:** Mixed execution strategy: Click CliRunner as primary, subprocess as secondary
  - Most commands validated via `click.testing.CliRunner` (fast, no subprocess overhead)
  - Commands involving environment variables or config file paths use subprocess for realism
- **D-08:** Isolated environment for each command
  - Clean `os.environ` copy per test run
  - Only injects minimal required variables (e.g., `DOCSIFT_DB_PATH` pointing to temp database)
  - Does not apply `export` statements from code blocks (they are display-only)

### Technical Docs Update
- **D-09:** Technical docs validation via AST parsing
  - Parse Python source files to extract public API (classes, functions, constants)
  - Scan `docs/*.md` for backtick-quoted class/function names and file paths
  - Validate that referenced names exist in the codebase
  - Report: "documented but not found" and "found in code but not documented"
- **D-10:** Architecture diagram strategy: hybrid
  - README keeps ASCII art high-level architecture diagram (manually maintained)
  - `docs/architecture.md` contains detailed module dependency graph generated by script
  - Script generates Mermaid diagram from `src/docsift/` import relationships

### Claude's Discretion
- Exact blacklist command patterns (specific commands to skip)
- JSON schema definitions for output validation (which keys to check per command)
- Mermaid diagram styling and layout in architecture.md
- pytest fixture data content (which test documents to insert)
- Makefile target name and exact commands (`make docs-test` vs `make test-docs`)
- GitHub Actions workflow trigger conditions (on PR, on push to main, etc.)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Spec
- `.planning/phases/06-documentation-audit-refresh/06-SPEC.md` — Locked requirements, boundaries, acceptance criteria
- `.planning/REQUIREMENTS.md` § DOC-01 through DOC-07
- `.planning/ROADMAP.md` § Phase 6: Documentation Audit & Refresh

### Prior Phase Context
- `.planning/phases/05-agent-context-experience/05-CONTEXT.md` — CLI command patterns, context add/list/remove structure
- `.planning/phases/04-advanced-search-pipeline/04-CONTEXT.md` — Search options (--explain, --candidate-limit, --intent), query expansion, reranker
- `.planning/phases/03-embedding-vector-search/03-CONTEXT.md` — Embedding backends, ModelScope, Settings fields

### Existing Code (Source of Truth)
- `src/docsift/cli/main.py` — CLI group registration, top-level commands
- `src/docsift/cli/commands/*.py` — All CLI command implementations
- `src/docsift/config/settings.py` — Settings class with all env vars and defaults
- `Makefile` — Existing targets (add `docs-test` target)
- `.github/workflows/` — CI workflow directory (currently empty)

### Existing Documentation
- `docs/cli-reference.md` — Current (stale) CLI reference
- `docs/configuration.md` — Current (stale) configuration guide
- `docs/quickstart.md` — Current (stale) quickstart
- `docs/mcp-server.md` — Current (likely stale) MCP documentation
- `docs/search-algorithms.md` — Current (likely stale) search algorithm docs
- `docs/architecture.md` — Current (likely stale) architecture docs
- `docs/models.md` — Current (likely stale) models documentation
- `README.md` — Current (stale) project README
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Click CLI structure in `src/docsift/cli/main.py` — can be introspected via `cli.commands` dict
- `Settings` class in `src/docsift/config/settings.py` — can be introspected via `pydantic` fields or `__fields__`
- Existing `Makefile` — add `docs-test` target alongside existing targets
- `click.testing.CliRunner` — already available via Click dependency

### Established Patterns
- CLI commands use `@click.command()` and `@click.option()` decorators
- Settings use Pydantic `BaseSettings` with `env_prefix="DOCSIFT_"`
- Tests use pytest with fixtures in `tests/` directory
- No existing docs testing infrastructure

### Integration Points
- `scripts/generate_cli_ref.py` needs to import `docsift.cli.main.cli` and traverse command tree
- `tests/test_docs.py` needs to import CLI commands and use `CliRunner`
- `Makefile` needs new `docs-test` target that runs pytest docs tests
- `.github/workflows/docs.yml` needs to set up Python environment and run docs tests
- Architecture diagram script needs to parse Python imports in `src/docsift/`
</code_context>

<specifics>
## Specific Ideas

- CLI reference should clearly distinguish command groups vs leaf commands:
  - Command groups: `collection`, `context`, `get`, `index`, `mcp`, `search`
  - Leaf commands: `bench`, `cleanup`, `ls`, `pull`, `status`
- Search command options differ between subcommands:
  - `search search` (BM25): `--limit`, `--collection`, `--all`, `--min-score`, `--full`, `--explain`, `--line-numbers`, `--json`, `--csv`, `--md`, `--xml`, `--files`
  - `search query` (hybrid): all BM25 options + `--candidate-limit`, `--intent`, `--model-type`
  - `search vsearch` (vector): subset of BM25 options + `--model-type`
- `collection` subcommands not in current docs: `disable`, `enable`, `exclude`, `include`, `ls`, `update-cmd`
- `context` subcommands not in current docs: `prune`, `rm` (alias for `remove`)
- `mcp` subcommands not in current docs: `daemon`, `http`, `stdio` (docs shows `mcp start` and `mcp config` which don't exist)
- Configuration docs should document `model_type` choices: `sentence_transformers`, `gguf`, `openai`, `modelscope`, `huggingface`
- Default model changed from `all-MiniLM-L6-v2` to `Qwen/Qwen3-Embedding-0.6B` (1024 dim)
- Reranker defaults: `Qwen/Qwen3-Reranker-0.6B`, type `transformers`
- Architecture diagram should reflect: `mcp_server/` (OOP) and legacy `mcp/` coexist
</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

### Reviewed Todos (not folded)
- None — no relevant pending todos found.
</deferred>

---

*Phase: 06-documentation-audit-refresh*
*Context gathered: 2026-04-18*
*Next step: /gsd-plan-phase 6 — implementation planning*
