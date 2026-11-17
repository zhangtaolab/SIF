#!/usr/bin/env python3
"""One-arm title-breadcrumb evaluation runbook (Phase 24, QUAL-03).

The breadcrumb is an embed-text-only overlay (D-04): enabling
``SIF_EMBED_BREADCRUMB`` changes only each chunk's embedding input, so stored
chunk content, chunks FTS, snippets, and BM25 stay byte-identical. This runbook
builds a single isolated, file-backed arm at the shipped chunk default
(512/128) with the breadcrumb on, asserts the arm's persisted embedder identity
equal to the Phase 23 baseline's ``modelscope:Qwen/Qwen3-Embedding-0.6B``, and
evaluates it per leg against that baseline.

Why the identity gate is mandatory: ``EmbedderIdentity`` records the vector
space but not the embed-text contract, and vectors from a different backend
are incompatible. A sentence-transformers arm (or a prompted one) would
produce a different ``cache_model_id`` and turn a backend swap into a fake
breadcrumb delta (research Pattern 2, Pitfall 4, T-24-13).

The default changes only on an overall held-out win plus a winning body leg
(D-04, D-05). The already-indexed title makes a literal H1 breadcrumb mostly
duplicate signal — 467/498 baseline documents have an H1 equal to their title
and 45.9% of chunks are sub-chunks without a heading — so a gain confined to
the title leg is rejected with numbers (research Pitfall 5).

``get_settings()`` is process-cached, so every stage runs in its own argv-list
subprocess under the arm environment. This module is stdlib-only at import
time; ``sif`` imports are deferred into the probe, baseline, and duplicate
helpers so ``--dry-run`` works without the embedding stack.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any


try:  # Running as ``python scripts/breadcrumb_eval.py``: scripts/ is sys.path[0].
    import chunk_sweep
    import harrier_eval
except ImportError:  # Imported as ``scripts.breadcrumb_eval`` or spec-loaded.
    from scripts import chunk_sweep, harrier_eval

if TYPE_CHECKING:
    from sif.core.models import DocumentChunk
    from sif.search.tuning_verdict import BreadcrumbDecision


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCRATCH_ROOT = PROJECT_ROOT / ".planning" / "tmp" / "phase-24-breadcrumb"
ARTIFACT_PATH = (
    PROJECT_ROOT
    / ".planning"
    / "phases"
    / "24-tuning-models-ux-install-docs"
    / "bench"
    / "breadcrumb-verdict.json"
)
ARM_NAME = "breadcrumb-512-128"
BASELINE_ARM_NAME = "baseline-512-128"
MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
MODEL_TYPE = "modelscope"
QWEN3_CACHE_MODEL_ID = "modelscope:Qwen/Qwen3-Embedding-0.6B"
EMBEDDING_DIM = 1024
MAX_TOKENS = 512
BATCH_SIZE = 32
CHUNK_SIZE = 512
CHUNK_OVERLAP = 128
COLLECTION_PREFIX = "phase24b"
SELECTION_RULE = "overall-heldout-plus-body-leg-veto"
EXPECTED_CORPUS_FINGERPRINT = "b5d50ce0c696ab3d"
MIN_HELDOUT_FOR_EPSILON_WIN = 101
LIMITATION = (
    "The Phase 23 curated corpus has N=56 held-out queries, below the 101 needed "
    "for a 0.01 mean-delta win, so insufficient-evidence is the expected "
    "outcome until a larger corpus is supplied; the result is corpus-scoped."
)
STATE_FILE_NAME = "run-state.json"
STAGE_TIMEOUT_SECONDS = 6 * 60 * 60
STAGE_SUFFIXES = ("index", "embed", "identity", "eval")
STAGE_PREFIXES = ("arm", "baseline")
FINAL_STAGES = ("verdict", "artifact")
IDENTITY_KEYS = chunk_sweep.IDENTITY_KEYS
# Reuse the sweep's removals; ``SIF_EMBED_BREADCRUMB`` is removed here too and
# then re-pinned per arm, so an inherited value can never choose the mode.
REMOVED_ENV = chunk_sweep.REMOVED_ENV
PINNED_RANKING_ENV = chunk_sweep.PINNED_RANKING_ENV


@dataclass(frozen=True)
class BreadcrumbArmSpec:
    """One breadcrumb arm (or its baseline twin) and its isolated scratch DB."""

    name: str
    chunk_size: int
    chunk_overlap: int
    embed_breadcrumb: bool
    db_path: Path


def _now() -> str:
    """UTC timestamp for run-state records."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_arm_spec(scratch_root: Path, *, baseline: bool = False) -> BreadcrumbArmSpec:
    """Build the single breadcrumb arm, or the fresh-baseline twin."""
    root = Path(scratch_root)
    if baseline:
        return BreadcrumbArmSpec(
            name=BASELINE_ARM_NAME,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            embed_breadcrumb=False,
            db_path=root / f"{BASELINE_ARM_NAME}.db",
        )
    return BreadcrumbArmSpec(
        name=ARM_NAME,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        embed_breadcrumb=True,
        db_path=root / f"{ARM_NAME}.db",
    )


