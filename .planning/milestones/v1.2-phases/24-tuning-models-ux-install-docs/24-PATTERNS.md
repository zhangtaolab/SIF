# Phase 24: Tuning + Models UX + Install Docs - Pattern Map

**Mapped:** 2026-11-17
**Files analyzed:** 34 (12 new, 22 modified/regenerated)
**Analogs found:** 31 / 34

All analog paths below are git-tracked source (verified with `git ls-files -- <path>`); no
`.gsd/capabilities/` mirror paths are used. No file was modified during this mapping.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/chunk_sweep.py` (NEW) | script / runbook | batch | `scripts/harrier_eval.py` | exact |
| `scripts/breadcrumb_eval.py` (NEW) | script / runbook | batch | `scripts/harrier_eval.py` | exact |
| `src/sif/search/tuning_verdict.py` (NEW) | policy / service | transform | `src/sif/search/embedder_verdict.py` | exact |
| `src/sif/indexing/breadcrumb.py` (NEW) | utility | transform | `src/sif/indexing/chunker.py` | role-match |
| `src/sif/cli/commands/models.py` (NEW) | controller (Click group) | request-response | `src/sif/cli/commands/pull.py` + `src/sif/cli/commands/eval.py` group | role-match |
| `tests/unit/scripts/test_chunk_sweep.py` (NEW) | test | batch | `tests/unit/scripts/test_harrier_eval.py` | exact |
| `tests/unit/scripts/test_breadcrumb_eval.py` (NEW) | test | batch | `tests/unit/scripts/test_harrier_eval.py` | exact |
| `tests/unit/search/test_tuning_verdict.py` (NEW) | test | transform | `tests/unit/search/test_embedder_verdict.py` | exact |
| `tests/unit/indexing/test_breadcrumb.py` (NEW) | test | transform | `tests/unit/indexing/test_chunker.py` | role-match |
| `tests/unit/cli/test_models.py` (NEW) | test | request-response | `tests/unit/cli/test_pull.py` + `tests/unit/cli/test_status.py` | role-match |
| `.planning/phases/24-…/bench/chunk-sweep.json` (NEW) | data artifact | batch | `bench/harrier-verdict.json` (Phase 23) | exact |
| `.planning/phases/24-…/bench/breadcrumb-verdict.json` (NEW) | data artifact | batch | `bench/harrier-verdict.json` (Phase 23) | exact |
| `src/sif/models/download.py` (MODIFIED) | service | file-I/O | itself (canonical-dir + manifest refactor) | exact |
| `src/sif/cli/commands/pull.py` (MODIFIED) | controller | request-response | itself (hidden deprecated alias) | exact |
| `src/sif/cli/main.py` (MODIFIED) | config / bootstrap | request-response | itself (command registration + migration) | exact |
| `src/sif/indexing/embed_writer.py` (MODIFIED) | service | file-I/O, batch | itself (`embed_document`) | exact |
| `src/sif/cli/commands/index.py` (MODIFIED) | controller | request-response | itself (`embed_cmd` chunker call site) | exact |
| `src/sif/config/settings.py` (MODIFIED, conditional) | config | — | itself (chunk/model fields) | exact |
| `tests/unit/models/test_download.py` (REWRITE) | test | file-I/O | itself (bug-pinning tests replaced) | exact |
| `tests/unit/cli/test_pull.py` (EXTEND) | test | request-response | itself | exact |
| `tests/unit/indexing/test_embed_writer.py` (EXTEND) | test | batch | itself | exact |
| `tests/test_docs.py` (EXTEND) | test | docs | itself | exact |
| `tests/test_ci_workflows.py` (EXTEND) | test | docs | itself | exact |
| `scripts/generate_cli_ref.py` (MODIFIED, conditional) | generator | transform | itself (`traverse_commands`) | exact |
| `scripts/generate_config_ref.py` (MODIFIED, conditional) | generator | transform | itself (`SECTIONS`) | exact |
| `docs/cli-reference.md`, `docs/configuration.md` (REGENERATED) | docs (generated) | transform | themselves via `make docs-generate` | exact |
| `docs/installation.md` (REWRITE) | docs | — | itself + `README.md` install section | exact |
| `README.md` (MODIFIED) | docs | — | itself (install section) | exact |
| `docs/quickstart.md` (MODIFIED) | docs | — | itself (## Installation) | exact |
| `docs/models.md` (MODIFIED) | docs | — | itself (append `## Model Management`) | exact |
| `docs/index.md` (MODIFIED) | docs | — | itself (`## Installation`) | exact |
| `docs/benchmarking.md` (MODIFIED) | docs | — | itself (`## CORR-04` / Phase 23 sections) | exact |
| `docs/migration.md` (MODIFIED, conditional) | docs | — | itself (`### Data Paths`) | exact |

## Pattern Assignments

### `scripts/chunk_sweep.py` and `scripts/breadcrumb_eval.py` (runbook, batch)

**Analog:** `scripts/harrier_eval.py` (1,888 lines; Phase 23 stage machine — copy its pure helpers, not its two-arm model gate).

**Module header / stdlib-only import discipline** (`scripts/harrier_eval.py:1-100`):

