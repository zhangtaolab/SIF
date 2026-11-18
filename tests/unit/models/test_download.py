"""ModelDownloader tests: canonical layout, SHA-256 manifest, atomic install, legacy.

Every test is hermetic: the ModelScope client is a scoped fake, ``Path.home`` is
redirected through the module seam so a developer's real ``~/.sif/models`` is
never read or moved, and no network call is ever attempted.
"""

import hashlib
import json
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from sif.config.settings import Settings
from sif.models.download import (
    DEFAULT_MODELS,
    MANIFEST_NAME,
    ModelDownloader,
    canonical_model_dir,
    inspect_cache,
    verify_manifest,
)


@pytest.fixture
def modelscope_module() -> Generator[MagicMock, None, None]:
    """Inject a scoped ModelScope module and remove only injected keys afterward."""
    injected_keys = ("modelscope", "modelscope.hub", "modelscope.hub.api")
    previous = {key: sys.modules.get(key) for key in injected_keys}
    module = MagicMock()
    hub_api = MagicMock()
    module.hub.api = hub_api
    sys.modules["modelscope"] = module
    sys.modules["modelscope.hub"] = module.hub
    sys.modules["modelscope.hub.api"] = hub_api
    try:
        yield module
    finally:
        for key, value in previous.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the downloader's home seam so the real user cache is never touched."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr("sif.models.download._home_directory", lambda: home)
    return home


@pytest.fixture
def downloader(tmp_path: Path) -> ModelDownloader:
    """Construct a downloader whose cache is always beneath tmp_path."""
    return ModelDownloader(cache_dir=tmp_path / "models")


def _write_model_files(
    root: Path,
    *,
    weights: bytes = b"fake-weights",
    revision: str = "master",
) -> None:
    """Write a minimal ModelScope snapshot tree."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "config.json").write_text('{"model_type": "fake"}', encoding="utf-8")
    (root / "model.safetensors").write_bytes(weights)
    (root / ".mv").write_text(
        f"Revision:{revision},CreatedAt:2026-11-16T00:00:00Z", encoding="utf-8"
    )


def _manifest_files(root: Path) -> dict[str, dict[str, object]]:
    """Build manifest entries from the current files in a directory."""
    return {
        candidate.relative_to(root).as_posix(): {
            "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            "size": candidate.stat().st_size,
        }
        for candidate in sorted(path for path in root.rglob("*") if path.is_file())
    }


def _write_manifest_payload(root: Path, files: dict[str, dict[str, object]]) -> None:
    """Write a manifest payload with the declared schema keys."""
    payload = {
        "version": 1,
        "model_id": "owner/model",
        "model_type": "modelscope",
        "revision_requested": "master",
        "revision_resolved": "master",
        "modelscope_version": "1.36.0",
        "created_at": "2026-11-16T00:00:00Z",
        "files": files,
    }
    (root / MANIFEST_NAME).write_text(json.dumps(payload), encoding="utf-8")


def _publish_model(root: Path, *, weights: bytes = b"fake-weights") -> None:
    """Create a canonical, manifest-verified model directory."""
    _write_model_files(root, weights=weights)
    _write_manifest_payload(root, _manifest_files(root))


def _snapshot_writing(**kwargs: Any) -> str:
    """Fake snapshot_download that materializes a model in the supplied local_dir."""
    local_dir = Path(kwargs["local_dir"])
    _write_model_files(local_dir, revision=str(kwargs.get("revision", "master")))
    return str(local_dir)


def _residue(directory: Path, name: str) -> list[Path]:
    """Return temporary or backup siblings left for a target name."""
    return [
        *directory.glob(f"{name}.tmp-*"),
        *directory.glob(f"{name}.backup-*"),
    ]


class TestCanonicalLayout:
    """The cache path is a deterministic two-level owner/name layout."""

    def test_canonical_dir_keeps_dots_and_avoids_modelscope_mangling(self, tmp_path: Path) -> None:
        """The canonical path is owner/name with dots intact, never name___."""
        path = canonical_model_dir(tmp_path, "Qwen/Qwen3-Embedding-0.6B")

        assert path == tmp_path / "Qwen" / "Qwen3-Embedding-0.6B"
        assert "___" not in str(path)

    @pytest.mark.parametrize(
        "model_id", ["", "model", "owner/", "/name", "a/b/c", "..", "../name", "owner/.."]
    )
    def test_malformed_model_ids_raise_value_error(self, tmp_path: Path, model_id: str) -> None:
        """A model id without exactly owner/name is rejected before any work."""
        with pytest.raises(ValueError, match="Invalid model id"):
            canonical_model_dir(tmp_path, model_id)

    def test_default_cache_dir_is_settings_cache_models(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The default cache root is the platformdirs cache divided by models."""
        cache_root = tmp_path / "platform-cache"
        cache_root.mkdir()
        settings = MagicMock()
        settings.get_cache_dir.return_value = cache_root
        monkeypatch.setattr("sif.config.settings.get_settings", lambda: settings)

        result = ModelDownloader()

        assert result.cache_dir == (cache_root / "models").resolve()
        assert result.cache_dir.is_dir()

    def test_explicit_cache_dir_is_expanded_resolved_and_created(self, tmp_path: Path) -> None:
        """An explicit cache directory is normalized and created on demand."""
        cache = tmp_path / "nested" / "models"

        result = ModelDownloader(cache_dir=cache)

        assert result.cache_dir == cache.resolve()
        assert result.cache_dir.is_dir()


