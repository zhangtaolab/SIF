---
phase: 06-documentation-audit-refresh
reviewed: 2026-11-06T15:35:16Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - README.md
  - docs/architecture.md
  - docs/configuration.md
  - docs/index.md
  - docs/mcp-server.md
  - docs/models.md
  - docs/quickstart.md
  - docs/search-algorithms.md
  - scripts/generate_arch_diagram.py
  - scripts/generate_config_ref.py
findings:
  critical: 3
  warning: 8
  info: 5
  total: 16
  necessity: 0
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-11-06T15:35:16Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed the phase-06 deliverables — 7 hand-maintained docs, 1 generator-owned doc, and 2 generator scripts — at standard depth, cross-verifying every claim against `src/sif`: CLI command names/options (all command modules), MCP tool schemas (`mcp/handlers.py`, `mcp/transports/http.py`), env vars and validators (`config/settings.py`), table DDL (`database/schema.py`), dataclass/enum definitions (`core/models.py`, `models/embedding.py`), and search behavior (`search/bm25.py`, `search/rrf.py`, `search/hybrid.py`, `search/rerank.py`, `search/expansion.py`).

Much of the tree is verifiably accurate: `docs/models.md` matches the source field-for-field (including the deliberately-caveated "convention, not enforced" validation notes, which are correct); `docs/mcp-server.md` tool schemas, endpoints, CORS defaults, and the `mcp http` port quirk all match the code; `docs/index.md` is clean. The defects cluster in three places: one empirically failing command in README, two generator defects that corrupt and destabilize `docs/configuration.md` under its own CI drift gate (findings target `scripts/generate_config_ref.py` per the generator-owned rule), and a stale Mermaid diagram in `docs/architecture.md` whose generator has drifted with no gate to catch it.

Evidence methods: direct source reads; live execution of `sif get --help` / the failing README command (project venv); byte-comparison of generator output against the checked-in artifact on Python 3.13; annotation-rendering comparison on Python 3.11 (with pydantic installed), 3.13, and 3.14; diff of `scripts/generate_arch_diagram.py` output against the diagram embedded in `docs/architecture.md`.

## Critical Issues

### CR-01: Documented command fails — `sif get <path>` is not a valid invocation

**File:** `README.md:355`
**Issue:** README documents `sif get notes/python_guide.md --lines 50 --line-numbers`. `get` is a Click *group*, not a command (`src/sif/cli/commands/get.py:20-26`); the single-document fetch is the `get` subcommand of that group. Empirically verified against the installed CLI:

```
$ sif get notes/python_guide.md --lines 50 --line-numbers
Error: No such command 'notes/python_guide.md'.
```

`docs/quickstart.md:248` documents the correct form (`sif get get <path-or-doc-id>`), so the two docs also contradict each other. Every reader who copies the README's "More CLI Commands" example gets a failing command.
**Fix:**

```bash
# Fetch a document by path or document ID, with an optional line range
sif get get notes/python_guide.md --lines 50 --line-numbers
```

### CR-02: Generator writes unescaped `|` into markdown table cells, corrupting six rows of docs/configuration.md

**File:** `scripts/generate_config_ref.py:231` (`_append_options_tables`, fed by `get_type_name`)
**Issue:** For optional fields, `get_type_name` returns strings like `pathlib._local.Path | None` and `str | None`. `_append_options_tables` inserts that string raw into a 4-column markdown table row (`f"| {env_var} | {type_name} | {default_str} | {description} |"`), so the union's pipe splits the Type column into two cells. Result in the shipped `docs/configuration.md`: the rows for `SIF_DB_PATH` (line 47), `SIF_MODEL_PATH` (54), `SIF_API_KEY` (77), `SIF_API_BASE` (78), `SIF_RERANKER_MODEL_PATH` (85), and `SIF_CACHE_DIR` (115) all render with a phantom extra column — e.g. `| SIF_DB_PATH | pathlib._local.Path | None | \`~/.local/share/sif/sif.db (computed)\` | ... |` is 5 cells under a 4-column header. The rendered tables are malformed at HEAD.
**Fix:** Escape pipes when emitting cell content in `_append_options_tables`:

```python
def _md_cell(value: str) -> str:
    return value.replace("|", "\\|")

lines.append(
    f"| {env_var} | {_md_cell(type_name)} | {default_str} | {_md_cell(description)} |"
)
```

