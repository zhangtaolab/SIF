#!/usr/bin/env python3
"""Two-arm Harrier vs Qwen3 evaluation runbook (Phase 23, MODEL-01/MODEL-02).

The runbook builds two fully isolated, file-backed indexes from the same
resolved corpus roots, one per embedder arm (D-01), proves each arm's stored
embedder identity (including the Harrier query prompt), checks EN+ZH held-out
adequacy before the embed budget is spent, records cost/provenance, and
writes one committed aggregate artifact. Every ``sif`` stage is an explicit
argv-list subprocess under its own per-arm environment: ``get_settings()`` is
process-cached, so an in-process arm switch would silently measure the wrong
model (research Pitfall 8).

This module is stdlib-only at import time; ``sif`` imports are deferred into
the probe, identity, and preflight helpers so ``--dry-run`` works without the
embedding stack.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
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


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCRATCH_ROOT = PROJECT_ROOT / ".planning" / "tmp" / "phase-23"
ARTIFACT_PATH = (
    PROJECT_ROOT
    / ".planning"
    / "phases"
    / "23-harrier-gated-evaluation"
    / "bench"
    / "harrier-verdict.json"
)
QWEN3_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
QWEN3_MODEL_TYPE = "modelscope"
HARRIER_MODEL_NAME = "microsoft/harrier-oss-v1-0.6b"
HARRIER_MODEL_TYPE = "sentence_transformers"
QWEN3_CACHE_MODEL_ID = "modelscope:Qwen/Qwen3-Embedding-0.6B"
HARRIER_QUERY_PROMPT = "web_search_query"
REQUIRED_LANGUAGES = ("en", "zh")
EMBEDDING_DIM = 1024
MAX_TOKENS = 512
BATCH_SIZE = 32
CHUNK_SIZE = 512
CHUNK_OVERLAP = 128
COLLECTION_PREFIX = "phase23"
PINNED_ENV = (
    "SIF_EMBEDDING_DIM",
    "SIF_MAX_TOKENS",
    "SIF_BATCH_SIZE",
    "SIF_CHUNK_SIZE",
    "SIF_CHUNK_OVERLAP",
)
PROMPT_ENV = ("SIF_QUERY_PROMPT_NAME", "SIF_DOCUMENT_PROMPT_NAME")
REMOVED_ENV = (
    "SIF_MODEL_PATH",
    "SIF_DB_PATH",
    "SIF_API_BASE",
    "SIF_API_KEY",
    *PROMPT_ENV,
)
PROBE_TIMEOUT_SECONDS = 300
STAGE_TIMEOUT_SECONDS = 6 * 60 * 60
MIN_FREE_DISK_BYTES = 10 * 1024**3
EXAMPLE_CORPUS_ROOT = PROJECT_ROOT / "example-corpus"
SCRATCH_DB_NAMES = ("qwen3", "harrier")
MIN_HELDOUT_FOR_EPSILON_WIN = 101
_REPLAY_NOTE = (
    "Scratch arms have no query_log history; replay stability is unavailable "
    "and never enters the verdict."
)

if TYPE_CHECKING:
    from sif.embedding.identity import EmbedderIdentity
    from sif.search.embedder_verdict import VerdictDecision


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


def _now() -> str:
    """UTC timestamp for run-state records."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _emit_err(line: str) -> None:
    """Write one failure/guard line to stderr."""
    sys.stderr.write(line + "\n")


def build_arm(name: str, scratch_root: Path) -> ArmSpec:
    """Build the named arm with its DB under the scratch root."""
    if name == "qwen3":
        return ArmSpec(
            name=name,
            model_type=QWEN3_MODEL_TYPE,
            model_name=QWEN3_MODEL_NAME,
            db_path=Path(scratch_root) / "qwen3.db",
        )
    if name == "harrier":
        return ArmSpec(
            name=name,
            model_type=HARRIER_MODEL_TYPE,
            model_name=HARRIER_MODEL_NAME,
            db_path=Path(scratch_root) / "harrier.db",
        )
    raise ValueError(f"unknown arm: {name!r}")


