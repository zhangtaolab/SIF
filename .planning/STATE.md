---
gsd_state_version: "1.0"
milestone: v1.2
milestone_name: Search Precision and Agent Experience
current_phase: 21
current_phase_name: Scale, Maintenance + Embedder Identity
status: executing
stopped_at: Completed 21-04-PLAN.md
last_updated: "2026-11-15T17:18:36.000Z"
last_activity: 2026-11-16
last_activity_desc: Phase 21 execution started
state_head: c9386e78c95babda34edb45b35ffc060432660c7
progress:
  total_phases: 8
  completed_phases: 4
  total_plans: 35
  completed_plans: 32
---

# DocSift — Project State

## Project Reference

- **Name:** DocSift (package `sif`, PyPI `docsif`)
- **Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。
- **Current Focus:** v1.2 Search Precision and Agent Experience — Phases 17-20 complete; Phase 20 (Metadata Filtering + Discovery) shipped and verified 26/26 must-haves at 2482 tests / 95.35% coverage. Next: plan Phase 21 (Scale, Maintenance + Embedder Identity)
- **Tech Stack:** Python 3.10+, SQLite (FTS5 + sqlite-vec), Click, Pydantic, sentence-transformers 5.4.1 (locked), llama-cpp-python; v1.2 adds ONLY `mcp>=2.3.0,<3` + `rapidfuzz>=3.14.5,<4`
- See: .planning/PROJECT.md (updated 2026-11-13)
- Archives: v1.0/v1.1 phase artifacts, full decision logs, per-plan metrics under .planning/milestones/

## Current Position

Phase: 21 (Scale, Maintenance + Embedder Identity) — EXECUTING
Plan: 6 of 8
Status: Ready to execute
Last activity: 2026-11-16 — Phase 21 execution started

Progress: [█████░░░░░] 50%

**v1.2 phase list:** 17 Engineering Foundation (CI + Hygiene + PyPI) · 18 Quality Instrument (Personal Bench + rapidfuzz DYM) · 19 Search Correctness · 20 Metadata Filtering + Discovery · 21 Scale, Maintenance + Embedder Identity · 22 MCP SDK v2 + Agent Packaging · 23 Harrier Gated Evaluation · 24 Tuning + Models UX + Install Docs

## Performance Metrics

- **Velocity:** v1.0 shipped 68 plans / 11 phases (2026-04-14 → 2026-11-07); v1.1 shipped 27 plans / 7 phases (2026-11-07 → 2026-11-12); recent plans averaged ~13-20 min
- **Suite at v1.1 close:** 1591 passed, 1 skipped @ 95.18% coverage (fail_under=90 active); ruff/format/ty green
- **v1.2:** 0/8 phases, 0 plans — per-plan metrics start at Phase 17

**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 17 P01 | 11min | 3 tasks | 14 files |
| Phase 17 P02 | 6min | 2 tasks | 4 files |
| Phase 17 P03 | 21min | 3 tasks | 4 files |
| Phase 17 P04 | 30min | 3 tasks | 10 files |
| Phase 17 P08 | 9 | 2 tasks | 9 files |
| Phase 17 P05 | 7min | 3 tasks | 8 files |
| Phase 17 P09 | 3min | 2 tasks | 8 files |
| Phase 17 P06 | 3h30m | 3 tasks | 3 files |
| Phase 17 P07 | 3h41m | 2 tasks | 4 files |
| Phase 18 P01 | 8min | 3 tasks | 9 files |
| Phase 18 P02 | 13min | 3 tasks | 6 files |
| Phase 18 P04 | 8min | 3 tasks | 5 files |
| Phase 18 P03 | 12min | 3 tasks | 7 files |
| Phase 19 P01 | 9min | 3 tasks | 9 files |
| Phase 19 P02 | 8min | 3 tasks | 11 files |
| Phase 19 P03 | 6min | 3 tasks | 10 files |
| Phase 19 P04 | 6 min | 2 tasks | 5 files |
| Phase 19 P05 | 9min | 3 tasks | 15 files |
| Phase 19 P06 | 13min | 3 tasks | 13 files |
| Phase 19 P07 | 7min | 3 tasks | 10 files |
| Phase 19 P08 | 7min | 3 tasks | 10 files |
| Phase 19 P09 | 9min | 3 tasks | 16 files |
| Phase 20 P01 | 18min | 3 tasks | 13 files |
| Phase 20 P02 | 9 min | 3 tasks | 6 files |
| Phase 20 P03 | 10min | 3 tasks | 5 files |
| Phase 20 P04 | 12min | 3 tasks | 8 files |
| Phase 20 P05 | 14min | 3 tasks | 13 files |
| Phase 21 P01 | 13min | 3 tasks | 14 files |
| Phase 21 P02 | 18 | 3 tasks | 15 files |
| Phase 21 P03 | 7min | 2 tasks | 4 files |
| Phase 21 P08 | 12min | 2 tasks | 12 files |
| Phase 21 P04 | 14min | 2 tasks | 12 files |

