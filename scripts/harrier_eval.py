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
import importlib.metadata
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


class IdentityGateError(ValueError):
    """One arm (or the arm pair) failed the embedder identity gate."""

    def __init__(self, arm: str, failures: Sequence[str]) -> None:
        """Record the arm and every failed check."""
        self.arm = arm
        self.failures = tuple(failures)
        detail = "; ".join(self.failures)
        super().__init__(f"embedder identity gate failed for {arm}: {detail}")


def verify_arm_identity(stored: EmbedderIdentity | None, arm: ArmSpec) -> None:
    """Raise unless the stored identity is this arm's verified vector space.

    The Qwen3 arm must stay byte-identical to the shipped default: the exact
    ``modelscope:Qwen/Qwen3-Embedding-0.6B`` cache id and no prompts. The
    Harrier arm must carry the known-model table's ``web_search_query`` query
    prompt and no document prompt. Width alone is not a guard: both models
    are 1024-dimensional.
    """
    if stored is None:
        raise IdentityGateError(arm.name, ["no stored embedder identity"])
    failures: list[str] = []
    if stored.source != "verified":
        failures.append(f"source is {stored.source!r}, expected 'verified'")
    if stored.dimension != EMBEDDING_DIM:
        failures.append(f"dimension is {stored.dimension}, expected {EMBEDDING_DIM}")
    if stored.model_name != arm.model_name:
        failures.append(f"model_name is {stored.model_name!r}, expected {arm.model_name!r}")
    if stored.model_type != arm.model_type:
        failures.append(f"model_type is {stored.model_type!r}, expected {arm.model_type!r}")
    if arm.name == "harrier":
        if stored.query_prompt != HARRIER_QUERY_PROMPT:
            failures.append(
                f"query_prompt is {stored.query_prompt!r}, expected {HARRIER_QUERY_PROMPT!r}"
            )
        if stored.document_prompt is not None:
            failures.append(f"document_prompt is {stored.document_prompt!r}, expected None")
    elif arm.name == "qwen3":
        if stored.cache_model_id != QWEN3_CACHE_MODEL_ID:
            failures.append(
                f"cache_model_id is {stored.cache_model_id!r}, expected {QWEN3_CACHE_MODEL_ID!r}"
            )
        if stored.query_prompt is not None:
            failures.append(f"query_prompt is {stored.query_prompt!r}, expected None")
        if stored.document_prompt is not None:
            failures.append(f"document_prompt is {stored.document_prompt!r}, expected None")
    if failures:
        raise IdentityGateError(arm.name, failures)


def verify_arm_pair(qwen3: EmbedderIdentity, harrier: EmbedderIdentity) -> None:
    """Raise when the two arms resolve to the same vector space.

    A single stored identity cannot see its peer, so the same-fingerprint and
    same-cache-bucket cases need this pairwise check (the same-width silent
    swap). It runs at the ``arm_b_identity`` stage, after both identities
    exist.
    """
    failures: list[str] = []
    if qwen3.fingerprint() == harrier.fingerprint():
        failures.append("both arms have identical identity fingerprints")
    if qwen3.cache_model_id == harrier.cache_model_id:
        failures.append(f"both arms resolve to cache_model_id {qwen3.cache_model_id!r}")
    if failures:
        raise IdentityGateError("pair", failures)


def probe_arm_command(python: str, arm: ArmSpec) -> list[str]:
    """Build the probe argv; the caller runs it under the arm env."""
    return [
        python,
        str(Path(__file__).resolve()),
        "--probe",
        "--arm",
        arm.name,
        "--scratch-root",
        str(arm.db_path.parent),
    ]


def require_probe_ok(payload: Mapping[str, Any], arm: ArmSpec) -> None:
    """Require a search-mode ``ok`` status and the expected full identity."""
    from sif.embedding.identity import EmbedderIdentity  # noqa: PLC0415

    status = payload.get("check_identity_status")
    if status != "ok":
        raise IdentityGateError(
            arm.name,
            [f"check_identity status is {status!r}, expected 'ok'"],
        )
    identity_payload = payload.get("identity")
    if not isinstance(identity_payload, Mapping):
        raise IdentityGateError(arm.name, ["probe payload has no identity object"])
    identity = EmbedderIdentity.from_json(json.dumps(identity_payload))
    verify_arm_identity(identity, arm)


STAGES = (
    "env_preflight",
    "arm_a_index",
    "adequacy",
    "arm_a_embed",
    "arm_a_probe",
    "arm_a_eval",
    "arm_b_index",
    "arm_b_identity",
    "arm_b_embed",
    "arm_b_probe",
    "arm_b_eval",
    "verdict",
    "artifact",
)


def scope_state(
    corpus_roots: Sequence[Path],
    scratch_root: Path,
    corpus_label: str,
) -> dict[str, Any]:
    """Describe the resolved corpus scope that invalidates prior markers."""
    return {
        "corpus_roots": [str(Path(root).resolve()) for root in corpus_roots],
        "corpus_label": corpus_label,
        "scratch_root": str(Path(scratch_root).resolve()),
    }


def scope_key(scope: Mapping[str, Any]) -> str:
    """Hash the sorted resolved roots plus the label to 16 hex chars."""
    roots = sorted(str(root) for root in scope.get("corpus_roots", []))
    lines = [*roots, str(scope.get("corpus_label", ""))]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:16]