def build_arms(scratch_root: Path) -> dict[str, ArmSpec]:
    """Build both arms, in the fixed Qwen3-then-Harrier order."""
    return {
        "qwen3": build_arm("qwen3", scratch_root),
        "harrier": build_arm("harrier", scratch_root),
    }


def build_arm_env(base_env: Mapping[str, str], arm: ArmSpec) -> dict[str, str]:
    """Copy ``base_env`` and pin one arm's values, removing every override.

    ``SIF_API_BASE``/``SIF_API_KEY`` are removed, not blanked, so an inherited
    API base cannot change the Qwen3 arm's ``cache_model_id`` (the identity
    gate requires the exact ``modelscope:Qwen/Qwen3-Embedding-0.6B``) and no
    credentials leak into either local arm. The prompt keys are removed for
    the same reason: the known-model table must supply Harrier's
    ``web_search_query``, while an empty string would disable it.
    """
    env = dict(base_env)
    for key in REMOVED_ENV:
        env.pop(key, None)
    env.update(
        {
            "SIF_MODEL_TYPE": arm.model_type,
            "SIF_MODEL_NAME": arm.model_name,
            "SIF_EMBEDDING_DIM": str(EMBEDDING_DIM),
            "SIF_MAX_TOKENS": str(MAX_TOKENS),
            "SIF_BATCH_SIZE": str(BATCH_SIZE),
            "SIF_CHUNK_SIZE": str(CHUNK_SIZE),
            "SIF_CHUNK_OVERLAP": str(CHUNK_OVERLAP),
            "SIF_CACHE_EMBEDDINGS": "1",
        }
    )
    return env