class TestCacheHitContract:
    """Only a manifest-verified tree is a cache hit."""

    def test_valid_manifest_returns_without_downloading(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """A verified cache short-circuits and never reaches ModelScope."""
        target = canonical_model_dir(downloader.cache_dir, "owner/cached")
        _publish_model(target)
        modelscope_module.snapshot_download.side_effect = AssertionError("network must not run")

        assert downloader.download("owner/cached") == target
        modelscope_module.snapshot_download.assert_not_called()

    def test_empty_directory_is_not_a_hit(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """An existing but empty canonical directory re-downloads."""
        target = canonical_model_dir(downloader.cache_dir, "owner/empty")
        target.mkdir(parents=True)
        modelscope_module.snapshot_download.side_effect = _snapshot_writing

        assert downloader.download("owner/empty") == target
        assert verify_manifest(target)
        modelscope_module.snapshot_download.assert_called_once()

    def test_nonempty_directory_without_manifest_is_not_a_hit(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """A populated but manifestless directory is not a cache hit."""
        target = canonical_model_dir(downloader.cache_dir, "owner/junk")
        target.mkdir(parents=True)
        (target / "config.json").write_text("{}", encoding="utf-8")
        modelscope_module.snapshot_download.side_effect = _snapshot_writing

        assert downloader.download("owner/junk") == target
        assert verify_manifest(target)
        modelscope_module.snapshot_download.assert_called_once()

    def test_size_mismatch_is_not_a_hit(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """A recorded size that no longer matches forces a re-download."""
        target = canonical_model_dir(downloader.cache_dir, "owner/size")
        _publish_model(target)
        (target / "model.safetensors").write_bytes(b"short")
        modelscope_module.snapshot_download.side_effect = _snapshot_writing

        assert downloader.download("owner/size") == target
        modelscope_module.snapshot_download.assert_called_once()

    def test_hash_mismatch_is_not_a_hit(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """Same-size content with a different digest forces a re-download."""
        target = canonical_model_dir(downloader.cache_dir, "owner/hash")
        _publish_model(target)
        (target / "model.safetensors").write_bytes(b"fake-weightz")
        modelscope_module.snapshot_download.side_effect = _snapshot_writing

        assert downloader.download("owner/hash") == target
        modelscope_module.snapshot_download.assert_called_once()

    def test_force_redownloads_despite_valid_manifest(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """Force bypasses the manifest check and refreshes the tree."""
        target = canonical_model_dir(downloader.cache_dir, "owner/forced")
        _publish_model(target)
        modelscope_module.snapshot_download.side_effect = _snapshot_writing

        assert downloader.download("owner/forced", force=True) == target
        modelscope_module.snapshot_download.assert_called_once()


class TestManifest:
    """The manifest records SHA-256 digests and the declared metadata keys."""

    def test_manifest_declares_keys_and_sha256_digest(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """The written manifest carries the declared keys, SHA-256, and a revision."""
        modelscope_module.snapshot_download.side_effect = _snapshot_writing
        target = downloader.download("owner/model")

        manifest = json.loads((target / MANIFEST_NAME).read_text(encoding="utf-8"))

        assert manifest["version"] == 1
        assert manifest["model_id"] == "owner/model"
        assert manifest["model_type"] == "modelscope"
        assert manifest["revision_requested"] == "master"
        assert manifest["revision_resolved"] == "master"
        assert "modelscope_version" in manifest
        assert manifest["created_at"].endswith("Z")
        assert {"config.json", "model.safetensors", ".mv"} <= set(manifest["files"])
        entry = manifest["files"]["model.safetensors"]
        assert entry["sha256"] == hashlib.sha256(b"fake-weights").hexdigest()
        assert entry["size"] == len(b"fake-weights")
        assert entry["sha256"] != hashlib.md5(b"fake-weights").hexdigest()

    def test_verify_manifest_accepts_published_model(self, tmp_path: Path) -> None:
        """A freshly published tree verifies."""
        target = tmp_path / "models" / "owner" / "model"
        _publish_model(target)

        assert verify_manifest(target) is True

    @pytest.mark.parametrize(
        "case",
        [
            "missing",
            "invalid_json",
            "wrong_version",
            "empty_files",
            "missing_file",
            "traversal",
        ],
    )
    def test_verify_manifest_rejects_broken_manifests(self, tmp_path: Path, case: str) -> None:
        """Every malformed or incomplete manifest state is rejected."""
        target = tmp_path / "models" / "owner" / "model"
        _publish_model(target)
        manifest_path = target / MANIFEST_NAME
        if case == "missing":
            manifest_path.unlink()
        elif case == "invalid_json":
            manifest_path.write_text("{not json", encoding="utf-8")
        elif case == "wrong_version":
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["version"] = 2
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        elif case == "empty_files":
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["files"] = {}
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        elif case == "missing_file":
            (target / "model.safetensors").unlink()
        else:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["files"] = {"../escape": {"sha256": "0" * 64, "size": 1}}
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")

        assert verify_manifest(target) is False


class TestAtomicInstall:
    """A failed download leaves no partial target and no scratch directories."""

    def test_success_leaves_no_temporary_or_backup_directories(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """A successful install cleans its temporary and backup siblings."""
        modelscope_module.snapshot_download.side_effect = _snapshot_writing
        target = downloader.download("owner/model")

        assert verify_manifest(target)
        assert _residue(target.parent, target.name) == []

    def test_replaces_unverified_target_and_removes_backup(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """An existing unverified target is replaced after the new tree verifies."""
        target = canonical_model_dir(downloader.cache_dir, "owner/model")
        target.mkdir(parents=True)
        (target / "config.json").write_text("{}", encoding="utf-8")
        modelscope_module.snapshot_download.side_effect = _snapshot_writing

        result = downloader.download("owner/model")

        assert result == target
        assert verify_manifest(target)
        assert _residue(target.parent, target.name) == []

    def test_client_failure_leaves_no_target_or_scratch_directory(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """A client exception propagates and cleans the temporary directory."""
        target = canonical_model_dir(downloader.cache_dir, "owner/broken")
        modelscope_module.snapshot_download.side_effect = RuntimeError("download failed")

        with pytest.raises(RuntimeError, match="download failed"):
            downloader.download("owner/broken")

        assert not target.exists()
        assert _residue(target.parent, target.name) == []

    def test_missing_config_json_fails_and_cleans_up(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """A snapshot without config.json is rejected and removed."""

        def only_weights(**kwargs: Any) -> str:
            Path(kwargs["local_dir"]).mkdir(parents=True, exist_ok=True)
            (Path(kwargs["local_dir"]) / "model.safetensors").write_bytes(b"weights")
            return str(kwargs["local_dir"])

        modelscope_module.snapshot_download.side_effect = only_weights
        target = canonical_model_dir(downloader.cache_dir, "owner/no-config")

        with pytest.raises(RuntimeError, match=r"config\.json"):
            downloader.download("owner/no-config")

        assert not target.exists()
        assert _residue(target.parent, target.name) == []


class TestMissingDependency:
    """A missing optional dependency yields an actionable error, not a traceback."""

    def test_missing_modelscope_raises_actionable_import_error(
        self, downloader: ModelDownloader
    ) -> None:
        """The ImportError names the embed extra and creates no partial cache."""
        target = canonical_model_dir(downloader.cache_dir, "owner/model")

        with patch.dict(sys.modules, {"modelscope": None}):
            with pytest.raises(ImportError, match="install the embed extra") as excinfo:
                downloader.download("owner/model")

        assert "modelscope is required" in str(excinfo.value)
        assert not target.exists()
        assert _residue(target.parent, target.name) == []


class TestInspectCache:
    """inspect_cache is a deterministic, offline state report."""

    def test_reports_all_states_without_importing_modelscope(
        self, tmp_path: Path, isolated_home: Path
    ) -> None:
        """absent, empty, unverified, legacy, and valid are distinct."""
        cache_root = tmp_path / "models"
        empty_target = canonical_model_dir(cache_root, "owner/empty")
        empty_target.mkdir(parents=True)
        unverified = canonical_model_dir(cache_root, "owner/unverified")
        unverified.mkdir(parents=True)
        (unverified / "config.json").write_text("{}", encoding="utf-8")
        legacy = cache_root / "owner" / "legacy___model"
        _write_model_files(legacy)
        valid = canonical_model_dir(cache_root, "owner/valid.model")
        _publish_model(valid)

        with patch.dict(sys.modules, {"modelscope": None}):
            assert inspect_cache("owner/absent", cache_root)["state"] == "absent"
            assert inspect_cache("owner/empty", cache_root)["state"] == "empty"
            assert inspect_cache("owner/unverified", cache_root)["state"] == "unverified"
            legacy_result = inspect_cache("owner/legacy.model", cache_root)
            assert legacy_result["state"] == "legacy"
            valid_result = inspect_cache("owner/valid.model", cache_root)

        assert valid_result["state"] == "valid"
        assert valid_result["revision"] == "master"
        assert valid_result["path"] == str(valid)
        assert isolated_home.is_dir()

    def test_rejects_malformed_model_ids(self, tmp_path: Path) -> None:
        """An invalid id is a named ValueError, not a filesystem lookup."""
        with pytest.raises(ValueError, match="Invalid model id"):
            inspect_cache("not-a-model-id", tmp_path)


class TestLegacyMigration:
    """Both legacy layouts migrate without data loss or false hits."""

    def test_modelscope_layout_is_migrated(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """<cache>/<owner>/<name___> is adopted and removed after verification."""
        legacy = downloader.cache_dir / "owner" / "legacy___model"
        _write_model_files(legacy)
        modelscope_module.snapshot_download.side_effect = AssertionError("network must not run")

        target = downloader.download("owner/legacy.model")

        assert target == canonical_model_dir(downloader.cache_dir, "owner/legacy.model")
        assert verify_manifest(target)
        assert not legacy.exists()
        modelscope_module.snapshot_download.assert_not_called()

    def test_home_sif_models_layout_is_migrated(
        self,
        tmp_path: Path,
        modelscope_module: MagicMock,
        isolated_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """~/.sif/models/<owner>/<name___> is adopted for the default cache root."""
        cache_root = tmp_path / "platform-cache"
        cache_root.mkdir()
        settings = MagicMock()
        settings.get_cache_dir.return_value = cache_root
        monkeypatch.setattr("sif.config.settings.get_settings", lambda: settings)
        downloader = ModelDownloader()
        legacy = isolated_home / ".sif" / "models" / "owner" / "home___model"
        _write_model_files(legacy)
        modelscope_module.snapshot_download.side_effect = AssertionError("network must not run")

        target = downloader.download("owner/home.model")

        assert target == canonical_model_dir(downloader.cache_dir, "owner/home.model")
        assert verify_manifest(target)
        assert not legacy.exists()
        modelscope_module.snapshot_download.assert_not_called()

    def test_pre_fix_parent_root_layout_is_migrated(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """v1.2.0's <cache>/<owner>/<name> tree is adopted into <cache>/models."""
        legacy = downloader.cache_dir.parent / "owner" / "legacy.model"
        _write_model_files(legacy)
        modelscope_module.snapshot_download.side_effect = AssertionError("network must not run")

        assert inspect_cache("owner/legacy.model", downloader.cache_dir)["state"] == "legacy"

        target = downloader.download("owner/legacy.model")

        assert target == canonical_model_dir(downloader.cache_dir, "owner/legacy.model")
        assert verify_manifest(target)
        assert not legacy.exists()
        modelscope_module.snapshot_download.assert_not_called()

    def test_non_models_root_never_probes_its_parent(
        self, tmp_path: Path, modelscope_module: MagicMock
    ) -> None:
        """An explicit root not named ``models`` never inspects its parent."""
        downloader = ModelDownloader(cache_dir=tmp_path / "custom")
        legacy = downloader.cache_dir.parent / "owner" / "parent___model"
        _write_model_files(legacy)
        modelscope_module.snapshot_download.side_effect = _snapshot_writing

        assert inspect_cache("owner/parent.model", downloader.cache_dir)["state"] == "absent"

        target = downloader.download("owner/parent.model")

        assert verify_manifest(target)
        assert legacy.exists()
        assert (legacy / "config.json").is_file()
        modelscope_module.snapshot_download.assert_called_once()

    def test_explicit_cache_root_ignores_home_legacy(
        self, downloader: ModelDownloader, isolated_home: Path
    ) -> None:
        """An explicit cache root is hermetic; the home legacy tree is not adopted."""
        legacy = isolated_home / ".sif" / "models" / "owner" / "home___legacy"
        _write_model_files(legacy)

        assert inspect_cache("owner/home.legacy", downloader.cache_dir)["state"] == "absent"
        assert downloader.list_cached_models() == []

    def test_failed_rename_falls_back_to_download_and_keeps_source(
        self,
        downloader: ModelDownloader,
        modelscope_module: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A failing legacy move leaves the source intact and downloads instead."""
        legacy = downloader.cache_dir / "owner" / "kept___model"
        _write_model_files(legacy)
        real_rename = Path.rename

        def flaky_rename(self: Path, target: Path) -> Path:
            if self == legacy:
                raise OSError("rename refused")
            return real_rename(self, target)

        monkeypatch.setattr(Path, "rename", flaky_rename)
        modelscope_module.snapshot_download.side_effect = _snapshot_writing

        target = downloader.download("owner/kept.model")

        assert verify_manifest(target)
        assert legacy.exists()
        assert (legacy / "config.json").is_file()
        assert not (legacy / MANIFEST_NAME).exists()
        modelscope_module.snapshot_download.assert_called_once()

    def test_legacy_directory_without_weights_is_ignored(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """A config-only legacy tree is never blessed as cached."""
        legacy = downloader.cache_dir / "owner" / "partial___model"
        legacy.mkdir(parents=True)
        (legacy / "config.json").write_text("{}", encoding="utf-8")
        modelscope_module.snapshot_download.side_effect = _snapshot_writing

        target = downloader.download("owner/partial.model")

        assert verify_manifest(target)
        assert legacy.exists()
        modelscope_module.snapshot_download.assert_called_once()

    def test_inspect_reports_legacy_then_valid(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """The same tree reports legacy before migration and valid afterward."""
        legacy = downloader.cache_dir / "owner" / "state___model"
        _write_model_files(legacy)
        modelscope_module.snapshot_download.side_effect = _snapshot_writing

        assert inspect_cache("owner/state.model", downloader.cache_dir)["state"] == "legacy"

        downloader.download("owner/state.model")

        assert inspect_cache("owner/state.model", downloader.cache_dir)["state"] == "valid"


class TestRegistry:
    """DEFAULT_MODELS matches the shipped Settings defaults (D-09)."""

    def test_registry_matches_shipped_settings_defaults(self) -> None:
        """Embedding and reranker ids equal the shipped Settings values."""
        settings = Settings(_env_file=None)

        assert DEFAULT_MODELS["embedding"]["model_id"] == settings.model_name
        assert DEFAULT_MODELS["reranker"]["model_id"] == settings.reranker_model_name
        assert DEFAULT_MODELS["query_expansion"]["model_id"] == "qwen/Qwen2.5-0.5B-Instruct"

    def test_registry_pins_master_revision_for_every_entry(self) -> None:
        """Every registry entry names an explicit branch revision."""
        assert {entry["revision"] for entry in DEFAULT_MODELS.values()} == {"master"}

    def test_class_registry_shares_the_module_mapping(self) -> None:
        """ModelDownloader.DEFAULT_MODELS is the importable module mapping."""
        assert ModelDownloader.DEFAULT_MODELS is DEFAULT_MODELS


class TestListingAndClearing:
    """Listing spans only the cache root and the legacy root; clearing is guarded."""

    def test_list_cached_models_reports_canonical_and_legacy(
        self,
        tmp_path: Path,
        isolated_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Canonical entries and recognized legacy entries report their model ids."""
        cache_root = tmp_path / "platform-cache"
        cache_root.mkdir()
        settings = MagicMock()
        settings.get_cache_dir.return_value = cache_root
        monkeypatch.setattr("sif.config.settings.get_settings", lambda: settings)
        downloader = ModelDownloader()
        canonical = canonical_model_dir(downloader.cache_dir, "owner/canonical.model")
        _publish_model(canonical)
        cache_legacy = downloader.cache_dir / "owner" / "cache___legacy"
        _write_model_files(cache_legacy)
        home_legacy = isolated_home / ".sif" / "models" / "owner" / "home___legacy"
        _write_model_files(home_legacy)

        entries = {entry["model_id"]: entry for entry in downloader.list_cached_models()}

        assert set(entries) == {
            "owner/canonical.model",
            "owner/cache.legacy",
            "owner/home.legacy",
        }
        assert entries["owner/canonical.model"]["source"] == "canonical"
        assert entries["owner/cache.legacy"]["source"] == "legacy"
        assert entries["owner/home.legacy"]["source"] == "legacy"

    def test_list_cached_models_missing_root_returns_empty(
        self, downloader: ModelDownloader, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The defensive missing-cache branch returns no entries."""
        monkeypatch.setattr(downloader, "cache_dir", downloader.cache_dir / "missing")

        assert downloader.list_cached_models() == []

    def test_clear_cache_refuses_home_directory(
        self, downloader: ModelDownloader, isolated_home: Path
    ) -> None:
        """The home directory is never cleared."""
        downloader.cache_dir = isolated_home

        with pytest.raises(ValueError, match="unsafe cache directory"):
            downloader.clear_cache()

        assert isolated_home.is_dir()

    def test_clear_cache_refuses_filesystem_root(self, downloader: ModelDownloader) -> None:
        """The filesystem root is never cleared."""
        downloader.cache_dir = Path("/")

        with pytest.raises(ValueError, match="unsafe cache directory"):
            downloader.clear_cache()

    def test_clear_cache_recreates_and_preserves_outside_paths(
        self, downloader: ModelDownloader
    ) -> None:
        """Clearing removes only cache content and recreates a reusable root."""
        model = downloader.cache_dir / "owner" / "model"
        model.mkdir(parents=True)
        (model / "weights.bin").write_text("weights", encoding="utf-8")
        outside = downloader.cache_dir.parent / "outside.txt"
        outside.write_text("keep me", encoding="utf-8")

        downloader.clear_cache()

        assert downloader.cache_dir.is_dir()
        assert list(downloader.cache_dir.iterdir()) == []
        assert outside.read_text(encoding="utf-8") == "keep me"

        downloader.clear_cache()

        assert downloader.list_cached_models() == []


class TestDownloadBehavior:
    """Quiet suppression, convenience delegation, and hub metadata mapping."""

    def test_download_quiet_suppresses_output(
        self,
        downloader: ModelDownloader,
        modelscope_module: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Quiet mode suppresses client stdout/stderr but still installs the model."""

        def noisy_download(**kwargs: Any) -> str:
            print("client stdout")
            print("client stderr", file=sys.stderr)
            return _snapshot_writing(**kwargs)

        modelscope_module.snapshot_download.side_effect = noisy_download
        with patch("sif.models.download.is_quiet", return_value=True):
            result = downloader.download("owner/quiet")

        captured = capsys.readouterr()
        assert verify_manifest(result)
        assert captured.out == ""
        assert captured.err == ""

    @pytest.mark.parametrize(
        ("method_name", "kind", "custom_id"),
        [
            ("download_embedding_model", "embedding", "org/custom-embedding"),
            ("download_reranker_model", "reranker", "org/custom-reranker"),
            ("download_query_expansion_model", "query_expansion", "org/custom-query"),
        ],
    )
    def test_convenience_methods_delegate_with_registry_defaults(
        self,
        downloader: ModelDownloader,
        modelscope_module: MagicMock,
        method_name: str,
        kind: str,
        custom_id: str,
    ) -> None:
        """Each convenience method resolves its registry default or the supplied id."""
        modelscope_module.snapshot_download.side_effect = _snapshot_writing
        method = getattr(downloader, method_name)

        default_target = method()
        custom_target = method(custom_id, force=True)

        default_id = DEFAULT_MODELS[kind]["model_id"]
        assert default_target == canonical_model_dir(downloader.cache_dir, default_id)
        assert custom_target == canonical_model_dir(downloader.cache_dir, custom_id)
        calls = modelscope_module.snapshot_download.call_args_list
        assert calls[0].kwargs["model_id"] == default_id
        assert calls[0].kwargs["revision"] == "master"
        assert calls[1].kwargs["model_id"] == custom_id

    def test_get_model_info_maps_expected_fields(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """Hub metadata maps into the downloader's stable information dictionary."""
        hub_api_class = modelscope_module.hub.api.HubApi
        hub_api_class.return_value.get_model_info.return_value = {
            "Name": "Example",
            "Description": "Example description",
            "Tags": ["embedding", "test"],
            "Ignored": "value",
        }

        result = downloader.get_model_info("org/model")

        assert result == {
            "model_id": "org/model",
            "name": "Example",
            "description": "Example description",
            "tags": ["embedding", "test"],
        }

    def test_get_model_info_defaults_and_error_dictionary(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """Missing metadata uses defaults and Hub failures become an error result."""
        api = modelscope_module.hub.api.HubApi.return_value
        api.get_model_info.return_value = {}

        assert downloader.get_model_info("org/empty") == {
            "model_id": "org/empty",
            "name": "",
            "description": "",
            "tags": [],
        }

        api.get_model_info.side_effect = RuntimeError("hub unavailable")
        assert downloader.get_model_info("org/broken") == {
            "model_id": "org/broken",
            "error": "hub unavailable",
        }
