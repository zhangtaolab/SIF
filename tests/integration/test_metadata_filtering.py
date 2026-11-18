"""Phase 20 integration battery: the filtered pipeline on a real schema.

Every document is inserted through ``DocumentRepository`` so the typed kv
rows are written by the production path (research Pitfall 10), and the search
runs against a real ``SchemaManager`` schema with FTS triggers and vec0 KNN.
The corpus is generated: ~2 % of the documents carry ``tag: rare`` and are
deliberately farthest from the query embedding, which is exactly the shape
the post-JOIN saturation bug under-returned (research Pitfall 1/13).

``pytest.skip`` is raised inside the corpus builder, never at module scope, so
a repository-level discovery test that does not need sqlite-vec can still run
on a host without the extension.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest

from sif.core.filters import parse_filter
from sif.core.models import Document, SearchOptions
from sif.database.metadata_repository import MetadataValueRepository
from sif.database.repositories import DocumentRepository
from sif.database.schema import SchemaManager
from sif.search.bm25 import BM25Searcher
from sif.search.filters import count_matching_documents
from sif.search.hybrid import HybridSearcher, SearchPipeline
from sif.search.vector import VectorSearcher
from tests.support.bench import EMBEDDING_DIM, ConceptEmbedder


C1 = "c1"
C2 = "c2"
NOW = "2026-11-15T00:00:00+00:00"
DOCUMENT_COUNT = 200
RARE_INDEXES = frozenset({180, 182, 184, 186})
NESTED_INDEX = 5
INT_PRIORITY_INDEX = 1
FLOAT_PRIORITY_INDEX = 2
OTHER_PRIORITY_INDEX = 3
BASE_MTIME = 1_700_000_000.0


def _metadata_for(index: int) -> dict[str, Any]:
    """Tag every document; add numeric priorities, one nested key."""
    metadata: dict[str, Any] = {"tag": "rare" if index in RARE_INDEXES else "common"}
    if index == INT_PRIORITY_INDEX:
        metadata["priority"] = 10  # JSON int -> number
    elif index == FLOAT_PRIORITY_INDEX:
        metadata["priority"] = 10.0  # JSON float -> number, same value
    elif index == OTHER_PRIORITY_INDEX:
        metadata["priority"] = 20
    elif index >= 150:
        metadata["priority"] = index
    if index == NESTED_INDEX:
        metadata["nested"] = {"a": 1}  # D-07: skipped per key, never indexed
    return metadata


def _content_for(index: int) -> str:
    """Common docs are alpha-heavy; rare docs are lexically distinctive and far."""
    if index in RARE_INDEXES:
        return f"alpha rare note {index} unique{index} extra"
    return "alpha " * 5 + f"common note {index}"


def _doc_index(document_id: str) -> int:
    """Corpus indexes are embedded in the deterministic document ids."""
    return int(document_id[1:])


def _build_corpus() -> sqlite3.Connection:
    """200 documents over two collections, one chunk + vec0 row each."""
    import sqlite_vec

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception:
        conn.close()
        pytest.skip("sqlite-vec not available")

    SchemaManager(conn, embedding_dim=EMBEDDING_DIM).create_all()
    conn.execute(
        "INSERT INTO collections (id, name, path, include_by_default, created_at, updated_at)"
        " VALUES ('c1', 'notes', '/notes', 1, ?, ?)",
        (NOW, NOW),
    )
    conn.execute(
        "INSERT INTO collections (id, name, path, include_by_default, created_at, updated_at)"
        " VALUES ('c2', 'archive', '/archive', 1, ?, ?)",
        (NOW, NOW),
    )

    embedder = ConceptEmbedder()
    documents = DocumentRepository(conn)
    embeddings: list[tuple[str, str, str, list[float]]] = []
    for index in range(DOCUMENT_COUNT):
        collection = C2 if index >= 190 else C1
        content = _content_for(index)
        document = Document(
            id=f"d{index}",
            collection_id=collection,
            path=f"/notes/doc-{index:03d}.md",
            content=content,
            title=f"Doc {index}",
            mtime=BASE_MTIME + index,
            metadata=_metadata_for(index),
        )
        documents.create(document)
        chunk_id = f"chunk-{index}"
        conn.execute(
            "INSERT INTO document_chunks (id, document_id, sequence, content, created_at)"
            " VALUES (?, ?, 0, ?, ?)",
            (chunk_id, document.id, content, NOW),
        )
        embeddings.append((f"e{index}", document.id, chunk_id, embedder.embed(content)))
    VectorSearcher(conn, embedding_dim=EMBEDDING_DIM).add_embeddings_batch(embeddings)
    conn.commit()
    return conn


@pytest.fixture(scope="module")
def search_db() -> Iterator[sqlite3.Connection]:
    """One generated corpus for the whole battery; skips without sqlite-vec."""
    conn = _build_corpus()
    try:
        yield conn
    finally:
        conn.close()


DISCOVERY_COUNT = 12


def _discovery_metadata(index: int) -> dict[str, Any]:
    """A small corpus with rare tags, numeric cohorts, and one nested key."""
    metadata: dict[str, Any] = {"tag": "rare" if index < 2 else "common"}
    if index == 1:
        metadata["priority"] = 10
    elif index == 2:
        metadata["priority"] = 20
    elif index >= 8:
        metadata["priority"] = index
    if index == NESTED_INDEX:
        metadata["nested"] = {"a": 1}  # D-07: skipped per key, never indexed
        metadata["nested_owner"] = "yes"
    return metadata


def _build_discovery_corpus() -> sqlite3.Connection:
    """Repository-built corpus for discovery parity, no sqlite-vec required.

    Discovery reads only ``documents`` and the typed kv tables, so this
    fixture deliberately skips the FTS/vec0 construction ``search_db`` needs.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    manager = SchemaManager(conn)
    manager._create_collections_table()
    manager._create_documents_table()
    manager._create_metadata_tables()
    conn.execute(
        "INSERT INTO collections (id, name, path, include_by_default, created_at, updated_at)"
        " VALUES ('c1', 'notes', '/notes', 1, ?, ?)",
        (NOW, NOW),
    )
    conn.execute(
        "INSERT INTO collections (id, name, path, include_by_default, created_at, updated_at)"
        " VALUES ('c2', 'archive', '/archive', 1, ?, ?)",
        (NOW, NOW),
    )
    documents = DocumentRepository(conn)
    for index in range(DISCOVERY_COUNT):
        documents.create(
            Document(
                id=f"d{index}",
                collection_id=C2 if index >= DISCOVERY_COUNT - 2 else C1,
                path=f"/notes/doc-{index:03d}.md",
                content=f"body {index}",
                title=f"Doc {index}",
                mtime=BASE_MTIME + index,
                metadata=_discovery_metadata(index),
            )
        )
    conn.commit()
    return conn


