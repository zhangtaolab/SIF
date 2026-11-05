---
phase: 05-agent-context-experience
reviewed: 2026-11-05T09:18:46Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/sif/cli/commands/search.py
  - tests/unit/cli/test_search.py
findings:
  critical: 1
  warning: 0
  info: 0
  total: 1
  necessity: 0
status: issues_found
---

# Phase 05: Code Review Report (Incremental Re-Review)

**Reviewed:** 2026-11-05T09:18:46Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Incremental re-review of the CR-01 and WR-01 fixes (commits `e78fa96`, `7170c08`) against diff_base `97c9862`. All 28 tests in the scoped test file pass (run with `env -u FORCE_COLOR NO_COLOR=1`); `ruff check` and `ruff format --check` are clean on both files.

**CR-01 fix (`format_results_csv`): PASS.** The rewrite uses `csv.writer` with `QUOTE_ALL` and an explicit `lineterminator="\n"`, and `_csv_field` handles both dict rows (`--line-numbers` path) and `SearchResult` objects. Verified `to_dict()` (`src/sif/core/models.py:223-237`) always emits the five consumed keys, so `float(_csv_field(r, 'score'))` cannot see a missing value. `rstrip("\n")` removes only the final row terminator — embedded newlines stay inside quotes. The regression test (`tests/unit/cli/test_search.py:291-332`) asserts exit 0, one line per result, and exact quoted output; re-ran it and the full file: green.

**WR-01 fix (`vsearch_cmd` settings guard): PASS.** `src/sif/cli/commands/search.py:331-335` wraps `get_settings()` in the identical `ValidationError -> ClickException` guard as `query_cmd`, placed before `model_copy`, with `test_vsearch_env_invalid_reranker_type_clean_error` (`tests/unit/cli/test_search.py:970-993`) asserting exit 1, a one-line error naming `reranker_model_type`, and no traceback.

**CR-02: the CR-01 bug class is still live in the `--md`/`--xml` formatters.** The prior review (2026-11-05T05:40Z, CR-01, last sentence) claimed "The `--md`/`--xml` formatters handle this via `hasattr(r, 'get')` first; only the CSV path was missed." That claim is incorrect: the `hasattr(r, "get")` guard covers only the optional `line_numbers` line (`search.py:92-95`, `:111-114`); the five mandatory fields are bare attribute access (`search.py:88-91` and `:107-110`). `sif search search <q> --line-numbers --md` and `--line-numbers --xml` (and the same combinations on `sif search query`) crash with a raw `AttributeError` traceback and exit code 1 — verified empirically below. The finding is absent from `05-REVIEW-DISPOSITION.md`. Note: ledger item WR-10 (open, out of scope) already tracks the *escaping* half of the XML formatter's problems; CR-02 is the distinct dict-vs-object crash and is reported here because it sits in a scoped file.

Necessity was assessed at standard depth per the rubric (`~/.claude/gsd-core/references/necessity-review.md`); no necessity findings — the new `_csv_field` accessor's uniform dict/object handling serves two real, reachable row shapes (proven by the two call-site paths), not a phantom state.

## Critical Issues

### CR-02: `--line-numbers --md` and `--line-numbers --xml` crash with `AttributeError: 'dict' object has no attribute 'rank'`

**File:** `src/sif/cli/commands/search.py:88-91` and `:107-110` (root cause); dict rows fed in at `:222-230`, `:231-239` (`search_cmd`) and `:593-601`, `:602-610` (`query_cmd`)
**Issue:** With `--line-numbers`, both commands pass `add_line_numbers_to_results([r.to_dict() for r in results])` — a `list[dict]` (`src/sif/cli/formatters.py:221-235`) — into `format_results_md` and `format_results_xml`. Both formatters immediately dereference `r.rank`, `r.title`, `r.score`, `r.path`, `r.collection_name` as attributes:

```python
# search.py:88-91 (format_results_md) — same shape at :107-110 (format_results_xml)
lines.append(f"## {r.rank}. {r.title}")
lines.append(f"- **Score:** {r.score:.4f}")
lines.append(f"- **Path:** `{r.path}`")
lines.append(f"- **Collection:** {r.collection_name}")
```

Every invocation of `sif search search <q> --line-numbers --md`, `--line-numbers --xml`, `sif search query <q> --line-numbers --md`, or `--line-numbers --xml` crashes. Verified empirically (mirroring the existing test scaffold, real `SearchResult` rows):

```
md: CRASH AttributeError: 'dict' object has no attribute 'rank'
xml: CRASH AttributeError: 'dict' object has no attribute 'rank'
search --line-numbers --md: exit=1 crash=AttributeError
search --line-numbers --xml: exit=1 crash=AttributeError
search --line-numbers --csv: exit=0 crash=None
```

The `hasattr(r, "get")` branch that the prior review relied on only guards the optional `line_numbers` line, which is unreachable because the crash happens on `r.rank` first. `vsearch_cmd` is unaffected (it has no `--md`/`--xml` options). Untested combination: only `--line-numbers --json` and (since this increment) `--line-numbers --csv` have tests. Same defect class as ledger CR-01 (fixed) but in the sibling formatters; absent from the disposition ledger.
**Fix:** Generalize the `_csv_field` accessor (rename to `_field`) and use it for the mandatory fields in both formatters:

```python
def _field(r: Any, name: str) -> Any:
    """Read a result field from a dict (--line-numbers path) or object row."""
    return r.get(name, "") if isinstance(r, dict) else getattr(r, name, "")


def format_results_md(results: list[Any], query: str) -> str:
    lines = [f"# Search Results: {query}", ""]
    for r in results:
        lines.append(f"## {_field(r, 'rank')}. {_field(r, 'title')}")
        lines.append(f"- **Score:** {float(_field(r, 'score')):.4f}")
        lines.append(f"- **Path:** `{_field(r, 'path')}`")
        lines.append(f"- **Collection:** {_field(r, 'collection_name')}")
        ...
```

Apply the same substitution in `format_results_xml` (`:107-110`). Add regression tests for `--line-numbers --md` and `--line-numbers --xml` asserting exit 0 (e.g. `"- **Path:** `/notes/test.md`"` in output, `"<path>/notes/test.md</path>"` respectively), alongside the existing `--csv` one.

---

_Reviewed: 2026-11-05T09:18:46Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