## Accumulated Context

### Decisions

Full log: PROJECT.md Key Decisions. Recent (v1.2 scoping, locked 2026-11-13):

- [v1.2 scope]: PDF/format expansion OUT; MCP official SDK v2 upgrade approved; full Windows deferred to v2 — Phase 17 ships a degradation smoke only via hc remote yoga (Python not preinstalled; `uv python install` first)
- [v1.2 scope]: metadata namespace = `qmd.metadata` compatible (migration parity); model arms MINIMAL (decision "d"): Harrier native vs Qwen3-Embedding-0.6B only; GGUF arm = conditional follow-up MODEL-F1; bge-reranker-v2-m3 OUT
- [v1.2 gate]: Harrier default switch ONLY on an EN+ZH held-out win beyond the 0.01 tie rule; embedder identity marker (not width-only — both models are 1024-dim) is a locked precondition: Phase 21 before Phase 23
- [v1.2 deps]: exactly two new runtime deps — `mcp>=2.3.0,<3` (Phase 22), `rapidfuzz>=3.14.5,<4` (Phase 18); sentence-transformers stays 5.4.1
- [v1.1 carryover]: WAL+flock concurrent DB core; one LiveIndexService watch core hosted three ways; IncrementalIndexer is the single per-file update path; rerank explicit opt-in; bench held-out tie rule round(delta,6) < 0.01
- [Phase 17]: Hygiene deletions land as one atomic plan: modules + exports + fixtures + dependent tests + absence guards, so the suite never stops collecting
- [Phase 17]: uv.lock torch upgraded to the documented 2.14.1/2.15.0 fleets (uv lock --upgrade-package torch) so macOS/Windows PyPI torch matches the Linux CPU fleet instead of lagging at 2.11.0
- [Phase 17]: Lock/packaging guards assert structure (a +cpu torch from the explicit CPU index, no nvidia/triton/black, explicit + Linux-marker index) not exact transitive versions, per D-02
- [Phase 17]: CI matrix follows D-01..D-04 exactly: all 8 cells on every push/PR, dependency-only cache, macos-latest arm64 only, per-ref cancel with fail-fast false
- [Phase 17]: conftest now resets leaked sif logger state before every test — the matrix exposed 13 order-dependent caplog failures under locked pytest 9.0.3 that local pytest 9.1.1 masks
- [Phase 17]: LlamaCppReranker validates the missing model path before importing llama_cpp so clean dev+embed CI environments raise the documented ValueError
- [Phase 17]: Windows degradation guards sit at both detach boundaries (daemon.detach RuntimeError + CLI ClickException) and in _service_manager for win32; the yoga smoke is argv-only, temp-DB, and model-free, with evidence recorded as smoke_head in the SUMMARY
- [Phase 17]: Rich spinners select the ASCII 'line' spinner when the console stream cannot encode braille frames (GBK) — found by the first yoga smoke as a UnicodeEncodeError on the missing-root path
- [Phase 17]: Docs absence guards scan docs/**/*.md (changelog exempt by resolved path) plus DESIGN.md for dotted imports, slash paths, and bare name.py tree entries in one literal list
- [Phase 17]: Removed stale models/search.py tree entries from architecture.md and DESIGN.md alongside the migrations.py/strategy.py rows; bandit VERIFY guard asserts exactly one docs marker remains
- [Phase 17]: Release identity: _version.py stays the only literal and the publish build job requires exact ASCII equality of v+literal to GITHUB_REF_NAME before building
- [Phase 17]: Publish workflow builds once and hands the dist artifact to job-scoped OIDC publish jobs (TestPyPI then PyPI); skip-existing only on TestPyPI; no secrets
- [Phase 17]: 3.13 classifier added only after gh run 43399300651 proved the 8-cell matrix green; README mcp-name marker verified inside the built wheel METADATA
- [Phase 17]: Tracked-junk guard requires a pyproject.toml sentinel in git ls-files so an empty/misrooted listing cannot pass vacuously; git-unavailable skips are explicit, never silent passes
- [Phase 17]: 17-06: maintainer confirmed both browser-only registrations on 2026-11-14 — PyPI trusted publisher for docsif (owner zhangtaolab, repo sif, workflow publish.yml, environment pypi) and TestPyPI pending publisher (project docsif, environment testpypi); end-to-end proof is the 17-07 OIDC publish
- [Phase 17]: 17-06: pre-tag gate bound to release_head c819f67228152f2544e79a864b9a9e12dbc79f69 — Test Matrix run 43561542242 green (8 py cells + lint); only src/sif change since smoke 48759e2c is _version.py (1.1.1 -> 1.1.2)
- [Phase 17]: 17-06: 17-07 must tag exactly the recorded release_head, never the later SUMMARY/STATE/ROADMAP metadata commit, which has no matrix run of its own
- [Phase 17]: 17-07: tagged release_head c819f67228152f2544e79a864b9a9e12dbc79f69 as v1.1.2 and pushed it; Publish run 43562577065 built successfully but TestPyPI token exchange failed invalid-publisher and the PyPI job was skipped — no upload to either index, so version 1.1.2 is not consumed
- [Phase 17]: 17-07 root cause: the OIDC claim repository is zhangtaolab/SIF (canonical uppercase); warehouse matches repository_name exactly and lowercases only environment names; the recorded TestPyPI pending publisher used lowercase sif — both publishers must specify SIF before the re-run
- [Phase 17]: 17-07 retry (attempt 2): after the maintainer confirmed both registrations were corrected to repository SIF, `gh run rerun 43562577065 --failed` still failed at TestPyPI token exchange with invalid-publisher; the claim already carries zhangtaolab/SIF, and Build distributions kept its attempt-1 timestamps (artifact reused, no rebuild)
- [Phase 17]: 17-07 stopped after the single policy-allowed retry — no upload reached either index (TestPyPI 404; PyPI latest 1.0.1, no 1.1.2), so version 1.1.2 is unconsumed and tag v1.1.2 stays on c819f67; the next fix is verifying/deleting-and-recreating the saved TestPyPI pending publisher (project docsif, owner zhangtaolab, repo SIF, workflow publish.yml, environment testpypi)
- [Phase 17]: 17-07 final retry (attempt 3): after the maintainer deleted and re-created the TestPyPI pending publisher with the exact expected fields and re-saved the PyPI trusted publisher, `gh run rerun 43562577065 --failed` failed identically at token exchange (`invalid-publisher`, same claims, Build distributions still reused with attempt-1 timestamps). Re-creating the record rules out form-value drift; the residual cause is a wrong index/account/record or a warehouse-side fault, so the workflow was not rerun again
- [Phase 17]: 17-07 did NOT fall back to an API-token/manual upload — that would deviate from the plan's trusted-publishing prohibition and requires an explicit one-way user decision plus a plan amendment; artifacts must be the same bytes (no rebuild, no version mutation)
- [Phase 17]: 17-07 complete: tag v1.1.2 on release_head c819f67228152f2544e79a864b9a9e12dbc79f69 published docsif 1.1.2 to TestPyPI and PyPI on Publish run 43562577065 attempt 4 — Build distributions, Publish to TestPyPI, and Publish to PyPI all success; the build artifact (id 14100657070, created 05:39:35Z) was reused from attempt 1, so no rebuild and no retag occurred
- [Phase 17]: 17-07: the TestPyPI blocker was the pending publisher; after the maintainer created and verified it (project docsif, publisher GitHub, repository zhangtaolab/SIF, workflow publish.yml, environment testpypi) the very next OIDC attempt minted successfully — the claim set had been correct all along and no further publisher change was needed
- [Phase 17]: 17-07: attestation verification must use the canonical repository case https://github.com/zhangtaolab/SIF — pypi-attestations 0.0.31 compares the signed repository string to the URL path with an exact case-sensitive !=, so the lowercase URL in the PyPI docs example reports a false identity mismatch; the canonical-case run prints OK
- [Phase 17]: 17-07: version 1.1.2 is now legitimately consumed by a complete release (nothing was uploaded on attempts 1-3); no patch bump, no artifact mutation, and no manual upload was needed
- [Phase 18]: 18-01: title leg is exact-term (one title query per sampled doc, no overlap budget) and reuses the legacy binary fixture schema (target=1); the additive SearchEvaluator.evaluate_per_query keeps bench output byte-identical
- [Phase 18]: 18-01: sampling is sha256(path\0checksum) digest then path then id; empty titles and NFC-normalized duplicate titles are counted rejections, never emitted
- [Phase 18]: 18-01: hybrid is the eval default and fails loudly with the docsif[embed] + --bm25-only remedy; --bm25-only never constructs EmbeddingManager; openai/modelscope disclosure goes to stderr
- [Phase 18]: 18-01: docs generator treats a subcommand-less Click group as a leaf, so sif eval has a generator-owned CLI reference section
- [Phase 18]: 18-02: per-leg budget — title exact-term/unbudgeted, body token Jaccard <=0.60, replay not synthesized; empty/overlap/duplicate rejections are counted per leg.
- [Phase 18]: 18-02: split = sha256(normalized query)[0] < 128; ensure_heldout widens the deterministic prefix from 50 docs toward min(corpus, 250) until 50 accepted / 25 held-out, loading bodies only for newly added docs.
- [Phase 18]: 18-02: PersonalReport carries corpus/top_k/model/records with rank-aligned retrieved_doc_ids; groups emit in leg x language x length order and <10 groups are named, never rendered as zero.
- [Phase 18]: 18-02: replay reads query_log only, normalizes/dedupes/sorts/caps at 500, stores rank-ordered paths only, and never enters known-item metrics/splits/groups.
- [Phase 18]: 18-04: did-you-mean scans the full sorted vocabulary with rapidfuzz fuzz.ratio at internal _DYM_CUTOFF=75.0 (limit=None, sort score desc -> term asc -> df desc, slice to n); the first-letter bucket, difflib import, and _ratio helper are deleted.
- [Phase 18]: 18-04: rapidfuzz>=3.14.5,<4 is locked; uv.lock resolves 3.14.5 on py3.10 and 3.14.6 on py3.11+ with an add-only diff (212 insertions, 0 deletions).
- [Phase 18]: 18-04: the 75.0 cutoff is inclusive (>=, no epsilon); resturant -> restaur at exactly 75.0 is test-pinned, while probe/hit, prefix, and history contracts stay byte-identical.
- [Phase 18]: 18-04: measured p50 1.513 ms at 73,040 terms (rapidfuzz 3.14.6); local first-letter recall 0.956 at cutoffs 70/75 vs 0.799 at 80, with 70 adding candidates and no recall.
- [Phase 18]: 18-03: saved runs are version 1 under <cache_dir>/eval with a 5 MB/10k cap, pre-decode size check, full envelope+record validation (bool-as-int, NaN/Infinity, content/snippet rejected), and rank-aligned retrieved_doc_ids as the comparison identity; created_at is stamped in run_to_saved.
- [Phase 18]: 18-03: --compare evaluates exactly the saved query set in saved order at saved.top_k with no synthesis, refuses a corpus-fingerprint mismatch naming both values, resolves targets id-first with a unique-path fallback, and grades both arms through document id (first-occurrence dedupe) so baseline nDCG@10 cannot exceed 1.0.
- [Phase 18]: 18-03: the noise gate is a seeded 10,000-resample percentile bootstrap; a winner needs a CI excluding zero AND round(mean_delta,6) >= 0.01, the report carries N/1/N/helped-hurt-unchanged, groups <10 are suppressed and named, and only the held-out summary gate sets warrants_default_change.
- [Phase 18]: 18-03: replay stability is Jaccard@10 + top-1 against the saved snapshot or available:false with a reason; comparison tables label tuning/per-group rows diagnostic and keep suppressed names and replay-unavailable notices on stderr.
- [Phase 19]: 19-01: D-08 checksum = body bytes + NUL + canonical JSON of ALL frontmatter (sort_keys, default=str, ensure_ascii=False, compact separators); recursive mapping-key coercion makes the serializer total because default=str covers values only
- [Phase 19]: 19-01: one canonical serializer serves both documents.metadata storage and the checksum input, so YAML dates persist as ISO text (latent TypeError fixed) and hashed/stored forms agree across the JSON round trip
- [Phase 19]: 19-01: IncrementalIndexer selects create_parser(file_path) or TextParser() per file and stores parsed.checksum on create; create_parser keeps its None-for-unmapped-suffix contract
- [Phase 19]: 19-02: reindexed_paths/metadata_only are compare=False; metadata-only work counts as updated in both update_collection and update_paths.
- [Phase 19]: 19-02: convention marker is per collection (convention:<id>), written after the loop+sweep in a short transaction only when failed == 0; empty collections are marked silently with no migrate event.
- [Phase 19]: 19-02: --force and migrating stay distinct bypasses of the checksum skip; both take the metadata fast path when the body is unchanged (Pitfall 15).
- [Phase 19]: 19-02: the watch embed leg is fed by result.reindexed_paths in burst and reconcile, and always runs at embed depth so _pending_retry still heals; the checksum-snapshot helpers are removed.
- [Phase 19]: 19-02: the full body-change path now refreshes documents.file_size, matching the metadata fast path (Rule 1 deviation).
- [Phase 19]: 19-03: enrich_results lives in context_attach.py and composes attach_path_contexts then mark_vector_staleness; staleness imports only sif.core.models, so the composition has no import cycle.
- [Phase 19]: 19-03: searchers are pure producers; every SearchPipeline.search exit (BM25/VECTOR/HYDE/hybrid) calls enrich_results exactly once, with the hybrid exit enriching after fusion, rerank, and snippets.
- [Phase 19]: 19-03: direct CLI search/vsearch and the MCP BM25 fallback remain unenriched until 19-04 lands their single enrich_results call (planned sequencing, not a regression).
- [Phase 19]: 19-03: marker parity is pinned on a real-DB hybrid fixture (verbatim context row attaches on read; a purged embedding marks only the BM25-only document).
- [Phase 19]: 19-04: B0 is recorded on a clean scratch index over the committed 150-document fixture corpus (100 queries, top_k 10, fingerprint 8c006123784348d1, mean self-compare delta 0.0); pre-CORR-01 saved runs are refused because corpus_fingerprint hashes stored checksums.
- [Phase 19]: 19-04: direct CLI search/vsearch enrich exactly once right after their searcher returns; the MCP boundary enriches only the BM25 fallback before the re-map (pipeline path untouched), and context_description stays CLI-visible only.
- [Phase 19]: 19-04: CORR-05 is closed at every public entry point; bench/b0.json is the committed pre-ranking-change baseline for CORR-02/03/04 comparisons.
- [Phase 19]: 19-05: BM25 min_score is bound as rank >= 1 - 1/min_score inside the FTS scan (both branches); ranks are offset + position and the 1/(1+|rank|) score formula is unchanged.
- [Phase 19]: 19-05: vector fetch_k = min(max((limit+offset)*4, 50), 2048), one slice, global ranks; a past-cap offset returns an empty page.
- [Phase 19]: 19-05: HybridSearcher is the single slice owner for direct callers (early returns included); the pipeline always calls hybrid at offset=0 and slices once after rerank/snippets.
- [Phase 19]: 19-05: the rerank pre-window is max(candidate_limit, limit+offset) when offset>0 and exactly candidate_limit at offset=0; top_k = limit+offset.
- [Phase 19]: 19-05: MCP offset is validated on QueryInput/LexSearchInput/VecSearchInput and forwarded through SearchBackend; lex/vec registration stays Phase 22.
- [Phase 19]: 19-05: B0 comparison at offset=0/min_score=0 reports n=100, mean delta 0.0, so the default path is drift-free.
- [Phase 19]: 19-06: vector dedup runs after min_score; rows group by document in distance order, the best row wins and carries chunk_id/sequence, chunk_matches counts the group, and per_chunk mode keeps rows ungrouped with chunk_matches 0.
- [Phase 19]: 19-06: fetch_k starts at min(max((limit+offset)*4, 50), 2048) and doubles only while the batch returned exactly k rows and the target is unmet; the cap is independent of offset, so a past-cap page is empty.
- [Phase 19]: 19-06: RRFFusion.fuse gained an optional key callable; chunk_key/fuse_key_for are the shared selectors at both fuse sites, and the merge adopts non-null chunk fields plus max(chunk_matches) without touching scores.
- [Phase 19]: 19-06: the default hybrid path keeps the post-fusion safety-net dedup (now metadata-merging) and per-chunk mode skips it; the rerank rebuild preserves chunk identity (Rule 2).
- [Phase 19]: 19-06: the SC1 hybrid golden was regenerated as the post-dedup baseline (scores unchanged on the one-chunk fixture); the held-out snapshot records identical pre/post numbers because the corpus has one chunk per document, with the rationale and the chunky-document regression carrying the contract evidence.
- [Phase 19]: The chunk_matches annotation lives in the shared _title_cell, gated on chunk_matches > 1; BM25 rows cannot trigger it, so sif search needs no option and no new column.
- [Phase 19]: Per-chunk table identity is a dedicated Chunk column (only in per-chunk mode) showing path#sequence, because no existing search table has a path column; document-level hybrid rows fall back to the bare path.
- [Phase 19]: MCP chunk identity rides the existing metadata dict (vectors_stale precedent): the explicit boundary re-map copies chunk_id/sequence/chunk_matches and the exact-metadata-set tests were updated.
- [Phase 19]: B1 is an identical-data baseline (same query set and retrieved ids as B0); the B0->B1 comparison is labeled the BM25 no-drift check because both arms are --bm25-only and never exercise the vector dedup path.
- [Phase 19]: The dedup evidence is cited from the regenerated held-out snapshot (identical pre/post totals and per_category on the one-chunk-per-document fixture) and the SC1 golden byte-identical scores, never from the BM25 deltas; no defaults claim is made.
- [Phase 19]: 19-08: FTS5 'rebuild' is the only documents-side population; the same-gated INSERT ... SELECT seed was removed because it indexes every document twice while PRAGMA integrity_check and the FTS integrity-check both still report OK, so the contract is asserted structurally.
- [Phase 19]: 19-08: documents_fts_v is dropped before documents_fts and recreated after the rebuild; the three document triggers are dropped explicitly because CREATE TRIGGER IF NOT EXISTS cannot replace one-column bodies.
- [Phase 19]: 19-08: both BM25 branches use a MATERIALIZED weighted-match CTE and apply min_score to m.score before LIMIT/OFFSET, so a raised title weight moves ordering and thresholding together; bm25(documents_fts, ?, ?) names the real table with bound weights.
- [Phase 19]: 19-08: SearchOptions.title_weight is an internal measurement-only override (None = _TITLE_WEIGHT 1.0); no setting and no CLI flag per D-11, and 19-09 pins the accepted value back into the constant.
- [Phase 19]: 19-08: at 1.0/1.0 the weighted bm25 expression reproduces rank exactly; the SC1 golden's two BM25-bearing rows moved while ordering/RRF/vector scores did not, and the held-out metrics were unchanged so only its rationale was extended with the title-column and H1-duplication caveat.
- [Phase 19]: 19-08: the title-FTS claim is scoped to tokenized EN-style titles; no lexical CJK title win is claimed or tested (porter treats contiguous CJK runs as single tokens).
- [Phase 19]: 19-09: SearchBackend runs Database.init_schema with the backend's own embedding dimension and commits before closing; the commit is required or the FTS rebuild/trigger/vocab statements roll back and leave a detected-as-migrated but empty index.
- [Phase 19]: 19-09: Database.init_schema(embedding_dim=N) skips get_settings when N is supplied, so an MCP-only host migrates the title FTS, triggers, and idx_documents_mtime at startup; the no-argument form and the dimension-mismatch RuntimeError are unchanged.
- [Phase 19]: 19-09: --compare reports per-leg and per-leg x split gates as additive legs/leg_splits keys and tables; absent combinations are sufficient=false with no winner, and warrants_default_change remains only the held-out summary gate.
- [Phase 19]: 19-09: D-12 rejected the 2.0/3.0/4.0 title-weight band with numbers — the held-out title leg was already at its 1.0 ceiling and the body held-out leg stayed flat at 0.900634933653854 — so _TITLE_WEIGHT stays 1.0; the sweep migrates the scratch index through init_schema first and aborts without a title column; verdict in bench/d12-verdict.json.
- [Phase 20]: 20-01: FilterNode parse_filter/parse_match implement qmd's 17 operators with field (D-18); parity pin qmd [Unreleased] @86d2365 verified 2026-11-15, superseding abfabc5's key naming.
- [Phase 20]: 20-01: compiler emits presence-aware ne/nin (EXISTS + NOT EXISTS), per-element all, instr/BLOB-substr text ops, half-open path prefix (idx_documents_path), and mtime ranges (idx_documents_mtime); values are never interpolated.
- [Phase 20]: 20-01: typed kv rows derive from canonical JSON in DocumentRepository.create/.update; filterable_metadata shadows path/mtime only, leaving qmd.metadata merge and caps to 20-02.
- [Phase 20]: 20-01: unfiltered BM25 is byte-identical to the pre-change capture (golden recording-connection test); --filter parses/validates before the database opens.
- [Phase 20]: 20-02: qmd.metadata resolution drops the qmd key only when qmd.metadata is a mapping; other qmd shapes remain native keys (nested-skipped).
- [Phase 20]: 20-02: typed_rows classifies sorted resolved keys (deterministic caps); list-of-lists is mixed_array, arrays containing objects nested; skips bounded at 64 rows/document.
- [Phase 20]: 20-02: backfill reads stored canonical documents.metadata with one short transaction per document; metadata_values_version is written to index_meta only after a complete pass and failures propagate out of create_all.
- [Phase 20]: 20-02: bench fixture derives synthetic bench_category/bench_doc keys through canonical_metadata_json; the frozen corpus and all ranking goldens are untouched.
- [Phase 20]: 20-03: filtered escalation keys the all-matches stop on distinct documents from RAW KNN rows and compares fetch_k to the GLOBAL vector count (a scoped count ended escalation on batch one).
- [Phase 20]: 20-03: the D-09 notice is gated on is_metadata_filtered, pre_count >= page_target, the ceiling exhausted, and a short page; collection-only searches never warn and stdout stays clean.
- [Phase 20]: 20-03: the post-KNN filter suffix is AND-prefixed; the unfiltered/unscoped path keeps the pre-change statement bytes, fetch window, stop condition, and emits no pre-count.
- [Phase 20]: 20-03: hybrid/pipeline filter passthrough is structural via dataclasses.replace (identity-asserted per leg); the single offset slice and ONE enrich at pipeline exit are unchanged.
- [Phase 20]: 20-03: the integration sqlite-vec skip lives inside the corpus fixture, never at module scope, so repo-level discovery tests can run on hosts without the extension.
- [Phase 20]: vsearch/query parse --filter before open_initialized_database, mirroring 20-01; an invalid filter never opens the index or pays _pre_search_refresh, and the filter param sits in the defaulted signature tail (Click binds by name).
- [Phase 20]: CLI AST errors keep 20-01 shipped spelling filter.<operator-path> with the field named inline (e.g. filter.gt: "gt" requires a numeric value; field tags got str); the plan example filter.tags.gt was reconciled in the test, never by rewriting the validator.
- [Phase 20]: MCP filter is a raw dict validated inside QueryToolHandler.handle via parse_filter; grammar/budget failures return ToolsCallResult(isError=True) with no stack trace, model-shape failures keep the server generic isError catch, and neither is ever INVALID_PARAMS.
- [Phase 20]: SearchBackend.hybrid_search takes filter_node (ruff A002), sets SearchOptions.filter by identity, and the BM25 degrade path receives the same options; annotated model fields keep the name filter with no noqa (A003 does not fire, RUF100 would).
- [Phase 20]: Discovery reads the same typed store as the filter compiler: documents is the collection-scope denominator, filteredDocuments appears only with a filter, and the fixed path/mtime builtIns section comes from the documents columns (D-16/D-03/D-20).
- [Phase 20]: The MCP metadata envelope (MetadataInput/MetadataOutput with builtIns) is frozen as the Phase 22 contract; CLI JSON emits the same envelope, with filteredDocuments absent when no filter was supplied.
- [Phase 21]: 21-01: identity JSON excludes source+fingerprint from the hash; comparison is field-wise with one-sided unknown-tolerance for pooling/revision, never fingerprint equality
- [Phase 21]: 21-01: cache vector validation uses the identity dimension (loaded model truth) for writes and reads; invalid entries become misses and are overwritten (T-21-01)
- [Phase 21]: 21-01: prompt scheme resolves once at manager construction and effective names reach the factory; no model-wide default_prompt_name, Qwen3 stays prompt-free
- [Phase 21]: 21-01: role dispatch is class-level (type(embedder)) so MagicMock never takes a phantom role path; protocol-only doubles keep embed/embed_batch
- [Phase 21]: 21-01: config-doc generator SECTIONS extended with query/document_prompt_name; generator-owned docs regenerated, never hand-edited
- [Phase 21]: 21-02: the shadow DDL is vec0-conditional and _create_embedded_documents_table returns None on a vec0-free database, so create_all issues no shadow SQL, writes no marker, and never raises
- [Phase 21]: 21-02: backfill forces the DELETE+INSERT pass when the table did not pre-exist even if the marker matches; rows come only from JOIN documents and the marker is written after the complete pass
- [Phase 21]: 21-02: staleness keeps the display gate and None degradation byte-identical while reading one probe plus indexed shadow PK lookups; the vec0 one-scan batching rule now applies only to get_all_embedded_chunk_ids
- [Phase 21]: 21-02: reconcile_embedded_documents leaves the commit to the caller (cleanup/vacuum wiring is 21-06) and sif status computes vector lag with one NOT EXISTS anti-join over byte-identical strings
- [Phase 21]: 21-03: the context-map cache is keyed by the resolved main DB path, never a connection object; :memory: databases and connections with an open transaction bypass it so no snapshot or uncommitted read is ever cached
- [Phase 21]: 21-03: invalidation samples the repository write generation, the sentinel PRAGMA data_version, and the inode before building; any sentinel failure closes it, drops the entry, and bypasses without caching
- [Phase 21]: 21-03: enrich_results gained keyword-only vectors_untrusted=False applied after the normal staleness pass; no call site changed, so two-argument callers and monkeypatched doubles stay intact
- [Phase 21]: 21-08: IdentityDimensionError + dimension_mismatch_text + schema_dimension_remedy live in identity.py; the schema guard and OpenAI messages stay byte-identical (D-05/T-21-27)
- [Phase 21]: 21-08: with an initial identity the schema width guard is check_identity(mode="init"); an injected dimension without one stays width-only and never reads settings (Phase 19 contract)
- [Phase 21]: 21-08: create_all assumes a legacy populated index once (one warning, no blocking) after the shadow backfill; fresh/embeddings-empty indexes write no identity row (D-02/D-04)
- [Phase 21]: 21-08: the watcher adopts manager.get_identity() in one short transaction (mismatch rolls back, one error event, embed disabled, BM25 continues); the MCP backend reuses one resolved prompt scheme for init_schema and factory.create_model and stores the full identity as self._identity (T-21-28)
- [Phase 21]: 21-04: SearchPipeline evaluates an injected identity closure once per instance and only on VECTOR/HYDE/hybrid exits; the BM25 exit returns before the call so lexical search is check-free.
- [Phase 21]: 21-04: a hybrid width mismatch runs the BM25 variant search through the same fusion/rerank/paginate/enrich path and marks every row stale; vec:/hyde: raise IdentityDimensionError, vsearch/bench/eval refuse with the shared search_dimension_error remedy.
- [Phase 21]: 21-04: hosts only enforce when the manager returns a real EmbedderIdentity (injected doubles have no policy); CachedEmbedder memoizes role APIs by (role, text) via one-element batch calls, and expansion normalizes EmbeddingResponse vs bare-list candidates.

