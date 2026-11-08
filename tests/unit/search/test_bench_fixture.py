"""Contract and integrity tests for the committed bench fixture pack."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sif.core.models import SearchOptions
from sif.search.benchmark import SearchEvaluator, result_key
from sif.search.hybrid import SearchPipeline
from tests.support.bench import (
    EMBEDDING_DIM,
    ConceptEmbedder,
    build_bench_db,
    load_fixture_queries,
)


PACK_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "bench"
FIXTURE_PATH = PACK_ROOT / "queries.json"
CORPUS_ROOT = PACK_ROOT / "corpus"


class TestConceptEmbedder:
    def test_embedder_embed_returns_dimension_length_vector(self) -> None:
        embedder = ConceptEmbedder()

        vec = embedder.embed("zephyr telemetry cascade")

        assert isinstance(vec, list)
        assert len(vec) == EMBEDDING_DIM
        assert all(isinstance(v, float) for v in vec)

    def test_embedder_is_deterministic_across_instances(self) -> None:
        first = ConceptEmbedder().embed("机器学习 fundamentals")
        second = ConceptEmbedder().embed("机器学习 fundamentals")

        assert first == second

    def test_embedder_repeat_calls_return_cached_identical_vector(self) -> None:
        embedder = ConceptEmbedder()

        assert embedder.embed("flux capacitor") == embedder.embed("flux capacitor")

    def test_embedder_embed_batch_returns_one_vector_per_text(self) -> None:
        embedder = ConceptEmbedder()

        vectors = embedder.embed_batch(["alpha", "beta gamma", ""])

        assert len(vectors) == 3
        assert all(len(v) == EMBEDDING_DIM for v in vectors)

    def test_embedder_dimension_property_is_stable(self) -> None:
        embedder = ConceptEmbedder()

        assert embedder.dimension == EMBEDDING_DIM
        assert embedder.dimension == len(embedder.embed("any text"))

    def test_embedder_unit_norm(self) -> None:
        vec = ConceptEmbedder().embed("velocity tuning handbook")

        assert abs(sum(v * v for v in vec) - 1.0) < 1e-9


class TestBuildBenchDb:
    def test_build_creates_collection_documents_fts_and_vec0_rows(self) -> None:
        md_count = sum(1 for _ in CORPUS_ROOT.rglob("*.md"))
        assert md_count >= 4  # one doc per category directory in the pack

        conn = build_bench_db(CORPUS_ROOT, ConceptEmbedder())
        try:
            collections = conn.execute("SELECT id, name, path FROM collections").fetchall()
            assert len(collections) == 1
            assert collections[0]["id"] == "bench"
            assert collections[0]["path"] == str(CORPUS_ROOT.resolve())

            docs = conn.execute("SELECT id FROM documents ORDER BY id").fetchall()
            assert [d["id"] for d in docs] == [f"doc-{i:03d}" for i in range(md_count)]

            # FTS rows arrive through the SchemaManager insert triggers.
            for table in ("documents_fts", "chunks_fts"):
                count = conn.execute(f"SELECT count(*) AS c FROM {table}").fetchone()["c"]
                assert count == md_count, table
            chunks = conn.execute("SELECT count(*) AS c FROM document_chunks").fetchone()["c"]
            assert chunks == md_count

            embeddings = conn.execute("SELECT count(*) AS c FROM document_embeddings").fetchone()[
                "c"
            ]
            assert embeddings == md_count
        finally:
            conn.close()

    def test_build_documents_carry_paths_under_the_corpus_root(self) -> None:
        conn = build_bench_db(CORPUS_ROOT, ConceptEmbedder())
        try:
            root = CORPUS_ROOT.resolve()
            for row in conn.execute("SELECT path FROM documents"):
                assert Path(row["path"]).resolve().is_relative_to(root)
        finally:
            conn.close()

    def test_build_db_connection_is_plain_sqlite(self) -> None:
        conn = build_bench_db(CORPUS_ROOT, ConceptEmbedder())
        try:
            assert isinstance(conn, sqlite3.Connection)
            assert isinstance(conn.row_factory, type(sqlite3.Row))
        finally:
            conn.close()


class TestMinimalPackEndToEnd:
    def test_minimal_pack_end_to_end_report_nonzero_ndcg(self) -> None:
        fixture = load_fixture_queries(FIXTURE_PATH)
        conn = build_bench_db(CORPUS_ROOT, ConceptEmbedder())
        try:
            pipeline = SearchPipeline(
                conn,
                embedder=ConceptEmbedder(),
                embedding_dim=EMBEDDING_DIM,
            )
            options = SearchOptions(limit=10, include_content=False, include_highlights=False)
            evaluator = SearchEvaluator(fixture, fixture_path=FIXTURE_PATH)

            report = evaluator.report(lambda query: pipeline.search(query, options))

            assert report.num_queries == 2
            assert report.categories["keyword"].count == 1
            assert report.categories["multilingual"].count == 1
            assert report.ndcg_at_10 > 0.0
            assert report.hit_at_10 > 0.0
        finally:
            conn.close()

    def test_minimal_pack_end_to_end_results_keyed_by_corpus_relative_path(self) -> None:
        """Path-keyed join: relevance keys and result keys resolve against the
        same corpus root derived from the fixture's declared corpus_root."""
        conn = build_bench_db(CORPUS_ROOT, ConceptEmbedder())
        try:
            pipeline = SearchPipeline(
                conn,
                embedder=ConceptEmbedder(),
                embedding_dim=EMBEDDING_DIM,
            )
            options = SearchOptions(limit=10, include_content=False, include_highlights=False)

            results = pipeline.search("zephyr telemetry", options)
            corpus_root = SearchEvaluator(
                load_fixture_queries(FIXTURE_PATH),
                fixture_path=FIXTURE_PATH,
            ).corpus_root
            assert corpus_root is not None

            keys = [result_key(r, "path", corpus_root) for r in results]

            assert keys[0] == "keyword/alpha.md"
        finally:
            conn.close()
