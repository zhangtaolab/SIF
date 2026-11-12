# Pitfalls Research

**Domain:** Live file-watching incremental indexing + search-quality tuning, added to an existing local hybrid search engine (Python, SQLite FTS5 + sqlite-vec, watchdog, Click CLI + MCP server, PyPI pure-Python package)
**Researched:** 2026-11-07
**Confidence:** HIGH for codebase-grounded and official-doc-backed findings; MEDIUM for community cross-verified findings (per-claim levels in Sources, aligned to the classify-confidence seam)

Research was grounded against the actual SIF codebase (`src/sif/indexing/watcher.py`, `src/sif/indexing/indexer.py`, `src/sif/database/connection.py`, `src/sif/search/hybrid.py`, `src/sif/search/rrf.py`, `src/sif/search/benchmark.py`, `src/sif/mcp/transports/http.py`) — several pitfalls below cite the exact line of code that will trigger them.

## Critical Pitfalls

### Pitfall 1: Shipping the watcher on a database with no WAL and no busy_timeout — instant "database is locked"

**What goes wrong:**
The moment a background watcher writes while an MCP search reads (or two CLI commands overlap), operations fail with `sqlite3.OperationalError: database is locked` — immediately, with no retry. Long embed jobs make it worse: in rollback-journal mode (SQLite default) a writer blocks **all readers** for the entire write transaction, so a multi-minute `--embed` update makes every concurrent `sif search` / MCP query hang or error.

**Why it happens:**
`DatabaseConnection._create_connection()` (`src/sif/database/connection.py:24-37`) sets `PRAGMA foreign_keys` but never `journal_mode=WAL` nor `busy_timeout`. SQLite's defaults are actively hostile to concurrency: journal mode DELETE (writer blocks readers), `busy_timeout=0` (first lock collision returns `SQLITE_BUSY` with zero wait). Every connection SIF opens today — and there are many, since `execute()`/`fetchall()` open a fresh connection per operation — has these defaults. Single-user batch CLI usage never exposed this; a resident watcher will on day one. One historical landmine: an early SIF decision made `embed_cmd` run **one transaction per collection** — under WAL that transaction holds the single write lock for the entire collection embed.

