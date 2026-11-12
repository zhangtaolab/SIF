---
phase: 15-search-quality-configuration-hybrid-weights-query-suggestions
reviewed: 2026-11-08T11:02:12Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - .claude/skills/sif-search/SKILL.md
  - docs/cli-reference.md
  - docs/configuration.md
  - scripts/generate_config_ref.py
  - src/sif/cli/commands/search.py
  - src/sif/cli/commands/suggest.py
  - src/sif/cli/main.py
  - src/sif/config/settings.py
  - src/sif/core/models.py
  - src/sif/database/repositories.py
  - src/sif/database/schema.py
  - src/sif/mcp/backend.py
  - src/sif/mcp/handlers.py
  - src/sif/mcp/protocol.py
  - src/sif/search/hybrid.py
  - src/sif/search/rrf.py
  - src/sif/search/suggest.py
  - tests/test_docs.py
  - tests/unit/cli/test_search.py
  - tests/unit/cli/test_suggest.py
  - tests/unit/config/test_settings.py
  - tests/unit/database/test_query_log_repo.py
  - tests/unit/database/test_schema.py
  - tests/unit/mcp/test_backend.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/search/test_rrf.py
  - tests/unit/search/test_suggest.py
findings:
  critical: 1
  warning: 5
  info: 7
  total: 13
  necessity: 0
status: issues_found
---

# Phase 15: Code Review Report

**Reviewed:** 2026-11-08T11:02:12Z
**Depth:** standard
**Files Reviewed:** 26
**Status:** issues_found

## Summary

Reviewed the Phase 15 implementation: weighted (multiply-form) RRF with byte-identical
defaults, MCP/CLI/settings plumbing for `rrf_k`/`bm25_weight`/`vector_weight`, the
`documents_fts_v` fts5vocab shadow, the `SuggestionEngine` (prefix / DYM / history), the
`query_log` repository and trim-in-write cap, zero-result DYM hooks on all three CLI search
commands plus MCP, and the new `sif suggest` command.

The weighted-fusion math is correct and the SC1 byte-identical default was verified by the
golden tests (`weight=1.0` is IEEE-exact; per-call `k` falls back to the instance `k`).
Schema/repository code is parameterized and safe, markup/JSON/XML output is escaped, MCP
suggestion remapping is explicit, and fail-soft postures are consistently applied. The full
local suite passes (1333 passed, 1 skipped), `ruff`/`ty` are clean.

