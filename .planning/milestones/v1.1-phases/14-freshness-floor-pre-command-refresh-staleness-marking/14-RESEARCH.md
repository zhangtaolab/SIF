# Phase 14: Freshness Floor (Pre-Command Refresh + Staleness Marking) - Research

**Researched:** 2026-11-08
**Domain:** Stat-based drift detection + bounded BM25 refresh in the CLI search path; derived vector-staleness marking across all result surfaces
**Confidence:** HIGH (codebase claims verified by direct file reads this session; performance claims verified by local probes; external claims minimal and corroborated by official sqlite-vec docs)

## Summary

Phase 14 is almost entirely a codebase-integration phase: every primitive it needs already exists and was verified by direct reads this session. The pre-command refresh (LIVE-10) is a new drift-detection helper in the CLI command layer that walks the searched collections' roots with `FileScanner`, compares `st_mtime` against the `documents` table, and — only when drift is found and under the file-count cap — reuses the exact burst pattern the watcher already uses (`index_lock` → `IncrementalIndexer.update_paths`). The staleness marker (QUAL-06) is a batched enrichment sibling of the existing `attach_path_contexts` seam, plus a `SearchResult` boolean and one forwarding line in the MCP backend mapping.

Three code-level corrections to the CONTEXT's assumptions are the most important findings: (1) `documents.file_size` is **not** the on-disk size (it is the frontmatter-stripped body byte length, never refreshed on update), so the stat compare must be mtime-primary — a naive size compare false-positives forever; (2) chunks exist **only** after `sif index embed`, and BM25-only updates purge chunks *and* embeddings together, so D-08's literal "has chunks but no embeddings" formula does not fire for the actual lag state — the correct derived signal is "document has **no embeddings**"; (3) the MCP query response does *not* automatically inherit new `SearchResult` fields — `backend.py` re-maps fields explicitly, so the flag needs one forwarding line there. Local probes confirmed the cost contract: a 5000-file rglob+stat walk takes ~43 ms and SQLite REAL round-trips `st_mtime` bit-exactly.

**Primary recommendation:** Build the drift helper as a presentation-free function over `(conn, collections) -> DriftReport` placed beside `IncrementalIndexer`, gate `update_paths` behind it (mtime-only compare, count-then-decide cap), hang the staleness flag on a sibling of `attach_path_contexts` called at the three existing seam sites, and forward the flag through the MCP backend mapping explicitly.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Copied verbatim from `.planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-CONTEXT.md` `## Implementation Decisions`:

