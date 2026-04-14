# Phase 1: Foundation Fix - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-14
**Phase:** 01-foundation-fix
**Areas discussed:** FTS5 Synchronization, Repository Consolidation, SQLite Connection Safety, Vector Search Fallback

---

## FTS5 Synchronization

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite triggers auto-sync | Create INSERT/UPDATE/DELETE triggers in SchemaManager to keep FTS5 tables synchronized automatically. | ✓ |
| Repository explicit sync | Handle FTS5 inserts/updates/deletes manually inside repository methods. | |

**User's choice:** SQLite triggers auto-sync
**Notes:** Chosen for reliability — no risk of missing a code path that forgets to update FTS5.

---

## Repository Consolidation

| Option | Description | Selected |
|--------|-------------|----------|
| Unify to repositories.py | Merge sqlite_repository.py functionality into repositories.py, then delete the duplicate. | ✓ |
| Unify to sqlite_repository.py | Migrate CLI and search layers to sqlite_repository.py, then delete repositories.py. | |

**User's choice:** Unify to repositories.py
**Notes:** repositories.py is already used by CLI and search layers; minimizes migration churn.

---

## SQLite Connection Safety

| Option | Description | Selected |
|--------|-------------|----------|
| Connection-per-request | CLI uses Database.transaction(); async contexts create a new Connection per request. | ✓ |
| Thread-local storage | Cache connections per thread via threading.local(). | |
| Connection pool | Introduce a sqlite3 connection pool. | |

**User's choice:** Connection-per-request
**Notes:** Simplest and safest for current project scale.

---

## Vector Search Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Hard requirement on sqlite-vec | Remove brute-force Python fallback entirely; fail fast if sqlite-vec is unavailable. | ✓ |
| Capped fallback | Allow Python fallback only for small indexes (e.g., ≤1000 chunks). | |

**User's choice:** Hard requirement on sqlite-vec
**Notes:** Cleanest code path; avoids silent performance degradation.

---

## Deferred Ideas

None — discussion stayed within phase scope.