```python
#!/usr/bin/env python3
"""Two-arm Harrier vs Qwen3 evaluation runbook (Phase 23, MODEL-01/MODEL-02).

... Every ``sif`` stage is an explicit argv-list subprocess under its own per-arm
environment: ``get_settings()`` is process-cached, so an in-process arm switch
would silently measure the wrong model (research Pitfall 8).

This module is stdlib-only at import time; ``sif`` imports are deferred into
the probe, identity, and preflight helpers so ``--dry-run`` works without the
embedding stack.
"""
from __future__ import annotations
# stdlib only: argparse, hashlib, importlib.metadata, json, os, platform,
# shutil, sqlite3, subprocess, sys, time, pathlib, dataclasses, datetime
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCRATCH_ROOT = PROJECT_ROOT / ".planning" / "tmp" / "phase-23"
ARTIFACT_PATH = PROJECT_ROOT / ".planning" / "phases" / "23-harrier-gated-evaluation" / "bench" / "harrier-verdict.json"
QWEN3_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
EMBEDDING_DIM = 1024
MAX_TOKENS = 512
BATCH_SIZE = 32
PINNED_ENV = ("SIF_EMBEDDING_DIM", "SIF_MAX_TOKENS", "SIF_BATCH_SIZE", "SIF_CHUNK_SIZE", "SIF_CHUNK_OVERLAP")
PINNED_RANKING_ENV = {"SIF_RRF_K": "60", "SIF_BM25_WEIGHT": "1.0", "SIF_VECTOR_WEIGHT": "1.0", "SIF_RERANK_CANDIDATE_LIMIT": "20"}
REMOVED_ENV = ("SIF_MODEL_PATH", "SIF_DB_PATH", "SIF_API_BASE", "SIF_API_KEY", *PROMPT_ENV)
```

**Arm spec / stage-command data model** (`scripts/harrier_eval.py:103-120`):

```python
@dataclass(frozen=True)
class ArmSpec:
    """One evaluation arm: its backend, model, and isolated scratch DB."""
    name: str
    model_type: str
    model_name: str
    db_path: Path

@dataclass(frozen=True)
class ArmCommand:
    """One stage command: a stage label, argv list, and per-arm env."""
    stage: str
    argv: list[str]
    env: dict[str, str]
```

**Per-arm env pinning** (`scripts/harrier_eval.py:159-187`) — for the sweep, replace the
model fields with a single fixed Qwen3 identity and make `chunk_size`/`chunk_overlap` arm
fields:

```python
def build_arm_env(base_env: Mapping[str, str], arm: ArmSpec) -> dict[str, str]:
    env = dict(base_env)
    for key in REMOVED_ENV:
        env.pop(key, None)          # removed, never blanked
    env.update({
        "SIF_MODEL_TYPE": arm.model_type,
        "SIF_MODEL_NAME": arm.model_name,
        "SIF_EMBEDDING_DIM": str(EMBEDDING_DIM),
        "SIF_MAX_TOKENS": str(MAX_TOKENS),   # held fixed at 512 for every arm
        "SIF_BATCH_SIZE": str(BATCH_SIZE),
        "SIF_CHUNK_SIZE": str(arm.chunk_size),
        "SIF_CHUNK_OVERLAP": str(arm.chunk_overlap),
        "SIF_CACHE_EMBEDDINGS": "1",
    })
    env.update(PINNED_RANKING_ENV)
    return env
```

**Ordered argv-only stage table** (`scripts/harrier_eval.py:190-254`) — the sweep arm keeps
this exact stage order; only `index embed` is required to re-chunk (Pitfall 1):

```python
base = [python, "-m", "sif.cli.main", "-q", "--index", str(arm.db_path)]
# per corpus root: collection add <root> --name phase23-<n>
# index update
# index embed --force --chunk-strategy auto
# eval --personal --all --compare <saved_run> --json
# (baseline arm instead: eval --personal --all --require-language en --require-language zh --json)
```

**Resumable scope-keyed stage machine** (`scripts/harrier_eval.py:440-547`) — copy verbatim,
extending `STAGES` with per-arm names:

```python
STAGES = ("env_preflight", "arm_a_index", "adequacy", "arm_a_embed", "arm_a_probe",
          "arm_a_eval", "arm_b_index", "arm_b_identity", "arm_b_embed", "arm_b_probe",
          "arm_b_eval", "verdict", "artifact")

def scope_key(scope: Mapping[str, Any]) -> str:
    roots = sorted(str(root) for root in scope.get("corpus_roots", []))
    lines = [*roots, str(scope.get("corpus_label", ""))]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:16]

def save_run_state(path: Path, state: Mapping[str, Any]) -> None:
    target = Path(path)
    payload = json.dumps(state, indent=2, sort_keys=True) + "\n"
    temporary = target.with_name(f"{target.name}.tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(target)
```

**Cost capture** (`scripts/harrier_eval.py:804-869`):

```python
def collect_arm_costs(db_path, cache_db_path, wall_seconds, *, cache_model_id=None, cache_rows_before=None):
    counts = _db_counts(db_path)               # documents, document_chunks, embedded_documents
    cache_rows_after = _cache_rows(cache_db_path, cache_model_id)  # read-only sqlite URI
    cache_hits = None
    if cache_rows_before is not None:
        added = max(0, cache_rows_after - cache_rows_before)
        cache_hits = max(0, counts["document_chunks"] - added)
    return {"documents": ..., "chunks": ..., "embedded_documents": ...,
            "embed_wall_seconds": round(float(wall_seconds), 3),
            "cache_rows_before": cache_rows_before, "cache_rows_after": cache_rows_after,
            "cache_hits": cache_hits}
```

