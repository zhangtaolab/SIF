---
status: resolved
trigger: E2E verification found 3 bugs after project rename from DocSift to SIF
created: "2026-04-27"
updated: "2026-04-27"
---

# Debug: E2E Get and Stats Bugs

## Symptoms

### Bug 1: sif get by short filename fails
- **Expected:** `sif get readme.md` retrieves the document
- **Actual:** `sif get readme.md` fails; `sif get /full/path/readme.md` works
- **Error:** Path resolution issue -- short filenames not resolved to full paths

### Bug 2: sif multi-get by short filenames fails
- **Expected:** `sif multi-get file1.md,file2.md` retrieves multiple documents
- **Actual:** Fails -- same root cause as Bug 1 (path resolution)

### Bug 3: collection show reports Documents: 0 after indexing
- **Expected:** `sif collection show <name>` shows correct document count after indexing
- **Actual:** Reports `Documents: 0` even though indexing completed successfully
- **Error:** Stats not refreshed after indexing

### Reproduction
1. Create a collection and index some markdown files
2. Run `sif get <short-filename>` -- fails
3. Run `sif get /full/path/to/<filename>` -- works
4. Run `sif collection show <name>` -- shows Documents: 0

### Timeline
- Appeared during E2E verification after Phase 08 (project rename from DocSift to SIF)
- All 377 unit tests pass -- these bugs are not covered by existing tests

## Current Focus

- **hypothesis:** Three distinct root causes confirmed
- **next_action:** resolved

## Evidence

- timestamp: 2026-04-27 investigation
  file: src/sif/cli/commands/get.py (lines 54-64)
  finding: >
    Bug 1 & 2: get_cmd and multi_get_cmd only try exact path match via
    doc_repo.get_by_path(path_or_docid, coll.id). The paths stored in DB
    are absolute (e.g. /Users/forrest/docs/readme.md) but users type short
    filenames like "readme.md". No fallback to match by filename column.

- timestamp: 2026-04-27 investigation
  file: src/sif/database/repositories.py (lines 111-127)
  finding: >
    Bug 3: CollectionRepository._row_to_collection() does not read
    document_count or chunk_count from the database row. These fields exist
    in the collections table but are silently dropped during row-to-object
    conversion. Every time a Collection is loaded, counts reset to 0.

- timestamp: 2026-04-27 investigation
  file: src/sif/core/models.py
  finding: >
    Collection dataclass has no mark_indexed() method. The DocumentIndexer
    class calls collection.mark_indexed() which would raise AttributeError.
    This code path is not exercised by the CLI (which uses its own inline
    indexing in update_cmd), so it does not cause a runtime error, but it
    is a latent bug.

## Eliminated

- Not a rename issue -- these bugs predate the DocSift->SIF rename

## Resolution

### root_cause
Three bugs: (1) get/multi-get only match by exact absolute path, no filename fallback; (2) _row_to_collection drops document_count/chunk_count from DB rows; (3) DocumentIndexer calls nonexistent mark_indexed() method.

### fix
Applied three fixes across four files:

1. **src/sif/database/repositories.py** -- Added `DocumentRepository.get_by_filename()` method (queries by filename column across all collections). Fixed `CollectionRepository._row_to_collection()` to include `document_count` and `chunk_count` from the database row.

2. **src/sif/cli/commands/get.py** -- Added filename-based fallback in `get_cmd` after path lookup fails. Refactored `multi_get_cmd` to use a shared `_lookup_by_id_or_path_or_filename` helper that tries ID, then path, then filename.

3. **src/sif/core/models.py** -- Added `mark_indexed()` method to `Collection` dataclass that sets `last_indexed_at` and `updated_at`.

4. **tests/unit/cli/test_get.py** -- Updated `test_multi_get_no_match` to mock `get_by_filename` returning None (avoids MagicMock truthy default). Added `test_multi_get_by_filename` to cover the new filename lookup path.

All 378 tests pass.
