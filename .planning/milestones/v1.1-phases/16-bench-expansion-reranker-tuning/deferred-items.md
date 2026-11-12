# Deferred Items

- Stale `Search Models` section in `docs/api-reference.md` (SearchQuery / SearchResult / SearchResponse blocks and the `from sif.models.search import ...` header describe a module that does not exist; the real models live in `sif.core.models`).
  **Status:** resolved
  Resolved 2026-11-11 by quick task 261111-kn2 — stale as written: src/sif/models/search.py exists and the documented SearchQuery, SearchResult, SearchOptions, and SearchType imports succeed; docs/api-reference.md intentionally remains unchanged.
  **What:** Pre-existing doc drift adjacent to this plan's api-reference edits — 16-05 replaced only the `SearchOptions` block (the surface it needed to carry the new fields) and added the Benchmark Module section; rewriting the whole stale section is out of the plan's file scope.
  **Where:** `docs/api-reference.md`, `## Models Module`.