**Committed artifact guard + scratch safety** (`scripts/harrier_eval.py:1000-1084`) — the
sweep artifact must refuse to overwrite a different grid/decision/corpus without `--force`:

```python
def write_committed_artifact(artifact: Mapping[str, Any], *, force: bool = False) -> Path:
    target = Path(ARTIFACT_PATH)
    existing = ...  # json.loads if file exists
    if existing is not None:
        old_identity = _envelope_identity(existing)   # (decision, corpus fingerprint)
        new_identity = _envelope_identity(artifact)
        if not force and old_identity != new_identity:
            raise RuntimeError(f"refusing to overwrite {target}: ... pass --force to replace it")
    return write_artifact(target, artifact)

def assert_within_scratch(path: Path, scratch_root: Path) -> Path:
    target, root = Path(path).resolve(), Path(scratch_root).resolve()
    if root in {Path("/"), Path.home()}:
        raise ValueError(f"refusing to use {root} as a scratch root")
    if target != root and not target.is_relative_to(root):
        raise ValueError(f"refusing path outside the scratch root: {target}")
    return target
```

**CLI entry point** (`scripts/harrier_eval.py:1790-1888`): argparse with `--corpus`
(repeatable), `--scratch-root`, `--corpus-label`, `--dry-run`, `--keep-arms`,
`--preflight-only`, `--force`, `--json`, and `main(argv) -> int` exits `3` for
insufficient evidence. Reuse that shape for `chunk_sweep.py` (add `--arm`/grid) and
`breadcrumb_eval.py` (single arm + duplicate metrics). Follow Pitfall 10: select the
candidate on the tuning split, then apply the gate to that single candidate on held-out;
report all arms' gates as diagnostic.

**Sweep-specific additions (no existing analog — draw from research):**
- Assert one shared Qwen3 identity across every arm (`verify_arm_identity` at
  `scripts/harrier_eval.py:373-391` is the template).
- Record per-arm `documents/chunks/vectors/embed_wall_seconds/cache_hits`, plus grid,
  corpus fingerprint `b5d50ce0c696ab3d`, `min_heldout_for_epsilon_win=101`.
- If the Phase 23 saved run is missing, regenerate the 512/128 baseline first.

---

### `src/sif/search/tuning_verdict.py` (policy, transform)

**Analog:** `src/sif/search/embedder_verdict.py` — the exact structural precedent for a
pure Phase-18 gate policy module.

**Module contract** (`src/sif/search/embedder_verdict.py:1-42`):

```python
"""Pure two-sided embedder verdict rule (Phase 23, MODEL-02).

No Click, Rich, embedding, or database imports: this module is a policy over
Phase 18 gate values, unit-testable without loading a model. ``GateResult``
already bundles the N floor, the 95% CI, the rounded 0.01 tie rule, and the
strict 1/N noise-floor veto, so nothing here re-derives bootstrap or gate
arithmetic (D-06, T-23-04).
"""
from sif.search.benchmark import EPSILON
from sif.search.personal_bench import SUPPRESS_BELOW

DECISION_ADOPT = "adopt-harrier"
DECISION_KEEP = "keep-qwen3"
DECISION_INSUFFICIENT = "insufficient-evidence"
MIN_HELDOUT_FOR_EPSILON_WIN = 101
LANGUAGE_FLOOR = -EPSILON
```

**Frozen decision record with literal rule booleans + reasons**
(`src/sif/search/embedder_verdict.py:45-93`): copy this `VerdictDecision` shape; rename to a
tuning verdict (e.g. `adopt-chunking` / `keep-default` / `insufficient-evidence`), keep
`min_heldout_for_epsilon_win` in the payload. The `to_dict()` fixed key order is what the
committed artifact consumes.

**Gate-input reader + decision core** (`src/sif/search/embedder_verdict.py:96-108`,
`153-228`):

```python
def _gate_value(gate: Any, field_name: str) -> Any:
    if isinstance(gate, Mapping):
        if field_name not in gate:
            raise ValueError(f"Gate payload is missing required field {field_name!r}")
        return gate[field_name]
    value = getattr(gate, field_name, _MISSING)
    if value is _MISSING:
        raise ValueError(f"Gate must be a GateResult or a mapping carrying {field_name!r}; ...")
    return value

# winner requires: adequate N, overall winner, per-leg floor
if not adequate:
    decision = DECISION_INSUFFICIENT
elif overall_winner and floor_ok:
    decision = DECISION_ADOPT
else:
    decision = DECISION_KEEP
    reasons.append("overall held-out winner is false")   # each false literal gets a reason
```

**Do not re-derive statistics:** call `personal_bench.noise_gate` /
`personal_bench.GateResult` (fields at `src/sif/search/personal_bench.py:374-417`;
`noise_gate` at `:1882-1944`) and `EPSILON = 0.01` at `src/sif/search/benchmark.py:33`.
For QUAL-03, add a duplicate-signal veto to the same decision record: reject if the
breadcrumb's body/long leg does not improve even when the title leg does (Pitfall 5).

---

### `src/sif/indexing/breadcrumb.py` (utility, transform)

