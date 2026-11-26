---
phase: "19"
slug: "search-correctness"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-18"
verified: "2026-11-26"
---

# Phase 19 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verified by /gsd-secure-phase 19 on 2026-11-18 at HEAD `763753d` (ASVS L1, block_on high).
> Register authored at plan time: all nine PLANs carry STRIDE `<threat_model>` blocks. L1
> grep-depth verification confirmed every mitigation present; `threats_open: 0`.
> Re-verified 2026-11-25 at HEAD `2808c67` (24 rows) and 2026-11-26 with HEAD `4cf172c` at the checks
> and `8a79d0f` at the end of the run, the two identical outside `.planning/` (37 rows: the three
> gap-closure plans 19-10, 19-11 and 19-12 add T-19-24 to T-19-36); ASVS L1, block_on high;
> `threats_open: 0`.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| user file content → parser → canonical metadata JSON → SQLite | Untrusted frontmatter keys and typed values cross into hash input and persisted JSON | Titles, metadata keys/values, checksums |
| persisted convention marker → index-writing pass | A missing, stale, or forged marker decides whether every document is re-parsed | Collection id, convention version |
| watcher event path → embed leg | Watch events select documents for chunk/vector writes | Paths, reindexed path set |
| indexing progress callback → CLI/watch/MCP hosts | The migrate notice crosses the presentation-free event protocol | Event text, document counts |
| persisted contexts/staleness signals → search results | Trust markers consumed by CLI/MCP renderers and agents | Context descriptions, staleness booleans |
| pipeline exit paths → enrichment helper | Every return path must pass through the same composition | Result list identity |
| CLI flags / MCP request fields → SQL LIMIT/OFFSET | User-controlled pagination values reach SQLite | Integers (offset/limit), booleans |
| MCP input schema → Pydantic model | Two hand-maintained schemas must agree | Field names, types, defaults |
| vec0 KNN rows → result rows | Duplicate chunk rows are collapsed and identity metadata is selected | Chunk id, sequence, match counts |
| vector/BM25 lists → RRF → API results | Fusion keys and metadata merging decide what clients see | Document ids, chunk identity |
| sqlite_master FTS SQL → migration gate | Stored DDL decides whether the index is rebuilt | Table DDL text |
| document rows → FTS triggers | Title and content values cross into the external-content index | Titles, body text |
| title-weight parameters → SQL | Internal constants are bound into the BM25 expression | Numeric weights |
| MCP-only process startup → schema | A host that never runs a CLI command must still migrate | Embedding dimension, DDL |
| saved run → comparison gate | Baseline artifacts and query sets decide a defaults claim | Paths, checksums, ids, metrics |
| internal weight override → shipped constant | A measurement knob must not become a user-facing configuration surface | None (internal only) |
| indexed document paths and titles → terminal, CSV, Markdown, XML (19-10) | Document-derived text, file names and titles chosen by whoever wrote the files, crosses into every renderer | Paths, titles, `path#sequence` addresses |
| terminal width → table layout (19-10) | Rich's column allocation decides which characters of a cell survive, and the terminal crops what Rich lays out wider than the console | Column widths, rendered cell text |
| path-only output → shell pipelines and scripts (19-10) | `--files` and `-q` output is consumed by scripts and by tools such as `xargs` | Paths, one per line |
| the scratch cache → the user's real model cache (19-10) | The evidence step of Task 2 links the real model directory into a scratch cache, and a link is not read-only; a cached model other than the configured one would make `sif index embed` replace a directory of the real cache | Model directory link, cache state |
| the tree at the plan base → the evidence artifact (19-11) | The artifact is the record a later verifier reads instead of re-running the old behaviour, which no longer exists after plan 19-12 | Plan base SHA, measured values |
| the operator → the implementation plan (19-11) | The decision authorises a change to a published output contract; an unattended run must not make it | Option id, `Decision:` line |
| the capture commands → the user's index and caches (19-11) | The CLI is run to produce evidence; a wrong path would write into the default database or the default cache | `SIF_DB_PATH`, `SIF_CACHE_DIR` |
| CLI flag and MCP field → SQL predicate (19-12) | A user-supplied threshold reaches the FTS query of three commands and of MCP `lex_search` and `query`; edge values (0, negative, NaN, 1 and above) each have a defined outcome | `min_score` float, bound threshold |
| the searcher → every output format and MCP (19-12) | The displayed score is a published contract consumed by people, scripts and MCP clients | BM25 displayed score |
| the tree → the amended truth and the evidence artifact (19-12) | A later verifier re-derives truths from the plans; the plan and the code must agree | Amended truth, golden values |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-19-01 | Tampering | `canonical_metadata_json` / `documents.metadata` | medium | mitigate | `src/sif/core/models.py:19-72` recursive key coercion; canonical string bound as a SQL parameter (`repositories.py:192,274`); nested-mixed-key/typed-value tests | closed |
| T-19-02 | Denial of Service | parser selection | low | mitigate | `incremental.py:393` extension dispatch with `TextParser` fallback; `parser.py:99-126` bounded whole-file read | closed |
| T-19-03 | Tampering | `index_meta` convention marker | medium | mitigate | Per-collection `convention:<id>` key; marker written only when stored-document failures are zero (`incremental.py:155-160,210-212`); failure-path tests | closed |
| T-19-04 | Repudiation | metadata fast path | high | mitigate | Fast path only on exact stored-content equality (`incremental.py:437-446`); body change purges chunks/embeddings (`:456-458`); watcher embed set from `reindexed_paths` (`watcher.py:904-907`); count regressions | closed |
| T-19-05 | Denial of Service | forced migration on a large collection | low | accept | Per-file short transactions, resumable marker discipline, notice names the scanned count | closed |
| T-19-06 | Repudiation | context/staleness markers across exit paths | high | mitigate | One `enrich_results` composition (`context_attach.py:317-346`) called once per pipeline exit (`hybrid.py:352-379,484`); spy + marker-parity tests | closed |
| T-19-07 | Tampering | context matching via `normalize_path` | low | mitigate | Constant SQL, no interpolated path (`context_attach.py:51-53`); two-sided normalization (`:110,311`) | closed |
| T-19-08 | Repudiation | CLI/MCP enrichment ownership | high | mitigate | Exactly one enrichment in `search.py:613,871-874`; MCP fallback enriches, pipeline does not (`backend.py:490-678`); exact-set spy tests | closed |
| T-19-09 | Tampering | saved-run baseline integrity (B0) | medium | mitigate | `personal_bench.py:84,1597,1693` rejects `content`/`snippet`; envelope validation `:1714-1805`; fingerprint over path/checksum/size `:1226-1235` | closed |
| T-19-10 | Tampering | BM25/vector SQL | high | mitigate | Weights, threshold, limit, offset bound as parameters (`bm25.py:87,96-97,164`); `IntRange(min=0)` / `Field(ge=0)` reject negatives | closed |
| T-19-11 | Denial of Service | vector `fetch_k` / huge offset | medium | mitigate | `_MAX_FETCH_K = 2048` (`vector.py:25`); bounded seed `:197`; past-end offset returns an empty page | closed |
| T-19-12 | Repudiation | rank numbering and page continuity | medium | mitigate | Global ranks `offset + position` in every path (`bm25.py:181`, `vector.py:251`, `hybrid.py:55-67,484`); continuity tests | closed |
| T-19-13 | Denial of Service | `VectorSearcher` fetch_k escalation | medium | mitigate | Doubles only while the batch is exactly `fetch_k` and target unmet, clamped at `_MAX_FETCH_K` (`vector.py:204-231`); ceiling tests | closed |
| T-19-14 | Tampering | chunk identity metadata at fusion | medium | mitigate | RRF adopts only non-null `chunk_id`/`sequence`, `max(chunk_matches)` (`rrf.py:36-47,127-128`); best-distance winner (`vector.py:296-322`) | closed |
| T-19-15 | Information Disclosure | per-chunk fields in CLI/MCP output | low | accept | `SearchResult.chunk_id/.sequence/.chunk_matches` are index-local identity/count metadata; no content or new path | closed |
| T-19-16 | Tampering | MCP schema / re-map | high | mitigate | Fixed six-key re-map (`backend.py:190-197`) with exact-set assertions; published schema derived from the tool signature (Phase 22 successor, `tools.py`), drift structurally impossible; wire goldens | closed |
| T-19-17 | Repudiation | B0/B1 comparison evidence | medium | mitigate | Fingerprint never trusted as current (`personal_bench.py:2184-2201`); `compare_saved_run` grades only the saved set `:2270-2294` | closed |
| T-19-18 | Tampering | title-FTS rebuild / `documents_fts_v` | high | mitigate | Column-list detection from `sqlite_master` (`schema.py:497-503`); savepoint `:519`; vocab dropped before FTS, triggers dropped explicitly, exactly one `VALUES('rebuild')` `:529-574`; idempotence tests | closed |
| T-19-19 | Tampering | weighted `bm25()` SQL | high | mitigate | Weights and `min_score` appended to bound params (`bm25.py:84-97,122-164`); both branches `bm25(documents_fts, ?, ?)`; `1.0/1.0 == rank` pinned | closed |
| T-19-20 | Denial of Service | `create_all` on a populated database | low | accept | One-time rebuild gated by one `sqlite_master` read; atomic via savepoint | closed |
| T-19-21 | Tampering | MCP-only schema startup | high | mitigate | `SearchBackend.__init__` runs `init_schema` with its own dimension (`backend.py:274-295`); supplied dimension never consults `get_settings()` (`database.py:37-60`) | closed |
| T-19-22 | Repudiation | D-12 title-weight verdict | high | mitigate | Per-leg and per-leg×split noise gates (`personal_bench.py:487-499,2015-2048`); verdict artifact carries full `GateResult`; `bench/d12-verdict.json` (decision `rejected`, pinned 1.0) | closed |
| T-19-23 | Elevation of Privilege | title-weight configuration surface | medium | mitigate | `SearchOptions.title_weight` internal only (`models.py:373-377`); `_TITLE_WEIGHT` module constant (`bm25.py:24-25`); zero CLI/config/docs surface; pinned-value test | closed |
| T-19-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package install in this phase; `pyproject.toml`/`uv.lock` unchanged across the phase commit range | closed |
| T-19-24 | Tampering | `_ChunkAddress`, `_chunk_cell`, `_chunk_column`, `_unique_paths` and the three formatters in `src/sif/cli/commands/search.py` | high | mitigate | The table cell yields a plain `Text`, so no Rich markup in a path is parsed (`search.py:249-250`); CSV keeps `csv.writer` `QUOTE_ALL` (`:516`); XML `path` and `sequence` elements pass through `_xml_sanitize` and `xml_escape` (`:586,589`); a markup-bearing path renders literally | closed |
| T-19-25 | Tampering | spreadsheet consumers of `--csv` | low | accept | A cell that begins with `=`, `+`, `-` or `@` is read as a formula by a spreadsheet, and quoting does not prevent it; the exposure is the pre-existing free-text `title` column (`search.py:521`). The per-chunk `path` value is a stored path followed by `#` and an integer (`chunk_address`, `search.py:202-204`), and stored paths are absolute (`src/sif/indexing/parser.py:84,120,187` resolve) (AR-19-04) | closed |
| T-19-26 | Denial of Service | per-chunk table layout on narrow terminals | medium | mitigate | Column declared through `_chunk_column` with `min_width` the smaller of 8 and the widest address and no `no_wrap` or cap (`search.py:263-273`), used by both per-chunk tables (`:1031`, `:1401`); the cell fits itself to the width Rich allots (`_fit_head` `:207-229`, `__rich_console__` `:249-250`); four 80-column render tests pin the fit and the suffix (`test_search.py:4441-4498`) | closed |
| T-19-27 | Repudiation | identity correctness of the rendered address | medium | mitigate | Each rendered cell is paired with its own row under `zip(..., strict=True)` and asserted to end with that row's `#sequence`; the document-level row is asserted to carry no `#` (`test_search.py:4450-4469,4481-4498`); the CSV test asserts the exact `path` and `sequence` of each of five rows (`:4573-4592`) | closed |
| T-19-28 | Repudiation | integrity of the before-evidence in `bench/g19-2-min-score.json` | high | mitigate | `probe.before.head` equals the recorded plan base `4ac6262`, the parent of the first `(19-11)` commit; the before half was committed at `043db46` on a tree whose `bm25.py` equals the planning commit `6e28002`; the validator of plan 19-11 pins every recorded value; `b0.json`, `b1.json` and `d12-verdict.json` are byte-identical since that base | closed |
| T-19-29 | Tampering | decision integrity: the `checkpoint:decision` in Task 2 of plan 19-11 | high | mitigate | `<task type="checkpoint:decision" gate="blocking-human">` at `19-11-PLAN.md:147` declares no `auto_select`; the three options carry their ids; `19-11-SUMMARY.md:269` holds the exact line `Decision: monotone-map`, equal to the artifact's `decision` field | closed |
| T-19-30 | Denial of Service | the user's default database and caches during the evidence captures | medium | mitigate | Procedural, in the plan text: every capture command exports `SIF_DB_PATH` and `SIF_CACHE_DIR` into a `mktemp -d` directory and aborts when it is missing (`19-11-PLAN.md:104`, `19-12-PLAN.md:246`); the SUMMARIES record identical snapshots before and after; today the default database `sif.db` was last modified 2026-11-20 and no capture scratch directory remains | closed |
| T-19-31 | Tampering | SQL construction in `BM25Searcher.search` | high | mitigate | Threshold computed by `bm25_rank_threshold` (`src/sif/search/bm25.py:60-77`) and bound as a parameter (`:131-134`), never interpolated; the only f-string placeholders in the SQL are the constant fragments; `params[3]` and the predicate's place before `LIMIT ? OFFSET ?` are pinned by tests (`tests/unit/search/test_bm25.py:120-124`, `test_filters_sql.py:844-861`); `m.score >= ?` count 0 and `1.0 / (1.0 + abs(` count 0 | closed |
| T-19-32 | Tampering | `--min-score` input validation | medium | mitigate | Every class of value has a defined, tested outcome: 0, a negative value and NaN omit the predicate (`bm25.py:73-74`), 1 and above binds negative infinity (`:75-76`), a value in `(0, 1)` binds `-M/(1-M)` (`:77`); `test_rank_threshold_table` (7 cases), `test_negative_min_score_omits_the_filter`, `test_min_score_of_one_returns_no_results` through the real CLI; `search.py` help text `higher is a stronger match` 1, `Minimum score threshold` 2 | closed |
| T-19-33 | Repudiation | agreement of plan, truth, golden and evidence with the code | high | mitigate | Fourth 19-05 truth amended in place with a dated note naming plan 19-12 (`19-05-PLAN.md:37`); `git diff --numstat 0744e83 HEAD -- 19-05-PLAN.md` is `1 1`; the old bound is gone; the 19-12 Task 2 validator prints `after-evidence OK` on the committed artifact; the SC1 regeneration command reproduces the two golden values from code; `TestHybridMinScoreLeg` 2 tests and the leg's rows in the artifact pin the hybrid BM25 leg | closed |
| T-19-34 | Information disclosure | consumers of the published BM25 score | medium | accept | The contract change itself: both score conversions run through `bm25_display_score` (`bm25.py:209`, `:269`); `sif query --min-score` and MCP `query` reach the same predicate through `hybrid.py:82`; the authorising decision is on record in both places (T-19-29); the remedy, subtract an old threshold from 1, is in `docs/changelog.md` (AR-19-05) | closed |
| T-19-35 | Tampering | the user's real model cache during the live-render evidence step of Task 2 of plan 19-10 | medium | mitigate | Procedural: status gate `cache.state: valid`, read with `SIF_CACHE_DIR` unset, before any link (`19-10-PLAN.md:204-210`, prohibition `:69`); premise holds in code: `inspect_cache` reports `valid` exactly when `verify_manifest` holds (`src/sif/models/download.py:409-414`) and `ModelDownloader.download` returns the cached directory without writing only in that case (`:462-464`), otherwise it migrates or downloads and installs (`:465-497`); `19-10-SUMMARY.md` (Live Render at 80 Columns, Model Cache) records `cache.state: valid` before the link and an identical cache snapshot after | closed |
| T-19-36 | Tampering | the user's real model cache during the full-suite gate | low | accept | 13 of the 15 `CrossEncoderReranker(...)` constructions in `tests/unit/search/test_rerank.py` and `tests/unit/inference/test_reranker.py` pass no `cache_dir`, which resolves to the real model cache (`src/sif/search/rerank.py:205,213,232`; `src/sif/models/download.py:78-84`); ModelScope's lock file under `models/.lock/` is rewritten and a temporary sibling directory is created and removed under `models/cross-encoder/`; nothing persists and no model is installed (AR-19-06) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-19-01 | T-19-05 | One-pass forced migration on a large collection: per-file short transactions, resumable marker discipline, notice names the scanned count. | Plan-time risk register (19-02-PLAN.md) | 2026-11-18 |
| AR-19-02 | T-19-15 | Per-chunk fields (`chunk_id`, `sequence`, `chunk_matches`) appear in CLI/MCP output: index-local identity/count metadata, no content or new path disclosure. | Plan-time risk register (19-06-PLAN.md) | 2026-11-18 |
| AR-19-03 | T-19-20 | One-time `create_all` rebuild on a populated database, gated by a `sqlite_master` read; bounded by index size and made atomic by the savepoint. | Plan-time risk register (19-08-PLAN.md) | 2026-11-18 |
| AR-19-04 | T-19-25 | CSV cells that begin with `=`, `+`, `-` or `@` can be read as formulas by spreadsheet software, and quoting does not prevent it. The cause is accepted because it is pre-existing: the exposure is the free-text `title` column (`src/sif/cli/commands/search.py:521`), and the per-chunk `path` value is a stored absolute path followed by `#` and a number (`chunk_address`, `:202-204`), which adds no formula-leading cell. Remedies if it materialises: open the file with formulas disabled or import it as text. Accepted by the plan-time risk register of plan 19-10. | Plan-time risk register (19-10-PLAN.md) | 2026-11-26 |
| AR-19-05 | T-19-34 | The published BM25 score changed value and direction, and `sif search query --min-score` and the `min_score` of MCP `query` now keep the stronger matches in their BM25 leg, deliberately. A person or script that read scores under the old map sees different numbers (an old value `v` reads `1 - v`), and a script that selected strong matches with a low-score comparison now selects weak ones; the remedy is to subtract an old threshold from 1, as the changelog entry records. Accepted because the operator chose it at the blocking 19-11 checkpoint with that scope and the evidence in front of them, and because the old map made `--min-score` remove the best matches first. | Plan-time risk register (19-12-PLAN.md) | 2026-11-26 |
| AR-19-06 | T-19-36 | The project's reranker tests construct `CrossEncoderReranker()` without a cache directory, so their loader calls `ModelDownloader.download` on the real model cache: ModelScope's lock file under `models/.lock/` is rewritten and a temporary sibling directory is created and removed under `models/cross-encoder/`. Nothing persists and no model is installed. Existing behaviour of the test suite, which this phase does not change; isolating it belongs to a test-isolation change outside this phase. | Plan-time risk register (19-10-PLAN.md) | 2026-11-26 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-18 | 24 | 24 | 0 | /gsd-secure-phase 19 (gsd-security-auditor, ASVS L1) |
| 2026-11-25 | 24 | 24 | 0 | ZCode (gsd-secure-phase 19, ASVS L1, block_on high; short-circuit, auditor not spawned — all 24 rows re-verified at HEAD `2808c67`; line references refreshed in T-19-09, T-19-17, T-19-22; no status change) |
| 2026-11-26 | 37 | 37 | 0 | ZCode (gsd-secure-phase 19, ASVS L1, block_on high; short-circuit, auditor not spawned — 13 new threats from plans 19-10, 19-11 and 19-12 confirmed by command and added as rows T-19-24 to T-19-36, with 3 accepted risks; all 24 earlier rows re-verified at HEAD `4cf172c`, which `8a79d0f` matches outside `.planning/`; no status change) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-18 — 24/24 threats closed at L1; 0 open at or above `high`.