def build_arm_env(base_env: Mapping[str, str], arm_spec: BreadcrumbArmSpec) -> dict[str, str]:
    """Copy ``base_env`` and pin the arm's fixed Qwen3/512 embed contract.

    API/base/prompt/model-path keys are removed, never blanked, so an inherited
    value cannot change the arm's ``cache_model_id`` or leak credentials. Only
    ``SIF_EMBED_BREADCRUMB`` differs between the arm and its baseline twin;
    ``SIF_MAX_TOKENS`` stays 512 because it is absent from the embedding cache
    key and would confound the breadcrumb effect (research Pitfall 3).
    """
    env = dict(base_env)
    for key in REMOVED_ENV:
        env.pop(key, None)
    env.update(
        {
            "SIF_MODEL_TYPE": MODEL_TYPE,
            "SIF_MODEL_NAME": MODEL_NAME,
            "SIF_EMBEDDING_DIM": str(EMBEDDING_DIM),
            "SIF_MAX_TOKENS": str(MAX_TOKENS),
            "SIF_BATCH_SIZE": str(BATCH_SIZE),
            "SIF_CHUNK_SIZE": str(arm_spec.chunk_size),
            "SIF_CHUNK_OVERLAP": str(arm_spec.chunk_overlap),
            "SIF_EMBED_BREADCRUMB": "1" if arm_spec.embed_breadcrumb else "0",
            "SIF_CACHE_EMBEDDINGS": "1",
        }
    )
    env.update(PINNED_RANKING_ENV)
    return env


def _identity_command(arm_spec: BreadcrumbArmSpec) -> list[str]:
    """The identity probe argv; the caller runs it under the arm env."""
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        "--probe-identity",
        "--index",
        str(arm_spec.db_path),
    ]


def build_stage_commands(
    arm_spec: BreadcrumbArmSpec,
    corpus_roots: Sequence[Path],
    baseline_saved_run: Path | None = None,
    *,
    prefix: str = "arm",
) -> list[dict[str, Any]]:
    """Build the ordered index/embed/identity/eval stage plan for one arm.

    Every ``sif`` argv is an argv list starting with ``-q`` (ModelScope
    pollutes stdout even on a cache hit) and ``--index``; no command is a
    shell string. A fresh baseline eval names both required languages; every
    comparison eval re-evaluates the saved query set with ``--compare`` and
    never resamples.
    """
    base = [sys.executable, "-m", "sif.cli.main", "-q", "--index", str(arm_spec.db_path)]
    env = build_arm_env(os.environ, arm_spec)
    index_commands: list[list[str]] = [
        [*base, "collection", "add", str(root), "--name", f"{COLLECTION_PREFIX}-{index}"]
        for index, root in enumerate(corpus_roots, start=1)
    ]
    index_commands.append([*base, "index", "update"])
    if baseline_saved_run is None:
        eval_command = [
            *base,
            "eval",
            "--personal",
            "--all",
            "--require-language",
            "en",
            "--require-language",
            "zh",
            "--json",
        ]
    else:
        eval_command = [
            *base,
            "eval",
            "--personal",
            "--all",
            "--compare",
            str(baseline_saved_run),
            "--json",
        ]
    return [
        {"stage": f"{prefix}:index", "commands": index_commands, "env": dict(env)},
        {
            "stage": f"{prefix}:embed",
            "commands": [[*base, "index", "embed", "--force", "--chunk-strategy", "auto"]],
            "env": dict(env),
        },
        {
            "stage": f"{prefix}:identity",
            "commands": [_identity_command(arm_spec)],
            "env": dict(env),
        },
        {"stage": f"{prefix}:eval", "commands": [eval_command], "env": dict(env)},
    ]


def build_arm_commands(
    arm_spec: BreadcrumbArmSpec,
    corpus_roots: Sequence[Path],
    baseline_saved_run: Path | None = None,
) -> list[dict[str, Any]]:
    """Build the single breadcrumb arm's ordered stage plan."""
    return build_stage_commands(arm_spec, corpus_roots, baseline_saved_run, prefix="arm")