### Pending Todos

- [ ] (Backlog) Phase 10 regen code review: WR-01..WR-10 open — ledger in 10-REVIEW-DISPOSITION.md
- [ ] (Backlog) Phase 10.1 regen code review: IN-10..IN-13 — ledger in 10.1-REVIEW-DISPOSITION.md

### Blockers/Concerns

- ⚠️ [Phase 11 re-review, advisory] WR-03 init_schema raw tracebacks, WR-04 impossible-state guards, IN-05 model-type set duplication — carried in 11-REVIEW-DISPOSITION.md (WR-01/WR-02 fixed)
- [Research gaps — resolve at plan time] qmd filter AST is UNRELEASED (re-verify CHANGELOG at Phase 20); MCP py3.10 install/import smoke at Phase 22 start; transport_security spoofed-header proof before deleting custom middleware (22); documents_fts_v vocab shadow survival on populated DB (19); contexts normalization decision touches a locked Key Decision (21 discussion)
- ✅ [17-07 resolved 2026-11-14] The TestPyPI `invalid-publisher` blocker was the missing/mismatched pending publisher. The maintainer created and verified it (project `docsif`, publisher GitHub, repository `zhangtaolab/SIF`, workflow `publish.yml`, environment `testpypi`); the next OIDC attempt minted successfully on Publish run `43562577065` attempt 4. No trusted-publishing fallback was needed. Nothing had been uploaded on attempts 1-3, so version 1.1.2 was published cleanly rather than consumed by a partial upload.

