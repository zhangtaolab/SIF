#!/usr/bin/env python3
"""Six-arm chunk size/overlap sweep runbook (Phase 24, QUAL-02).

The runbook builds one isolated, file-backed index per chunk configuration
from the same resolved corpus roots, drives every stage as an explicit
argv-list subprocess under its own per-arm environment, selects a candidate
on the tuning split, and confirms it on the held-out split. ``get_settings()``
is process-cached, so an in-process arm switch would silently measure the
wrong model; every stage therefore runs in its own subprocess.

Only ``SIF_CHUNK_SIZE`` and ``SIF_CHUNK_OVERLAP`` vary between arms: every
arm pins the Phase 23 keep-qwen3 embedder on the ModelScope backend, the
1024-dimension width, and ``SIF_MAX_TOKENS=512`` (research Pitfall 2/3). The
selection rule is tuning-select then held-out-confirm (research Pitfall 10);
no candidate is ever adopted from the tuning split alone.

Every arm's persisted embedder identity is asserted equal to
``modelscope:Qwen/Qwen3-Embedding-0.6B`` after the embed and before the eval;
a baseline saved run whose corpus or model identity differs is rejected and
regenerated on the same backend. The committed artifact is aggregate-only:
counts, gates, an identity object, a corpus label/fingerprint, and no query
text or absolute paths.

This module is stdlib-only at import time; ``sif`` imports are deferred into
the probe and baseline helpers so ``--dry-run`` works without the embedding
stack.
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


try:  # Running as ``python scripts/chunk_sweep.py``: scripts/ is sys.path[0].
    import harrier_eval
except ImportError:  # Imported as ``scripts.chunk_sweep`` or spec-loaded.
    from scripts import harrier_eval

if TYPE_CHECKING:
    from sif.search.tuning_verdict import ChunkArm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCRATCH_ROOT = PROJECT_ROOT / ".planning" / "tmp" / "phase-24-chunk-sweep"
ARTIFACT_PATH = (
    PROJECT_ROOT
    / ".planning"
    / "milestones"
    / "v1.2-phases"
    / "24-tuning-models-ux-install-docs"
    / "bench"
    / "chunk-sweep.json"
)
MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
MODEL_TYPE = "modelscope"
QWEN3_CACHE_MODEL_ID = "modelscope:Qwen/Qwen3-Embedding-0.6B"
EMBEDDING_DIM = 1024
MAX_TOKENS = 512
BATCH_SIZE = 32
COLLECTION_PREFIX = "phase24"
SELECTION_RULE = "tuning-select-then-heldout-confirm"
MIN_HELDOUT_FOR_EPSILON_WIN = 101


def build_limitation(corpus_label: str, heldout_n: int) -> str:
    """Return corpus-scoped limitation text with the measured held-out count."""
    if heldout_n >= MIN_HELDOUT_FOR_EPSILON_WIN:
        return (
            f"The {corpus_label} corpus has {heldout_n} held-out queries, at or above "
            f"the {MIN_HELDOUT_FOR_EPSILON_WIN} needed for a 0.01 mean-delta win."
        )
    return (
        f"The {corpus_label} corpus has {heldout_n} held-out queries, below the "
        f"{MIN_HELDOUT_FOR_EPSILON_WIN} needed for a 0.01 mean-delta win, so only "
        "keep-default or insufficient-evidence is reachable until a larger sample is supplied."
    )


STATE_FILE_NAME = "run-state.json"
_STAGE_PARTS = 3
STAGE_SUFFIXES = ("index", "embed", "identity", "eval")
FINAL_STAGES = ("verdict", "artifact")
STAGE_TIMEOUT_SECONDS = 6 * 60 * 60
IDENTITY_KEYS = (
    "cache_model_id",
    "dimension",
    "source",
    "query_prompt",
    "document_prompt",
    "check_identity_status",
)
# Reuse the Phase 23 removals and additionally drop the breadcrumb switch: a
# breadcrumb setting must never leak into a sweep arm (D-04, D-05).
REMOVED_ENV = (*harrier_eval.REMOVED_ENV, "SIF_EMBED_BREADCRUMB")
PINNED_RANKING_ENV = harrier_eval.PINNED_RANKING_ENV


@dataclass(frozen=True)
class SweepArmSpec:
    """One sweep arm: its chunk configuration and isolated scratch DB."""

    arm: ChunkArm
    db_path: Path

    @property
    def name(self) -> str:
        """The arm's fixed grid name."""
        return self.arm.name


