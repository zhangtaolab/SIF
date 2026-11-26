---
phase: "18"
slug: "quality-instrument-personal-bench-rapidfuzz-dym"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-14"
verified: "2026-11-25"
---

# Phase 18 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verified by /gsd-secure-phase 18 on 2026-11-14 at HEAD `e7eebb0` (ASVS L1, block_on high).
> Register authored at plan time: all four PLANs carry STRIDE `<threat_model>` blocks. L1
> grep-depth verification confirmed every mitigation present; `threats_open: 0`.
>
> Re-verified by /gsd-secure-phase 18 on 2026-11-25 at HEAD `9927d41` (ASVS L1, block_on high,
> orchestrator L1 short-circuit, no auditor spawn) against the tree after the v1.2 archive commit
> `b817ebb`. All 16 register rows were re-verified at HEAD, weighted toward `T-18-11` and
> `T-18-SC`, the rows whose mitigations cite `pyproject.toml` / `uv.lock`. No citation broke and
> no mitigation regressed; the delta invalidates nothing. `threats_open: 0`. Detail: the
> 2026-11-25 re-audit notes below.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Personal corpus DB → eval synthesis | Metadata scan of the whole corpus; document bodies only for the sampled subset | Titles, paths, checksums, sampled content |
| Eval report → Rich table / JSON | Query/path-derived text rendered as terminal cells or machine JSON | Query text, paths, group names |
| Saved-run file → `--compare` | Untrusted JSON read from the user cache dir | Versioned envelope, per-query records |
| Saved paths → filesystem | Saved paths are inspection values and a unique-match fallback; never opened | Path strings |
| Current DB → comparison | A different corpus behind the same fingerprint would manufacture deltas | Corpus fingerprint, document ids |
| Config → embedder provider | A remote-capable provider can receive synthesized query text | Query text, embeddings |
| PyPI → build | The phase's only new package enters through the lock | rapidfuzz wheels |
| FTS vocabulary → suggestions | Vocab terms and query text become terminal cells | Terms, rewritten queries |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-18-01 | Spoofing | `eval.py` table cells | medium | mitigate | Truncate then `rich.markup.escape()` every title/path-derived cell; tests assert bracket text renders literally. | closed |
| T-18-02 | Denial of Service | `load_document_metadata` / synthesis | medium | mitigate | Whole-corpus pass selects metadata columns only (`include_content=False`), iterates the cursor, never `fetchall()`s the corpus; bodies load only for the bounded sample (≤250 docs); query candidates capped at 500. | closed |
| T-18-03 | Tampering | collection scope resolution | low | mitigate | `CollectionRepository.get_by_name` / parameterized SQL only; never interpolates collection names into SQL. | closed |
| T-18-04 | Information Disclosure | replay/report serialization | high | mitigate | Saved runs store title-leg query text and a short normalized body excerpt (never full bodies, snippets, or embeddings); `_SAVED_FORBIDDEN_KEYS` rejects content/snippet keys; docs and tests state the excerpt explicitly. | closed |
| T-18-05 | Denial of Service | body synthesis / Jaccard / grouping | medium | mitigate | Body candidates capped at 10 tokens, replay at 500, synthesized queries at 500; Jaccard on token sets in one pass; content loaded only for the sampled subset. | closed |
| T-18-06 | Spoofing | group names / query cells in Rich output | medium | mitigate | Truncate then `rich.markup.escape()` every query/path-derived cell; group names built from fixed enums, not user text. | closed |
| T-18-07 | Tampering / Denial of Service | `load_saved_run` / `validate_saved_run` | high | mitigate | `MAX_SAVED_FILE_BYTES = 5 MB`, `MAX_SAVED_RECORDS = 10_000`, `version == 1`; envelope and every record type/range/enum-checked with `.get`/`isinstance`; non-finite floats and bool-as-int rejected; all defects → `ValueError` → `ClickException` naming the field path. | closed |
| T-18-08 | Information Disclosure | saved `target_path`/`retrieved` paths | medium | mitigate | Paths are inspection values and a unique-match fallback, never grading keys; grading uses saved `retrieved_doc_ids` against `target_doc_id`; target paths resolve with a parameterized `documents` lookup only; saved paths are never `open()`-ed; no content stored. | closed |
| T-18-09 | Spoofing / Integrity | corpus fingerprint match | high | mitigate | The fingerprint is recomputed from the current DB; a mismatch refuses the comparison and names both values; the saved fingerprint is never trusted as the current one. | closed |
| T-18-10 | Repudiation / Transparency | noise gate | high | mitigate | A winner requires a bootstrap CI excluding zero AND a rounded mean delta ≥ 0.01; the report includes N, 1/N, and helped/hurt/unchanged; held-out alone can warrant a change. | closed |
| T-18-11 | Tampering | `pyproject.toml` / `uv.lock` / install | high | mitigate | Blocking human package-legitimacy checkpoint (18-04 Task 1, approved 2026-11-14); locked range `>=3.14.5,<4`; `uv lock --check`; CI installs with `uv sync --frozen`. | closed |
| T-18-12 | Denial of Service | full-vocabulary `process.extract` | medium | mitigate | `score_cutoff=75.0` bounds candidates; measured p50 1.513 ms/query at 73,040 terms vs ~5.9 ms for the old bucket; the budget test asserts a generous CI ceiling and the SUMMARY records p50/p95. | closed |
| T-18-13 | Tampering / Integrity | emitted suggestions | high | mitigate | Every variant still flows through `_hits`/`_probe` (≥1 document); `_probe` remains fail-soft; SC2 tests stay in place. | closed |
| T-18-14 | Spoofing | suggestion output / CLI table | low | mitigate | Existing `_cell` truncate-then-escape convention in `sif suggest`; no new output surface. | closed |
| T-18-15 | Information Disclosure | configured embedder provider | medium | mitigate | The provider is named in the report; for `openai`/`modelscope` types a stderr disclosure states document titles, body-sentence excerpts, and replay query history reach that provider and names `--bm25-only` as the local path; eval-owned code never uploads or serializes personal data. | closed |
| T-18-SC | Tampering | dependency installs | high | mitigate | The phase's only new package is rapidfuzz, gated by the 18-04 blocking human checkpoint and the lock verification; every other plan installs nothing. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `workflow.security_block_on` count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-14 | 16 | 16 | 0 | Claude (gsd-secure-phase, ASVS L1, block_on high) |
| 2026-11-15 | 16 | 16 | 0 | Claude (post-fix reconciliation: CR-01/WR-01..WR-10 fixed) |
| 2026-11-25 | 16 | 16 | 0 | ZCode (gsd-secure-phase, ASVS L1 short-circuit — all 16 rows re-verified at HEAD `9927d41`; no register change) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-14 — 16/16 threats closed at L1; 0 open at or above `high`.

