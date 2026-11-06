---
phase: 260917-dkf-typing-debt-batch-2-clear-indexing-watch
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/indexing/watcher.py
  - src/sif/embedding/manager.py
  - src/sif/models/embedding.py
  - src/sif/embedding/embedder.py
autonomous: true
requirements: [PHASE03-DEFERRED-TYPING]  # phase-03 open deferred item: mypy strict-mode typing debt; batch 2 of N (batch 1 = quick 260917-bo2, rerank.py 22->0)
estimate:
  tokens: 36000
  raw_tokens: 36000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/indexing/watcher.py` exits 0 (all 13 current errors cleared; the `pyproject.toml: note: unused section(s)` NOTE may print under single-file invocation — config-level, expected, NOT in scope)"
    - "`env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/embedding/manager.py` exits 0 (all 12 current errors cleared via the EmbeddingConfig declaration fix + return annotation)"
    - "`env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/embedding/embedder.py` exits 0 (all 14 current errors cleared)"
    - "ZERO behavior change: for str event paths `os.fsdecode` is identity so watcher log output is byte-identical; `Field(5)` and `Field(default=5)` are the identical pydantic call so every EmbeddingConfig default (model_type=MODELSCOPE, model_name=Qwen/Qwen3-Embedding-0.6B, embedding_dim=1024, max_tokens=512, batch_size=32, n_gpu_layers=0, n_ctx=2048, api_key/api_path=None, cache_embeddings=True) is unchanged; embedder edits are annotations and typed intermediate locals only — no logic, no guard, no signature-value changes anywhere"
    - "Full-project mypy drops 117 -> 78 errors (13+12+14 = 39 cleared; batch context said 'expect 75' but it assumed 14 errors per file — fresh per-file counts are 13/12/14). If the count differs from 78, diff the error list against baseline before proceeding; the three target files must be at zero regardless"
    - "`env -u FORCE_COLOR NO_COLOR=1 python -m pytest` green (676 passed / 0 failed expected; if exactly 2 order-dependent caplog failures appear in tests/unit/embedding/test_openai_embedder.py they are pre-existing WINDOWS.md #3/#4)"
    - "`ruff check src tests` and `ruff format --check src tests` both clean (in particular NO new RUF100 from the two removed `# noqa: F821` in watcher.py)"
  artifacts:
    - "src/sif/indexing/watcher.py — TYPE_CHECKING DocumentIndexer import, `_event_path` coercion helper, `BaseObserver` annotation, both `# noqa: F821` removed"
    - "src/sif/models/embedding.py — EmbeddingConfig's 10 positional `Field(<default>, ...)` first args converted to `default=<default>` keyword form (declaration syntax only)"
    - "src/sif/embedding/manager.py — `from typing import Any` import, `get_model_info() -> dict[str, Any]`"
    - "src/sif/embedding/embedder.py — three `self._dimension: int` annotations, typed return locals at the 9 remaining no-any-return sites, `dict[str, int]` vocabulary annotation, `**kwargs: Any` on create_embedder"
  key_links:
    - "TYPE_CHECKING `from sif.indexing.indexer import DocumentIndexer` <-> the two quoted `\"DocumentIndexer\"` annotations (watcher.py lines 20, 91) — typecheck-only, zero runtime import edge, no circular-import risk (indexer.py does not import watcher.py)"
    - "`from watchdog.observers.api import BaseObserver` <-> `self._observer: BaseObserver | None` (line 102) while `Observer()` stays the constructor (line 114; runtime-verified Observer is a BaseObserver subclass — mypy cannot use the conditionally-imported `watchdog.observers.Observer` name as a type, hence the api base class)"
    - "`_event_path(path: bytes | str) -> str` via `os.fsdecode` (probe-verified `os.fsdecode: (bytes | str) -> str`) <-> all four `event.src_path` call sites + `event.dest_path` in the on_moved log line"
    - "EmbeddingConfig `Field(default=...)` keyword form <-> manager.py's two construction sites (line 39 bare `EmbeddingConfig()`, line 54 `from_settings` omitting n_ctx) — probe-verified: mypy's native pydantic `dataclass_transform` support treats a field as defaulted ONLY when the default is the `default=` keyword or a direct assignment; positional `Field(<default>)` reads as required (no mypy plugin is configured in pyproject.toml, and none is needed for this fix)"
    - "`self._dimension: int = <Any-typed third-party call>` at the three __init__ assignment sites (lines 82, 165, 327) <-> the three `dimension` properties (116, 263, 348) returning int"
    - "typed locals (`result: <declared return type> = <Any expr>`) <-> the 12 no-any-return sites — probe-verified numpy `ndarray.mean()` and `ndarray.tolist()` return `Any` even on typed ndarrays, and `sentence_transformers`/`llama_cpp`/`openai` resolve to Any (not installed in the uv env), so every returning expression is Any and needs a typed local or annotated source field"