(or render optional fields as e.g. `Path (optional)` / `str (optional)` instead of a union repr).

### CR-03: Generator output is Python-version-dependent — CI drift gate cannot reproduce the checked-in artifact

**File:** `scripts/generate_config_ref.py:19-40` (`get_type_name`)
**Issue:** `get_type_name` relies on `str(annotation)` / `__name__` of `types.UnionType` members, which render differently per interpreter. Verified end-to-end with pydantic installed:

- Python 3.11: `Settings.model_fields['db_path'].annotation` → `pathlib.Path | None`
- Python 3.13 (project venv): → `pathlib._local.Path | None`; `generate_markdown()` output is byte-identical to the checked-in `docs/configuration.md` (verified `MATCHES_CHECKED_IN: True`), proving the shipped file was generated on 3.13
- Python 3.14: `get_type_name(Path | None)` degrades to bare `Union` (loses the member type entirely)

The CI drift gate (`.github/workflows/docs.yml:35-38`) regenerates on **Python 3.11** and runs `git diff --exit-code docs/cli-reference.md docs/configuration.md`. On 3.11 the regenerated bytes contain `pathlib.Path` where the checked-in 3.13 artifact has `pathlib._local.Path`, so the gate fails (or, viewed from the other side, any regeneration ping-pongs depending on the contributor's interpreter). The generator is not reproducible under the project's own documented process (`make docs-generate`), and on 3.14 it would silently emit garbage type names.
**Fix:** Normalize annotations explicitly instead of relying on interpreter reprs:

```python
import types
import typing

def get_type_name(annotation: object) -> str:
    if annotation is None:
        return ""
    if isinstance(annotation, type):
        return "Path" if annotation.__module__ == "pathlib" else annotation.__name__
    if isinstance(annotation, types.UnionType) or typing.get_origin(annotation) is typing.Union:
        args = [get_type_name(a) for a in typing.get_args(annotation) if a is not type(None)]
        return " | ".join(args) if args else "None"
    return getattr(annotation, "__name__", str(annotation))
```

(plus escaping per CR-02). Optionally also pin the generation environment to CI's Python version.

## Warnings

### WR-01: BM25 k1 default contradicts search-algorithms.md and the actual FTS5 behavior

**File:** `README.md:243`
**Issue:** README states "`k1`: Controls term frequency saturation (default: 1.5)". `docs/search-algorithms.md:62-67` — the dedicated, audited reference — states SIF does not expose k1/b and uses FTS5's built-in defaults (k1 = 1.2, b = 0.75), which matches the implementation (`src/sif/search/bm25.py:73-87` orders by FTS5's bare `rank`; no k1 is plumbed anywhere). The 1.5 figure exists only as the dead `bm25_k1` field of the unused Pydantic boundary model `src/sif/models/search.py:28`, which nothing in the search layer reads. Two docs in the same tree give different defaults for the same parameter; README's is wrong.
**Fix:** README: change "(default: 1.5)" to "(FTS5 built-in default: 1.2)" — or drop the number and link to `docs/search-algorithms.md` as the source of truth.

### WR-02: architecture.md Mermaid diagram has drifted from its own generator; nothing regenerates it

**File:** `docs/architecture.md:323-368`
**Issue:** The block footer claims "_Generated by `scripts/generate_arch_diagram.py` from actual source imports._", but running the script at HEAD produces one additional edge, `search --> config`, missing from the embedded diagram (verified by diffing the doc block against fresh generator output). The edge originates from a `TYPE_CHECKING`-only import (`src/sif/search/rerank.py:19`, `from sif.config.settings import Settings` under `if TYPE_CHECKING:`) that the generator's AST walk counts as a runtime dependency — so either the doc is stale or the edge is phantom, and both are defects: the checked-in artifact does not match its cited generator, and `make docs-generate` (Makefile:71-74) runs only `generate_cli_ref.py` + `generate_config_ref.py`, so no gate can ever catch this class of drift.
**Fix:** Decide the semantics and align: (a) filter imports guarded by `if TYPE_CHECKING:` in `extract_imports` (e.g., skip `ImportFrom` nodes whose enclosing statement is `if TYPE_CHECKING`), regenerate, and add `generate_arch_diagram.py` to `docs-generate` + the CI drift gate; or (b) accept type-only imports as edges and regenerate the doc so it matches the tool it claims to be generated by.