def load_run_state(
    path: Path,
    *,
    scope_key: str,
    scope: Mapping[str, Any],
) -> dict[str, Any]:
    """Load run state under the current, or start a fresh one.

    A missing, unreadable, or differently scoped file discards every prior
    stage marker: skipping work against a changed ``--corpus`` set would
    evaluate the wrong corpus.
    """
    fresh: dict[str, Any] = {
        "version": 1,
        "scope_key": scope_key,
        "scope": dict(scope),
        "started_at": _now(),
        "stages": {},
    }
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return fresh
    if not isinstance(payload, dict) or payload.get("scope_key") != scope_key:
        return fresh
    if not isinstance(payload.get("stages"), dict):
        payload["stages"] = {}
    payload.setdefault("version", 1)
    payload.setdefault("scope", dict(scope))
    payload.setdefault("started_at", fresh["started_at"])
    return payload


def save_run_state(path: Path, state: Mapping[str, Any]) -> None:
    """Write run state atomically with sorted keys and a trailing newline."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, indent=2, sort_keys=True) + "\n"
    temporary = target.with_name(f"{target.name}.tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(target)


def write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    """Write one local JSON record atomically with sorted keys."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
    return target


def stage_done(state: Mapping[str, Any], stage: str) -> bool:
    """Whether ``stage`` is recorded complete in this scope."""
    stages = state.get("stages")
    if not isinstance(stages, Mapping):
        return False
    entry = stages.get(stage)
    return isinstance(entry, Mapping) and entry.get("status") == "complete"


def mark_stage(state: dict[str, Any], stage: str, detail: Any = None) -> None:
    """Mark ``stage`` complete with an optional machine-readable detail."""
    if stage not in STAGES:
        raise ValueError(f"unknown stage: {stage!r}")
    stages = state.setdefault("stages", {})
    stages[stage] = {"status": "complete", "at": _now(), "detail": detail}