- **D-01:** **Search trio only** — `sif search`, `sif vsearch`, `sif query` run the drift check; get/multi-get/ls/pull do not. The check lives in the **CLI command layer** (`cli/commands/search.py`), NOT in the searchers or `SearchPipeline` — so `sif bench` (invokes searchers directly, `bench.py:91`) and the MCP server bypass it by construction; bench latency stays measurement-clean for Phase 16.
- **D-02:** **Every invocation, stateless** — no watermark table, no throttle window. Each search pays one stat walk (~<50ms at personal-KB scale per research). Clean index = read-only walk, zero writes, zero locks (SC2's near-zero cost). No "checked N seconds ago" staleness window to reason about.
- **D-03:** **Always run, even when a watch/daemon is live** — the check doubles as the event-overflow backstop (kernel queues silently drop events; research STACK #99). Host detection is unreliable anyway: only the detached daemon writes a PID file; foreground watch and MCP watch leave no trace a CLI process can see. When watch already handled everything, the walk finds zero drift (stat-decides no-op); when drift is found mid-watch-burst, per-burst flock + wait-then-run (11-D02, 12-D04) arbitrates.
- **D-04:** **Sweep only the collections being searched** (respecting `-c`/`--all` filters) — cost proportional to what the search will actually query; the results you're about to see are exactly the fresh ones. Un-searched collections drift until searched or `sif index update`.
- **D-05:** **Over-cap = skip refresh entirely + warn** — count drifted files first (the stat walk already knows); if count > cap, do NO refresh, search proceeds on the stale index, and a prominent stderr warning names the drift size and says to run `sif index update`. Rationale: partial refresh would mix fresh and stale docs in one ranking with no way to tell which; the branch-switch pathology should be surfaced, not half-fixed. Search never becomes an error because the index drifted.
- **D-06:** **Cap shape = file count** via an `SIF_` setting (e.g. `SIF_SEARCH_REFRESH_MAX_FILES`, exact name/default = Claude's discretion). Deterministic — the project's test culture (11-D08/D-09, 12-D15) can assert exact over-cap/under-cap behavior with no timing flakiness. A file-count cap directly bounds parse/write work.
- **D-07:** **Visibility contract** — under-cap refresh prints ONE stderr notice (e.g. `refreshed 3 files (bm25) before search`); stdout stays clean for `--json`/`--csv` piping; `-q/--quiet` suppresses. The over-cap warning is also stderr. Silence when clean.
- **D-08:** **Derived at query time — no schema change** — stale = doc has chunks but no embeddings. This is true by construction: Phase 12 D-10 BM25-only updates purge stale chunks/vectors, and delete-before-insert keeps embedding state all-or-nothing per doc. Detect via a SQL existence check during result assembly. (See Research Finding B1 — the literal formula must be corrected to "no embeddings"; the derivation intent survives.)
- **D-09:** **All search surfaces, one code path** — the stale flag is computed in the shared result-assembly path so `search`, `query`, and the MCP query tool mark consistently. Note: the marker only ever FIRES on docs surfaced via the BM25/FTS leg — a vector-stale doc has no vector, so `vsearch` cannot return it. But wherever such a doc appears, it is marked.
- **D-10:** **`sif status` gains a vector-lag line** (e.g. `Vector lag: N documents`) — same derived SQL, glanceable index health; extends the Phase 13 Watch-section pattern in the existing Rich table.
- **D-11:** **Boolean field on `SearchResult`** (e.g. `vectors_stale: true`, exact name = Claude's discretion) added to `to_dict()` — CLI `--json` AND the MCP query response carry it automatically, one code path. (See Finding B5 — MCP needs one explicit forwarding line.)
- **D-12:** **All output formats** — Rich table: compact inline annotation next to the title (dim; exact glyph/wording = discretion), no new column. JSON: the boolean field. CSV: one extra column. Markdown: same inline annotation as the table. XML: an attribute (Phase 10.1 sanitizer story governs XML safety). SC3 (table + JSON) is the floor; no format silently drops a signal the others show.
- **D-13:** **Remedy hint** — when ≥1 result is stale, one stderr line after results (e.g. `3 results have stale vectors — run 'sif embed' to refresh`; wording = discretion; `-q` suppresses). Matches the over-cap warning's remedy pattern.

**Carried forward (do not re-litigate):** BM25-only refresh, never embed; reuse `IncrementalIndexer.update_paths`; stat-walk recipe (no hashing; checksums only on drifted files via the existing incremental path); disableable via an `SIF_` setting; missing-root guard free via the shared core (12-D11); per-burst flock + wait-then-run (11-D01..D-03, 12-D04); zero new runtime dependencies; docs are generator-owned (`make docs-generate` only).

### Claude's Discretion

- `SIF_` settings field names (max-files cap, enable/disable toggle) and the cap's default value
- Whether the opt-out also gets a per-invocation flag (e.g. `--no-refresh`) in addition to the setting
- Drift-detection helper placement and shape (e.g. `indexing/` service vs CLI helper; how the walk reuses `FileScanner` short of checksums)
- Exact stderr notice/warning/hint wording; marker glyph/wording in table and Markdown; exact JSON field name
- How result assembly computes staleness (one batched SQL for the result set vs per-result check) as long as D-09's one-code-path contract holds
- Status-line wording and placement within the existing `sif status` table
- Lock-wait deadline used by the refresh burst (existing wait-then-run default is fine)
- Test scaffolding details (synthetic drift setups in `tmp_path`; deterministic over/under-cap assertions)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (from REQUIREMENTS.md) | Research Support |
|----|------------------------------------|------------------|
| LIVE-10 | 未运行 watch 时，搜索命令前 stat 漂移检测自动刷新（有上限，干净时零成本）— with no watch running, search commands stat-detect drift and auto-refresh (capped, zero cost when clean) | Findings A1–A13: verified `update_paths` seam, walk shape, mtime-only compare rationale, cost probes, cap mechanics, stderr contract, missing-root guard |
| QUAL-06 | 分层更新深度下，向量滞后的搜索结果标记 staleness 状态 — under tiered update depth, results whose vectors lag carry a staleness marker | Findings B1–B9, C: corrected derived signal, the `attach_path_contexts` seam, vec0 batching constraint, per-format touchpoints, MCP forwarding, status line |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Quality gates: `ruff check src tests`, `ruff format --check src tests`, `pytest` (fail_under=90 active, `--cov` in addopts), `ty check src/sif` — all new code fully type-annotated
- Style: Python 3.10+, `list[str] | None` union syntax, line length 100, max complexity (mccabe) 10, ruff isort `combine-as-imports`, stdlib → third-party → `sif` import order, two blank lines after imports
- CLI errors via `click.ClickException(str(e))`; database transactions via `Database.transaction()` with automatic rollback
- Logging: `logger = get_logger(__name__)`, names prefixed `sif`, output to **stderr**
- Project skills exist (`sif-get`, `sif-search`) — they drive `sif -q search ... --json`; stdout cleanliness under `--json` (D-07) protects these consumers
- Docs: `docs/cli-reference.md` / `docs/configuration.md` are generator-owned — never hand-edit; regenerate via `make docs-generate`
- GSD: run full quality suite after every plan completes within the phase

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Drift detection (stat walk + mtime compare) | CLI command layer helper (indexing-adjacent service) | Database (read-only `documents` query) | D-01 locks placement in the CLI layer so bench/MCP bypass by construction; the walk itself is presentation-free |
| Drift refresh (BM25-only writes) | `IncrementalIndexer.update_paths` (application/indexing layer) | `index_lock` flock (infrastructure) | The per-path seam 12-D06 built for exactly this consumer; refresh burst is just another invoker under the collision contract |
| Staleness computation | Search layer enrichment seam (sibling of `attach_path_contexts`) | — | D-09: one code path covering BM25Searcher/VectorSearcher/HybridSearcher exits = CLI search/query + MCP + (benignly) bench |
| Staleness presentation | CLI output formatters (search.py format battery) | MCP backend mapping (backend.py) | Formats are CLI-owned; MCP re-maps fields explicitly and must forward the flag |
| Vector-lag status line | CLI `status_cmd` (main.py) | SchemaManager stats | Extends the Phase 13 Watch-section pattern; degraded rendering never takes status down |
| Settings + docs | `config/settings.py` + `scripts/generate_config_ref.py` SECTIONS allowlist | — | New `SIF_` fields reach configuration.md only via the generator |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| (stdlib) `pathlib.Path.rglob` / `os.stat` | Python 3.10+ | The drift walk | Already `FileScanner.scan`'s engine; zero new deps [VERIFIED: src/sif/indexing/scanner.py:129-139] |
| (stdlib) `sqlite3` | bundled | mtime compare target + staleness SQL | `documents.mtime REAL` exists; vec0 `document_embeddings` queryable by metadata column [VERIFIED: src/sif/database/schema.py:69, 341-348] |
| `IncrementalIndexer.update_paths` | in-repo (Phase 12) | The refresh itself | Presentation-free, stat-decides, missing-root guarded, `matches()`-filtered [VERIFIED: src/sif/indexing/incremental.py:164-247] |
| `index_lock` (fcntl flock) | in-repo (Phase 11) | Single-writer arbitration for the refresh burst | Per-DB lock, wait-then-run deadline; the burst is one more invoker [VERIFIED: src/sif/database/locking.py:42-98] |
| Rich | existing dep | Dim inline marker in table + status row | Already the table/markup stack; `escape()` discipline for titles |
| Click | existing dep | `--no-refresh` flag (if added); `click.echo(..., err=True)` for stderr notices | The stderr contract needs Click's `err=True` — the module `Console()` writes to **stdout** (see Pitfall 5) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `FileScanner.scan` / `FileScanner.matches` | in-repo | Walk with the ONE exclusion predicate (pattern + defaults + settings + per-collection ignores) | Always — scan/watch/pre-command must share membership semantics [VERIFIED: src/sif/indexing/scanner.py:61-101] |
| `attach_path_contexts` (as pattern) | in-repo | The batched-enrichment seam to sibling | The staleness marker copies this shape: one constant SQL, decorate in Python [VERIFIED: src/sif/search/context_attach.py:24-62] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| mtime-only drift compare | mtime + persisted `st_size` | Persisting `st_size` in `_process_file` would make size usable, but changes `documents.file_size` semantics for every existing consumer (`to_dict`, `get_stats` SUM) and touches the shared core for marginal benefit — mtime alone is sufficient and exact (Finding A2) |
| Derived "no embeddings" signal | An `embedded_at`/flag column | Rejected by D-08 (schema change; 4+ write paths must maintain it — the silent-lie bug class). Derived stays truthful by construction |
| One flock window for the whole multi-collection refresh | Per-collection lock windows (watch's per-job shape) | Both fit the contract; one window is simpler and the drift set is already bounded by the cap. Watch precedent is per-job because bursts arrive per-collection [VERIFIED: src/sif/indexing/watcher.py:736-745] |

**Installation:** Nothing to install — **zero new runtime dependencies** (locked decision; verified `pyproject.toml` untouched by this phase).

**Version verification:** Not applicable — no external packages recommended or introduced.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | Phase installs nothing |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
sif search / vsearch / query          (CLI command layer — the ONLY tier that runs the check)
        │
        ├─ resolve collections (-c names | --all → list_all | default → list_enabled)
        │           │  (today: names→IDs only, Collection objects discarded — refactor to keep both)
        │           ▼
        │   [NEW] drift check (D-01..D-07)  ── disabled? (SIF_ setting / --no-refresh) ──► skip, search as-is
        │           │
        │           ▼
        │   stat walk: FileScanner.scan(root)  ×  lightweight SELECT path,mtime FROM documents
        │           │           (read-only, lock-free, no writes when clean)
        │           ▼
        │   DriftReport { drifted paths per collection, deleted paths, new files, count }
        │           │
        │     count == 0 ──► silence (SC2 clean path; never touches the lock file)
        │     count > cap ──► NO refresh + stderr warning naming count + 'sif index update' remedy (D-05)
        │     0 < count ≤ cap
        │           │
        │           ▼
        │   with index_lock(db_path, settings.lock_wait_timeout):     ◄── the watcher's exact burst shape
        │       IncrementalIndexer(conn).update_paths(collection, drifted ∪ deleted ∪ new)
        │           │            (BM25-only; purges chunks+vectors of changed docs — never embeds)
        │           ▼
        │   stderr notice "refreshed N files (bm25) before search" (D-07; -q suppresses)
        │
        ▼
searcher / SearchPipeline.search(...)         (unchanged construction; bench + MCP never see the check)
        │
        ▼
result assembly exits:  BM25Searcher.search ─┐
                        VectorSearcher.search ─┼─ each calls attach_path_contexts(db, results)
                        HybridSearcher.search ─┘         + [NEW] mark_vector_staleness(db, results)
        │           (one batched scan of document_embeddings → Python set → stale = doc ∉ set)
        ▼
SearchResult.vectors_stale: bool  →  to_dict() → --json (automatic)
                                   →  Rich table / CSV / MD / XML formatters (explicit, D-12)
                                   →  MCP backend.hybrid_search mapping (explicit forward, D-11/B5)
        │
        ▼
≥1 stale? → stderr remedy hint "run 'sif embed'" after results (D-13; -q suppresses)

sif status  ──►  Rich table gains "Vector lag: N documents" row (D-10; degrade when vec0 missing)
```

### Recommended Project Structure (deltas only)

```
src/sif/
├── indexing/
│   └── drift.py            # NEW (recommended placement, discretion): presentation-free
│                           #   detect_drift(conn, collections) -> DriftReport
│                           #   refresh_drift(db_path, conn, report) -> IncrementalResult (flock-wrapped)
├── search/
│   └── staleness.py        # NEW (or extend context_attach.py): mark_vector_staleness(db, results)
├── core/
│   └── models.py           # SearchResult gains vectors_stale: bool = False + to_dict() entry
├── database/
│   └── repositories.py     # DocumentRepository gains lightweight list_stat_by_collection()
│                           #   (SELECT path, mtime — must NOT load content)
├── cli/
│   ├── commands/search.py  # shared _resolve_collections() helper; drift-check call in the trio;
│   │                       #   format battery gains the marker (csv/md/xml/table); stderr notices
│   └── main.py             # status_cmd gains Vector lag row
├── mcp/
│   └── backend.py          # hybrid_search mapping forwards vectors_stale (metadata or field)
├── config/
│   └── settings.py         # search-refresh enable toggle + max-files cap fields
└── scripts/generate_config_ref.py  # SECTIONS allowlist: register the new field names
```

### Pattern 1: The Refresh Burst Is the Watcher's BM25 Leg, Verbatim

**What:** The under-cap refresh reuses the exact lock-then-`update_paths` shape the foreground watch proved.
**When to use:** Always — do not invent a second write path.
**Example:**
```python
# Source: src/sif/indexing/watcher.py:741-742 and 776-782 (read this session), and
#         src/sif/cli/commands/index.py:53-57 (update_cmd's wrap)
# watcher._run_job -> BM25-only depth:
with index_lock(self._db_path, self._config.lock_timeout):
    result = self._run_burst(collection, folded)
# _run_burst, bm25 depth:
indexer = IncrementalIndexer(self._conn)
if self._config.depth != "embed":
    return indexer.update_paths(collection, paths, progress=progress)
```
The pre-command equivalent: `with index_lock(Path(index_path), settings.lock_wait_timeout): IncrementalIndexer(db.connection).update_paths(coll, drifted_paths)`. Acquire the lock **only after** the walk found under-cap drift — a clean search must never open/create the lock file (SC2).

### Pattern 2: Drift Walk — Stat Gate Before Any Parse

**What:** `update_paths` *parses* every candidate file (`self._parser.parse(file_path)` computes the sha256) — even unchanged files cost a full read [VERIFIED: src/sif/indexing/incremental.py:267, 272-276]. The walk is therefore the cheap gate: mtime mismatch/new/deleted decides the drifted set; `update_paths` then re-verifies via checksum (a touched-but-unchanged file costs one parse and lands in `unchanged` — correct and cheap).
**When to use:** Always — passing the whole tree to `update_paths` would re-read every file on every search.
**Example (shape, not gospel):**
```python
# Sketch — mtime-primary compare; size is NOT usable (Finding A2)
def detect_drift(conn, collections) -> DriftReport:
    repo = DocumentRepository(conn)
    drifted: dict[str, set[Path]] = {}
    for coll in collections:
        root = Path(coll.path)
        if not root.exists():          # mirror incremental.py:114-120 — rglob on a missing
            continue                   # root yields nothing; unguarded = phantom mass-delete drift
        disk = FileScanner().scan(root, pattern=coll.pattern,
                                  ignore_patterns=coll.ignore_patterns).files
        stored = {path: mtime for path, mtime in repo.list_stat_by_collection(coll.id)}
        seen: set[str] = set()
        for f in disk:
            key = str(f.resolve())     # resolve consistently (parser stores resolved paths)
            seen.add(key)
            st = f.stat()
            if key not in stored or stored[key] != st.st_mtime:   # float compare is exact (Finding A3)
                drifted.setdefault(coll.id, set()).add(f)
        for key in stored:             # deleted: in DB, never seen on the walk
            if key not in seen:
                drifted.setdefault(coll.id, set()).add(Path(key))
    return DriftReport(drifted)
```

### Pattern 3: Staleness Enrichment — Sibling of `attach_path_contexts`

**What:** Every searcher exit already calls one batched enrichment; add the staleness marker at the same sites.
**When to use:** Always — this is D-09's one-code-path contract made concrete.
**Verified call sites:** `src/sif/search/bm25.py:121`, `src/sif/search/vector.py:134`, `src/sif/search/hybrid.py:114` (SearchPipeline's default route goes through HybridSearcher's; its `lex:`/`vec:`/`hyde:` routes get it inside BM25Searcher/VectorSearcher).
**Example:**
```python
# Source: shape of src/sif/search/context_attach.py:24-62 (read this session)
def mark_vector_staleness(db, results):
    if not results:
        return results
    try:
        cursor = db.execute("SELECT document_id FROM document_embeddings")  # ONE full scan —
    except sqlite3.OperationalError:                                        # vec0 missing → no markers
        return results
    embedded = {row[0] for row in cursor}
    for r in results:
        r.vectors_stale = r.document_id not in embedded
    return results
```
Why one scan and not a correlated `NOT EXISTS` per result: sqlite-vec's own docs state vec0 metadata columns filter via full scans (no metadata index) [CITED: github.com/asg017/sqlite-vec `site/features/vec0.md`], and the in-repo docstring prescribes batching for exactly this reason — verbatim: "The vec0 virtual table has no index on its metadata columns, so each per-document filtered lookup costs a full table scan; callers judging every document must batch." [VERIFIED: src/sif/search/vector.py:221-228]

### Anti-Patterns to Avoid

- **Deeper placement of the drift check** (searchers/pipeline): silently re-adds cost to bench (Phase 16 latency) and changes MCP behavior — D-01's whole point [VERIFIED: bench builds `SearchPipeline` directly, src/sif/cli/commands/bench.py:95-121; MCP backend likewise, src/sif/mcp/backend.py:95-100]
- **Partial over-cap refresh:** mixes fresh and stale docs in one ranking with no signal which — D-05 locks skip-and-warn
- **A watermark/throttle table:** D-02 locks stateless-every-invocation
- **New chunk/vector write paths:** `update_paths` is the only seam; embed NEVER happens here (LIVE-05)
- **Per-result staleness queries:** N full vec0 scans per page (Pattern 3)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Incremental BM25 refresh | A bespoke reindex loop | `IncrementalIndexer.update_paths` | The 12-D06 seam; stat-decides, missing-root guard, `matches()` filter, per-file txns all inside [VERIFIED: incremental.py:164-247] |
| Directory walk + exclusions | Custom rglob + ignore list | `FileScanner.scan` / `matches` | The ONE shared predicate — pre-command must not invent membership rules scanner/watch don't have [VERIFIED: scanner.py:61-101] |
| Writer arbitration | PID checks, stand-down protocols | `index_lock` per burst | flock semantics; stale-lock-proof; the collision contract all hosts already follow [VERIFIED: locking.py:42-98] |
| Result enrichment | Per-command marker code | Seam sibling of `attach_path_contexts` | 3 call sites cover every surface incl. MCP [VERIFIED: bm25.py:121, vector.py:134, hybrid.py:114] |
| Vector-lag detection | Schema column / watermark | Derived existence SQL | D-08: derived cannot drift from reality; a column must be maintained by 4+ write paths |

**Key insight:** Phase 14's entire risk lives in *gating and placement* — making sure the expensive machinery (`update_paths`, flock, parses) runs only when the cheap detector says so, and only in the CLI layer. Everything expensive already exists and is battle-tested by Phases 11–13.

## Common Pitfalls

### Pitfall 1: `documents.file_size` is body length, not on-disk size — a size compare false-positives forever

**What goes wrong:** The CONTEXT says "mtime/size vs documents table", but `Document.file_size` defaults to `len(self.content.encode())` of the frontmatter-**stripped** body [VERIFIED: src/sif/core/models.py:151-152 — `self.file_size = len(self.content.encode())`], and `_process_file`'s update branch refreshes mtime but **never file_size** [VERIFIED: src/sif/indexing/incremental.py:291-299 — sets content/title/metadata/mtime/checksum, not file_size]. Comparing `st_size != file_size` flags every file with frontmatter as drifted, permanently — the refresh would parse it, checksum-skip it, and flag it again next search.
**How to avoid:** Compare **mtime only** (exact float equality — see Pitfall 2). If size must participate, that requires first persisting `stat.st_size` in `_process_file` (shared-core change, semantics shift for `to_dict`/`get_stats`) — recommend NOT doing that this phase; flag as an open question.
**Warning signs:** "refreshed N files" notice firing on every search of a never-touched index.

### Pitfall 2: Assuming mtime float compare is fuzzy

**What goes wrong:** Fear of float compare leads to epsilon tolerances or string casts.
**Why it's safe:** `os.stat().st_mtime` is a C double; SQLite `REAL` is an IEEE 754 double; the round-trip is bit-exact [VERIFIED: local probe this session — `mtime roundtrip exact: True (1794103738.2293167)`]. Stored mtime comes from `stat.st_mtime` at parse time [VERIFIED: src/sif/indexing/parser.py:47-48] and is refreshed on every content update [VERIFIED: incremental.py:294].
**How to avoid:** Plain `!=` on the float. `os.utime` in tests sets exact mtimes deterministically.

### Pitfall 3: D-08's literal formula ("has chunks but no embeddings") never fires for the real lag state

**What goes wrong:** Chunks are created ONLY by `embed_cmd` [VERIFIED: src/sif/cli/commands/index.py:337-355 — `chunks = chunker.chunk(doc.content)` + `chunk_repo.create(chunk)`] and the watcher's embed session; the BM25-only update path deletes chunks AND embeddings together, creating none [VERIFIED: src/sif/indexing/incremental.py:286-288 — `self._chunk_repo.delete_by_document(existing.id)` + `self._vector_purger.delete_embeddings_by_document(existing.id)`]. Durable states: never-embedded = no chunks/no embeddings; embedded = both; **BM25-updated-after-embed (the tiered-depth lag) = no chunks/no embeddings**. "Has chunks but no embeddings" only matches crash-leftover states.
**How to avoid:** The derived signal that satisfies SC3 ("vectors lag behind BM25/FTS") is **stale = document has no rows in `document_embeddings`**. Same D-08 virtues: derived, schema-free, cannot lie (BM25 updates purge; embed's per-collection delete-before-insert transaction keeps chunks-without-embeddings transient [VERIFIED: index.py:312-358 — one `with db.connection:` txn per collection]). Consequence to surface honestly: never-embedded docs are also marked (they genuinely cannot appear in vsearch/hybrid's vector leg; the `sif embed` remedy is correct). Noise-control option at discretion: gate marking on the index having ≥1 embedding overall so pure-BM25 users see no markers.
**Warning signs:** A staleness test that constructs "chunks without embeddings" via raw SQL and passes while production never marks anything.

### Pitfall 4: The walk on a missing root reads as mass deletion

**What goes wrong:** `FileScanner.scan` on a nonexistent root yields an empty file list (the rglob-yields-nothing behavior 12-D11 documented [VERIFIED: src/sif/indexing/incremental.py:111-114 comment: "rglob on a missing root yields no files, which the sweep below would otherwise treat as 'every file vanished'"]). `update_paths` guards this, but the WALK runs first — unguarded, every stored doc counts as "deleted" drift, blows the cap, and warns about phantom drift on every search of an unmounted collection.
**How to avoid:** Skip the walk (once, with a warning) for collections whose root doesn't exist — mirror the guard the shared core already has.

### Pitfall 5: Rich `Console()` writes to stdout — the stderr contract needs `err=True`

**What goes wrong:** D-07/D-13 require notices/warnings/hints on **stderr** so `--json`/`--csv` stdout stays pipeable. The search module's `console = Console()` defaults to **stdout** [VERIFIED: src/sif/cli/commands/search.py:26 — `console = Console()`; Rich's default stream is stdout]. Copying the neighboring `console.print(...)` pattern for the new notices puts them on stdout and corrupts JSON piping.
**How to avoid:** Use `click.echo(msg, err=True)` (or a dedicated stderr `Console(file=sys.stderr)`) for: the under-cap refresh notice, the over-cap warning, and the remedy hint. `set_quiet`/`-q` gates them.

### Pitfall 6: Clean search acquires the lock "just in case"

**What goes wrong:** Wrapping the whole check in `index_lock` unconditionally makes every clean search open/create the lock file (`os.open(..., O_CREAT)` runs on entry) [VERIFIED: src/sif/database/locking.py:70] and pay flock syscalls — violating SC2's "zero locks when clean" and littering `.lock` files next to freshly-created indexes.
**How to avoid:** Order: walk (read-only) → count → only if `0 < count ≤ cap` acquire the lock and refresh.

### Pitfall 7: `list_by_collection` loads full content into the walk

**What goes wrong:** The natural "get the stored side" call is `DocumentRepository.list_by_collection`, but it is `SELECT *` — content included [VERIFIED: src/sif/database/repositories.py:192-198] — so the "near-zero cost" walk would read every document's text from SQLite.
**How to avoid:** Add a lightweight repository method (`SELECT path, mtime FROM documents WHERE collection_id = ?` — the `idx_documents_collection` index exists [VERIFIED: schema.py:353-356]).

### Pitfall 8: MCP silently drops the new field

**What goes wrong:** D-11 says the MCP response carries the flag "automatically", but `backend.hybrid_search` re-maps every field explicitly into `sif.mcp.protocol.SearchResult` (fields: doc_id/path/title/content/score/highlights/metadata) [VERIFIED: src/sif/mcp/backend.py:100-112; protocol.py:199-208]. Unknown core-model fields are dropped at this boundary.
**How to avoid:** Forward explicitly — either `metadata={"rank": ..., "collection_name": ..., "vectors_stale": r.vectors_stale}` (zero protocol change; `model_dump()` at handlers serializes it) or a real protocol field. One line; D-09's computation-level one-code-path still holds.

### Pitfall 9: Settings fields missing from the SECTIONS allowlist silently miss docs

**What goes wrong:** `docs/configuration.md` is rendered from `SECTIONS` in `scripts/generate_config_ref.py` [VERIFIED: scripts/generate_config_ref.py:150-190 — field names enumerated per section]. A field added to Settings but not registered there never appears in docs, and `tests/test_docs.py` gates drift.
**How to avoid:** Register the new field names (natural home: "Search Settings" or a small new subsection) in the same change, then `make docs-generate`.

### Pitfall 10: Path-resolution mismatch between walk and stored paths

**What goes wrong:** Stored `documents.path` values are resolved (`str(file_path.resolve())` [VERIFIED: parser.py:74]; `update_paths` resolves candidates [VERIFIED: incremental.py:203]). Comparing unresolved walk paths against stored resolved strings mismatches on symlinked roots (macOS `/tmp` vs `/private/tmp` — the exact trap `context_attach.py`'s docstring recounts).
**How to avoid:** Resolve walk paths before comparing (`.resolve()`), as the sketch in Pattern 2 does.

### Pitfall 11: Timing-based drift tests

**What goes wrong:** Tests that `sleep(0.1)` for mtime to advance, or assert wall-clock budgets for SC2 — flaky.
**How to avoid:** Deterministic drift: `os.utime(path, (t, t))` with explicit distinct timestamps, or write-content changes (mtime advances). SC2's "near-zero" is evidenced by the local probes below + asserting no writes occurred (e.g., lock file absent, DB mtime unchanged) rather than a latency assert. Culture: 11-D08/D-09, 12-D15.

## Code Examples

### Verified: the three seam call sites to extend

```python
# Source: src/sif/search/bm25.py:119-121 (identical shape at vector.py:132-134, hybrid.py:112-114)
def _attach_contexts(self, results: list[SearchResult]) -> list[SearchResult]:
    """Attach path context descriptions to search results via batch query."""
    return attach_path_contexts(self.db, results)
# The staleness sibling is called right beside each of these.
```

### Verified: SearchResult and to_dict today (where the boolean lands)

```python
# Source: src/sif/core/models.py:207-237 (verbatim field list)
@dataclass
class SearchResult:
    """A search result."""

    document_id: str
    title: str
    path: str
    collection_name: str
    score: float
    content: str | None = None
    highlights: list[str] = field(default_factory=list)
    rank: int = 0
    scores: dict[str, float | None] = field(default_factory=dict)
    snippet: str | None = None
    context_description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        ...
# Add: vectors_stale: bool = False (after context_description) + "vectors_stale": self.vectors_stale
# in to_dict(). The --line-numbers path preserves new keys: add_line_numbers_to_results
# copies dicts and only adds 'line_numbers' [VERIFIED: src/sif/cli/formatters.py:11-25].
```

### Verified: where the check slots into each command

```python
# Source: src/sif/cli/commands/search.py:198-227 (search_cmd; vsearch 379-405 and query 517-546
# have the same shape)
with Database(index_path) as db:
    db.init_schema()
    options = SearchOptions(...)
    # collection resolution: -c → get_by_name per name | --all → None (unfiltered) |
    # default → list_enabled() ids   [VERIFIED: search.py:209-222, 389-401, 531-544]
    ...
    # [NEW] drift check goes HERE: after resolution (needs Collection objects), before
    # searcher/pipeline construction. `--all` currently leaves collection_ids=None —
    # the walk must then use ALL collections (repo.list_all()).
    with db.connection:
        searcher = BM25Searcher(db.connection)
        results = searcher.search(query, options)
```

### Verified: CSV/MD/XML headers the marker joins

```python
# Source: src/sif/cli/commands/search.py:85 (CSV header, verbatim):
#   buf.write("rank,score,title,path,collection\n")
# MD per-result block starts: f"## {_field(r, 'rank')}. {_field(r, 'title')}"  (search.py:104)
# XML per-result element: f'  <result rank="{_field(r, "rank")}" score="{score}">'  (search.py:127)
# _field() reads attributes on SearchResult rows and keys on --line-numbers dicts (search.py:72-74),
# so `vectors_stale` is readable from both row shapes.
```

### Test sketch: deterministic drift + cap boundary

```python
# tmp_path collection; index via IncrementalIndexer/CLI; then:
(path_a).write_text("# changed")                    # content drift (mtime moves)
os.utime(path_b, (1_700_000_000, 1_700_000_000))    # pure touch drift, deterministic
(path_c).unlink()                                   # deletion drift
# under cap: refreshed == 3 (a updated, b unchanged-after-parse, c removed); notice on stderr
# over cap (set SIF_...MAX_FILES=2 via runner env): NO refresh — DB unchanged,
#   warning names 3 and the 'sif index update' remedy; search still returns stale-but-hit docs
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `sif index update` before search when watch is off (v1.0 status quo) | Stat-gated bounded auto-refresh in the CLI search trio (this phase) | Phase 14 | The "always works even without watch" floor; doubles as event-overflow backstop (D-03) |
| Silent tiered-depth vector lag (Phase 12 D-10 accepted trade-off) | Derived staleness marker on every surface + status line | Phase 14 | Closes the Phase 12 deferral; no schema change |
| qmd-style mtime+size sync-state table (milestone FEATURES prior-art claim) | SIF: stateless per-invocation walk vs `documents.mtime` | — | NOTE: the qmd `file_sync_state` claim could NOT be re-confirmed by web search this session (DeepWiki's source analysis of tobi/qmd describes SHA-256-based change detection; [ASSUMED] as prior art). Irrelevant to feasibility — SIF's own mtime column and cost profile are verified in-repo and by local probe |

**Deprecated/outdated:** nothing in-repo; this phase adds, replaces nothing.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | qmd's `file_sync_state` mtime+size fast-path exists as described in milestone FEATURES.md | State of the Art | Cosmetic — prior-art citation only; SIF's mechanism is independently verified. Web search this session found no confirmation (DeepWiki says hash-based) |
| A2 | Cap default in the ~100–200 file range is a sensible "reasonable edit session vs branch switch" boundary | Open Questions | Low — value is a setting; any default is functionally safe; pick and document |
| A3 | Marking never-embedded docs as stale (in addition to BM25-refreshed docs) is acceptable UX, optionally gated on index-has-embeddings | Findings B1/Pitfall 3 | Medium — if unwelcome, users who never embed see markers on every result; the gate option mitigates; needs a decision at plan time (discretion area) |
| A4 | A file touched-but-unchanged (mtime moved, content same) counts as drift and refreshes to `unchanged` at cost of one parse | Pattern 2 | Low — self-consistent behavior; alternative (checksum in the walk) re-reads files, defeating the cheap gate |

## Open Questions (RESOLVED)

All three resolved at plan time; decisions encoded in 14-01-PLAN.md / 14-02-PLAN.md.

1. **Does the size half of "mtime/size" need to exist at all?** — RESOLVED: mtime-only.
   - What we know: `documents.file_size` is body-byte-length, stale on updates (Pitfall 1); mtime alone is exact and sufficient.
   - Resolution (14-01): drift compare is mtime-primary; `st_size` is NOT persisted; the size column's misleading semantics are noted in the drift helper's docstring. Capability unchanged — content changes always move mtime.
2. **Marker on never-embedded docs — ungated or gated on index-has-embeddings?** — RESOLVED: gated on index-has-embeddings.
   - What we know: both are schema-free derivations; ungated is maximally honest, gated avoids nagging pure-BM25 users (A3).
   - Resolution (14-02): markers activate only when the index has at least one embedding; either reading satisfies QUAL-06's letter; tests assert the gate (zero-embedding index → no markers, no remedy hint).
3. **`--no-refresh` flag in addition to the setting?** — RESOLVED: yes.
   - Resolution (14-01 Task 2): `--no-refresh` added to all three trio commands, for symmetry with explicit-control flags; `SIF_SEARCH_REFRESH_ENABLED` remains the master off-switch.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | everything | ✓ (local probes ran) | system python3 | — |
| sqlite-vec extension | staleness SQL, vector-lag status line | conditional (existing runtime fact) | 0.1.9 floor in pyproject | degrade: no markers, status shows n/a (Pattern 3 try/except; table creation is conditional [VERIFIED: schema.py:315-323]) |
| watchdog | nothing new (watch hosts already own it) | ✓ (Phases 12–13 shipped on it) | >=4.0.0,<7.0.0 | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** sqlite-vec absence — handled degradation path above (existing codebase pattern).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-cov (addopts `--cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths `tests`, fail_under=90) |
| Quick run command | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_search.py -x` |
| Full suite command | `env -u FORCE_COLOR NO_COLOR=1 pytest` |

(The env prefix is a project-specific requirement: the suite fails spuriously under `FORCE_COLOR`; unsetting it — not setting it to 0 — plus `NO_COLOR=1` is the verified invocation.)

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIVE-10 | Drift helper: mtime/new/deleted detection; missing-root skip; resolve-consistent compares | unit | `pytest tests/unit/indexing/test_drift.py -x` | ❌ Wave 0 |
| LIVE-10 | Cap boundary: N refreshed / N+1 skipped+warned; count-first (no parse when over cap) | unit | `pytest tests/unit/indexing/test_drift.py -x` | ❌ Wave 0 |
| LIVE-10 | Clean index: zero writes, no lock file created, no notice (SC2) | unit | `pytest tests/unit/cli/test_search.py -k refresh -x` | ✅ extend |
| LIVE-10 | Trio integration: search/vsearch/query refresh drifted docs before searching; `-q` and setting/flag opt-out honored; stderr-not-stdout notices (CliRunner `mix_stderr=False`-style separation) | unit (CliRunner) | `pytest tests/unit/cli/test_search.py -x` | ✅ extend |
| LIVE-10 | Coexistence: refresh burst under flock vs a held lock (wait-then-run) — reuse the 11-D08 parent-holds-lock pattern | subprocess/unit | `pytest tests/unit/cli/test_index_locking.py -x` (pattern home) | ✅ extend |
| QUAL-06 | Staleness enrichment: embedded→unmarked; never-embedded/BM25-refreshed→marked; vec0-missing→no markers | unit | `pytest tests/unit/search/test_staleness.py -x` | ❌ Wave 0 |
| QUAL-06 | Format battery: JSON key (incl. `--line-numbers`), CSV column, MD/XML annotation, table render | unit | `pytest tests/unit/cli/test_search.py -k stale -x` | ✅ extend |
| QUAL-06 | MCP forwarding: backend.hybrid_search mapping carries the flag | unit | `pytest tests/unit/mcp/ -k stale -x` | ✅ extend (tests/unit/mcp exists) |
| QUAL-06 | Regression: BM25-only update leaves doc embeddings-free (the D-08 invariant the signal rests on) | unit | `pytest tests/unit/indexing/test_incremental.py -x` | ✅ extend |
| QUAL-06 | `sif status` Vector lag row; degraded rendering when vec0 missing | unit | `pytest tests/unit/cli/test_status.py -x` | ✅ extend |

### Sampling Rate
- **Per task commit:** `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit -x -q` (or the targeted files above)
- **Per wave merge:** full suite — `env -u FORCE_COLOR NO_COLOR=1 pytest`
- **Phase gate:** full suite + `ruff check src tests` + `ruff format --check src tests` + `ty check src/sif` green before `/gsd-verify-work`; docs regenerated (`make docs-generate`) when settings/flags land, with `tests/test_docs.py` green

### Wave 0 Gaps
- [ ] `tests/unit/indexing/test_drift.py` — drift helper + cap behavior (LIVE-10)
- [ ] `tests/unit/search/test_staleness.py` — enrichment seam (QUAL-06)
- [ ] No new framework/config needed — existing infrastructure covers the phase

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No new auth surface (local CLI; no network) |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (weakly) | Drift set comes from the FS walk, not user input; all DB access via existing parameterized repositories; the staleness boolean is computed, never parsed from input. Collection names via `-c` flow through `get_by_name` (parameterized) as today |
| V6 Cryptography | no | — |

### Known Threat Patterns for this phase's stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path-based confusion (symlinked roots, `/tmp` vs `/private/tmp`) | Tampering | Resolve all walk paths before compare (Pitfall 10); the walk is scoped to registered collection roots via `matches()` — no traversal outside roots [VERIFIED: scanner.py:86-88 `is_relative_to(root)`] |
| Content leakage through notices/logs | Information Disclosure | Notices name counts and commands, never document content (project logging discipline: content never logged; stderr paths only at debug) |
| XML output injection via marker | Tampering | Marker is a boolean rendered as an attribute value (`vectors_stale="true"`); it is not document-derived text — no sanitizer surface added, but keep the Phase 10.1 `quoteattr` discipline for any wording variant |
| DoS via pathological trees during walk | DoS | The cap bounds refresh work; the walk itself is one rglob+stat pass (~43 ms @ 5k files, verified locally) and is disableable via the SIF_ setting (locked: disableable) |
| Lock-file creation on clean search (touching `sif.db.lock` as a side effect) | — (hygiene) | Gate lock acquisition behind detected under-cap drift (Pitfall 6); file already created `0600` [VERIFIED: locking.py:70] |

No new network surface, no new dependencies, no secrets handling — threat profile unchanged from Phase 13.

## Sources

### Primary (HIGH confidence)
- Direct reads this session of: `src/sif/indexing/incremental.py` (full), `src/sif/indexing/scanner.py` (full), `src/sif/core/models.py` (full), `src/sif/indexing/parser.py` (ParsedDocument + MarkdownParser), `src/sif/database/repositories.py` (Collection/Document repos), `src/sif/database/schema.py` (full), `src/sif/database/locking.py` (full), `src/sif/database/database.py` (get_stats), `src/sif/cli/commands/search.py` (full), `src/sif/search/bm25.py` (full), `src/sif/search/hybrid.py` (full), `src/sif/search/context_attach.py` (full), `src/sif/search/vector.py` (embedding query paths), `src/sif/cli/commands/index.py` (update_cmd + embed_cmd), `src/sif/indexing/watcher.py` (burst/reconcile), `src/sif/cli/commands/bench.py` (search_fn), `src/sif/mcp/backend.py` (hybrid_search), `src/sif/mcp/protocol.py` (SearchResult), `src/sif/mcp/handlers.py` (query tool), `src/sif/cli/main.py` (status_cmd), `src/sif/config/settings.py` (full), `src/sif/cli/formatters.py` (add_line_numbers_to_results), `scripts/generate_config_ref.py` (SECTIONS), `tests/conftest.py`, `pyproject.toml` (pytest/coverage)
- Local probes (this machine, 2026-11-08): 5000-file rglob+double-stat ≈ 42.6 ms; single-stat pass ≈ 7.8 ms; `st_mtime` float round-trip through SQLite REAL bit-exact
- Milestone research already in repo: `.planning/research/STACK.md` (#8 recipe, overflow-backstop rationale), `ARCHITECTURE.md` (pre-search flow sketch, "cheap first" + >N cap), `FEATURES.md` (staleness semantics), `PITFALLS.md` (Pitfall 5 double-writer) — read this session

### Secondary (MEDIUM confidence)
- sqlite-vec official vec0 documentation (github.com/asg017/sqlite-vec `site/features/vec0.md`) — metadata columns filterable but via full scans; auxiliary columns not filterable — corroborates the in-repo batching rule
- qmd DeepWiki source analysis (deepwiki.com/tobi/qmd) — SHA-256-based change detection; conflicts with the `file_sync_state` claim (see A1)

### Tertiary (LOW confidence)
- The qmd `file_sync_state` prior-art claim from milestone FEATURES.md — unconfirmed this session; treated as [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new deps; everything verified in-repo
- Architecture: HIGH — seam call sites, command shapes, and burst patterns read directly; three CONTEXT-assumption corrections carry file:line evidence
- Pitfalls: HIGH — all codebase-grounded (file:line or local probe); the one external claim (qmd) explicitly downgraded

**Research date:** 2026-11-08
**Valid until:** 2026-12-08 (stable domain — in-repo integration; re-verify only if Phases 11–13 code moves)
