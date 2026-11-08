# Deferred Items

- Stale `Search Models` section in `docs/api-reference.md` (SearchQuery / SearchResult / SearchResponse blocks and the `from sif.models.search import ...` header describe a module that does not exist; the real models live in `sif.core.models`).
  status: open
  **Status:** open
  **What:** Pre-existing doc drift adjacent to this plan's api-reference edits — 16-05 replaced only the `SearchOptions` block (the surface it needed to carry the new fields) and added the Benchmark Module section; rewriting the whole stale section is out of the plan's file scope.
  **Where:** `docs/api-reference.md`, `## Models Module`.