@pytest.fixture(scope="module")
def discovery_db() -> Iterator[sqlite3.Connection]:
    """Discovery corpus that runs on hosts without the sqlite-vec extension."""
    conn = _build_discovery_corpus()
    try:
        yield conn
    finally:
        conn.close()


def _options(**overrides: Any) -> SearchOptions:
    """Page options with highlights off (they add unrelated FTS lookups)."""
    fields: dict[str, Any] = {"include_highlights": False}
    fields.update(overrides)
    return SearchOptions(**fields)


def _hybrid(conn: sqlite3.Connection) -> HybridSearcher:
    """Hybrid searcher over the shared hermetic embedder."""
    return HybridSearcher(conn, embedder=ConceptEmbedder(), embedding_dim=EMBEDDING_DIM)


def _vector(conn: sqlite3.Connection) -> tuple[VectorSearcher, list[float]]:
    """Vector searcher plus the deterministic query embedding."""
    return (
        VectorSearcher(conn, embedding_dim=EMBEDDING_DIM),
        ConceptEmbedder().embed("alpha"),
    )


def _pipeline(conn: sqlite3.Connection) -> SearchPipeline:
    """Default hybrid pipeline (the ``query`` path)."""
    return SearchPipeline(conn, embedder=ConceptEmbedder(), embedding_dim=EMBEDDING_DIM)


_CONTAINMENT_CASES = [
    pytest.param(
        {"field": "tag", "operator": "eq", "value": "rare"},
        lambda index: index in RARE_INDEXES,
        id="tag-rare",
    ),
    pytest.param(
        {"field": "tag", "operator": "eq", "value": "common"},
        lambda index: index not in RARE_INDEXES,
        id="tag-common",
    ),
    pytest.param(
        {"field": "priority", "operator": "gte", "value": 10},
        lambda index: _metadata_for(index).get("priority", 0) >= 10,
        id="priority-gte",
    ),
    pytest.param(
        {"field": "path", "operator": "prefix", "value": "/notes/doc-00"},
        lambda index: index < 100,
        id="path-prefix",
    ),
    pytest.param(
        {"field": "mtime", "operator": "gte", "value": BASE_MTIME + 150},
        lambda index: index >= 150,
        id="mtime-g",
    ),
]


