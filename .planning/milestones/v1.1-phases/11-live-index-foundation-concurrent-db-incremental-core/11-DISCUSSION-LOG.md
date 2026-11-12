# Phase 11: Live-Index Foundation (Concurrent DB + Incremental Core) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-07
**Phase:** 11-Live-Index Foundation (Concurrent DB + Incremental Core)
**Areas discussed:** Arbitration semantics, Write granularity, Connection consolidation, Concurrency test depth

---

## Arbitration semantics

### Q1: What should the flock single-writer lock cover?

| Option | Description | Selected |
|--------|-------------|----------|
| Indexer + embed | flock guards every long-running write job (index update, MCP index tool, embed_cmd); short CRUD writers stay outside under busy_timeout + BEGIN IMMEDIATE | ✓ |
| IncrementalIndexer only | Narrowest match to SC2; embed running concurrently can still BUSY-fail after 5s during long embeds | |
| All write paths | Serializes collection CRUD and context writes too — lock chatter for operations busy_timeout already covers | |

**User's choice:** Indexer + embed
**Notes:** embed holds the write lock for an entire collection (locked Phase 03 decision); arbitration prevents a concurrent update from erroring after busy_timeout.

### Q2: When a second writer finds the lock held, what does it do?

| Option | Description | Selected |
|--------|-------------|----------|
| Wait then run | Loser try-flocks, waits up to a configurable timeout (~30s) for the winner, then runs its own pass; never drops distinct work | ✓ |
| Skip with notice | Research's daemon-era model — immediate exit 0, but `update -c B` would skip while collection A runs | |
| Fail non-zero | Safest for scripts, but breaks the daemon-era flow where pre-command checks and MCP refresh must defer silently | |

**User's choice:** Wait then run
**Notes:** The different-collection case (`update -c A` vs `update -c B`) motivated wait over skip.

### Q3: One global lock per database, or per-collection locks?

| Option | Description | Selected |
|--------|-------------|----------|
| Global per-DB | One lock file next to the DB (0600); daemon holds ONE lock, everything defers to it; matches research and LIVE-07 wording | ✓ |
| Per-collection locks | Parallel updates of different collections, but N locks for Phases 12–14 hosts and "is a watcher running?" becomes a set query | |

**User's choice:** Global per-DB
**Notes:** Different-collection updates queue behind wait-then-run instead of running in parallel.

---

## Write granularity

### Q1: What transaction scope should the extracted IncrementalIndexer use?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-file | Each file's document + chunks + FTS writes commit as one short BEGIN IMMEDIATE transaction; resumable; identical final index on success | ✓ |
| Per-collection | Mirrors embed_cmd's locked Phase 03 pattern; longer lock holds but usually seconds (BM25 only) | |
| Whole-run (status quo) | Today's exact semantics — entire run one transaction; defeats the point of short upfront write locks | |

**User's choice:** Per-file
**Notes:** Only failure semantics change (mid-run crash keeps progress instead of whole-run rollback); SC3 identical-results holds for successful runs.

### Q2: Does embed_cmd's per-collection transaction get revisited in Phase 11?

| Option | Description | Selected |
|--------|-------------|----------|
| Leave as-is | flock absorbs the concurrency pain; Phase 03 CR-02 semantics stay locked; Phase 12 --embed gets per-file via IncrementalIndexer | ✓ |
| Split embed now | Fully fixes the research perf trap but rewrites locked Phase 03 behavior and widens the blast radius beyond SC3/SC4 | |

**User's choice:** Leave as-is
**Notes:** None.

---

## Connection consolidation

### Q1: One shared connection factory, or pragma blocks at each existing site?

| Option | Description | Selected |
|--------|-------------|----------|
| Unify to one | Shared factory (pragma block + sqlite-vec + bounded first-open retry) in one place; Database (CLI) and DatabaseConnection (MCP) route through it | ✓ |
| Patch each site | Smallest diff, but three copies of the recipe that future sites (Phase 13 daemon) must remember to copy | |

**User's choice:** Unify to one
**Notes:** The 1015-test suite at 96.2% is the safety net for the refactor.

### Q2: What happens to the dead connection code (ConnectionPool + duplicate DatabaseConnection)?

| Option | Description | Selected |
|--------|-------------|----------|
| Retire both | Delete ConnectionPool (zero real callers) and duplicate DatabaseConnection in database.py:108; consistent with retiring dead DocumentIndexer | ✓ |
| Retire pool only | Keep both DatabaseConnection classes; safer if external code imports the database.py one | |
| Keep everything | Leave dead pieces; two same-named classes and a WAL-bypassing pool remain as traps | |

**User's choice:** Retire both
**Notes:** None.

---

## Concurrency test depth

### Q1: How should SC1/SC2 concurrency guarantees be proven in the test suite?

| Option | Description | Selected |
|--------|-------------|----------|
| Both layers | In-suite real connections/threads vs file DB in tmp_path + 2–3 subprocess-level two-writer tests; deterministic by construction | ✓ |
| In-suite only | No subprocess flakiness, full coverage credit, but SC2's "two processes" only simulated | |
| Subprocess only | Strongest literal proof, but coverage-thin and slow feedback | |

**User's choice:** Both layers
**Notes:** Parent holds/releases the lock and asserts the child's outcome — never timing-race assertions.

### Q2: Where do the subprocess concurrency tests live?

| Option | Description | Selected |
|--------|-------------|----------|
| In default run | Part of plain `pytest` (fail_under=90 stays honest), serialized, generous timeouts (30s+), no deadline-less sleep-polling | ✓ |
| Marked + CI-only | Zero flake risk for daily runs, but the concurrency proof can silently rot if the CI step is skipped | |

**User's choice:** In default run
**Notes:** None.

---

## Claude's Discretion

- Lock file exact name/path derivation (next to DB, 0600)
- Wait-timeout default value and its `SIF_` settings field name (~30s suggested)
- Connection factory module placement and internal API shape
- `IncrementalIndexer` class/API shape (must carry added/updated/removed counts for identical CLI output)
- Subprocess test implementation details (deterministic + serialized)
- Bounded first-open/DDL retry bounds
- CLI wait-notice wording; winner/loser exit codes (both 0 on success)

## Deferred Ideas

None — discussion stayed within phase scope.