**Analog:** `src/sif/indexing/chunker.py` — pure, regex-driven, no I/O, fully docstringed
helper in the same package.

**Style/import pattern** (`src/sif/indexing/chunker.py:1-20`):

```python
"""Document chunking strategies."""
from __future__ import annotations
import re
from abc import ABC, abstractmethod

from sif.core.models import DocumentChunk

CHARS_PER_TOKEN = 4

def token_size_to_chars(tokens: int) -> int:
    """Convert a token budget to an approximate character count."""
    return max(1, int(tokens) * CHARS_PER_TOKEN)
```

**Heading parsing** (`src/sif/indexing/chunker.py:104`): reuse the same `^(#{1,6}\s+.+)$`
shape (`re.compile(r"^(#{1,6}\s+.+)$", re.MULTILINE)`), but the breadcrumb builder must
strip the `#` run and derive the path from the ordered chunk sequence + `doc.title`
(research Pattern 2 sketch; do **not** use `start_pos`, which is section-relative for
sub-chunks — `src/sif/indexing/chunker.py:128-136`).

**Contract to encode:** title + most recent heading of any level; no heading → title-only;
empty title → content-only; separator `" > "`; prepend `f"{path}\n\n{chunk.content}"`.
Return a parallel `list[str]` — never mutate `DocumentChunk.content`.

**Storage-neutral guardrail:** `DocumentChunk` has no heading-path field
(`src/sif/core/models.py:162-186`), and `EmbedderIdentity` has no embed-text mode
(`src/sif/embedding/identity.py:118-150`). One fresh DB per arm remains mandatory.

---

### `src/sif/cli/commands/models.py` (controller, request-response)

**Analog A:** `src/sif/cli/commands/pull.py` — the existing model-download command and its
HF→ModelScope fallback; becomes the deprecated alias target.
**Analog B:** `src/sif/cli/commands/eval.py:969-1035` — a Click group with flags, a long
help docstring, and `--json` output.

**Import-guard + ClickException pattern** (`src/sif/cli/commands/pull.py:12-22, 63-84`):

```python
try:
    from huggingface_hub import hf_hub_download
except ImportError:  # pragma: no cover
    hf_hub_download = None  # type: ignore[misc,assignment]

try:
    from modelscope import snapshot_download
except ImportError:  # pragma: no cover
    snapshot_download = None  # type: ignore[misc,assignment]

console = Console()
...
try:
    return _download_from_hf(repo_id, filename, target_cache)
except Exception as hf_err:
    console.print(f"[yellow]HuggingFace failed: {hf_err}[/yellow]")
    try:
        return _download_from_modelscope(repo_id, filename, target_cache)
    except ImportError:
        raise click.ClickException(f"HuggingFace failed: {hf_err}. ModelScope not installed.") from hf_err
    except Exception as ms_err:
        raise click.ClickException(f"Download failed: HF={hf_err}, MS={ms_err}") from ms_err
```

**Group + option pattern** (`src/sif/cli/commands/eval.py:969-1035`): `@click.group("models")`,
then `@models_group.command("pull")` / `@models_group.command("status")`; `--json` is a
plain `is_flag=True` option; `--force` mirrors `index embed` (`src/sif/cli/commands/index.py:252`).

**Status rendering:** follow `main.py` status's degrade-never-fail table
(`src/sif/cli/main.py:189-231`) with Rich `Table(title=..., add_column(..., style=...))`,
but branch on `sys.stdout.isatty()` and emit `json.dumps(...)` or plain
`click.echo(f"{section}.{key}: {value}")` in non-TTY (research Pattern 4 / Pitfall 9).
`bench.py`'s stdout purity rule applies: `console_err = Console(stderr=True)` for
deprecation notices (`src/sif/cli/commands/bench.py:51-55`).

**Status data sources (verified APIs):**
- Configured identity: `build_settings_identity(settings, scheme)` at
  `src/sif/embedding/identity.py:334-352` (no model load).
- Persisted identity: `read_identity(conn)` at `src/sif/embedding/identity.py:385-392`
  (`None` when absent/corrupt); `IdentityCheck` at `:209-225`.
- Backend probe: `importlib.util.find_spec(...)` (no in-repo `find_spec` precedent) and the
  degrade-never-fail bool probe style from `VectorSearcher._check_vec_extension`
  (`src/sif/search/vector.py:65-71`). Do **not** download or import the model.
- Dimension: `settings.embedding_dim` + `schema_embedding_dim(conn)`
  (`src/sif/embedding/identity.py:355-369`).

**No new runtime dependency** (D-07); `modelscope`/`huggingface_hub` stay optional imports.

---

### `src/sif/models/download.py` (service, file-I/O)

**Analog:** itself; Phase 24 replaces the md5/non-empty cache check with a canonical
directory + SHA-256 manifest + atomic replace.

**Current bug surface to replace** (`src/sif/models/download.py:18-98`):

```python
DEFAULT_MODELS = types.MappingProxyType({
    "embedding": {"model_id": "iic/gte_Qwen2-7B-instruct", ...},
    "reranker":  {"model_id": "iic/gte_Qwen2-7B-instruct", ...},
    "query_expansion": {"model_id": "qwen/Qwen2.5-0.5B-Instruct", ...},
})
...
if cache_dir is None:
    cache_dir = Path.home() / ".sif" / "models"
self.cache_dir = Path(cache_dir).expanduser().resolve()
self.cache_dir.mkdir(parents=True, exist_ok=True)
...
model_hash = hashlib.md5(model_id.encode()).hexdigest()[:8]
model_cache_dir = self.cache_dir / model_hash
if not force and model_cache_dir.exists() and any(model_cache_dir.iterdir()):
    logger.info(f"Using cached model: {model_id}")
    return model_cache_dir
```