**Re-verification:** verified 2026-11-25 — 24/24 threats closed at L1; 0 open at or above `high` (delta re-audit at HEAD `2808c67`; no status change; line references refreshed in T-19-09, T-19-17, T-19-22).

**Re-verification:** verified 2026-11-26 — 37/37 threats closed at L1; 0 open at or above `high` (gap-closure audit with HEAD `4cf172c` at the checks and `8a79d0f` at the end of the run, identical outside `.planning/`: plans 19-10, 19-11 and 19-12 add T-19-24 to T-19-36 and accepted risks AR-19-04 to AR-19-06; no earlier row changed status, ID or text; the stale line references of T-19-08, T-19-10, T-19-12 and T-19-19 are refreshed in the dated section below, the rows themselves are left as written).

## Security Audit 2026-11-25

| Metric | Count |
|---|---|
| Threats found | 24 |
| Closed | 24 |
| Open | 0 |

### Re-audit notes (2026-11-25, HEAD `2808c67`)

- **Scope.** State A re-audit of the existing register against the tree after `b817ebb`, the
  last commit that touched this file. Depth L1, `block_on: high`, ASVS level 1. The register is
  authored at plan time (all nine PLANs carry STRIDE `<threat_model>` blocks) and `threats_open`
  was 0, so the workflow short-circuit applied: Steps 4 and 5 were skipped and
  `gsd-security-auditor` was not spawned. This runtime has no Agent tool either. The orchestrator
  classified every row, and all 24 were read at HEAD rather than only the delta rows. No SUMMARY
  file carries a `## Threat Flags` heading or any threat text, so there are no unregistered flags.
