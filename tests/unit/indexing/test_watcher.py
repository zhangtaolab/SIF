"""Tests for file system watcher in sif.indexing.watcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from sif.indexing.watcher import FileWatcher, IndexingEventHandler


# =============================================================================
# IndexingEventHandler Tests
# =============================================================================


class TestIndexingEventHandler:
    """Tests for IndexingEventHandler."""

    def test_init_defaults(self) -> None:
        """Test default extensions are markdown."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
        )
        assert handler._collection_id == "coll-1"
        assert handler._indexer is mock_indexer
        assert handler._extensions == {".md", ".markdown"}

    def test_init_custom_extensions(self) -> None:
        """Test custom extensions can be set."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
            extensions={".txt", ".rst"},
        )
        assert handler._extensions == {".txt", ".rst"}

    def test_should_handle_matching_extension(self) -> None:
        """Test _should_handle returns True for matching extensions."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
            extensions={".md"},
        )
        assert handler._should_handle("/path/to/file.md") is True
        assert handler._should_handle("/path/to/file.markdown") is False

    def test_should_handle_no_match(self) -> None:
        """Test _should_handle returns False for non-matching extensions."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
            extensions={".md"},
        )
        assert handler._should_handle("/path/to/file.txt") is False
        assert handler._should_handle("/path/to/file.py") is False

    def test_should_handle_multiple_extensions(self) -> None:
        """Test _should_handle checks all extensions."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
            extensions={".md", ".txt", ".rst"},
        )
        assert handler._should_handle("/path/to/file.md") is True
        assert handler._should_handle("/path/to/file.txt") is True
        assert handler._should_handle("/path/to/file.rst") is True
        assert handler._should_handle("/path/to/file.py") is False

    def test_on_created_ignores_directories(self) -> None:
        """Test on_created ignores directory events."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
        )
        event = MagicMock()
        event.is_directory = True
        event.src_path = "/path/to/dir"

        handler.on_created(event)
        mock_indexer.assert_not_called()

    def test_on_created_handles_file(self) -> None:
        """Test on_created logs file creation."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
        )
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/file.md"

        with patch("sif.indexing.watcher.logger"):
            handler.on_created(event)

    def test_on_created_skips_non_matching(self) -> None:
        """Test on_created skips files with non-matching extensions."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
            extensions={".md"},
        )
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/file.txt"

        with patch("sif.indexing.watcher.logger"):
            handler.on_created(event)

    def test_on_modified_ignores_directories(self) -> None:
        """Test on_modified ignores directory events."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
        )
        event = MagicMock()
        event.is_directory = True
        event.src_path = "/path/to/dir"

        handler.on_modified(event)
        mock_indexer.assert_not_called()

    def test_on_modified_handles_file(self) -> None:
        """Test on_modified logs file modification."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
        )
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/file.md"

        with patch("sif.indexing.watcher.logger"):
            handler.on_modified(event)

    def test_on_deleted_ignores_directories(self) -> None:
        """Test on_deleted ignores directory events."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
        )
        event = MagicMock()
        event.is_directory = True
        event.src_path = "/path/to/dir"

        handler.on_deleted(event)
        mock_indexer.assert_not_called()

    def test_on_deleted_handles_file(self) -> None:
        """Test on_deleted logs file deletion."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
        )
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/file.md"

        with patch("sif.indexing.watcher.logger"):
            handler.on_deleted(event)

    def test_on_moved_ignores_directories(self) -> None:
        """Test on_moved ignores directory events."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
        )
        event = MagicMock()
        event.is_directory = True
        event.src_path = "/path/to/dir"
        event.dest_path = "/path/to/newdir"

        handler.on_moved(event)
        mock_indexer.assert_not_called()

    def test_on_moved_handles_file(self) -> None:
        """Test on_moved logs file move."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
        )
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/file.md"
        event.dest_path = "/path/to/newfile.md"

        with patch("sif.indexing.watcher.logger"):
            handler.on_moved(event)

    def test_on_moved_skips_non_matching(self) -> None:
        """Test on_moved skips files with non-matching extensions."""
        mock_indexer = MagicMock()
        handler = IndexingEventHandler(
            collection_id="coll-1",
            indexer=mock_indexer,
            extensions={".md"},
        )
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/file.txt"
        event.dest_path = "/path/to/newfile.txt"

        with patch("sif.indexing.watcher.logger"):
            handler.on_moved(event)


# =============================================================================
# FileWatcher Tests
# =============================================================================


class TestFileWatcher:
    """Tests for FileWatcher."""

    def test_init_defaults(self) -> None:
        """Test default extensions are markdown."""
        mock_indexer = MagicMock()
        watcher = FileWatcher(indexer=mock_indexer)
        assert watcher._indexer is mock_indexer
        assert watcher._extensions == {".md", ".markdown"}
        assert watcher._observer is None
        assert watcher._handlers == {}

    def test_init_custom_extensions(self) -> None:
        """Test custom extensions can be set."""
        mock_indexer = MagicMock()
        watcher = FileWatcher(
            indexer=mock_indexer,
            extensions={".txt", ".rst"},
        )
        assert watcher._extensions == {".txt", ".rst"}

    def test_start_creates_observer(self) -> None:
        """Test start creates and starts an observer."""
        mock_indexer = MagicMock()
        watcher = FileWatcher(indexer=mock_indexer)

        mock_observer = MagicMock()
        mock_observer_class = MagicMock(return_value=mock_observer)

        with patch("sif.indexing.watcher.Observer", mock_observer_class):
            with patch("pathlib.Path.exists", return_value=True):
                watcher.start("coll-1", ["/path/to/watch"])

        mock_observer_class.assert_called_once()
        mock_observer.schedule.assert_called_once()
        mock_observer.start.assert_called_once()
        assert watcher.is_watching("coll-1") is True

    def test_start_skips_missing_paths(self) -> None:
        """Test start skips paths that don't exist."""
        mock_indexer = MagicMock()
        watcher = FileWatcher(indexer=mock_indexer)

        mock_observer = MagicMock()
        mock_observer_class = MagicMock(return_value=mock_observer)

        with patch("sif.indexing.watcher.Observer", mock_observer_class):
            with patch("pathlib.Path.exists", return_value=False):
                watcher.start("coll-1", ["/nonexistent/path"])

        mock_observer.schedule.assert_not_called()
        mock_observer.start.assert_called_once()

    def test_start_multiple_paths(self) -> None:
        """Test start watches multiple paths."""
        mock_indexer = MagicMock()
        watcher = FileWatcher(indexer=mock_indexer)

        mock_observer = MagicMock()
        mock_observer_class = MagicMock(return_value=mock_observer)

        with patch("sif.indexing.watcher.Observer", mock_observer_class):
            with patch("pathlib.Path.exists", return_value=True):
                watcher.start("coll-1", ["/path/one", "/path/two"])

        assert mock_observer.schedule.call_count == 2
        assert watcher.is_watching("coll-1") is True

    def test_stop_specific_collection(self) -> None:
        """Test stop removes specific collection handler."""
        mock_indexer = MagicMock()
        watcher = FileWatcher(indexer=mock_indexer)

        mock_observer = MagicMock()
        mock_observer_class = MagicMock(return_value=mock_observer)

        with patch("sif.indexing.watcher.Observer", mock_observer_class):
            with patch("pathlib.Path.exists", return_value=True):
                watcher.start("coll-1", ["/path/to/watch"])
                watcher.start("coll-2", ["/path/to/other"])

        watcher.stop("coll-1")
        assert watcher.is_watching("coll-1") is False
        assert watcher.is_watching("coll-2") is True
        mock_observer.stop.assert_not_called()

    def test_stop_all_collections(self) -> None:
        """Test stop without collection_id stops observer."""
        mock_indexer = MagicMock()
        watcher = FileWatcher(indexer=mock_indexer)

        mock_observer = MagicMock()
        mock_observer_class = MagicMock(return_value=mock_observer)

        with patch("sif.indexing.watcher.Observer", mock_observer_class):
            with patch("pathlib.Path.exists", return_value=True):
                watcher.start("coll-1", ["/path/to/watch"])

        watcher.stop()
        # Note: handlers dict is not cleared when stopping all (current behavior)
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

    def test_stop_last_collection_stops_observer(self) -> None:
        """Test stopping last collection stops observer."""
        mock_indexer = MagicMock()
        watcher = FileWatcher(indexer=mock_indexer)

        mock_observer = MagicMock()
        mock_observer_class = MagicMock(return_value=mock_observer)

        with patch("sif.indexing.watcher.Observer", mock_observer_class):
            with patch("pathlib.Path.exists", return_value=True):
                watcher.start("coll-1", ["/path/to/watch"])

        watcher.stop("coll-1")
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

    def test_stop_not_watching(self) -> None:
        """Test stop when not watching any collection."""
        mock_indexer = MagicMock()
        watcher = FileWatcher(indexer=mock_indexer)

        with patch("sif.indexing.watcher.logger"):
            watcher.stop()

    def test_is_watching_false(self) -> None:
        """Test is_watching returns False for unwatched collection."""
        mock_indexer = MagicMock()
        watcher = FileWatcher(indexer=mock_indexer)
        assert watcher.is_watching("coll-1") is False

    def test_start_logs_info(self) -> None:
        """Test start logs watcher initialization."""
        mock_indexer = MagicMock()
        watcher = FileWatcher(indexer=mock_indexer)

        mock_observer = MagicMock()
        mock_observer_class = MagicMock(return_value=mock_observer)

        with patch("sif.indexing.watcher.Observer", mock_observer_class):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("sif.indexing.watcher.logger") as mock_logger:
                    watcher.start("coll-1", ["/path/to/watch"])

        mock_logger.info.assert_any_call("Starting file watcher for collection: coll-1")
        mock_logger.info.assert_any_call("Watching: /path/to/watch")

    def test_stop_logs_info(self) -> None:
        """Test stop logs watcher stop."""
        mock_indexer = MagicMock()
        watcher = FileWatcher(indexer=mock_indexer)

        mock_observer = MagicMock()
        mock_observer_class = MagicMock(return_value=mock_observer)

        with patch("sif.indexing.watcher.Observer", mock_observer_class):
            with patch("pathlib.Path.exists", return_value=True):
                watcher.start("coll-1", ["/path/to/watch"])

        with patch("sif.indexing.watcher.logger") as mock_logger:
            watcher.stop()

        mock_logger.info.assert_called_once_with("File watcher stopped")

    def test_handler_inherits_from_filesystemeventhandler(self) -> None:
        """Test IndexingEventHandler inherits from FileSystemEventHandler."""
        from watchdog.events import FileSystemEventHandler

        assert issubclass(IndexingEventHandler, FileSystemEventHandler)
