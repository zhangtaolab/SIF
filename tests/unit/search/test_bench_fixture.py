"""Contract and integrity tests for the committed bench fixture pack."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sif.core.models import SearchOptions
from sif.search.benchmark import (
    CATEGORIES,
    GRADE_MAX,
    SPLITS,
    SearchEvaluator,
    resolve_corpus_root,
    result_key,
)
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


class TestCommittedPackEndToEnd:
    def test_committed_pack_end_to_end_report_nonzero_ndcg(self) -> None:
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

            assert report.num_queries == len(fixture["queries"])
            for category in ("keyword", "synonym", "multilingual", "rival"):
                assert report.categories[category].count > 0, category
            assert report.ndcg_at_10 > 0.0
            assert report.hit_at_10 > 0.0
        finally:
            conn.close()

    def test_committed_pack_end_to_end_results_keyed_by_corpus_relative_path(self) -> None:
        """Path-keyed join: relevance keys and result keys resolve against the
        same corpus root derived from the fixture's declared corpus_root."""
        fixture = load_fixture_queries(FIXTURE_PATH)
        first = fixture["queries"][0]
        grade3_key = next(key for key, grade in first["relevance"].items() if grade == 3)
        conn = build_bench_db(CORPUS_ROOT, ConceptEmbedder())
        try:
            pipeline = SearchPipeline(
                conn,
                embedder=ConceptEmbedder(),
                embedding_dim=EMBEDDING_DIM,
            )
            options = SearchOptions(limit=10, include_content=False, include_highlights=False)

            results = pipeline.search(first["query"], options)
            corpus_root = SearchEvaluator(fixture, fixture_path=FIXTURE_PATH).corpus_root
            assert corpus_root is not None

            keys = [result_key(r, "path", corpus_root) for r in results]

            assert keys[0] == grade3_key
        finally:
            conn.close()


class TestFixtureContractCounts:
    def test_contract_counts_56_queries_36_tuning_20_heldout(self) -> None:
        """D-03: >=50 queries, >=20 held-out, tuning is the remainder."""
        queries = load_fixture_queries(FIXTURE_PATH)["queries"]

        total = len(queries)
        heldout = sum(1 for q in queries if q["split"] == "heldout")
        tuning = sum(1 for q in queries if q["split"] == "tuning")

        assert total >= 50
        assert heldout >= 20
        assert tuning == total - heldout
        assert (total, tuning, heldout) == (56, 36, 20)

    def test_contract_evaluator_loads_every_query_without_drops(self) -> None:
        """No query is silently dropped by SearchEvaluator's parsing."""
        fixture = load_fixture_queries(FIXTURE_PATH)

        evaluator = SearchEvaluator(fixture, fixture_path=FIXTURE_PATH)

        assert len(evaluator.query_items) == len(fixture["queries"])


class TestFixtureContractSplitsAndCategories:
    def test_contract_every_query_carries_exactly_one_valid_split(self) -> None:
        queries = load_fixture_queries(FIXTURE_PATH)["queries"]

        for q in queries:
            assert q["split"] in SPLITS, q

    def test_contract_every_category_appears(self) -> None:
        queries = load_fixture_queries(FIXTURE_PATH)["queries"]
        seen = {q["category"] for q in queries}

        for category in CATEGORIES:
            assert category in seen, category

    def test_contract_every_category_has_heldout_coverage(self) -> None:
        """A category losing held-out coverage would blind EVAL-04 for it."""
        queries = load_fixture_queries(FIXTURE_PATH)["queries"]

        for category in CATEGORIES:
            heldout = [q for q in queries if q["category"] == category and q["split"] == "heldout"]
            assert heldout, f"category {category} has no held-out queries"


