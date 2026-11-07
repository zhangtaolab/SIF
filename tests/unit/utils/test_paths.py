"""Behavior tests for path expansion, normalization, and directory helpers."""

from pathlib import Path
from unittest.mock import patch

import pytest

from sif.utils.paths import (
    expand_path,
    get_cache_dir,
    get_config_dir,
    get_data_dir,
    get_relative_path,
    is_markdown_file,
    normalize_path,
)


class TestPathHelpers:
    """Path helpers use real temporary directories and isolated platform overrides."""

    def test_expand_path_home_relative_and_dot_segments(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Home, relative paths, and dot segments resolve to absolute paths."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        nested = tmp_path / "nested"
        nested.mkdir()

        assert expand_path("~/notes/../notes/a.md") == tmp_path.resolve() / "notes/a.md"
        assert expand_path("nested/../a.md") == tmp_path.resolve() / "a.md"

    def test_normalize_path_resolves_real_symlink(self, tmp_path: Path) -> None:
        """Normalization resolves symlinks while preserving nonexistent tails."""
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        alias = tmp_path / "alias"
        alias.symlink_to(real_dir)

        result = normalize_path(alias / "future.md")

        assert result == str(real_dir.resolve() / "future.md")
        assert Path(result).is_absolute()

    def test_normalize_unexpandable_user_degrades_to_raw_string(self) -> None:
        """An unknown ~user target is a non-throwing nonmatching raw path."""
        raw = "~sif-no-such-user-7f3a/notes.md"

        assert normalize_path(raw) == raw

    def test_normalize_resolution_oserror_degrades_to_raw_string(self) -> None:
        """Filesystem resolution errors degrade to the raw string instead of escaping."""
        with patch("sif.utils.paths.expand_path", side_effect=OSError("unresolvable")):
            assert normalize_path("/broken/path") == "/broken/path"

    def test_get_relative_path_inside_and_outside_base(self, tmp_path: Path) -> None:
        """Contained paths become relative; outside paths remain unchanged."""
        base = tmp_path / "base"
        contained = base / "notes" / "a.md"
        outside = tmp_path / "other" / "b.md"

        assert get_relative_path(contained, base) == Path("notes/a.md")
        assert get_relative_path(outside, base) == outside

    @pytest.mark.parametrize(
        ("name", "expected"),
        [("note.md", True), ("NOTE.MD", True), ("note.markdown", True), ("note.txt", False)],
    )
    def test_is_markdown_file_uses_case_insensitive_extensions(
        self, name: str, expected: bool
    ) -> None:
        """Markdown detection recognizes configured extensions case-insensitively."""
        assert is_markdown_file(Path(name)) is expected

    def test_get_data_dir_uses_override_beneath_tmp_path(self, tmp_path: Path) -> None:
        """Application data is created only at the overridden temporary location."""
        target = tmp_path / "data"

        with patch("sif.utils.paths.user_data_dir", return_value=str(target)) as user_data:
            result = get_data_dir()

        assert result == target
        assert target.is_dir()
        user_data.assert_called_once_with("sif")

    def test_get_cache_dir_uses_override_beneath_tmp_path(self, tmp_path: Path) -> None:
        """Application cache is created only at the overridden temporary location."""
        target = tmp_path / "cache"

        with patch("sif.utils.paths.user_cache_dir", return_value=str(target)) as user_cache:
            result = get_cache_dir()

        assert result == target
        assert target.is_dir()
        user_cache.assert_called_once_with("sif")

    def test_get_config_dir_uses_override_beneath_tmp_path(self, tmp_path: Path) -> None:
        """Application configuration is created only at the temporary location."""
        target = tmp_path / "config"

        with patch("sif.utils.paths.user_config_dir", return_value=str(target)) as user_config:
            result = get_config_dir()

        assert result == target
        assert target.is_dir()
        user_config.assert_called_once_with("sif")
