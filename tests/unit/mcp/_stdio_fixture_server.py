"""Cold-first-query stdio fixture server (Phase 22 D-16/T-22-20).

Run as ``python -m tests.unit.mcp._stdio_fixture_server <db_path>``. The
process seeds a temporary index and monkeypatches the lazy embedder loader so
the first ``query`` "loads" a hermetic ``ConceptEmbedder`` while deliberately
printing a progress-bar-like line to stdout. The SDK stdio transport must
divert that write to stderr, leaving the protocol channel JSON-RPC only.

The stub also borrows the settings-derived identity so the loaded dimension
matches the schema width (32) and the query is a normal successful page.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from sif.config.settings import get_settings
from sif.database.database import Database
from sif.embedding.identity import EmbedderIdentity, build_settings_identity
from sif.embedding.prompts import resolve_prompt_scheme
from sif.mcp import backend as backend_module
from tests.support.bench import ConceptEmbedder


def _settings_identity() -> EmbedderIdentity:
    """The same settings-only identity the backend writes at schema open."""
    settings = get_settings()
    scheme = resolve_prompt_scheme(
        settings.model_name,
        settings.model_type,
        settings.query_prompt_name,
        settings.document_prompt_name,
    )
    return build_settings_identity(settings, scheme)


class _NoisyStubManager:
    """Manager double whose load writes progress text to stdout on purpose."""

    def __init__(self) -> None:
        self._embedder = ConceptEmbedder()
        self._identity = _settings_identity()

    @property
    def model(self) -> ConceptEmbedder:
        return self._embedder

    def load_model(self) -> None:
        print("Loading model weights: 10%|##        | 1/10", flush=True)

    def get_identity(self) -> EmbedderIdentity:
        return self._identity

    def embed_query(self, text: str) -> list[float]:
        return self._embedder.embed(text)

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return [self._embedder.embed(text) for text in texts]


def _seed(db_path: str) -> None:
    """Create the schema and one searchable document."""
    db = Database(db_path)
    try:
        db.init_schema(embedding_dim=32)
        now = datetime.now(timezone.utc).isoformat()
        with db.connection:
            db.connection.execute(
                "INSERT INTO collections (id, name, path, created_at, updated_at)"
                " VALUES ('c1', 'notes', '/vault', ?, ?)",
                (now, now),
            )
            db.connection.execute(
                "INSERT INTO documents (id, collection_id, path, filename, title,"
                " content, checksum, mtime, created_at, updated_at)"
                " VALUES ('d1', 'c1', '/vault/seed.md', 'seed.md', 'Seed',"
                " 'seed paragraph quantum machine', 'ck-1', 1.0, ?, ?)",
                (now, now),
            )
    finally:
        db.close()


def main() -> None:
    db_path = sys.argv[1]
    _seed(db_path)
    # The lazy loader is the single seam every vector-touching route uses.
    backend_module.EmbeddingManager.from_settings = (  # type: ignore[method-assign]
        lambda _settings: _NoisyStubManager()
    )
    # Drive the real CLI entrypoint (including its pre-run docsift migration
    # notice) so the test exercises the production stdio composition path.
    sys.argv = ["sif", "--index", db_path, "mcp", "stdio"]
    from sif.cli.main import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