class TestFixtureContractGrades:
    def test_contract_grades_are_ints_in_range_with_3_and_2_per_query(self) -> None:
        queries = load_fixture_queries(FIXTURE_PATH)["queries"]

        for q in queries:
            grades = q["relevance"]
            assert grades, q["query"]
            for key, grade in grades.items():
                assert isinstance(grade, int), (q["query"], key)
                assert not isinstance(grade, bool), (q["query"], key)
                assert 0 <= grade <= GRADE_MAX, (q["query"], key, grade)
            assert 3 in grades.values(), q["query"]
            assert 2 in grades.values(), q["query"]

    def test_contract_relevance_maps_capped_at_five_entries(self) -> None:
        queries = load_fixture_queries(FIXTURE_PATH)["queries"]

        for q in queries:
            assert len(q["relevance"]) <= 5, q["query"]

    def test_contract_rival_queries_carry_a_zero_neighbor(self) -> None:
        queries = load_fixture_queries(FIXTURE_PATH)["queries"]

        for q in queries:
            if q["category"] == "rival":
                assert 0 in q["relevance"].values(), q["query"]


class TestFixtureContractPaths:
    def test_contract_keys_are_relative_posix_paths(self) -> None:
        """No absolute keys, no '..' segments (T-16-05)."""
        queries = load_fixture_queries(FIXTURE_PATH)["queries"]

        for q in queries:
            for key in q["relevance"]:
                assert not key.startswith("/"), key
                assert "\\" not in key, key
                assert ".." not in Path(key).parts, key

    def test_contract_keys_resolve_under_the_declared_root_and_name_files(self) -> None:
        """resolve_corpus_root (never fixture_path.parent alone) is the single
        root rule; every key stays inside it and names a committed corpus file."""
        fixture = load_fixture_queries(FIXTURE_PATH)

        root = resolve_corpus_root(fixture, FIXTURE_PATH)

        assert root == CORPUS_ROOT.resolve()
        for q in fixture["queries"]:
            for key in q["relevance"]:
                resolved = (root / key).resolve()
                assert resolved.is_relative_to(root), key  # never escapes the root
                assert resolved.is_file(), key  # names a committed corpus file


class TestFixtureRetrievalIntegrity:
    def test_retrieval_every_query_returns_at_least_one_result(self) -> None:
        """On the deterministic in-memory index every fixture query retrieves
        at least one result — including the multilingual category, whose CJK
        terms are exact contiguous runs under the porter tokenizer."""
        fixture = load_fixture_queries(FIXTURE_PATH)
        conn = build_bench_db(CORPUS_ROOT, ConceptEmbedder())
        try:
            pipeline = SearchPipeline(
                conn,
                embedder=ConceptEmbedder(),
                embedding_dim=EMBEDDING_DIM,
            )
            options = SearchOptions(limit=10, include_content=False, include_highlights=False)

            for q in fixture["queries"]:
                results = pipeline.search(q["query"], options)
                assert results, q["query"]
        finally:
            conn.close()

    def test_retrieval_multilingual_queries_return_results(self) -> None:
        """Explicit multilingual assertion (CJK/FTS porter constraint): the
        Chinese runs are exact contiguous tokens present in the documents."""
        fixture = load_fixture_queries(FIXTURE_PATH)
        conn = build_bench_db(CORPUS_ROOT, ConceptEmbedder())
        try:
            pipeline = SearchPipeline(
                conn,
                embedder=ConceptEmbedder(),
                embedding_dim=EMBEDDING_DIM,
            )
            options = SearchOptions(limit=10, include_content=False, include_highlights=False)

            multilingual = [q for q in fixture["queries"] if q["category"] == "multilingual"]
            assert multilingual
            for q in multilingual:
                assert pipeline.search(q["query"], options), q["query"]
        finally:
            conn.close()


class TestFixtureSplitNonInterference:
    def test_split_query_sets_are_disjoint_and_exhaustive(self) -> None:
        """A tuning query never contributes to held-out metrics and vice
        versa: the two split sets partition the full query set."""
        queries = load_fixture_queries(FIXTURE_PATH)["queries"]
        tuning = {q["query"] for q in queries if q["split"] == "tuning"}
        heldout = {q["query"] for q in queries if q["split"] == "heldout"}
        everything = {q["query"] for q in queries}

        assert tuning & heldout == set()
        assert tuning | heldout == everything
