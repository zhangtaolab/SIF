---
gsd_state_version: "1.0"
milestone: v1.2
status: Awaiting next milestone
stopped_at: Phase 24 complete — all phases complete
last_updated: "2026-11-26T10:10:00.000Z"
last_activity: 2026-11-26
last_activity_desc: Phase 19 second gap-closure plans 19-13, 19-14, 19-15 committed (c3d2db7) and plan-checked (round 2 - 0 blockers, 0 warnings, 7 advisories); awaiting operator confirmation of A-19-9-1 before /gsd-execute-phase 19 --gaps-only
state_head: c3d2db7
milestone_name: Search Precision and Agent Experience
current_phase: 24
progress:
  total_phases: 8
  completed_phases: 8
  total_plans: 55
  completed_plans: 55
---

# DocSift — Project State

## Project Reference

- **Name:** DocSift (package `sif`, PyPI `docsif`)
- **Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。
- **Current Focus:** v1.2 Search Precision and Agent Experience — **shipped and archived 2026-11-18**: PR #3 merged `dev` → `main` (merge commit `975cb09`), tag `v1.2.0` pushed, `docsif 1.2.0` published to TestPyPI and PyPI (Publish run 44289577210), and the milestone closed to `.planning/milestones/v1.2-*`. All 8 phases verified `passed` with fresh fingerprints (17: 55/55, 18: 44/44, 19: 63/63, 20: 26/26, 21: 63/63, 22: 77/77, 23: 31/31, 24: 43/43 truths), all `threats_open: 0`. Next milestone is not yet planned.
- **Tech Stack:** Python 3.10+, SQLite (FTS5 + sqlite-vec), Click, Pydantic, sentence-transformers 5.4.1 (locked), llama-cpp-python; v1.2 added ONLY `mcp>=2.3.0,<3` + `rapidfuzz>=3.14.5,<4`
- See: .planning/PROJECT.md (updated 2026-11-18)
- Archives: v1.0/v1.1/v1.2 phase artifacts, full decision logs, per-plan metrics under .planning/milestones/

## Current Position

Phase: Milestone v1.2 complete
Plan: —
Status: Awaiting next milestone
Last activity: 2026-11-26 - Phase 19's second gap-closure round planned: plans `19-13` (exact `--min-score` threshold, gap G-19-8), `19-14` (truthful text for `query --min-score`, gap G-19-9, under assumption `A-19-9-1`) and `19-15` (three unguarded behaviours, gap G-19-10) committed at `c3d2db7` and plan-checked (round 2: 0 blockers, 0 warnings, 7 advisories); the UAT record was corrected at `43b4dc3`. Earlier the same day - Phase 19 UAT completed by the orchestrator as tester at the operator's request (`f5ece6b`): 10 tests, 7 passed and 3 issues, all three diagnosed in `19-UAT.md` and not yet planned (G-19-8, the exact-threshold drop of IN-09; G-19-9, what `query --min-score` compares, IN-10; G-19-10, three unguarded behaviours). Tests 4 and 5 were accepted as the tester's verdict and can be reversed. Earlier the same day - Phase 19 gap closure executed and re-verified: plans 19-10 (chunk identity on the per-chunk surfaces), 19-11 (G-19-2 before-evidence; operator decision monotone-map) and 19-12 (monotone BM25 score, bound `-M/(1-M)`, fourth 19-05 truth amended) ran from 4e258cf to d5382ae; gates green (3303 passed, 1 skipped, 95.16%); verification re-run at `d12fc6e`: human_needed, 85/90 truths, none failed; UAT updated at `9aa5125` (tests 1, 2 and 7 pass; seven decisions pending). The round re-staled the verifications of Phases 17, 18 and 24. Earlier, 2026-11-25 - Phase 17 gap closed and re-verified: plan 17-10 restored the 8-cell CI matrix and every-branch push trigger; verification passed; Test Matrix run 45522236981 green on 8/8 cells + lint (95.12% each); UAT complete. Phase 24 was re-verified 2026-11-24 and again 2026-11-25 (10691bd, 43/43 truths) after plan 17-10 changed tests/test_ci_workflows.py. Phase 18 was re-verified 2026-11-25 (2f4fff8, 44/44 truths). Phase 19 was re-verified 2026-11-25 (b3633c9): human_needed, 61/63 truths, 2 uncertain (truths 17 and 34), five decisions pending in 19-UAT.md.

## Performance Metrics

