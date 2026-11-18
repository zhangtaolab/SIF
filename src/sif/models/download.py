"""Model download from ModelScope with a manifest-verified canonical cache.

The cache layout is ``<cache root>/<owner>/<name>`` where the cache root defaults
to ``Settings.get_cache_dir() / "models"``. A cache hit requires ``.sif-model.json``
with a matching size and SHA-256 for every listed file; a non-empty directory
without a valid manifest is never accepted. Downloads land in a sibling temporary
directory, are verified there, and replace the target only after the manifest is
written, so a failed download leaves the previous cache untouched.

ModelScope accepts branch/tag revisions only for the models SIF ships, so the
recorded ``master`` revision is the requested name, not an immutable commit pin.
The manifest supplies local-content determinism; ``revision_resolved`` records
what the ModelScope ``.mv`` marker reported when present.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import types
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from sif.utils.logging import get_logger, is_quiet, suppress_output


logger = get_logger(__name__)

MANIFEST_NAME = ".sif-model.json"
MANIFEST_VERSION = 1
MODELSCOPE_INSTALL_HINT = (
    "modelscope is required to download models; "
    "install the embed extra: uv tool install 'docsif[embed]'"
)
WEIGHT_SUFFIXES = frozenset({".safetensors", ".bin", ".gguf", ".pt"})
_MANIFEST_TEMP_SUFFIX = ".tmp"
_MODEL_ID_PARTS = 2

_DEFAULT_MODELS = types.MappingProxyType(
    {
        "embedding": {
            "model_id": "Qwen/Qwen3-Embedding-0.6B",
            "description": "Qwen3 0.6B text embedding model (1024 dimensions)",
            "revision": "master",
        },
        "reranker": {
            "model_id": "Qwen/Qwen3-Reranker-0.6B",
            "description": "Qwen3 0.6B reranking model",
            "revision": "master",
        },
        "query_expansion": {
            "model_id": "qwen/Qwen2.5-0.5B-Instruct",
            "description": "Query expansion model",
            "revision": "master",
        },
    }
)

DEFAULT_MODELS: types.MappingProxyType[str, dict[str, str]] = _DEFAULT_MODELS


def _home_directory() -> Path:
    """Return the user home directory through one overridable seam."""
    return Path.home()


def _home_models_root() -> Path:
    """Return the legacy ``~/.sif/models`` cache root."""
    return _home_directory() / ".sif" / "models"


def _resolve_cache_root(cache_dir: str | Path | None) -> Path:
    """Return the cache root, defaulting to ``Settings.get_cache_dir()/models``."""
    if cache_dir is None:
        from sif.config.settings import get_settings  # noqa: PLC0415

        return get_settings().get_cache_dir() / "models"
    return Path(cache_dir).expanduser()


def _split_model_id(model_id: str) -> tuple[str, str]:
    """Split a model id into exactly an owner and a name."""
    parts = model_id.split("/") if isinstance(model_id, str) else []
    if len(parts) != _MODEL_ID_PARTS or any(not part for part in parts):
        raise ValueError(f"Invalid model id {model_id!r}; expected 'owner/name'")
    if any(part in {".", ".."} or "\\" in part or "\x00" in part for part in parts):
        raise ValueError(f"Invalid model id {model_id!r}; expected 'owner/name'")
    return parts[0], parts[1]


def canonical_model_dir(cache_root: Path, model_id: str) -> Path:
    """Return the canonical ``<cache_root>/<owner>/<name>`` model directory."""
    owner, name = _split_model_id(model_id)
    return Path(cache_root) / owner / name


def _mangled_name(name: str) -> str:
    """Return the ModelScope cache spelling where dots become three underscores."""
    return name.replace(".", "___")


def _file_sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file, read once in 1 MiB chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest(model_dir: Path) -> dict[str, Any] | None:
    """Load the manifest payload, returning None when it is missing or malformed."""
    try:
        payload = json.loads((Path(model_dir) / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def verify_manifest(model_dir: Path) -> bool:
    """Return True when the manifest and every listed file match size and SHA-256."""
    root = Path(model_dir)
    payload = _read_manifest(root)
    if payload is None or payload.get("version") != MANIFEST_VERSION:
        return False
    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        return False
    return all(_manifest_entry_matches(root, relative, info) for relative, info in files.items())


def _manifest_entry_matches(root: Path, relative: object, info: object) -> bool:
    """Return True when one manifest entry resolves to a matching local file."""
    if not isinstance(relative, str) or not isinstance(info, dict):
        return False
    digest = info.get("sha256")
    size = info.get("size")
    if not isinstance(digest, str) or not isinstance(size, int) or isinstance(size, bool):
        return False
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return False
    candidate = root / relative_path
    try:
        if not candidate.is_file() or candidate.stat().st_size != size:
            return False
        return _file_sha256(candidate) == digest
    except OSError:
        return False


def _write_manifest(model_dir: Path, payload: dict[str, Any]) -> None:
    """Write the manifest atomically inside a model directory."""
    manifest = Path(model_dir) / MANIFEST_NAME
    temporary = manifest.with_name(manifest.name + _MANIFEST_TEMP_SUFFIX)
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(manifest)


def _modelscope_version() -> str | None:
    """Return the installed ModelScope version when the package is importable."""
    try:
        return version("modelscope")
    except PackageNotFoundError:
        return None


def _resolved_revision(model_dir: Path, requested: str) -> str:
    """Return the revision recorded by ModelScope's ``.mv`` marker, or the request."""
    try:
        marker = (Path(model_dir) / ".mv").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return requested
    match = re.search(r"Revision:([^,\r\n]+)", marker)
    if match is None or not match.group(1).strip():
        return requested
    return match.group(1).strip()


