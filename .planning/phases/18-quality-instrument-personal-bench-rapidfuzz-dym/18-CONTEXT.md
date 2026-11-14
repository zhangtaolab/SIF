# Phase 18: Quality Instrument (Personal Bench + rapidfuzz DYM) - Context

**Gathered:** 2026-11-14
**Status:** Ready for planning

<domain>
## Phase Boundary

The milestone's measurement phase — make search quality measurable on the user's OWN corpus with trustworthy bias controls, and make did-you-mean faster and higher-recall. Delivers exactly EVAL-01, EVAL-02, QUAL-01:

1. **Personal bench (EVAL-01)** — `sif eval --personal` synthesizes known-item queries from the user's indexed corpus (no manual labeling), reusing the legacy fixture schema + `SearchEvaluator`, plus a query_log replay leg.
2. **Trustworthy bias controls (EVAL-02)** — paraphrase overlap budget, per-leg × per-language × per-category reports, hash-split tuning/held-out separation, paired deltas with a bootstrap noise gate.
3. **rapidfuzz DYM (QUAL-01)** — replace difflib + first-letter bucketing with a full-vocabulary rapidfuzz Indel scorer; re-measure the cutoff on the 0–100 scale; preserve the tie-break and probe contracts; stay within the ≤10 ms core budget.

NOT in scope: ranking-behavior changes (Phase 19), metadata filters (20), embedder identity (21), MCP/Registry work (22), Harrier evaluation (23), chunking/title-breadcrumb sweeps (24), LLM-assisted query synthesis or grading, match-time fuzzy retrieval, spellfix1/symspellpy fallbacks.

</domain>

<decisions>
## Implementation Decisions

### Personal query synthesis (EVAL-01)
- **D-01:** **Three query legs by default** — title/H1, body snippet, and query_log replay. Title/body legs are known-item synthesis; replay is a separate leg with its own semantics. — **Reversibility:** reversible — leg composition is a report/query-set change.
- **D-02:** **query_log replay measures stability/regression, not absolute quality** — replay each logged query and compare its top-k against a baseline snapshot (rank overlap/consistency). No pseudo-relevance labels; the CLI-only replay bias (MCP queries are not logged, Phase 15 D-08) is documented in the report. — **Reversibility:** costly — the replay leg's meaning is a stored-run comparison contract.
- **D-03:** **Deterministic hash sampling with caps** — sample documents by content hash: minimum 50 queries, maximum 500, proportional to corpus size; the same corpus yields the same query set across runs. — **Reversibility:** reversible.
- **D-04:** **Known-item labels reuse the legacy binary fixture schema** — the target document is grade 1, all other documents grade 0; no synthetic graded labels. nDCG@10 therefore behaves as a rank-sensitive known-item metric and the report says so. — **Reversibility:** reversible — label semantics are documented with the run.

### Bias controls and reporting (EVAL-02)
- **D-05:** **Paraphrase overlap budget = token Jaccard ≤ 0.60** — measure between the query and the target document's title plus opening text; reject queries over budget, and report the rejection count and the per-leg budget. — **Reversibility:** costly — changing the budget changes the query set, so saved runs are not directly comparable across a threshold change.
- **D-06:** **Hash split = 50/50 tuning/held-out, held-out ≥ 25** — split by query-text hash so it is stable across runs; if the held-out pool would fall below 25, widen sampling rather than shrink the gate. — **Reversibility:** costly — the split defines which runs can support a defaults decision.
- **D-07:** **Noise gate = paired bootstrap 95% CI + mean Δ ≥ 0.01** — compute per-query paired deltas between two arms, bootstrap the mean delta, and declare a winner only when the CI excludes 0 and the mean delta reaches the 0.01 tie rule. Report the 1/N per-query noise floor and each group's N. — **Reversibility:** reversible — analysis method.
- **D-08:** **Full-dimensional report with small-group suppression** — report per leg × per language × per category; suppress groups with fewer than 10 queries and list the suppressed group names so an empty cell is never mistaken for a zero. — **Reversibility:** reversible.