class TestContainmentInvariant:
    """filtered-hybrid ⊆ unfiltered-hybrid ∩ filter-set over a real corpus."""

    @pytest.mark.parametrize(("payload", "admitted"), _CONTAINMENT_CASES)
    def test_filtered_hybrid_is_a_subset_of_unfiltered_and_filter_set(
        self,
        search_db: sqlite3.Connection,
        payload: dict[str, Any],
        admitted,
    ) -> None:
        unfiltered = _hybrid(search_db).search("alpha", _options(limit=DOCUMENT_COUNT))
        filtered = _hybrid(search_db).search(
            "alpha", _options(limit=DOCUMENT_COUNT, filter=parse_filter(payload))
        )

        unfiltered_ids = {result.document_id for result in unfiltered}
        assert len(unfiltered_ids) == DOCUMENT_COUNT
        assert filtered, "a filter that admits documents must not return an empty page"
        for result in filtered:
            assert result.document_id in unfiltered_ids
            assert admitted(_doc_index(result.document_id))
        assert {result.document_id for result in filtered} <= {
            f"d{index}" for index in range(DOCUMENT_COUNT) if admitted(index)
        }


class TestAdmitAllEquivalence:
    """A filter admitting every document reproduces the unfiltered page."""

    def test_exists_tag_reproduces_the_unfiltered_page_byte_for_byte(
        self, search_db: sqlite3.Connection
    ) -> None:
        unfiltered = _hybrid(search_db).search("alpha", _options(limit=20))
        filtered = _hybrid(search_db).search(
            "alpha",
            _options(
                limit=20,
                filter=parse_filter({"field": "tag", "operator": "exists", "value": True}),
            ),
        )

        assert [(r.document_id, r.rank, r.score) for r in filtered] == [
            (r.document_id, r.rank, r.score) for r in unfiltered
        ]


class TestSelectiveRecall:
    """The Pitfall 13 regression: ~2 % selectivity must return its matches."""

    def test_two_percent_filter_returns_rare_documents_on_all_paths(
        self, search_db: sqlite3.Connection
    ) -> None:
        node = parse_filter({"field": "tag", "operator": "eq", "value": "rare"})
        expected = {f"d{index}" for index in RARE_INDEXES}

        bm25_results = BM25Searcher(search_db).search("alpha", _options(limit=10, filter=node))
        vector_searcher, query_embedding = _vector(search_db)
        vector_results = vector_searcher.search(query_embedding, _options(limit=10, filter=node))
        query_results = _pipeline(search_db).search("alpha", _options(limit=10, filter=node))

        assert {r.document_id for r in bm25_results} == expected
        assert {r.document_id for r in vector_results} == expected
        assert {r.document_id for r in query_results} == expected
        assert all(
            len(results) == len(expected)
            for results in (
                bm25_results,
                vector_results,
                query_results,
            )
        )


class TestComposition:
    """Filter x collection x pagination compose by AND on every leg."""

    def test_filter_and_collection_compose_by_and(self, search_db: sqlite3.Connection) -> None:
        node = parse_filter({"field": "tag", "operator": "eq", "value": "rare"})
        bm25 = BM25Searcher(search_db)
        in_notes = bm25.search("alpha", _options(limit=50, filter=node, collection_ids=[C1]))
        in_archive = bm25.search("alpha", _options(limit=50, filter=node, collection_ids=[C2]))

        assert {r.document_id for r in in_notes} == {f"d{index}" for index in RARE_INDEXES}
        # The rare documents live in c1; the archive scope admits none of them.
        assert in_archive == []

    def test_filter_collection_and_pagination_compose(self, search_db: sqlite3.Connection) -> None:
        node = parse_filter({"field": "tag", "operator": "eq", "value": "common"})
        bm25 = BM25Searcher(search_db)
        page = bm25.search("alpha", _options(limit=5, offset=5, filter=node, collection_ids=[C1]))
        window = bm25.search(
            "alpha", _options(limit=10, offset=0, filter=node, collection_ids=[C1])
        )

        assert [r.document_id for r in page] == [r.document_id for r in window][5:10]
        assert [r.rank for r in page] == [6, 7, 8, 9, 10]

    def test_built_in_mtime_and_path_filters_ride_the_vector_leg(
        self, search_db: sqlite3.Connection
    ) -> None:
        searcher, query_embedding = _vector(search_db)

        mtime_node = parse_filter({"field": "mtime", "operator": "gte", "value": BASE_MTIME + 150})
        mtime_results = searcher.search(
            query_embedding, _options(limit=DOCUMENT_COUNT, filter=mtime_node)
        )
        assert {r.document_id for r in mtime_results} == {
            f"d{index}" for index in range(150, DOCUMENT_COUNT)
        }

        path_node = parse_filter({"field": "path", "operator": "prefix", "value": "/notes/doc-00"})
        path_results = searcher.search(
            query_embedding, _options(limit=DOCUMENT_COUNT, filter=path_node)
        )
        assert path_results
        assert all(r.path.startswith("/notes/doc-00") for r in path_results)


