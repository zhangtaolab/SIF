"""Document indexer for orchestrating the indexing process."""

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from sif.core.models import Collection, Document, DocumentChunk
from sif.database.repositories import DocumentRepository
from sif.embedding.manager import EmbeddingManager
from sif.indexing.chunker import Chunker
from sif.indexing.parser import MarkdownParser
from sif.indexing.scanner import FileScanner
from sif.utils.logging import get_logger
from sif.utils.progress import ProgressTracker, RichProgressTracker

logger = get_logger(__name__)


class IndexStatus(Enum):
    """Status of indexing operation."""

    PENDING = auto()
    INDEXING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()


@dataclass
class IndexResult:
    """Result of indexing operation."""

    files_processed: int
    files_added: int
    files_updated: int
    files_skipped: int
    files_failed: int
    chunks_created: int
    errors: list[str]


class DocumentIndexer:
    """Orchestrates the document indexing process.

    Coordinates file scanning, parsing, chunking, embedding generation,
    and database storage for document indexing.
    """

    def __init__(
        self,
        scanner: FileScanner,
        parser: MarkdownParser,
        chunker: Chunker,
        embedding_manager: EmbeddingManager,
        repository: DocumentRepository,
        progress_tracker: ProgressTracker | None = None,
    ) -> None:
        """Initialize document indexer.

        Args:
            scanner: File scanner
            parser: Markdown parser
            chunker: Document chunker
            embedding_manager: Embedding manager
            repository: Document repository
            progress_tracker: Progress tracker
        """
        self._scanner = scanner
        self._parser = parser
        self._chunker = chunker
        self._embedding_manager = embedding_manager
        self._repository = repository
        self._progress = progress_tracker or RichProgressTracker()

    def index_collection(self, collection: Collection) -> IndexResult:
        """Index all documents in a collection.

        Args:
            collection: Collection to index

        Returns:
            Indexing result
        """
        logger.info(f"Indexing collection: {collection.name}")

        # Scan for files
        scan_result = self._scanner.scan(
            Path(collection.path),
            pattern=collection.pattern,
            ignore_patterns=collection.ignore_patterns,
        )

        logger.info(f"Found {scan_result.file_count} files to index")

        # Index files
        self._progress.start("Indexing documents", total=scan_result.file_count)

        result = IndexResult(
            files_processed=0,
            files_added=0,
            files_updated=0,
            files_skipped=0,
            files_failed=0,
            chunks_created=0,
            errors=[],
        )

        for file_path in scan_result.files:
            try:
                file_result = self._index_file(file_path, collection.id)

                result.files_processed += 1
                if file_result == IndexStatus.ADDED:
                    result.files_added += 1
                elif file_result == IndexStatus.COMPLETED:
                    result.files_updated += 1
                elif file_result == IndexStatus.SKIPPED:
                    result.files_skipped += 1

                self._progress.update()

            except Exception as e:
                logger.error(f"Error indexing {file_path}: {e}")
                result.files_failed += 1
                result.errors.append(f"{file_path}: {str(e)}")

        self._progress.finish()

        # Update collection stats
        collection.document_count = self._repository.list_by_collection(collection.id).__len__()
        collection.mark_indexed()

        logger.info(
            f"Indexing complete: {result.files_added} added, "
            f"{result.files_updated} updated, {result.files_failed} failed"
        )

        return result

    def _index_file(
        self,
        file_path: Path,
        collection_id: str,
    ) -> IndexStatus:
        """Index a single file.

        Args:
            file_path: Path to file
            collection_id: Collection ID

        Returns:
            Index status
        """
        import hashlib
        import uuid

        # Calculate checksum
        with open(file_path, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()

        # Check if file already indexed
        existing = self._repository.get_by_path(str(file_path), collection_id)
        if existing:
            if existing.checksum == checksum:
                logger.debug(f"File unchanged, skipping: {file_path}")
                return IndexStatus.SKIPPED

        # Parse file
        parse_result = self._parser.parse(file_path)

        # Create document
        document = Document(
            id=str(uuid.uuid4()) if not existing else existing.id,
            collection_id=collection_id,
            path=str(file_path),
            content=parse_result.content,
            title=parse_result.title or file_path.name,
            checksum=checksum,
            file_size=file_path.stat().st_size,
            mtime=file_path.stat().st_mtime,
            metadata=parse_result.metadata,
        )

        # Chunk document
        chunks = self._chunker.chunk(parse_result.content)

        # Generate embeddings for chunks
        if chunks:
            chunk_texts = [c.content for c in chunks]
            embedding_response = self._embedding_manager.embed(chunk_texts)

            # Create document chunks with embeddings
            for i, (chunk, embedding) in enumerate(zip(chunks, embedding_response.embeddings)):
                doc_chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=document.id,
                    content=chunk.content,
                    start_pos=chunk.start_pos,
                    end_pos=chunk.end_pos,
                    token_count=chunk.token_count,
                    embedding=embedding,
                )
                document.add_chunk(doc_chunk)

        # Save to repository
        if existing:
            self._repository.update(document)
            return IndexStatus.COMPLETED
        else:
            self._repository.create(document)
            return IndexStatus.ADDED

    def reindex_collection(self, collection: Collection) -> IndexResult:
        """Reindex all documents in a collection.

        Args:
            collection: Collection to reindex

        Returns:
            Indexing result
        """
        # Clear existing documents
        self._repository.delete_by_collection(collection.id)

        # Reindex
        return self.index_collection(collection)
