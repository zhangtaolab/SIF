---
phase: 02-cli-core-completion
reviewed: 2026-04-15T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - src/docsift/cli/commands/collection.py
  - src/docsift/cli/commands/get.py
  - src/docsift/cli/commands/index.py
  - src/docsift/cli/commands/ls.py
  - src/docsift/cli/commands/pull.py
  - src/docsift/cli/commands/search.py
  - src/docsift/cli/main.py
  - src/docsift/core/models.py
  - src/docsift/database/repositories.py
  - src/docsift/database/schema.py
  - tests/unit/cli/test_collection.py
  - tests/unit/cli/test_get.py
  - tests/unit/cli/test_ls.py
  - tests/unit/cli/test_pull.py
  - tests/unit/cli/test_search.py
findings:
  critical: 5
  warning: 10
  info: 4
  total: 19
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-15
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Reviewed CLI command modules, core models, database repositories/schema, and corresponding unit tests for the CLI core completion phase. Found 5 critical issues including a command injection vulnerability, data integrity bugs in document updates and embedding management, a missing import causing crashes in error handling, and runtime crashes when combining certain output formats with `--line-numbers`. Additionally found 10 warnings and 4 info items related to code duplication, dead code, local imports, and incorrect user-facing messages.

## Critical Issues

### CR-01: Command Injection via `shell=True` in Index Update Pre-Update Hook

**File:** `src/docsift/cli/commands/index.py:71`
**Issue:** `subprocess.run(coll.pre_update_cmd, shell=True, capture_output=True, text=True)` executes a shell command stored in the collection's `pre_update_cmd` field without any sanitization. A malicious value injected into `pre_update_cmd` (e.g., via `docsift collection update-cmd`) will execute arbitrary shell commands during `docsift index update`.
**Fix:** Avoid `shell=True`. Parse the command into a list and use `shell=False`, or validate/sanitize the command before execution.
```python
# Safer approach using shell=False
result = subprocess.run(
    shlex.split(coll.pre_update_cmd),
    shell=False,
    capture_output=True,
    text=True,
)
```

### CR-02: Stale Checksum and File Size on Document Update

**File:** `src/docsift/cli/commands/index.py:128-132`
**Issue:** When updating an existing document, `existing.content` is assigned but `existing.checksum` and `existing.file_size` are not recomputed. `Document.__post_init__` only runs at instantiation, so the database stores stale derived fields. This breaks future incremental updates (checksum mismatch on every run) and corrupts stats.
**Fix:** Recompute `checksum` and `file_size` after modifying `content`.
```python
existing.content = parsed.content
existing.title = parsed.title
existing.metadata = parsed.metadata
existing.mtime = parsed.mtime
existing.checksum = hashlib.sha256(existing.content.encode()).hexdigest()
existing.file_size = len(existing.content.encode())
doc_repo.update(existing)
```

### CR-03: Missing `sqlite3` Import Causes Crash in Cleanup Error Path

**File:** `src/docsift/cli/main.py:155`
**Issue:** `cleanup_cmd` catches `sqlite3.OperationalError`, but `sqlite3` is never imported in `main.py`. If the `document_embeddings` table does not exist, Python raises `NameError: name 'sqlite3' is not defined` while evaluating the `except` clause, causing an unhandled crash.
**Fix:** Add `import sqlite3` at the top of `main.py`.

### CR-04: `--csv`, `--md`, and `--xml` Output Crashes with `--line-numbers`

**File:** `src/docsift/cli/commands/search.py`
**Issue:** When `--line-numbers` is used with `--csv`, `--md`, or `--xml`, the code passes a list of dicts (from `add_line_numbers_to_results`) to `format_results_csv`, `format_results_md`, and `format_results_xml`. These formatter functions access object attributes (e.g., `r.rank`, `r.title`) on the dicts, causing `AttributeError` at runtime. Only `--json` handles dicts correctly.
**Fix:** Update the formatter functions to handle both objects and dicts, or add `line_numbers` directly to `SearchResult` instances instead of converting to dicts.
```python
def _get_attr(r: Any, name: str) -> Any:
    if isinstance(r, dict):
        return r.get(name)
    return getattr(r, name)
```

### CR-05: Orphaned Embeddings Accumulate on Re-Embed

**File:** `src/docsift/cli/commands/index.py:244-274`
**Issue:** `embed_cmd` deletes old chunks via `chunk_repo.delete_by_document(doc.id)` but never deletes the corresponding rows from `document_embeddings`. Because `document_embeddings` has no foreign key cascade (it is a virtual table or fallback table without FK constraints), stale embeddings accumulate indefinitely, bloating the database and polluting vector search results. The same issue exists in `DocumentRepository.delete` and `delete_by_collection`, and in `collection_remove`.
**Fix:** Delete existing embeddings for the document before adding new ones. Use a direct SQL delete or add a repository/vector searcher method.
```python
# Inside embed_cmd, before chunking:
cursor = db.connection.execute(
    "DELETE FROM document_embeddings WHERE document_id = ?",
    (doc.id,)
)
```
Also add equivalent cleanup to `DocumentRepository.delete`, `delete_by_collection`, and `collection_remove`.

## Warnings

### WR-01: Unused `Syntax` Import and Dead Conditional Branches

