---
phase: 06-documentation-audit-refresh
plan: 06
subsystem: docs
completed_date: "2026-04-18"
duration: "16m"
tasks_completed: 3
total_tasks: 3
---

# Phase 06 Plan 06: Docs Code Block Validator Summary

Pytest-based documentation code block validator that executes or syntax-checks every code example in documentation, with fixes for all broken examples discovered during validation.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| e5af2bf | test | Add docs test fixtures (docs_test_db, docs_runner) |
| 6ff1e31 | test | Create docs code block validator (tests/test_docs.py) |
| 823c257 | fix | Fix broken examples discovered by validator |
| b8e299e | refactor | Ruff compliance for test_docs.py |
| 12bdf9c | fix | Update EmbeddingConfig default model in models.md |

## Key Changes

### tests/test_docs.py (459 lines)

Created comprehensive docs validator with 12 test methods:

1. **test_json_blocks_are_valid** — All JSON code blocks parse via json.loads
2. **test_json_output_examples_have_expected_keys** — JSON output examples contain expected schema keys (per D-05)
3. **test_python_blocks_are_valid_syntax** — All Python blocks parse via ast.parse, with stub/signature-only block detection
4. **test_shell_commands_exist** — Shell commands verified against Click CLI command tree
5. **test_no_removed_commands_in_docs** — Detects removed commands (collection create, search similar, etc.)
6. **test_model_names_are_current** — Ensures old model names (all-MiniLM-L6-v2) only appear with Qwen context
7. **test_no_bare_search_command** — Detects missing search subcommands (search/query/vsearch)
8. **test_no_positional_args_for_option_only_commands** — Detects positional args for commands that only take options
9. **test_no_collection_delete_command** — Detects old "collection delete" (should be "remove")
10. **test_configuration_no_phantom_fields** — Detects phantom env vars in configuration.md
11. **test_cli_reference_has_all_commands** — Verifies cli-reference.md covers all Click commands
12. **test_sql_blocks_are_valid** — SQL blocks start with valid keywords

### tests/conftest.py

Added docs-specific fixtures:
- `docs_test_db` — Temporary database with test collection and 2 documents
- `docs_runner` — CliRunner with DOCSIFT_DB_PATH pre-configured

### Documentation Fixes

| File | Fixes |
|------|-------|
| README.md | search query subcommand, index update --collection, collection remove, status |
| docs/index.md | search query subcommand, index update --collection, search types (search/vsearch/query) |
| docs/cli-reference.md | index update --collection, search query subcommand |
| docs/configuration.md | Replace config show with status |
| docs/quickstart.md | collection remove instead of delete |
| docs/architecture.md | search query subcommand |
| docs/models.md | EmbeddingConfig default model to Qwen3 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Collection/Document import mismatch in fixtures**
- **Found during:** Task 1
- **Issue:** conftest.py imports Collection from docsift.core.collection (different fields: paths vs path) but the database repository expects docsift.core.models.Collection (path field)
- **Fix:** Used local imports with aliases (DocsCollection, DocsDocument) in the docs_test_db fixture to use the correct models
- **Files modified:** tests/conftest.py

**2. [Rule 1 - Bug] Command verification with Click PATH validation**
- **Found during:** Task 2
- **Issue:** Replacing positional args with "dummy" caused Click to fail on PATH-type arguments that validate directory existence
- **Fix:** Changed command verification to strip positional args entirely and only test subcommand existence via --help
- **Files modified:** tests/test_docs.py

**3. [Rule 1 - Bug] Python stub blocks in mcp-server.md**
- **Found during:** Task 2
- **Issue:** API reference blocks with method signatures missing bodies (e.g., `def start(self) -> None` without `:` or `...`) fail AST parsing
- **Fix:** Added `_is_stub_block()` helper that detects class stubs with method signatures, `...` placeholders, and multi-line `__init__` signatures
- **Files modified:** tests/test_docs.py

**4. [Rule 1 - Bug] SQL blocks with leading comments**
- **Found during:** Task 2
- **Issue:** SQL blocks starting with `-- Create FTS5 virtual table` failed the "starts with valid keyword" check
- **Fix:** Skip leading comment lines when checking SQL block validity
- **Files modified:** tests/test_docs.py

**5. [Rule 2 - Missing critical functionality] config command does not exist**
- **Found during:** Task 2
- **Issue:** docs/configuration.md referenced `docsift config show` which is not implemented in the CLI
- **Fix:** Changed to `docsift status` and `docsift status --verbose`
- **Files modified:** docs/configuration.md

**6. [Rule 2 - Missing critical functionality] EmbeddingConfig default model outdated in models.md**
- **Found during:** Task 3
- **Issue:** models.md showed `all-MiniLM-L6-v2` as the default model_name in EmbeddingConfig, but the actual default is `Qwen/Qwen3-Embedding-0.6B`
- **Fix:** Updated default model_name and model_type in the EmbeddingConfig example
- **Files modified:** docs/models.md

## Known Stubs

None. All code blocks in documentation are either executable, syntax-validated, or explicitly skipped (long-running commands like mcp server, pip install).

## Threat Flags

None. The docs validator only reads local files and uses CliRunner for command verification. No new network endpoints, auth paths, or file access patterns introduced.

## Self-Check: PASSED

- [x] tests/test_docs.py exists (459 lines)
- [x] All 12 tests pass
- [x] ruff check tests/test_docs.py passes
- [x] ruff format --check tests/test_docs.py passes
- [x] Commits verified: e5af2bf, 6ff1e31, 823c257, b8e299e, 12bdf9c
- [x] No file deletions in any commit
- [x] Existing tests still pass (tests/unit/cli/test_collection.py: 7 passed)
