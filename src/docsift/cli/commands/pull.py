"""Model download command."""

from __future__ import annotations

from pathlib import Path
from urllib import request

import click
from rich.console import Console

console = Console()


@click.command("pull")
@click.argument("model_spec")
@click.option(
    "--cache-dir",
    type=click.Path(),
    help="Custom cache directory",
)
@click.pass_context
def pull_cmd(
    ctx: click.Context,
    model_spec: str,
    cache_dir: str | None,
) -> None:
    """Download a GGUF model file."""
    target_cache = (
        Path(cache_dir).expanduser().resolve()
        if cache_dir
        else Path.home() / ".docsift" / "models"
    )
    target_cache.mkdir(parents=True, exist_ok=True)

    # Direct URL fallback
    if model_spec.startswith(("http://", "https://")):
        local_name = Path(model_spec).name
        if not local_name:
            raise click.ClickException("Could not determine filename from URL")
        downloaded = target_cache / local_name
        console.print(f"[dim]Downloading from URL: {model_spec}[/dim]")
        try:
            request.urlretrieve(model_spec, downloaded)
        except Exception as e:
            raise click.ClickException(f"Download failed: {e}")
    else:
        parts = model_spec.split("/")
        if len(parts) < 3:
            raise click.ClickException(
                "Model spec must be owner/repo/filename.gguf or a direct URL"
            )
        repo_id = "/".join(parts[:-1])
        filename = parts[-1]

        try:
            from huggingface_hub import hf_hub_download

            console.print(f"[dim]Downloading from HuggingFace: {repo_id}/{filename}[/dim]")
            path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                cache_dir=str(target_cache),
                local_files_only=False,
            )
            downloaded = Path(path)
        except Exception as hf_err:
            console.print(f"[yellow]HuggingFace failed: {hf_err}[/yellow]")
            try:
                from modelscope import snapshot_download

                console.print(f"[dim]Trying ModelScope fallback...[/dim]")
                model_path = snapshot_download(repo_id, cache_dir=str(target_cache))
                downloaded = Path(model_path) / filename
            except ImportError:
                raise click.ClickException(
                    f"HuggingFace failed: {hf_err}. ModelScope not installed."
                )
            except Exception as ms_err:
                raise click.ClickException(
                    f"Download failed: HF={hf_err}, MS={ms_err}"
                )

    if not downloaded.exists() or downloaded.stat().st_size == 0:
        raise click.ClickException("Downloaded file is missing or empty.")

    console.print(f"[green]Downloaded to {downloaded}[/green]")
