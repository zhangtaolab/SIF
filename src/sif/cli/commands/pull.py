"""Model download command."""

from __future__ import annotations

from pathlib import Path
from urllib import request

import click
from rich.console import Console


try:
    from huggingface_hub import hf_hub_download
except ImportError:  # pragma: no cover
    hf_hub_download = None  # type: ignore[misc,assignment]

try:
    from modelscope import snapshot_download
except ImportError:  # pragma: no cover
    snapshot_download = None  # type: ignore[misc,assignment]

console = Console()

_MIN_SPEC_PARTS = 3


def _download_from_url(model_spec: str, target_cache: Path) -> Path:
    local_name = Path(model_spec).name
    if not local_name:
        raise click.ClickException("Could not determine filename from URL")
    downloaded = target_cache / local_name
    console.print(f"[dim]Downloading from URL: {model_spec}[/dim]")
    try:
        request.urlretrieve(model_spec, downloaded)
    except Exception as e:
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
                f"HuggingFace failed: {hf_err}. ModelScope not installed."
            ) from hf_err
        except Exception as ms_err:
            raise click.ClickException(f"Download failed: HF={hf_err}, MS={ms_err}") from ms_err


@click.command("pull")
@click.argument("model_spec")
@click.option(
    "--cache-dir",
    type=click.Path(),
    help="Custom cache directory",
)
@click.pass_context
def pull_cmd(
    _ctx: click.Context,
    model_spec: str,
    cache_dir: str | None,
) -> None:
    """Download a GGUF model file."""
    target_cache = (
        Path(cache_dir).expanduser().resolve() if cache_dir else Path.home() / ".sif" / "models"
    )
    target_cache.mkdir(parents=True, exist_ok=True)

    downloaded = _download_model(model_spec, target_cache)

    if not downloaded.exists() or downloaded.stat().st_size == 0:
        raise click.ClickException("Downloaded file is missing or empty.")

    console.print(f"[green]Downloaded to {downloaded}[/green]")