def build_dry_run_payload(
    scratch_root: Path,
    corpus_roots: Sequence[Path],
    baseline_saved_run: Path | None = None,
) -> dict[str, Any]:
    """Return the single-arm plan without invoking a subprocess or writing."""
    root = Path(scratch_root)
    arm_spec = build_arm_spec(root)
    baseline_spec = build_arm_spec(root, baseline=True)
    default_baseline = root / "saved-runs" / "baseline.json"
    effective_baseline = default_baseline if baseline_saved_run is None else baseline_saved_run
    return {
        "version": 1,
        "arm": {
            "name": arm_spec.name,
            "chunk_size": arm_spec.chunk_size,
            "chunk_overlap": arm_spec.chunk_overlap,
            "embed_breadcrumb": arm_spec.embed_breadcrumb,
            "model_name": MODEL_NAME,
            "model_type": MODEL_TYPE,
            "embedding_dim": EMBEDDING_DIM,
            "max_tokens": MAX_TOKENS,
            "db_path": os.path.relpath(arm_spec.db_path, root),
        },
        "env": build_arm_env(os.environ, arm_spec),
        "stages": build_arm_commands(arm_spec, corpus_roots, effective_baseline),
        "baseline": {
            "saved_run": str(effective_baseline),
            "regenerated_when": (
                "missing, invalid, corpus-fingerprint-mismatched, or model-identity-mismatched"
            ),
            "stages": build_stage_commands(baseline_spec, corpus_roots, None, prefix="baseline"),
        },
        "expected_identity": {
            "cache_model_id": QWEN3_CACHE_MODEL_ID,
            "dimension": EMBEDDING_DIM,
            "query_prompt": None,
            "document_prompt": None,
        },
        "selection_rule": SELECTION_RULE,
        "max_tokens": MAX_TOKENS,
        "model_name": MODEL_NAME,
        "model_type": MODEL_TYPE,
        "expected_corpus_fingerprint": EXPECTED_CORPUS_FINGERPRINT,
        "min_heldout_for_epsilon_win": MIN_HELDOUT_FOR_EPSILON_WIN,
    }


def _print_dry_run_table(payload: Mapping[str, Any]) -> None:
    """Print a readable single-arm plan for an interactive dry run."""
    arm = payload["arm"]
    print(  # noqa: T201 - CLI output
        f"{arm['name']:<22} chunk={arm['chunk_size']}/{arm['chunk_overlap']} "
        f"breadcrumb={arm['embed_breadcrumb']} "
        f"model={arm['model_type']}:{arm['model_name']} max_tokens={arm['max_tokens']} "
        f"db={arm['db_path']}"
    )
    for stage in payload["stages"]:
        print(f"  {stage['stage']}: {len(stage['commands'])} command(s)")  # noqa: T201


def _emit_err(line: str) -> None:
    """Write one refusal/failure line to stderr."""
    sys.stderr.write(line + "\n")


def _connect_read_only(db_path: Path) -> sqlite3.Connection:
    """Open one read-only SQLite connection."""
    uri = f"file:{Path(db_path).resolve().as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _cache_db_path() -> Path:
    """Resolve the shared embedding-cache DB before any arm env is chosen."""
    from sif.config.settings import get_settings  # noqa: PLC0415 - deferred sif import

    return Path(get_settings().get_cache_dir()) / "embeddings_cache.db"


def _corpus_summary(db_path: Path) -> tuple[str, int]:
    """Return the arm DB's corpus fingerprint and document count."""
    from sif.search.personal_bench import (  # noqa: PLC0415 - deferred sif import
        corpus_fingerprint,
        load_document_metadata,
    )

    conn = _connect_read_only(db_path)
    try:
        metadata = load_document_metadata(conn, None)
    finally:
        conn.close()
    return corpus_fingerprint(metadata), len(metadata)


def baseline_rejection_reason(saved_run_path: Path | None, live_fingerprint: str) -> str | None:
    """Return a short reason the saved run cannot be the baseline, or None."""
    return chunk_sweep.baseline_rejection_reason(saved_run_path, live_fingerprint)


def choose_baseline(
    saved_run_path: Path | None,
    live_fingerprint: str,
) -> tuple[str, Path | None]:
    """Choose the saved-run baseline or request a fresh same-backend baseline.

    A saved run is usable only when it validates, its corpus fingerprint
    matches the live corpus, and its model identity is the pinned modelscope
    Qwen3 pair (T-24-13). Every rejection regenerates a fresh 512/128 Qwen3
    baseline with the breadcrumb off rather than comparing incomparable
    vectors. Reasons are path-free so they can be recorded in the artifact.
    """
    reason = baseline_rejection_reason(saved_run_path, live_fingerprint)
    if reason is None and saved_run_path is not None:
        return "saved-run", saved_run_path
    return f"fresh-baseline ({reason})", None


def require_probe_identity(payload: Mapping[str, Any]) -> None:
    """Raise a named error unless a probe payload carries the fixed identity."""
    chunk_sweep.require_probe_identity(payload)