---

<objective>
Clear all mypy strict-mode errors in the three hottest typing-debt files (batch 2 of the phase-03 deferred series, following batch 1 = quick 260917-bo2): `src/sif/indexing/watcher.py` (13), `src/sif/embedding/manager.py` (12), `src/sif/embedding/embedder.py` (14). Full-project count drops 117 -> 78. Zero behavior change — annotations, TYPE_CHECKING imports, declaration-syntax fixes, typed intermediate locals, and stale-noqa removal only. The 676-test suite stays green.

Planner-verified error inventory (fresh run this session, `env -u FORCE_COLOR NO_COLOR=1 uv run mypy <file>`; counts are 13/12/14, not the 14/14/14 the batch context estimated):

- `watcher.py` (13): name-defined x2 (lines 20, 91 — quoted `"DocumentIndexer"` never imported); arg-type x4 + str-bytes-safe x4 (lines 39/40, 48/49, 57/58, 66/67 — `event.src_path`/`dest_path` are typed `bytes | str` by watchdog, runtime-verified); valid-type x1 (line 102 — `watchdog.observers.Observer` is a conditionally-imported name, so mypy sees a variable, not a type) + attr-defined x2 (141/142 `Observer?` has no stop/join — cascade of the same).
- `manager.py` (12): call-arg x11 (line 39 x10 + line 54 x1) + type-arg x1 (line 230 bare `dict`). Root cause of all 11 call-args, probe-verified this session: `EmbeddingConfig` (src/sif/models/embedding.py, pydantic 2.13.1) declares 10 fields as `Field(<positional default>)`; mypy's native pydantic `dataclass_transform` support only recognizes defaults passed as the `default=` keyword or as direct assignments (the two unflagged fields `api_base`/`cache_dir` use plain `= None`). No mypy plugin is configured or needed.
- `embedder.py` (14): no-any-return x12 + type-arg x1 (line 532 bare `dict`) + no-untyped-def x1 (line 567 `**kwargs` untyped). All 12 no-any-return sites return expressions typed Any — either calls on uninstalled third-party models (`sentence_transformers`, `llama_cpp`, `openai` resolve to Any under `ignore_missing_imports`) or numpy members that return Any even on typed arrays (probe-verified: `ndarray.mean()`, `ndarray.tolist()` reveal `Any`).

