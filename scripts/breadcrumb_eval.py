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
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


try:  # Running as ``python scripts/breadcrumb_eval.py``: scripts/ is sys.path[0].
    import chunk_sweep
    import harrier_eval
except ImportError:  # Imported as ``scripts.breadcrumb_eval`` or spec-loaded.
    from scripts import chunk_sweep, harrier_eval


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
    "The Phase 23 curated corpus has 56 held-out queries, below the 101 needed "
    "for a 0.01 mean-delta win, so insufficient-evidence is the expected "
    "outcome until a larger corpus is supplied; the result is corpus-scoped."
)
STATE_FILE_NAME = "run-state.json"
STAGE_TIMEOUT_SECONDS = 6 * 60 * 60
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


def main(argv: list[str] | None = None) -> int:
    """Run the requested mode; return 0 success, 1 failure, 2 refusal, 3 short."""
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
    _emit_err("FAIL: the stage machine is not available in this build")
    return 1


if __name__ == "__main__":
    sys.exit(main())