def _run_identity_probe(index_path: Path) -> int:
    """Load the arm's model under its env and print the persisted identity.

    Runs in its own subprocess because ``get_settings()`` is process-cached;
    the deferred ``sif`` imports keep this module stdlib-only at import.
    """
    try:
        from sif.config.settings import get_settings  # noqa: PLC0415 - deferred
        from sif.embedding.identity import read_identity  # noqa: PLC0415 - deferred
        from sif.embedding.manager import EmbeddingManager  # noqa: PLC0415 - deferred
        from sif.utils.logging import set_quiet  # noqa: PLC0415 - deferred
    except ImportError as exc:
        _emit_err(f"FAIL identity probe: {exc}")
        return 4
    try:
        set_quiet(True)
        settings = get_settings()
        manager = EmbeddingManager.from_settings(settings)
        configured = manager.get_identity()
        conn = _connect_read_only(index_path)
        try:
            stored = read_identity(conn)
        finally:
            conn.close()
        failures = chunk_sweep.identity_failures(stored)
        if failures:
            raise ValueError("embedder identity gate failed: " + "; ".join(failures))
        payload = {
            "cache_model_id": stored.cache_model_id,
            "dimension": stored.dimension,
            "source": stored.source,
            "query_prompt": stored.query_prompt,
            "document_prompt": stored.document_prompt,
            "model_name": stored.model_name,
            "model_type": stored.model_type,
            "configured_model_name": configured.model_name,
            "configured_model_type": configured.model_type,
            "configured_dimension": configured.dimension,
            "check_identity_status": "ok",
        }
    except Exception as exc:  # Any load or gate failure maps to exit 1.
        _emit_err(f"FAIL identity probe: {exc}")
        return 1
    print(json.dumps(payload, sort_keys=True))  # noqa: T201 - probe stdout contract
    return 0


def _split_gate(eval_payload: Any, split: str) -> dict[str, Any] | None:
    """Return one split's gate mapping from a ``--compare`` payload."""
    if not isinstance(eval_payload, Mapping):
        return None
    comparison = eval_payload.get("comparison")
    if not isinstance(comparison, Mapping):
        return None
    splits = comparison.get("splits")
    if not isinstance(splits, Mapping):
        return None
    gate = splits.get(split)
    return dict(gate) if isinstance(gate, Mapping) else None


def _leg_gates(eval_payload: Any) -> dict[str, dict[str, Any]]:
    """Return the held-out per-leg gates (falling back to the all-split legs)."""
    from_legs: Mapping[str, Any] = {}
    from_splits: Mapping[str, Any] = {}
    if isinstance(eval_payload, Mapping):
        comparison = eval_payload.get("comparison")
        if isinstance(comparison, Mapping):
            legs = comparison.get("legs")
            if isinstance(legs, Mapping):
                from_legs = legs
            leg_splits = comparison.get("leg_splits")
            if isinstance(leg_splits, Mapping):
                held = leg_splits.get("heldout")
                if isinstance(held, Mapping):
                    from_splits = held
    gates: dict[str, dict[str, Any]] = {}
    for leg in ("title", "body", "replay"):
        gate = from_splits.get(leg, from_legs.get(leg))
        if isinstance(gate, Mapping):
            gates[leg] = dict(gate)
    return gates


def _load_document_chunks(db_path: Path) -> list[tuple[str, list[DocumentChunk]]]:
    """Read every document's title and its chunks in sequence order."""
    from sif.core.models import DocumentChunk  # noqa: PLC0415 - deferred sif import

    conn = _connect_read_only(db_path)
    try:
        documents = conn.execute(
            "SELECT id, COALESCE(title, '') FROM documents ORDER BY id"
        ).fetchall()
        rows = conn.execute(
            "SELECT document_id, sequence, content FROM document_chunks "
            "ORDER BY document_id, sequence"
        ).fetchall()
    finally:
        conn.close()
    by_document: dict[str, list[DocumentChunk]] = {}
    for document_id, sequence, content in rows:
        by_document.setdefault(str(document_id), []).append(
            DocumentChunk(
                content=str(content),
                sequence=int(sequence),
                start_pos=0,
                end_pos=0,
                document_id=str(document_id),
            )
        )
    return [(str(title), by_document.get(str(document_id), [])) for document_id, title in documents]


def aggregate_duplicate_metrics(
    per_document: Sequence[Mapping[str, object]],
) -> dict[str, Any]:
    """Aggregate per-document duplicate shares, weighted by chunk count.

    A per-document average would let a one-chunk document outweigh a large
    one; the measured duplicate risk is a per-chunk property, so the
    denominator is the total chunk count.
    """
    total_chunks = sum(int(entry.get("chunks", 0)) for entry in per_document)
    total_documents = sum(int(entry.get("documents", 0)) for entry in per_document)
    aggregated: dict[str, Any] = {"chunks": total_chunks, "documents": total_documents}
    for name in ("title_share", "in_content_share", "subchunk_share", "title_equals_heading_share"):
        if total_chunks:
            weighted = sum(
                float(entry.get(name, 0.0)) * int(entry.get("chunks", 0)) for entry in per_document
            )
            aggregated[name] = round(weighted / total_chunks, 6)
        else:
            aggregated[name] = 0.0
    return aggregated


