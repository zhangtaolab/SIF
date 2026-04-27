"""File system watcher for auto-indexing."""

from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from sif.utils.logging import get_logger

logger = get_logger(__name__)


class IndexingEventHandler(FileSystemEventHandler):
    """Event handler for file system changes."""

    def __init__(
        self,
        collection_id: str,
        indexer: "DocumentIndexer",
        extensions: set[str] | None = None,
    ) -> None:
        """Initialize event handler.

        Args:
            collection_id: Collection ID
            indexer: Document indexer
            extensions: File extensions to watch
        """
        self._collection_id = collection_id
        self._indexer = indexer
        self._extensions = extensions or {".md", ".markdown"}

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation."""
        if event.is_directory:
            return

        if self._should_handle(event.src_path):
            logger.info(f"File created: {event.src_path}")
            # Trigger incremental index

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification."""
        if event.is_directory:
            return

        if self._should_handle(event.src_path):
            logger.info(f"File modified: {event.src_path}")
            # Trigger incremental index

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion."""
        if event.is_directory:
            return

        if self._should_handle(event.src_path):
            logger.info(f"File deleted: {event.src_path}")
            # Trigger removal from index

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move/rename."""
        if event.is_directory:
            return

        if self._should_handle(event.src_path):
            logger.info(f"File moved: {event.src_path} -> {event.dest_path}")
            # Trigger update

    def _should_handle(self, path: str) -> bool:
        """Check if a path should be handled.

        Args:
            path: File path

        Returns:
            True if path should be handled
        """
        return any(path.endswith(ext) for ext in self._extensions)


class FileWatcher:
    """File system watcher for auto-indexing.

    Watches directories for changes and triggers incremental
    indexing when files are created, modified, or deleted.
    """

    def __init__(
        self,
        indexer: "DocumentIndexer",
        extensions: set[str] | None = None,
    ) -> None:
        """Initialize file watcher.

        Args:
            indexer: Document indexer
            extensions: File extensions to watch
        """
        self._indexer = indexer
        self._extensions = extensions or {".md", ".markdown"}
        self._observer: Observer | None = None
        self._handlers: dict[str, IndexingEventHandler] = {}

    def start(self, collection_id: str, paths: list[str]) -> None:
        """Start watching paths.

        Args:
            collection_id: Collection ID
            paths: Paths to watch
        """
        logger.info(f"Starting file watcher for collection: {collection_id}")

        self._observer = Observer()

        handler = IndexingEventHandler(
            collection_id=collection_id,
            indexer=self._indexer,
            extensions=self._extensions,
        )

        for path in paths:
            if Path(path).exists():
                self._observer.schedule(handler, path, recursive=True)
                logger.info(f"Watching: {path}")

        self._observer.start()
        self._handlers[collection_id] = handler

    def stop(self, collection_id: str | None = None) -> None:
        """Stop watching.

        Args:
            collection_id: Collection to stop watching (None for all)
        """
        if collection_id and collection_id in self._handlers:
            del self._handlers[collection_id]

        if not collection_id or not self._handlers:
            if self._observer:
                self._observer.stop()
                self._observer.join()
                self._observer = None

            logger.info("File watcher stopped")

    def is_watching(self, collection_id: str) -> bool:
        """Check if a collection is being watched.

        Args:
            collection_id: Collection ID

        Returns:
            True if collection is being watched
        """
        return collection_id in self._handlers
