# Deferred Items — Quick Task 261105-g1u

## Group callback creates the index parent directory unconditionally (out-of-scope discovery)

- **Found during:** Task 1 manual spot-check (2026-11-05).
- **Behavior:** `cli` group callback in `src/sif/cli/main.py` runs
  `ctx.obj["index_path"].parent.mkdir(parents=True, exist_ok=True)` on every
  invocation, so `sif --index /tmp/missing/sif.db context add ...` prints
  "No index found." and creates no DB file (WR-03 fix intact) but still
  creates the empty parent directory.
- **Pre-existing:** `context list` (guarded since Phase 05) behaves
  identically — the mkdir predates this task and applies to every command,
  including index-creating ones that legitimately need it.
- **Why deferred:** Changing group-level mkdir semantics (e.g., only create
  the parent on write commands) affects all commands and is an architectural
  decision beyond WR-03's finding (empty index DB materialization). Not
  auto-fixed per scope boundary.
- **Candidate follow-up:** move/gate the mkdir to commands that actually
  create the index (`index update`, `collection add`, ...).