- **Delta outside `.planning/`, `b817ebb..HEAD`: 59 files.** Of the 19 files a mitigation cell
  cites, 17 are byte-identical to `b817ebb`: all 16 under `src/`, and `bench/d12-verdict.json`.
  The two that changed are both cited by `T-19-SC`:
  - `pyproject.toml`: only the two torch extras floors, `"torch"` to `"torch>=2.11"` (`embed`,
    `all`). Two commits produced this: `a13b134c` raised the floor to `>=2.14`, then `848e6b6a`
    lowered it to `>=2.11`.
  - `uv.lock`: 23 lines removed, 23 added. Four are torch `requires-dist` entries gaining
    `specifier = ">=2.11"`; the other 19 are `resolution-markers` strings reordered inside
    package blocks, the same strings on both sides. No line touching a package name, version,
    sdist, wheel, URL, hash or index changed, and the name@version multiset is the same on both
    sides. No commit tagged for this phase touched either file, from the first task commit
    `5b964e18` through `e137ca04`, the four `fix(19)` review fixes included.
  - **`T-19-SC` holds.** A floor on an already-locked optional dependency adds no package,
    version, source or index.
- **Cited tests.** No mitigation cell names a test file by path. Where a cell names tests by
  description, the deciding tests were located. Those in files changed by `c95d2cee` (Windows
  portability):
  - `tests/unit/cli/test_search.py` (+6/-2): `TestSingleEnrichmentOwner` (T-19-08) is untouched.
    The commit relaxes two title-cell literals in `TestSearchOutputBranches`, Phase 10 tests that
    no row cites.
  - `tests/unit/mcp/test_backend.py` (+3/-3): `TestSingleEnrichmentOwner`, the exact-set re-map
    assertions (T-19-16, `:884`, `:905`), the input-model tests (`:923-933`) and
    `TestSchemaInitializationAtStartup` (T-19-21) are untouched; `symlink_or_skip` replaces
    `os.symlink` in two document-get alias tests (`test_get_document_alias_path_normalized`,
    `test_get_documents_by_pattern_alias_prefix`). Net line shift 0.
  - `tests/unit/search/test_context_attach.py` (+7/-1): the `alias_pair` fixture goes through
    `symlink_or_skip`; a `win32` skipif on the un-expandable-tilde test.
  - `tests/unit/database/test_repositories.py` (+3/-1): the `alias_pair` fixture goes through
    `symlink_or_skip`; a `tzset` skipif on an LLM-cache expiry test.
    `TestDocumentMetadataCanonicalStorage` (T-19-01) takes only `db` and is untouched.
  - `symlink_or_skip` still calls `symlink_to` and skips only on `NotImplementedError` or
    `OSError`, so on a host that can create a symlink every one of these tests runs as before.
    On a host that cannot (Windows without Developer Mode or elevation) they now skip instead of
    failing. That covers ten tests in `test_context_attach.py`, seven of them in
    `TestAttachPathContextsRealSQL` behind T-19-07. T-19-07's mitigation is product code
    (`context_attach.py:51-53`, `:110`, `:311`) and is unchanged. CI runs only `ubuntu-latest`
    and `macos-latest` (`.github/workflows/test-matrix.yml:23`), so no CI cell exercises that
    skip path.
  - `tests/unit/search/test_rerank.py` (+76, `f8ff9bea`): `TestRebuildChunkIdentity`, three
    tests pinning that `_sort_and_build_results` (`src/sif/search/rerank.py:24`) keeps
    `chunk_id`, `sequence` and `chunk_matches` through the sort (CORR-02). Additive: the 15
    earlier tests are unchanged. `src/sif/search/rerank.py` differs from `b817ebb` by one hunk
    in `create_reranker` (`:436-438`, the cache path gains `models`; `5f9c0869`) and is
    byte-identical to `fee02316`. No mitigation cell cites that file.