class TestEmptyMatchSentinel:
    """A filter matching nothing is an empty page, never the unfiltered set."""

    def test_empty_match_returns_empty_from_all_commands_and_both_legs(
        self, search_db: sqlite3.Connection
    ) -> None:
        node = parse_filter({"field": "no_such_key", "operator": "exists", "value": True})
        vector_searcher, query_embedding = _vector(search_db)

        assert BM25Searcher(search_db).search("alpha", _options(limit=10, filter=node)) == []
        assert vector_searcher.search(query_embedding, _options(limit=10, filter=node)) == []
        assert _hybrid(search_db).search("alpha", _options(limit=10, filter=node)) == []
        assert _pipeline(search_db).search("alpha", _options(limit=10, filter=node)) == []

        # The same query is non-empty unfiltered: the sentinel never degrades.
        assert BM25Searcher(search_db).search("alpha", _options(limit=10))


class TestTypedExactMatch:
    """Numeric typing uses the typed column: 10 == 10.0, but "10" is a string."""

    def test_number_ten_matches_int_and_float_but_never_a_string(
        self, search_db: sqlite3.Connection
    ) -> None:
        expected = {f"d{INT_PRIORITY_INDEX}", f"d{FLOAT_PRIORITY_INDEX}"}
        numeric_node = parse_filter({"field": "priority", "operator": "eq", "value": 10})
        string_node = parse_filter({"field": "priority", "operator": "eq", "value": "10"})

        bm25 = BM25Searcher(search_db)
        assert {
            r.document_id
            for r in bm25.search("alpha", _options(limit=DOCUMENT_COUNT, filter=numeric_node))
        } == expected
        assert bm25.search("alpha", _options(limit=DOCUMENT_COUNT, filter=string_node)) == []

        vector_searcher, query_embedding = _vector(search_db)
        assert {
            r.document_id
            for r in vector_searcher.search(
                query_embedding, _options(limit=DOCUMENT_COUNT, filter=numeric_node)
            )
        } == expected
        assert (
            vector_searcher.search(
                query_embedding, _options(limit=DOCUMENT_COUNT, filter=string_node)
            )
            == []
        )


class TestInjectionShapedValues:
    """T-20-09: an operand can never alter the SQL structure."""

    @pytest.mark.parametrize(
        "value",
        ["rare'", "rare;", "rare--", "rare%", "'; DROP TABLE documents; --"],
    )
    def test_injection_shaped_values_match_like_a_plain_non_match(
        self, search_db: sqlite3.Connection, value: str
    ) -> None:
        node = parse_filter({"field": "tag", "operator": "eq", "value": value})
        vector_searcher, query_embedding = _vector(search_db)

        assert BM25Searcher(search_db).search("alpha", _options(limit=10, filter=node)) == []
        assert vector_searcher.search(query_embedding, _options(limit=10, filter=node)) == []
        # The documents table survived intact and still serves the corpus.
        assert (
            len(BM25Searcher(search_db).search("alpha", _options(limit=DOCUMENT_COUNT)))
            == DOCUMENT_COUNT
        )


class TestSkippedKeyVisibility:
    """D-07: a non-indexable key is skipped per key, never per document."""

    def test_nested_key_document_stays_filterable_by_other_keys(
        self, search_db: sqlite3.Connection
    ) -> None:
        common_node = parse_filter({"field": "tag", "operator": "eq", "value": "common"})
        common_results = BM25Searcher(search_db).search(
            "alpha", _options(limit=DOCUMENT_COUNT, filter=common_node)
        )
        assert f"d{NESTED_INDEX}" in {r.document_id for r in common_results}

        nested_node = parse_filter({"field": "nested", "operator": "exists", "value": True})
        assert BM25Searcher(search_db).search("alpha", _options(limit=10, filter=nested_node)) == []

        rows = search_db.execute(
            "SELECT key, reason FROM document_metadata_skips WHERE document_id = ?",
            (f"d{NESTED_INDEX}",),
        ).fetchall()
        assert [(row["key"], row["reason"]) for row in rows] == [("nested", "nested")]