**Target behavior (research Pattern 3):**
- Default cache dir `Settings.get_cache_dir() / "models"` (see
  `src/sif/config/settings.py:412-421`); accept an explicit `cache_dir` for tests.
- Canonical target `<cache>/models/<owner>/<name>` (ModelScope writes
  `<cache>/<owner>/<name___>`; recognize both and migrate legacy `~/.sif/models`).
- Download into a sibling temp dir, write `.sif-model.json` manifest, atomically replace.
- A cache hit requires manifest presence and every file's size + SHA-256 match; a
  non-empty directory without a manifest is **not** a hit.
- `--force` bypasses the manifest check.
- Keep `is_quiet()`/`suppress_output()` wrapping (`src/sif/models/download.py:89-93`;
  helpers at `src/sif/utils/logging.py:32,73`).

**SHA-256 file helper precedent** (`src/sif/embedding/embedder.py:92-101`):

```python
def _file_sha256(path: Path) -> str | None:
    """Return ``sha256:<hex>`` over a model file, read once in 1 MiB chunks."""
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as model_file:
            for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return f"sha256:{digest.hexdigest()}"
```

Use SHA-256, never md5, for integrity (security V6). Pin `revision="master"` in the
registry; record the resolved revision in the manifest but do not claim immutability
(Pitfall 7).

**`DEFAULT_MODELS` correction (D-09):** embedding `Qwen/Qwen3-Embedding-0.6B` (ModelScope,
1024-dim), reranker `Qwen/Qwen3-Reranker-0.6B`, query expansion
`qwen/Qwen2.5-0.5B-Instruct`. Keep `types.MappingProxyType`.

---

### `src/sif/cli/commands/pull.py` (controller, request-response)

**Analog:** itself. Convert `@click.command("pull")` to `hidden=True` and route its body to
the new `models pull` handler; emit a stderr deprecation notice (one release, D-06).

**Existing invocation contract** (`src/sif/cli/commands/pull.py:87-111`):

```python
@click.command("pull")
@click.argument("model_spec")
@click.option("--cache-dir", type=click.Path(), help="Custom cache directory")
@click.pass_context
def pull_cmd(_ctx: click.Context, model_spec: str, cache_dir: str | None) -> None:
    """Download a GGUF model file."""
    target_cache = (Path(cache_dir).expanduser().resolve() if cache_dir
                    else Path.home() / ".sif" / "models")
    ...
    if not downloaded.exists() or downloaded.stat().st_size == 0:
        raise click.ClickException("Downloaded file is missing or empty.")
```

Keep the GGUF/URL path but add a timeout (Pitfall 14) and optional hash check when the
spec supplies one. Deprecation text goes through a **stderr** console, not stdout.

**Generator/test constraint:** `scripts/generate_cli_ref.py:90-108` traverses every
command with no hidden check, and `tests/test_docs.py:435-447` also collects all commands.
If `pull` becomes hidden, both must skip `if cmd.hidden: continue` (otherwise the
generated reference and the docs gate still require/show `sif pull`).

---

### `src/sif/cli/main.py` (config/bootstrap, request-response)

**Analog:** itself.

**Registration pattern** (`src/sif/cli/main.py:94-120`): add
`from sif.cli.commands.models import models_group` to the deferred import block and
`cli.add_command(models_group)` in the same style. `sif pull` keeps its existing
`cli.add_command(pull_cmd)` (now hidden).

**Legacy path migration pattern** (`src/sif/cli/main.py:287-299`) — reuse this shape in
`ModelDownloader` for `~/.sif/models` → canonical cache (note current code migrates
docsift→sif; do not conflate the two):

```python
old_model_dir = Path.home() / ".local" / "share" / "docsift" / "models"
new_model_dir = Path.home() / ".local" / "share" / "sif" / "models"
if old_model_dir.exists() and not new_model_dir.exists():
    new_model_dir.parent.mkdir(parents=True, exist_ok=True)
    old_model_dir.rename(new_model_dir)
    console_err.print("[green]Migrated: ...[/green]")   # stderr, never stdout
```

---

### `src/sif/indexing/embed_writer.py` (service, file-I/O / batch)

**Analog:** itself; the breadcrumb changes only the embedding input, not persistence.

**Current seam** (`src/sif/indexing/embed_writer.py:170-233`):

```python
chunks = self._chunk_document(doc)
...
for batch_index, batch in enumerate(_batches(chunks, self._batch_size)):
    response = self._manager.embed_documents([chunk.content for chunk in batch])   # line 185
    ...
with self._conn:
    self._chunk_repo.delete_by_document(doc.id)
    self._searcher.delete_embeddings_by_document(doc.id)
    for chunk in chunks:
        chunk.document_id = doc.id
        self._chunk_repo.create(chunk)                                            # line 219
    self._searcher.add_embeddings_batch([...])                                    # lines 220-225
```

