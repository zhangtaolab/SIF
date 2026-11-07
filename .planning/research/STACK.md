# Stack Research

**Domain:** Live file-watch indexing + search-quality tooling for a local hybrid search engine (DocSIF/SIF v1.1)
**Researched:** 2026-11-07
**Confidence:** HIGH (headline verdict verified against primary sources: watchdog official changelog raw-fetched from GitHub, PyPI JSON API, sqlite.org WAL doc, plus local runtime experiments on this machine)

## Headline Verdict

**ZERO new runtime dependencies.** Every v1.1 capability is buildable with the existing dep set (watchdog + SQLite + Click + Pydantic Settings) plus the Python stdlib. The only dependency change required is a **version cap on watchdog**: `watchdog>=3.0.0` → `watchdog>=4.0.0,<7.0.0`. Everything else is configuration (SQLite WAL pragmas), stdlib code (double-fork detach, plist/unit generation, difflib), and in-house modules (weighted RRF, nDCG@k/MAP, suggestion engine). This keeps the PyPI package light and pure-Python, per the project constraint.

## Recommended Stack

### Core Technologies (existing deps, new usage)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| watchdog | **`>=4.0.0,<7.0.0`** (change from `>=3.0.0`) | `sif watch` file-event source | Already vendored. `Observer()` auto-selects native backends (FSEvents on macOS, inotify on Linux) with no code per-OS. Ships a built-in **`watchdog.utils.event_debouncer.EventDebouncer`** (present since 3.0.0) — no hand-rolled debounce thread needed. Cap at `<7`: watchdog **7.0.0 (2026-10-31) dropped Python 3.10** (`requires-python >=3.11`) and made breaking behavior changes (see Version Compatibility); 6.0.0 (2024-11-01) is the newest release supporting 3.10, which SIF's `requires-python = ">=3.10"` mandates. Floor raised to 4.0 for a supported, modern baseline (5.0 dropped only 3.8). |
| SQLite via stdlib `sqlite3` | system/bundled (any ≥3.7 for WAL; ≥3.34 for trigram) | Concurrent access: watch-daemon writer + CLI/MCP readers | WAL is the canonical multi-process SQLite configuration (sqlite.org): readers don't block the writer and vice versa; still exactly one writer at a time — fine, the watch daemon is the sole background writer. sqlite-vec `vec0` tables are confirmed working under WAL in production stacks (llama-stack added exactly these pragmas to their sqlite-vec provider to fix multi-worker `database is locked`). No dependency change — this is pragma configuration in `DatabaseConnection._create_connection()`. |
| Python stdlib (`os`, `signal`, `subprocess`, `plistlib`/string templates) | 3.10+ | `--detach` daemonization; launchd/systemd service generation | A correct double-fork detach is ~30 lines of stdlib. launchd/systemd integration is "write a text template + invoke `launchctl`/`systemctl` with an explicit argv list" — the proven pattern used by taosmd, dotagent, agenttap. Critically, under a supervisor the process must run **foreground** (never fork), so `python-daemon` would be dead weight even besides the dependency cost. |
| stdlib `difflib` + FTS5 `trigram` tokenizer + query-history table | SQLite ≥3.34.0 for trigram | did-you-mean / query suggestions | Zero-dep suggestion pipeline: generate a small candidate set in SQL (trigram substring match, or first-letter/length buckets when trigram is unavailable), rank with `difflib.get_close_matches` / `SequenceMatcher`, bias by FTS5 term frequency, and supplement with prefix matches over a stored query-history table. difflib full-vocab scans are too slow (≈0.58s/lookup at 15k terms) — hence the SQL pre-filter, which makes it fast. |
| In-house pure-Python metrics (extend `src/sif/search/benchmark.py`) | n/a | bench expansion: nDCG@k, MAP | `benchmark.py` already has P@k, recall@k, MRR with fixture validation. nDCG@k + MAP are ~40 lines each of pure Python; at personal-KB bench scale (dozens of queries × top-10) performance is a non-issue — even the pytrec_eval paper concedes native Python is competitive at these sizes. No eval-harness library needed. |
| Pydantic Settings (existing) | pydantic-settings ≥2.0 | Hybrid weights, reranker tuning, watch options | All v1.1 tunables are plain Settings fields: `bm25_weight`, `vector_weight`, `rrf_k` (default 60), reranker score threshold / top-n / latency budget, `watch_debounce_interval`, `watch_ignore_patterns`, update-depth default. Consumed by `HybridSearcher`/`RRFFusion`, `SearchPipeline`, and the new watcher wiring. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none new at runtime) | — | — | — |
| `ir-measures` | 0.4.3 | Cross-check in-house metric implementations | **Dev-only, one-off scratch env** — verify nDCG@k/MAP numbers once during bench development, then uninstall. Has a hard dependency on the `pytrec-eval-terrier` C extension; must never enter `[project.dependencies]`. |
| `symspellpy` | 6.7.x (SymSpell v6.7.2 port) | Higher-quality spell correction fallback | **Only if** the trigram+difflib suggestion quality proves insufficient in UAT. Pure Python (MIT) with `editdistpy` fast comparer, 0.033ms/word at edit-distance 2; would be a new runtime dep, so treat as last resort. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `sqlite3` CLI / `PRAGMA journal_mode` inspection | Verify WAL switched, check `-wal`/`-shm` files and checkpoint behavior | `PRAGMA journal_mode;` returns `wal` on success; the switch needs a write lock — set `busy_timeout` first |
| Existing quality suite (pytest/ruff/ty) | Everything new ships under the fail_under=90 gate | Watcher/daemon code needs injected fake observers and `tmp_path` trees; coverage gate already permanent |
| `launchctl print gui/$(id -u)/<label>` / `journalctl --user -u <unit> -f` | UAT of installed services | Manual verification commands to print in CLI output after install |