### `sif eval` command and data (EVAL-01)
- **D-09:** **New `sif eval` command group with `--personal`** — `sif bench` stays the committed synthetic-fixture instrument; `sif eval --personal` is the personal-corpus entry point, matching the roadmap's literal command. — **Reversibility:** costly — a public CLI surface is a compatibility commitment once shipped.
- **D-10:** **Auto-save the synthesized query set to the cache directory** — write query/path/split/leg/language/grade only (never document content) under `~/.cache/sif/eval/`; `--no-save` opts out. Saved runs are the comparison substrate. — **Reversibility:** reversible.
- **D-11:** **Thresholds and retrieval mode** — require at least 50 indexed documents and 50 synthesized queries; default to hybrid retrieval (the embed extra). If the embed extra is unavailable, fail with a `pip install docsif[embed]` remedy hint; `--bm25-only` is the explicit degradation path. — **Reversibility:** reversible.
- **D-12:** **Comparison entry point = `--compare <saved-run.json>`** — load a prior run, validate that its corpus fingerprint matches, and report paired deltas + bootstrap CI; every run auto-saves. A mismatched corpus refuses the comparison with a clear message. — **Reversibility:** reversible — the saved-run format can evolve with a version field.
- **D-13:** **`rapidfuzz>=3.14.5,<4` is a hard runtime dependency; no difflib fallback** — a missing import is a broken install and raises a clear error. This is the v1.2-locked second dependency. — **Reversibility:** reversible — code can return to difflib, but the packaging change is already locked for v1.2.

### rapidfuzz DYM (QUAL-01)
- **D-14:** **Full-vocabulary `rapidfuzz.fuzz.ratio` (Indel 0–100), no first-letter bucket** — replace `difflib.get_close_matches` over the ±1-letter bucket; start at cutoff 75 and re-measure on the bench vocabulary, pinning the chosen cutoff with the ≤10 ms core-function budget. — **Reversibility:** reversible.
- **D-15:** **Deterministic tie-break = score desc → term lexicographic asc → document frequency desc** — preserves the current difflib sorted-term determinism while keeping high-frequency terms competitive. — **Reversibility:** reversible.
- **D-16:** **Cutoff is an internal constant, not a setting or CLI flag** — the bench evidence pins it; tests guard both the constant and the behavior. No new user-facing knob. — **Reversibility:** reversible — exposing it later is additive.
- **D-17:** **Preserve the probe/hit contracts and untouched sections** — every emitted suggestion must still return ≥1 hit; `_probe` stays fail-soft; prefix completions and history ranking are unchanged. The 100 ms `sif suggest` budget remains the end-to-end guard. — **Reversibility:** reversible.

### Claude's Discretion
- Personal-eval **category axis**: query-length buckets (`short` ≤2 tokens, `medium` 3–5, `long` ≥6), orthogonal to leg and language; revisit if research finds a better axis.
- Language classification: CJK codepoint ratio (`en` / `zh` / `mixed`), with the exact threshold pinned by tests.
- Saved-run JSON schema and version field; the corpus fingerprint algorithm (content hash over paths + sizes/checksums).
- Replay baseline snapshot shape (top-k document paths + ranks) and how “no baseline” is reported.
- Hybrid-default embedder selection (configured model or `ConceptEmbedder` in tests), and the exact `--bm25-only` report flag.
- rapidfuzz scorer call shape (`process.extract` vs `cdist`), early-exit strategy for very large vocabularies, and the measured cutoff within the 70–80 range.
- Exact `sif eval --personal` table columns and JSON field names, following the `bench` output conventions.
- Whether `sif eval` also exposes a fixture mode for the committed synthetic corpus (alias) or stays personal-only in this phase.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — EVAL-01, EVAL-02, QUAL-01; Out of Scope (match-time fuzzy, silent rewrites, LLM-in-DYM, spellfix1/symspellpy, LLM-assisted tuning)
- `.planning/ROADMAP.md` §Phase 18 — goal + three success criteria; §Phase 19/23/24 — consumers of the instrument
- `.planning/PROJECT.md` §Key Decisions — v1.2 scope, exactly two new runtime deps, Harrier held-out gate

### Prior phase decisions (carry forward, do not re-litigate)
- `.planning/milestones/v1.1-phases/15-search-quality-configuration-hybrid-weights-query-suggestions/15-CONTEXT.md` — DYM D-05..D-14 (zero-result trigger, FTS5 vocab source, full-query rewrite, query_log D-08..D-10, 100 ms budget), probe contract
- `.planning/milestones/v1.1-phases/16-bench-expansion-reranker-tuning/16-CONTEXT.md` — bench fixture D-01..D-09 (graded 0–3, fixed splits, nDCG/Hit/latency, 0.01 tie rule), D-13 SearchEvaluator extension
- `.planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-CONTEXT.md` — CI matrix D-01..D-04, deterministic test environment, zero-new-deps exception for this milestone