**Required modification:** compute `embed_texts` once per document
(`breadcrumb_embed_texts(doc.title, chunks)` when enabled, else `[c.content ...]`) and pass
`batch_embed_texts[batch_start:batch_end]` at line 185. Persist `chunk.content` unchanged
(lines 218-225). Keep the delete-before-insert transaction and the identity claim
(`_claim_identity_in_transaction`, lines 235-268) untouched. Default off must keep the
byte-identical embed path (D-05).

**Chunker factory call site** (`src/sif/cli/commands/index.py:399-403`) — the Settings
knobs and chars-per-token conversion live here:

```python
chunker = create_chunker(
    chunk_strategy,
    max_chunk_size=token_size_to_chars(settings.chunk_size),
    overlap=token_size_to_chars(settings.chunk_overlap),
)
```

If a `embed_breadcrumb: bool = False` setting is adopted (research Open Question 3), read it
here and pass a flag into `StreamingEmbedWriter`; add `SIF_EMBED_BREADCRUMB` and the field
description the same way as `chunk_size` (`src/sif/config/settings.py:211-223`). A new
Settings field must be added to `scripts/generate_config_ref.py` `SECTIONS`
(`:150-208`) and the docs regenerated (Pitfall 8).

---

### `tests/unit/scripts/test_chunk_sweep.py` and `tests/unit/scripts/test_breadcrumb_eval.py` (test, batch)

**Analog:** `tests/unit/scripts/test_harrier_eval.py`.

**Structure to copy:** module-level identity/gate factories
(`_qwen3_identity`, `_gate_payload` at `:70, :760`), then classes:
`TestDryRun`, `TestCorpusRootsGuard`, `TestIdentityGate`, `TestProbe`, `TestStageMachine`.
Key assertions to port:
- every command is an argv list with `-q` and `--index` (`:124`);
- arm env removes API keys/prompt overrides (`:138`);
- arms pin identical chunk/batch values (`:159`);
- baseline eval requires both languages; candidate eval compares without resampling
  (`:215, :223`);
- `--dry-run` invokes no subprocess (`:238`);
- duplicate/parent-child corpus roots refused before any command is built (`:254-320`);
- stage resume/discard on scope-key change (`:442-560`);
- `parse_json_stdout` rejects identity-guard text / nonzero exit / non-JSON (`:570-597`).

Add sweep-specific tests: grid contains 512/128; every arm fixes `SIF_MAX_TOKENS=512` and
Qwen3; artifact is aggregate-only (no query text, no absolute paths); selection rule
(tuning-select → held-out-confirm) recorded. Follow Wave 0 list in RESEARCH.

---

### `tests/unit/search/test_tuning_verdict.py` (test, transform)

**Analog:** `tests/unit/search/test_embedder_verdict.py`.

**Gate fixture pattern** (`tests/unit/search/test_embedder_verdict.py:29-56`):

```python
def _gate(baseline: float, current: float, n: int) -> GateResult:
    return noise_gate([baseline] * n, [current] * n)

def _payload(overall: GateResult, languages: dict[str, GateResult]) -> dict[str, object]:
    ...
```

**Cases to port/adapt** (`:123-269`): `n100` +0.01 ties its own 1/N floor; `n101` +0.02
clears it; CI containing zero never adopts; language/leg regression vetoes a winning
overall gate; absent/thin evidence is `insufficient-evidence`; malformed payloads raise
named `ValueError`s; every rejection names a reason and adopt is clean. For QUAL-03 add:
title-leg-only gain is rejected as duplicate signal; body-leg gain can adopt.

---

### `tests/unit/indexing/test_breadcrumb.py` (test, transform)

**Analog:** `tests/unit/indexing/test_chunker.py` (pure case classes, no DB/model).

**Style** (`tests/unit/indexing/test_chunker.py:18-23`):

```python
def _chunk_fields(chunks: list[DocumentChunk]) -> list[tuple[str, int, int, int]]:
    return [(c.content, c.sequence, c.start_pos, c.end_pos) for c in chunks]

class TestChunkerStrategies:
    def test_markdown_splits_on_heading_boundaries(self) -> None: ...
```

Port the parametrized/edge-case discipline. Required cases (Wave 0): H1-first doc, H2-first
doc, H1-per-section doc, no headings, CJK headings, empty title, title == heading (dedupe),
separator/depth, and stored content byte-identical to input chunks.

---

### `tests/unit/cli/test_models.py` (test, request-response)

**Analog:** `tests/unit/cli/test_pull.py` (CliRunner + `patch`) and
`tests/unit/cli/test_status.py` (status-table sections via `CliRunner`).

**Pattern** (`tests/unit/cli/test_pull.py:14-38`):

```python
runner = CliRunner()
with patch("sif.cli.commands.pull.hf_hub_download", return_value=fake_path) as mock_hf:
    result = runner.invoke(pull_cmd, ["--cache-dir", cache_dir, "owner/repo/model.gguf"])
assert result.exit_code == 0
assert "Downloaded to" in result.output
mock_hf.assert_called_once_with(repo_id=..., filename=..., cache_dir=..., local_files_only=False)
```

**JSON/non-TTY pattern** (`tests/unit/cli/test_eval.py:319-325`):
`result = runner.invoke(cli, [...])`, `payload = json.loads(result.stdout)`.