def _now() -> str:
    """UTC timestamp for run-state records."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sweep_grid() -> tuple[ChunkArm, ...]:
    """Import the pure grid lazily so this module stays stdlib-only at import."""
    from sif.search.tuning_verdict import SWEEP_GRID  # noqa: PLC0415 - deferred sif import

    return SWEEP_GRID


def _baseline_arm_name() -> str:
    """Import the baseline arm name alongside the lazily loaded grid."""
    from sif.search.tuning_verdict import BASELINE_ARM_NAME  # noqa: PLC0415 - deferred

    return BASELINE_ARM_NAME


def build_sweep_arms(scratch_root: Path) -> list[SweepArmSpec]:
    """Build every arm in fixed grid order, each with its own DB file."""
    root = Path(scratch_root)
    return [SweepArmSpec(arm=arm, db_path=root / f"{arm.name}.db") for arm in _sweep_grid()]


def build_arm_env(base_env: Mapping[str, str], arm_spec: SweepArmSpec) -> dict[str, str]:
    """Copy ``base_env`` and pin one arm's fixed embed contract.

    API/base/prompt/model-path keys are removed, never blanked, so an
    inherited value cannot change the arm's ``cache_model_id`` or leak
    credentials. Only ``SIF_CHUNK_SIZE``/``SIF_CHUNK_OVERLAP`` differ between
    arms; ``SIF_MAX_TOKENS`` stays 512 because it is absent from the embedding
    cache key and would confound the chunking effect (research Pitfall 2/3).
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
            "SIF_CHUNK_SIZE": str(arm_spec.arm.chunk_size),
            "SIF_CHUNK_OVERLAP": str(arm_spec.arm.chunk_overlap),
            "SIF_CACHE_EMBEDDINGS": "1",
        }
    )
    env.update(PINNED_RANKING_ENV)
    return env


def _identity_command(arm_spec: SweepArmSpec) -> list[str]:
    """The identity probe argv; the caller runs it under the arm env."""
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        "--probe-identity",
        "--index",
        str(arm_spec.db_path),
    ]


def build_arm_commands(
    arm_spec: SweepArmSpec,
    corpus_roots: Sequence[Path],
    baseline_saved_run: Path | None = None,
) -> list[dict[str, Any]]:
    """Build the ordered index/embed/identity/eval stage plan for one arm.

    Every ``sif`` argv is an argv list starting with ``-q`` (ModelScope
    pollutes stdout even on a cache hit) and ``--index``; no command is a
    shell string. A fresh baseline eval names both required languages and
    raises the held-out floor to the epsilon gate's 101; every comparison eval
    re-evaluates the saved query set with ``--compare`` and never resamples.
    """
    base = [sys.executable, "-m", "sif.cli.main", "-q", "--index", str(arm_spec.db_path)]
    env = build_arm_env(os.environ, arm_spec)
    index_commands: list[list[str]] = [
        [
            *base,
            "collection",
            "add",
            str(root),
            "--name",
            f"{COLLECTION_PREFIX}-{index}",
        ]
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
            "--min-heldout",
            str(MIN_HELDOUT_FOR_EPSILON_WIN),
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
        {"stage": f"arm:{arm_spec.name}:index", "commands": index_commands, "env": dict(env)},
        {
            "stage": f"arm:{arm_spec.name}:embed",
            "commands": [[*base, "index", "embed", "--force", "--chunk-strategy", "auto"]],
            "env": dict(env),
        },
        {
            "stage": f"arm:{arm_spec.name}:identity",
            "commands": [_identity_command(arm_spec)],
            "env": dict(env),
        },
        {"stage": f"arm:{arm_spec.name}:eval", "commands": [eval_command], "env": dict(env)},
    ]