Verified environment facts (probe-tested under `.planning/tmp/`, then deleted):
- `Field(5)` -> mypy "Missing named argument"; `Field(default=5)` and `x: int = 5` -> clean. `Field(5)` and `Field(default=5)` are the identical pydantic call at runtime.
- `os.fsdecode` accepts `bytes | str` and returns `str` (identity for str).
- `watchdog.observers.api.BaseObserver` imports cleanly at runtime; the platform `Observer` (FSEventsObserver here) is a `BaseObserver` subclass, so `Observer()` construction at line 114 stays untouched and `schedule`/`start`/`stop`/`join` all resolve on the base-class annotation.
- `DocumentIndexer` lives at `src/sif/indexing/indexer.py:44`; `indexer.py` does not import `watcher.py`, and the TYPE_CHECKING import adds no runtime edge regardless.
- Settings has NO `n_ctx` attribute — `from_settings` (manager.py:54) legitimately omits it; `load_model` reads `self._config.n_ctx` which defaults to 2048 exactly as today. Do not invent a settings pass-through.
- Tests: watcher -> tests/unit/indexing/test_watcher.py; manager/EmbeddingConfig -> tests/unit/embedding/test_manager.py (+test_factory.py same package); embedder -> tests/unit/embedding/ directory.
- Batch-1 conventions apply throughout: per-file gate `env -u FORCE_COLOR NO_COLOR=1 uv run mypy <file>`; the `pyproject.toml: unused section(s)` NOTE is expected under single-file invocation — do NOT touch pyproject.toml; no blanket `# type: ignore`; pathspec-only commits; untracked runtime dirs (.gsd/, .planning/state.json, .planning/tmp/, .planning/ui-reviews/) and the pre-staged `mypy.ini` deletion stay untouched.

Purpose: continue chipping the phase-03 deferred mypy debt file-by-file with provable zero behavior change; next batches target mcp/handlers.py (12) and the remaining ~30 files.
Output: three mypy-clean files, green suite, clean ruff, full-project count 117 -> 78, three pathspec-scoped commits.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/quick/260917-bo2-typing-debt-batch-1-clear-search-rerank-/260917-bo2-PLAN.md
@src/sif/indexing/watcher.py
@src/sif/embedding/manager.py
@src/sif/models/embedding.py
@src/sif/embedding/embedder.py
@pyproject.toml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Type watcher event paths, Observer annotation, DocumentIndexer import (13 errors -> 0)</name>
  <files>src/sif/indexing/watcher.py</files>
  <action>
Edits confined to src/sif/indexing/watcher.py:

1. Imports: add `import os` and `from typing import TYPE_CHECKING` to the stdlib group (before the watchdog imports), and `from watchdog.observers.api import BaseObserver` directly after `from watchdog.observers import Observer` (isort order: `watchdog.observers` sorts before `watchdog.observers.api`). After the `from sif.utils.logging import get_logger` import and before `logger = get_logger(__name__)`, add:
   `if TYPE_CHECKING:` block containing `from sif.indexing.indexer import DocumentIndexer`.

2. Both quoted annotations (line 20 in IndexingEventHandler.__init__ and line 91 in FileWatcher.__init__): remove the trailing `# noqa: F821` but KEEP the quotes on `"DocumentIndexer"` — the TYPE_CHECKING import makes the name resolve for mypy and ruff, so the noqa would trip RUF100 if left.

3. Line 102: `self._observer: Observer | None = None` -> `self._observer: BaseObserver | None = None`. Line 114 `self._observer = Observer()` stays byte-identical (runtime-verified: the platform Observer is a BaseObserver subclass; mypy just cannot use the conditionally-imported Observer name as a type). This fixes valid-type at 102 and the stop/join attr-defined cascade at 141-142.