Cover: pull defaults/args/`--force`/non-TTY quiet; status configured vs stored identity
match/mismatch/dimension-mismatch/no-index/legacy; backend probe states; `--json` parse;
plain output with no Rich box characters; deprecation notice on `sif pull` goes to stderr.

---

### `tests/unit/models/test_download.py` (rewrite, file-I/O)

**Analog:** itself — rewrite the tests that pin the bug.

**Fixture pattern to keep** (`tests/unit/models/test_download.py:14-38`):

```python
@pytest.fixture
def modelscope_module() -> Generator[MagicMock, None, None]:
    injected_keys = ("modelscope", "modelscope.hub", "modelscope.hub.api")
    previous = {key: sys.modules.get(key) for key in injected_keys}
    module = MagicMock(); hub_api = MagicMock(); module.hub.api = hub_api
    sys.modules["modelscope"] = module; ...
    try:
        yield module
    finally:
        for key, value in previous.items(): ...   # remove only injected keys

@pytest.fixture
def downloader(tmp_path: Path) -> ModelDownloader:
    return ModelDownloader(cache_dir=tmp_path / "models")
```

**Delete/replace** `test_default_cache_dir_resolves_under_monkeypatched_home` (pins
`~/.sif/models`, `:44-54`), `test_download_uses_cached_nonempty_model_directory`
(pins the md5 bug, `:81-93`), and the md5-based force test (`:95-113`). New cases:
canonical `<cache>/models/<owner>/<name>`; manifest valid → no network; non-empty dir
without manifest → re-download; corrupt hash → re-download; `--force`; legacy
`~/.sif/models` and `<cache>/<owner>/<name___>` detection/migration; corrected
`DEFAULT_MODELS` values; atomic replace leaves no temp dir; missing `modelscope` remedy.

---

### `tests/test_docs.py` and `tests/test_ci_workflows.py` (extend, docs)

**Analog:** themselves.

**`DOCS_FILES` + skip + subcommand maps** (`tests/test_docs.py:21-45, 243-264`):

```python
DOCS_FILES = [Path("README.md"), Path("docs/index.md"), ... Path("docs/models.md")]
SKIP_COMMAND_PATTERNS = ["mcp http", "mcp daemon", "mcp stdio", "pull ", "index embed",
                         "pip install", "git clone", "git checkout", "bench "]
_SUBCOMMANDS = {..., "models": ["pull", "status"], ...}
```

**Add:** `docs/installation.md`, `docs/migration.md` (and `docs/quickstart.md` already
listed) to `DOCS_FILES`; `models` to `_SUBCOMMANDS`; hidden-command skipping in
`_collect_click_commands` (`:435-447`) if `sif pull` becomes hidden; a guard that
`docs/installation.md`/`docs/models.md` never name the old 7B `iic/gte_Qwen2-7B-instruct`
defaults; `uv tool install --torch-backend=cpu` presence in the install docs.

**CI-text assertion pattern** (`tests/test_ci_workflows.py:16-32, 159-166`): module
constants for paths (`INSTALLATION = DOCS_ROOT / "installation.md"`, `CPU_INDEX_URL = ...`)
and text-level assertions; extend for uv-first/CPU recipe/degradation-matrix claims.

---

### Docs (`README.md`, `docs/installation.md`, `docs/quickstart.md`, `docs/models.md`, `docs/index.md`, `docs/benchmarking.md`, `docs/migration.md`)

**Analog:** the existing hand-maintained docs; generator-owned
`docs/cli-reference.md` / `docs/configuration.md` must only be regenerated.

**README install block to correct** (`README.md:28-62`):

```markdown
### Recommended: uv tool install
uv tool install 'docsif[embed]'
`uv tool install` keeps SIF in an isolated environment ... On Linux, the embed install
resolves CPU-only torch from the explicit PyTorch CPU index declared in `pyproject.toml`
(`https://download.pytorch.org/whl/cpu`), so no CUDA stack is pulled in.
```

Replace the misleading `pyproject.toml` claim with the verified `uv tool install
--torch-backend=cpu 'docsif[embed]'` recipe (uv ≥ 0.9.19; local 0.13.7), and document the
BM25-only base + `uvx` fallback + degradation matrix (no embed extra → BM25; no
sqlite-vec → vector unavailable; Windows daemon refusal). Keep a pip section as secondary.

**`docs/installation.md`** currently is pip-first (`:10-49` "Method 1: Install from PyPI",
`:51-100` optional deps). Restructure to uv-first, keeping the extras table truthful
(`sentence-transformers>=5.4.1`, `torch`, `modelscope>=1.36.0`, `numpy>=1.24.0`,
`llama-cpp-python>=0.3.35`, `openai>=2.0.0`) and add the llama-cpp wheel-index recipe with
an explicit human-verification marker (Pitfalls 13, A1/A2/A11).

**`docs/quickstart.md`** `## Installation` (`:38-70`) and **`docs/index.md`**
`## Installation` (`:66-76`) repeat the pip-first block; update both.

**`docs/models.md`** is "Data Models" and ends with `## Related Documentation`
(`:514-518`); append a new `## Model Management` section (Open Question 5) linking
`installation.md` and `mcp-server.md`, after the generator-owned docs are regenerated.
Client config snippets (Claude Desktop/Code, plugin) live in `docs/mcp-server.md`
(`:254-305` "Installing the Claude Code plugin", `:305-325` "Manual MCP configuration") —
link rather than duplicate.

