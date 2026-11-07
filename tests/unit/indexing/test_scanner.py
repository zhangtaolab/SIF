"""Real temporary-tree behavior tests for recursive file scanning."""

from __future__ import annotations

from pathlib import Path

from sif.indexing.scanner import FileScanner, ScanResult


class TestFileScanner:
    """Discovery, ignores, and statistics operate only beneath tmp_path."""

    def test_scan_finds_nested_matching_files_and_skips_ignores_and_directories(
        self, tmp_path: Path
    ) -> None:
        """Only real matching files outside ignored path components are returned."""
        notes = tmp_path / "notes"
        nested = notes / "nested"
        nested.mkdir(parents=True)
        included = notes / "root.md"
        nested_included = nested / "entry.md"
        included.write_text("root", encoding="utf-8")
        nested_included.write_text("nested", encoding="utf-8")
        (notes / "not-markdown.txt").write_text("other", encoding="utf-8")
        (nested / "draft.skip").write_text("custom ignore", encoding="utf-8")
        (nested / "also.md").write_text("custom ignore", encoding="utf-8")

        git = notes / ".git"
        git.mkdir()
        (git / "hidden.md").write_text("ignored", encoding="utf-8")
        (notes / "directory.md").mkdir()

        result = FileScanner().scan(notes, ignore_patterns=["*.skip", "also.md"])

        assert set(result.files) == {included, nested_included}
        assert result.file_count == 2
        assert result.scanned_dirs == {notes.resolve()}
        assert all(path.is_relative_to(tmp_path) for path in result.files)

    def test_scan_empty_result_uses_independent_default_collections(self, tmp_path: Path) -> None:
        """Default result values are empty and are not shared between instances."""
        first = ScanResult()
        second = ScanResult()

        first.files.append(tmp_path / "only-first.md")
        first.scanned_dirs.add(tmp_path)

        assert first.file_count == 0
        assert second.files == []
        assert second.scanned_dirs == set()
        assert second.file_count == 0

        result = FileScanner().scan(tmp_path)
        assert result.files == []
        assert result.file_count == 0
        assert result.scanned_dirs == {tmp_path.resolve()}

    def test_outside_root_path_is_not_ignored(self, tmp_path: Path) -> None:
        """The direct outside-root contract returns False rather than raising."""
        root = tmp_path / "root"
        root.mkdir()
        outside = tmp_path / "outside.md"
        outside.write_text("outside", encoding="utf-8")

        assert FileScanner()._should_ignore(outside, root, ["*.md"]) is False

    def test_full_relative_path_glob_ignores_nested_match(self, tmp_path: Path) -> None:
        """A pattern matching the entire relative path ignores that nested file."""
        root = tmp_path / "root"
        nested = root / "private"
        nested.mkdir(parents=True)
        hidden = nested / "entry.md"
        hidden.write_text("hidden", encoding="utf-8")

        assert FileScanner()._should_ignore(hidden, root, ["private/*.md"]) is True

    def test_get_stats_aggregates_extensions_and_existing_file_sizes(self, tmp_path: Path) -> None:
        """Missing files do not contribute bytes; extension counts retain scan entries."""
        markdown = tmp_path / "note.MD"
        plain = tmp_path / "note.txt"
        extensionless = tmp_path / "README"
        removed = tmp_path / "removed.md"
        for path, content in [(markdown, "你好"), (plain, "abc"), (extensionless, "12345")]:
            path.write_text(content, encoding="utf-8")
        removed.write_text("gone", encoding="utf-8")
        expected_size = sum(path.stat().st_size for path in (markdown, plain, extensionless))
        removed.unlink()
        result = ScanResult(files=[markdown, plain, extensionless, removed])

        stats = FileScanner().get_stats(result)

        assert result.file_count == 4
        assert stats == {
            "file_count": 4,
            "total_size_bytes": expected_size,
            "total_size_mb": round(expected_size / (1024 * 1024), 2),
            "extensions": {".md": 2, ".txt": 1, "(no extension)": 1},
        }
