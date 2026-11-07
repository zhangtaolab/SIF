"""Golden equivalence proof for the extracted incremental core (SC3).

``update_cmd`` now delegates to :class:`sif.indexing.incremental.IncrementalIndexer`
with per-file BEGIN IMMEDIATE transactions (D-04). This test pins the golden
expectation: identical index state (documents, chunks, FTS external-content
sync) and identical CLI counts across add / modify / delete / idempotent
re-run cycles through the extracted core.

Assertions are made on query results through fresh connections only — never on
``-wal``/``-shm`` file listings (research Pitfall 5).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from sif.cli.commands.index import update_cmd
from sif.config.settings import Settings
from sif.core.models import Collection, DocumentChunk
from sif.database.database import Database
from sif.database.repositories import CollectionRepository, DocumentChunkRepository


ALPHA_BODY = "# Alpha Heading\n\n" + ("Alpha body text with keywords. " * 30)
BETA_BODY = "# Beta Heading\n\n" + ("Beta nested body prose. " * 30)
GAMMA_BODY = "# Gamma Ünïcode 标题\n\n" + ("Unicode body — em-dash, 中文, emoji 🎯. " * 30)
DELTA_BODY = "# Delta Heading\n\n" + ("Delta fresh body text. " * 30)
APPENDED = "\n\nAppended line for the second run."


def _delenv_settings_vars(monkeypatch) -> None:
    """Keep Settings construction hermetic against a developer shell."""
    for var in ("SIF_EMBEDDING_DIM", "SIF_MODEL_TYPE", "SIF_MODEL_NAME"):
        monkeypatch.delenv(var, raising=False)


def _test_settings() -> Settings:
    """Build hermetic test settings."""
    return Settings(embedding_dim=8, model_name="test", cache_embeddings=False)


def _build_fixture_tree(root: Path) -> None:
    """Create 3 markdown files (one nested, one unicode) plus one ignored file."""
    (root / "sub").mkdir()
    (root / "alpha.md").write_text(ALPHA_BODY, encoding="utf-8")
    (root / "sub" / "beta.md").write_text(BETA_BODY, encoding="utf-8")
    (root / "gamma_unicode.md").write_text(GAMMA_BODY, encoding="utf-8")
    # Non-matching extension: must be invisible to the collection's *.md pattern.
    (root / "ignored-notes.txt").write_text("Alpha body text with keywords.", encoding="utf-8")


def _seed_collection(db_path: Path, settings: Settings, root: Path) -> None:
    """Init schema and create one collection pointing at the fixture tree."""
    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=settings):
        db.init_schema()
        with db.connection:
            CollectionRepository(db.connection).create(Collection(name="notes", path=str(root)))
    db.close()


def _invoke_update(db_path: Path, settings: Settings, args: list[str] | None = None) -> object:
    """Invoke update_cmd through CliRunner against the real database."""
    runner = CliRunner()
    with patch("sif.config.settings.get_settings", return_value=settings):
        return runner.invoke(update_cmd, args or [], obj={"index_path": db_path})


def _simulate_embed_pass(db_path: Path) -> None:
    """Give every live document exactly two deterministic chunks (embed stand-in).

    ``update`` itself is BM25-only (D-05): chunks arrive from ``embed``. The
    golden cycle models the real workflow — update, embed, mutate, update — so
    chunk purge/drop behavior is proven against real chunk rows.
    """
    db = Database(db_path)
    try:
        with db.connection:
            doc_rows = db.connection.execute(
                "SELECT id, title, content FROM documents ORDER BY path"
            ).fetchall()
            chunk_repo = DocumentChunkRepository(db.connection)
            for row in doc_rows:
                doc_id, title, content = row["id"], row["title"], row["content"]
                if chunk_repo.get_by_document(doc_id):
                    continue
                midpoint = len(content) // 2
                chunk_repo.create(
                    DocumentChunk(
                        content=content[:midpoint],
                        sequence=0,
                        start_pos=0,
                        end_pos=midpoint,
                        document_id=doc_id,
                    )
                )
                chunk_repo.create(
                    DocumentChunk(
                        content=f"part two of {title}",
                        sequence=1,
                        start_pos=midpoint,
                        end_pos=len(content),
                        document_id=doc_id,
                    )
                )
    finally:
        db.close()


class _Snapshot:
    """Index state read through a fresh connection after the runner exits."""

    def __init__(self, db_path: Path) -> None:
        conn = sqlite3.connect(str(db_path))
        try:
            self.documents: dict[str, dict[str, str]] = {
                row[0]: {"title": row[1], "checksum": row[2], "content": row[3]}
                for row in conn.execute("SELECT path, title, checksum, content FROM documents")
            }
            self.fts_count: int = conn.execute("SELECT COUNT(*) FROM documents_fts").fetchone()[0]
            self.fts_match_counts = {
                token: conn.execute(
                    "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH ?",
                    (token,),
                ).fetchone()[0]
                for token in ("alpha", "nested", "unicode", "appended", "delta")
            }
            self.chunks_by_path: dict[str, list[int]] = {
                row[0]: ([int(seq) for seq in (row[1] or "").split(",") if seq != ""])
                for row in conn.execute(
                    "SELECT d.path, GROUP_CONCAT(dc.sequence, ',') "
                    "FROM documents d LEFT JOIN document_chunks dc ON dc.document_id = d.id "
                    "GROUP BY d.path ORDER BY d.path"
                )
            }
        finally:
            conn.close()

    def chunk_sequences_are_contiguous(self) -> bool:
        """Every document's chunk sequences are 0..n-1 with no gaps."""
        return all(seqs == list(range(len(seqs))) for seqs in self.chunks_by_path.values())