## Installation

```bash
# No new packages. The only change (pyproject.toml):
#   "watchdog>=3.0.0"  ->  "watchdog>=4.0.0,<7.0.0"
# then refresh the lock:
uv lock
```

## Key Integration Points (what the roadmap plans should touch)

1. **`src/sif/database/connection.py` — `_create_connection()`** (single choke point; also `ConnectionPool.get_connection()`, which notably loads neither sqlite-vec nor pragmas today). Add, **in this order**:
   ```python
   conn = sqlite3.connect(str(self._db_path), check_same_thread=False, timeout=5.0)
   conn.execute("PRAGMA busy_timeout=5000")        # FIRST: the WAL switch itself needs a write lock
   conn.execute("PRAGMA journal_mode=WAL")          # persistent — stored in DB header, set once per DB
   conn.execute("PRAGMA synchronous=NORMAL")        # canonical WAL pairing; index is rebuildable anyway
   # ... then enable_load_extension + sqlite_vec.load(conn) as today
   ```
   On watch-daemon shutdown: `PRAGMA wal_checkpoint(TRUNCATE)` to keep the `-wal` file small. Add a bounded retry (a handful of attempts, small backoff) around first open: read→write lock upgrades return `SQLITE_BUSY` immediately without honoring `busy_timeout`, so two processes racing the very first open (or schema DDL) can still collide.