- **Line references.** Every cited range was read at HEAD. Seventeen of the 20 mitigate rows
  that carry one resolve exactly as written. Three did not, all in
  `src/sif/search/personal_bench.py`, and all for one reason outside `b817ebb..HEAD`:
  `618997c1` (2026-11-18 18:33) inserted 17 lines at line 599 after these references were taken
  and before this file was committed at `b817ebb` (20:02). The file is byte-identical to
  `b817ebb`. Each mitigation was re-read at its new range and holds; only the numbers changed.
  - `T-19-09`: `:1580` to `:1597`, `:1676` to `:1693`, `:1697-1790` to `:1714-1805`,
    `:1209-1217` to `:1226-1235`.
  - `T-19-17`: `:2160-2183` to `:2184-2201` (`require_matching_corpus`), `:2253-2277` to
    `:2270-2294`.
  - `T-19-22`: `:1998-2031` to `:2015-2048` (`leg_noise_gates`).
- **Result.** 24/24 closed, 0 open, 0 open below the `high` threshold. **The delta invalidates
  nothing.** No row changed status or ID and no row was added. No accepted risk was added.
- **Evidence.** `pytest` from PATH (9.1.1), 0 failed. The 20 test files the validation map
  cites: 1000 passed in 21.72 s. Per-threat classes: `TestDocumentMetadataCanonicalStorage` 2,
  `TestAttachPathContextsRealSQL` 10, `TestSingleEnrichmentOwner` 3 (CLI), `test_staleness.py`
  20, `TestRebuildChunkIdentity` 3, `TestSchemaInitializationAtStartup` 5, the three
  dimension-injection tests in `test_schema.py` 3, `TestPerLegNoiseGates` 4,
  `TestSavedRunContract` 7, `TestCorpusFingerprint` 2, `TestCompareSavedRun` 13,
  `TestSavedRunsCli` 6, title-weight pins 3. Artifact shape: `bench/d12-verdict.json` is
  `decision: rejected` at `pinned_title_weight: 1.0` with candidates 2.0/3.0/4.0, and
  `bench/b0.json` holds 100 query records under fingerprint `8c006123784348d1` with no `content`
  or `snippet` key. GitHub Actions Test Matrix run `45522236981` on `a25eb07` is green on 8/8
  cells plus lint; `a25eb07..HEAD` differs only under `.planning/` and in
  `tests/unit/search/test_rerank.py`. Its `Type check` step is not counted as evidence. Full
  suite at HEAD, run without coverage: 3263 passed, 1 skipped in 121.47 s.