**`docs/benchmarking.md`** sections (`## CORR-04 Title-Aware Ranking` at `:227`, `### CJK
scope and duplication caveat` at `:255`, `## Embedder Substitution Evidence` at `:259`):
add `## Chunk-Size/Overlap Sweep (QUAL-02)` and `## Title-Breadcrumb Experiment (QUAL-03)`
with a per-arm table (documents/chunks/vectors/embed seconds/cache hits/gate) and the
verdict or recorded rejection. Reuse the prose style at `:265-274` (decision first, corpus
fingerprint, adequacy, `min_heldout_for_epsilon_win = 101`, identity table, aggregate-only
artifact citation).

**`docs/migration.md`** (`### Data Paths` at `:46-53`, "Model cache: Auto-migrates on first
`sif` run") gets the canonical cache path/migration note if the legacy path is retired.

**Generated docs workflow** (`Makefile:73-76`):

```make
docs-generate:
	@echo "Regenerating CLI and configuration reference docs..."
	python scripts/generate_cli_ref.py
	python scripts/generate_config_ref.py
```

After adding commands/settings: run `make docs-generate`, commit the regenerated
`docs/cli-reference.md` / `docs/configuration.md`, and run `pytest tests/test_docs.py`.
Add `embed_breadcrumb` to `scripts/generate_config_ref.py` `SECTIONS` (`:150-208`) if the
setting lands; a missing SECTIONS entry is silently undocumented.

## Shared Patterns

### Phase 18 gate discipline (QUAL-02, QUAL-03, all defaults)
**Source:** `src/sif/search/personal_bench.py` (`GateResult` `:374-417`, `noise_gate` `:1882-1944`, `compare_saved_run` `:2248-2292`, `require_matching_corpus` `:2162-2179`), `src/sif/search/benchmark.py:33` (`EPSILON = 0.01`).
**Apply to:** `tuning_verdict.py`, both runbooks, both artifact writers.
Never re-derive bootstrap/CI/1/N; call the instrument. Artifacts record
`min_heldout_for_epsilon_win=101` and the corpus scope; a no-win is a recorded outcome.

### Atomic JSON writes + sorted keys
**Source:** `scripts/harrier_eval.py:510-530` (`save_run_state`, `write_json`).
**Apply to:** run states, both committed artifacts. Write `.tmp` then `replace()`;
`json.dumps(..., indent=2, sort_keys=True) + "\n"`.

### Failure/quiet discipline
**Source:** `scripts/harrier_eval.py:127-129` (`_emit_err`), `src/sif/utils/logging.py:32,73` (`is_quiet`, `suppress_output`), `src/sif/cli/commands/bench.py:51-55` (stderr console).
**Apply to:** runbooks (stderr guard lines), `models pull` (suppress ModelScope progress),
`models status`plain/JSON in pipes), `sif pull` deprecation (stderr).

### CLI error convention
**Source:** `src/sif/cli/main.py:42-46`, `src/sif/cli/commands/pull.py:75-84`.
**Apply to:** `models.py` — wrap validation/OSError/DB errors in
`click.ClickException(str(e))`; never leak a raw traceback for user-facing errors.

### Cache/manifest hashing
**Source:** `src/sif/embedding/embedder.py:92-101` (`_file_sha256`, 1 MiB chunks).
**Apply to:** `models/download.py` manifest and optional GGUF hash. SHA-256 only; never md5.

### Identity read/write
**Source:** `src/sif/embedding/identity.py` (`build_settings_identity` `:334-352`, `read_identity` `:385-392`, `IdentityCheck` `:209-225`, `write_identity` `:395-400`).
**Apply to:** `models status` (configured vs stored identity, no model load) and the
runbooks' per-arm identity assertion.

### Corpus isolation
**Source:** `scripts/harrier_eval.py:1041-1084` (`assert_within_scratch`, `cleanup_arms`).
**Apply to:** both runbooks — one file-backed DB per arm under a gitignored scratch root,
never reuse a Phase 23 arm DB for a different chunk/breadcrumb contract (Pitfall 4).

## No Analog Found

Files with no close in-repo match (planner should use RESEARCH.md patterns):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/sif/indexing/breadcrumb.py` (heading-path builder) | utility | transform | No title/heading-path builder exists; `chunker.py` supplies the style and regex, not the algorithm. Use research Pattern 2 sketch. |
| `src/sif/cli/commands/models.py` `status` backend probe | controller | request-response | No `importlib.util.find_spec` probe exists in `src/sif`; only sqlite-vec runtime probes (`vector.py:65-71`). Use `find_spec` (no download/import). |
| `.sif-model.json` manifest verifier | service | file-I/O | No manifest concept in the repo; use research Pattern 3 / `verify_manifest` sketch + `_file_sha256`. |

## Metadata

**Analog search scope:** `scripts/`, `src/sif/{search,indexing,models,cli,config,embedding,utils}/`,
`tests/unit/{scripts,search,indexing,models,cli}/`, `tests/`, `docs/`, `Makefile`,
`scripts/generate_*.py`.
**Files scanned:** 48 (21 read in full or targeted ranges; 27 inspected via grep/headings).
**Tracked-source check:** every named analog verified with `git ls-files --`; no
`.gsd/capabilities/` mirror paths used.
**Pattern extraction date:** 2026-11-17.