2. **`src/sif/indexing/watcher.py`** — wire the existing stubs: `IndexingEventHandler` currently only logs. Route events through `EventDebouncer` (call it **positionally** — `EventDebouncer(interval, callback)` — the first kwarg was renamed `debounce_interval_seconds`→`debounce_interval` in 7.0; positional works on 3.x–7.x). Use `PatternMatchingEventHandler` (ignore `.git/`, `.obsidian/`, `node_modules/`, `*.swp`, `*.tmp` — editor noise). Fix a latent gap: `on_moved` checks only `src_path`; editors doing atomic save deliver *rename into* the tree, so filter on **`dest_path`** for create-equivalent semantics. Coalesce delete→create sequences per path.
3. **`src/sif/config/settings.py`** — new fields (all `SIF_`-prefixed env-overridable): `watch_debounce_interval` (suggest 0.5–1.0s; the watchdog docs recipe uses 1s), `watch_ignore_patterns`, `watch_update_depth` (`bm25` default / `embed` opt-in), `bm25_weight` (default 1.0), `vector_weight` (default 1.0), `rrf_k` (default 60 — preserves current behavior), reranker threshold/top-n/latency-budget fields.
4. **`src/sif/search/rrf.py`** — weighted RRF: `score = Σ_i w_i / (k + rank_i)`; `HybridSearcher.__init__` currently hardcodes `RRFFusion(k=60)` — read weights from Settings. Pure arithmetic, no deps.
5. **`src/sif/search/benchmark.py`** — add `ndcg_at_k` (graded relevance) and `mean_average_precision` beside existing metrics; extend the fixture schema for graded relevance levels.
6. **New `sif watch` CLI command** — foreground loop (`observer.start()` + signal-driven shutdown: SIGINT/SIGTERM → `observer.stop(); debouncer.stop()`), `--detach` (stdlib double-fork: fork → setsid → fork, redirect stdio to log file/`/dev/null`), and a service-install path that writes:
   - macOS: `~/Library/LaunchAgents/com.docsif.watch.plist` — `RunAtLoad=true`, `KeepAlive=true`, `ThrottleInterval=10`, `ProgramArguments=[sys.executable, "-m", "sif", "watch", ...]`, logs to `~/Library/Logs/sif/`; start via `launchctl bootstrap gui/$(id -u) <plist>` (stop: `bootout`, restart: `kickstart -k`).
   - Linux: `~/.config/systemd/user/sif-watch.service` — `Type=simple` (foreground, never fork under systemd), `Restart=on-failure`, `RestartSec=5`, `WantedBy=default.target`; start via `systemctl --user daemon-reload && systemctl --user enable --now sif-watch`; document `loginctl enable-linger $USER` for survive-logout.
   - All subprocess calls with explicit argv lists, never `shell=True`; friendly errors when `launchctl`/`systemctl` is missing.