def build_arm_commands(
    python: str,
    arm: ArmSpec,
    corpus_roots: Sequence[Path],
    *,
    saved_run_path: Path | None = None,
) -> list[ArmCommand]:
    """Build the ordered argv-only stage table for one arm.

    Every command is ``-q`` (ModelScope pollutes stdout even on a cache hit)
    and carries ``--index``; no command is a shell string. The baseline eval
    names both required languages; the candidate eval re-evaluates the saved
    query set with ``--compare`` and never resamples, so it takes no
    ``--require-language`` and no prompt override.
    """
    base = [python, "-m", "sif.cli.main", "-q", "--index", str(arm.db_path)]
    env = build_arm_env(os.environ, arm)
    commands: list[ArmCommand] = []
    for index, root in enumerate(corpus_roots, start=1):
        commands.append(
            ArmCommand(
                stage=f"collection_add_{index}",
                argv=[
                    *base,
                    "collection",
                    "add",
                    str(root),
                    "--name",
                    f"{COLLECTION_PREFIX}-{index}",
                ],
                env=env,
            )
        )
    commands.append(ArmCommand(stage="index_update", argv=[*base, "index", "update"], env=env))
    commands.append(
        ArmCommand(
            stage="index_embed",
            argv=[*base, "index", "embed", "--force", "--chunk-strategy", "auto"],
            env=env,
        )
    )
    if saved_run_path is None:
        eval_argv = [
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
        eval_argv = [
            *base,
            "eval",
            "--personal",
            "--all",
            "--compare",
            str(saved_run_path),
            "--json",
        ]
    commands.append(ArmCommand(stage="eval", argv=eval_argv, env=env))
    return commands


def _env_summary(env: Mapping[str, str]) -> dict[str, Any]:
    """Record only the pinned values and the explicitly removed keys."""
    pinned = {
        key: env[key]
        for key in ("SIF_MODEL_TYPE", "SIF_MODEL_NAME", *PINNED_ENV, "SIF_CACHE_EMBEDDINGS")
    }
    return {"pinned": pinned, "removed": list(REMOVED_ENV)}


def build_dry_run_payload(
    python: str,
    arms: Mapping[str, ArmSpec],
    corpus_roots: Sequence[Path],
    artifact_path: Path,
) -> dict[str, Any]:
    """Return the full two-arm plan without invoking a subprocess."""
    qwen3 = arms["qwen3"]
    harrier = arms["harrier"]
    saved_run_path = harrier.db_path.parent / "saved-runs" / "qwen3.json"
    commands: dict[str, list[dict[str, Any]]] = {}
    for arm in (qwen3, harrier):
        arm_saved_run = None if arm.name == "qwen3" else saved_run_path
        commands[arm.name] = [
            {
                "stage": command.stage,
                "argv": list(command.argv),
                "env_summary": _env_summary(command.env),
            }
            for command in build_arm_commands(
                python,
                arm,
                corpus_roots,
                saved_run_path=arm_saved_run,
            )
        ]
    return {
        "version": 1,
        "artifact_path": str(artifact_path),
        "arms": [
            {
                "name": arm.name,
                "model_type": arm.model_type,
                "model_name": arm.model_name,
                "db_path": str(arm.db_path),
            }
            for arm in (qwen3, harrier)
        ],
        "commands": commands,
        "planned_artifact": {
            "path": str(artifact_path),
            "version": 1,
            "decision": "computed at the verdict stage",
            "min_heldout_for_epsilon_win": MIN_HELDOUT_FOR_EPSILON_WIN,
            "required_languages": list(REQUIRED_LANGUAGES),
            "arms": [qwen3.name, harrier.name],
        },
    }


def resolve_corpus_roots(roots: Sequence[Path]) -> tuple[Path, ...]:
    """Resolve corpus roots and refuse duplicates or nesting.

    A duplicate root would index the same document path into two collections,
    and a nested pair would do the same across collections; both make
    ``--compare``'s saved-target resolution ambiguous. The supplied order is
    preserved because it determines the ``phase23-<n>`` collection names.
    """
    resolved: list[Path] = []
    for raw_root in roots:
        root = Path(raw_root).resolve()
        if root in resolved:
            raise ValueError(f"duplicate corpus root: {root}")
        for other in resolved:
            if root.is_relative_to(other) or other.is_relative_to(root):
                raise ValueError(f"nested corpus roots: {other} and {root}")
        resolved.append(root)
    return tuple(resolved)


def build_parser() -> argparse.ArgumentParser:
    """Build the runbook argument parser."""
    parser = argparse.ArgumentParser(
        description="Run the two-arm Harrier vs Qwen3 gated evaluation.",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        action="append",
        default=None,
        help="Corpus root to index into both arms (repeatable; all roots must be disjoint)",
    )
    parser.add_argument(
        "--scratch-root",
        type=Path,
        default=DEFAULT_SCRATCH_ROOT,
        help="Scratch directory for arm DBs, saved runs, and run state",
    )
    parser.add_argument("--corpus-label", default="personal", help="Aggregate corpus label")
    parser.add_argument(
        "--keep-arms",
        action="store_true",
        help="Keep the scratch arm DBs and saved runs after the verdict",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the full two-arm command plan as JSON and exit",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Build the baseline arm and run the EN+ZH adequacy preflight only",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    parser.add_argument("--probe", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--arm",
        choices=("qwen3", "harrier"),
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the requested mode; return 0 success, 1 failure, 2 refusal, 3 short."""
    args = build_parser().parse_args(argv)
    if args.probe:
        _emit_err("FAIL --probe is an internal stage; run the full runbook")
        return 2
    roots = list(args.corpus) if args.corpus else [EXAMPLE_CORPUS_ROOT]
    try:
        corpus_roots = resolve_corpus_roots(roots)
    except ValueError as exc:
        _emit_err(f"REFUSED: {exc}")
        return 2
    arms = build_arms(Path(args.scratch_root))
    if args.dry_run:
        payload = build_dry_run_payload(sys.executable, arms, corpus_roots, ARTIFACT_PATH)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    _emit_err("FAIL run mode is not wired yet")
    return 1


if __name__ == "__main__":
    sys.exit(main())