def build_dry_run_payload(
    scratch_root: Path,
    corpus_roots: Sequence[Path],
    baseline_saved_run: Path | None = None,
) -> dict[str, Any]:
    """Return the full six-arm plan without invoking a subprocess or writing."""
    root = Path(scratch_root)
    default_baseline = root / "saved-runs" / "baseline.json"
    arms = build_sweep_arms(root)
    baseline_arm_name = _baseline_arm_name()
    arm_payload: list[dict[str, Any]] = []
    command_payload: list[dict[str, Any]] = []
    for arm_spec in arms:
        effective_baseline = baseline_saved_run
        if effective_baseline is None and arm_spec.name != baseline_arm_name:
            effective_baseline = default_baseline
        arm_payload.append(
            {
                "name": arm_spec.name,
                "chunk_size": arm_spec.arm.chunk_size,
                "chunk_overlap": arm_spec.arm.chunk_overlap,
                "max_tokens": MAX_TOKENS,
                "model_name": MODEL_NAME,
                "model_type": MODEL_TYPE,
                "db_path": os.path.relpath(arm_spec.db_path, root),
            }
        )
        command_payload.append(
            {
                "arm": arm_spec.name,
                "stages": build_arm_commands(arm_spec, corpus_roots, effective_baseline),
            }
        )
    return {
        "version": 1,
        "grid": [
            {
                "name": arm.name,
                "chunk_size": arm.chunk_size,
                "chunk_overlap": arm.chunk_overlap,
            }
            for arm in _sweep_grid()
        ],
        "arms": arm_payload,
        "commands": command_payload,
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
        "expected_corpus_fingerprint": None,
        "min_heldout_for_epsilon_win": MIN_HELDOUT_FOR_EPSILON_WIN,
    }


def _print_dry_run_table(payload: Mapping[str, Any]) -> None:
    """Print a readable per-arm plan for an interactive dry run."""
    print(f"grid: {len(payload['grid'])} arms")  # noqa: T201 - CLI output
    for arm in payload["arms"]:
        print(  # noqa: T201 - CLI output
            f"{arm['name']:<22} chunk={arm['chunk_size']}/{arm['chunk_overlap']} "
            f"model={arm['model_type']}:{arm['model_name']} max_tokens={arm['max_tokens']} "
            f"db={arm['db_path']}"
        )


def _emit_err(line: str) -> None:
    """Write one refusal/failure line to stderr."""
    sys.stderr.write(line + "\n")


def _connect_read_only(db_path: Path) -> sqlite3.Connection:
    """Open one read-only SQLite connection."""
    uri = f"file:{Path(db_path).resolve().as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


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


def _cache_db_path() -> Path:
    """Resolve the shared embedding-cache DB before any arm env is chosen."""
    from sif.config.settings import get_settings  # noqa: PLC0415 - deferred sif import

    return Path(get_settings().get_cache_dir()) / "embeddings_cache.db"


def _corpus_summary(db_path: Path) -> tuple[str, int]:
    """Return arm DB's corpus fingerprint and document count."""
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


def identity_failures(stored: Any) -> list[str]:
    """Name every field that is not the fixed modelscope Qwen3 identity."""
    if stored is None:
        return ["no stored embedder identity"]
    failures: list[str] = []
    if stored.cache_model_id != QWEN3_CACHE_MODEL_ID:
        failures.append(
            f"cache_model_id is {stored.cache_model_id!r}, expected {QWEN3_CACHE_MODEL_ID!r}"
        )
    if stored.dimension != EMBEDDING_DIM:
        failures.append(f"dimension is {stored.dimension}, expected {EMBEDDING_DIM}")
    if stored.source != "verified":
        failures.append(f"source is {stored.source!r}, expected 'verified'")
    if stored.query_prompt is not None:
        failures.append(f"query_prompt is {stored.query_prompt!r}, expected None")
    if stored.document_prompt is not None:
        failures.append(f"document_prompt is {stored.document_prompt!r}, expected None")
    return failures