4. After the `logger = get_logger(__name__)` line, add a module-level helper:
   `def _event_path(path: bytes | str) -> str:` with docstring "Normalize a watchdog event path to str." and body `return os.fsdecode(path)` (probe-verified identity for str, decode for the bytes case watchdog's typing permits but never produces in practice — the old code would have raised TypeError in `str.endswith` on bytes anyway, so no reachable behavior changes).

5. In each of on_created / on_modified / on_deleted: after the `if event.is_directory: return` early-exit, add `src_path = _event_path(event.src_path)`; change the guard call to `self._should_handle(src_path)`; change the log line to interpolate the local (`f"File created: {src_path}"` etc.).

6. on_moved: same local for src_path; the log line becomes `logger.info(f"File moved: {src_path} -> {_event_path(event.dest_path)}")` — dest_path is also typed `bytes | str` and must be coerced in the f-string.

7. `_should_handle(self, path: str)` signature unchanged (callers now pass str). Touch nothing else — no guard removals, no handler-logic edits.

Then run the verification; commit pathspec-only: `git commit -m "fix(260917-dkf): type watcher event paths, observer, and DocumentIndexer; watcher.py mypy-clean" -- src/sif/indexing/watcher.py`.
  </action>
  <verify>
    <automated>env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/indexing/watcher.py > /dev/null 2>&1 && env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -q && ruff check src/sif/indexing/watcher.py && ruff format --check src/sif/indexing/watcher.py</automated>
  </verify>
  <done>mypy on watcher.py exits 0 with "Success" (unused-section NOTE acceptable); tests/unit/indexing/test_watcher.py fully green; ruff check + format clean on the file; diff contains only the import additions, the two noqa removals, the BaseObserver annotation, the _event_path helper, and the four handler locals; pathspec commit created.</done>
</task>

<task type="auto">
  <name>Task 2: Declare EmbeddingConfig Field defaults as keywords; type manager returns (12 errors -> 0)</name>
  <files>src/sif/models/embedding.py, src/sif/embedding/manager.py</files>
  <action>
1. src/sif/models/embedding.py — EmbeddingConfig class ONLY (do not touch EmbeddingModelInfo / EmbeddingRequest / EmbeddingResponse; their `Field(...)` Ellipsis fields are intentionally required and out of scope). Convert the 10 positional `Field(<default>, ...)` first arguments to `default=<default>` keyword form, changing nothing else in each call: model_type `Field(default=ModelType.MODELSCOPE, description="Model type")`; model_path `Field(default=None, ...)`; model_name `Field(default="Qwen/Qwen3-Embedding-0.6B", ...)`; embedding_dim `Field(default=1024, ge=1, ...)`; max_tokens `Field(default=512, ge=1, ...)`; batch_size `Field(default=32, ge=1, ...)`; n_gpu_layers `Field(default=0, ge=0, ...)`; n_ctx `Field(default=2048, ge=512, ...)`; api_key `Field(default=None, exclude=True, repr=False)`; cache_embeddings `Field(default=True, ...)`. This is declaration syntax only — `Field(5)` and `Field(default=5)` are the identical pydantic call — and it is the fix for all 11 call-arg errors (probe-verified: mypy's native pydantic dataclass_transform support reads defaults only from the `default=` keyword or direct assignment; `api_base`/`cache_dir` with plain `= None` were never flagged).

2. src/sif/embedding/manager.py — do NOT touch lines 39 and 54; both construction sites become type-correct once the declaration is fixed (`EmbeddingConfig()` at 39 uses defaults exactly as at runtime today; `from_settings` at 54 legitimately omits n_ctx — Settings has no n_ctx attribute, and `load_model` reads `self._config.n_ctx` defaulting to 2048 exactly as today). The only manager edits: add `from typing import Any` to the stdlib group after `import time`, and change line 230 `def get_model_info(self) -> dict:` -> `def get_model_info(self) -> dict[str, Any]:`.

3. Scope guards: no pydantic-plugin addition to pyproject.toml (not needed, and pyproject is out of scope); no signature changes to EmbeddingManager; no new constructor arguments anywhere.

Then run the verification; commit pathspec-only: `git commit -m "fix(260917-dkf): declare EmbeddingConfig Field defaults as keywords; type manager; manager.py mypy-clean" -- src/sif/models/embedding.py src/sif/embedding/manager.py`.
  </action>
  <verify>
    <automated>env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/embedding/manager.py > /dev/null 2>&1 && env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/embedding/test_manager.py tests/unit/embedding/test_factory.py -q && ruff check src/sif/models/embedding.py src/sif/embedding/manager.py && ruff format --check src/sif/models/embedding.py src/sif/embedding/manager.py</automated>
  </verify>
  <done>mypy on manager.py exits 0 (follows imports into models/embedding.py, so this validates the pair); test_manager.py + test_factory.py fully green (constructor defaults unchanged at runtime); ruff clean on both files; diff on models/embedding.py is exactly the 10 keyword-form conversions; pathspec commit created.</done>
</task>

<task type="auto">
  <name>Task 3: Annotate embedder third-party returns; full-project gate (14 errors -> 0, 117 -> 78)</name>
  <files>src/sif/embedding/embedder.py</files>
  <action>
Edits confined to src/sif/embedding/embedder.py. Two patterns, both probe-verified this session (numpy `ndarray.mean()`/`ndarray.tolist()` reveal Any even on typed arrays; sentence_transformers/llama_cpp/openai resolve to Any since they are not installed in the uv env):

A. Source-field annotations (fix the three `dimension` properties at the assignment sites — assigning Any to a typed attribute is allowed and makes the properties return int):
   1. Line 82 (SentenceTransformerEmbedder.__init__): `self._dimension = self.model.get_sentence_embedding_dimension()` -> `self._dimension: int = self.model.get_sentence_embedding_dimension()`.
   2. Line 165 (LlamaCppEmbedder.__init__): `self._dimension = self.model.n_embd()` -> `self._dimension: int = self.model.n_embd()`.
   3. Line 327 (ModelScopeEmbedder.__init__): same annotation on `self._dimension: int = self.model.get_sentence_embedding_dimension()`.

B. Typed intermediate locals immediately before each return (zero runtime cost; returning a typed local is the deterministic no-any-return fix). Keep the original expression byte-identical on the RHS:
   - Line 95 (SentenceTransformerEmbedder.embed): `result: list[float] = embedding.tolist()` then `return result`.
   - Line 111 (embed_batch): `result: list[list[float]] = embeddings.tolist()` then `return result`.
   - Line 184 (LlamaCppEmbedder.embed): `result: list[float] = vector.tolist()` then `return result`.
   - Line 193 (_unwrap_embedding): annotate the local `arr: np.ndarray = np.asarray(raw, dtype=float)` — fixes the bare `return arr` at 199.
   - Line 205: `result: np.ndarray = arr.mean(axis=0)` then `return result` (mean() returns Any even on typed arrays — probe-verified).
   - Line 213: `result: np.ndarray = arr[0].mean(axis=0)` then `return result`.
   - Lines 253-258 (create_completion): assign the existing call expression to `result: dict[str, Any] = self.model.create_completion(...)` (arguments unchanged, including the `stop if stop is not None else []` normalization) then `return result`.
   - Line 334 (ModelScopeEmbedder.embed): `result: list[float] = embedding.tolist()` then `return result`.
   - Line 343 (ModelScopeEmbedder.embed_batch): `result: list[list[float]] = embeddings.tolist()` then `return result`.
   - Line 514 (OpenAIEmbedder._normalize): `result: list[float] = arr.tolist()` then `return result`.

C. Two stragglers:
   - Line 532 (SimpleEmbedder.__init__): `self.vocabulary: dict = {}` -> `self.vocabulary: dict[str, int] = {}` (TF-IDF term-to-index convention; the field is never populated — the annotation just documents intent).
   - Line 567 (create_embedder): `**kwargs,` -> `**kwargs: Any,` (`Any` already imported at line 9).

Do NOT touch: any `# noqa: PLC0415` runtime imports, the is_quiet/suppress_output branches, the ragged/misindexed response guards in OpenAIEmbedder.embed_batch, or the ValueError shapes in _unwrap_embedding — all load-bearing behavior.

Then the full gates per CLAUDE.md: per-file mypy, the FULL quality suite, and the full-project mypy count check (expect 78 errors in 31 files; the batch context's "expect 75" assumed 14 errors per file but fresh counts were 13/12/14 = 39 cleared). If the full-project count is not exactly 78, diff the current error list against the pre-task baseline before concluding — the three target files must be at zero regardless, and any unexpected NEW error elsewhere must be investigated, not ignored. Commit pathspec-only: `git commit -m "fix(260917-dkf): annotate embedder third-party returns; embedder.py mypy-clean" -- src/sif/embedding/embedder.py`.
  </action>
  <verify>
    <automated>env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/embedding/embedder.py > /dev/null 2>&1 && env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/embedding -q && ruff check src tests && ruff format --check src tests && env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q && [ "$(env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif 2>&1 | grep -c 'error:')" -le 78 ] && ! env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif 2>&1 | grep "error:" | grep -q "indexing/watcher.py\|embedding/manager.py\|embedding/embedder.py"</automated>
  </verify>
  <done>mypy on embedder.py exits 0; tests/unit/embedding green; full pytest suite green (676 passed / 0 failed expected; exactly-2 pre-existing caplog flakers in tests/unit/embedding/test_openai_embedder.py are WINDOWS.md #3/#4 — verify they are exactly those 2); ruff check + format --check clean across src and tests; full-project mypy shows 78 errors with zero in the three target files; diff review confirms annotations/typed-locals/noqa-and-keyword-form changes only — zero behavior change; pathspec commit created.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| none new | Typing-only change: annotations, declaration syntax, typed locals, TYPE_CHECKING imports. No new inputs, outputs, or call paths. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260917-dkf-01 | Tampering | watcher `_event_path` (os.fsdecode on event paths) | low | accept | Watchdog paths were already trusted process input; fsdecode is identity for the str paths actually produced and only replaces a latent TypeError for hypothetical bytes — no new parsing or execution. |
| T-260917-dkf-02 | Information disclosure | embedder/manager typing near api_key fields | low | accept | api_key flows (constructor-only, exclude=True, repr=False) are untouched — edits are return-type annotations and Field declaration syntax with identical runtime semantics. |
</threat_model>

<verification>
1. Per-file gates (definition of done for the typing work): `env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/indexing/watcher.py` / `src/sif/embedding/manager.py` / `src/sif/embedding/embedder.py` — each exits 0 with "Success". The `pyproject.toml: note: unused section(s)` note is acceptable; any `error:` line is a failure.
2. Full quality suite (CLAUDE.md): `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` (676 passed / 0 failed expected; 2 order-dependent caplog failures in tests/unit/embedding/test_openai_embedder.py are pre-existing WINDOWS.md #3/#4 if they appear), `ruff check src tests`, `ruff format --check src tests`.
3. Full-project count check: `env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif 2>&1 | tail -1` reports 78 errors in 31 files (117 - 39; investigate any deviation, never paper over it), and no error line references any of the three target files.
4. Zero-behavior-change audit: `git diff HEAD~3 -- src/sif/indexing/watcher.py src/sif/models/embedding.py src/sif/embedding/manager.py src/sif/embedding/embedder.py` — every hunk is one of: import additions (os / typing / TYPE_CHECKING block / BaseObserver), the `_event_path` helper + four handler locals, the two `# noqa: F821` removals, the BaseObserver field annotation, the 10 `Field(default=...)` keyword conversions, `dict[str, Any]` on get_model_info, `self._dimension: int` x3, typed return locals x9, `arr: np.ndarray`, `dict[str, int]` vocabulary, `**kwargs: Any`. No logic edits, no guard removals, no constructor/value changes.
5. Commits are pathspec-scoped to the four files only; `git status` still shows the untracked runtime dirs (.gsd/, .planning/state.json, .planning/tmp/, .planning/ui-reviews/) and the pre-staged mypy.ini deletion untouched by this task's commits.
</verification>

<success_criteria>
- All three files mypy strict-clean in this environment (13 + 12 + 14 = 39 errors cleared).
- Full-project mypy 117 -> 78 errors; zero errors remain in watcher.py, manager.py, or embedder.py.
- Test suite green at baseline; ruff check + format --check clean.
- Zero behavior change proven by diff audit (fsdecode identity for str, identical pydantic Field calls, annotations/locals only).
- Three atomic pathspec commits landed; no unrelated files swept in.
- SUMMARY records deferred-item progress for the next batches (78 errors remain in 31 files; next hottest mcp/handlers.py 12).
</success_criteria>

<output>
Create `.planning/quick/260917-dkf-typing-debt-batch-2-clear-indexing-watch/260917-dkf-SUMMARY.md` when done
</output>