def collect_duplicate_summary(db_path: Path) -> dict[str, Any]:
    """Compute the aggregate duplicate metrics from the arm DB's stored chunks."""
    from sif.indexing.breadcrumb import (  # noqa: PLC0415 - deferred sif import
        duplicate_metrics,
    )

    per_document = [
        duplicate_metrics(title, chunks) for title, chunks in _load_document_chunks(db_path)
    ]
    return aggregate_duplicate_metrics(per_document)


# -- Stage machine -----------------------------------------------------------


def scope_state(
    corpus_roots: Sequence[Path],
    scratch_root: Path,
    corpus_label: str,
) -> dict[str, Any]:
    """Describe the resolved corpus scope that invalidates prior markers."""
    return harrier_eval.scope_state(corpus_roots, scratch_root, corpus_label)


def scope_key(scope: Mapping[str, Any]) -> str:
    """Hash the sorted resolved roots plus the label to 16 hex chars."""
    return harrier_eval.scope_key(scope)


def prepare_run_state(
    corpus_roots: Sequence[Path],
    scratch_root: Path,
    corpus_label: str,
) -> tuple[dict[str, Any], Path]:
    """Load the scope-keyed run state, or a fresh one for a changed scope."""
    state_path = Path(scratch_root) / STATE_FILE_NAME
    scope = scope_state(corpus_roots, scratch_root, corpus_label)
    current_key = scope_key(scope)
    state = harrier_eval.load_run_state(state_path, scope_key=current_key, scope=scope)
    return state, state_path


def save_run_state(path: Path, state: Mapping[str, Any]) -> None:
    """Write run state atomically with sorted keys and a trailing newline."""
    harrier_eval.save_run_state(path, state)


def _is_known_stage(stage: str) -> bool:
    """Whether ``stage`` is one of this runbook's stage labels."""
    if stage in FINAL_STAGES:
        return True
    prefix, _, suffix = stage.partition(":")
    return prefix in STAGE_PREFIXES and suffix in STAGE_SUFFIXES


def mark_stage(state: dict[str, Any], stage: str, detail: Any = None) -> None:
    """Mark ``stage`` complete with an optional machine-readable detail."""
    if not _is_known_stage(stage):
        raise ValueError(f"unknown stage: {stage!r}")
    stages = state.setdefault("stages", {})
    stages[stage] = {"status": "complete", "at": _now(), "detail": detail}


def _previous_scope_key(state_path: Path) -> str | None:
    """Read the scope key recorded by a prior run, if any."""
    try:
        payload = json.loads(Path(state_path).read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(payload, Mapping):
        return None
    value = payload.get("scope_key")
    return value if isinstance(value, str) else None


def _cleanup_scratch(scratch_root: Path, specs: Sequence[BreadcrumbArmSpec]) -> list[str]:
    """Delete only the run's own DB files/sidecars and the baseline saved run."""
    root = Path(scratch_root).resolve()
    candidates: list[Path] = []
    for spec in specs:
        candidates.extend(
            [
                spec.db_path,
                Path(f"{spec.db_path}-wal"),
                Path(f"{spec.db_path}-shm"),
                Path(f"{spec.db_path}.lock"),
            ]
        )
    candidates.append(root / "saved-runs" / "baseline.json")
    removed: list[str] = []
    for candidate in candidates:
        target = harrier_eval.assert_within_scratch(candidate, root)
        if target.is_file():
            target.unlink()
            removed.append(target.name)
    return removed


def _run_commands(stage_entry: Mapping[str, Any]) -> subprocess.CompletedProcess[str]:
    """Run every argv of one stage sequentially; never a shell string."""
    env = stage_entry["env"]
    proc: subprocess.CompletedProcess[str] | None = None
    for argv in stage_entry["commands"]:
        try:
            proc = subprocess.run(
                argv,
                cwd=PROJECT_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=STAGE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"{stage_entry['stage']} timed out") from exc
        if proc.returncode != 0:
            return proc
    if proc is None:  # pragma: no cover - every stage carries at least one argv
        raise RuntimeError(f"{stage_entry['stage']} has no commands")
    return proc


def _cache_rows(cache_db_path: Path) -> int:
    """Count this model's rows in the shared embedding cache; never write."""
    path = Path(cache_db_path)
    if not path.is_file():
        return 0
    try:
        conn = _connect_read_only(path)
    except sqlite3.Error:
        return 0
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM embeddings WHERE model_id LIKE ?",
            (f"{QWEN3_CACHE_MODEL_ID}%",),
        ).fetchone()
    except sqlite3.Error:
        return 0
    finally:
        conn.close()
    return int(row[0]) if row is not None else 0