- **Recorded, not re-triaged.**
  - The header names `763753d` as the verified HEAD. The references in this register were not
    read from that tree: at `763753d` several cited ranges are past end of file, and
    `src/sif/mcp/tools.py` (cited by `T-19-16`) does not exist. They match `618997c1^` exactly.
    The header is left as written.
  - The closing phrase of `T-19-16`'s cell, "wire goldens", names no file, and no test was tied
    to it with confidence. It is left as written; the exact-set re-map assertions in the same
    cell were verified.
  - Threat Ref reconciliation against the 2026-11-25 validation map. `19-VALIDATION.md` was not
    edited by this audit; this is a report for the validate-phase owner, and none of it changes
    a row here.
    - `T-19-21` (MCP-only schema startup): the move off the mtime-index row is correct. It is now
      cited by "19-09 T1 (MCP startup)", whose command runs
      `tests/unit/mcp/test_backend.py::TestSchemaInitializationAtStartup` (5 tests), which
      decides the `backend.py:274-295` half. The stated ground is incomplete, though: the
      `database.py:37-60` half (a supplied dimension never consults `get_settings()`) is decided
      by `TestDatabaseInitSchemaDimension` (`tests/unit/database/test_schema.py:1372`, `:1389`),
      and those two tests run under the mtime-index row's command and under no row that cites
      `T-19-21`. Optional tightening: add `tests/unit/database/test_schema.py` to the MCP-startup
      row's command.
    - `T-19-22` (D-12 verdict): correct. Decided by `TestPerLegNoiseGates` (4 tests) and
      `tests/unit/cli/test_eval.py`, plus the recorded `bench/d12-verdict.json`; nothing in
      `test_schema.py` touches it. Now cited by "19-09 T2", whose command runs both files.
    - `T-19-09` (B0 saved-run integrity): the removal is right, the result is not. The old CORR-05
      row never decided it (`test_staleness.py` and `test_context_attach.py` hold no saved-run
      test; the ID rode on a plan-level `19-04` tag). But no row now cites a `mitigate` threat,
      and the recorded ground "no map command targets it" is inaccurate: the "19-09 T2" command
      already runs `TestSavedRunContract`, `TestCorpusFingerprint`, `TestCompareSavedRun` and
      `TestSavedRunsCli`, 28 green tests. Suggested repair: add a row "19-04 T1 (B0 saved run)"
      (plan 19-04, wave 4, CORR-05, T-19-09) citing that command. Not a security gap: the
      mitigation is present and tested.
    - `T-19-23` (title-weight surface; not part of the change): cited by no row before or after.
      Its three pins sit in `tests/unit/search/test_bm25.py` and run under "19-05 T1" and
      "19-08 T2"; the latter's stated behavior includes the constant pin. Adding `T-19-23` to
      that row's Threat Ref would close it.

## Security Audit 2026-11-26

| Metric | Count |
|---|---|
| Threats found | 37 |
| Closed | 37 |
| Open | 0 |

### Register verification notes (2026-11-26, HEAD `4cf172c`)