def _build_manifest(model_dir: Path, model_id: str, revision_requested: str) -> dict[str, Any]:
    """Hash every regular file in a model directory into a manifest payload."""
    root = Path(model_dir)
    files: dict[str, dict[str, object]] = {}
    for candidate in sorted(path for path in root.rglob("*") if path.is_file()):
        relative = candidate.relative_to(root).as_posix()
        if relative == MANIFEST_NAME or relative == MANIFEST_NAME + _MANIFEST_TEMP_SUFFIX:
            continue
        files[relative] = {
            "sha256": _file_sha256(candidate),
            "size": candidate.stat().st_size,
        }
    return {
        "version": MANIFEST_VERSION,
        "model_id": model_id,
        "model_type": "modelscope",
        "revision_requested": revision_requested,
        "revision_resolved": _resolved_revision(root, revision_requested),
        "modelscope_version": _modelscope_version(),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": files,
    }


def _unique_sibling(path: Path, kind: str) -> Path:
    """Return a unique sibling path used for temporary or backup directories."""
    return path.with_name(f"{path.name}.{kind}-{uuid.uuid4().hex[:8]}")


def _remove_path(path: Path) -> None:
    """Remove a file or directory tree without raising for ordinary races."""
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def _install_directory(staged: Path, target: Path, *, restore_staged: bool = False) -> None:
    """Replace ``target`` with ``staged`` only after manifest verification.

    When ``restore_staged`` is true the staged directory is the legacy source and
    is moved back on failure instead of being deleted; the original target is
    restored from its backup in both cases.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    staged_moved = False
    try:
        if target.exists():
            backup = _unique_sibling(target, "backup")
            target.rename(backup)
        staged.rename(target)
        staged_moved = True
        if not verify_manifest(target):
            raise RuntimeError(f"Model directory failed manifest verification: {target}")
    except BaseException:
        if staged_moved and restore_staged and target.exists() and not staged.exists():
            target.rename(staged)
        elif staged_moved and target.exists():
            _remove_path(target)
        if backup is not None and backup.exists() and not target.exists():
            backup.rename(target)
        raise
    if backup is not None and backup.exists():
        _remove_path(backup)


def _is_adoptable(path: Path) -> bool:
    """Return True when a legacy directory holds a config and at least one weight file."""
    try:
        if not path.is_dir() or not (path / "config.json").is_file():
            return False
        return any(
            child.is_file() and child.suffix.lower() in WEIGHT_SUFFIXES for child in path.rglob("*")
        )
    except OSError:
        return False


def _legacy_candidates(cache_root: Path, model_id: str, *, include_home: bool) -> tuple[Path, ...]:
    """Return the recognized legacy locations in deterministic order.

    Recognized layouts, tried in order:

    - ``<cache_root>/<owner>/<name___>`` — the ModelScope mangled tree, always.
    - ``<cache_root>/../<owner>/<name>`` and, when it differs, the mangled
      spelling — the pre-fix v1.2.0 embedder/reranker layout
      ``<cache>/<owner>/<name>`` as seen from the canonical ``<cache>/models``
      root. Probed only when the cache root itself is named ``models``, so an
      explicit root such as ``/tmp/custom`` never inspects its parent.
    - ``~/.sif/models/<owner>/<name___>`` — the legacy home tree, only when
      ``include_home`` is true (the default cache root).
    """
    root = Path(cache_root)
    owner, name = _split_model_id(model_id)
    mangled = _mangled_name(name)
    candidates = [root / owner / mangled]
    if root.name == "models":
        candidates.append(root.parent / owner / name)
        if mangled != name:
            candidates.append(root.parent / owner / mangled)
    if include_home:
        candidates.append(_home_models_root() / owner / mangled)
    return tuple(candidates)


def _find_legacy_model_dir(cache_root: Path, model_id: str, *, include_home: bool) -> Path | None:
    """Return the first adoptable legacy model directory, if any."""
    target = canonical_model_dir(cache_root, model_id)
    seen: set[Path] = set()
    for candidate in _legacy_candidates(cache_root, model_id, include_home=include_home):
        if candidate in seen or candidate == target:
            continue
        seen.add(candidate)
        if _is_adoptable(candidate):
            return candidate
    return None


def _adopt_legacy_model(
    cache_root: Path, model_id: str, revision_requested: str, *, include_home: bool
) -> Path | None:
    """Migrate a verified legacy model directory into the canonical target."""
    source = _find_legacy_model_dir(cache_root, model_id, include_home=include_home)
    if source is None:
        return None
    target = canonical_model_dir(cache_root, model_id)
    manifest_existed = (source / MANIFEST_NAME).exists()
    try:
        _write_manifest(source, _build_manifest(source, model_id, revision_requested))
        if not verify_manifest(source):
            raise ValueError(f"Legacy model directory failed verification: {source}")
        _install_directory(source, target, restore_staged=True)
    except (OSError, RuntimeError, ValueError):
        if not manifest_existed:
            (source / MANIFEST_NAME).unlink(missing_ok=True)
        (source / (MANIFEST_NAME + _MANIFEST_TEMP_SUFFIX)).unlink(missing_ok=True)
        logger.info(f"Could not migrate legacy model cache at {source}; downloading instead")
        return None
    logger.info(f"Migrated legacy model cache into {target}")
    return target


def _import_snapshot_download() -> Callable[..., Any]:
    """Import ModelScope lazily and raise an actionable error when it is absent."""
    try:
        from modelscope import snapshot_download  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(MODELSCOPE_INSTALL_HINT) from exc
    return snapshot_download


def _default_revision(model_id: str) -> str:
    """Return the registry revision for a known model id, else ``master``."""
    for entry in DEFAULT_MODELS.values():
        if entry.get("model_id") == model_id:
            revision = entry.get("revision")
            if isinstance(revision, str) and revision:
                return revision
    return "master"


def _cache_entry(owner: str, child: Path) -> dict[str, str] | None:
    """Describe one two-level cache directory, or None when it is not a model."""
    if "___" in child.name:
        if not _is_adoptable(child):
            return None
        model_id = f"{owner}/{child.name.replace('___', '.')}"
        return {
            "model_id": model_id,
            "name": model_id,
            "path": str(child),
            "source": "legacy",
        }
    try:
        if not any(child.iterdir()):
            return None
    except OSError:
        return None
    model_id = f"{owner}/{child.name}"
    return {
        "model_id": model_id,
        "name": model_id,
        "path": str(child),
        "source": "canonical",
    }


def _scan_cache_root(root: Path) -> list[dict[str, str]]:
    """List two-level model directories beneath one cache root."""
    if not root.is_dir():
        return []
    try:
        owners = sorted(path for path in root.iterdir() if path.is_dir() and not path.is_symlink())
    except OSError:
        return []
    entries: list[dict[str, str]] = []
    for owner_dir in owners:
        try:
            children = sorted(
                path for path in owner_dir.iterdir() if path.is_dir() and not path.is_symlink()
            )
        except OSError:
            continue
        entries.extend(
            entry for child in children if (entry := _cache_entry(owner_dir.name, child))
        )
    return entries


def inspect_cache(model_id: str, cache_dir: str | Path | None = None) -> dict[str, object]:
    """Report the cache state for a model without downloading anything.

    States are ``absent``, ``empty``, ``unverified``, ``legacy``, and ``valid``.
    """
    cache_root = _resolve_cache_root(cache_dir)
    target = canonical_model_dir(cache_root, model_id)
    result: dict[str, object] = {
        "model_id": model_id,
        "path": str(target),
        "state": "absent",
        "revision": None,
    }
    manifest = _read_manifest(target)
    if manifest is not None and verify_manifest(target):
        revision = manifest.get("revision_resolved") or manifest.get("revision_requested")
        result["state"] = "valid"
        result["revision"] = revision if isinstance(revision, str) else None
        return result
    if target.exists():
        result["state"] = "unverified"
        try:
            if target.is_dir() and not any(target.iterdir()):
                result["state"] = "empty"
        except OSError:
            pass
        return result
    if _find_legacy_model_dir(cache_root, model_id, include_home=cache_dir is None) is not None:
        result["state"] = "legacy"
    return result


class ModelDownloader:
    """Download models from ModelScope into a canonical, verified cache."""

    DEFAULT_MODELS = _DEFAULT_MODELS

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        """Initialize the downloader and create its cache root.

        Args:
            cache_dir: Cache root; defaults to ``Settings.get_cache_dir()/models``
        """
        self.cache_dir = _resolve_cache_root(cache_dir).expanduser().resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._include_legacy_home = cache_dir is None

    def download(
        self,
        model_id: str,
        revision: str | None = None,
        force: bool = False,
    ) -> Path:
        """Download a model and return its canonical, manifest-verified directory.

        Args:
            model_id: ModelScope model ID (``owner/name``)
            revision: Branch or tag name; defaults to the registry revision
            force: Re-download even when the existing cache verifies

        Returns:
            Path to the canonical model directory
        """
        target = canonical_model_dir(self.cache_dir, model_id)
        requested = revision or _default_revision(model_id)

        if not force and verify_manifest(target):
            logger.info(f"Using cached model: {model_id}")
            return target
        if not force:
            migrated = _adopt_legacy_model(
                self.cache_dir,
                model_id,
                requested,
                include_home=self._include_legacy_home,
            )
            if migrated is not None:
                return migrated

        snapshot_download = _import_snapshot_download()
        logger.info(f"Downloading model from ModelScope: {model_id}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = _unique_sibling(target, "tmp")
        try:
            temporary.mkdir(parents=True)
            download_kwargs = {
                "model_id": model_id,
                "revision": requested,
                "cache_dir": str(self.cache_dir),
                "local_dir": str(temporary),
            }
            if is_quiet():
                with suppress_output():
                    snapshot_download(**download_kwargs)
            else:
                snapshot_download(**download_kwargs)
            if not (temporary / "config.json").is_file():
                raise RuntimeError(f"Download did not produce config.json for {model_id}")
            _write_manifest(temporary, _build_manifest(temporary, model_id, requested))
            if not verify_manifest(temporary):
                raise RuntimeError(f"Download failed manifest verification for {model_id}")
            _install_directory(temporary, target)
        except BaseException:
            _remove_path(temporary)
            raise

        logger.info(f"Model downloaded to: {target}")
        return target

    def download_embedding_model(
        self,
        model_id: str | None = None,
        force: bool = False,
    ) -> Path:
        """Download the embedding model, using the registry default when omitted."""
        resolved = model_id or self.DEFAULT_MODELS["embedding"]["model_id"]
        return self.download(resolved, force=force)

    def download_reranker_model(
        self,
        model_id: str | None = None,
        force: bool = False,
    ) -> Path:
        """Download the reranker model, using the registry default when omitted."""
        resolved = model_id or self.DEFAULT_MODELS["reranker"]["model_id"]
        return self.download(resolved, force=force)

    def download_query_expansion_model(
        self,
        model_id: str | None = None,
        force: bool = False,
    ) -> Path:
        """Download the query expansion model, using the registry default when omitted."""
        resolved = model_id or self.DEFAULT_MODELS["query_expansion"]["model_id"]
        return self.download(resolved, force=force)

    def get_model_info(self, model_id: str) -> dict:
        """Get information about a model.

        Args:
            model_id: ModelScope model ID

        Returns:
            Model information dictionary
        """
        try:
            from modelscope.hub.api import HubApi  # noqa: PLC0415

            api = HubApi()
            info = api.get_model_info(model_id)
            return {
                "model_id": model_id,
                "name": info.get("Name", ""),
                "description": info.get("Description", ""),
                "tags": info.get("Tags", []),
            }
        except Exception as e:
            logger.error(f"Failed to get model info for {model_id}: {e}")
            return {"model_id": model_id, "error": str(e)}

    def list_cached_models(self) -> list[dict[str, str]]:
        """List canonical and recognized legacy model directories.

        The legacy ``~/.sif/models`` root is scanned only for the default cache
        root; an explicit cache root is reported on its own.

        Returns:
            Dictionaries carrying ``model_id``, ``name``, ``path``, and ``source``
        """
        entries = _scan_cache_root(self.cache_dir)
        home_root = _home_models_root()
        if self._include_legacy_home and home_root.resolve() != self.cache_dir.resolve():
            entries.extend(_scan_cache_root(home_root))
        deduped: dict[str, dict[str, str]] = {}
        for entry in entries:
            deduped.setdefault(entry["path"], entry)
        return sorted(deduped.values(), key=lambda item: item["model_id"])

    def clear_cache(self) -> None:
        """Clear cached models, refusing the filesystem root and the home directory."""
        root = self.cache_dir.resolve()
        if root == Path(root.anchor) or root == _home_directory().resolve():
            raise ValueError(f"Refusing to clear unsafe cache directory: {root}")
        _remove_path(root)
        root.mkdir(parents=True, exist_ok=True)
        logger.info("Model cache cleared")