**Re-verification:** verified 2026-11-25 — 16/16 threats closed at L1; 0 open at or above `high` (all rows re-verified at HEAD `9927d41`; no register change).

## Security Audit 2026-11-18

| Metric | Count |
|---|---|
| Threats found | 0 |
| Closed | 0 |
| Open | 0 |

## Security Audit 2026-11-25

| Metric | Count |
|---|---|
| Threats found | 16 |
| Closed | 16 |
| Open | 0 |

### Re-audit notes (2026-11-25, HEAD `9927d41`)

- **Scope.** State A re-audit of the existing register against the tree after `b817ebb`, the
  last commit that touched this file. Depth L1, `block_on: high`, ASVS level 1. The register is
  authored at plan time (all four PLANs carry STRIDE `<threat_model>` blocks) and
  `threats_open` was 0, so the workflow short-circuit applied: Steps 4 and 5 were skipped and
  `gsd-security-auditor` was not spawned. The orchestrator classified every row, and all 16 were
  read at HEAD rather than only the delta rows. The four SUMMARY files carry
  `## Threat Surface Scan` sections (there is no `## Threat Flags` heading); each reports no new
  security-relevant surface, so there are no unregistered flags.
- **Delta outside `.planning/`, `b817ebb..HEAD`: 58 files.** Of the files behind this register,
  exactly two changed, both cited by `T-18-11` (`T-18-SC` cites the same lock):
  - `pyproject.toml`: only the two torch extras floors, `"torch"` to `"torch>=2.11"` (`embed`,
    `all`). Two commits produced this: `a13b134c` raised the floor to `>=2.14`, then `848e6b6a`
    lowered it to `>=2.11`. `rapidfuzz>=3.14.5,<4` at `pyproject.toml:41` is untouched.
  - `uv.lock`: 23 lines removed, 23 added. Four are torch `requires-dist` entries gaining
    `specifier = ">=2.11"`; the other 19 are `resolution-markers` strings reordered inside ten
    package blocks, the same strings on both sides. No line touching an sdist, wheel, URL, hash,
    version or source changed, and the package set is the same 106 with an identical
    name@version multiset. The rapidfuzz 3.14.5 / 3.14.6 split is unchanged (`uv.lock:1741`,
    `uv.lock:1835`); both blocks are identical modulo that marker reordering.
  - `uv lock --check` exits 0 at HEAD (uv 0.9.8). `.github/` is byte-identical to `b817ebb` and
    to `e7eebb0`, so `uv sync --frozen` is still the test-matrix install
    (`.github/workflows/test-matrix.yml:41`, `:65`).
  - `docs/installation.md`, the "install" part of the `T-18-11` component, gained torch backend
    recipes on the official `download.pytorch.org` index and the `torch>=2.11` extras row.
    Nothing in it changes how rapidfuzz is resolved or installed.
  - **`T-18-11` and `T-18-SC` hold.** A floor raise on an already-locked optional dependency adds
    no package, version, source or index. The package-legitimacy gate is therefore not
    re-triggered and "the phase's only new package is rapidfuzz" stays true. The torch floor is
    itself a registered threat under Phase 17 (`T-17-06`, closed).