- **Scope.** State A update for the three gap-closure plans that ran since the 2026-11-25 audit:
  19-10 (UAT gap G-19-1, CORR-02), 19-11 and 19-12 (UAT gap G-19-2, CORR-03). Each carries a
  `<threat_model>` block; together they add T-19-24 to T-19-36, thirteen rows: ten `mitigate` and
  three `accept` (T-19-25, T-19-34, T-19-36). Depth L1. `workflow.security_block_on` was read with
  `gsd-tools.cjs query config-get` and is `high`; the key is present, so no fallback was needed, and
  only an open threat of severity high or critical would count in `threats_open`. ASVS level is 1.
- **Gate.** `threats_open: 0`, the register is authored at plan time and ASVS is L1, so the workflow's
  short-circuit applied: the auditor was not spawned and its job was done inline. Every `mitigate`
  row below was confirmed by command at HEAD, never on the register's word; every `accept` row's
  accepted cause was confirmed. Severity by disposition: mitigate T-19-24, 26, 27, 28, 29, 30, 31,
  32, 33, 35 and T-19-SC (6 high, 5 medium); accept T-19-25, 34, 36 (1 medium, 2 low).
- **Tree audited.** Code audited at `4cf172c`. Two commits landed after dispatch (`e822b28`,
  `4cf172c`); they touch only `19-12-SUMMARY.md` and `.planning/WINDOWS.md`, so the code audited is
  byte-identical to the dispatched `d5382ae`. Three more landed while this report was written
  (`0d696e8`, `b86da79`, `8a79d0f`, the HEAD at the end of the run); they change only
  `19-VALIDATION.md`, `19-REVIEW.md` and `19-UI-REVIEW.md`, so nothing outside `.planning/` differs
  from `d5382ae`. Delta outside `.planning/` since `2808c67`: ten files, under `src/`
  only `src/sif/cli/commands/search.py` and `src/sif/search/bm25.py`. Every other source file a
  mitigation cell cites is byte-identical to `2808c67`. Scope gates: plan 19-10 changed exactly its
  three declared files outside `.planning/`, plan 19-11 nothing, plan 19-12 exactly its nine
  (`git diff --name-only 0744e83 HEAD -- . ':(exclude).planning'`).
- **Threat flags.** No SUMMARY carries a `## Threat Flags` heading; the three new ones each state
  that no file adds an endpoint, auth path, file-access pattern or schema change beyond what its
  threat model records. No unregistered flag.
- **Stale text at dispatch, not a gap.** `19-12-SUMMARY.md` still called its Task 3 human check
  pending when this audit began. `e822b28` records the check as performed and approved by the
  orchestrator on the operator's behalf, and `.planning/WINDOWS.md` entry 13 is closed.
- **Result.** 37/37 closed: 24 earlier rows and 13 new. 0 open, and 0 open below the `high`
  threshold. By severity the register now holds 0 critical, 15 high, 15 medium and 7 low; before
  this audit it held 0 critical, 10 high, 9 medium and 5 low. No earlier row changed status, ID or
  text. Rows T-19-24 to T-19-36 and accepted risks AR-19-04, AR-19-05 and AR-19-06 were added.

### New registers: one row per threat (2026-11-26)

