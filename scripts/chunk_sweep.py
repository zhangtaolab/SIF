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

This module is stdlib-only at import time; ``sif`` imports are deferred into
the probe and baseline helpers so ``--dry-run`` works without the embedding
stack.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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
    / "phases"
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
EXPECTED_CORPUS_FINGERPRINT = "b5d50ce0c696ab3d"
MIN_HELDOUT_FOR_EPSILON_WIN = 101
LIMITATION = (
    "The Phase 23 curated corpus has 56 held-out queries, below the 101 needed "
    "for a 0.01 mean-delta win, so only keep-default or insufficient-evidence "
    "is reachable until a larger corpus is supplied."
)
# Reuse the Phase 23 removals and additionally drop the breadcrumb switch: a
# breadcrumb setting must never leak into a sweep arm (D-04, D-05).
REMOVED_ENV = (*harrier_eval.REMOVED_ENV, "SIF_EMBED_BREADCRUMB")
PINNED_ENV = harrier_eval.PINNED_ENV
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
    shell string. The baseline arm evaluated without a saved run names both
    required languages; every comparison eval re-evaluates the saved query set
    with ``--compare`` and never resamples.
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
        "expected_corpus_fingerprint": EXPECTED_CORPUS_FINGERPRINT,
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


def main(argv: list[str] | None = None) -> int:
    """Run the requested mode; return 0 success, 2 refusal, 3 short (Task 2)."""
    args = build_parser().parse_args(argv)
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
    if args.probe_identity:
        _emit_err("REFUSED: the identity probe is not available in this revision")
        return 2
    _emit_err("REFUSED: the sweep stage machine is not available in this revision")
    return 2


if __name__ == "__main__":
    sys.exit(main())