**How to avoid:**
- `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=5000` on **every** connection (it is a per-connection setting, so it belongs in `_create_connection()` and in `ConnectionPool.get_connection()`). WAL persists in the DB file once set. Verified compatible with sqlite-vec `vec0` tables (llama-stack ships exactly this fix; sqlite-vec itself added WAL concurrency tests by v0.1.10-alpha.2).
- Keep write transactions short: compute embeddings **outside** the transaction, then commit document+chunks+FTS trigger updates in one fast transaction. Never hold a write transaction across an embed call.
- Start write transactions with `BEGIN IMMEDIATE` (or `sqlite3`'s isolation handling equivalent) — a deferred read-then-write transaction upgrade failure returns `SQLITE_BUSY` that `busy_timeout` cannot absorb.
- Bound concurrent writers to one watcher process (see Pitfall 5 single-instance enforcement).
- Note WAL caveats: does not work on network filesystems (fine — the DB lives in the platform data dir), readers prevent checkpoint completion ("checkpoint starvation") — acceptable for a local tool, but a long-lived MCP connection that holds a read snapshot open can grow the `-wal` file.

**Warning signs:**
- `OperationalError: database is locked` in any test that runs search while indexing; intermittent MCP search failures when watch is on; `-wal` file growing unboundedly.
- In CI: any test that opens two `Database` objects concurrently fails today — that test currently cannot exist.

**Phase to address:**
The **first Live Index phase (`sif watch` MVP)** — this is a precondition, not a follow-up. Every later live-index form (MCP-embedded, daemon, pre-command) inherits it.

---

### Pitfall 2: Treating a save as a "modify" event — macOS atomic-write rename chains

**What goes wrong:**
On macOS, most editors (TextEdit-style `.sb-` saves, and many apps built on the same NSDocument machinery) save by **write-temp-then-rename**: the handler sees `FileMovedEvent(file.md → file.md.sb-XXXX)`, `FileDeletedEvent(file.md.sb-XXXX)`, `FileCreatedEvent(file.md)`, `FileModifiedEvent(file.md)` — *never* a simple modify on the original path. A watcher that only acts on `on_modified` misses these saves entirely. Conversely, a handler that treats the `FileMovedEvent` src as "file moved away" and deletes it from the index, then re-adds on `FileCreatedEvent`, churns the index (delete + re-embed) on **every single save**. Vim is the opposite case: it writes in-place (`backupcopy`) and fires modify events — but also creates `.foo.md.swp`, `4913`, and backup files that must not be indexed.

**Why it happens:**
`watcher.py` dispatches each event type independently (`on_created`/`on_modified`/`on_deleted`/`on_moved`) with no reconciliation — each handler comment says "Trigger incremental index" and there is no state to tie the event chain together. Developers test with `echo hi > note.md` (clean modify event) and never with a real editor save. Watchdog's own issue #538 documented exactly this confusion ("I end up with no file") — pre-4.0 watchdog even emitted the events in the wrong order.

**How to avoid:**
- Make the **path, not the event**, the unit of work: accumulate events per path, debounce (Pitfall 3), then reconcile against ground truth — stat the path; if it exists and checksum changed → re-index; if gone → tombstone. SIF's per-file sha256 skip makes reconciliation cheap and idempotent.
- Handle `on_moved` by checking `dest_path` against the extension filter (dest is the real signal for renames into a watched dir), and never index paths matching temp-file patterns (`.swp`, `.sb-*`, `~`, `.#`, `4913`, `.DS_Store`, `.tmp`).
- Require watchdog >= 4.x (inode-paired FSEvents handling, PRs #750/#754); `pyproject.toml` currently pins `watchdog>=3.0.0` — bump it.
- Test with real save chains: a fixture test that emits the documented TextEdit sequence (moved→deleted→created→modified on the same path) must produce exactly one re-index and zero spurious deletes.

**Warning signs:**
- "I saved the file but search returns the old text" (missed saves); index statistics showing add+delete pairs per save; `.sb-` or `.swp` files appearing in indexed document lists.

**Phase to address:**
`sif watch` MVP phase (the event→index pipeline is built there and reused everywhere).

---

### Pitfall 3: No debounce — editor save storms and whole-file re-embeds per keystroke

**What goes wrong:**
Editors like Obsidian write the file many times during one editing session (autosave per pause); sync tools rewrite hundreds of files in bursts; a `git checkout` fires events for every changed file plus the entire `.git` internals tree. Without coalescing, each burst event triggers parse → chunk → (with `--embed`) a model inference. The result is CPU burn, laptop fans, SQLite write churn, and — with the Qwen3 embedder — seconds of inference **per keystroke pause**.

**Why it happens:**
The naive pattern (call the indexer directly inside the event handler, which is what `watcher.py` is shaped to do) has no concept of time. Debounce feels like an optional polish item, so it gets deferred, and the watcher "works" in demos.

**How to avoid:**
- Per-path trailing debounce: a `dict[path, timer]`; each event resets the timer; only when a path is quiet for N ms (community-consistent values: 300–500 ms) does it enter the work queue. Process the queue serially (one worker), deduping repeated paths — SIF's checksum-skip then makes BM25-only updates nearly free and embed updates exactly one per settled save.
- Add a **settle check** on the changed path only (two consecutive `stat` size+mtime readings equal) before reading — events fire at the *start* of a write (Pitfall 6). Critically, do **not** poll the whole tree for write-completion: a chokidar-based project (openclaw PR #81802) exhausted file descriptors polling every watched file (EBADF on child spawns) on large Markdown trees; settle only the paths that emitted events (O(N)→0 held FDs).
- On macOS, watchdog >= 7 exposes the FSEvents `latency` kwarg (previously hard-coded 10 ms); raising it lets the OS coalesce duplicates before they even reach the queue.
- Keep `.git` (and any collection ignore patterns) out of the watch scope entirely (Pitfall 4) rather than filtering events after the fact.

**Warning signs:**
- Log lines showing multiple index events for one save; CPU usage of the watch process staying above ~20% while a note is open in an editor; `files_updated` counters an order of magnitude above actual edits.

**Phase to address:**
`sif watch` MVP phase (debounce is load-bearing from the first commit of the watcher wiring, not a tuning knob to add later).

---

### Pitfall 4: Silent watch loss and missed deletes — recursive watch limits and unfiltered watch scope

**What goes wrong:**
On Linux, `Observer.schedule(handler, path, recursive=True)` allocates one inotify watch **per subdirectory**. Kernel `fs.inotify.max_user_watches` defaults to 8,192 (older kernels; RAM-scaled up to ~1M on 5.11+). A notes tree containing a `node_modules`, a `.venv`, or simply many subdirs blows the limit — and **recursive-watch exhaustion fails silently**: events from some subtrees simply never arrive (notify issue #109; non-recursive watches at least raise the cryptic `ENOSPC: No space left on device`). Independently, event-queue overflow (`IN_Q_OVERFLOW`) makes the kernel **discard events** (Watchman's answer is a full recrawl; it treats an un-watchable dir as a poisoned state requiring process restart). Meanwhile watchdog schedules the recursive watch over *everything* under the root — SIF's scanner ignores `.git` and collection `ignore_patterns`, but `watcher.py`'s `_should_handle` only checks extensions, so (a) the kernel burns watches on subtrees SIF will never index, and (b) live events bypass collection ignore rules entirely — a file excluded by `private/**` at scan time gets indexed the moment it's saved.

**Why it happens:**
"Ignore" is implemented as event filtering instead of watch-scope shaping, and nobody tests on a tree with 10k directories. Watchdog also has lifecycle traps in the current skeleton: `FileWatcher.stop()` removes the handler from a dict but never calls `observer.unschedule()` (the watches keep firing into a handler map that watchdog still holds — fixed upstream only in v7's `dispatch_events`), and `start()` overwrites `self._observer` without stopping a previous one.

**How to avoid:**
- Shape the **watch scope**: exclude scanner-ignored directories (`.git`, `node_modules`, collection `ignore_patterns`) from what gets scheduled/watched (watchdog supports per-watch patterns; on Linux this is what actually conserves watch descriptors), and reuse `FileScanner`'s exact ignore logic for event filtering so live and scan behavior can't diverge.
- Handle `on_deleted`/`on_moved`-out as first-class tombstones (remove doc + chunks + vectors in one transaction); a missed delete leaves a permanently stale document that no scan will fix unless a full `index update` runs.
- Install an overflow/error recovery path: watchdog's `ObservableQueue` + emitter exceptions should trigger (a) a logged warning and (b) a bounded full rescan of affected collections (checksum-skip makes rescan cheap), never silent swallowing.
- Log the number of watches/directories at startup; on Linux, detect ENOSPC and print the `sysctl fs.inotify.max_user_watches` remediation.
- Fix the skeleton lifecycle: `stop()` must `unschedule_all()`/join; `start()` must not orphan an existing observer.

**Warning signs:**
- "Changes in `notes/sub/x.md` never show up but `notes/y.md` does" (the classic partial-silent-failure signature); documents in the index that no longer exist on disk; watcher log silent during a `git checkout`.

**Phase to address:**
`sif watch` MVP phase (scope shaping + tombstones) and revisited in the **daemon phase** (long-running exposure is where silent loss compounds — a daemon that has silently lost watches for a week is the worst-case variant).

---

### Pitfall 5: Daemon lifecycle — stale PID files, orphaned watchers, and the double-writer

**What goes wrong:**
Three failure classes, all field-proven: (1) **Stale PID file**: daemon crashes or is SIGKILLed (OOM), PID file remains, next start treats it as a live conflict and refuses to start — under systemd `Restart=on-failure` this loops to `StartLimitBurst` and the service stays dead until a human deletes the file (exact incident: Hermes gateway #13655). (2) **Orphaning**: `--detach` without proper session detach (setsid), signal handling, or parent-death semantics leaves a watcher process consuming CPU with no controlling way to find or stop it; on shutdown it may be mid-transaction. (3) **Double-writer**: `sif watch --detach` daemon + MCP-embedded watch + command-pre auto-check all alive simultaneously — three processes racing to index the same file (WAL serializes the writes so nothing corrupts, but embedding work triples, and CPU/battery pays for it).

**Why it happens:**
PID-file-checked-without-liveness is the textbook shortcut; `os.kill(pid, 0)` liveness validation + `flock` feel like over-engineering until the restart-loop incident. Double-writer happens because each live-index form (foreground, MCP, daemon, pre-command) is built in a separate phase and each "just checks" whether indexing is needed without a shared mutual-exclusion mechanism.

**How to avoid:**
- Single-instance lock via **kernel flock** on a lock file (e.g. next to the DB): the kernel releases it on death, making stale locks impossible; `flock` also arbitrates the double-writer case (daemon holds it; MCP-embedded watch and pre-command checks detect a running watcher and skip). If a PID file is kept for operator convenience, validate with `os.kill(pid, 0)` (`ProcessLookupError` → stale, delete and continue; `PermissionError` → alive but not ours), write it `0600`, and store a process signature (starttime/cmdline hash) to defeat PID recycling.
- SIGTERM/SIGINT handlers must drain gracefully: finish the current file's transaction, stop the observer, release the lock, remove the PID file. SIGKILL cannot be trapped — flock is the backstop.
- For launchd/systemd: run **in the foreground** (`Type=simple`), let the supervisor own restart/PID/logging (macOS LaunchAgent with `RunAtLoad`/`KeepAlive`; systemd user unit with `Restart=on-failure`). Do **not** double-fork under a supervisor — it breaks supervision. `--detach` (self-daemonize) is the fallback for no-supervisor users; generate the plist/unit files rather than documenting them by hand.
- Correct exit codes matter for supervisors; a clean stop exits 0.

**Warning signs:**
- "ERROR: already running with PID …" after any crash; `ps` showing two `sif watch` processes; watch daemon surviving terminal close but unkillable by the documented stop command; systemd start-limit hits.

**Phase to address:**
**Daemon phase** (`--detach`/launchd/systemd) for PID/flock/signals; but the **flock-based single-writer arbitration** must be designed in the watch MVP phase (cheap then, a compatibility headache once three watch forms exist) and consumed by the MCP-embedded and pre-command phases.

---

### Pitfall 6: Reading a file mid-write — indexing truncated content

**What goes wrong:**
Filesystem events fire at the **beginning** of a write, not the end. A handler that immediately reads the file can read a half-written document: the truncated content gets chunked, embedded (paying inference cost), stored, and — worse — the sha256 checksum of the truncation gets persisted, so the *next* event for the same logical save may or may not match. Windows is particularly prone (tailwind observed empty reads); large notes and slow disks make the window real everywhere.

**Why it happens:**
The event feels like a completion notification. It isn't. Also, mtime looks like a natural stability check, but copy/sync tools preserve source mtimes and clocks differ across machines — a freshly-synced file can carry an hours-old mtime.

**How to avoid:**
- Debounce (Pitfall 3) plus a settle check on the changed path only: two consecutive `stat()` calls (size + mtime) agree before reading. A single unchanged reading is not proof — writers pause.
- After reading, SIF already computes sha256 — treat that as the completeness gate it is: if a file yields zero parseable content but non-zero size, log and retry on the next event rather than persisting.
- Measure "age" from first-seen (your clock), never from file mtime.

**Warning signs:**
- Documents whose indexed content is visibly truncated or empty; checksum mismatch churn (same file re-indexed twice in quick succession); flaky bench numbers on freshly written fixtures.

**Phase to address:**
`sif watch` MVP phase (it lives inside the debounce→read step).

---

### Pitfall 7: Tuning hybrid weights/RRF k on a tiny bench fixture and shipping them as defaults

**What goes wrong:**
The bench fixture grows to 20–30 hand-written queries; BM25/vector weights and RRF k are swept until metrics look best; the tuned config ships as (or becomes) the recommended default. It then fails on real queries: measured case study — hand-tuned weighted fusion beat untuned RRF on the 20 tuning queries (Recall@10 0.91 vs 0.85) and **collapsed on 30 held-out queries (0.68 vs 0.79)**. With query counts this small, a two-point metric improvement can be driven by one query. A related trap: weights tuned for one k are invalid at another k — Qdrant's tuning guide is explicit that k must be settled first, and that on 300 queries (SciFact) *no* fusion config had a bootstrap interval excluding zero — sometimes the right answer is the default you already have.

**Why it happens:**
The milestone makes weights configurable, configuration invites tuning, tuning needs a fixture, and the fixture is the only labeled data around. "A one-parameter model overfit to 20 points is still overfit." SIF's current bench is a user-supplied JSON of `queries`/`relevant_docids` — exactly the shape where this happens.

**How to avoid:**
- Make the **default** the explicitly-evaluated baseline: bench must compare (BM25-only, vector-only, RRF default k=60 unweighted, candidate-weighted) and a weight change only replaces the default if it wins on **held-out** queries. Build the split into the bench command (`--tune-split` / auto 70/30) so leakage is structurally hard.
- Expand the fixture to ≥50 queries (guides say 50–200) across query *types* (exact token, paraphrase, natural-language, typo) before any tuning claim; per-type slices expose where weights help vs hurt.
- Report paired per-query deltas and query counts, not just averaged metrics; a global average hides "helped 18 keyword queries, broke 2 semantic ones."
- Choose k from relevant-docs-per-query in the fixture (~1 relevant doc → small k; many → larger k), then sweep weights at that k.
- Remember the pipeline shape: when the reranker runs after fusion, fusion should be tuned for **recall@candidate-K** (feed the reranker good candidates), not final precision.

**Warning signs:**
- Weight defaults that came out of a sweep on the dev fixture; bench metrics that improve on every tuning run; fixture queries phrased with the same vocabulary as the notes (self-matching); nobody can state the held-out number.

**Phase to address:**
**Bench expansion phase must precede/accompany the hybrid-weights phase** — the roadmap should order bench expansion first (it is the measurement instrument for everything else in Search Quality).

---

### Pitfall 8: Benchmark leakage — the same fixture tuned on, reported on, and enshrined in tests

**What goes wrong:**
Distinct from overfitting: the tuned weights plus their fixture both land in the repo; CI then asserts bench metrics against that fixture, so the numbers are forever circular. Any future tuning iterates against the same fixture until it's exhausted — the fixture becomes the spec. A second leakage vector: relevance labels generated by *running the current search* and keeping the top results ("it found what it finds") — the ground truth is the system under test.

**Why it happens:**
Hand-labeling relevance is tedious; generating labels from search output is easy and looks rigorous. And once a fixture drives a CI gate, nobody dares change it.

**How to avoid:**
- Version fixtures and split roles: `fixtures/tuning.json` vs `fixtures/heldout.json`, with heldout excluded from sweeps and CI asserts scoped to *regression bands* (metric ≥ floor), not exact values.
- Label relevance from document identity/independent judgment (the human read the note and knows it answers the query), never from the engine's own output.
- Record tuning provenance: which fixture version + split produced the shipped defaults, in the bench output itself.
- Rotate/grow heldout when the corpus shifts (optimal weights drift with content).

**Warning signs:**
- PRs that "improve" bench by editing the fixture; CI bench assertions with golden numbers; labels that perfectly match current top-10 results.

**Phase to address:**
**Bench expansion phase** (structure the corpus of fixtures right the first time; retrofitting splits after weights exist reopens every decision).

---

### Pitfall 9: Reranker latency on CPU breaks interactive search and MCP tool budgets

**What goes wrong:**
Qwen3-Reranker (SIF's default) scores each (query, chunk) pair with a full causal-LM forward pass. Measured on CPU: ~0.6–1 s **per candidate**; 20–30 candidates = 34–49 s per query (this is not hypothetical — it is issue #264 on **qmd, the project SIF ports**, reporting exactly this against qwen3-reranker-0.6b; M1 Pro: ~580 ms/candidate, 18 candidates ≈ 10.4 s; another CPU run: 10 docs = 2.6 s, 50 = 13.8 s, 100 = OOM/crash at ~4 GB). An MCP assistant that calls `query` on every collection multiplies it further. "Reranker tuning (threshold/latency)" tuned for quality alone will produce a configuration nobody can use.

**Why it happens:**
Threshold sweeps measure score distributions, not wall-clock. Latency scales with candidates × context length, and the reranker batch size setting (default 32) encourages feeding it more candidates than a CPU can afford.

**How to avoid:**
- Make latency a first-class axis of reranker tuning: bench must report p50/p95 per-query latency alongside nDCG/MRR; every threshold/candidate-count option documents its latency cost (pair quality metrics with p95, always).
- Default candidate cap for CPU rerank: ~10–20; expose it as a setting. Enforce a hard ceiling (measured systems crash/timeout past ~20–50 on CPU).
- Provide and default-to a fast path for interactive use: skip-rerank hybrid (qmd's own community answer: 25–35× faster at minimal quality loss when top results feed an LLM anyway), with rerank opt-in (`query` vs `search` semantics).
- Remember embedding is not free either (~320–380 ms/query on CPU for 0.6B) — suggestions and expansion add embed calls per keystroke-class interactions.
- Threshold filtering (drop candidates below score X) reduces *output* noise but not *input* latency — the cap on candidates is what controls latency.

**Warning signs:**
- `query` taking >10 s on a laptop; MCP clients timing out; bench output showing quality metrics with no timing column; "tuned" thresholds that only got slower.

**Phase to address:**
**Reranker tuning phase** (and the bench expansion phase must already be emitting latency numbers, or the reranker phase will tune blind).

---

### Pitfall 10: Query suggestions that scan the index per keystroke — or correct to words not in the corpus

**What goes wrong:**
Two symmetric traps. (1) Naive did-you-mean over the term dictionary — edit-distance against every indexed term — is O(|V|·L²) per query; measured on a real engine: 315 ms average, 1.2 s max, unusable for interactive suggestions. (2) Using a general-purpose dictionary/spell model suggests corrections that *aren't in the index* ("trumen show" → "true man show" instead of the indexed "truman show"), so the suggestion returns zero hits and users learn suggestions are noise.

**Why it happens:**
`SELECT term FROM …` looks like the obvious vocabulary source, and difflib looks like the obvious comparator. Both are fine at 100 terms and terrible at 100k. SIF has no `fts5vocab` table today, so the vocabulary isn't even materialized yet.

**How to avoid:**
- Materialize the vocabulary once (FTS5 `fts5vocab` virtual table is the native way) and build a precomputed suggestion index at load: SymSpell-style delete-only index over the index vocabulary gives ~0.03 ms/word at edit distance 2, vs brute force's hundreds of ms. Budget: suggestions must answer well under 100 ms.
- Constrain suggestions to terms that actually occur in the corpus (the fts5vocab IS the dictionary); verify candidates with exact edit distance after candidate generation.
- Rebuild the suggestion index on index updates (it's derived data — incremental rebuild on the debounced indexing worker, not per query).
- Keep 10–15% in mind: that's the fraction of queries with misspellings — the feature matters, which is why the latency trap is worth engineering around rather than dropping.

**Warning signs:**
- Suggestion latency growing with library size; suggestions that return zero results when applied; suggestions of common English words absent from the notes.

**Phase to address:**
**Query suggestions phase** (with the vocabulary materialization sized as part of that phase, not discovered mid-phase).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Call indexer inline in the event handler | Watcher "works" in a demo | No place to put debounce/settle/queue; every event type re-triggers full parse+embed; save storms | Never |
| Filter events by extension only (current `watcher.py` `_should_handle`) | Tiny code | `.git`/`node_modules` burn watch descriptors; ignore_patterns bypassed live; temp files indexed | Never — reuse scanner ignore logic |
| Skip WAL/busy_timeout "until we see lock errors" | Zero migration work | Every live-index phase builds on instant-BUSY defaults; retrofit touches every connection site | Never — one PR, done in watch MVP |
| Tune weights on the bench fixture and move on | Fast "improvement" | Defaults nobody can defend; every future tuning compounds the overfit | Only with a held-out split reported alongside |
| PID file without flock/liveness check | Works in happy path | Restart-loop lockout after any crash; operator trust erosion | Never for a daemon shipped to users |
| Polling the watch tree to detect write completion | Avoids settle-check code | FD exhaustion at scale (proven: EBADF on large MD trees) | Never — settle only event-bearing paths |
| Separate watch logic per form (CLI/MCP/daemon each own their watcher) | Each phase ships faster | Three divergent event pipelines; double-writer races; bug fixes ×3 | MVP only for the first form; factor the event→index core immediately after |
| Golden-number bench asserts in CI | Regression safety theater | Fixture becomes immutable spec; leakage enshrined | Regression floor bands instead |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| watchdog (macOS FSEvents) | Assuming save = FileModifiedEvent | Handle the moved→deleted→created→modified chain as one reconciled path event; require watchdog ≥4 (≥6.0 gets `dest_path` ignore policies); consider v7 `latency` kwarg to coalesce |
| watchdog (Linux inotify) | Recursive watch on unshaped tree; assuming exhaustion raises | Exclude ignored subtrees from watch scope; treat silent event absence as possible watch loss; ENOSPC = watch limit, not disk; overflow → bounded rescan |
| watchdog events API | Using `FileSystemEvent` as dict key/set member; relying on `FileClosedEvent` everywhere | Events are mutable (hash derived from fields — mutation strands them); `on_closed` only exists on InotifyObserver/Linux |
| SQLite (writer+reader) | Rollback journal + busy_timeout=0 (current SIF defaults) | WAL + busy_timeout=5000 every connection; short write transactions; BEGIN IMMEDIATE for writes |
| sqlite-vec | Assuming old versions handle multi-connection concurrency | vec0 had cross-connection locking bugs (fixed in 0.0.1-alpha.37 era) — require current sqlite-vec; WAL verified compatible; wrap vec0 writes in explicit transactions |
| vim / modern editors | Indexing `.swp`/`4913`/`.sb-*`/`.DS_Store` | Extension allowlist + temp-file denylist at event intake; document `set noswapfile` for vim users in troubleshooting docs |
| Obsidian vaults | One event per autosave pause = full re-embed | Per-path debounce (300–500 ms) + checksum skip; `--embed` depth default off |
| Network-synced dirs (iCloud/Dropbox/NFS) | Kernel events assumed delivered | FSEvents/inotify do not fire for remote changes on network mounts — offer PollingObserver fallback (slow, "not recommended" per docs, battery cost) or an mtime-scan precheck fallback |
| launchd/systemd | Double-fork daemonizing under a supervisor; PID files under /var/run for user units | Foreground + `Type=simple`; LaunchAgent in `~/Library/LaunchAgents`, systemd `--user` unit; supervisor owns restarts |
| MCP server (asyncio) + watchdog (threads) | Calling blocking indexer/embedder from the event loop; sharing one sqlite3 connection across threads naively | Bridge via `call_soon_threadsafe`/queue; run indexing in a worker thread; per-thread connections (`check_same_thread=False` already set, but connections must not be shared mid-transaction) |
| Editors on macOS APFS | Trusting mtime for freshness/stability | Copy/sync preserves mtimes; measure age from first-seen; size+mtime both stable = settled |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Embed on every debounced save (`--embed` auto) | Fans, battery drain, seconds of CPU per save | Default BM25-only depth; embed via explicit opt-in or a coalesced batch job (e.g., embed after N quiet minutes) | Any laptop, immediately with autosave editors |
| Reranking >20 candidates on CPU | 10–50 s queries; MCP timeouts | Hard candidate cap 10–20; latency reported with quality | ~20 candidates on CPU |
| Suggestion scan over full vocabulary | 100 ms–1 s per keystroke-class call | Precomputed SymSpell delete-index over fts5vocab | ~10k+ distinct terms |
| Long single transaction per collection embed | All other writes blocked for minutes; BUSY storms | Transaction per document (or small batch); embed outside transaction | First concurrent search during embed |
| Watch + scan full-tree polling for write-finish | FD exhaustion (EBADF) in long-running daemon | Settle-check only paths that emitted events | ~thousands of watched files |
| One-observer-per-collection in one process | Watch descriptor and thread multiplication | Single observer, multiple scheduled watches; scheduler map keyed by collection | Many collections on Linux |
| Checkpoint starvation (long-lived MCP read connections) | `-wal` grows unboundedly | Close/idle read connections; periodic checkpoint when quiet | Days-long MCP server uptime |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| World-readable PID/lock files next to the DB | Local info disclosure / tampering (another user's process could spoof liveness) | Create with `0600` in the user data dir; validate PID ownership before trusting |
| Daemon accepting work from any local process (MCP HTTP + watch daemon ports) | Unauthenticated local RPC driving embed jobs (CPU DoS) | No network surface for the daemon; IPC via the DB/lockfile only; MCP HTTP auth unchanged from existing milestone fixes |
| Bench fixture path in CI treated as trusted | Malicious fixture JSON (huge `relevant_docids`, crafted queries) OOMs CI or exfiltrates via embed API mode | Size limits on fixture; bench fixtures are dev-local data, never user-supplied input in the shipped tool |
| Suggestion index built from document content surfaced without ACLs | Suggestions leak term existence from all collections cross-collection | Per-collection scoping of suggestions or explicit global opt-in |
| Logs printing full paths/content of every watched file change | Notes content patterns leak to logs (stderr, journald) | Log paths at debug level only; never log parsed content |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent index staleness (watch died, nobody told) | "Search returns deleted documents" — trust collapse | `sif status`/MCP tool surfacing watcher health (running since, last event, last error); auto-rescan on detected watch loss |
| Save-storm latency visible in search (partial updates) | Half-updated doc visible mid-save | Update doc row atomically (delete+insert in one transaction) so readers see old or new, never mixed |
| Suggestions that return zero results when clicked | Users learn to ignore the feature | Suggest only corpus terms; verify suggestion yields hits before offering |
| Weight config exposed as raw floats with no guidance | Users cargo-cult random weights and blame the engine | Ship named presets (keyword-leaning / balanced / semantic-leaning) + bench command guidance; document held-out evaluation |
| Rerank on by default for `query` | 30 s+ MCP tool calls; assistants stop using the tool | Fast default path, rerank opt-in with documented latency cost |
| Watch daemon errors only in journald/system log | "It just stopped working" | `sif watch status`/`sif watch log` commands; heartbeat state in DB |

## "Looks Done But Isn't" Checklist

- [ ] **`sif watch`:** Often missing real-editor testing — verify a TextEdit/Obsidian-style save chain (moved→deleted→created→modified) produces exactly one re-index and a vim save produces one (no `.swp` indexing)
- [ ] **`sif watch`:** Often missing delete handling — verify deleting a file removes it from search results without a full `index update`
- [ ] **`sif watch`:** Often missing ignore-pattern parity — verify a file matched by collection `ignore_patterns` is NOT live-indexed when saved
- [ ] **Live index:** Often missing concurrency proof — verify a search executing during a `--embed` update never raises `database is locked` and never blocks >busy_timeout
- [ ] **Daemon:** Often missing crash recovery — verify `kill -9` then restart recovers cleanly (flock released, no refuse-to-start, resyncs state)
- [ ] **Daemon:** Often missing SIGTERM drain — verify `sif watch stop` (or launchctl kill) finishes the in-flight file and exits 0
- [ ] **MCP embedded watch:** Often missing event-loop hygiene — verify indexing work never blocks MCP request handling (measure p95 of a concurrent search during a burst)
- [ ] **Pre-command check:** Often missing cost bound — verify `sif search` on an unchanged library adds near-zero startup time (checksum/stat fast path)
- [ ] **Hybrid weights:** Often missing held-out evaluation — verify shipped defaults report a held-out number, not just the tuning-fixture number
- [ ] **Bench:** Often missing latency metrics — verify reranker/bench output includes p50/p95 wall-clock
- [ ] **Suggestions:** Often missing corpus constraint — verify every offered suggestion returns ≥1 hit when executed
- [ ] **Suggestions:** Often missing scale proof — verify latency on the largest realistic vocabulary (not a 20-file test vault)

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| DB locked errors shipped (no WAL/busy_timeout) | LOW | Add pragmas in `_create_connection()`/pool — one PR, file format unchanged (WAL persists per-file; old DBs convert on first open) |
| Index churned by save storms | MEDIUM | Add debounce+settle layer in front of existing indexer; re-run `index update` to clean duplicate/orphan rows from the churn period |
| Missed deletes left stale docs | MEDIUM | Full `index update` (scanner reconciles reality); then add tombstone handling |
| Silent watch loss (inotify exhaustion) | MEDIUM | Restart watcher (re-arms watches); fix scope shaping; log watch counts; users on huge trees may need sysctl guidance |
| Stale-PID lockout | LOW | Delete stale PID/lockfile (flock variant self-heals); add liveness check so users never repeat it |
| Overfit weights shipped as defaults | LOW | Revert to unweighted RRF k=60 default (the evidence-backed default); keep weights opt-in until a real held-out set exists |
| Circular bench fixture | MEDIUM | Freeze current fixture as tuning set; hand-label a new held-out set; re-baseline defaults against held-out only |
| Partial/mixed content indexed from mid-write | LOW | Settle-check + next save self-heals via checksum mismatch; affected docs re-index on following event |
| Reranker unusable on CPU | LOW | Lower candidate cap; add skip-rerank path; already-indexed data unaffected |

## Pitfall-to-Phase Mapping

Phases named by feature (per PROJECT.md Active list) since roadmap numbering is created downstream.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. SQLite WAL/busy_timeout | Watch MVP (`sif watch`) — precondition | CI test: concurrent search + embed update, zero lock errors; pragma audit on all connection sites |
| 2. Rename-chain saves | Watch MVP | Fixture test reproducing TextEdit event sequence; real-editor manual UAT |
| 3. Debounce/settle | Watch MVP | Burst test (N rapid writes → exactly 1 index op); CPU profile during editing session |
| 4. Watch scope + silent loss + tombstones | Watch MVP, hardened in Daemon phase | Ignore-pattern parity test; delete tombstone test; simulated overflow → rescan test; watch-count logging |
| 5. Daemon lifecycle + single-writer | flock design in Watch MVP; full treatment in Daemon phase | kill -9 restart test; SIGTERM drain test; two-writer arbitration test (daemon + MCP + pre-command) |
| 6. Mid-write reads | Watch MVP | Truncated-write simulation test; checksum-churn assertion |
| 7. Weight overfitting | Bench expansion phase (before weights phase) | Held-out split shipped with bench; defaults justified by held-out numbers |
| 8. Benchmark leakage | Bench expansion phase | Separate tuning/heldout fixtures; regression-floor CI bands, no golden numbers; label provenance documented |
| 9. Reranker latency | Reranker tuning phase (bench emits latency from bench-expansion phase onward) | p50/p95 in bench output; candidate cap enforced; skip-rerank path latency budget met |
| 10. Suggestion latency/corpus constraint | Query suggestions phase | Latency on large vocabulary <100 ms; zero-result suggestions impossible by construction |

## Sources

- **watchdog FSEvents rename chains, coalescing, editor saves** — watchdog `observers/fsevents.py` source; GitHub issues #538, PRs #750, #754; watchdog events docs; SO "vim doesn't fire change event on OS X" (HIGH — official source/issues)
- **watchdog version/changelog facts (latency kwarg, unschedule leaks, inotify registration errors, daemon threads, CIFS→PollingObserver)** — PyPI watchdog v7.1.0 changelog; watchdog polling docs (HIGH — official docs)
- **SQLite WAL/busy_timeout/BEGIN IMMEDIATE/checkpoint starvation** — sqlite.org/wal.html; tenthousandmeters.com SQLite concurrent writes (2025); mako.ai transactions guide (2026); productionhardening.org busy-timeout; zeroexp.dev locking model (MEDIUM-HIGH — cross-verified across 5 independent sources; core claims rest on official sqlite.org docs = HIGH)
- **sqlite-vec WAL compatibility + multi-connection history** — asg017/sqlite-vec issue #40 and v0.1.10-alpha.2 compare (WAL concurrency tests); llama-stack PR #5442 (HIGH — upstream repo evidence)
- **Watch limits: inotify 8192 silent exhaustion, IN_Q_OVERFLOW, FSEvents UserDropped** — Syncovery inotify limits guide; Watchman troubleshooting docs; notify issue #109; shire PR #290 ENOSPC crash (MEDIUM — cross-verified vendor + community evidence)
- **Daemonization: stale PID, flock, kill(pid,0), supervisor patterns** — freedesktop.org daemon(7); bhekani.com PID files; mironsoft.de daemon guide (2025); dev.to pidlock stale-check (2026); Hermes-agent issue #13655 restart loop; celery create_pidlock (HIGH — official manual + upstream incidents)
- **Mid-write reads, settle checks, FD-pressure** — sysax size-stability guide; SO chokidar awaitWriteFinish; usrcp-obsidian watcher source; openclaw PR #81802; tailwindcss PR #5758 (MEDIUM — cross-verified community/engineering evidence)
- **Fusion tuning overfitting, held-out methodology, k-before-weights** — qdrant.tech hybrid tuning guide; chicong115.com case study (2026-09, measured overfit numbers); claude-dev-suite alpha-tuning (50–200 query minimum); testland hybrid-eval anti-patterns; qaskills retrieval tuning (2026-08) (MEDIUM — consistent across 5 independent community sources; includes upstream vendor guide)
- **Reranker CPU latency** — tobi/qmd issue #264 (the project SIF ports; 34–49 s on CPU); cried-nutty-won/rag-system (M1 Pro ~580 ms/candidate, 18-cap); dev.to production RAG (CPU/T4 latency table, OOM at 100 docs); aimultiple reranker benchmark (autoregressive yes/no vs single-pass) (MEDIUM-HIGH — includes qmd upstream issue = HIGH for the qmd-specific numbers)
- **Suggestions latency/algorithm** — blog.cf8.gg lnx SymSpell migration (315 ms→~47 ms measured); seekstorm SymSpell vs BK-tree; wolfgarbe/SymSpell (0.033 ms/word); mercemay edit-distance candidate generation (2025-11) (MEDIUM — cross-verified community/practitioner sources)
- **Battery/CPU of watchers, polling vs event-driven** — watchdog polling docs; AgentMonitors issue #469 (wakes dominate drain); SO network-mount answers (LOW-MEDIUM — directional, single-community-source; treat battery claims as hypotheses to validate in-phase)
- **Codebase grounding** — direct reads of SIF source: `watcher.py` (unwired handlers, no debounce, stop/unschedule gap), `connection.py` (no WAL/busy_timeout), `indexer.py` (no public single-file API; embed-then-write), `hybrid.py`/`rrf.py` (hardcoded k=60, unweighted fuse in use, in-place result mutation), `benchmark.py`/`bench.py` (fixture shape), `mcp/transports/http.py` (asyncio), `schema.py` (no fts5vocab) (HIGH — verified locally 2026-11-07)

Open gaps (flagged for phase-specific research): exact watchdog version floor to require (≥4 needed for rename-chain correctness; v7 for latency kwarg — decide in watch MVP); launchd plist vs systemd unit generation specifics (daemon phase); whether SIF's existing `SearchOptions.candidate_limit` already caps rerank input today (reranker phase should audit before adding a new knob).

---
*Pitfalls research for: live indexing + search quality on SIF (DocSift v1.1)*
*Researched: 2026-11-07*