| Threat ID | Plan | Category | Severity | Disposition | Verdict | Evidence at HEAD |
|-----------|------|----------|----------|-------------|---------|------------------|
| T-19-24 | 19-10 | Tampering | high | mitigate | CLOSED | `src/sif/cli/commands/search.py:249-250` yields a plain `Text`, so no Rich markup in a path is parsed; `csv.writer` with `QUOTE_ALL` at `:516`; XML `path` at `:586` and `sequence` at `:588` pass through `_xml_sanitize` and `xml_escape`; both XML tests parse with `ElementTree` (`tests/unit/cli/test_search.py:4619,4640`); two markup-bearing paths rendered literally through `_chunk_cell` |
| T-19-25 | 19-10 | Tampering | low | accept | CLOSED, AR-19-04 | Cause confirmed: `title` is written as-is by the CSV writer (`search.py:521`); the new per-chunk `path` value is a stored path, `#` and an integer (`chunk_address`, `:202-204`), and stored paths are resolved to absolute form (`src/sif/indexing/parser.py:84,120,187`), so the value cannot begin with a formula character |
| T-19-26 | 19-10 | Denial of Service | medium | mitigate | CLOSED | `_chunk_column` returns `min_width` `min(_CHUNK_MIN_WIDTH, widest)` with 8 as the constant and no `no_wrap` or cap (`search.py:64,263-273`); both per-chunk tables declare their column through it (`:1031`, `:1401`), the only `no_wrap` in the module is on the cell's `Text` (`:250`); four 80-column render tests pass at HEAD and all four fail by name when the column is given `no_wrap` |
| T-19-27 | 19-10 | Repudiation | medium | mitigate | CLOSED | Render tests pair each cell with its own row under `zip(..., strict=True)` and assert `cell.endswith` its sequence; the document-level row is asserted to carry no `#` (`test_search.py:4450-4468,4481-4497`); the CSV test asserts the exact `path` and `sequence` of five rows (`:4589-4592`); all four render tests fail when a cell is given the next row's sequence |
| T-19-28 | 19-11 | Repudiation | high | mitigate | CLOSED | `probe.before.head` is `4ac6262d506f…`, the recorded plan base (`.git/gsd-plan-19-11-base`) and the parent of the first `(19-11)` commit `043db46`; every pin of the 19-11 Task 1 validator holds on the committed artifact; no path outside `.planning/` differs in `4ac6262..dbb82b5` or `4ac6262..0744e83`; `src/sif/search/bm25.py` is byte-identical at `6e28002`, `4ac6262` and `0744e83`; `bench/b0.json`, `b1.json` and `d12-verdict.json` are byte-identical since `4ac6262` |
| T-19-29 | 19-11 | Tampering | high | mitigate | CLOSED | `<task type="checkpoint:decision" gate="blocking-human">` at `19-11-PLAN.md:147` carries no `auto_select` attribute; the three options are `monotone-map`, `describe-current`, `deprecate-flag` (`:162,167,172`); between `043db46` and `dbb82b5` only the `decision` field of the artifact changed, from the pending marker to `monotone-map`; `19-11-SUMMARY.md:269` is exactly `Decision: monotone-map`; the artifact field and the 19-12 Task 1 gate agree |
| T-19-30 | 19-11 | Denial of Service | medium | mitigate | CLOSED | The capture prefix is in the plan text (`19-11-PLAN.md:104`, `19-12-PLAN.md:246`): it reloads a `mktemp -d` directory, aborts when it is missing, and exports `SIF_DB_PATH` and `SIF_CACHE_DIR` inside it; both scratch records are absent from `.git` and no `bench.db`, `probe.json` or `leg.json` remains under the OS temp directory; the default database was not written on 2026-11-26 (`~/Library/Application Support/sif/sif.db` modified 2026-11-20 09:35, `sif.db-shm` 2026-11-25 22:14, both before the captures); both SUMMARIES record identical cache snapshots before and after |
| T-19-31 | 19-12 | Tampering | high | mitigate | CLOSED | `bm25_rank_threshold` at `src/sif/search/bm25.py:60-77`; `params.append(threshold)` at `:133`; the constant fragment `AND m.score <= ?` at `:134`, interpolated into the outer WHERE of both branches (`:175`, `:197`) ahead of `LIMIT ? OFFSET ?` (`:177`, `:199`); `m.score >= ?` count 0 and `1.0 / (1.0 + abs(` count 0; `params[3]` and the predicate's place pinned (`tests/unit/search/test_bm25.py:120-124`), parameter order pinned (`tests/unit/search/test_filters_sql.py:844-861`); the five diff hunks touch neither `_sanitize_term` nor `term_match.py` |
| T-19-32 | 19-12 | Tampering | medium | mitigate | CLOSED | `bm25.py:73-74` returns `None` for anything not above 0, NaN included; `:75-76` returns negative infinity from 1; `:77` returns `-M/(1-M)`; `test_rank_threshold_table` (7 cases), `test_min_score_at_or_above_one_keeps_nothing` (2), `test_negative_min_score_omits_the_filter` and the zero-threshold test pass in `tests/unit/search/test_bm25.py`, and `test_min_score_of_one_returns_no_results` passes through the real CLI; help-text counts in `search.py`: `higher is a stronger match` 1, `Minimum score threshold` 2 |
| T-19-33 | 19-12 | Repudiation | high | mitigate | CLOSED | `19-05-PLAN.md:37` carries `Amended 2026-11-26 by plan 19-12`, `m.score <= ?` and `-min_score/(1 - min_score)`; `git diff --numstat 0744e83 HEAD` on that file is `1 1`; the 19-12 Task 2 validator prints `after-evidence OK` on the committed artifact (identical titles and ranks, identical B0 and B1 deltas); the regeneration command prints `d3 1.3749981093775994e-06` and `d1 1.313431110717347e-06`, equal to `TestHybridSC1PipelineGolden.SNAPSHOT`; the dated rationale is in the class docstring (`tests/unit/search/test_hybrid.py:797-808`); `TestHybridMinScoreLeg` 2 tests and the artifact's `hybrid_bm25_leg` rows agree: no row before at 0.3 or 0.5, both matches after |
| T-19-34 | 19-12 | Information disclosure | medium | accept | CLOSED, AR-19-05 | Cause confirmed: both score conversions run through `bm25_display_score` (`bm25.py:209`, `:269`); `sif query --min-score` and MCP `query` reach the same predicate through `hybrid.py:82`; `hybrid.py`, `rrf.py`, `vector.py` and `src/sif/mcp` are byte-identical to `0744e83`, so the scope is the searcher alone; the authorising decision is on record in both places (T-19-29); the remedy is in `docs/changelog.md` ("subtract it from 1"); the orchestrator's approved human check (`e822b28`) observed the changed values on an isolated index |
| T-19-35 | 19-10 | Tampering | medium | mitigate | CLOSED | Gate before link, in the plan text (`19-10-PLAN.md:204-210`, prohibition `:69`); the premise holds in code: `inspect_cache` reports `valid` exactly when the manifest verifies (`src/sif/models/download.py:409-414`), and `ModelDownloader.download` returns the cached directory without writing only in that case (`:462-464`), otherwise it migrates a legacy directory or downloads and installs (`:465-497`); `19-10-SUMMARY.md` records `cache.state: valid` before the link and an identical cache snapshot after the step; today `models/Qwen/Qwen3-Embedding-0.6B` still carries its 2026-11-19 modification time, so no model directory of the real cache was replaced |
| T-19-36 | 19-10 | Tampering | low | accept | CLOSED, AR-19-06 | Cause confirmed: 13 of the 15 `CrossEncoderReranker(...)` constructions in `tests/unit/search/test_rerank.py` and `tests/unit/inference/test_reranker.py` pass no `cache_dir` (`src/sif/search/rerank.py:205,213,232`), which resolves to the real cache (`src/sif/models/download.py:78-84`), and no autouse fixture of `tests/conftest.py` redirects either path; the two entries the register names exist: the lock file is 0 bytes and `models/cross-encoder` is empty; the cache holds 129 entries including its root, the count `19-10-SUMMARY.md` gives, 128 below it, the count `19-12-SUMMARY.md` gives |
| T-19-SC | 19-10, 19-11, 19-12 | Tampering | high | mitigate | CLOSED, existing row | `git diff --quiet` on `pyproject.toml` and `uv.lock` exits 0 for `147661b..4ac6262`, `4ac6262..0744e83`, `0744e83..d5382ae` and `2808c67..HEAD`, and against the working tree; no commit since `2808c67` touches a manifest, lock file, requirements file or workflow file |

### Re-audit notes (2026-11-26)

- **Earlier rows in the two changed modules.** Each mitigation was re-read at HEAD and holds; only
  the line numbers moved. The rows are left as written, so these refreshed references apply:
  - `T-19-08`: `search.py:613,871-874` is now `search.py:730,988-991`. Exactly one enrichment on the
    direct BM25 exit (`:730`) and on the vector exit (`:989`, `:991`, the two branches of one call);
    `query_cmd` has none; `src/sif/mcp/backend.py` is unchanged.
  - `T-19-10`: `bm25.py:87,96-97,164` is now `bm25.py:123,132-133,201`. `IntRange(min=0)` stands at
    `search.py:627,835,1071` and `Field(ge=0)` at `src/sif/mcp/protocol.py:98,131,159`.
  - `T-19-12`: `bm25.py:181` is now `bm25.py:219`; `vector.py:251` and `hybrid.py:55-67,484` are
    unchanged.
  - `T-19-19`: `bm25.py:84-97,122-164` is now `bm25.py:120-134,159-203`; both branches still bind
    `bm25(documents_fts, ?, ?)` (`:162`, `:184`) and `test_1_0_1_0_reproduces_rank_exactly_on_real_corpus`
    passes, re-pinned to the new map.
  - `T-19-23`: `bm25.py:24-25` and `models.py:373-377` are unchanged. Of the three docs files that
    changed, no line adds a title-weight setting or flag; `SIF_TITLE_WEIGHT` appears in
    `docs/benchmarking.md:233` only in the sentence that says there is none.
  - `T-19-15` (accepted): the per-chunk `path` of CSV, Markdown and XML now carries the
    `path#sequence` address, the same stored path plus an integer, so "no content or new path" still
    reads true.