**File:** `src/docsift/cli/commands/get.py:10-11,108-111`
**Issue:** `from rich.syntax import Syntax` is imported but never used. The `if doc.path.endswith(".md"):` conditional has identical branches, making it dead code.
**Fix:** Remove the unused import and either implement syntax highlighting or remove the conditional.

### WR-02: Inconsistent Use of `Optional` Type Hint

**File:** `src/docsift/cli/commands/get.py:35-36`
**Issue:** `get_cmd` uses `from typing import Optional` and `Optional[int]` for `from_line` and `lines`. The project targets Python 3.9+ and uses `int | None` syntax everywhere else.
**Fix:** Replace `Optional[int]` with `int | None` and remove the `typing` import.

### WR-03: Missing `Any` Import in Type Annotations

**File:** `src/docsift/cli/commands/search.py:24`
**Issue:** `format_results_json` annotates `r: Any`, but `Any` is not imported. While `from __future__ import annotations` defers evaluation, type checkers and introspection tools will fail.
**Fix:** Add `from typing import Any` to the imports.

### WR-04: Unnecessary Local Imports Inside Same Module

**File:** `src/docsift/database/repositories.py:228,248`
**Issue:** `DocumentRepository.delete` and `delete_by_collection` locally import `DocumentChunkRepository` from `docsift.database.repositories` even though they are defined in the same module. This is unnecessary and risks circular import issues.
**Fix:** Remove the local imports and instantiate `DocumentChunkRepository(self.db)` directly.

### WR-05: Duplicate Commands (`include`/`exclude` vs `enable`/`disable`)

**File:** `src/docsift/cli/commands/collection.py:211-318`
**Issue:** `collection_enable`/`collection_disable` and `collection_include`/`collection_exclude` perform identical operations. This is code duplication that confuses the CLI surface.
**Fix:** Remove the duplicate pair or implement one pair as aliases to the other.

### WR-06: `VectorSearcher` Instantiated Inside Inner Loop

**File:** `src/docsift/cli/commands/index.py:267-268`
**Issue:** `VectorSearcher` is imported and instantiated inside the `for chunk in chunks` loop. This creates a new searcher object for every chunk, which is highly inefficient and indicates a logic placement error.
**Fix:** Move the import and instantiation outside the `for doc in documents` loop.

### WR-07: Stale Document Chunks Not Invalidated on Content Update

**File:** `src/docsift/cli/commands/index.py:120-133`
**Issue:** When `update_cmd` detects a changed document and updates it, the old chunks in `document_chunks` are left in place. The chunks table becomes out of sync with the document content until `embed_cmd` is run.
**Fix:** Delete existing chunks for the document during update, or mark them as stale.

### WR-08: Incorrect User-Facing Command Suggestions

**File:** `src/docsift/cli/main.py:95`, `src/docsift/cli/commands/search.py:116,243,358`
**Issue:** Error messages tell users to run `docsift update` and `docsift embed`, but the actual registered commands are `docsift index update` and `docsift index embed`.
**Fix:** Update the messages to reference the correct command names.

### WR-09: Byte Check Mismatched with Character Truncation

**File:** `src/docsift/cli/commands/get.py:186-187`
**Issue:** `multi_get_cmd` checks `len(content.encode()) > max_bytes` (byte length) but truncates using `content[:max_bytes]` (character count). A multi-byte document may still exceed `max_bytes` after truncation.
**Fix:** Truncate by encoded bytes, or switch the check to character length for consistency.

### WR-10: `--from-line 0` Treated as `--from-line 1`

**File:** `src/docsift/cli/commands/get.py:93`
**Issue:** `start = (from_line or 1) - 1` uses truthiness, so an explicit `--from-line 0` is coerced to `1`.
**Fix:** Use a ternary that respects `0`: `start = from_line - 1 if from_line is not None else 0`.

## Info

### IN-01: Local Imports Should Be Module-Level

**File:** `src/docsift/cli/commands/get.py:58,132`, `src/docsift/cli/commands/index.py:157,189,199,267`
**Issue:** `CollectionRepository`, `fnmatch`, `datetime`, `SentenceTransformer`, `VectorSearcher`, and `get_settings` are imported locally inside functions. Moving them to the top improves readability and avoids repeated import overhead.
**Fix:** Move imports to the top of their respective modules.

### IN-02: Redundant Local `FileScanner` Import

**File:** `src/docsift/cli/commands/collection.py:340`
**Issue:** `FileScanner` is already imported at the module level (line 17) but is imported again inside `collection_ls`.
**Fix:** Remove the local import.

### IN-03: Fragile Tree Node Comparison

**File:** `src/docsift/cli/commands/ls.py:63`
**Issue:** `next((c for c in node.children if str(c.label) == part), None)` relies on `str(c.label)` exactly matching the path part. If Rich ever wraps labels or applies styling to intermediate nodes, the comparison will fail.
**Fix:** Track nodes in a dictionary keyed by path part rather than relying on label string comparison.

### IN-04: CSV and XML Output Lack Proper Escaping

**File:** `src/docsift/cli/commands/search.py:31-72`
**Issue:** `format_results_csv` does not escape commas or quotes in titles/paths. `format_results_xml` does not escape XML special characters (`<`, `>`, `&`). Documents containing these characters will produce malformed output.
**Fix:** Use Python's `csv` module for CSV generation, and `xml.sax.saxutils.escape` for XML content.

---

_Reviewed: 2026-04-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