7. **MCP embedded refresh** — watchdog is thread-based, the MCP server is asyncio: bridge with a `queue.Queue` filled by the observer thread and drained by a periodic asyncio task (or `loop.call_soon_threadsafe` wakeup). Stdlib-only; do not add janus. The refresh task reuses the same incremental-index path as `sif watch`.
8. **Pre-command auto-detect** — lightweight staleness check before search commands: per-collection scan watermark (store last-scan fingerprint in an existing meta/settings table) + bounded `stat()` sweep of collection roots; run incremental BM25-only reindex only when deltas are seen, with a time budget so it stays "轻量兜底". Reuses `scanner.py` checksum logic; no new deps.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Cap `watchdog<7` | Bump `requires-python` to ≥3.11 and adopt watchdog 7.x | If the project later drops Python 3.10: 7.1.0 (2026-11-04) has real at-scale fixes — inotify queue-overflow reconciliation, lazy inotify instance, watches on directories moved into the tree. Until then, the cap is mandatory for 3.10 users. |
| watchdog `EventDebouncer` | Hand-rolled `threading.Timer` coalescer (the common StackOverflow recipe) | Never for this milestone — built-in, battle-tested, and 7.0 even fixed a starvation bug in it (which we cap away; at 6.0 the official docs recipe pattern applies). Only if a per-path settle-time semantic (vs global quiet-window) is demanded by UAT. |
| stdlib double-fork + supervisor templates | `python-daemon` 3.1.2 (PEP 3143) | Only if the detach path grows real complexity (pidfiles, signal policy, privilege drop). Even then it conflicts with supervisor mode: launchd `KeepAlive`/systemd `Type=simple` expect a foreground process; a forking daemon defeats exit tracking. Slow release cadence (2008–2024), POSIX-only, Apache-2.0/GPL-3 dual files. |
| In-house nDCG@k/MAP | `ir-measures` 0.4.3 / `pytrec_eval` / `ranx` 0.3.21 | Never at runtime: ir-measures hard-depends on the `pytrec-eval-terrier` C extension; pytrec_eval is a compiled extension; ranx needs numba (JIT, huge wheel) + scipy + more. Dev-only cross-checking in a scratch env is fine. |
| SQL candidates (trigram/bucket) + difflib ranking | `symspellpy` | If UAT shows correction quality gaps (SymSpell's delete-dictionary + frequency prior is the quality ceiling at 0.033ms/word). Requires building a frequency dictionary from indexed terms — cheap from FTS5 vocab. Acceptable future optional extra, not v1.1. |
| `PollingObserver` (watchdog built-in) | Native observers (default) | Only for network-mounted collections (NFS/SMB — kernel events don't cross hosts; WAL also requires same-host FS, so a network DB path needs `journal_mode` fallback handling) or when inotify watch limits are hit and cannot be raised. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| watchdog ≥7.0.0 while on Python 3.10 | 7.0.0 dropped 3.9/3.10 (`requires-python >=3.11`); also silently changes `PatternMatchingEventHandler` semantics (`path.match` → `path.full_match`: `*.py` no longer matches nested paths) and splits attribute events out of `on_modified` | `watchdog>=4.0.0,<7.0.0` |
| `ranx` | numba JIT dependency (plus scipy/pandas/ir-datasets chain) — destroys the light pure-Python package | In-house pure-Python metrics in `benchmark.py` |
| `ir-measures` / `pytrec_eval` as runtime deps | Hard C-extension dependency / compiled wheel availability issues | Same as above; dev-only scratch cross-check if wanted |
| SQLite `spellfix1` extension for did-you-mean | Not compiled into CPython's bundled sqlite3 — **verified locally** (`no such module: spellfix1`, SQLite 3.50.4 on macOS py3.13); cannot be relied on in a pip-distributed pure-Python package | FTS5 trigram tokenizer + difflib (spellfix1 was the only piece making the fuzzy-suggest problem look extension-dependent) |
| `python-daemon` / `daemonize` | New runtime dep for ~30 stdlib lines; forking behavior actively harmful under launchd/systemd supervision | stdlib double-fork for `--detach`; foreground under supervisors |
| janus / any asyncio-thread bridge library | One `queue.Queue` + polling task or `call_soon_threadsafe` is sufficient | stdlib queue |
| Unversioned `watchdog>=3.0.0` (status quo) | Resolves to 7.x on Python 3.11+ and 6.0.0 on 3.10 — split-brain behavior across the user fleet, CI on different interpreters sees different event semantics | Pinned range as above |
| Default journal mode (DELETE) + no busy_timeout for the daemon era | First concurrent write from the watch daemon while a CLI search holds a read lock → `database is locked` failures; this is exactly the bug llama-stack hit in production with sqlite-vec | WAL + busy_timeout + synchronous=NORMAL per the pragma block above |

## Stack Patterns by Variant

**If the collection tree is large (>~8k directories on Linux):**
- Watchdog inotify uses one watch descriptor per directory; `fs.inotify.max_user_watches` defaults to 8192 on many distros. Detect `OSError`/queue-overflow symptoms, warn with the `sysctl fs.inotify.max_user_watches=...` fix, and/or fall back to `PollingObserver` for that collection.
- Because overflow events can silently drop changes even below 7.x's overflow-reconciliation fixes, the **pre-command auto-detect staleness check doubles as the safety net** — design them to share the watermark/incremental code path.

**If the watched path is on a network filesystem (NFS/SMB):**
- Use `PollingObserver`; and since WAL requires same-host shared memory, a DB on network storage must fall back to `journal_mode=DELETE` — detect WAL-switch failure (pragma returns the old mode) and degrade gracefully with a logged warning.

**If `--embed` update depth is enabled in the daemon:**
- Embedding model loads lazily and stays cached (`EmbeddingManager._model`) — the daemon becomes the only process that should embed; keep `--embed` off by default so `sif watch` stays BM25-cheap on startup. Chunk/vector writes: **always inside explicit transactions** (vec0 writes left outside transactions historically caused multi-connection lockups — sqlite-vec issue #40).

**If macOS:**
- Default `Observer()` already selects FSEvents (coalesces same-inode event chains; may emit historic events up to 30s pre-watch — watchdog suppresses via starting snapshot). Note FSEvents reports dir-level changes; watchdog diffs snapshots to produce per-file events — debouncing still required for editor bursts.

**If suggestions run on an old SQLite (<3.34, e.g. Ubuntu 20.04 system sqlite 3.31):**
- Runtime capability check `sqlite3.sqlite_version_info >= (3, 34)`; degrade to first-letter/length-bucket candidate generation + difflib (slower, still correct). Never hard-require trigram.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| watchdog 6.0.0 (capped max) | Python 3.9–3.10 | The only 6.x release; supports SIF's 3.10 floor |
| watchdog 7.x | Python ≥3.11 only | 7.0.0 also: pattern `full_match` semantics, `FileAttribEvent`/`DirAttribEvent` split from `on_modified`, `Observer` context manager, `ignore_policy` on pattern handlers |
| `EventDebouncer(interval, callback)` positional | watchdog 3.0 → 7.x | First kwarg renamed (`debounce_interval_seconds` → `debounce_interval`) in 7.0; old kwarg deprecated-but-working. **Pass positionally.** |
| FTS5 `trigram` tokenizer | SQLite ≥3.34.0 | Verified locally: macOS py3.13/SQLite 3.50.4 OK. Debian 11 (3.34.2) OK; Ubuntu 20.04 (3.31) NOT — needs runtime check + fallback |
| WAL mode | SQLite ≥3.7.0; same-host filesystem only | Persistent DB-header property; no network FS; cannot open read-only WAL DBs |
| sqlite-vec 0.1.9 (current, = pyproject floor) | WAL journal mode | Confirmed by llama-stack's identical pragma fix; keep vec0 writes transactional |
| WAL + watchdog writer + CLI/MCP readers | one writer, many readers | `busy_timeout` covers most waits; read→write upgrades return BUSY immediately — bounded retry on first open/DDL |

## Sources

- watchdog official changelog (raw, GitHub `gorakhargosh/watchdog/master/changelog.rst`) — version history, 7.0.0/7.1.0 changes, Python support drops; `src/watchdog/utils/event_debouncer.py` verified present at tags v3.0.0–v6.0.0 with positional signature (primary source)
- PyPI JSON API `pypi.org/pypi/{watchdog,python-daemon,ir-measures,ranx,symspellpy,sqlite-vec}/json` — latest versions, `requires_python`, dependency lists (primary source; fetched 2026-11-07)
- watchdog official docs — EventDebouncer recipe (examples.html), FSEvents coalescing/history notes (observers/fsevents.py docstrings) (primary)
- sqlite.org WAL documentation (`sqlite.org/wal.html`) and SQLite forum thread on WAL multi-process — WAL semantics, persistence, BUSY edge cases, checkpointing (primary)
- llama-stack PRs #5428/#5442 and sqlite-vec issue #40 — production confirmation of WAL+busy_timeout+NORMAL with sqlite-vec, transactional vec0 writes (HIGH relevance, MEDIUM confidence individually)
- taosmd `service_install.py`, agenttap `running-as-a-service.md`, dotagent daemon-lifecycle docs — plist/systemd-user-unit generation pattern, launchctl bootstrap/bootout/kickstart, `Type=simple` foreground, linger (MEDIUM confidence, cross-checked across three independent implementations)
- difflib performance benchmark (StackOverflow 21408760), SymSpell repo, tdom.dev FTS5 fuzzy-search walkthrough — suggestion-engine options (MEDIUM)
- **Local verification (2026-11-07, this machine, macOS 26.6.2 / Python 3.13.11 / SQLite 3.50.4):** fts5 trigram tokenizer OK; `spellfix1` NOT available in CPython sqlite3; WAL pragma OK. SIF repo inspected: `connection.py` has no WAL/busy_timeout; `watcher.py` unwired (log-only handlers, `on_moved` filters on src only); `rrf.py` k=60 hardcoded; `benchmark.py` has P@k/R@k/MRR only (HIGH)

---
*Stack research for: SIF v1.1 Live Index and Search Quality*
*Researched: 2026-11-07*