def require_probe_identity(payload: Mapping[str, Any]) -> None:
    """Raise a named error unless a probe payload carries the fixed identity."""
    failures: list[str] = []
    if payload.get("cache_model_id") != QWEN3_CACHE_MODEL_ID:
        failures.append(
            f"cache_model_id is {payload.get('cache_model_id')!r}, "
            f"expected {QWEN3_CACHE_MODEL_ID!r}"
        )
    if payload.get("dimension") != EMBEDDING_DIM:
        failures.append(f"dimension is {payload.get('dimension')!r}, expected {EMBEDDING_DIM}")
    if payload.get("source") != "verified":
        failures.append(f"source is {payload.get('source')!r}, expected 'verified'")
    if payload.get("query_prompt") is not None:
        failures.append(f"query_prompt is {payload.get('query_prompt')!r}, expected None")
    if payload.get("document_prompt") is not None:
        failures.append(f"document_prompt is {payload.get('document_prompt')!r}, expected None")
    if failures:
        raise ValueError("embedder identity gate failed: " + "; ".join(failures))


def _run_identity_probe(index_path: Path) -> int:
    """Load one arm's model under its env and print the persisted identity."""
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
        failures = identity_failures(stored)
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


def baseline_rejection_reason(
    saved_run_path: Path | None,
    live_fingerprint: str,
) -> str | None:
    """Return a short reason the saved run cannot be the baseline, or None.

    A saved run is usable only when it validates, its corpus fingerprint
    equals the live fingerprint, and its model identity is the pinned
    modelscope Qwen3 pair (T-24-13). Reasons are path-free so they can be
    recorded in the committed artifact.
    """
    if saved_run_path is None:
        return "no-saved-run"
    from sif.search.personal_bench import load_saved_run  # noqa: PLC0415 - deferred

    try:
        saved = load_saved_run(saved_run_path)
    except (OSError, ValueError):
        return "invalid-saved-run"
    saved_fingerprint = saved.corpus.get("fingerprint")
    if saved_fingerprint != live_fingerprint:
        return "corpus-fingerprint-mismatch"
    model = saved.model or {}
    if model.get("model_type") != MODEL_TYPE:
        return "model-type-mismatch"
    if model.get("model_name") != MODEL_NAME:
        return "model-name-mismatch"
    return None


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


def load_run_state(
    path: Path,
    *,
    scope_key: str,
    scope: Mapping[str, Any],
) -> dict[str, Any]:
    """Load run state under the current scope, or start a fresh one."""
    return harrier_eval.load_run_state(path, scope_key=scope_key, scope=scope)


def save_run_state(path: Path, state: Mapping[str, Any]) -> None:
    """Write run state atomically with sorted keys and a trailing newline."""
    harrier_eval.save_run_state(path, state)


def _is_known_stage(stage: str) -> bool:
    """Whether ``stage`` is one of this runbook's stage labels."""
    if stage in FINAL_STAGES:
        return True
    parts = stage.split(":")
    return len(parts) == _STAGE_PARTS and parts[0] == "arm" and parts[2] in STAGE_SUFFIXES


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


