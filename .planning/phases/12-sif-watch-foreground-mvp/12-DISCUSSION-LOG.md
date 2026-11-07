# Phase 12: `sif watch` Foreground MVP - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-07
**Phase:** 12-`sif watch` Foreground MVP
**Mode:** `--auto` (Claude selected recommended options; no interactive prompts)
**Areas discussed:** watch scope & lifecycle, flock discipline, event→work pipeline, `--embed` mechanics, missing-root protection, foreground UX & shutdown, test determinism

---

## Watch scope & collection lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| All collections by default + `-c` filter | Watch every registered collection root; repeatable flag narrows to a subset | ✓ |
| Explicit-only selection | Require `-c` per run; nothing watched by default | |
| Watch broader than collection roots | e.g. home dir (recoll monitordirs anti-pattern) | |

**User's choice:** [auto] Recommended default — all collections + `-c` filter; restart for collection-set changes in MVP; startup full reconcile pass.
**Notes:** Live rescope on `collection add/remove` deferred to Phase 13 daemon. Watch exactly registered roots, never broader.

---

## flock discipline for the resident writer

| Option | Description | Selected |
|--------|-------------|----------|
| Per work-burst acquire/release | Lock around each debounced batch; idle watch holds nothing | ✓ |
| Hold for process lifetime | Watch owns the lock from start to exit | |

**User's choice:** [auto] Recommended default — per-burst. Lifetime hold pushes `update`/`embed` past their wait deadline into "proceed unlocked", recreating LIVE-07's duplicate-embed race.
**Notes:** Watch is just another IncrementalIndexer invoker under the Phase 11 D-02/D-03 contract.

---

## Event→work pipeline

| Option | Description | Selected |
|--------|-------------|----------|
| Per-path targeted updates for bursts + startup full pass | Path as unit of work; stat → index or remove; cost proportional to burst | ✓ |
| Full `update_collection` pass per burst | Reuse proven loop verbatim; re-parses entire collection per save burst | |
| Per-path only, no startup pass | Cheapest; pre-watch drift stays stale until files change again | |

**User's choice:** [auto] Recommended default — hybrid. Full passes per burst burn CPU proportional to KB size per save (Pitfall 3); startup pass anchors freshness and correctness.
**Notes:** Per-path API designed for reuse by Phase 13 hosts and Phase 14 drift refresh. Exclusion predicate shared with `FileScanner` (single source of truth); `on_moved` filters on `dest_path`; editor-noise patterns added to `DEFAULT_IGNORE_PATTERNS`.

---

## `--embed` depth mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Per-file inline under per-burst lock, lazy model load | BM25 commit → embed outside txn → short vector txn; model loads on first embed work | ✓ |
| Batch embed after burst settle | Collect changed files, embed together | |
| Delegate to `embed_cmd` collection pass | Watch triggers the existing command per collection | |

**User's choice:** [auto] Recommended default — per-file inline (Phase 11 D-05's locked direction).
**Notes:** Accepted trade-off: large embed bursts hold the lock longer; concurrent `update_cmd` may wait past deadline — acceptable post-debounce; Phase 13 can split if it bites. Without `--embed`, vectors purge on change; staleness markers are Phase 14 (QUAL-06).

---

## Missing-root protection

| Option | Description | Selected |
|--------|-------------|----------|
| Core guard + watcher re-stat/reschedule | Skip-with-warning (never sweep) in IncrementalIndexer; periodic re-stat, reschedule + reconcile on return | ✓ |
| Watcher-level guard only | Watcher skips missing roots; update_cmd keeps its latent mass-delete bug | |
| Treat as user error | Document "don't unmount while watching" | |

**User's choice:** [auto] Recommended default — both levels. Core guard also fixes the existing `update_cmd` mass-delete-on-missing-root latent bug.
**Notes:** Warn once per transition, not per poll.

---

## Foreground UX & shutdown

| Option | Description | Selected |
|--------|-------------|----------|
| Progress-event protocol + per-batch summaries | Reuse Phase 11 `"code payload"` events; banner with roots/mode/debounce; `--verbose` per-file | ✓ |
| Stream every event raw | Log every filesystem event as it arrives | |
| Silent unless error | Minimal output; summaries only on failure | |

**User's choice:** [auto] Recommended default — per-batch summaries via the existing event protocol.
**Notes:** SIGINT/SIGTERM: flush in-flight batch (bounded), release lock, `wal_checkpoint(TRUNCATE)`, exit 0; second signal exits immediately.

---

## Test determinism

| Option | Description | Selected |
|--------|-------------|----------|
| Synthetic events + manual debounce flush + 1–2 real-FS e2e | Construct watchdog event objects directly; deterministic by construction; serialized e2e with generous timeouts | ✓ |
| Real-FS timing tests throughout | Real observers + sleeps everywhere | |
| Unit-only, no real-observer coverage | Fast but never proves the real event chain | |

**User's choice:** [auto] Recommended default — synthetic-first (Phase 11 D-08/D-09 culture), plus 1–2 real-FS end-to-end proofs.
**Notes:** Never sleep-polling without a deadline.

---

## Claude's Discretion

CLI surface details beyond `-c`/`--embed`/`--verbose` naming; per-path API shape on IncrementalIndexer; debounce default value; missing-root re-stat interval; watcher module rewrite (known skeleton lifecycle gaps); burst/queue/worker internals; where the shared exclusion predicate lives.

## Deferred Ideas

- Live rescope on collection add/remove mid-run — Phase 13
- Embed compute split outside the flock window — Phase 13 if D-10's trade-off bites
- Periodic wal_checkpoint during long runs — Phase 13
- inotify watch-limit detection + PollingObserver fallback UX — Phase 13 (Linux daemon testing)