class TestIncrementalEquivalence:
    """SC3: identical index state and CLI counts through the extracted core."""

    def _advance_to_after_first_run(
        self,
        tmp_path: Path,
    ) -> tuple[Path, Path, Settings, _Snapshot]:
        """Build the fixture, index it once, embed, snapshot; return state."""
        db_path = tmp_path / "golden.db"
        root = tmp_path / "notes"
        root.mkdir()
        settings = _test_settings()
        _build_fixture_tree(root)
        _seed_collection(db_path, settings, root)
        assert _invoke_update(db_path, settings).exit_code == 0
        _simulate_embed_pass(db_path)
        return db_path, root, settings, _Snapshot(db_path)

    def _mutate_tree(self, root: Path) -> None:
        """Apply the run-2 mutations: append to alpha, delete beta, add delta."""
        (root / "alpha.md").write_text(ALPHA_BODY + APPENDED, encoding="utf-8")
        (root / "sub" / "beta.md").unlink()
        (root / "delta.md").write_text(DELTA_BODY, encoding="utf-8")

    def test_first_run_indexes_fixture_tree(self, tmp_path: Path, monkeypatch) -> None:
        """Run 1: Added: 3 / Updated: 0 / Removed: 0 with FTS 1:1 and chunked docs."""
        _delenv_settings_vars(monkeypatch)
        _db_path, root, _settings, snap1 = self._advance_to_after_first_run(tmp_path)

        alpha_path = str(root / "alpha.md")
        beta_path = str(root / "sub" / "beta.md")
        gamma_path = str(root / "gamma_unicode.md")
        assert set(snap1.documents) == {alpha_path, beta_path, gamma_path}
        # The non-matching .txt file never entered the index.
        assert "ignored-notes.txt" not in " ".join(snap1.documents)
        # External-content FTS stays 1:1 with documents through the per-file
        # transactions, and each content body is searchable.
        assert snap1.fts_count == len(snap1.documents) == 3
        assert snap1.fts_match_counts["alpha"] == 1
        assert snap1.fts_match_counts["nested"] == 1
        assert snap1.fts_match_counts["unicode"] == 1
        # Unicode body stored intact (title, content, checksum coherent).
        assert snap1.documents[gamma_path]["title"] == "Gamma Ünïcode 标题"
        assert "中文" in snap1.documents[gamma_path]["content"]
        # The embed stand-in gave every document a contiguous chunk set.
        assert sorted(snap1.chunks_by_path.values(), key=len) == [[0, 1]] * 3
        assert snap1.chunk_sequences_are_contiguous()

    def test_mutation_run_tracks_modify_delete_and_add(self, tmp_path: Path, monkeypatch) -> None:
        """Run 2: Added: 1 / Updated: 1 / Removed: 1 with FTS trigger proofs."""
        _delenv_settings_vars(monkeypatch)
        db_path, root, settings, snap1 = self._advance_to_after_first_run(tmp_path)
        self._mutate_tree(root)

        result2 = _invoke_update(db_path, settings)
        assert result2.exit_code == 0
        assert "Added: 1" in result2.output
        assert "Updated: 1" in result2.output
        assert "Removed: 1" in result2.output

        snap2 = _Snapshot(db_path)
        alpha_path = str(root / "alpha.md")
        beta_path = str(root / "sub" / "beta.md")
        gamma_path = str(root / "gamma_unicode.md")
        delta_path = str(root / "delta.md")
        assert set(snap2.documents) == {alpha_path, gamma_path, delta_path}
        # The modified document's checksum and content both moved forward...
        assert snap2.documents[alpha_path]["checksum"] != snap1.documents[alpha_path]["checksum"]
        assert "Appended line" in snap2.documents[alpha_path]["content"]
        # ...and the FTS update trigger served the new text inside the
        # per-file transaction.
        assert snap2.fts_match_counts["appended"] == 1
        # The deleted document is gone from BOTH documents and documents_fts
        # (external-content delete trigger fired inside the sweep transaction).
        assert beta_path not in snap2.documents
        assert snap2.fts_count == len(snap2.documents) == 3
        assert snap2.fts_match_counts["nested"] == 0
        # Stale chunks of the modified document were purged (CR-01); the
        # deleted document's chunks went with it; untouched documents keep
        # theirs.
        assert snap2.chunks_by_path[alpha_path] == []
        assert snap2.chunks_by_path[gamma_path] == [0, 1]
        assert beta_path not in snap2.chunks_by_path
        assert snap2.chunks_by_path[delta_path] == []

        # The embed pass after the mutation converges every live document —
        # including the new one — to a full, contiguous chunk set.
        _simulate_embed_pass(db_path)
        snap2_chunked = _Snapshot(db_path)
        for path in (alpha_path, gamma_path, delta_path):
            assert snap2_chunked.chunks_by_path[path] == [0, 1]
        assert snap2_chunked.chunk_sequences_are_contiguous()

    def test_third_run_is_idempotent(self, tmp_path: Path, monkeypatch) -> None:
        """Run 3: nothing changed on disk — all zeros, no state disturbed (SC2)."""
        _delenv_settings_vars(monkeypatch)
        db_path, _root, settings, _snap1 = self._advance_to_after_first_run(tmp_path)
        self._mutate_tree(_root)
        assert _invoke_update(db_path, settings).exit_code == 0
        _simulate_embed_pass(db_path)
        snap2_chunked = _Snapshot(db_path)

        result3 = _invoke_update(db_path, settings)
        assert result3.exit_code == 0
        assert "Added: 0" in result3.output
        assert "Updated: 0" in result3.output
        assert "Removed: 0" in result3.output

        snap3 = _Snapshot(db_path)
        assert snap3.documents == snap2_chunked.documents
        assert snap3.fts_count == 3
        # The no-op run destroyed no chunks/embeddings state (SC2 no-duplication).
        assert snap3.chunks_by_path == snap2_chunked.chunks_by_path
