# Phase 14: Freshness Floor (Pre-Command Refresh + Staleness Marking) - Context

**Gathered:** 2026-11-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Two capabilities on top of the Phase 11/12 machinery — the "always works even without watch" floor:

1. **Pre-command drift refresh (LIVE-10)** — with no watch/daemon running, the CLI search commands stat-check the collections being searched and refresh drifted files (BM25-only) before searching:
   - stat-based drift detection (mtime/size vs `documents` table — no hashing) via a walk of the searched collections' roots
   - clean index pays near-zero cost (read-only, lock-free walk; no refresh work, no writes)
   - drift refresh is capped so a branch switch never becomes a hidden full reindex
2. **Staleness marking (QUAL-06)** — search results for documents whose vectors lag behind BM25/FTS (tiered depth without `--embed`) carry a visible staleness marker across all output surfaces, plus a vector-lag line in `sif status`.

NOT in scope: any new watch host (Phases 12–13 done), search-quality tuning (Phases 15–16: weights, suggestions, reranker, bench metrics), auto-embed of stale docs (explicit `sif embed` remains the only vector refresh path — LIVE-05), MCP-side pre-command refresh (MCP freshness is `SIF_MCP_WATCH`'s job), match-time typo tolerance.

</domain>

<decisions>
## Implementation Decisions

### Pre-command check scope & cadence (LIVE-10)
- **D-01:** **Search trio only** — `sif search`, `sif vsearch`, `sif query` run the drift check; get/multi-get/ls/pull do not. The check lives in the **CLI command layer** (`cli/commands/search.py`), NOT in the searchers or `SearchPipeline` — so `sif bench` (invokes searchers directly, `bench.py:91`) and the MCP server bypass it by construction; bench latency stays measurement-clean for Phase 16. — **Reversibility:** costly — moving the check deeper later re-touches every search entry point.
- **D-02:** **Every invocation, stateless** — no watermark table, no throttle window. Each search pays one stat walk (~<50ms at personal-KB scale per research). Clean index = read-only walk, zero writes, zero locks (SC2's near-zero cost). No "checked N seconds ago" staleness window to reason about.
- **D-03:** **Always run, even when a watch/daemon is live** — the check doubles as the event-overflow backstop (kernel queues silently drop events; research STACK #99). Host detection is unreliable anyway: only the detached daemon writes a PID file; foreground watch and MCP watch leave no trace a CLI process can see. When watch already handled everything, the walk finds zero drift (stat-decides no-op); when drift is found mid-watch-burst, per-burst flock + wait-then-run (11-D02, 12-D04) arbitrates.
- **D-04:** **Sweep only the collections being searched** (respecting `-c`/`--all` filters) — cost proportional to what the search will actually query; the results you're about to see are exactly the fresh ones. Un-searched collections drift until searched or `sif index update`.

### Over-cap behavior (SC2)
- **D-05:** **Over-cap = skip refresh entirely + warn** — count drifted files first (the stat walk already knows); if count > cap, do NO refresh, search proceeds on the stale index, and a prominent stderr warning names the drift size and says to run `sif index update`. Rationale: partial refresh would mix fresh and stale docs in one ranking with no way to tell which; the branch-switch pathology should be surfaced, not half-fixed. (Research recipe verbatim: "skip if >N files changed — tell the user to run `index update`.") Search never becomes an error because the index drifted.
- **D-06:** **Cap shape = file count** via an `SIF_` setting (e.g. `SIF_SEARCH_REFRESH_MAX_FILES`, exact name/default = Claude's discretion). Deterministic — the project's test culture (11-D08/D-09, 12-D15) can assert exact over-cap/under-cap behavior with no timing flakiness. A file-count cap directly bounds parse/write work.
- **D-07:** **Visibility contract** — under-cap refresh prints ONE stderr notice (e.g. `refreshed 3 files (bm25) before search`); stdout stays clean for `--json`/`--csv` piping; `-q/--quiet` suppresses. The over-cap warning is also stderr. Silence when clean (research: "quiet when nothing changed").

### Staleness signal (QUAL-06)
- **D-08:** **Derived at query time — no schema change** — stale = doc has chunks but no embeddings. This is true by construction: Phase 12 D-10 BM25-only updates purge stale chunks/vectors, and delete-before-insert keeps embedding state all-or-nothing per doc. Detect via a SQL existence check during result assembly. The signal cannot drift from reality because it IS reality (vs. an `embedded_at`/flag column that 4+ write paths must maintain — the silent-lie class of bug Phase 10.1 hunted).
- **D-09:** **All search surfaces, one code path** — the stale flag is computed in the shared result-assembly path so `search`, `query`, and the MCP query tool mark consistently. Note: the marker only ever FIRES on docs surfaced via the BM25/FTS leg — a vector-stale doc has no vector, so `vsearch` cannot return it. But wherever such a doc appears, it is marked.
- **D-10:** **`sif status` gains a vector-lag line** (e.g. `Vector lag: N documents`) — same derived SQL, glanceable index health; extends the Phase 13 Watch-section pattern in the existing Rich table.

### Marker presentation (SC3)
- **D-11:** **Boolean field on `SearchResult`** (e.g. `vectors_stale: true`, exact name = Claude's discretion) added to `to_dict()` — CLI `--json` AND the MCP query response carry it automatically, one code path.
- **D-12:** **All output formats** — Rich table: compact inline annotation next to the title (dim; exact glyph/wording = discretion), no new column. JSON: the boolean field. CSV: one extra column. Markdown: same inline annotation as the table. XML: an attribute (Phase 10.1 sanitizer story governs XML safety). SC3 (table + JSON) is the floor; no format silently drops a signal the others show.
- **D-13:** **Remedy hint** — when ≥1 result is stale, one stderr line after results (e.g. `3 results have stale vectors — run 'sif embed' to refresh`; wording = discretion; `-q` suppresses). Matches the over-cap warning's remedy pattern.

### Carried forward (pre-decided in research/prior phases — do not re-litigate)
- **BM25-only refresh, never embed** — pre-command refresh never computes embeddings (LIVE-05; the 13-D02 billing-surprise guard applies to every host the user didn't explicitly flag).
- **Reuse `IncrementalIndexer.update_paths`** — the per-path seam 12-D06 explicitly designed for this phase; stat-decides, cost ∝ drift size.
- **Stat-walk recipe** — walk collection roots, compare mtime+size vs `documents` table (no hashing; checksums only on drifted files via the existing incremental path). Sources: STACK #8, ARCHITECTURE pre-search sketch.
- **Disableable** — an `SIF_` setting turns the pre-command check off (research FEATURES #22 requirement); quiet-when-clean is likewise locked.
- **Missing-root guard** free via the shared core (12-D11) — a searched collection whose root is gone skips with a warning, never sweeps.
- **Per-burst flock + wait-then-run** (11-D01..D-03, 12-D04) — the refresh burst is just another `update_paths` invoker under the collision contract.
- **Zero new runtime dependencies.**
- **Docs are generator-owned** — new settings/flags reach `docs/cli-reference.md` / `docs/configuration.md` only via `make docs-generate` (12-03 precedent).

### Claude's Discretion
- `SIF_` settings field names (max-files cap, enable/disable toggle) and the cap's default value
- Whether the opt-out also gets a per-invocation flag (e.g. `--no-refresh`) in addition to the setting
- Drift-detection helper placement and shape (e.g. `indexing/` service vs CLI helper; how the walk reuses `FileScanner` short of checksums)
- Exact stderr notice/warning/hint wording; marker glyph/wording in table and Markdown; exact JSON field name
- How result assembly computes staleness (one batched SQL for the result set vs per-result check) as long as D-09's one-code-path contract holds
- Status-line wording and placement within the existing `sif status` table
- Lock-wait deadline used by the refresh burst (existing wait-then-run default is fine)
- Test scaffolding details (synthetic drift setups in `tmp_path`; deterministic over/under-cap assertions)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone research (authoritative recipes)
- `.planning/research/STACK.md` §"Key Integration Points" #8 — pre-command auto-detect recipe: per-collection bounded `stat()` sweep, BM25-only incremental on deltas, no new deps
- `.planning/research/STACK.md` (~line 99) — the pre-command check doubles as the watcher's overflow safety net (basis for D-03)
- `.planning/research/ARCHITECTURE.md` §pre-search flow sketch (~lines 208–216) — `stat_walk` → compare mtimes vs documents → drift-gated refresh; the "cheap first" guard and the >N-files cap rationale (basis for D-05/D-06)
- `.planning/research/ARCHITECTURE.md` §Integration (~line 300) — "CLI search commands ↔ staleness check: function call before pipeline construction; must stay optional + cheap" (basis for D-01)
- `.planning/research/FEATURES.md` §"Table Stakes" — pre-command staleness detection row (mtime+size stat scan → checksum-verified incremental path; quiet, bounded, disableable) + tiered-depth staleness semantics row (BM25 fresh / vectors stale until `sif embed`)
- `.planning/research/FEATURES.md` §"Staleness-aware search results" row — vector-lag marking rationale (silent quality cliff in hybrid fusion)
- `.planning/research/PITFALLS.md` §"Pitfall 5" — double-writer arbitration across watch forms (pre-command is the fourth writer; flock is the mechanism)

### Planning documents
- `.planning/REQUIREMENTS.md` — LIVE-10, QUAL-06 definitions; Out of Scope table (auto-embed rejected; watcher-as-sole-truth rejected — pre-command IS the backstop)
- `.planning/ROADMAP.md` §"Phase 14" — goal and success criteria 1–3 (the acceptance contract)
- `.planning/phases/12-sif-watch-foreground-mvp/12-CONTEXT.md` — D-06 `update_paths` seam (designed for this phase), D-10 purge-on-BM25-update (makes the derived staleness signal sound), D-11 missing-root guard
- `.planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/13-CONTEXT.md` — D-03 coexistence (stat-decides), D-08 status Watch-section pattern (D-10 extends it), D-02 BM25-forced-depth billing guard
- `.planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-CONTEXT.md` — flock contract (D-01..D-03), wait-then-run loser semantics, deterministic test culture (D-08/D-09)

### Project conventions
- `CLAUDE.md` — quality gates (pytest fail_under=90, ruff, ty), error-handling conventions, docs regeneration rule

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `IncrementalIndexer` (`src/sif/indexing/incremental.py:66`) — `update_paths()` (line 164, the per-path seam this phase consumes) + `update_collection()` (line 88); presentation-free via progress events; missing-root guard inside.
- `documents` table stat columns — `Document.mtime` / `Document.file_size` (`src/sif/core/models.py:139-140`) are persisted (`repositories.py:147`): the drift compare target already exists; no schema work for LIVE-10.
- `index_lock()` (`src/sif/database/locking.py:43`) — per-DB flock with wait-then-run deadline; the refresh burst acquires it exactly like a watch burst.
- `SearchResult` (`src/sif/core/models.py:208`) + `to_dict()` — where the staleness boolean lands; the same dict flows to CLI `--json` and the MCP query response (one change covers both, D-11).
- `FileScanner` (`src/sif/indexing/scanner.py`) — the walk + single exclusion predicate (`matches`); the stat sweep reuses its traversal short of checksum/parsing.
- `status_cmd` (`src/sif/cli/main.py` ~line 132) — Rich table that gained a Watch section in Phase 13; gains the Vector-lag line (D-10).

### Established Patterns
- Search trio entry points: `search_cmd` (`src/sif/cli/commands/search.py:170`), `vsearch` (:310), `query` (:454) — all already `with Database(...)`-shaped; the check slots in before searcher construction (D-01's CLI-layer placement).
- `sif bench` builds `SearchOptions` and calls searchers directly (`bench.py:91`) — bypasses any CLI-layer check by construction.
- Output format battery (table/JSON/CSV/MD/XML) lives in the search commands; XML passes through the Phase 10.1 sanitizer; CSV/MD/XML each need the marker (D-12).
- Settings → docs via generator SECTIONS allowlist (`watch_*` precedent, Phase 12); new `SIF_` fields follow the same path.
- Deterministic tests: synthetic setups in `tmp_path`, subprocess tests where parents hold/release the flock, generous deadlines, never naked sleep-polling (11-D08/D-09, 12-D15).

### Integration Points
- `src/sif/cli/commands/search.py` — the three command bodies gain the pre-command check call + stderr notices
- `src/sif/config/settings.py` — new fields: max-files cap, enable/disable toggle (names at discretion)
- `src/sif/core/models.py` `SearchResult.to_dict()` — the staleness boolean
- Result assembly (wherever results are built into `SearchResult`s — shared across search/query/MCP) — the batched staleness SQL per D-08/D-09
- `src/sif/cli/main.py` `status_cmd` — vector-lag line
- New drift-detection helper (placement at discretion) — stat walk + mtime/size diff vs DB, returning the drifted path set and its size (cap decision input)
- `pyproject.toml` — no dependency changes

</code_context>

<specifics>
## Specific Ideas

No specific external references — decisions above are self-contained. Construction insights worth preserving for the planner:

- **Bench/MCP bypass is architectural, not conditional**: placing the check in the CLI command layer (not the searchers) is what keeps bench latency clean for Phase 16 and MCP behavior unchanged — a deeper placement silently re-adds both costs.
- **The derived staleness signal rests on Phase 12 D-10's purge behavior** (BM25-only update deletes stale chunks+vectors): "chunks exist, embeddings missing" is exactly the lag state. If any future path keeps stale embeddings, D-08's signal degrades — worth a regression test asserting the invariant.
- **vsearch cannot return a vector-stale doc** (its vector was purged) — the marker effectively only fires on BM25/hybrid legs; tests should not try to construct a stale vsearch hit.
- **Over-cap counting is free**: the stat walk already produces the drifted set before any refresh work; cap evaluation is a `len()` check on it, so "count first, then decide" (D-05) costs nothing extra.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-Freshness Floor (Pre-Command Refresh + Staleness Marking)*
*Context gathered: 2026-11-08*