- **Velocity:** v1.0 shipped 68 plans / 11 phases (2026-04-14 → 2026-11-07); v1.1 shipped 27 plans / 7 phases (2026-11-07 → 2026-11-12); recent plans averaged ~13-20 min
- **Suite at v1.1 close:** 1591 passed, 1 skipped @ 95.18% coverage (fail_under=90 active); ruff/format/ty green
- **v1.2 shipped:** 8/8 phases, 55/55 plans — suite 3234 passed / 1 skipped @ 95.03% coverage; ruff/format/ty green; CI 8/8 matrix + Docs Validation green; `docsif` 1.2.0 on PyPI

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
| Phase 21 P05 | 10min | 3 tasks | 9 files |
| Phase 21 P06 | 8min | 3 tasks | 8 files |
| Phase 21 P07 | 7min | 3 tasks | 9 files |
| Phase 22 P01 | 24min | 3 tasks | 23 files |
| Phase 22 P02 | 15min | 3 tasks | 24 files |
| Phase 22 P03 | 11min | 3 tasks | 10 files |
| Phase 22 P04 | 12min | 3 tasks | 12 files |
| Phase 22 P05 | 17min | 3 tasks | 17 files |
| Phase 22 P06 | 10min | 3 tasks | 12 files |
| Phase 22 P07 | 7 | 3 tasks | 5 files |
| Phase 23 P01 | 8min | 2 tasks | 6 files |
| Phase 23 P2 | 6min | 2 tasks | 2 files |
| Phase 23 P03 | 13min | 3 tasks | 4 files |
| Phase 23 P04 | 5min | 3 tasks | 3 files |
| Phase 23 P05 | 5min | 3 tasks | 1 files |
| Phase 23 P06 | 4min | 2 tasks | 1 files |
| Phase 24 P01 | 15 | 2 tasks | 4 files |
| Phase 24 P02 | 10min | 2 tasks | 11 files |
| Phase 24 P03 | ~9 min | 2 tasks | 2 files |
| Phase 24 P07 | ~20 min | 3 tasks | 6 files |
| Phase 24 P04 | ~7 min | 3 tasks | 8 files |
| Phase 24 P05 | 20 min | 3 tasks | 10 files |
| Phase 24 P06 | ~3h | 3 tasks | 17 files |

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
- [Phase 21]: 21-05: StreamingEmbedWriter runs chunk+embed outside any transaction and commits one short per-document transaction carrying chunks, vectors, the shadow row, stats, and the first-write identity; embed_cmd and the watcher share it.
- [Phase 21]: 21-05: D-15 refinement — collection stats recompute once per collection in one O(N) joined count; a collection aborting mid-loop keeps previous counts until its next successful run.
- [Phase 21]: 21-05: identity enforcement is host-gated on a real SQLite connection + real EmbedderIdentity (21-04 injected-double precedent); the writer's identity=None path exists only for test doubles.
- [Phase 21]: 21-05: batch sanity checks count/dimension/finiteness/L2 norm with stdlib math; a violation persists nothing and aborts after prior commits; locked/busy SQLite is systemic, every other document exception is local and re-queueable.
- [Phase 21]: 21-05: source=verified only from a fresh index's first commit or a complete unfiltered zero-failure --force; an empty-index --force certifies vacuously and D-02 lets the next embedder's first write replace it.
- [Phase 21]: 21-06: vacuum_index measures (database + WAL) after the reconcile commit, checkpoints TRUNCATE, prechecks 2x that size with required/available bytes, then VACUUMs with conn.in_transaction asserted False at execute time; the final checkpoint is advisory (warning) while the first busy checkpoint is retryable
- [Phase 21]: 21-06: backup_index validates the target before any connection (symlink checked before resolve, existing file, DB/WAL/SHM/lock collision, stale target sidecars) and refuses a missing source; the copy is Connection.backup on a fresh target connection, verified with PRAGMA integrity_check == [('ok',)] and chmod 0600
- [Phase 21]: 21-06: backup/OS failure removes the just-created copy, an integrity failure keeps it and names the copy plus integrity rows; busy/locked maps to MaintenanceBusyError in both maintenance commands and the CLI translates to a retryable click.ClickException
- [Phase 21]: 21-06: cleanup reconciles embedded_documents inside its existing db.transaction() and prints removed/added counts; no second transaction, the vec0 OperationalError swallow stays, and a missing shadow/vec0 remains a no-op
- [Phase 21]: 21-06: docs/cli-reference.md was regenerated by make docs-generate for index vacuum/backup and a second run leaves both generated docs byte-identical; docs/configuration.md unchanged
- [Phase 21]: 21-07: the D-19 baseline is recorded as literals (modelscope:Qwen/Qwen3-Embedding-0.6B plus the prompt-free defaults tuple) asserted against the code, never regenerated from it
- [Phase 21]: 21-07: a role-capable embedder with no prompt must reproduce the recorded SC1 hybrid page byte-for-byte, which is the default-path D-19 proof
- [Phase 21]: 21-07: legacy upgrade tests build a real index then strip the shadow, its marker, and the identity row so production create_all performs the upgrade
- [Phase 21]: 21-07: a fresh first embed writes exactly embedded_documents_version, metadata_values_version, embedder.identity plus one shadow row and a verified identity
- [Phase 21]: 21-07: the phase gate is green at 2734 passed / 1 skipped / 95.22% coverage with ruff, format, ty, generator-clean docs, and no dependency change; maintenance concurrency and MCP policy needed no new tests
- [Phase 22]: 22-01: tools and the docs:// resource are registered inside the SDK lifespan (where SearchBackend is constructed) behind a one-registration guard; Annotated[CallToolResult, Model] return annotations publish outputSchema while the explicit builder keeps compact text + structuredContent.
- [Phase 22]: 22-01: build_server records its resolved TransportSecuritySettings on the server and create_http_app reuses it; verified SDK codes are bad Host 421, bad Origin 403, non-JSON Content-Type 400.
- [Phase 22]: 22-01: outputSchema/structuredContent appear on 2024-era responses (C9) and the five goldens record it; the writer is re-runnable via SIF_UPDATE_WIRE_GOLDENS=1 for 22-02/22-04/22-05.
- [Phase 22]: 22-01: the status-only e2e bridge skips three query-dependent watch tests and the drift test's query tail with a reason naming 22-02's seven-tool battery; the intermediate SDK surface is a dev-branch state with no release.
- [Phase 22]: 22-01: SearchBackend construction is model-free (no factory/load/identity) with _load_lock/_load_attempted/_load_failed for 22-04; the docsift migration notice moved to console_err on stderr.
- [Phase 22]: 22-01: package legitimacy for mcp==2.3.0 approved by the maintainer 2026-11-16 (official modelcontextprotocol/python-sdk, MIT); uv.lock regenerated add-only with no existing package version change.
- [Phase 22]: 22-02: per-tool registration helpers keep register_tools under mccabe 10; every tool keeps the Annotated[CallToolResult, Model] return annotation so outputSchema derives with no type ignore.
- [Phase 22]: 22-02: vec_search maps RuntimeError (no embedder/dimension mismatch/sqlite-vec) to ToolError with the install/model remedy; _ensure_embedder is one locked attempt and stores the identity only when it is a real EmbedderIdentity.
- [Phase 22]: 22-02: lex/vec direct paths share _resolve_collection_ids/_map_core_results with hybrid and each owns exactly one enrich_results; min_score is additive on both inputs.
- [Phase 22]: 22-02: the seven-tool battery proved dual-channel parity, idempotency (unchanged data_version/row counts), wire isError, and the real Phase 20 envelope before the shell, wire types, and replaced tests were deleted.
- [Phase 22]: 22-02: all four watch e2e proofs run live again; the five goldens were regenerated for seven tools with only tools/list changed and initialize/status byte-identical.
- [Phase 22]: 22-03: explicit --allowed-hosts values UNION the loopback defaults and a literal wildcard is dropped, so a bind name can never remove loopback or disable validation; a non-loopback bind without the flag warns instead of widening (D-13).
- [Phase 22]: 22-03: /health carries a narrow FastAPI Header dependency over the same resolved allowlist and answers a bad Host with 421, matching the SDK /mcp status (C2).
- [Phase 22]: 22-03: the MCP daemon owns <db>.mcp.pid (mode mcp, depth bm25); corroborate_pid/stop_daemon take a keyword-only marker defaulting to watch, so watch and MCP daemons coexist and each --stop signals only its own process (D-20/C5).
- [Phase 22]: 22-03: mcp daemon arms quietly on a schema-ready, model-free backend before bind, removes the PID in finally on every exit path, and the POSIX e2e uses real sif.cli.main subprocesses to prove initialize, stop, bind-failure cleanup, and watch coexistence.
- [Phase 22]: Prefix-first routing resolves lex:/BM25 before any load decision; a latched load failure degrades query directly to BM25 over prefix-free text with the loader's one warning (D-15).
- [Phase 22]: Query now reuses CLI SearchPipeline components per request; rerank is gate-before-construct, latches ImportError/ValueError with one warning, and retries execution failures with reranker=None (D-17).
- [Phase 22]: 22-05: extract_with_range reports the inclusive snippet window and extract() delegates to element 0, so CLI snippet bytes never move; line_start/line_end are dataclass-only and excluded from to_dict.
- [Phase 22]: 22-05: content_hash is the stored documents.checksum fetched by one batched get_checksums call per result page; get is 1..N or the requested range, and the direct lex/BM25 routes keep the documented no-snippet deviation while attaching hashes.
- [Phase 22]: 22-05: the frozen Phase 20 metadata envelope is deep-equaled on both channels; five era goldens were regenerated and only tools/list exchanges changed.
- [Phase 22]: 22-06: the repo root is a sif plugin/marketplace; plugin and marketplace versions mirror _version.py and .mcp.json runs only the installed sif mcp stdio with no path or credentials.
- [Phase 22]: 22-06: plugin skills under skills/ grant mcp__sif__ tools only and keep the untrusted-content warning; sif-cite requires get before citing docid plus lines and forbids snippet-only citation.
- [Phase 22]: 22-06: the gate is plain claude plugin validate --json . (success, zero errors, no description warning); the repo-root CLAUDE.md warning is tolerated and --strict stays banned.
- [Phase 22]: 22-06: docs/mcp-server.md and src/sif/mcp/README.md describe the SDK composition root and seven-tool surface; README makes uv tool install docsif[embed] primary with a BM25-only base and uvx fallback.
- [Phase 22]: 22-07 Task 2 recorded `blocked no-github-login` (user decision 2026-11-16): the optional public MCP Registry listing is deferred; no GitHub auth was performed and no publish attempted. The local MCP server/plugin/skills/transports need no GitHub login. 22-07 Task 3 proceeds with the blocked outcome recorded in 22-07-SUMMARY; re-run `python scripts/publish_registry.py --publish` after a future `mcp-publisher login github`. — Plan D-24 explicitly allows a blocked run as a non-code outcome, and --publish is idempotent (already listed), so deferring loses nothing.
- [Phase 22]: 22-07 Task 2 (live MCP Registry publish) recorded as blocked: user chose 'blocked no-github-login' on 2026-11-16; no mcp-publisher login, publish, or credential storage was attempted, and D-24 explicitly permits the blocked non-code outcome.
- [Phase 22]: 22-07 real-client evidence uses the stream-json system/init event of a headless Claude Code session (2.1.325) because 'claude mcp get' reports connection status but not the seven-tool list; the temporary local-scope sif-smoke entry was removed after the run.
- [Phase 22]: 22-07 phase gate green: 2866 passed / 1 skipped at 95.11% coverage, ruff/format/ty clean, make docs-generate no-diff, claude plugin validate success with zero errors, registry --check green; _version.py stays 1.1.2 and no v1.2 tag exists.
- [Phase 22]: 22 code review: 2 Critical + 10 Warning fixed with pre-fix failing regression tests (CR-01 lazy-load lock, CR-02 vec_search off the event loop, WR-01/02/03/05/06/07/08/09/10/11); 1 necessity (WR-04) + 8 Info remain open per project convention; verifier found non-blocking W-01 (multi_get explicit max_bytes line range) as a follow-up.
- [Phase 22]: 22 verified 77/77 must-haves and marked complete 2026-11-16; suite 2889 passed / 1 skipped @ 95.13% coverage, ruff/format/ty/docs-generate/plugin-validate/registry --check green; no v1.2 tag; public Registry listing remains blocked no-github-login (deferred maintainer action).
- [Phase 23]: Defaulted ComparisonReport.language_splits/leg_language_splits keep the Phase 18 constructor and output valid while adding per-language evidence
- [Phase 23]: Language-aware widening adds the language floor to both the widening loop and the cap guard; required_languages=() is byte-identical
- [Phase 23]: The --require-language option is click.Choice(LANGUAGES); compare mode warns once on stderr and never resamples the saved query set
- [Phase 23]: 23-02: A missing overall held-out gate is insufficient-evidence with zeroed overall fields; language evidence is still recorded for audit
- [Phase 23]: 23-02: Non-mapping top-level language_splits raises ValueError; missing/malformed per-language entries are absent evidence, never a pass
- [Phase 23]: 23-02: VerdictDecision.to_dict emits a fixed 16-key order with copied nested maps, and adopt-harrier carries empty reasons while every rejection names its failed conditions
- [Phase 23]: 23-03: Per-arm env removes API base/key and prompt keys entirely so Qwen3 keeps the exact modelscope cache id and Harrier gets web_search_query from the known-model table
- [Phase 23]: 23-03: Run state is keyed to the resolved corpus roots plus label; a changed --corpus set discards every marker, and an inadequate adequacy verdict is recorded but never marked complete
- [Phase 23]: 23-03: The pairwise identity gate runs after arm B's probe (both stored identities exist); the artifact maps the comparison payload's gate leaf to the documented overall leaf
- [Phase 23]: 23-04: Real two-arm EN+ZH run recorded keep-qwen3 — overall held-out mean delta +0.009430 at N=56 (CI includes zero, below the 0.01 epsilon and 0.017857 1/N floor); the Qwen3-Embedding-0.6B default did not move
- [Phase 23]: 23-04: Corpus adequacy was gated before the embed — adequate=true with held-out en=42, zh=11, mixed=3; both required languages cleared N>=10
- [Phase 23]: 23-04: Both arm identities are source: verified at 1024 dimensions with distinct fingerprints, so the arms could not share an embedding cache bucket
- [Phase 23]: 23-04: The docs section records the full held-out/per-language/per-leg/per-leg-language gates, suppressed group names, per-arm costs, and replay unavailability; the committed artifact remains aggregate-only
- [Phase 23]: 23-04: The conditional default flip and explicit-Qwen3 zero-delta proof were not exercised by keep-qwen3 and remain pending for plans 23-05/23-06
- [Phase 23]: The blocking-human checkpoint resolved to keep-qwen3, matching the artifact decision; default_flip is recorded as not-applicable and no code or default-claim doc changed
- [Phase 23]: Plan 23-06 remains flip-conditional: with default_flip.decision not flipped, its specified branch records zero_delta_proof not-applicable without a model run
- [Phase 23]: Plan 23-06 executed its non-flip branch: default_flip.decision not-applicable means zero_delta_proof {status: not-applicable} is recorded and no model runs (D-10)
- [Phase 23]: No real-model explicit-Qwen3 comparison ran and no proof code or tests were added because the proof is flip-conditional
- [Phase 23]: The not-applicable block lives at default_flip.zero_delta_proof and every existing artifact field is unchanged
- [Phase 23]: 23 real EN+ZH A/B on a user-approved curated bilingual subset (7 Chinese-heavy folders, 498 docs; adequacy en=42/zh=11; held-out N=56) recorded keep-qwen3: overall Δ +0.00943 (CI [-0.0296,+0.0484]) below the 0.01 tie rule and strict 1/N floor; en +0.01385, zh -0.00487 above the -0.01 floor; default embedder unchanged; default_flip and zero_delta_proof recorded not-applicable; artifact + docs/benchmarking evidence committed.
- [Phase 23]: 23 code review: 2 Critical + 6 Warning fixed with regression tests (CR-01 scratch-root home/root guard, CR-02 stale-artifact prevention, WR-01 idempotent arm indexing/resume, WR-02 corpus-fingerprint scope invalidation, WR-03 held-out docs table, WR-04 artifact block preservation, WR-05 ranking settings recorded, WR-06 malformed-JSON error surface) plus IN-03 runbook ruff/format; 5 Info findings remain open. Regression gate 2,268 prior-phase tests passed.
- [Phase 24]: Chunk sweep selects on tuning, adopts only a strict held-out winner; every arm pins modelscope Qwen3/1024/512 and varies only chunk size/overlap
- [Phase 24]: The breadcrumb is an embed-text-only overlay: stored chunk content, chunks FTS, snippets, and BM25 stay byte-identical; only the embedding input changes.
- [Phase 24]: Settings embed_breadcrumb (SIF_EMBED_BREADCRUMB, default False) is the only switch surface; no CLI flag is added, and the default-off path passes raw chunk content byte-identically.
- [Phase 24]: A cache hit requires .sif-model.json with per-file size + SHA-256; manifestless directories re-download.
- [Phase 24]: Home legacy (~/.sif/models) detection applies only to the default cache root; explicit cache_dir is hermetic.
- [Phase 24]: Downloads stage in a sibling temp dir and replace the target only after verification, restoring the backup on failure.
- [Phase 24]: The breadcrumb arm is one isolated DB at 512/128 with SIF_EMBED_BREADCRUMB=1, pinned to modelscope Qwen/Qwen3-Embedding-0.6B, dim 1024, max_tokens 512, no prompts (D-04).
- [Phase 24]: A baseline saved run whose corpus fingerprint or model_type/model_name differs is rejected and a fresh breadcrumb-off Qwen3 baseline is generated, so no backend swap enters the breadcrumb delta (T-24-13).
- [Phase 24]: Breadcrumb adoption requires an overall held-out win plus a winning, sufficient body leg and a recorded duplicate summary; title-leg-only, flat, and regressing body legs are keep-breadcrumb-off with named reasons, and an absent body leg is insufficient evidence (D-04/D-05).
- [Phase 24]: Duplicate shares aggregate weighted by chunk count; the artifact records identity/model_type, min_heldout_for_epsilon_win=101, and the N=56 limitation, and refuses a differing decision or fingerprint without --force (T-24-06).
- [Phase 24]: Pull target resolution: configured embedder/reranker/registry ids or one-slash owner/name; unknown tokens fail with the accepted list; --force and --cache-dir reach the downloader.
- [Phase 24]: models status decides match/mismatch/dimension-mismatch from stored dimension, schema FLOAT width, and cache_model_id; source and display fingerprints are display-only (D-08).
- [Phase 24]: Backend probes use find_spec plus importlib.metadata.version with distribution names (llama-cpp-python, sentence-transformers, sqlite-vec); no backend import and no download.
- [Phase 24]: sif pull stays hidden and delegates registry/owner-name ids to models pull; legacy GGUF/URL path uses a 60s urlopen timeout and stderr-only notices.
- [Phase 24]: Install docs are uv-first (uv tool, uvx, pip order) with the explicit --torch-backend=cpu Linux recipe and a uv 0.9.19 floor; llama-cpp wheel recipes are marked manually verified.
- [Phase 24]: The degradation matrix separates CLI fail-fast from the MCP hybrid_search BM25 degradation, and model management documents the canonical manifest cache plus legacy migration.
- [Phase 24]: 24-06 corpus amended on 2026-11-17 (user-authorized) to `/Users/forrest/Playground/books_markdown` — 610 documents (2 English books + 608 mostly-Chinese papers; 422 zh-dominant, 163 en-dominant, 23 mixed) — because Phase 23's SynologyDrive roots are off-limits; artifacts are corpus-scoped to label `books-markdown-papers-2026-11`.
- [Phase 24]: `sif eval` gained the additive `--min-heldout` option (default 25, range 25–500); the runbooks pass 101 for the fresh baseline, which sampled 200 documents and produced held-out N=194 (en=136/zh=244/mixed=12), making the 0.01 gate admissible (1/N≈0.00515); the limitation text is generated from the measured N and the Phase 23 N=56 wording is retired.
- [Phase 24]: 24-06 real evidence is complete on the amended corpus: QUAL-02 `keep-default` (tuning-selected overlap-0 +0.000737, held-out -0.008605, CI [-0.021559, +0.003094], helped 2/hurt 9/unchanged 183, N=194) and QUAL-03 `keep-breadcrumb-off` (overall +0.014104, CI [-0.005664, +0.035548], winner false; title leg +0.048521 winner, body leg +0.006243 not; duplicate metrics title_share=1.0, in_content_share=0.622955; replay unavailable). No defaults changed, no marker code, no re-embed migration.
- [Phase 24]: Platform verification at `256380e` is green — macOS arm64: 3,233 passed / 1 skipped / 95.03%; Linux x86_64 (nv5090, Python 3.13.18): 3,232 passed / 2 skipped / 95.04% with ruff/format/ty green, using a shared torch 2.14.1+cu130 under `CUDA_VISIBLE_DEVICES=` and `-p no:platformdirs` because the CPU torch index was DNS-unreachable; Windows 11 (Yoga): `windows_smoke.py` 8/8 PASS plus 346 changed-area and 124 affected-module tests. Windows' 14 docs-test failures under GBK are pre-existing at `48759e2` and pass with `PYTHONUTF8=1`; full Windows support stays deferred to v2.
- [Phase 24]: Breadcrumb artifact write bug fixed: `breadcrumb_eval.write_committed_artifact` now defaults to its own `ARTIFACT_PATH` instead of forwarding `None` to the chunk-sweep path; the shared guard had refused the overwrite after a 34-minute arm run. The resumed artifact write took 0.38 s and a regression test pins the default path.