def _stage_detail(  # noqa: PLR0913 - explicit stage context
    suffix: str,
    stage_entry: Mapping[str, Any],
    proc: subprocess.CompletedProcess[str],
    *,
    spec: BreadcrumbArmSpec,
    cache_db_path: Path,
    elapsed: float,
) -> dict[str, Any]:
    """Build one stage's recorded detail from its process result."""
    if suffix == "index":
        fingerprint, documents = _corpus_summary(spec.db_path)
        return {"corpus_fingerprint": fingerprint, "documents": documents}
    if suffix == "embed":
        return harrier_eval.collect_arm_costs(
            spec.db_path,
            cache_db_path,
            elapsed,
            cache_model_id=QWEN3_CACHE_MODEL_ID,
        )
    if suffix == "identity":
        payload = json.loads(proc.stdout)
        if not isinstance(payload, Mapping):
            raise RuntimeError(f"{stage_entry['stage']} did not emit a JSON object")
        require_probe_identity(payload)
        return {key: payload.get(key) for key in IDENTITY_KEYS}
    payload = json.loads(proc.stdout)
    if not isinstance(payload, Mapping):
        raise RuntimeError(f"{stage_entry['stage']} did not emit a JSON object")
    return {
        "run_path": payload.get("run_path"),
        "tuning": _split_gate(payload, "tuning"),
        "heldout": _split_gate(payload, "heldout"),
        "legs": _leg_gates(payload),
        "duplicates": collect_duplicate_summary(spec.db_path),
    }


def _absorb_detail(suffix: str, detail: Mapping[str, Any], result: dict[str, Any]) -> None:
    """Fold one stage detail into the arm's accumulated result."""
    if suffix == "index":
        result["corpus_fingerprint"] = detail.get("corpus_fingerprint")
        result["documents"] = detail.get("documents")
    elif suffix == "embed":
        result["costs"] = dict(detail)
    elif suffix == "identity":
        result["identity"] = dict(detail)
    elif suffix == "eval":
        result["tuning"] = detail.get("tuning")
        result["heldout"] = detail.get("heldout")
        result["legs"] = detail.get("legs")
        result["duplicates"] = detail.get("duplicates")
        result["run_path"] = detail.get("run_path")


def _execute_stage(  # noqa: PLR0913 - explicit stage context
    state: dict[str, Any],
    state_path: Path,
    stage_entry: Mapping[str, Any],
    spec: BreadcrumbArmSpec,
    result: dict[str, Any],
    *,
    cache_db_path: Path,
) -> int:
    """Run or resume one stage; return 0 on success and 1 on failure."""
    stage = stage_entry["stage"]
    suffix = stage.rpartition(":")[2]
    if harrier_eval.stage_done(state, stage):
        detail = (state["stages"][stage] or {}).get("detail")
        _absorb_detail(suffix, detail if isinstance(detail, Mapping) else {}, result)
        return 0
    cache_before = _cache_rows(cache_db_path) if suffix == "embed" else None
    started = time.monotonic()
    try:
        proc = _run_commands(stage_entry)
        elapsed = time.monotonic() - started
        if proc.returncode != 0:
            state["failed_stage"] = stage
            save_run_state(state_path, state)
            _emit_err(f"FAIL {stage} exited {proc.returncode}: {proc.stderr[-4000:]}")
            return 1
        detail = _stage_detail(
            suffix,
            stage_entry,
            proc,
            spec=spec,
            cache_db_path=cache_db_path,
            elapsed=elapsed,
        )
        if suffix == "embed" and cache_before is not None:
            detail["cache_rows_before"] = cache_before
            added = max(0, int(detail["cache_rows_after"]) - cache_before)
            detail["cache_hits"] = max(0, int(detail["chunks"]) - added)
    except (json.JSONDecodeError, RuntimeError, OSError, ValueError, sqlite3.Error) as exc:
        state["failed_stage"] = stage
        save_run_state(state_path, state)
        _emit_err(f"FAIL {stage}: {exc}")
        return 1
    _absorb_detail(suffix, detail, result)
    mark_stage(state, stage, detail)
    save_run_state(state_path, state)
    return 0


def _run_stage_list(  # noqa: PLR0913 - explicit stage context
    stages: Sequence[Mapping[str, Any]],
    state: dict[str, Any],
    state_path: Path,
    spec: BreadcrumbArmSpec,
    result: dict[str, Any],
    *,
    cache_db_path: Path,
) -> int:
    """Run or resume a list of stages; return 0 on success and 1 on failure."""
    for stage_entry in stages:
        if (
            _execute_stage(
                state,
                state_path,
                stage_entry,
                spec,
                result,
                cache_db_path=cache_db_path,
            )
            != 0
        ):
            return 1
    return 0


# -- Artifact ----------------------------------------------------------------


