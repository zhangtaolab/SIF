"""ModelDownloader tests with temporary caches and mocked ModelScope clients."""

import hashlib
import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sif.models.download import ModelDownloader


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


@pytest.fixture
def downloader(tmp_path: Path) -> ModelDownloader:
    """Construct a downloader whose cache is always beneath tmp_path."""
    return ModelDownloader(cache_dir=tmp_path / "models")


class TestModelDownloader:
    """Downloader behavior is isolated from network and real home caches."""

    def test_default_cache_dir_resolves_under_monkeypatched_home(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The default cache expands HOME and creates only a temporary directory."""
        monkeypatch.setenv("HOME", str(tmp_path))

        result = ModelDownloader()

        assert result.cache_dir == (tmp_path / ".sif" / "models").resolve()
        assert result.cache_dir.is_dir()
        assert result.cache_dir.is_relative_to(tmp_path.resolve())

    def test_explicit_cache_dir_is_expanded_resolved_and_created(self, tmp_path: Path) -> None:
        """An explicit cache directory is normalized and created on demand."""
        cache = tmp_path / "nested" / "models"

        result = ModelDownloader(cache_dir=cache)

        assert result.cache_dir == cache.resolve()
        assert result.cache_dir.is_dir()

    def test_download_returns_path_and_passes_exact_kwargs(
        self, downloader: ModelDownloader, modelscope_module: MagicMock, tmp_path: Path
    ) -> None:
        """A successful download returns its Path and calls snapshot_download at source."""
        downloaded = tmp_path / "downloaded"
        modelscope_module.snapshot_download.return_value = str(downloaded)

        result = downloader.download("org/model", revision="v1.2")

        assert result == downloaded
        modelscope_module.snapshot_download.assert_called_once_with(
            model_id="org/model",
            cache_dir=str(downloader.cache_dir),
            revision="v1.2",
        )

    def test_download_uses_cached_nonempty_model_directory(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """A populated cache short-circuits without importing a usable network client."""
        model_id = "org/cached"
        model_hash = hashlib.md5(model_id.encode()).hexdigest()[:8]
        cached = downloader.cache_dir / model_hash
        cached.mkdir()
        (cached / "config.json").write_text("{}", encoding="utf-8")
        modelscope_module.snapshot_download.side_effect = AssertionError("network must not run")

        assert downloader.download(model_id) == cached
        modelscope_module.snapshot_download.assert_not_called()

    def test_download_force_bypasses_populated_cache(
        self, downloader: ModelDownloader, modelscope_module: MagicMock, tmp_path: Path
    ) -> None:
        """Force re-downloads even when the expected model cache is populated."""
        model_id = "org/cached"
        model_hash = hashlib.md5(model_id.encode()).hexdigest()[:8]
        cached = downloader.cache_dir / model_hash
        cached.mkdir()
        (cached / "config.json").write_text("{}", encoding="utf-8")
        downloaded = tmp_path / "fresh"
        modelscope_module.snapshot_download.return_value = downloaded

        result = downloader.download(model_id, force=True)

        assert result == downloaded
        modelscope_module.snapshot_download.assert_called_once_with(
            model_id=model_id,
            cache_dir=str(downloader.cache_dir),
        )

    def test_download_quiet_suppresses_output(
        self,
        downloader: ModelDownloader,
        modelscope_module: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Quiet mode suppresses client stdout/stderr but preserves the returned Path."""
        downloaded = tmp_path / "quiet-model"

        def noisy_download(**_kwargs: object) -> str:
            print("client stdout")
            print("client stderr", file=sys.stderr)
            return str(downloaded)

        modelscope_module.snapshot_download.side_effect = noisy_download
        with patch("sif.models.download.is_quiet", return_value=True):
            result = downloader.download("org/quiet")

        captured = capsys.readouterr()
        assert result == downloaded
        assert captured.out == ""
        assert captured.err == ""

    def test_download_missing_modelscope_preserves_import_error(
        self, downloader: ModelDownloader
    ) -> None:
        """A missing optional dependency raises ImportError before any cache lookup."""
        with patch.dict(sys.modules, {"modelscope": None}):
            with pytest.raises(ImportError):
                downloader.download("org/model")

    def test_download_exception_propagates(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """Network/client errors propagate rather than returning a false cache Path."""
        modelscope_module.snapshot_download.side_effect = RuntimeError("download failed")

        with pytest.raises(RuntimeError, match="download failed"):
            downloader.download("org/broken")

    @pytest.mark.parametrize(
        ("method_name", "kind", "custom_id"),
        [
            ("download_embedding_model", "embedding", "org/custom-embedding"),
            ("download_reranker_model", "reranker", "org/custom-reranker"),
            ("download_query_expansion_model", "query_expansion", "org/custom-query"),
        ],
    )
    def test_download_convenience_methods_defaults_and_custom_ids(
        self,
        downloader: ModelDownloader,
        modelscope_module: MagicMock,
        tmp_path: Path,
        method_name: str,
        kind: str,
        custom_id: str,
    ) -> None:
        """Each convenience method uses its declared default or a supplied model ID."""
        method = getattr(downloader, method_name)
        modelscope_module.snapshot_download.return_value = str(tmp_path / kind)

        assert method() == tmp_path / kind
        assert method(custom_id, force=True) == tmp_path / kind

        default_id = ModelDownloader.DEFAULT_MODELS[kind]["model_id"]
        assert modelscope_module.snapshot_download.call_args_list[0].kwargs == {
            "model_id": default_id,
            "cache_dir": str(downloader.cache_dir),
        }
        assert modelscope_module.snapshot_download.call_args_list[1].kwargs == {
            "model_id": custom_id,
            "cache_dir": str(downloader.cache_dir),
        }

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
        hub_api_class.assert_called_once_with()
        hub_api_class.return_value.get_model_info.assert_called_once_with("org/model")

    def test_get_model_info_defaults_and_error_dictionary(
        self, downloader: ModelDownloader, modelscope_module: MagicMock
    ) -> None:
        """Missing metadata uses defaults and Hub failures become an error result."""
        api = modelscope_module.hub.api.HubApi.return_value
        api.get_model_info.return_value = {}

        defaults = downloader.get_model_info("org/empty")

        assert defaults == {
            "model_id": "org/empty",
            "name": "",
            "description": "",
            "tags": [],
        }

        api.get_model_info.side_effect = RuntimeError("hub unavailable")
        failure = downloader.get_model_info("org/broken")

        assert failure == {"model_id": "org/broken", "error": "hub unavailable"}

    def test_list_cached_models_empty_populated_and_files_ignored(
        self, downloader: ModelDownloader
    ) -> None:
        """Only cache subdirectories appear, with stable path/name dictionaries."""
        assert downloader.list_cached_models() == []

        first = downloader.cache_dir / "first"
        second = downloader.cache_dir / "second"
        first.mkdir()
        second.mkdir()
        (downloader.cache_dir / "ignored.txt").write_text("not a model", encoding="utf-8")

        result = downloader.list_cached_models()

        assert sorted(result, key=lambda item: item["name"]) == [
            {"path": str(first), "name": "first"},
            {"path": str(second), "name": "second"},
        ]

    def test_list_cached_models_missing_directory(
        self, downloader: ModelDownloader, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The defensive missing-cache branch returns no cached entries."""
        monkeypatch.setattr(downloader, "cache_dir", downloader.cache_dir / "missing")

        assert downloader.list_cached_models() == []

    def test_clear_cache_recreates_directory_and_is_idempotent(
        self, downloader: ModelDownloader
    ) -> None:
        """Clearing removes model content and recreates a reusable empty cache."""
        model = downloader.cache_dir / "model"
        model.mkdir()
        (model / "weights.bin").write_text("weights", encoding="utf-8")

        downloader.clear_cache()

        assert downloader.cache_dir.is_dir()
        assert list(downloader.cache_dir.iterdir()) == []

        downloader.clear_cache()

        assert downloader.cache_dir.is_dir()
        assert downloader.list_cached_models() == []