def run_command(
    command: ArmCommand,
    *,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one argv-list command from the project root; never a shell."""
    try:
        return subprocess.run(
            command.argv,
            cwd=PROJECT_ROOT,
            env=command.env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{command.stage} timed out after {timeout} seconds") from exc


_IDENTITY_MISMATCH_LITERAL = "Embedder identity mismatch"


def parse_json_stdout(
    proc: subprocess.CompletedProcess[str],
    stage: str,
) -> Any:
    """Parse one stage's strict JSON stdout, failing loudly on guard text.

    Only the ``check_identity`` guard literal fails here. The expected
    ``--compare`` cross-model notice (``Model identity differs:``) is the
    D-05 workflow and is informational.
    """
    if proc.returncode != 0:
        raise RuntimeError(
            f"{stage} failed with exit {proc.returncode}: {proc.stderr[-4000:]}"
        )
    if _IDENTITY_MISMATCH_LITERAL in proc.stderr:
        raise RuntimeError(
            f"{stage} reported an embedder identity mismatch: {proc.stderr[-4000:]}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{stage} did not emit JSON (stdout {proc.stdout[-2000:]!r}): {exc}"
        ) from exc


def _connect_read_only(db_path: Path) -> sqlite3.Connection:
    """Open one read-only connection, loading sqlite-vec best-effort."""
    uri = f"file:{Path(db_path).resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        import sqlite_vec  # noqa: PLC0415

        conn.enable_load_extension(True)
        try:
            sqlite_vec.load(conn)
        finally:
            conn.enable_load_extension(False)
    except (AttributeError, ImportError, sqlite3.Error):
        pass
    return conn


def _read_stored_identity(db_path: Path) -> EmbedderIdentity | None:
    """Read one arm's stored identity with a real sqlite-vec connection."""
    from sif.embedding.identity import read_identity  # noqa: PLC0415

    conn = _connect_read_only(db_path)
    try:
        return read_identity(conn)
    finally:
        conn.close()


def _model_device(manager: Any) -> str:
    """Best-effort device label from the loaded embedder wrapper."""
    embedder = getattr(manager, "model", None)
    for candidate in (getattr(embedder, "model", None), embedder):
        device = getattr(candidate, "device", None)
        if device is not None:
            return str(device)
    return "unknown"


def _run_probe(arm_name: str, scratch_root: Path) -> int:
    """Load one arm's model under its env and print the identity JSON."""
    try:
        from sif.config.settings import get_settings  # noqa: PLC0415
        from sif.embedding.identity import check_identity  # noqa: PLC0415
        from sif.embedding.manager import EmbeddingManager  # noqa: PLC0415
        from sif.utils.logging import set_quiet  # noqa: PLC0415
    except ImportError as exc:
        _emit_err(f"FAIL probe {arm_name}: {exc}")
        return 4
    arm = build_arm(arm_name, scratch_root)
    set_quiet(True)
    try:
        settings = get_settings()
        manager = EmbeddingManager.from_settings(settings)
        identity = manager.get_identity()
        conn = _connect_read_only(arm.db_path)
        try:
            check = check_identity(conn, identity, mode="search")
        finally:
            conn.close()
        cache_db_path = Path(settings.get_cache_dir()) / "embeddings_cache.db"
    except Exception as exc:  # noqa: BLE001 - probe maps any load failure to exit 4
        _emit_err(f"FAIL probe {arm_name}: {exc}")
        return 4
    payload = {
        "arm": arm_name,
        "identity": json.loads(identity.to_json()),
        "check_identity_status": check.status,
        "dimension": identity.dimension,
        "pooling": identity.pooling,
        "revision": identity.revision,
        "device": _model_device(manager),
        "cache_db_path": str(cache_db_path),
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


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


def preflight_adequacy(
    db_path: Path,
    *,
    required_languages: Sequence[str] = REQUIRED_LANGUAGES,
) -> dict[str, Any]:
    """Run the EN+ZH adequacy preflight on one arm DB before embedding.

    Adequacy is the Phase 18 instrument's own language-aware widening; an
    inadequate corpus returns its sampled/language counts instead of raising,
    so the runbook can record the honest outcome and never claim a verdict.
    """
    from sif.search.personal_bench import (  # noqa: PLC0415
        HeldoutFloorError,
        ensure_heldout,
        heldout_language_counts,
        load_document_metadata,
    )

    try:
        conn = _connect_read_only(db_path)
    except sqlite3.Error as exc:
        raise RuntimeError(f"adequacy preflight could not open {db_path.name}: {exc}") from exc
    try:
        metadata = load_document_metadata(conn, None)
        try:
            sampled, synthesis = ensure_heldout(
                metadata,
                conn,
                required_languages=required_languages,
            )
        except HeldoutFloorError as exc:
            return {
                "adequate": False,
                "sampled": exc.sampled,
                "counts": dict(exc.language_counts),
                "accepted": exc.accepted,
                "heldout": exc.heldout,
            }
        counts = heldout_language_counts(synthesis.queries)
        return {
            "adequate": True,
            "sampled": len(sampled),
            "counts": counts,
            "accepted": len(synthesis.queries),
            "heldout": sum(counts.values()),
        }
    except (ValueError, sqlite3.Error) as exc:
        raise RuntimeError(f"adequacy preflight failed for {db_path.name}: {exc}") from exc
    finally:
        conn.close()


def assert_disk_headroom(
    scratch_root: Path,
    *,
    minimum_bytes: int = MIN_FREE_DISK_BYTES,
) -> None:
    """Refuse a multi-GB two-arm run below the free-space floor."""
    free = shutil.disk_usage(scratch_root).free
    if free < minimum_bytes:
        raise RuntimeError(
            f"insufficient disk space for the two-arm run: {free} bytes free, "
            f"{minimum_bytes} required"
        )


def query_set_fingerprint(saved_run: Mapping[str, Any]) -> str:
    """Hash the saved query set to 16 hex chars; target ids are excluded.

    Target doc ids are per-arm UUIDs, so including them would make two
    identical query sets hash differently. Every field that defines the
    measured query is included.
    """
    queries = saved_run.get("queries")
    if not isinstance(queries, list):
        raise ValueError("saved run is missing a 'queries' list")
    lines: list[str] = []
    for record in queries:
        if not isinstance(record, Mapping):
            raise ValueError("saved run queries must be JSON objects")
        try:
            line = (
                f"{record['leg']}\0{record['language']}\0{record['split']}\0"
                f"{record['query']}"
            )
        except KeyError as exc:
            raise ValueError(f"saved run query is missing {exc.args[0]!r}") from exc
        lines.append(line)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:16]


def _pair_query_set_fingerprint(
    qwen3_saved_run: Path,
    harrier_saved_run: Path,
) -> str | None:
    """Fingerprint the paired saved query sets, or None when either is absent.

    A recorded verdict whose scratch runs were cleaned up after a completed
    run is still a valid resume: there is nothing left to disagree with.
    When both runs exist the arms must name the same query set (the
    ``--compare`` pairing contract).
    """
    paths = (Path(qwen3_saved_run), Path(harrier_saved_run))
    if not all(path.is_file() for path in paths):
        return None
    fingerprints = [
        query_set_fingerprint(json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]
    if fingerprints[0] != fingerprints[1]:
        raise RuntimeError(
            "query-set fingerprint mismatch between arms: "
            f"{fingerprints[0]} vs {fingerprints[1]}"
        )
    return fingerprints[0]


def _cache_rows(cache_db_path: Path, cache_model_id: str | None) -> int:
    """Count cache rows for one arm's bucket prefix; never write."""
    cache_db_path = Path(cache_db_path)
    if not cache_db_path.exists():
        return 0
    try:
        conn = sqlite3.connect(
            f"file:{cache_db_path.resolve().as_posix()}?mode=ro",
            uri=True,
        )
    except sqlite3.Error:
        return 0
    try:
        rows = conn.execute(
            "SELECT model_id, COUNT(*) FROM embeddings GROUP BY model_id"
        ).fetchall()
    except sqlite3.Error:
        return 0
    finally:
        conn.close()
    if cache_model_id is None:
        return sum(int(count) for _model_id, count in rows)
    return sum(
        int(count)
        for model_id, count in rows
        if str(model_id).startswith(cache_model_id)
    )


def _db_counts(db_path: Path) -> dict[str, int]:
    """Count documents, chunks, and vectors in one arm DB."""
    conn = _connect_read_only(db_path)
    counts: dict[str, int] = {}
    try:
        for table in ("documents", "document_chunks", "embedded_documents"):
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            except sqlite3.Error:
                counts[table] = 0
                continue
            counts[table] = int(row[0]) if row is not None else 0
    finally:
        conn.close()
    return counts


def collect_arm_costs(
    db_path: Path,
    cache_db_path: Path,
    wall_seconds: float,
    *,
    cache_model_id: str | None = None,
    cache_rows_before: int | None = None,
) -> dict[str, Any]:
    """Aggregate one arm's counts, wall time, and shared-cache deltas."""
    counts = _db_counts(db_path)
    cache_rows_after = _cache_rows(cache_db_path, cache_model_id)
    cache_hits: int | None = None
    if cache_rows_before is not None:
        added = max(0, cache_rows_after - cache_rows_before)
        cache_hits = max(0, counts["document_chunks"] - added)
    return {
        "documents": counts["documents"],
        "chunks": counts["document_chunks"],
        "embedded_documents": counts["embedded_documents"],
        "embed_wall_seconds": round(float(wall_seconds), 3),
        "cache_rows_before": cache_rows_before,
        "cache_rows_after": cache_rows_after,
        "cache_hits": cache_hits,
    }


_PACKAGE_NAMES = ("sentence-transformers", "transformers", "torch", "modelscope")


def _git_value(args: Sequence[str]) -> str:
    """Read one git value from the project root; empty on any failure."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def collect_environment(*, device: str | None = None) -> dict[str, Any]:
    """Record the Python/platform/package stack, git provenance, and device.

    Never records interpreter paths or user home paths.
    """
    packages: dict[str, str] = {}
    missing: list[str] = []
    for name in _PACKAGE_NAMES:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = ""
            missing.append(name)
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
        "missing_packages": missing,
        "git_head": _git_value(["rev-parse", "HEAD"]),
        "git_dirty": bool(_git_value(["status", "--porcelain"])),
        "device": device or "unknown",
    }


def build_artifact(
    *,
    decision: VerdictDecision,
    arms: Mapping[str, Any],
    corpus: Mapping[str, Any],
    query_set_fingerprint: str | None,
    gates: Mapping[str, Any],
    environment: Mapping[str, Any],
    replay_available: bool,
    notes: Sequence[str],
) -> dict[str, Any]:
    """Build the committed aggregate envelope in its documented key order.

    Gate leaves are copied verbatim, corpus scope labels are reduced to
    basenames, and only aggregate counts/hashes survive: never query text,
    saved-run records, or absolute personal paths.
    """
    adequacy = corpus.get("adequacy") or {}
    if not isinstance(adequacy, Mapping):
        raise ValueError("corpus adequacy must be a mapping")
    labels = corpus.get("scope_labels") or []
    return {
        "version": 1,
        "decision": decision.decision,
        "rule": decision.to_dict(),
        "arms": dict(arms),
        "corpus": {
            "fingerprint": corpus.get("fingerprint"),
            "documents": corpus.get("documents"),
            "sampled": corpus.get("sampled"),
            "adequacy": {
                "adequate": bool(adequacy.get("adequate", False)),
                "sampled": adequacy.get("sampled"),
                "counts": dict(adequacy.get("counts") or {}),
            },
            "scope_labels": [Path(str(label)).name for label in labels],
        },
        "query_set_fingerprint": query_set_fingerprint,
        "gates": dict(gates),
        "replay": {
            "available": bool(replay_available),
            "note": (
                "Replay stability was reported by the comparison."
                if replay_available
                else _REPLAY_NOTE
            ),
        },
        "environment": dict(environment),
        "min_heldout_for_epsilon_win": decision.min_heldout_for_epsilon_win,
        "notes": list(notes),
    }


def write_artifact(path: Path, artifact: Mapping[str, Any]) -> Path:
    """Write the committed artifact atomically, sorted, with a trailing newline."""
    return write_json(path, artifact)


def assert_within_scratch(path: Path, scratch_root: Path) -> Path:
    """Resolve and refuse the root, the home directory, or any outside path.

    The scratch root is guarded, not only the target: with ``--scratch-root
    ~`` every run-owned candidate (``~/qwen3.db`` and its sidecars,
    ``~/saved-runs/qwen3.json``) is nested under the resolved home directory,
    so a target-only check would let cleanup delete unrelated user files
    (CR-01). Both sides are resolved first, so a symlink to the home
    directory is rejected the same way.
    """
    target = Path(path).resolve()
    root = Path(scratch_root).resolve()
    if root in {Path("/"), Path.home()}:
        raise ValueError(f"refusing to use {root} as a scratch root")
    if target in {Path("/"), Path.home()}:
        raise ValueError("refusing to operate on the filesystem root or home directory")
    if target != root and not target.is_relative_to(root):
        raise ValueError(f"refusing path outside the scratch root: {target}")
    return target


def cleanup_arms(scratch_root: Path, *, keep_arms: bool) -> list[str]:
    """Delete only the run's own DB files/sidecars and the baseline saved run."""
    if keep_arms:
        return []
    root = Path(scratch_root).resolve()
    candidates: list[Path] = []
    for name in SCRATCH_DB_NAMES:
        candidates.extend(
            [
                root / f"{name}.db",
                root / f"{name}.db-wal",
                root / f"{name}.db-shm",
                root / f"{name}.db.lock",
            ]
        )
    candidates.append(root / "saved-runs" / "qwen3.json")
    removed: list[str] = []
    for candidate in candidates:
        target = assert_within_scratch(candidate, root)
        if target.is_file():
            target.unlink()
            removed.append(target.name)
    return removed


def _complete_stage(
    state: dict[str, Any],
    state_path: Path,
    stage: str,
    detail: Any = None,
) -> None:
    """Mark one stage complete and persist the state immediately."""
    mark_stage(state, stage, detail)
    save_run_state(state_path, state)


def _drop_stages(state: dict[str, Any], state_path: Path, stages: Sequence[str]) -> bool:
    """Remove named completion markers; persist when anything changed."""
    recorded = state.get("stages")
    if not isinstance(recorded, dict):
        return False
    dropped = False
    for stage in stages:
        if recorded.pop(stage, None) is not None:
            dropped = True
    if dropped:
        save_run_state(state_path, state)
    return dropped


def _find_command(commands: Sequence[ArmCommand], stage: str) -> ArmCommand:
    """Return the one command for ``stage`` or fail loudly."""
    for command in commands:
        if command.stage == stage:
            return command
    raise RuntimeError(f"missing stage command: {stage}")


def _require_success(proc: subprocess.CompletedProcess[str], stage: str) -> None:
    """Raise a named error for a non-zero stage exit."""
    if proc.returncode != 0:
        raise RuntimeError(f"{stage} failed with exit {proc.returncode}: {proc.stderr[-4000:]}")


def _arm_cache_model_id(arm: ArmSpec) -> str:
    """The arm's cache bucket base; API bases are removed from every arm env."""
    return f"{arm.model_type}:{arm.model_name}"


def _collection_paths(db_path: Path) -> dict[str, str]:
    """Read ``name -> resolved path`` for the collections in one arm DB."""
    path = Path(db_path)
    if not path.is_file():
        return {}
    try:
        conn = _connect_read_only(path)
    except sqlite3.Error:
        return {}
    try:
        try:
            rows = conn.execute("SELECT name, path FROM collections").fetchall()
        except sqlite3.Error:
            return {}
    finally:
        conn.close()
    return {str(row[0]): str(row[1]) for row in rows}


def _command_collection_name(command: ArmCommand) -> str | None:
    """The ``--name`` value of a collection-add command, if present."""
    try:
        return command.argv[command.argv.index("--name") + 1]
    except (IndexError, ValueError):
        return None


def _command_collection_root(command: ArmCommand) -> str | None:
    """The resolved positional root of a collection-add command, if present."""
    try:
        return str(Path(command.argv[command.argv.index("add") + 1]).resolve())
    except (IndexError, ValueError):
        return None


def _collection_remove_command(command: ArmCommand, name: str) -> ArmCommand:
    """Derive ``collection remove <name> --yes`` from an add command."""
    base = command.argv[: command.argv.index("add")]
    return ArmCommand(
        stage=f"collection_remove_{name}",
        argv=[*base, "remove", name, "--yes"],
        env=command.env,
    )


def _run_index_commands(commands: Sequence[ArmCommand], db_path: Path) -> None:
    """Run collection-add/index-update commands idempotently on one arm DB.

    ``collection add`` fails when the name already exists, while the stage
    marker is written only after every command succeeds. A retry after a
    later command failed would otherwise fail forever on the first duplicate
    collection (WR-01). An existing run-owned collection with the same root is
    skipped; one pointing at a different root (a stale scope) is removed and
    re-added so the arm measures the requested corpus.
    """
    existing = _collection_paths(db_path)
    for command in commands:
        if command.stage.startswith("collection_add_"):
            name = _command_collection_name(command)
            root = _command_collection_root(command)
            if name is not None and name in existing:
                if root is not None and existing[name] == root:
                    continue
                removal = _collection_remove_command(command, name)
                proc = run_command(removal, timeout=STAGE_TIMEOUT_SECONDS)
                _require_success(proc, removal.stage)
        if command.stage.startswith("collection_add_") or command.stage == "index_update":
            proc = run_command(command, timeout=STAGE_TIMEOUT_SECONDS)
            _require_success(proc, command.stage)
            if command.stage.startswith("collection_add_"):
                name = _command_collection_name(command)
                root = _command_collection_root(command)
                if name is not None and root is not None:
                    existing[name] = root


def _cache_db_path() -> Path:
    """Resolve the shared embedding-cache DB before any arm env is chosen.

    This is a read-only settings lookup; it runs before ``build_arm_commands``
    so no ``get_settings()`` call happens after per-arm env values exist
    (research Pitfall 8).
    """
    from sif.config.settings import get_settings  # noqa: PLC0415

    return Path(get_settings().get_cache_dir()) / "embeddings_cache.db"


def _run_env_preflight(
    state: dict[str, Any],
    state_path: Path,
    scratch_root: Path,
) -> None:
    """Refuse a run without enough free disk before any index stage."""
    if stage_done(state, "env_preflight"):
        return
    assert_disk_headroom(scratch_root)
    free = shutil.disk_usage(scratch_root).free
    _complete_stage(state, state_path, "env_preflight", {"free_bytes": free})


def _run_index_stage(
    state: dict[str, Any],
    state_path: Path,
    commands: Sequence[ArmCommand],
    stage: str,
    db_path: Path,
) -> None:
    """Run collection-add and index-update commands, then mark the stage.

    The completion detail carries the corpus fingerprint so a later resume can
    tell whether the indexed content under the same roots has moved (WR-02).
    """
    if stage_done(state, stage):
        return
    _run_index_commands(commands, db_path)
    fingerprint, documents = _corpus_summary(db_path)
    _complete_stage(
        state,
        state_path,
        stage,
        {"corpus_fingerprint": fingerprint, "documents": documents},
    )


_DOWNSTREAM_AFTER_ARM_A_INDEX = (
    "arm_a_index",
    "adequacy",
    "arm_a_embed",
    "arm_a_probe",
    "arm_a_eval",
    "arm_b_index",
    "arm_b_identity",
    "arm_b_embed",
    "arm_b_probe",
    "arm_b_eval",
    "verdict",
    "artifact",
)


def _sync_arm_a_fingerprint(
    state: dict[str, Any],
    state_path: Path,
    commands: Sequence[ArmCommand],
    db_path: Path,
) -> None:
    """Refresh arm A on resume and invalidate the run when its content moved.

    ``index update`` is the cheap rescan; the corpus fingerprint persisted at
    arm-A index completion then decides whether the recorded stages still
    describe the corpus on disk (WR-02). A content change under the same
    roots invalidates the arm-A index marker and every downstream stage, so
    the run re-indexes and re-measures instead of reusing the old indexes.
    """
    if not stage_done(state, "arm_a_index"):
        return
    _run_index_commands(commands, db_path)
    recorded = state["stages"]["arm_a_index"].get("detail")
    detail = recorded if isinstance(recorded, Mapping) else {}
    fingerprint, documents = _corpus_summary(db_path)
    if detail.get("corpus_fingerprint") == fingerprint and detail.get("documents") == documents:
        return
    state.pop("adequacy", None)
    _drop_stages(state, state_path, _DOWNSTREAM_AFTER_ARM_A_INDEX)
    save_run_state(state_path, state)


def _run_adequacy_stage(
    state: dict[str, Any],
    state_path: Path,
    db_path: Path,
) -> dict[str, Any]:
    """Run the EN+ZH preflight; only an adequate verdict marks it complete."""
    if stage_done(state, "adequacy"):
        return dict(state.get("adequacy") or {})
    result = preflight_adequacy(db_path)
    state["adequacy"] = result
    if result.get("adequate"):
        mark_stage(
            state,
            "adequacy",
            {"sampled": result.get("sampled"), "counts": result.get("counts")},
        )
    save_run_state(state_path, state)
    return result


def _run_embed_stage(
    state: dict[str, Any],
    state_path: Path,
    commands: Sequence[ArmCommand],
    arm: ArmSpec,
    stage: str,
    cache_db_path: Path,
) -> dict[str, Any]:
    """Run one arm's full re-embed and record wall time and cache deltas."""
    if stage_done(state, stage):
        return dict(state["stages"][stage].get("detail") or {})
    command = _find_command(commands, "index_embed")
    cache_model_id = _arm_cache_model_id(arm)
    cache_before = _cache_rows(cache_db_path, cache_model_id)
    started = time.monotonic()
    proc = run_command(command, timeout=STAGE_TIMEOUT_SECONDS)
    elapsed = time.monotonic() - started
    _require_success(proc, command.stage)
    costs = collect_arm_costs(
        arm.db_path,
        cache_db_path,
        elapsed,
        cache_model_id=cache_model_id,
        cache_rows_before=cache_before,
    )
    _complete_stage(state, state_path, stage, costs)
    return costs


def _run_probe_stage(
    state: dict[str, Any],
    state_path: Path,
    arm: ArmSpec,
    stage: str,
) -> dict[str, Any]:
    """Load the arm model in its own subprocess and gate its identity."""
    if stage_done(state, stage):
        return dict(state["stages"][stage].get("detail") or {})
    command = ArmCommand(
        stage=f"probe_{arm.name}",
        argv=probe_arm_command(sys.executable, arm),
        env=build_arm_env(os.environ, arm),
    )
    proc = run_command(command, timeout=PROBE_TIMEOUT_SECONDS)
    payload = parse_json_stdout(proc, stage)
    require_probe_ok(payload, arm)
    _complete_stage(state, state_path, stage, payload)
    return payload


def _run_eval_stage(
    state: dict[str, Any],
    state_path: Path,
    commands: Sequence[ArmCommand],
    stage: str,
    saved_run_path: Path,
    comparison_path: Path | None = None,
) -> dict[str, Any]:
    """Run one eval, copy its auto-saved run, and keep any comparison JSON."""
    if stage_done(state, stage):
        return dict(state["stages"][stage].get("detail") or {})
    command = _find_command(commands, "eval")
    proc = run_command(command, timeout=STAGE_TIMEOUT_SECONDS)
    payload = parse_json_stdout(proc, stage)
    run_path = payload.get("run_path")
    if not run_path:
        raise RuntimeError(f"{stage} did not report a saved run path")
    saved_run_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(str(run_path)), saved_run_path)
    detail: dict[str, Any] = {"run_path": str(saved_run_path)}
    if comparison_path is not None:
        comparison = payload.get("comparison")
        if not isinstance(comparison, Mapping):
            raise RuntimeError(f"{stage} payload has no comparison object")
        write_json(comparison_path, comparison)
        detail["comparison_path"] = str(comparison_path)
    _complete_stage(state, state_path, stage, detail)
    return detail


def _corpus_summary(db_path: Path) -> tuple[str, int]:
    """Return the arm DB's corpus fingerprint and document count."""
    from sif.search.personal_bench import (  # noqa: PLC0415
        corpus_fingerprint,
        load_document_metadata,
    )

    conn = _connect_read_only(db_path)
    try:
        metadata = load_document_metadata(conn, None)
    finally:
        conn.close()
    return corpus_fingerprint(metadata), len(metadata)


def _run_arm_b_index_stage(
    state: dict[str, Any],
    state_path: Path,
    commands: Sequence[ArmCommand],
    qwen3_db: Path,
    harrier_db: Path,
) -> None:
    """Build arm B, then refuse a corpus drift between the two arms."""
    if stage_done(state, "arm_b_index"):
        return
    _run_index_commands(commands, harrier_db)
    qwen3_fingerprint, qwen3_documents = _corpus_summary(qwen3_db)
    harrier_fingerprint, harrier_documents = _corpus_summary(harrier_db)
    if (qwen3_fingerprint, qwen3_documents) != (harrier_fingerprint, harrier_documents):
        raise RuntimeError(
            "corpus fingerprint mismatch between arms: "
            f"qwen3 {qwen3_fingerprint}/{qwen3_documents}, "
            f"harrier {harrier_fingerprint}/{harrier_documents}"
        )
    _complete_stage(
        state,
        state_path,
        "arm_b_index",
        {"corpus_fingerprint": qwen3_fingerprint, "documents": qwen3_documents},
    )


def _run_pair_identity_stage(
    state: dict[str, Any],
    state_path: Path,
    qwen3: ArmSpec,
    harrier: ArmSpec,
) -> None:
    """Read both stored identities and run the pairwise swap gate."""
    if stage_done(state, "arm_b_identity"):
        return
    stored_qwen3 = _read_stored_identity(qwen3.db_path)
    stored_harrier = _read_stored_identity(harrier.db_path)
    if stored_qwen3 is None or stored_harrier is None:
        raise IdentityGateError("pair", ["a stored identity is missing before the pair check"])
    verify_arm_identity(stored_qwen3, qwen3)
    verify_arm_identity(stored_harrier, harrier)
    verify_arm_pair(stored_qwen3, stored_harrier)
    _complete_stage(
        state,
        state_path,
        "arm_b_identity",
        {
            "qwen3": stored_qwen3.display_fingerprint(),
            "harrier": stored_harrier.display_fingerprint(),
        },
    )


def _gates_from_comparison(comparison: Mapping[str, Any]) -> dict[str, Any]:
    """Copy the documented gate leaves verbatim from the comparison payload.

    ``ComparisonReport.to_dict`` names the overall gate ``gate`` (with the
    ``warrants_default_change`` flag folded in); the artifact envelope's
    documented leaf name is ``overall``.
    """
    overall = comparison.get("overall")
    if overall is None:
        overall = comparison.get("gate", {})
    return {
        "overall": overall,
        "splits": comparison["splits"],
        "language_splits": comparison.get("language_splits", {}),
        "legs": comparison["legs"],
        "leg_splits": comparison["leg_splits"],
        "leg_language_splits": comparison.get("leg_language_splits", {}),
        "groups": comparison["groups"],
        "suppressed": comparison["suppressed"],
        "top_k": comparison["top_k"],
    }


def _build_insufficient_artifact(
    adequacy: Mapping[str, Any],
    corpus_roots: Sequence[Path],
    db_path: Path,
) -> dict[str, Any]:
    """Build the recorded no-verdict artifact; no comparison ever ran."""
    from sif.search.embedder_verdict import decide_from_gates  # noqa: PLC0415

    fingerprint, documents = _corpus_summary(db_path)
    decision = decide_from_gates(None, {}, required_languages=REQUIRED_LANGUAGES)
    return build_artifact(
        decision=decision,
        arms={},
        corpus={
            "fingerprint": fingerprint,
            "documents": documents,
            "sampled": adequacy.get("sampled"),
            "adequacy": adequacy,
            "scope_labels": [Path(root).name for root in corpus_roots],
        },
        query_set_fingerprint=None,
        gates={},
        environment=collect_environment(),
        replay_available=False,
        notes=[
            "EN+ZH held-out adequacy is insufficient; no comparison ran and "
            "Qwen3 remains the default."
        ],
    )


def _recorded_artifact_if_current(
    state: Mapping[str, Any],
    corpus_payload: Mapping[str, Any],
    qwen3_saved_run: Path,
    harrier_saved_run: Path,
) -> dict[str, Any] | None:
    """Return the recorded artifact only when every input fingerprint agrees.

    The insufficient-evidence path never marks the artifact complete, and an
    older marker is trusted only while its stored query-set and corpus
    fingerprints still match this run's inputs (CR-02). Otherwise the caller
    drops the stale markers and recomputes.
    """
    if not stage_done(state, "artifact") or not Path(ARTIFACT_PATH).is_file():
        return None
    recorded = state.get("stages")
    entry = recorded.get("artifact") if isinstance(recorded, Mapping) else None
    detail = entry.get("detail") if isinstance(entry, Mapping) else None
    if not isinstance(detail, Mapping):
        return None
    stored_query = detail.get("query_set_fingerprint")
    stored_corpus = detail.get("corpus_fingerprint")
    if not isinstance(stored_query, str) or not isinstance(stored_corpus, str):
        return None
    if stored_corpus != corpus_payload.get("fingerprint"):
        return None
    try:
        payload = json.loads(Path(ARTIFACT_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, Mapping):
        return None
    artifact_corpus = payload.get("corpus")
    if not isinstance(artifact_corpus, Mapping):
        return None
    if artifact_corpus.get("fingerprint") != stored_corpus:
        return None
    if payload.get("query_set_fingerprint") != stored_query:
        return None
    current_query = _pair_query_set_fingerprint(qwen3_saved_run, harrier_saved_run)
    if current_query is not None and current_query != stored_query:
        return None
    return dict(payload)


def _run_verdict_stage(
    state: dict[str, Any],
    state_path: Path,
    *,
    comparison_path: Path,
    qwen3_saved_run: Path,
    harrier_saved_run: Path,
    arms_payload: Mapping[str, Any],
    corpus_payload: Mapping[str, Any],
    device: str,
) -> dict[str, Any]:
    """Compute the pure two-sided verdict and write the aggregate artifact."""
    recorded = _recorded_artifact_if_current(
        state, corpus_payload, qwen3_saved_run, harrier_saved_run
    )
    if recorded is not None:
        return recorded
    if stage_done(state, "artifact"):
        # A marker whose inputs no longer agree is stale; never let it shadow
        # the recomputation below (CR-02).
        _drop_stages(state, state_path, ("verdict", "artifact"))
    from sif.search.embedder_verdict import decide_from_payload  # noqa: PLC0415

    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    if not isinstance(comparison, Mapping):
        raise RuntimeError("comparison payload is not a JSON object")
    fingerprint_a = _pair_query_set_fingerprint(qwen3_saved_run, harrier_saved_run)
    if fingerprint_a is None:
        raise RuntimeError("saved runs are missing; cannot compute the verdict")
    decision = decide_from_payload(comparison, required_languages=REQUIRED_LANGUAGES)
    replay = comparison.get("replay")
    replay_available = bool(replay.get("available")) if isinstance(replay, Mapping) else False
    artifact = build_artifact(
        decision=decision,
        arms=arms_payload,
        corpus=corpus_payload,
        query_set_fingerprint=fingerprint_a,
        gates=_gates_from_comparison(comparison),
        environment=collect_environment(device=device),
        replay_available=replay_available,
        notes=[
            "Two isolated file-backed arms; no vectors are shared.",
            "The strict 1/N noise floor admits a 0.01 win only above "
            f"N={MIN_HELDOUT_FOR_EPSILON_WIN} held-out queries.",
        ],
    )
    write_artifact(ARTIFACT_PATH, artifact)
    _complete_stage(
        state,
        state_path,
        "verdict",
        {"decision": decision.decision, "query_set_fingerprint": fingerprint_a},
    )
    _complete_stage(
        state,
        state_path,
        "artifact",
        {
            "path": str(ARTIFACT_PATH),
            "decision": decision.decision,
            "query_set_fingerprint": fingerprint_a,
            "corpus_fingerprint": corpus_payload.get("fingerprint"),
        },
    )
    return artifact


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


def run_stage_machine(
    arms: Mapping[str, ArmSpec],
    corpus_roots: Sequence[Path],
    scratch_root: Path,
    *,
    corpus_label: str,
    keep_arms: bool,
    output_json: bool,
    preflight_only: bool = False,
) -> int:
    """Run (or resume) the scope-keyed two-arm stage machine."""
    # The guard runs before any mkdir/write/delete: a home-directory or
    # filesystem-root scratch root must be refused (CR-01).
    scratch_root = assert_within_scratch(scratch_root, scratch_root)
    scratch_root.mkdir(parents=True, exist_ok=True)
    saved_runs = scratch_root / "saved-runs"
    saved_runs.mkdir(parents=True, exist_ok=True)
    qwen3 = arms["qwen3"]
    harrier = arms["harrier"]
    scope = scope_state(corpus_roots, scratch_root, corpus_label)
    state_path = scratch_root / "run-state.json"
    current_key = scope_key(scope)
    previous_key = _previous_scope_key(state_path)
    state = load_run_state(state_path, scope_key=current_key, scope=scope)
    if previous_key is not None and previous_key != current_key:
        # A changed --corpus set gets a fresh scope key, but the old arm DBs
        # still hold collections pointing at the old roots; clear every
        # run-owned file before indexing (WR-01).
        cleanup_arms(scratch_root, keep_arms=False)
    # Resolve the shared cache before any per-arm env is chosen (Pitfall 8).
    cache_db_path = _cache_db_path()
    commands_a = build_arm_commands(sys.executable, qwen3, corpus_roots)
    qwen3_saved_run = saved_runs / "qwen3.json"
    commands_b = build_arm_commands(
        sys.executable,
        harrier,
        corpus_roots,
        saved_run_path=qwen3_saved_run,
    )
    _run_env_preflight(state, state_path, scratch_root)
    _sync_arm_a_fingerprint(state, state_path, commands_a, qwen3.db_path)
    _run_index_stage(state, state_path, commands_a, "arm_a_index", qwen3.db_path)
    adequacy = _run_adequacy_stage(state, state_path, qwen3.db_path)
    if preflight_only:
        print(json.dumps(adequacy, indent=2, sort_keys=True))
        return 0 if adequacy.get("adequate") else 3
    if not adequacy.get("adequate"):
        artifact = _build_insufficient_artifact(adequacy, corpus_roots, qwen3.db_path)
        write_artifact(ARTIFACT_PATH, artifact)
        # Deliberately no verdict/artifact marker: an inadequate preflight is
        # recorded in ``state["adequacy"]`` but never marked complete, so a
        # resumed full run re-checks adequacy and recomputes instead of
        # returning this artifact (CR-02).
        if output_json:
            print(json.dumps(artifact, indent=2, sort_keys=True))
        else:
            print(f"SHORT {artifact['decision']} artifact={ARTIFACT_PATH}")
        return 3
    costs_a = _run_embed_stage(
        state, state_path, commands_a, qwen3, "arm_a_embed", cache_db_path
    )
    probe_a = _run_probe_stage(state, state_path, qwen3, "arm_a_probe")
    _run_eval_stage(state, state_path, commands_a, "arm_a_eval", qwen3_saved_run)
    _run_arm_b_index_stage(state, state_path, commands_b, qwen3.db_path, harrier.db_path)
    costs_b = _run_embed_stage(
        state, state_path, commands_b, harrier, "arm_b_embed", cache_db_path
    )
    probe_b = _run_probe_stage(state, state_path, harrier, "arm_b_probe")
    _run_pair_identity_stage(state, state_path, qwen3, harrier)
    comparison_path = saved_runs / "harrier-comparison.json"
    _run_eval_stage(
        state,
        state_path,
        commands_b,
        "arm_b_eval",
        saved_runs / "harrier.json",
        comparison_path,
    )
    fingerprint, documents = _corpus_summary(qwen3.db_path)
    artifact = _run_verdict_stage(
        state,
        state_path,
        comparison_path=comparison_path,
        qwen3_saved_run=qwen3_saved_run,
        harrier_saved_run=saved_runs / "harrier.json",
        arms_payload={
            "qwen3": {"identity": probe_a.get("identity", {}), "costs": costs_a},
            "harrier": {"identity": probe_b.get("identity", {}), "costs": costs_b},
        },
        corpus_payload={
            "fingerprint": fingerprint,
            "documents": documents,
            "sampled": adequacy.get("sampled"),
            "adequacy": adequacy,
            "scope_labels": [Path(root).name for root in corpus_roots],
        },
        device=str(probe_b.get("device", "unknown")),
    )
    if not keep_arms:
        cleanup_arms(scratch_root, keep_arms=False)
    if output_json:
        print(json.dumps(artifact, indent=2, sort_keys=True))
    else:
        print(f"PASS decision={artifact['decision']} artifact={ARTIFACT_PATH}")
    return 0


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
        if args.arm is None:
            _emit_err("REFUSED: --probe requires --arm")
            return 2
        return _run_probe(args.arm, Path(args.scratch_root))
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
    try:
        return run_stage_machine(
            arms,
            corpus_roots,
            Path(args.scratch_root),
            corpus_label=args.corpus_label,
            keep_arms=args.keep_arms,
            output_json=args.json,
            preflight_only=args.preflight_only,
        )
    except IdentityGateError as exc:
        _emit_err(f"FAIL {exc}")
        return 1
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
        _emit_err(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