### Milestone research
- `.planning/research/SUMMARY.md` — v1.2 recommended scope; Phase 18 positioning
- `.planning/research/STACK.md` — rapidfuzz selection/version; existing bench stack
- `.planning/research/PITFALLS.md` — held-out overfitting, paraphrase leakage, small-N noise

### Code and data surfaces (verified this session)
- `src/sif/search/benchmark.py` — `SearchEvaluator`, `CATEGORIES`, `SPLITS`, `LEGACY_K_VALUES`, fixture loading, metrics, sweep ranking
- `src/sif/cli/commands/bench.py` — `sif bench` table/JSON output, sweep, rerank states
- `src/sif/search/suggest.py` — `SuggestionEngine`, `_close_matches` first-letter bucket + difflib cutoff 0.75, `_probe`/`_hits`
- `src/sif/cli/commands/suggest.py` — `sif suggest` three-section output
- `src/sif/database/repositories.py` — `QueryLogRepository.history()` (query, count, last_used)
- `src/sif/database/schema.py` — `query_log` table (query, result_count, collections, created_at)
- `src/sif/config/settings.py` — settings/cache-dir helpers and query-history settings
- `CLAUDE.md` — quality gates (ruff/format/ty/pytest 90%), generator-owned docs, error culture

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SearchEvaluator` (`src/sif/search/benchmark.py:410`) — fixture-driven evaluator; extend with personal query legs and paired deltas rather than rewriting metrics.
- Fixture schema — legacy `{"queries": [...]}` (docid-keyed, binary) and graded path-keyed 0–3 fixtures both load; personal known-item legs reuse the legacy shape.
- `sif bench` table + `--json` rendering — the output convention `sif eval` should follow; per-category breakdown already exists.
- `QueryLogRepository.history()` — one GROUP BY returning `(query, count, last_used)`; the replay leg's source.
- `SuggestionEngine._probe` / `_hits` — the existing guarantees that every suggestion returns ≥1 hit; keep them in the rapidfuzz path.
- `Settings.get_cache_dir()` — cache-dir resolution for saved personal runs.

### Established Patterns
- Deterministic tests: `tmp_path` batteries, `ConceptEmbedder` for hermetic embeddings, no wall-clock races; latency asserts on core functions with generous headroom.
- Table + `--json` for measurement commands; soft-fail warnings on stderr, never corrupting stdout.
- Generator-owned docs (`docs/cli-reference.md`, `docs/configuration.md`) — new settings/flags must flow through `scripts/generate_config_ref.py` + `make docs-generate`.
- No new runtime deps beyond the v1.2-locked pair; rapidfuzz is the one this phase adds.

### Integration Points
- New `src/sif/cli/commands/eval.py` (or `eval/` module) + registration in `src/sif/cli/main.py`
- New personal-bench module (e.g., `src/sif/search/personal_bench.py`) consuming `SearchEvaluator` + `QueryLogRepository`
- `src/sif/search/suggest.py` — replace `_close_matches` internals; keep `_probe`/`_hits`
- `pyproject.toml` + `uv.lock` — `rapidfuzz>=3.14.5,<4`
- `docs/` — CLI reference (generator), search-algorithms/testing narrative updates
- Tests: `tests/unit/search/`, `tests/unit/cli/`, `tests/e2e/` following existing patterns

</code_context>

<specifics>
## Specific Ideas

- **Noise floor math:** one query contributes roughly 1/N to mean nDCG; at N≈71 that is the roadmap's ~0.014. The report must print N and the implied floor so a 0.01 "win" on a 50-query corpus is visibly below noise.
- **Replay honesty:** query_log has no clicks. The replay leg's report says "stability vs baseline", never "quality", and lists the CLI-only bias (MCP queries are not logged).
- **Overlap rejection is visible:** the report shows how many synthesized queries were rejected per leg; a silent shrunk query set would make the instrument look cleaner than it is.
- **≤10 ms is a core-function budget**, measured like Phase 15's 100 ms: CLI cold start excluded; test the `SuggestionEngine` call directly with generous headroom.
- **Cutoff evidence:** record the measured recall/precision trade-off at 70/75/80 on the bench vocabulary; the chosen constant and the measurement live together in the SUMMARY.
- **Comparison guard:** `--compare` refuses a different corpus fingerprint; a silently compared different corpus would manufacture a delta.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 18-Quality Instrument (Personal Bench + rapidfuzz DYM)*
*Context gathered: 2026-11-14*