### Pending Todos

- [ ] (Backlog) Phase 10 regen code review: WR-01..WR-10 open — ledger in 10-REVIEW-DISPOSITION.md
- [ ] (Backlog) Phase 10.1 regen code review: IN-10..IN-13 — ledger in 10.1-REVIEW-DISPOSITION.md

### Blockers/Concerns

- ⚠️ [Phase 17, follow-up] The CI guards in `tests/test_ci_workflows.py` do not examine filters nested under `push:` / `pull_request:` (seven trigger shapes, plus four more noted in `17-SECURITY.md`), so `17-VALIDATION.md` reads `nyquist_compliant: false`; the recipe `test_matrix_triggers_are_unfiltered` is in its Manual-Only row 8. Adding it and re-running `/gsd-validate-phase 17` would restore compliance.
- ⚠️ [Phase 17, accepted risk AR-17-03] Plan 17-10 restored the 8-cell matrix on every branch push, re-exposing both causes of the 261118-lmm reduction: hosted macOS arm64 runner capacity cancelling PR jobs, and two full runs per feature-branch commit that has an open PR. The first run after the restore (`45522236981`) had no cancellation. Failure path: re-run a cancelled cell once; a renewed reduction needs a recorded decision against D-01/D-03, not a silent revert.
- ⚠️ [Phase 24, latent hazard WR-04] `scripts/chunk_sweep.py` and `scripts/breadcrumb_eval.py` still default their `ARTIFACT_PATH`, and `docs/benchmarking.md` still cite, the retired `.planning/phases/24-…` prefix. A re-run would write there, where the overwrite guard cannot see the archived `bench/` artifacts. Open in `24-REVIEW-DISPOSITION.md`; fix before any real sweep re-run.
- ⚠️ [CI, pre-existing] The Test Matrix lint job's `Type check` step is vacuous for code importing `transformers`, `huggingface-hub`, `sentence-transformers` or `torch`: the job installs none of them and `ty`'s `import-not-found = "ignore"` hides the resulting errors, so the 10 local `ty check src/sif` diagnostics go unchecked in CI. Found in the 2026-11-25 Phase 18 re-audit; fixing it means a workflow edit.
- ⚠️ [Phase 17 register, observation] `.github/workflows/docs.yml:33` installs with `pip install -e ".[dev]"` and so bypasses `uv.lock`; the Phase 17 security register does not mention it. Noted in the 2026-11-25 Phase 18 re-audit; triage pending.
- ✅ [BM25 `search`, resolved 2026-11-26] `--min-score` used to remove the best matches first (the displayed score was `1/(1+|bm25|)` and fell as the match improved). After the operator's `monotone-map` decision, plan 19-12 made the displayed score `|bm25|/(1+|bm25|)` and the predicate `m.score <= ?` bound `-M/(1-M)` (37b6315). Two items stay open in `19-REVIEW-DISPOSITION.md`: IN-09, with `--min-score` equal to a row's own displayed score that row is dropped in about 41% of cases (251 of 617 real bench rows), because the bound is not the exact inverse of the rounded score map, so the help text's "at least" does not hold at equality; IN-10, `sif query --min-score` filters each leg on its own scale and never the displayed RRF score. Both failed their UAT tests on 2026-11-26 and are diagnosed as gaps G-19-8 and G-19-9 in `19-UAT.md`; plans 19-13 and 19-14 close them and are not yet executed.
- ✅ [Phase 19 scope gap, resolved 2026-11-26] Plan 19-10 (4e258cf, 8cf0ec9) keeps `#sequence` on both per-chunk tables at 80 columns and carries chunk identity in per-chunk CSV, Markdown, XML and path-only output. The machine-format layout shipped under assumption `A-19-10-1`, UAT test 3 passed on 2026-11-26 as the tester's verdict at the operator's request; the layout can still be amended.
- ⚠️ [Phase 19 verification] `human_needed` at `d12fc6e` (85/90 truths, none failed): truths 17 and 34 are uncertain because Phase 20 (`bfc1b41c`) changed the offset start formula for scoped searches and Phase 21 replaced the batched `document_embeddings` scan with per-result lookups on the `embedded_documents` shadow (this also touches prohibition 19-03 P1). UAT tests 4 and 5 passed on 2026-11-26 as the tester's verdict (accepted for their guarantees), which the operator can reverse; the report reads `stale` since plans 19-13 to 19-15 landed, is re-verified after they run, and flips to `passed` only once the UAT holds no unresolved issue.
- ⚠️ [Phase 19 validation] `19-VALIDATION.md` reads `nyquist_compliant: false` after the 2026-11-26 audit (0d696e8): three behaviours have no test that fails without them, each right today by direct probe. V19-26-1, a document-level row has no sequence in per-chunk Markdown and XML; V19-26-2, a markup-bearing path renders literally in the per-chunk Chunk cell (the mitigation of T-19-24); V19-26-3, `search_chunks` uses the new score map. The Fix/Skip gate was put to the operator and not answered, so no test was added. Adding the three tests touches `tests/unit/cli/test_search.py` and `tests/unit/search/test_bm25.py` and re-stales Phases 19, 20 and 21 (UAT test 10, recorded as gap G-19-10 on 2026-11-26; plan 19-15 adds them and is not yet executed).
- ⚠️ [Phases 17, 18, 24, re-staled 2026-11-26] The Phase 19 gap closure changed `docs/changelog.md`, `docs/cli-reference.md`, `docs/benchmarking.md` and `tests/unit/search/test_hybrid.py`, which sit in the covered sets of Phases 17, 18 and 24, so their verifications read `stale` again (they read `passed` at `0441ad7`, `2f4fff8` and `10691bd`). No test covering those surfaces failed in the full suite or in the verifier's battery. `/gsd-execute-phase <N>` routes each to the verifier re-run gate.
- ⚠️ [quick task 261119-fww, test quality] IN-07: the relaxed title-cell assertions in `tests/unit/cli/test_search.py` lost their lower bound, so `_TITLE_MAX_LEN` (50) can drop to 10 without failing its only guard. IN-08: `tests.support.symlink_or_skip` turns any `OSError` (EEXIST, ENOENT) into a host-capability skip. Both open in `19-REVIEW-DISPOSITION.md`.
- ℹ️ [Phase 19 validation] A real coverage gap was closed on 2026-11-25: `f8ff9bea` added `TestRebuildChunkIdentity` (3 tests) pinning that the rerank rebuild keeps `chunk_id` / `sequence` / `chunk_matches` (CORR-02).
- ℹ️ [test hygiene, observed 2026-11-26] A full pytest run touches the real model cache: it updates the modification time of `~/Library/Caches/sif/models/.lock/cross-encoder___ms-marco-MiniLM-L-6-v2` and of `models/cross-encoder` (no path or size change), because the reranker tests build against the real cache (accepted risk T-19-36). Separately, a `sif` command that needs an embedder (`vsearch`, `query`) run with an empty scratch `SIF_CACHE_DIR` goes to the network and starts downloading the embedding model instead of failing. The Phase 19 verifier did this once by mistake on 2026-11-26; the request was aborted, no weights were written and the real cache was untouched.
- ℹ️ [CLI `index embed`, observation 2026-11-26] `sif index embed` prints `Already embedded: <path>` with the path unescaped in Rich markup (`src/sif/cli/commands/index.py:434`), and its collection-level error line does the same with the exception text (`:464`). A path holding text Rich reads as an unmatched closing tag (for example a directory named `[`, which gives `[/3]-review.md`) makes the command exit 1 before anything pending is embedded, and the error line then hides the first error; tag-like names such as `[red]…[/red]` lose their brackets in that line only. Found by accident during a UAT probe; the other commands were not audited for the same pattern.

