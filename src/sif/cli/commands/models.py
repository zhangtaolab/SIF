"""Model management commands: download and inspect embedder-family models.

``sif models pull`` resolves a registry name (``embedding``, ``reranker``,
``query_expansion``) or a ModelScope ``owner/name`` id to the canonical,
manifest-verified cache. ``sif models status`` reports what is configured,
cached, and persisted without importing a backend or downloading anything;
non-TTY output is plain ``section.key: value`` lines so pipes stay clean.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import click
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from sif.config.settings import Settings, get_settings
from sif.embedding.identity import (
    EmbedderIdentity,
    build_settings_identity,
    read_identity,
    schema_embedding_dim,
)
from sif.embedding.prompts import resolve_prompt_scheme
from sif.models.download import DEFAULT_MODELS, ModelDownloader, inspect_cache
from sif.utils.logging import is_quiet


console = Console()

_SECTION_ORDER = ("settings", "cache", "backend", "vector_backend", "identity")

# model_type -> (importable module, distribution name used for the version).
_BACKEND_MODULES: dict[str, tuple[str, str]] = {
    "sentence_transformers": ("sentence_transformers", "sentence-transformers"),
    "modelscope": ("modelscope", "modelscope"),
    "gguf": ("llama_cpp", "llama-cpp-python"),
    "openai": ("openai", "openai"),
}
_VECTOR_BACKEND = ("sqlite_vec", "sqlite_vec", "sqlite-vec")

_ACCEPTED_TARGETS = "one of embedding, reranker, query_expansion, or a ModelScope id 'owner/name'"
_REGISTRY_TARGETS = frozenset({"embedding", "reranker", "query_expansion"})
_MODEL_ID_PARTS = 2


@click.group("models")
def models_group() -> None:
    """Download and inspect embedding, reranker, and query-expansion models."""


def resolve_model_target(name: str | None) -> str:
    """Resolve a pull target to its ModelScope ``owner/name`` model id.

    ``None`` and ``embedding`` mean the configured embedder, ``reranker`` the
    configured reranker, and ``query_expansion`` the registry entry. A value
    with exactly one slash is taken as an explicit ModelScope id.
    """
    settings = get_settings()
    if name is None or name == "embedding":
        return settings.model_name
    if name == "reranker":
        return settings.reranker_model_name
    if name == "query_expansion":
        return DEFAULT_MODELS["query_expansion"]["model_id"]
    parts = name.split("/")
    if len(parts) == _MODEL_ID_PARTS and all(parts):
        return name
    raise click.ClickException(f"Unknown model target {name!r}; expected {_ACCEPTED_TARGETS}")


def download_model(model_id: str, *, force: bool, cache_dir: str | None) -> Path:
    """Download one model id through the manifest-verified canonical cache.

    Backend and filesystem failures are converted to ``ClickException`` so a
    missing ``modelscope`` or an unwritable cache never surfaces a traceback.
    """
    try:
        downloader = ModelDownloader(cache_dir=cache_dir)
        return downloader.download(model_id, force=force)
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


def download_model_target(name: str | None, *, force: bool, cache_dir: str | None) -> Path:
    """Resolve ``name`` and download it, returning the verified model directory."""
    return download_model(resolve_model_target(name), force=force, cache_dir=cache_dir)


def _stdout_is_tty() -> bool:
    """Whether stdout is an interactive terminal (test seam)."""
    return sys.stdout.isatty()


@models_group.command("pull")
@click.argument("name", required=False)
@click.option("--force", is_flag=True, help="Re-download even when the cached copy verifies")
@click.option(
    "--cache-dir",
    type=click.Path(),
    help="Cache root (defaults to the SIF cache directory)",
)
def models_pull_cmd(name: str | None, force: bool, cache_dir: str | None) -> None:
    """Download the configured or named model through the verified cache."""
    model_id = resolve_model_target(name)
    path = download_model(model_id, force=force, cache_dir=cache_dir)
    if _stdout_is_tty() and not is_quiet():
        console.print(f"[dim]Model ready: {model_id}[/dim]")
    click.echo(f"{model_id}: {path}")


def _probe_module(name: str, module: str, distribution: str) -> dict[str, object]:
    """Report module availability and version without importing it."""
    try:
        available = importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        available = False
    version: str | None = None
    if available:
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            version = None
    return {"name": name, "available": available, "version": version}


def _backend_section(model_type: str) -> dict[str, object]:
    """Probe the configured embedding backend by module name only."""
    module, distribution = _BACKEND_MODULES.get(model_type, (model_type, model_type))
    return _probe_module(model_type, module, distribution)


def _index_path(ctx: click.Context) -> Path:
    """Return the index path from the Click context, without creating it."""
    index_path = (ctx.obj or {}).get("index_path")
    if index_path is not None:
        return Path(index_path)
    try:
        return get_settings().get_db_path()
    except ValidationError as e:
        raise click.ClickException(str(e)) from e


def _empty_identity_section(current: EmbedderIdentity) -> dict[str, object]:
    """Payload for a status that cannot read a stored identity."""
    return {
        "status": "no-index",
        "source": None,
        "stored_model_name": None,
        "stored_cache_model_id": None,
        "stored_dimension": None,
        "stored_fingerprint": None,
        "schema_dimension": None,
        "current_cache_model_id": current.cache_model_id,
        "current_fingerprint": current.display_fingerprint(),
    }


def _read_identity_fields(index_path: Path) -> tuple[EmbedderIdentity | None, int | None]:
    """Read the persisted identity and schema width from a read-only connection."""
    with closing(sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)) as conn:
        return read_identity(conn), schema_embedding_dim(conn)


def _identity_section(
    settings: Settings,
    index_path: Path,
    current: EmbedderIdentity,
) -> dict[str, object]:
    """Compare the persisted identity against the configured one (D-08).

    The stored ``source`` and display fingerprints are reported as display
    fields; the status is decided by the stored dimension/schema width and
    the stored ``cache_model_id``. A missing index, a missing row, or an
    unreadable database degrades to a value — never an exception.
    """
    payload = _empty_identity_section(current)
    if not index_path.exists():
        return payload

    payload["status"] = "no-identity"
    try:
        stored, schema_dimension = _read_identity_fields(index_path)
    except (sqlite3.Error, OSError, ValueError):
        return payload

    payload["schema_dimension"] = schema_dimension
    if stored is None:
        return payload

    payload.update(
        source=stored.source,
        stored_model_name=stored.model_name,
        stored_cache_model_id=stored.cache_model_id,
        stored_dimension=stored.dimension,
        stored_fingerprint=stored.display_fingerprint(),
    )
    if stored.dimension != settings.embedding_dim or (
        schema_dimension is not None and schema_dimension != settings.embedding_dim
    ):
        payload["status"] = "dimension-mismatch"
    elif stored.cache_model_id != current.cache_model_id:
        payload["status"] = "mismatch"
    else:
        payload["status"] = "match"
    return payload


def _render_plain(payload: dict[str, dict[str, object]]) -> None:
    """Emit fixed-order ``section.key: value`` lines for pipes."""
    for section in _SECTION_ORDER:
        for key, value in payload[section].items():
            click.echo(f"{section}.{key}: {'' if value is None else value}")


def _render_table(payload: dict[str, dict[str, object]]) -> None:
    """Render one Rich table row per section/key on a TTY."""
    table = Table(title="Model Status")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    for section in _SECTION_ORDER:
        for key, value in payload[section].items():
            table.add_row(f"{section}.{key}", "" if value is None else str(value))
    console.print(table)


@models_group.command("status")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def models_status_cmd(ctx: click.Context, output_json: bool) -> None:
    """Show configured, cached, and persisted model identity."""
    settings = get_settings()
    scheme = resolve_prompt_scheme(
        settings.model_name,
        settings.model_type,
        settings.query_prompt_name,
        settings.document_prompt_name,
    )
    current = build_settings_identity(settings, scheme)
    model_cache_dir = settings.get_cache_dir() / "models"
    cache = inspect_cache(settings.model_name, model_cache_dir)
    vector_name, vector_module, vector_distribution = _VECTOR_BACKEND

    payload: dict[str, dict[str, object]] = {
        "settings": {
            "model_name": settings.model_name,
            "model_type": settings.model_type,
            "api_base": settings.api_base,
            "dimension": settings.embedding_dim,
            "cache_dir": str(model_cache_dir),
        },
        "cache": {
            "path": cache["path"],
            "state": cache["state"],
            "revision": cache["revision"],
        },
        "backend": _backend_section(settings.model_type),
        "vector_backend": _probe_module(
            vector_name,
            vector_module,
            vector_distribution,
        ),
        "identity": _identity_section(settings, _index_path(ctx), current),
    }

    if output_json:
        click.echo(json.dumps(payload, indent=2, sort_keys=True))
        return
    if _stdout_is_tty() and not is_quiet():
        _render_table(payload)
        return
    _render_plain(payload)