class TestNoticeStaysOffStdout:
    """T-20-11: the D-09 notice goes to stderr only, never machine output."""

    def test_too_selective_notice_never_reaches_stdout(
        self,
        search_db: sqlite3.Connection,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setattr("sif.search.vector._MAX_FETCH_K", 8)
        node = parse_filter({"field": "tag", "operator": "eq", "value": "common"})
        searcher, query_embedding = _vector(search_db)

        with caplog.at_level(logging.WARNING):
            results = searcher.search(query_embedding, _options(limit=10, filter=node))

        captured = capsys.readouterr()
        assert captured.out == ""
        assert "highly selective" in caplog.text
        assert len(results) == 8


class TestDiscoveryParity:
    """D-16: discovery never lies, proven in both directions.

    Uses ``discovery_db`` (a repository-built corpus without sqlite-vec), so
    these assertions run on hosts where the extension is unavailable.
    """

    def _discover(self, conn: sqlite3.Connection, **overrides: Any) -> dict[str, Any]:
        """Discover with the explicit no-filter/no-match defaults."""
        params: dict[str, Any] = {
            "collection_ids": None,
            "filter_predicate": None,
            "match_predicate": None,
            "limit": 1000,
            "value_limit": 100,
        }
        params.update(overrides)
        return MetadataValueRepository(conn).discover(**params)

    def test_every_reported_key_and_value_is_filterable(
        self, discovery_db: sqlite3.Connection
    ) -> None:
        """reported => filterable: counts equal ``count_matching_documents``."""
        result = self._discover(discovery_db)
        assert result["keys"]
        for entry in result["keys"]:
            key = entry["key"]
            present = parse_filter({"field": key, "operator": "exists", "value": True})
            assert count_matching_documents(discovery_db, present, None) == entry["documents"]
            for type_entry in entry["types"]:
                assert type_entry["values"], f"{key}/{type_entry['type']} reports no values"
                for value in type_entry["values"]:
                    node = parse_filter({"field": key, "operator": "eq", "value": value["value"]})
                    matches = count_matching_documents(discovery_db, node, None)
                    assert matches == value["documents"]
                    assert matches > 0

    def test_every_filterable_key_is_reported(self, discovery_db: sqlite3.Connection) -> None:
        """filterable => reported: the typed store's key set equals ``keys``."""
        reported = {entry["key"] for entry in self._discover(discovery_db)["keys"]}
        stored = {
            row[0]
            for row in discovery_db.execute(
                "SELECT DISTINCT key FROM document_metadata_values"
            ).fetchall()
        }
        assert reported == stored
        assert "path" not in reported
        assert "mtime" not in reported

    def test_non_indexable_key_is_counted_not_filterable(
        self, discovery_db: sqlite3.Connection
    ) -> None:
        """The nested key is skipped once, absent from keys, and matches nothing."""
        result = self._discover(discovery_db)
        assert result["skippedKeys"] == 1
        assert "nested" not in {entry["key"] for entry in result["keys"]}
        nested = parse_filter({"field": "nested", "operator": "exists", "value": True})
        assert count_matching_documents(discovery_db, nested, None) == 0
        owner = parse_filter({"field": "nested_owner", "operator": "eq", "value": "yes"})
        assert count_matching_documents(discovery_db, owner, None) == 1

    def test_built_ins_are_reported_and_filterable(self, discovery_db: sqlite3.Connection) -> None:
        """``path``/``mtime`` are reported as built-ins and themselves filterable."""
        result = self._discover(discovery_db)
        assert [entry["key"] for entry in result["builtIns"]] == ["path", "mtime"]
        assert [entry["documents"] for entry in result["builtIns"]] == [
            DISCOVERY_COUNT,
            DISCOVERY_COUNT,
        ]

        path_node = parse_filter({"field": "path", "operator": "prefix", "value": "/notes/doc-00"})
        expected_paths = sum(
            1
            for index in range(DISCOVERY_COUNT)
            if f"/notes/doc-{index:03d}.md".startswith("/notes/doc-00")
        )
        assert expected_paths
        assert count_matching_documents(discovery_db, path_node, None) == expected_paths

        mtime_node = parse_filter({"field": "mtime", "operator": "gte", "value": BASE_MTIME + 8})
        expected_mtimes = sum(
            1 for index in range(DISCOVERY_COUNT) if BASE_MTIME + index >= BASE_MTIME + 8
        )
        assert expected_mtimes
        assert count_matching_documents(discovery_db, mtime_node, None) == expected_mtimes