One acceptance criterion is nevertheless broken: the phase's **SC2 bar — "every emitted DYM
suggestion returns ≥1 hit"** — does not hold for multi-word queries, because suggestions are
built token-by-token and never validated as an AND conjunction against the index. A second
engine defect (`_retrievable`'s prefix-substring test) both suppresses legitimate corrections
and spuriously "corrects" valid inflected words. Remaining findings are a documented-flag
mismatch, documentation drift left behind when `RRFFusion.fuse_with_weights` was deleted, and
small quality gaps.

The known pre-existing WR-02 (`vsearch`/`query` crash without sqlite-vec) is **not widened**
by this phase: `VectorSearcher`/`SearchPipeline` construction placement is unchanged, and the
new `sif suggest` path uses FTS only. The accepted UAT trade-offs (porter-stem display,
index-global suggestions under collection filters) were not treated as findings.

No necessity findings: the `_ensure_vocab` re-create guards a genuinely reachable upgrade
state (an MCP connection opened against a pre-Phase-15 DB before any CLI command has run
`create_all`), and the fail-soft handlers guard real failure modes.

## Critical Issues

### CR-01: DYM suggestions are never validated as a conjunction — emitted suggestions can return zero hits (SC2 violated)

**File:** `src/sif/search/suggest.py:111-166` (also `tests/unit/search/test_suggest.py:170-179`)
**Issue:** `did_you_mean()` builds each variant by substituting per-token close matches but never
checks the rewritten query against the index. Each substituted term is guaranteed to exist
*somewhere*, but the suggestion is an AND of quoted-prefix phrases (`BM25Searcher._build_fts_query`),
so the terms can live in different documents and the suggestion retrieves nothing. This
directly violates the phase's stated acceptance bar (QUAL-02 / SC2: "every emitted suggestion,
run as a real BM25 query, returns ≥ 1 result"), which is pinned by a test that only uses a
fixture where all replacement terms happen to co-occur.

Verified against the production engine/searcher (real schema, real FTS triggers):

```
corpus: d1="alpha", d2="beta"
query: "alphx beta"          -> 0 hits (expected)
did_you_mean(...)            -> ["alpha beta"]
BM25Searcher.search("alpha beta") -> 0 hits   # SC2 violation
```

`"beta"` is kept here because it individually retrieves; the conjunction is what fails. Any
query whose suggested terms do not co-occur in one document reproduces this (e.g. a typo in
one topic word plus a valid word from another topic).

**Fix:** validate each generated variant against `documents_fts` before returning it, and drop
variants with no hits (return `[]` when none survive). Reuse the searcher's sanitizer so the
probe is identical to what will actually run:

```python
from sif.search.bm25 import _build_fts_query  # or _sanitize_term per token

def _hits(self, variant: str) -> bool:
    row = self.db.execute(
        "SELECT 1 FROM documents_fts WHERE documents_fts MATCH ? LIMIT 1",
        (_build_fts_query(variant),),
    ).fetchone()
    return row is not None

# in did_you_mean(), after _expand_variants:
return [v for v in self._expand_variants(slots, n) if self._hits(v)]
```

Then strengthen the SC2 pin: use a corpus where the correctable token and the kept token live
in **different** documents (the current `machien quantom` fixture is co-occurring and cannot
catch this class of bug).

## Warnings

### WR-01: `_retrievable` prefix-substring test is unsound — suppresses real corrections and invents spurious ones

**File:** `src/sif/search/suggest.py:209-222` (line 222)
**Issue:** The "in-vocab" predicate accepts a token if **any prefix of any length** of it is a
vocab term. That is not equivalent to "the searcher would match this token": FTS matches the
porter-stemmed token as a prefix, and the implementation never stems. Two demonstrated
consequences:

1. **Legitimate corrections suppressed.** Corpus with the word `rest` and `restaurant`
   (stems `rest`, `restaur`): `did_you_mean("resturant")` returns `[]`, because
   `"resturant".startswith("rest")`. `BM25Searcher.search("resturant")` returns 0 rows, so the
   user gets no help. Any typo beginning with a common short stem (`a`, `i`, `is`, `in`, `re`,
   `rest`, ...) is silently deemed retrievable.
2. **Valid words spuriously "corrected."** Corpus `happy day` + `doggy bone`: vocab stems are
   `happi`, `dai`, `doggi`, `bone`. `"happy"` is judged *not* retrievable (its Porter stem is
   `happi`), so `did_you_mean("happy dog")` returns `["happi dog"]` — rewriting a word that
   actually matches the index (and, per CR-01, the rewrite itself returns 0 hits).

The research note flags exactly this risk ("a too-loose prefix test suppresses legitimate
corrections"), so the current branch is the known-bad side of the trade-off.

**Fix:** make the predicate match the way the searcher matches. Cheapest correct option is the
same FTS probe used for CR-01:

```python
def _retrievable(self, token: str) -> bool:
    row = self.db.execute(
        "SELECT 1 FROM documents_fts WHERE documents_fts MATCH ? LIMIT 1",
        (f'"{_FTS_METACHARS.sub(" ", token).strip()}"*',),
    ).fetchone()
    return row is not None
```

(or add a Porter stemming pass over the token and compare stems). Add regression tests for
both directions (`resturant` with `rest` in vocab must suggest `restaur`; `happy` must not be
rewritten when `happi` is in vocab).

### WR-02: `sif suggest --limit` does not cap the "Did you mean" section

**File:** `src/sif/cli/commands/suggest.py:99` (help at `:110-116`; cap at `src/sif/search/suggest.py:237`)
**Issue:** `--limit` is documented as "Maximum entries per section" (and the plan says it
"caps each section"), and it is passed to `prefix_completions` and `history_suggestions`, but
the DYM call omits it: `engine.did_you_mean(query)` uses the default `n=3` and
`_close_matches` hardcodes `n=3` again. Verified via the CLI with a synthetic vocab that
yields three close matches: `--limit 1` and `--limit 10` both return the same three DYM
entries. Either the flag is wrong or the help/plan is wrong.

**Fix:** thread the flag through if per-section capping is intended:

```python
did_you_mean = engine.did_you_mean(query, limit)
# and in _close_matches: difflib.get_close_matches(token, bucket, n=n, cutoff=0.75)
```

Otherwise change the help text to state the DYM section is fixed at 3 (and fix the plan
truth), so `--limit` is not silently partial.

### WR-03: Docs still advertise the deleted `RRFFusion.fuse_with_weights` and deny the new knobs

**File:** `docs/api-reference.md:465-476`, `docs/search-algorithms.md:236-247`
**Issue:** This phase deleted `RRFFusion.fuse_with_weights` (`src/sif/search/rrf.py`), but
`docs/api-reference.md` still lists it and shows a stale `fuse()` signature without the new
`weights`/`k` parameters. `docs/search-algorithms.md` says "optional per-source weights via
the Python API (`RRFFusion.fuse_with_weights`)" and "no CLI or environment knob selects
weights: the CLI always fuses with equal weights" — both now false (`--bm25-weight`,
`--vector-weight`, `--rrf-k`, `SIF_BM25_WEIGHT`, `SIF_VECTOR_WEIGHT`, `SIF_RRF_K` exist).

**Fix:** update both to the current API:

```python
def fuse(self, results_lists, limit=10, weights=None, k=None) -> list[SearchResult]: ...
```

and describe the CLI/`SIF_` knobs (multiply form, never normalized).

### WR-04: `docs/mcp-server.md` query tool contract not updated for the new params/response field

**File:** `docs/mcp-server.md:85-120`
**Issue:** The `query` tool's parameter table omits `rrf_k`, `bm25_weight`, `vector_weight`
(all accepted by `QueryInput` and declared in the handler's `input_schema`), and the response
example omits the new `suggestions` array (non-empty on zero-result responses). MCP clients
discovering the tool from this doc cannot know the overrides exist or that the response shape
gained a key.

**Fix:** add the three parameters (types/ranges: `rrf_k` integer ≥ 1, weights number > 0,
omitted = server `SIF_` settings) and add `"suggestions": []` to the response example with a
note that it is populated only on zero results.

### WR-05: `sif suggest --json` writes human text to stdout when the index is missing (and `-q` does not suppress it)

**File:** `src/sif/cli/commands/suggest.py:137-139`
**Issue:** Before collecting anything the command does
`console.print("[yellow]No index found.[/yellow]")` regardless of `--json` and of `quiet`
(the file's own guard test pins this). A machine consumer/agent invoking
`sif suggest "foo" --json` on a fresh install gets `No index found.\n` on stdout and a
`JSONDecodeError`, not the documented three-array JSON. This is the exact consumer pattern the
phase's agent skill relies on for `sif search`.

**Fix:** honour machine output: emit `{"completions": [], "did_you_mean": [], "history": []}`
when `--json` is set (or write the notice to stderr and exit non-zero), and gate the notice on
`not quiet`. Update `tests/unit/cli/test_suggest.py:191-198` accordingly.

## Info

### IN-01: `docs/quickstart.md` jq example assumes `--json` is always an array

**File:** `docs/quickstart.md:355-360` (behavior in `src/sif/cli/commands/search.py:307-320`)
**Issue:** The phase deliberately made zero-result-with-suggestions emit
`{"query","results":[],"suggestions":[...]}` while plain results stay an array. The quickstart
still documents `sif search query "python" --json | jq '.[].path'`, which misbehaves on that
zero-result shape. `SKILL.md` was updated; the human docs were not.
**Fix:** document both shapes in the quickstart (or use `jq 'if type == "array" then .[] else .results[] end'`).

### IN-02: `sif bench` ignores the new global fusion settings

**File:** `src/sif/cli/commands/bench.py:94-99`
**Issue:** `bench` constructs `SearchOptions` without resolving `rrf_k`/`bm25_weight`/
`vector_weight`, so `SIF_RRF_K`/`SIF_BM25_WEIGHT`/`SIF_VECTOR_WEIGHT` do not affect benchmark
runs even though `docs/configuration.md:103-105` describes them as global. This matters for
the Phase 16 weights sweep if it is driven through `sif bench`.
**Fix:** resolve the three fields from the already-loaded `settings` the same way `query_cmd`
does (or document that bench deliberately pins defaults).

### IN-03: Generated config docs omit the new knobs from the `.env` example and Validation Rules

**File:** `docs/configuration.md:138-193`, `scripts/generate_config_ref.py:321-403`
**Issue:** The Search Settings table gained `rrf_k`/weights/history rows, but the "Complete
.env Example" and the "Validation Rules" table were not extended, so the documented `.env`
template lacks the new tuning knobs and the range rules (`rrf_k` ≥ 1, weights > 0,
`query_history_limit` ≥ 1) that now reject invalid config are undocumented.
**Fix:** add the rows to `_append_env_example` and the handwritten range rules in
`_append_validation_rules`, then regenerate.

### IN-04: Dead/duplicated formulas introduced or left beside the changed arithmetic

**File:** `src/sif/search/rrf.py:112-122`, `src/sif/core/models.py:222-230`
**Issue:** `compute_rrf_score()` duplicates the `1/(k+rank)` formula that `fuse()` now applies
with a weight, but is unused anywhere in `src/` or `tests/` — a second source of truth for the
score formula. Likewise `QueryLogEntry.to_dict()` is never called. Both are low-risk but are
unexercised code added/left adjacent to this phase's core math.
**Fix:** either use `compute_rrf_score` inside `fuse` (multiplied/divided consistently) or
delete it; drop `QueryLogEntry.to_dict` unless a consumer is planned.

### IN-05: Prefix completions are effectively dead for multi-word queries

**File:** `src/sif/cli/commands/suggest.py:98`, `src/sif/search/suggest.py:89-109`
**Issue:** `prefix_completions` treats the **entire** QUERY as one prefix, so
`sif suggest "quantum machine learn"` bisects for a term starting with the whole string and
always returns `[]`. Only single-token inputs produce completions, even though the command is
described as typing-aid for partial queries.
**Fix:** complete on the last whitespace-delimited token (and document that completions are
single-token).

### IN-06: `sif suggest` lets DB/config failures escape as tracebacks and prints `--clear-history` confirmation under `-q`

**File:** `src/sif/cli/commands/suggest.py:63-71`, `:93-105`
**Issue:** `db.init_schema()` and `_clear_history()` are outside any `try`, so a locked/corrupt
DB or an invalid unrelated `SIF_` setting surfaces as a raw pydantic/sqlite traceback instead
of the project's `click.ClickException(str(e))` convention (the engine calls themselves are
correctly fail-soft). The `Cleared N ...` line is also printed even with `-q`.
**Fix:** wrap `init_schema`/`_clear_history` and convert to `click.ClickException`; gate the
confirmation on `not quiet` (or document that `-q` only suppresses tables).

### IN-07: Stale roadmap/architecture doc references for the delivered feature

**File:** `README.md:314`, `docs/changelog.md:209`, `docs/architecture.md:256-262`
**Issue:** "Query suggestions" is still listed as an unimplemented roadmap item in README and
the changelog roadmap, and the architecture module tree/API reference do not list the new
`search/suggest.py`, `SuggestionEngine`, or `QueryLogRepository`. Readers get a picture that
contradicts the shipped code.
**Fix:** tick/remove the roadmap entries for this milestone and add the new module/repository
to the architecture and API docs.

---

_Reviewed: 2026-11-08T11:02:12Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