### WR-03: Arch-diagram generator resolves its source tree relative to CWD and silently emits an empty diagram

**File:** `scripts/generate_arch_diagram.py:9`
**Issue:** `SRC_DIR = Path("src/sif")` is working-directory-relative. Invoked from any directory other than the repo root (absolute path, editor task, CI step with a different workdir), `rglob("*.py")` over a nonexistent directory yields nothing, `build_dependency_graph` gets `{}`, and the script prints a valid-but-empty `graph TD` block and exits 0 — silently wrong output from a generator whose product is checked into the docs. This is inconsistent with the sibling `generate_config_ref.py:13-14`, which anchors `PROJECT_ROOT` via `Path(__file__).resolve().parent.parent`.
**Fix:**

```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "sif"
```

(optionally fail loudly if `SRC_DIR` doesn't exist).

### WR-04: Validator scanner records only the first field of multi-field validators

**File:** `scripts/generate_config_ref.py:43-59` (`get_validators`)
**Issue:** The line-oriented parser takes `inner.split(",")[0]` from the decorator argument list. `Settings` has `@field_validator("db_path", "cache_dir", mode="before")` (`src/sif/config/settings.py:194`), so the generated doc annotates `SIF_DB_PATH` with "(validated by `expand_path`)" but not `SIF_CACHE_DIR`, even though both fields pass through the same validator. Verified at runtime: `get_validators()` returns keys `model_type, reranker_model_type, api_base, db_path, log_level` — `cache_dir` is absent.
**Fix:** Extract every quoted field name from the decorator arguments:

```python
fields = re.findall(r"[\"']([^\"']+)[\"']", inner)
for f in fields:
    validators[f] = ...  # assigned when the following def is seen
```

### WR-05: Validation Rules table omits the enforced `reranker_model_type` rule

**File:** `scripts/generate_config_ref.py:239-268` (`_append_validation_rules`)
**Issue:** The table claims to cover startup validation ("SIF validates configuration on startup. Invalid values will raise errors:") and lists `model_type`'s membership rule, but omits `reranker_model_type`, which is validated identically by `Settings.validate_reranker_model_type` (`src/sif/config/settings.py:166-181`, must be `gguf` or `sentence_transformers`). This is a hand-maintained list inside the generator that has already drifted from the validators that exist — in tension with the script's own anti-staleness design (`get_valid_model_types` refuses to emit a stale set).
**Fix:** Derive the row from introspection (reuse `get_validators()` plus the valid-set extraction pattern from `get_valid_model_types`), or at minimum add: ``| `reranker_model_type` | Must be one of: `gguf`, `sentence_transformers` | `Invalid reranker_model_type: xyz. Must be one of ['gguf', 'sentence_transformers']` |``

### WR-06: Computed-default paths presented as Linux-only values

**File:** `scripts/generate_config_ref.py:90-96` (`get_computed_default`)
**Issue:** `get_computed_default` hardcodes `"~/.local/share/sif/sif.db (computed)"` and `"~/.cache/sif (computed)"` as the Default column for `SIF_DB_PATH` / `SIF_CACHE_DIR`. These are the Linux platformdirs values; on macOS the computed defaults are `~/Library/Application Support/sif/sif.db` and `~/Library/Caches/sif` (via `Settings.get_db_path()` / `get_cache_dir()`, `src/sif/config/settings.py:212-232`). `docs/mcp-server.md:202-205` documents the per-platform truth correctly; the configuration reference — the doc users consult for exactly this question — states a single path as "the" default. Misleads macOS/Windows users into looking in the wrong place for their index.
**Fix:** Change the computed strings to name the mechanism and both platforms, e.g. `"platformdirs default (Linux: ~/.local/share/sif/sif.db; macOS: ~/Library/Application Support/sif/sif.db)"`.

### WR-07: "Weighted Combination" documents a fusion scheme that does not exist

**File:** `docs/search-algorithms.md:237-245`
**Issue:** The section presents `final_score = bm25_weight * bm25_score + vector_weight * vector_score` as an available fine-grained control. No weighted raw-score fusion exists anywhere in the search layer: `bm25_weight`/`vector_weight` appear only in the unused Pydantic boundary model `src/sif/models/search.py:32-35` (nothing in `src/sif/search/` reads them); `HybridSearcher` calls `RRFFusion.fuse([bm25_results, vector_results], options.limit)` with default equal weights (`src/sif/search/hybrid.py:73`), and `RRFFusion`'s weights multiply `1/(k+rank)`, not raw scores (`src/sif/search/rrf.py:125`). There is also no CLI/env knob exposing any weight. The doc describes a capability the product does not have.
**Fix:** Delete the section, or rewrite it to describe what exists: `RRFFusion.fuse(results_lists, limit, weights)` applies per-list weights inside the RRF term (`weight * 1/(k+rank)`), defaulting to equal weights and not configurable from the CLI.

### WR-08: Quickstart "Search History" tip is non-functional

**File:** `docs/quickstart.md:348-350`
**Issue:** The tip suggests `sif search query "" | tee -a ~/.sif_searches` "to create a search history file". An empty query sanitizes to the FTS phrase `'""'`, which matches nothing (`src/sif/search/bm25.py:159-171` — `_build_fts_query` returns `'""'` when no usable terms exist), so the command tees an empty result set; and even with a real query it would append *results*, not a history of *queries*. The instructions cannot do what they claim under any input.
**Fix:** Remove the tip, or replace with something that actually records queries, e.g. a shell function: `sifq() { echo "$*" >> ~/.sif_searches; sif search query "$*"; }`.

## Info

### IN-01: Template-substitution residue — stray triple spaces in command lines

**File:** `docs/quickstart.md:32`
**Issue:** Multiple quickstart commands contain unexplained triple spaces where an argument appears to have been removed: lines 32, 172, 180, 188, 304, 310, 317, 320 (e.g. `sif collection add ~/Documents/notes --name my-notes   --description "My personal notes"`). Harmless to copy-paste but visibly sloppy in rendered output.
**Fix:** Normalize to single spaces.

### IN-02: README Python API example never closes the Database

**File:** `README.md:391-399`
**Issue:** The example uses `with db.connection:` (which only commits/rolls back the sqlite transaction) and never closes the connection or the `Database` wrapper. The project's own documented discipline (architecture.md, "Connection Management": every CLI command uses `with Database(index_path) as db:`) is the pattern the flagship README example should model.
**Fix:**

```python
with Database(Path.home() / ".local" / "share" / "sif" / "sif.db") as db:
    db.init_schema()
    with db.connection:
        searcher = BM25Searcher(db.connection)
        results: list[SearchResult] = searcher.search("python decorators")
```

### IN-03: Config generator silently drops unknown SECTIONS field names

**File:** `scripts/generate_config_ref.py:218-220`
**Issue:** `if field_name not in model_fields: continue` means a renamed or mistyped entry in `SECTIONS` silently vanishes from the reference instead of failing — inconsistent with the script's own fail-fast posture in `get_valid_model_types` (which raises rather than emit stale content). The CI diff gate would catch the resulting omission, but only after someone thinks to regenerate.
**Fix:** Raise `RuntimeError(f"SECTIONS references unknown Settings field: {field_name}")` instead of `continue`.

### IN-04: Arch-diagram module keys use "/" separators and degenerate for root-level files

**File:** `scripts/generate_arch_diagram.py:35`
**Issue:** `module_name = "sif." + "/".join(rel.parent.parts) + "/" + rel.stem` produces `sif.cli/main` and, for files directly under `sif/`, `sif./_version`. It works only because `package_of_module` returns `""` for the degenerate form and skips it. Fragile coupling between two half-formats.
**Fix:** Build dotted module names: `"sif." + ".".join((*rel.parent.parts, rel.stem))` (guarding the empty-parent case).

### IN-05: Published examples hardcode one user's home directory

**File:** `docs/mcp-server.md:234`
**Issue:** The Claude Desktop config and Custom Tool Handler examples embed `/Users/forrest/Library/Application Support/sif/sif.db` (also line 320). A real username in published docs reads as an oversight rather than an example.
**Fix:** Use a placeholder path (`/Users/<you>/Library/Application Support/sif/sif.db`) or `~`-expansion note.

---

_Reviewed: 2026-11-06T15:35:16Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
