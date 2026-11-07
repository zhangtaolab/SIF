---
phase: 02-cli-core-completion
verified: 2026-04-15T12:00:00Z
status: passed
score: 6/6
overrides_applied: 0
gaps: []
deferred: []
human_verification: []
---

# Phase 02: CLI Core Completion Verification Report

**Phase Goal:** Complete the CLI command surface for core document retrieval, collection management, and search workflows.

**Verified:** 2026-04-15T12:00:00Z

**Status:** passed

**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                 | Status     | Evidence                                                                 |
| --- | --------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------ |
| 1   | User can batch-retrieve documents by glob, comma-separated list, or docid with `multi-get` | VERIFIED   | `src/docsift/cli/commands/get.py` contains three-branch auto-detection (comma > glob > single) using `fnmatch.fnmatch` and `doc_repo.get_by_id` / `get_by_path`. `tests/unit/cli/test_get.py` covers all branches plus no-match case. |
| 2   | User can list indexed documents as a virtual file tree via `ls`       | VERIFIED   | `src/docsift/cli/commands/ls.py` implements `ls_cmd` with `rich.tree.Tree` rendering and queries `DocumentRepository.list_by_collection`. `tests/unit/cli/test_ls.py` covers no-index, all collections, specific collection, subpath filter, and not-found cases. |
| 3   | User can set or clear a pre-index shell command per collection with `collection update-cmd` | VERIFIED   | `src/docsift/cli/commands/collection.py` contains `collection_update_cmd` with `--cmd` and `--clear` options. `Collection.pre_update_cmd` is persisted via `CollectionRepository`. `tests/unit/cli/test_collection.py` covers set, clear, and missing-collection cases. |
| 4   | User can include or exclude collections from default queries with `collection include/exclude` | VERIFIED   | `src/docsift/cli/commands/collection.py` contains `collection_include` and `collection_exclude` commands. `src/docsift/cli/commands/search.py` wires `--all` flag into `search_cmd`, `query_cmd`, and `vsearch_cmd` to filter via `CollectionRepository.list_enabled()`. `tests/unit/cli/test_search.py` verifies filtering behavior. |
| 5   | User can download and verify local GGUF model files with `pull`       | VERIFIED   | `src/docsift/cli/commands/pull.py` implements `pull_cmd` with HuggingFace primary download (`hf_hub_download`), ModelScope fallback (`snapshot_download`), direct URL support, and file existence/size verification. `tests/unit/cli/test_pull.py` covers all 6 test cases. |
| 6   | Search and retrieval output can display line numbers via `--line-numbers` | VERIFIED   | `src/docsift/cli/formatters.py` provides `prepend_line_numbers` and `add_line_numbers_to_results`. `get.py`, `search.py` commands accept `--line-numbers` and apply it to table and structured output (JSON, CSV, MD, XML). `tests/unit/cli/test_formatters.py`, `test_get.py`, `test_search.py` cover line-number behavior. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/docsift/cli/commands/get.py` | multi-get command with auto-detection | VERIFIED | Exists, substantive, wired into `get_group` |
| `src/docsift/cli/commands/ls.py` | top-level ls command implementation | VERIFIED | Exists, substantive, registered in `main.py` |
| `src/docsift/cli/commands/pull.py` | pull command implementation | VERIFIED | Exists, substantive, registered in `main.py` |
| `src/docsift/cli/commands/search.py` | search/query/vsearch with --all and --line-numbers | VERIFIED | Exists, substantive, wired into `search_group` |
| `src/docsift/cli/commands/collection.py` | update-cmd, include, exclude subcommands | VERIFIED | Exists, substantive, wired into `collection_group` |
| `src/docsift/cli/commands/index.py` | pre_update_cmd hook in index update | VERIFIED | Exists, substantive, uses `subprocess.run` with fail-fast |
| `src/docsift/cli/formatters.py` | line-number-aware formatting helpers | VERIFIED | Exists, substantive, imported by get.py and search.py |
| `src/docsift/cli/main.py` | command registration | VERIFIED | Imports and registers all commands |
| `src/docsift/core/models.py` | Collection.pre_update_cmd field | VERIFIED | Field present with to_dict/from_dict support |
| `src/docsift/database/schema.py` | Safe migration for pre_update_cmd column | VERIFIED | `_add_column_if_missing` called for `pre_update_cmd` |
| `src/docsift/database/repositories.py` | pre_update_cmd persistence + list_enabled | VERIFIED | CREATE/UPDATE/row-mapping include `pre_update_cmd`; `list_enabled()` implemented |
| `tests/unit/cli/test_get.py` | Unit tests for multi-get and line-numbers | VERIFIED | 6 tests pass |
| `tests/unit/cli/test_ls.py` | Unit tests for ls | VERIFIED | 5 tests pass |
| `tests/unit/cli/test_collection.py` | Unit tests for update-cmd and index hook | VERIFIED | 7 tests pass |
| `tests/unit/cli/test_search.py` | Unit tests for search filtering and line-numbers | VERIFIED | 8 tests pass |
| `tests/unit/cli/test_pull.py` | Unit tests for pull | VERIFIED | 6 tests pass |
| `tests/unit/cli/test_formatters.py` | Unit tests for line-number helpers | VERIFIED | 3 tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `get.py:multi_get_cmd` | `fnmatch.fnmatch` | glob matching against doc.path and doc.filename | WIRED | `fnmatch.fnmatch(doc.path, pattern)` and `fnmatch.fnmatch(doc.filename, pattern)` at line 162 |
| `get.py:multi_get_cmd` | `doc_repo.get_by_id` / `doc_repo.get_by_path` | single-item fallback retrieval | WIRED | Called in all three branches (comma, glob, single) |
| `ls.py:ls_cmd` | `rich.tree.Tree` | virtual directory tree rendering | WIRED | `Tree` imported and instantiated at line 58 |
| `ls.py:ls_cmd` | `DocumentRepository.list_by_collection` | database query for indexed documents | WIRED | Called at line 50 inside collection loop |
| `index.py:update_cmd` | `Collection.pre_update_cmd` | subprocess.run with shell=True, fail fast on non-zero exit | WIRED | `subprocess.run(coll.pre_update_cmd, shell=True, ...)` at line 71; raises `ClickException` on non-zero exit |
| `search.py:search_cmd` | `CollectionRepository.list_enabled` | search_all flag controls collection resolution | WIRED | `elif not search_all:` blocks call `repo.list_enabled()` in `search_cmd`, `query_cmd`, and `vsearch_cmd` |
| `pull.py:pull_cmd` | `huggingface_hub.hf_hub_download` | primary download path | WIRED | Module-level optional import; `_download_from_hf` calls it at line 45 |
| `pull.py:pull_cmd` | `modelscope.snapshot_download` | fallback download path | WIRED | Module-level optional import; `_download_from_modelscope` calls it at line 59 |
| `get.py / search.py` | `formatters.py` | preprocess content with line numbers before passing to formatter or console.print | WIRED | `prepend_line_numbers` imported and used in `get.py`; `add_line_numbers_to_results` and `prepend_line_numbers` imported and used in `search.py` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `ls.py:ls_cmd` | `docs` | `DocumentRepository.list_by_collection(coll.id)` | DB query | FLOWING |
| `search.py:search_cmd` | `results` | `BM25Searcher.search(query, options)` | DB query via FTS5 | FLOWING |
| `search.py:query_cmd` | `results` | `HybridSearcher.search(query, options)` | DB query via FTS5 + vector | FLOWING |
| `search.py:vsearch_cmd` | `results` | `VectorSearcher.search(query_embedding, options)` | DB query via sqlite-vec | FLOWING |
| `get.py:get_cmd` | `doc` | `DocumentRepository.get_by_id` / `get_by_path` | DB query | FLOWING |
| `index.py:update_cmd` | `result` | `subprocess.run(coll.pre_update_cmd, ...)` | Real subprocess execution | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| `docsift --help` shows registered commands | `python -m docsift.cli.main --help` | Shows `ls`, `pull`, `get`, `search`, `collection`, `index` | PASS |
| `docsift ls --help` works | `python -m docsift.cli.main ls --help` | Shows usage with optional COLLECTION and SUBPATH | PASS |
| `docsift pull --help` works | `python -m docsift.cli.main pull --help` | Shows usage with MODEL_SPEC and --cache-dir | PASS |
| `docsift get multi-get --help` works | `python -m docsift.cli.main get multi-get --help` | Shows usage with PATTERN and --line-numbers | PASS |
| `docsift search search --help` shows --line-numbers and --all | `python -m docsift.cli.main search search --help` | Shows both flags | PASS |
| `docsift collection update-cmd --help` works | `python -m docsift.cli.main collection update-cmd --help` | Shows --cmd and --clear options | PASS |
| All unit tests pass | `pytest tests/unit/cli/test_*.py -v` | 35 passed, 0 failed | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| CLI-01 | 02-01-PLAN.md | multi-get batch document retrieval | SATISFIED | `get.py` implements three-branch auto-detection; `test_get.py` covers all branches |
| CLI-02 | 02-02-PLAN.md | `ls` virtual file tree for indexed documents | SATISFIED | `ls.py` renders Tree from DB; `test_ls.py` covers all branches |
| CLI-03 | 02-03a-PLAN.md | `collection update-cmd` pre-index shell command | SATISFIED | `collection.py` has update-cmd; `index.py` runs subprocess hook; `test_collection.py` verifies both |
| CLI-04 | 02-03a-PLAN.md, 02-03b-PLAN.md | `collection include/exclude` and `--all` in search | SATISFIED | `collection.py` has include/exclude; `search.py` wires `--all` to `list_enabled()`; `test_search.py` verifies |
| CLI-05 | 02-04-PLAN.md | `pull` command for GGUF model download | SATISFIED | `pull.py` implements HF primary + ModelScope fallback + URL direct; `test_pull.py` covers all cases |
| CLI-08 | 02-05-PLAN.md | `--line-numbers` display flag | SATISFIED | `formatters.py` has helpers; `get.py` and `search.py` wire the flag; tests verify table and structured output |

### Anti-Patterns Found

No blockers, warnings, or notable anti-patterns found in the phase 02 modified files.

- No `TODO` / `FIXME` / `XXX` / `HACK` / `PLACEHOLDER` comments
- No placeholder text ("coming soon", "not yet implemented")
- No empty returns (`return null`, `return {}`, `return []`)
- No hardcoded empty data flowing to rendering

### Human Verification Required

None. All behaviors are verifiable programmatically through unit tests and CLI help output checks.

### Gaps Summary

No gaps found. All 6 roadmap success criteria are satisfied, all artifacts exist and are substantive, all key links are wired, and all 35 unit tests pass.

---

_Verified: 2026-04-15T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