def build_breadcrumb_artifact(  # noqa: PLR0913 - one keyword per artifact input
    *,
    decision: BreadcrumbDecision,
    spec: BreadcrumbArmSpec,
    identity: Mapping[str, Any],
    confirmation: Mapping[str, Any],
    legs: Mapping[str, Mapping[str, Any]],
    duplicates: Mapping[str, Any],
    corpus_label: str,
    corpus_fingerprint: str,
    baseline_source: str,
) -> dict[str, Any]:
    """Build the committed aggregate envelope in its documented key order.

    Aggregate-only: counts, gates, an identity object, and a corpus
    label/fingerprint. Never query text, query ids, document paths, or
    absolute paths (T-24-06).
    """
    return {
        "schema_version": 1,
        "decision": decision.decision,
        "decision_record": decision.to_dict(),
        "arm": spec.name,
        "chunk_size": spec.chunk_size,
        "chunk_overlap": spec.chunk_overlap,
        "embed_breadcrumb": spec.embed_breadcrumb,
        "model_name": MODEL_NAME,
        "model_type": MODEL_TYPE,
        "embedding_dim": EMBEDDING_DIM,
        "max_tokens": MAX_TOKENS,
        "identity": {key: identity.get(key) for key in IDENTITY_KEYS},
        "confirmation": dict(confirmation),
        "legs": {leg: dict(gate) for leg, gate in legs.items()},
        "duplicates": dict(duplicates),
        "corpus_label": corpus_label,
        "corpus_fingerprint": corpus_fingerprint,
        "baseline_source": baseline_source,
        "selection_rule": SELECTION_RULE,
        "min_heldout_for_epsilon_win": MIN_HELDOUT_FOR_EPSILON_WIN,
        "limitation": LIMITATION,
    }


def write_committed_artifact(
    artifact: Mapping[str, Any],
    *,
    force: bool = False,
    path: Path | None = None,
) -> Path:
    """Write the committed evidence, never silently replacing another run."""
    return chunk_sweep.write_committed_artifact(artifact, force=force, path=path)


