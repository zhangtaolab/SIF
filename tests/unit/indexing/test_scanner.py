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


class TestSharedPredicate:
    """LIVE-04 parity: scan() membership equals matches() truth (D-07/D-08)."""

    def test_default_ignore_patterns_include_editor_noise(self) -> None:
        """D-08: the four editor-noise patterns live in the shared list."""
        patterns = FileScanner.DEFAULT_IGNORE_PATTERNS
        for required in ("*.sb-*", "4913", ".#*", "*.tmp"):
            assert required in patterns

    def test_scan_membership_equals_matches_over_parametrized_tree(self, tmp_path: Path) -> None:
        """set(scan().files) == {p in tree if matches(...)}, incl. root-level files."""
        root = tmp_path / "notes"
        sub = root / "sub"
        nested_ignored = root / "node_modules"
        sub.mkdir(parents=True)
        nested_ignored.mkdir()
        files = {
            root / "note.md": "root-level file (zero-dir **/ case)",
            sub / "note2.md": "nested file",
            nested_ignored / "x.md": "file under an ignored directory",
            root / "a.md.sb-ABCD": "atomic-save temp",
            root / "4913": "vim housekeeping",
            root / ".#b.md": "emacs lock (matches *.md!)",
            root / "c.tmp": "tmp scratch",
            root / "d.swp": "swap",
            root / "e~": "backup suffix",
        }
        for path, content in files.items():
            path.write_text(content, encoding="utf-8")

        scanner = FileScanner()
        scan_result = scanner.scan(root)
        matches_truth = {p for p in files if scanner.matches(root, p)}

        assert set(scan_result.files) == matches_truth
        assert matches_truth == {root / "note.md", sub / "note2.md"}

    def test_watch_ignore_patterns_setting_extends_both_scan_and_matches(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A4: the settings field extends the SHARED predicate — no scan/watch drift."""
        import os

        from sif.config.settings import Settings

        for key in [k for k in os.environ if k.startswith("SIF_")]:
            monkeypatch.delenv(key, raising=False)
        fake = Settings(watch_ignore_patterns=["secret/**"])
        monkeypatch.setattr("sif.config.settings.get_settings", lambda: fake)

        root = tmp_path / "notes"
        secret = root / "secret"
        secret.mkdir(parents=True)
        keep = root / "keep.md"
        hidden = secret / "under.md"
        keep.write_text("kept", encoding="utf-8")
        hidden.write_text("hidden", encoding="utf-8")

        scanner = FileScanner()
        assert set(scanner.scan(root).files) == {keep}
        assert scanner.matches(root, hidden) is False
        assert scanner.matches(root, keep) is True