### Roadmap Evolution

- 2026-11-13: v1.2 roadmap created — Phases 17-24 (numbering continues from v1.1's 16.1; no reset). Cross-phase contracts recorded in ROADMAP.md: embedder identity/role-aware embed (21 → 22/23), `metadata` tool schema (20 → 22), docs-generate gate (every phase adding commands/settings)

## Deferred Items

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| Feature | MODEL-F1 GGUF Harrier arm (only if MODEL-01/02 gate passes AND quantized deployment wanted) | Conditional follow-up | 2026-11-13 | v1.2 |
| Feature | WIN-F1 full Windows support (daemon/service/flock parity) | v2+ | 2026-11-13 | v1.2 |
| Feature | FUTR-01 spellfix1 DYM acceleration | Superseded by rapidfuzz (QUAL-01) | 2026-11-07 | v1.1 |
| Feature | FUTR-02 LLM-assisted weight tuning | v2+ | 2026-11-07 | v1.1 |
| Feature | FUTR-03 symspellpy DYM fallback (only if >200k-vocab gaps) | v2+ | 2026-11-07 | v1.1 |
| Candidate | EVAL-F1 LLM-judge grading · FILT-F1 saved filters · QUAL-F1 sweep automation | v1.x candidates | 2026-11-13 | v1.2 |

## Session Continuity

Last session: 2026-11-15T17:18:35.466Z
Stopped at: Completed 21-04-PLAN.md
Resume file: None

- **Next expected action:** plan and execute Phase 21 (Scale, Maintenance + Embedder Identity — SCALE-01..03, EMB-01/02), then 22 → 23 → 24. Phase 20 delivered FILT-01..05: shared 17-operator filter grammar on CLI+MCP, `path`/`mtime` built-ins, pre-RRF per-leg pushdown with the corrected vector escalation, typed kv storage + `index_meta`-gated backfill, and the `metadata` discovery tool whose envelope is the frozen Phase 22 contract. Two audits remain recorded as debt (see Blockers/Concerns): `/gsd-secure-phase 20` and `/gsd:validate-phase 20`.