- **Tests in the changed files.** The tests the earlier rows name by description still decide them:
  both `TestSingleEnrichmentOwner` classes (3 CLI, 2 MCP, with the exact-set re-map assertions
  T-19-16 cites at `tests/unit/mcp/test_backend.py:884,905`), the global-rank tests, the three
  title-weight pins and `test_1_0_1_0_reproduces_rank_exactly_on_real_corpus` in `test_bm25.py`.
  Plan 19-12 re-pinned the six tests that had pinned the inverted direction.
- **Recorded, not re-triaged.**
  - `T-19-24`'s plan text says Markdown and XML "keep `_xml_sanitize` and `xml_escape`". In the
    code those two functions run in the XML formatter only (`search.py:584-602`); the Markdown
    formatter has never escaped its values (`:532-561`). The row holds as implemented: the only new
    Markdown content is the `Sequence` line, an integer, and the `#sequence` suffix of the Path line.
  - `T-19-35` and `T-19-30` are procedural controls for steps that have already run. They exist as
    plan text and SUMMARY records, not as code, so a later re-run of those steps is protected only by
    the plan text.
  - `search_chunks` (`bm25.py:236-273`) keeps a post-window `min_score` filter, where a NaN drops
    every row. It has no caller in `src/` (`git grep`: its definition and two tests), so no CLI or
    MCP value reaches it; it is outside `T-19-32`'s surface and is already a residual observation in
    `19-12-SUMMARY.md`.
  - Plan 19-12 says five tests in `test_hybrid.py` compare against the SC1 snapshot. The class holds
    four tests, two of which compare against `SNAPSHOT` directly (`test_hybrid.py:960,966`). The two
    `bm25_score` values that `T-19-33` depends on are checked; the count is a plan-text inaccuracy.
  - The two entries `T-19-36` names were last modified 2026-11-26 11:30, later than the plan's own
    runs, which matches the timing of the full-suite gate run on `d5382ae` rather than the plan's
    evidence steps. Which process wrote them was not observed.
  - Threat Ref mapping. `19-VALIDATION.md` at `8a79d0f`, the version the validate-phase owner
    committed during this run, cites T-19-24, T-19-26 to T-19-34 and T-19-SC on its gap-closure rows.
    T-19-25, T-19-35 and T-19-36 are not cited: two are accepted risks and the third is a procedural
    control that no test can decide.
  - Test gaps the validate-phase owner recorded at `8a79d0f`, which are missing regression tests
    and not missing mitigations: V19-26-2 for the Chunk-cell half of T-19-24 (no test renders a
    per-chunk table with a path that carries markup), and V19-26-1 for the document-level row of a
    per-chunk page in Markdown and XML (no test covers that row). The code holds in both places
    (`search.py:249-250` and `:548-551`, `:585-589`) and the first was confirmed by command here;
    neither property is pinned by an automated test.
- **Evidence.** `pytest` from PATH (9.1.1) with `-p no:cacheprovider --no-cov`, `SIF_DB_PATH` and
  `SIF_CACHE_DIR` pointing into a `mktemp -d` directory since removed: 97 passed in 1.37 s.
  `TestPerChunkSurfaces` 30, `TestSingleEnrichmentOwner` 3 (CLI) and 2 (MCP),
  `test_search_min_score.py` 2, `tests/unit/search/test_bm25.py` 49, `TestBm25ParamOrder` 1,
  `TestHybridMinScoreLeg` 2, `TestHybridSC1PipelineGolden` 4,
  `TestVectorSearcher::test_search_applies_min_score` 1, `TestRebuildChunkIdentity` 3. The plan
  validators were run verbatim: the 19-11 Task 1 validator now fails only on its after-half
  clause, by design, because plan 19-12 added the after half; its before-half pins pass. The 19-12
  Task 1 gate likewise passes its two decision clauses and fails its start-of-plan after-half clause
  by design. The 19-12 Task 2 validator prints `after-evidence OK`. No `sif` command was run. Build,
  full suite, lint, type check and docs-sync gates were run by the orchestrator on `d5382ae`, whose
  tree outside `.planning/` is byte-identical to `4cf172c`; they were not repeated.
- **Could not check.**
  - The process-time controls (`T-19-30`, `T-19-35`) were not re-run: one loads an embedding model,
    and both must stay off the default database and cache. They rest on the plan text, the code
    premise and the SUMMARY records, with the metadata read today as corroboration.
  - Who answered the 19-11 checkpoint cannot be re-derived from the tree, as the plan itself records.
    What is on record is that the checkpoint declares no `auto_select`, that it stops in every mode,
    and that both records agree on `monotone-map`.
  - `tests/unit/search/test_rerank.py` outside `TestRebuildChunkIdentity` and
    `tests/unit/inference/test_reranker.py` were not run: they construct the reranker against the
    real model cache (`T-19-36`), which this audit may not touch. Both files are unchanged since
    `2808c67`.
- **Recommendations, none applied here.**
  - Refresh the line references in rows `T-19-08`, `T-19-10`, `T-19-12` and `T-19-19` to the ranges
    above. This run left those rows as written.
  - Repair the Markdown half of `T-19-24`'s wording in the plan and in the register row.
  - Isolate the reranker tests from the real model cache (a scratch cache directory set by the test
    fixtures) to retire `T-19-36`. A test-isolation change outside this phase.
  - Add the two regression tests the validation report suggests for V19-26-2 and V19-26-1, so the
    Chunk-cell and document-level-row properties of T-19-24 and T-19-27 are pinned and not only
    spot-checked. A test change outside this audit.