def finalize_breadcrumb(  # noqa: PLR0913 - one keyword per artifact input
    *,
    decision: BreadcrumbDecision,
    spec: BreadcrumbArmSpec,
    identity: Mapping[str, Any],
    confirmation: Mapping[str, Any],
    legs: Mapping[str, Mapping[str, Any]],
    duplicates: Mapping[str, Any],
    corpus_label: str,
    corpus_fingerprint: str,
    baseline_source: str,
    force: bool = False,
    artifact_path: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    """Build and write the artifact; return (exit code, artifact).

    An insufficient-evidence outcome still writes a countable artifact and
    exits 3; a written verdict exits 0 (D-12).
    """
    from sif.search.tuning_verdict import DECISION_INSUFFICIENT  # noqa: PLC0415 - deferred

    artifact = build_breadcrumb_artifact(
        decision=decision,
        spec=spec,
        identity=identity,
        confirmation=confirmation,
        legs=legs,
        duplicates=duplicates,
        corpus_label=corpus_label,
        corpus_fingerprint=corpus_fingerprint,
        baseline_source=baseline_source,
    )
    write_committed_artifact(artifact, force=force, path=artifact_path)
    code = 3 if artifact["decision"] == DECISION_INSUFFICIENT else 0
    return code, artifact


def _empty_confirmation() -> dict[str, Any]:
    """The honest gate payload when the eval stage produced none."""
    return {
        "n": 0,
        "mean_delta": 0.0,
        "winner": False,
        "sufficient": False,
    }


def run_stage_machine(  # noqa: PLR0913 - one keyword per run option
    corpus_roots: Sequence[Path],
    scratch_root: Path,
    *,
    corpus_label: str,
    baseline_saved_run: Path | None,
    keep_arms: bool,
    output_json: bool,
    force: bool = False,
    artifact_path: Path | None = None,
) -> int:
    """Run (or resume) the one-arm scope-keyed breadcrumb stage machine."""
    from sif.search.tuning_verdict import (  # noqa: PLC0415 - deferred sif import
        decide_breadcrumb_default,
    )

    # The guard runs before any mkdir/write/delete (T-24-01).
    scratch_root = harrier_eval.assert_within_scratch(scratch_root, scratch_root)
    scratch_root.mkdir(parents=True, exist_ok=True)
    arm_spec = build_arm_spec(scratch_root)
    baseline_spec = build_arm_spec(scratch_root, baseline=True)
    for spec in (arm_spec, baseline_spec):
        harrier_eval.assert_within_scratch(spec.db_path, scratch_root)
    saved_runs = scratch_root / "saved-runs"
    saved_runs.mkdir(parents=True, exist_ok=True)
    state, state_path = prepare_run_state(corpus_roots, scratch_root, corpus_label)
    previous_key = _previous_scope_key(state_path)
    if previous_key is not None and previous_key != state["scope_key"]:
        _cleanup_scratch(scratch_root, (arm_spec, baseline_spec))
    cache_db_path = _cache_db_path()
    arm_result: dict[str, Any] = {}
    # Index first: the arm's live corpus fingerprint decides whether the
    # supplied saved run may be compared against at all.
    if (
        _run_stage_list(
            build_arm_commands(arm_spec, corpus_roots)[:1],
            state,
            state_path,
            arm_spec,
            arm_result,
            cache_db_path=cache_db_path,
        )
        != 0
    ):
        return 1
    live_fingerprint = str(arm_result.get("corpus_fingerprint") or "")
    baseline_source, baseline_run_path = choose_baseline(baseline_saved_run, live_fingerprint)
    if baseline_run_path is None:
        baseline_result: dict[str, Any] = {}
        if (
            _run_stage_list(
                build_stage_commands(baseline_spec, corpus_roots, None, prefix="baseline"),
                state,
                state_path,
                baseline_spec,
                baseline_result,
                cache_db_path=cache_db_path,
            )
            != 0
        ):
            return 1
        run_path = baseline_result.get("run_path")
        if not isinstance(run_path, str) or not run_path:
            _emit_err("FAIL baseline eval did not report a saved run path")
            return 1
        target = harrier_eval.assert_within_scratch(saved_runs / "baseline.json", scratch_root)
        shutil.copy2(Path(run_path), target)
        baseline_run_path = target
    if (
        _run_stage_list(
            build_arm_commands(arm_spec, corpus_roots, baseline_run_path)[1:],
            state,
            state_path,
            arm_spec,
            arm_result,
            cache_db_path=cache_db_path,
        )
        != 0
    ):
        return 1
    heldout = arm_result.get("heldout") or _empty_confirmation()
    legs = arm_result.get("legs") or {}
    duplicates = arm_result.get("duplicates") or {}
    identity = arm_result.get("identity") or {}
    decision = decide_breadcrumb_default(heldout, legs, duplicates)
    code, artifact = finalize_breadcrumb(
        decision=decision,
        spec=arm_spec,
        identity=identity,
        confirmation=heldout,
        legs=legs,
        duplicates=duplicates,
        corpus_label=corpus_label,
        corpus_fingerprint=live_fingerprint,
        baseline_source=baseline_source,
        force=force,
        artifact_path=artifact_path,
    )
    mark_stage(state, "verdict", {"decision": artifact["decision"]})
    mark_stage(
        state,
        "artifact",
        {
            "decision": artifact["decision"],
            "corpus_fingerprint": artifact["corpus_fingerprint"],
        },
    )
    save_run_state(state_path, state)
    if not keep_arms:
        _cleanup_scratch(scratch_root, (arm_spec, baseline_spec))
    if output_json:
        print(json.dumps(artifact, indent=2, sort_keys=True))  # noqa: T201 - CLI output
    else:
        print(  # noqa: T201 - CLI output
            f"PASS decision={artifact['decision']} artifact={artifact_path or ARTIFACT_PATH}"
        )
    return code


def build_parser() -> argparse.ArgumentParser:
    """Build the runbook argument parser."""
    parser = argparse.ArgumentParser(
        description="Run the single held-out-gated title-breadcrumb arm.",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        action="append",
        default=None,
        help="Corpus root to index into the arm (repeatable; roots must be disjoint)",
    )
    parser.add_argument(
        "--scratch-root",
        type=Path,
        default=DEFAULT_SCRATCH_ROOT,
        help="Scratch directory for the arm DB, saved runs, and run state",
    )
    parser.add_argument("--corpus-label", default="phase23-zh-heavy", help="Aggregate label")
    parser.add_argument(
        "--baseline-saved-run",
        type=Path,
        default=None,
        help="Phase 23 Qwen3 saved run to compare against (regenerated when unusable)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the full single-arm stage plan and exit without a subprocess",
    )
    parser.add_argument(
        "--keep-arms",
        action="store_true",
        help="Keep the scratch arm DB and saved runs after the verdict",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite a committed artifact whose decision or fingerprint differs",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    parser.add_argument("--probe-identity", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--index", type=Path, default=None, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:  # noqa: PLR0911 - one per CLI mode
    """Run the requested mode; return 0 success, 1 failure, 2 refusal, 3 short."""
    args = build_parser().parse_args(argv)
    if args.probe_identity:
        if args.index is None:
            _emit_err("REFUSED: --probe-identity requires --index")
            return 2
        return _run_identity_probe(args.index)
    roots = list(args.corpus) if args.corpus else [harrier_eval.EXAMPLE_CORPUS_ROOT]
    try:
        corpus_roots = harrier_eval.resolve_corpus_roots(roots)
        scratch_root = harrier_eval.assert_within_scratch(args.scratch_root, args.scratch_root)
    except ValueError as exc:
        _emit_err(f"REFUSED: {exc}")
        return 2
    if args.dry_run:
        payload = build_dry_run_payload(scratch_root, corpus_roots, args.baseline_saved_run)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))  # noqa: T201 - CLI output
        else:
            _print_dry_run_table(payload)
        return 0
    try:
        return run_stage_machine(
            corpus_roots,
            scratch_root,
            corpus_label=args.corpus_label,
            baseline_saved_run=args.baseline_saved_run,
            keep_arms=args.keep_arms,
            output_json=args.json,
            force=args.force,
        )
    except RuntimeError as exc:
        _emit_err(f"REFUSED: {exc}")
        return 2
    except (OSError, sqlite3.Error, ValueError) as exc:
        _emit_err(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
