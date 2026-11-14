---
phase: "18"
slug: "quality-instrument-personal-bench-rapidfuzz-dym"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-14"
verified: "2026-11-14"
---

# Phase 18 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verified by /gsd-secure-phase 18 on 2026-11-14 at HEAD `e7eebb0` (ASVS L1, block_on high).
> Register authored at plan time: all four PLANs carry STRIDE `<threat_model>` blocks. L1
> grep-depth verification confirmed every mitigation present; `threats_open: 0`.

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

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-14 — 16/16 threats closed at L1; 0 open at or above `high`.