- ℹ️ [Windows, pre-existing] 14 `tests/test_docs.py` tests fail under the GBK locale because they call `Path.read_text()` without an encoding; the same failure occurs at the untouched `48759e2` checkout. Use `PYTHONUTF8=1` for Windows runs, or make the docs tests UTF-8-explicit in a future Windows-support phase. Full Windows support remains deferred to v2.

- ✅ [Phase 24, resolved 2026-11-17] 24-06 corpus amended to `/Users/forrest/Playground/books_markdown` (610 docs: 2 English books + 608 mostly-Chinese papers; sampled 200, held-out N=194, en=136/zh=244/mixed=12) after the user supplied the papers and authorized the instrument extension. Both real runs completed and recorded keep-defaults; artifacts are in `bench/`, evidence in `docs/benchmarking.md`; Phase 24 verification remains. SynologyDrive was never read or written.
- ⚠️ [Phase 11 re-review, advisory] WR-03 init_schema raw tracebacks, WR-04 impossible-state guards, IN-05 model-type set duplication — carried in 11-REVIEW-DISPOSITION.md (WR-01/WR-02 fixed)
- [Research gaps — resolved] qmd AST parity pinned in Phase 20; MCP py3.10 install/import smoke and transport_security spoofed-header proof completed in Phase 22; documents_fts_v shadow survival covered in Phase 19. Remaining: contexts normalization decision touches a locked Key Decision (21 discussion)
- ⚠️ [Phase 22, debt] `22-VALIDATION.md` is still `status: draft` (nyquist validate-phase not run) and no `22-SECURITY.md` exists (secure-phase not run); recorded by `phase.complete` warnings — same audit-debt pattern as Phases 20/21
- ⚠️ [Phase 22, follow-up] W-01: `multi_get` computes `_full_line_range` before `_truncate_content` when an explicit `max_bytes` exceeds the 100 KiB default; the default budget and the `get` citation path are unaffected
- ⚠️ [Phase 22, deferred] Public MCP Registry listing for `io.github.zhangtaolab/sif` remains unlisted (`blocked no-github-login`); re-run `mcp-publisher login github` + `python scripts/publish_registry.py --publish` when wanted
- ⚠️ [Phase 23, debt] `23-VALIDATION.md` remains `status: draft` (nyquist validate-phase not run) and no `23-SECURITY.md` exists (secure-phase not run); recorded by `phase.complete` warnings
- ⚠️ [Phase 23, follow-up] Five open Info review findings: IN-01 (Rich markup path in eval), IN-02 (per-arm identity gate records but does not explicitly compare revision), IN-04 (`docs/benchmarking.md` omits `--require-language`), IN-05 (stale zero-delta sentence), IN-06 (cleanup leaves Harrier saved run/comparison JSON)
- ℹ️ [Phase 23, corpus scope] The real A/B ran on a user-approved curated bilingual subset (7 Chinese-heavy folders, 498 docs, en=42/zh=11, held-out N=56), not the full 6,213-doc corpus; the artifact and docs scope the claim, and Qwen3 remains the default. A larger bilingual corpus (held-out N≥101) would be needed for the 0.01 tie rule to be admissible.
- ℹ️ [Phase 23, housekeeping] `.planning/tmp/phase-23/` holds a stale preliminary Qwen3 DB from the earlier 8-root scope; the real evidence is in `.planning/tmp/phase-23-zh-heavy/`. Both are gitignored; deletion is optional.
- ✅ [17-07 resolved 2026-11-14] The TestPyPI `invalid-publisher` blocker was the missing/mismatched pending publisher. The maintainer created and verified it (project `docsif`, publisher GitHub, repository `zhangtaolab/SIF`, workflow `publish.yml`, environment `testpypi`); the next OIDC attempt minted successfully on Publish run `43562577065` attempt 4. No trusted-publishing fallback was needed. Nothing had been uploaded on attempts 1-3, so version 1.1.2 was published cleanly rather than consumed by a partial upload.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261118-i0b | Update the torch dependency floor to >=2.14 (embed and all extras), regenerate uv.lock, update contract tests and install docs | 2026-11-18 | a13b134 | [261118-i0b-update-the-torch-dependency-floor-to-2-1](./quick/261118-i0b-update-the-torch-dependency-floor-to-2-1/) |
| 261118-ib0 | Fix GitHub issues #4 (L2-norm gate abort on Qwen3-Embedding) and #5 (model cache root omits /models) | 2026-11-18 | 5f9c086 | [261118-ib0-fix-github-issues-4-l2-norm-gate-abort-o](./quick/261118-ib0-fix-github-issues-4-l2-norm-gate-abort-o/) |
| 261118-ipu | Follow-up fixes: normalize cached embeddings on read (issue #4 stale-cache gap) and make the Qwen3 reranker CPU-load test hermetic on GPU hosts | 2026-11-18 | ffad91b | [261118-ipu-follow-up-fixes-normalize-cached-embeddi](./quick/261118-ipu-follow-up-fixes-normalize-cached-embeddi/) |
| 261118-jbj | Release v1.2.1: bump version across all parity surfaces, add changelog section, and update install docs for CUDA/MPS/CPU backends | 2026-11-18 | 62c5d99 | [261118-jbj-release-v1-2-1-bump-version-across-all-p](./quick/261118-jbj-release-v1-2-1-bump-version-across-all-p/) |
| 261118-lmm | Reduce the CI matrix to six cells (macOS only on py3.10/3.13) and trigger push CI only on main, updating the CI contract tests and docs | 2026-11-18 | f665eee | [261118-lmm-reduce-the-ci-matrix-to-six-cells-macos-](./quick/261118-lmm-reduce-the-ci-matrix-to-six-cells-macos-/) |
| 261119-bl9 | Verify Windows conda envs dnallm-cpu/cuda/xpu and add Intel XPU auto-selection (CUDA > XPU > MPS > CPU) with tests and docs | 2026-11-19 | 82df76b | [261119-bl9-windows-conda-env-verification-for-sif-c](./quick/261119-bl9-windows-conda-env-verification-for-sif-c/) |
| 261119-fww | Windows portability follow-ups: guard fcntl test imports, mark POSIX-only tests, fix Windows subpath filters, lower torch floor to 2.11 (2.14 recommended), regenerate uv.lock | 2026-11-19 | 848e6b6 | [261119-fww-windows-portability-follow-ups-guard-fcn](./quick/261119-fww-windows-portability-follow-ups-guard-fcn/) |
| 261119-juo | Release 1.2.2: bump the version literal and all parity surfaces (server.json, plugin/marketplace manifests, changelog, install docs, release-metadata tests) | 2026-11-19 | 9f6a227 | [261119-juo-release-version-1-2-2-bump-the-single-ve](./quick/261119-juo-release-version-1-2-2-bump-the-single-ve/) |
| 9 | Fix the PyPI attestation verification example to use the canonical repository case (zhangtaolab/SIF) | 2026-11-19 | 0cdd69d | — |
| 261122-leb | Add a machine-to-machine migration runbook: verified index export/restore, embedding and model caches, embedder identity, source paths, MCP/watch recreation | 2026-11-22 | 6b40903 | [261122-leb-write-a-machine-to-machine-migration-gui](./quick/261122-leb-write-a-machine-to-machine-migration-gui/) |

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

Last session: 2026-11-18T07:14:41.672Z
Stopped at: Phase 24 complete — all phases complete
Resume file: (none; the Phase 24 .continue-here.md remains as the last handoff)

- **Next expected action:** Phase 17's gap is closed and verified as of 2026-11-25: plan 17-10 restored the 8-cell, every-branch CI matrix (reversing quick task 261118-lmm), verification reads `passed` (59/60 truths at `5608576`, canonicalized at `0441ad7` after Test Matrix run `45522236981` ran green), and its UAT is complete. Phase 24's verification was refreshed on 2026-11-24 (`e64c52c`) and re-verified on 2026-11-25 (`10691bd`, 43/43 truths) after plan 17-10 changed `tests/test_ci_workflows.py`; v1.2 itself was already shipped and archived on 2026-11-18. Phase 18 was re-verified on 2026-11-25 (`2f4fff8`, 44/44 truths). Phase 19 was re-verified on 2026-11-26 (`d12fc6e`) after its gap closure ran: plans `19-10`, `19-11` and `19-12` executed between `4e258cf` and `d5382ae` (the operator answered the 19-11 `--min-score` checkpoint with `monotone-map`; the orchestrator performed and approved the plans' three human checks on isolated indexes), and the phase reads `human_needed` (85/90 truths, none failed; truths 17 and 34 uncertain). Phase 19's UAT was completed on 2026-11-26 by the orchestrator as tester at the operator's request (`f5ece6b`): ten tests, seven passed (1 to 7) and three failed, each diagnosed in `19-UAT.md`. G-19-8: with `--min-score` equal to a row's own displayed score that row is dropped in about half of the cases (40 of 84 bench rows). G-19-9: `sif query --min-score` filters each leg on its own scale and never the displayed score. G-19-10: three behaviours with no test that fails without them. All three are planned as of 2026-11-26 and committed at `c3d2db7`: `19-13` replaces the `-M/(1-M)` bound by a comparison of the mapped score so that a row whose displayed score equals `--min-score` is kept (it removes `bm25_rank_threshold` and amends the fourth truth of `19-05-PLAN.md` once more); `19-14` makes the help texts of `query` and `vsearch`, the generated CLI reference, the MCP doc page and the changelog describe what `query --min-score` does, with no change of behaviour; `19-15` adds the three tests. They pass the plan checker (round 2: 0 blockers, 0 warnings, 7 advisories) and are committed, which their phase-directory gate requires. Next: the operator confirms assumption `A-19-9-1` (`sif query --min-score` keeps its per-leg behaviour and its text describes it), then `/gsd-execute-phase 19 --gaps-only`. Adding a description to the MCP wire schema is out of scope and stays a Phase 22 follow-up. The verification report reads `stale` since the plans landed and is re-verified after they run; it flips to `passed` only once the UAT holds no unresolved issue, and UAT test 9 must then be restated to the per-leg contract, as its note in `19-UAT.md` says. Phases 17, 18 and 24 read `stale` again since the gap-closure round. Phases 20-23 still carry `stale` verification after the post-ship quick tasks — `/gsd-execute-phase <N>` routes each to the verifier re-run gate. Platform evidence at `256380e`: macOS 3,233 passed / 1 skipped / 95.03%; Linux 3,232 passed / 2 skipped / 95.04% with ruff/format/ty green; Windows smoke 8/8 plus 346 changed-area and 124 affected-module tests. Two audits remain recorded as debt (see Blockers/Concerns): `/gsd-secure-phase 20` and `/gsd:validate-phase 20`.

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