- **Rows behind other changed files.**
  - `T-18-15` (embedder provider boundary): `src/sif/embedding/embedder.py`, `factory.py` and
    `manager.py` changed and `normalize.py` was added, but the delta is device auto-selection
    (CUDA, XPU, MPS, CPU), cache-dir plumbing and float64 L2 renormalization. `ModelType` gained
    no member and `huggingface` is still unimplemented (`src/sif/embedding/factory.py:98`), so
    the `_REMOTE_MODEL_TYPES = {"openai", "modelscope"}` condition
    (`src/sif/cli/commands/eval.py:82`) still covers every remote-capable type. `eval.py` is
    byte-identical to `b817ebb`.
  - Docs gate, cited by no mitigation cell: `scripts/generate_config_ref.py` and
    `tests/test_docs.py` changed. Both generators exit 0 on a clean `HEAD` extract, and
    `docs/cli-reference.md` and `docs/configuration.md` come out byte-identical to the tracked
    files.
- **A second window, outside the brief's delta but inside this register's.** The last
  substantive reconciliation of this file is `58ab80dc` (2026-11-15). Between it and `b817ebb`,
  six later-phase commits (`f3bc9e7e`, `c9386e78`, `cf6e0bed`, `2c948aec`, `ef50fcef`,
  `618997c1`) moved `src/sif/cli/commands/eval.py` (+179/-11) and
  `src/sif/search/personal_bench.py` (+272/-18). The rows citing those files were therefore
  re-read at HEAD instead of carried forward:
  - `T-18-02`: held-out widening (Phase 18, extended by Phase 23) still runs under
    `cap=MAX_SAMPLE_DOCUMENTS` (`personal_bench.py:1123`, `:1154`), so bodies still load for at
    most 250 documents, and `load_document_metadata` still selects metadata columns only (`:803`).
  - `T-18-10`: the winner rule is stricter than the cell states, not weaker. `618997c1` added
    `strictly_above_noise_floor` (`:609-617`) and a winner must now also be strictly above the
    displayed 1/N floor (`:1951`, `:1963`). `warrants_default_change` is still the held-out
    summary gate alone (`:2396-2397`).
  - `T-18-01`, `T-18-06`: the `--require-language` and `--min-heldout` compare warnings print
    only `click.Choice`-bounded language names and an integer.
  - `src/sif/search/suggest.py`, `src/sif/search/benchmark.py`,
    `src/sif/cli/commands/suggest.py` and both suggest test files are untouched since `58ab80dc`,
    so `T-18-12`, `T-18-13` and `T-18-14` rest on unchanged code.
- **Result.** 16/16 closed, 0 open, 0 open below the `high` threshold. No row changed status or
  ID and no row was added. No mitigation cell carries a line reference, so there was none to
  refresh. No accepted risk was added.
- **Evidence.** `pytest` from PATH (miniconda 3.13.9, rapidfuzz 3.14.6), 302 passed and 0
  failed: `tests/unit/cli/test_eval.py` 75, `tests/unit/search/test_personal_bench.py` 159,
  `tests/unit/search/test_suggest.py` 32, `tests/unit/cli/test_suggest.py` 15,
  `tests/test_docs.py` 21. That includes the pins `test_every_suggestion_hits_as_query`,
  `test_full_vocab_dym_under_budget_on_60k_vocab`,
  `test_load_rejects_an_oversized_file_before_decoding` and
  `test_fingerprint_mismatch_refuses_and_names_both_values`. GitHub Actions Test Matrix run
  `45522236981` on `a25eb07` is green on 8/8 cells plus lint, and `a25eb07..HEAD` differs only
  under `.planning/` (8 files). The lint job's `ty check` is not counted as evidence: that job
  syncs only `--extra dev`, so `transformers` and `torch` are absent and
  `import-not-found = "ignore"` (`pyproject.toml:219`) hides the gap.
- **Recorded, not re-triaged.** Two observations. Neither is introduced by this delta and
  neither changes a row.
  - The `## Security Audit 2026-11-18` block above reads 0 / 0 / 0, which does not describe this
    16-row register. It is left byte-identical as history; the 16 / 16 / 0 block is the count of
    record.
  - "CI installs with `uv sync --frozen`" (`T-18-11`) is true of the test matrix.
    `.github/workflows/docs.yml:33` (Docs Validation: `pull_request` on docs paths, `push` to
    `main`, `permissions: contents: read`) installs with `pip install -e ".[dev]"`, which does
    not consume the lock. That workflow is byte-identical back to `e7eebb0`, the HEAD of the
    original audit, so it predates every entry here. It is CI install surface, which belongs to
    the Phase 17 register rather than this one.
