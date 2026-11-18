"""Deprecated ``sif pull`` alias.

The public surface is ``sif models pull``. This hidden command keeps working for
one release: registry names and ModelScope ``owner/name`` ids delegate to the
shared models handler, while the legacy GGUF/URL spec path is retained with a
bounded timeout and a non-empty check. The deprecation notice and every legacy
progress line go to stderr so stdout carries only the plain result line.
"""

from __future__ import annotations

from pathlib import Path
from urllib import request

import click
from rich.console import Console

from sif.cli.commands.models import download_model, resolve_model_target


try:
    from huggingface_hub import hf_hub_download
except ImportError:  # pragma: no cover
    hf_hub_download = None  # type: ignore[misc,assignment]

try:
    from modelscope import snapshot_download
except ImportError:  # pragma: no cover
    snapshot_download = None  # type: ignore[misc,assignment]

console = Console(stderr=True)

_MIN_SPEC_PARTS = 3
_MODEL_ID_PARTS = 2
_REGISTRY_NAMES = frozenset({"embedding", "reranker", "query_expansion"})
_URL_TIMEOUT_SECONDS = 60
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024
_DEPRECATION_NOTICE = "'sif pull' is deprecated and will be removed; use 'sif models pull'."


def _download_from_url(model_spec: str, target_cache: Path) -> Path:
    """Stream a direct URL to ``target_cache`` with a bounded timeout."""
    local_name = Path(model_spec).name
    if not local_name:
        raise click.ClickException("Could not determine filename from URL")
    downloaded = target_cache / local_name
    console.print(f"[dim]Downloading from URL: {model_spec}[/dim]")
    try:
        with (
            request.urlopen(model_spec, timeout=_URL_TIMEOUT_SECONDS) as response,
            open(downloaded, "wb") as handle,
        ):
            for chunk in iter(lambda: response.read(_DOWNLOAD_CHUNK_SIZE), b""):
                handle.write(chunk)
    except Exception as e:
        downloaded.unlink(missing_ok=True)
        raise click.ClickException(f"Download failed: {e}") from e
    return downloaded


def _download_from_hf(repo_id: str, filename: str, target_cache: Path) -> Path:
    if hf_hub_download is None:
        raise ImportError("huggingface_hub not installed")

    console.print(f"[dim]Downloading from HuggingFace: {repo_id}/{filename}[/dim]")
    path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        cache_dir=str(target_cache),
        local_files_only=False,
    )
    return Path(path)


def _download_from_modelscope(repo_id: str, filename: str, target_cache: Path) -> Path:
    if snapshot_download is None:
        raise ImportError("modelscope not installed")

    console.print("[dim]Trying ModelScope fallback...[/dim]")
    model_path = snapshot_download(repo_id, cache_dir=str(target_cache))
    return Path(model_path) / filename


def _download_model(model_spec: str, target_cache: Path) -> Path:
    if model_spec.startswith(("http://", "https://")):
        return _download_from_url(model_spec, target_cache)

    parts = model_spec.split("/")
    if len(parts) < _MIN_SPEC_PARTS:
        raise click.ClickException("Model spec must be owner/repo/filename.gguf or a direct URL")
    repo_id = "/".join(parts[:-1])
    filename = parts[-1]

    try:
        return _download_from_hf(repo_id, filename, target_cache)
    except Exception as hf_err:
        console.print(f"[yellow]HuggingFace failed: {hf_err}[/yellow]")
        try:
            return _download_from_modelscope(repo_id, filename, target_cache)
        except ImportError:
            raise click.ClickException(
                f"HuggingFace failed: {hf_err}. ModelScope not installed.",
            ) from hf_err
        except Exception as ms_err:
            raise click.ClickException(f"Download failed: HF={hf_err}, MS={ms_err}") from ms_err


def _delegates_to_models(model_spec: str) -> bool:
    """Whether the spec is a registry name or a ModelScope ``owner/name`` id."""
    if model_spec in _REGISTRY_NAMES:
        return True
    parts = model_spec.split("/")
    return len(parts) == _MODEL_ID_PARTS and all(parts)


def _legacy_cache_dir(cache_dir: str | None) -> Path:
    """Return the legacy GGUF cache root (unchanged for one release)."""
    target_cache = (
        Path(cache_dir).expanduser().resolve() if cache_dir else Path.home() / ".sif" / "models"
    )
    target_cache.mkdir(parents=True, exist_ok=True)
    return target_cache


@click.command("pull", hidden=True)
@click.argument("model_spec")
@click.option(
    "--cache-dir",
    type=click.Path(),
    help="Custom cache directory",
)
def pull_cmd(model_spec: str, cache_dir: str | None) -> None:
    """Download a model (deprecated: use 'sif models pull')."""
    console.print(_DEPRECATION_NOTICE)

    if _delegates_to_models(model_spec):
        model_id = resolve_model_target(model_spec)
        path = download_model(model_id, force=False, cache_dir=cache_dir)
        click.echo(f"{model_id}: {path}")
        return

    if model_spec.startswith(("http://", "https://")) or (
        len(model_spec.split("/")) >= _MIN_SPEC_PARTS
    ):
        downloaded = _download_model(model_spec, _legacy_cache_dir(cache_dir))
        if not downloaded.exists() or downloaded.stat().st_size == 0:
            raise click.ClickException("Downloaded file is missing or empty.")
        click.echo(f"{model_spec}: {downloaded}")
        return

    raise click.ClickException(
        "Model spec must be owner/repo/filename.gguf or a direct URL, "
        "a registry name (embedding, reranker, query_expansion), or a ModelScope id owner/name",
    )