def _cleanup_scratch(scratch_root: Path, arms: Sequence[SweepArmSpec]) -> list[str]:
    """Delete only the run's own DB files/sidecars and the baseline saved run."""
    root = Path(scratch_root).resolve()
    candidates: list[Path] = []
    for arm_spec in arms:
        db_path = arm_spec.db_path
        candidates.extend(
            [
                db_path,
                Path(f"{db_path}-wal"),
                Path(f"{db_path}-shm"),
                Path(f"{db_path}.lock"),
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


def _stage_detail(  # noqa: PLR0913 - explicit stage context
    suffix: str,
    stage_entry: Mapping[str, Any],
    proc: subprocess.CompletedProcess[str],
    *,
    arm_spec: SweepArmSpec,
    cache_db_path: Path,
    elapsed: float,
) -> dict[str, Any]:
    """Build one stage's recorded detail from its process result."""
    if suffix == "index":
        fingerprint, documents = _corpus_summary(arm_spec.db_path)
        return {"corpus_fingerprint": fingerprint, "documents": documents}
    if suffix == "embed":
        return harrier_eval.collect_arm_costs(
            arm_spec.db_path,
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
    }


def _absorb_detail(suffix: str, detail: Mapping[str, Any], arm_result: dict[str, Any]) -> None:
    """Fold one stage detail into the arm's accumulated result."""
    if suffix == "embed":
        arm_result["costs"] = dict(detail)
    elif suffix == "identity":
        arm_result["identity"] = dict(detail)
    elif suffix == "eval":
        arm_result["tuning"] = detail.get("tuning")
        arm_result["heldout"] = detail.get("heldout")
        arm_result["run_path"] = detail.get("run_path")


def _execute_arm_arm_stage(  # noqa: PLR0913 - explicit stage context
    state: dict[str, Any],
    state_path: Path,
    stage_entry: Mapping[str, Any],
    arm_spec: SweepArmSpec,
    arm_result: dict[str, Any],
    *,
    cache_db_path: Path,
) -> int:
    """Run or resume one arm stage; return 0 on success and 1 on failure."""
    stage = stage_entry["stage"]
    suffix = stage.rsplit(":", 1)[-1]
    if harrier_eval.stage_done(state, stage):
        detail = (state["stages"][stage] or {}).get("detail")
        _absorb_detail(suffix, detail if isinstance(detail, Mapping) else {}, arm_result)
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
            arm_spec=arm_spec,
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
    _absorb_detail(suffix, detail, arm_result)
    mark_stage(state, stage, detail)
    save_run_state(state_path, state)
    return 0


def _arm_stages(
    arm_spec: SweepArmSpec,
    corpus_roots: Sequence[Path],
    baseline_run_path: Path | None,
) -> list[dict[str, Any]]:
    """Build one arm's stages against the chosen baseline saved run."""
    return build_arm_commands(arm_spec, corpus_roots, baseline_run_path)


def _run_stage_list(  # noqa: PLR0913 - explicit stage context
    stages: Sequence[Mapping[str, Any]],
    state: dict[str, Any],
    state_path: Path,
    arm_spec: SweepArmSpec,
    arm_result: dict[str, Any],
    *,
    cache_db_path: Path,
) -> int:
    """Run or resume a list of stages; return 0 on success and 1 on failure."""
    for stage_entry in stages:
        status = _execute_arm_arm_stage(
            state,
            state_path,
            stage_entry,
            arm_spec,
            arm_result,
            cache_db_path=cache_db_path,
        )
        if status != 0:
            return 1
    return 0


def run_stage_machine(  # noqa: C901, PLR0912, PLR0913, PLR0915
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
    """Run (or resume) the six-arm scope-keyed sweep stage machine."""
    # The guard runs before any mkdir/write/delete (T-24-01).
    scratch_root = harrier_eval.assert_within_scratch(scratch_root, scratch_root)
    scratch_root.mkdir(parents=True, exist_ok=True)
    arms = build_sweep_arms(scratch_root)
    for arm_spec in arms:
        harrier_eval.assert_within_scratch(arm_spec.db_path, scratch_root)
    saved_runs = scratch_root / "saved-runs"
    saved_runs.mkdir(parents=True, exist_ok=True)
    scope = scope_state(corpus_roots, scratch_root, corpus_label)
    state_path = scratch_root / STATE_FILE_NAME
    current_key = scope_key(scope)
    previous_key = _previous_scope_key(state_path)
    state = load_run_state(state_path, scope_key=current_key, scope=scope)
    if previous_key is not None and previous_key != current_key:
        _cleanup_scratch(scratch_root, arms)
    cache_db_path = _cache_db_path()
    results: dict[str, dict[str, Any]] = {}
    baseline_run_path = baseline_saved_run
    baseline_source = "unknown"
    live_fingerprint = ""
    baseline_arm_name = _baseline_arm_name()
    for arm_spec in arms:
        arm_result = results.setdefault(arm_spec.name, {})
        if arm_spec.name == baseline_arm_name:
            # The baseline arm's index decides whether the supplied saved run
            # is the same corpus; only then may its eval compare against it.
            all_stages = _arm_stages(arm_spec, corpus_roots, None)
            if _run_stage_list(
                all_stages[:1], state, state_path, arm_spec, arm_result, cache_db_path=cache_db_path
            ):
                return 1
            index_detail = state["stages"][all_stages[0]["stage"]].get("detail") or {}
            live_fingerprint = str(index_detail.get("corpus_fingerprint", ""))
            reason = baseline_rejection_reason(baseline_saved_run, live_fingerprint)
            if reason is None:
                baseline_source = "saved-run"
                baseline_run_path = baseline_saved_run
            else:
                baseline_source = f"fresh-baseline ({reason})"
                baseline_run_path = None
            remaining = _arm_stages(arm_spec, corpus_roots, baseline_run_path)[1:]
            if _run_stage_list(
                remaining, state, state_path, arm_spec, arm_result, cache_db_path=cache_db_path
            ):
                return 1
            if baseline_run_path is None:
                run_path = arm_result.get("run_path")
                if not isinstance(run_path, str) or not run_path:
                    _emit_err("FAIL baseline eval did not report a saved run path")
                    return 1
                target = harrier_eval.assert_within_scratch(
                    saved_runs / "baseline.json", scratch_root
                )
                shutil.copy2(Path(run_path), target)
                baseline_run_path = target
            continue
        if _run_stage_list(
            _arm_stages(arm_spec, corpus_roots, baseline_run_path),
            state,
            state_path,
            arm_spec,
            arm_result,
            cache_db_path=cache_db_path,
        ):
            return 1
    code, artifact = finalize_sweep(
        grid=_sweep_grid(),
        results=results,
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
        _cleanup_scratch(scratch_root, arms)
    if output_json:
        print(json.dumps(artifact, indent=2, sort_keys=True))  # noqa: T201 - CLI output
    else:
        print(  # noqa: T201 - CLI output
            f"PASS decision={artifact['decision']} artifact={artifact_path or ARTIFACT_PATH}"
        )
    return code


# -- Artifact ----------------------------------------------------------------


def build_arms_payload(
    grid: Sequence[ChunkArm],
    results: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build the per-arm aggregate records in fixed grid order."""
    arms_payload: list[dict[str, Any]] = []
    for arm in grid:
        result = results.get(arm.name) or {}
        costs = result.get("costs") or {}
        tuning = result.get("tuning") or {}
        heldout = result.get("heldout") or {}
        identity = result.get("identity") or {}
        arms_payload.append(
            {
                "name": arm.name,
                "chunk_size": arm.chunk_size,
                "chunk_overlap": arm.chunk_overlap,
                "documents": costs.get("documents"),
                "chunks": costs.get("chunks"),
                "embedded_documents": costs.get("embedded_documents"),
                "embed_wall_seconds": costs.get("embed_wall_seconds"),
                "cache_rows_before": costs.get("cache_rows_before"),
                "cache_rows_after": costs.get("cache_rows_after"),
                "cache_hits": costs.get("cache_hits"),
                "tuning_mean_delta": tuning.get("mean_delta"),
                "heldout_mean_delta": heldout.get("mean_delta"),
                "heldout_winner": heldout.get("winner"),
                "heldout_sufficient": heldout.get("sufficient"),
                "identity": {key: identity.get(key) for key in IDENTITY_KEYS},
            }
        )
    return arms_payload


def build_sweep_artifact(
    *,
    grid: Sequence[ChunkArm],
    results: Mapping[str, Mapping[str, Any]],
    corpus_label: str,
    corpus_fingerprint: str,
    baseline_source: str,
) -> dict[str, Any]:
    """Build the committed aggregate envelope in its documented key order."""
    from sif.search.tuning_verdict import (  # noqa: PLC0415 - deferred sif import
        decide_chunk_default,
        select_tuning_candidate,
    )

    arms_payload = build_arms_payload(grid, results)
    selection: dict[str, dict[str, Any]] = {}
    for index, arm_payload in enumerate(arms_payload):
        mean_delta = arm_payload["tuning_mean_delta"]
        wall_seconds = arm_payload["embed_wall_seconds"]
        selection[arm_payload["name"]] = {
            "mean_delta": 0.0 if mean_delta is None else float(mean_delta),
            "embed_wall_seconds": 0.0 if wall_seconds is None else float(wall_seconds),
            "grid_index": index,
        }
    selected = select_tuning_candidate(selection)
    selected_result = results.get(selected or "") or {}
    tuning = selected_result.get("tuning") or {}
    confirmation = selected_result.get("heldout") or {
        "n": 0,
        "mean_delta": 0.0,
        "winner": False,
        "sufficient": False,
    }
    decision = decide_chunk_default(selected, tuning.get("mean_delta"), confirmation)
    confirmation_n = int(confirmation.get("n", 0) or 0)
    return {
        "schema_version": 1,
        "decision": decision.decision,
        "selected_arm": decision.selected_arm,
        "tuning_mean_delta": decision.tuning_mean_delta,
        "confirmation": dict(confirmation),
        "arms": arms_payload,
        "grid": [
            {
                "name": arm.name,
                "chunk_size": arm.chunk_size,
                "chunk_overlap": arm.chunk_overlap,
            }
            for arm in grid
        ],
        "model_name": MODEL_NAME,
        "model_type": MODEL_TYPE,
        "embedding_dim": EMBEDDING_DIM,
        "max_tokens": MAX_TOKENS,
        "corpus_label": corpus_label,
        "corpus_fingerprint": corpus_fingerprint,
        "baseline_source": baseline_source,
        "selection_rule": SELECTION_RULE,
        "min_heldout_for_epsilon_win": MIN_HELDOUT_FOR_EPSILON_WIN,
        "limitation": build_limitation(corpus_label, confirmation_n),
    }


def write_committed_artifact(
    artifact: Mapping[str, Any],
    *,
    force: bool = False,
    path: Path | None = None,
) -> Path:
    """Write the committed evidence, never silently replacing another run.

    A same-decision, same-fingerprint rewrite is allowed; a different
    decision or corpus fingerprint requires an explicit ``--force`` (T-24-01).
    """
    target = Path(path) if path is not None else ARTIFACT_PATH
    existing: Mapping[str, Any] | None = None
    if target.is_file():
        try:
            loaded = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            loaded = None
        if isinstance(loaded, Mapping):
            existing = loaded
    if existing is not None:
        old_identity = (existing.get("decision"), existing.get("corpus_fingerprint"))
        new_identity = (artifact.get("decision"), artifact.get("corpus_fingerprint"))
        if not force and old_identity != new_identity:
            raise RuntimeError(
                f"refusing to overwrite {target}: recorded decision/corpus "
                f"{old_identity!r} differs from this run's {new_identity!r}; "
                "pass --force to replace it"
            )
    return harrier_eval.write_json(target, artifact)


def finalize_sweep(  # noqa: PLR0913 - one keyword per artifact input
    *,
    grid: Sequence[ChunkArm],
    results: Mapping[str, Mapping[str, Any]],
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

    artifact = build_sweep_artifact(
        grid=grid,
        results=results,
        corpus_label=corpus_label,
        corpus_fingerprint=corpus_fingerprint,
        baseline_source=baseline_source,
    )
    write_committed_artifact(artifact, force=force, path=artifact_path)
    code = 3 if artifact["decision"] == DECISION_INSUFFICIENT else 0
    return code, artifact


def build_parser() -> argparse.ArgumentParser:
    """Build the runbook argument parser."""
    parser = argparse.ArgumentParser(
        description="Run the six-arm held-out-gated chunk size/overlap sweep.",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        action="append",
        default=None,
        help="Corpus root to index into every arm (repeatable; roots must be disjoint)",
    )
    parser.add_argument(
        "--scratch-root",
        type=Path,
        default=DEFAULT_SCRATCH_ROOT,
        help="Scratch directory for arm DBs, saved runs, and run state",
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
        help="Print the full six-arm stage plan and exit without a subprocess",
    )
    parser.add_argument(
        "--keep-arms",
        action="store_true",
        help="Keep the scratch arm DBs and saved runs after the verdict",
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
