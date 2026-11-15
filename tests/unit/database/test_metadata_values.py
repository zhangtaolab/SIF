"""Typed metadata derivation and the typed kv store (Phase 20, D-05/D-07/D-19).

The derived view is the migration contract: ``qmd.metadata`` resolution,
reserved-name shadowing, the D-07 caps, and bounded skip accounting must all
produce the same rows from the live canonical string and from the stored
``documents.metadata`` blob — otherwise the backfill and the write path
disagree (research Pitfall 3).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from sif.core.filters import parse_filter
from sif.core.models import Collection, Document, canonical_metadata_json
from sif.database.metadata_repository import (
    MetadataValueRepository,
    SkippedKey,
    TypedRow,
    filterable_metadata,
    typed_rows,
)
from sif.database.repositories import CollectionRepository, DocumentRepository
from sif.database.schema import SchemaManager
from sif.search.filters import count_matching_documents


@pytest.fixture
def db():
    """Real in-memory SQLite with the production documents/metadata DDL."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    manager = SchemaManager(conn)
    manager._create_collections_table()
    manager._create_documents_table()
    manager._create_metadata_tables()
    yield conn
    conn.close()


def _seed_collection(db: sqlite3.Connection) -> Collection:
    """Create the one collection the document fixtures reference."""
    collection = Collection(id="coll-meta-values", name="meta-values", path="/notes")
    CollectionRepository(db).create(collection)
    return collection


def _seed_document(
    db: sqlite3.Connection,
    metadata: dict[str, Any],
    document_id: str = "doc-1",
    path: str = "/notes/doc-1.md",
) -> Document:
    """Write one document through the production repository path."""
    document = Document(
        id=document_id,
        collection_id="coll-meta-values",
        path=path,
        content="body",
        metadata=metadata,
    )
    DocumentRepository(db).create(document)
    db.commit()
    return document


def _stored_rows(db: sqlite3.Connection, document_id: str) -> list[tuple[Any, ...]]:
    """Return the typed value rows for one document in key/ordinal order."""
    return [
        (
            row["key"],
            row["ordinal"],
            row["value_type"],
            row["text_value"],
            row["number_value"],
            row["boolean_value"],
        )
        for row in db.execute(
            "SELECT key, ordinal, value_type, text_value, number_value, boolean_value "
            "FROM document_metadata_values WHERE document_id = ? ORDER BY key, ordinal",
            (document_id,),
        )
    ]


class TestDerivation:
    """The canonical-JSON derivation contract shared by writes and backfill."""

    def test_date_valued_key_parity_between_live_and_stored(self, db):
        """A live datetime and its stored canonical blob derive identical rows."""
        _seed_collection(db)
        document = _seed_document(db, {"due": datetime(2024, 1, 2, 3, 4, 5), "status": "active"})
        stored_json = db.execute(
            "SELECT metadata FROM documents WHERE id = ?", (document.id,)
        ).fetchone()[0]

        live_rows = typed_rows(canonical_metadata_json(document.metadata))
        backfill_rows = typed_rows(stored_json)

        assert live_rows == backfill_rows
        rows, skipped = live_rows
        assert skipped == []
        assert rows == [
            TypedRow("due", 0, "string", text_value="2024-01-02 03:04:05"),
            TypedRow("status", 0, "string", text_value="active"),
        ]
        # The repository write path stored exactly the derived rows.
        assert _stored_rows(db, document.id) == [
            ("due", 0, "string", "2024-01-02 03:04:05", None, None),
            ("status", 0, "string", "active", None, None),
        ]

    def test_numeric_values_compare_as_numbers(self, db):
        """10 and 10.0 share a number_value; a boolean row is never a number."""
        _seed_collection(db)
        _seed_document(db, {"score": 10}, document_id="doc-int", path="/notes/int.md")
        _seed_document(db, {"score": 10.0}, document_id="doc-float", path="/notes/float.md")
        _seed_document(db, {"score": True}, document_id="doc-bool", path="/notes/bool.md")

        rows_int, _ = typed_rows('{"score":10}')
        rows_float, _ = typed_rows('{"score":10.0}')
        assert rows_int == rows_float
        assert rows_int[0].number_value == 10.0

        int_filter = parse_filter({"field": "score", "operator": "eq", "value": 10})
        float_filter = parse_filter({"field": "score", "operator": "eq", "value": 10.0})
        assert count_matching_documents(db, int_filter, None) == 2
        assert count_matching_documents(db, float_filter, None) == 2

        bool_rows, bool_skipped = typed_rows('{"score":true}')
        assert bool_skipped == []
        assert bool_rows == [TypedRow("score", 0, "boolean", boolean_value=1)]
        assert bool_rows[0].number_value is None
        assert count_matching_documents(db, int_filter, None) == 2

    def test_namespace_wins_on_collision_and_merges_native_keys(self):
        """qmd.metadata overrides a colliding native key; native keys fill the rest."""
        resolved = filterable_metadata(
            {
                "status": "native",
                "tags": ["a", "b"],
                "qmd": {"metadata": {"status": "namespace", "owner": "ada"}},
            }
        )

        assert resolved == {"status": "namespace", "tags": ["a", "b"], "owner": "ada"}
        rows, skipped = typed_rows(
            canonical_metadata_json(
                {
                    "status": "native",
                    "qmd": {"metadata": {"status": "namespace", "owner": "ada"}},
                }
            )
        )
        assert skipped == []
        assert [(row.key, row.text_value) for row in rows] == [
            ("owner", "ada"),
            ("status", "namespace"),
        ]

    def test_document_without_namespace_is_unaffected(self):
        """A SIF-native document derives the same rows as before the namespace."""
        metadata = {"status": "active", "tags": ["x", "y"], "score": 3}
        canonical = canonical_metadata_json(metadata)

        assert filterable_metadata(metadata) == metadata
        rows, skipped = typed_rows(canonical)
        assert skipped == []
        assert [(row.key, row.ordinal, row.value_type) for row in rows] == [
            ("score", 0, "number"),
            ("status", 0, "string"),
            ("tags", 0, "string"),
            ("tags", 1, "string"),
        ]

    def test_reserved_names_are_shadowed_not_skipped(self):
        """path/mtime frontmatter keys produce no row and no skip row (D-03)."""
        rows, skipped = typed_rows('{"path":"/notes/a.md","mtime":123,"status":"ok"}')

        assert rows == [TypedRow("status", 0, "string", text_value="ok")]
        assert skipped == []

        rows, skipped = typed_rows(
            '{"qmd":{"metadata":{"path":"/qmd/a.md","mtime":9}},"status":"ok"}'
        )
        assert rows == [TypedRow("status", 0, "string", text_value="ok")]
        assert skipped == []

    @pytest.mark.parametrize(
        ("metadata", "key", "reason"),
        [
            ({"obj": {"nested": 1}}, "obj", "nested"),
            ({"arr_obj": [{"nested": 1}]}, "arr_obj", "nested"),
            ({"nothing": None}, "nothing", "null"),
            ({"mixed": ["a", 1]}, "mixed", "mixed_array"),
            ({"mixed_bool": [True, 1]}, "mixed_bool", "mixed_array"),
            ({"list_of_lists": [[1], [2]]}, "list_of_lists", "mixed_array"),
            ({"k" * 129: "v"}, "k" * 129, "cap_key"),
            ({"long": "x" * 1025}, "long", "cap_string"),
            ({"many": [1] * 129}, "many", "cap_array"),
        ],
    )
    def test_skip_reasons(self, metadata: dict[str, Any], key: str, reason: str):
        """Every per-key skip reason is reachable from one documented shape."""
        rows, skipped = typed_rows(canonical_metadata_json(metadata))

        assert rows == []
        assert skipped == [SkippedKey(key, reason)]

    def test_cap_keys_skips_keys_after_the_first_64(self):
        """A 65-key document stores 64 keys and records exactly one cap_keys skip."""
        metadata = {f"k{index:02d}": index for index in range(65)}

        rows, skipped = typed_rows(canonical_metadata_json(metadata))

        assert len({row.key for row in rows}) == 64
        assert skipped == [SkippedKey("k64", "cap_keys")]

    def test_frontmatter_cap_skips_all_keys_bounded_to_64(self):
        """A >64 KB blob records at most 64 cap_frontmatter skips and no rows."""
        metadata = {f"k{index:02d}": "x" * 1000 for index in range(70)}
        canonical = canonical_metadata_json(metadata)
        assert len(canonical.encode("utf-8")) > 65_536

        rows, skipped = typed_rows(canonical)

        assert rows == []
        assert len(skipped) == 64
        assert {skip.reason for skip in skipped} == {"cap_frontmatter"}
        assert [skip.key for skip in skipped] == sorted(metadata)[:64]

    def test_skip_rows_never_exceed_64_per_document(self):
        """A hostile 200-key document is bounded to 64 skip rows."""
        metadata = {f"k{index:03d}": {"nested": 1} for index in range(200)}

        rows, skipped = typed_rows(canonical_metadata_json(metadata))

        assert rows == []
        assert len(skipped) == 64

    def test_homogeneous_array_emits_ordinal_rows(self):
        """Flat arrays become one typed row per element, preserving order."""
        rows, skipped = typed_rows('{"tags":["a","b"],"scores":[1,2.5]}')

        assert skipped == []
        assert [(row.key, row.ordinal, row.value_type) for row in rows] == [
            ("scores", 0, "number"),
            ("scores", 1, "number"),
            ("tags", 0, "string"),
            ("tags", 1, "string"),
        ]

    def test_non_mapping_canonical_payload_derives_nothing(self):
        """A JSON array (never produced by the serializer) yields no rows or skips."""
        assert typed_rows("[]") == ([], [])
        assert typed_rows("") == ([], [])

    def test_replace_from_canonical_rebuilds_idempotently(self, db):
        """Delete-then-insert is idempotent and returns row/skip counts."""
        _seed_collection(db)
        document = _seed_document(db, {"status": "active"})
        repo = MetadataValueRepository(db)
        first_json = canonical_metadata_json({"status": "archived", "tags": ["a", "b"]})

        assert repo.replace_from_canonical(document.id, first_json) == (3, 0)
        assert repo.replace_from_canonical(document.id, first_json) == (3, 0)
        assert len(_stored_rows(db, document.id)) == 3
        assert repo.delete_by_document(document.id) == 3
        assert _stored_rows(db, document.id) == []


class TestBenchFixtureFilterable:
    """The frozen 150-document bench corpus is filterable (FILT-04).

    The corpus carries no YAML frontmatter, so ``build_bench_db`` derives two
    synthetic keys per document. Expected counts are derived from the frozen
    corpus with the same walk the builder uses — never hardcoded guesses.
    """

    CORPUS_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "bench" / "corpus"

    @classmethod
    def _derived_distribution(cls) -> dict[str, int]:
        """Category counts from the same sorted ``rglob`` walk as the builder."""
        counts: dict[str, int] = {}
        for path in sorted(cls.CORPUS_ROOT.rglob("*.md")):
            category = path.relative_to(cls.CORPUS_ROOT).parts[0]
            counts[category] = counts.get(category, 0) + 1
        return counts

    @pytest.fixture
    def bench_db(self):
        """Build the real bench index (skips when sqlite-vec is unavailable)."""
        from tests.support.bench import EMBEDDING_DIM, ConceptEmbedder, build_bench_db

        conn = build_bench_db(self.CORPUS_ROOT, ConceptEmbedder(), embedding_dim=EMBEDDING_DIM)
        yield conn
        conn.close()

    def test_corpus_distribution_is_the_measured_one(self):
        """The frozen corpus has four categories in the measured distribution."""
        assert self._derived_distribution() == {
            "keyword": 40,
            "multilingual": 36,
            "rival": 36,
            "synonym": 38,
        }
        assert len(list(self.CORPUS_ROOT.rglob("*.md"))) == 150

    def test_bench_categories_and_docs_are_filterable(self, bench_db):
        """Four bench_category values, 150 bench_doc rows, and the exact synonym count."""
        categories = [
            row[0]
            for row in bench_db.execute(
                "SELECT DISTINCT text_value FROM document_metadata_values"
                " WHERE key = 'bench_category' AND value_type = 'string'"
                " ORDER BY text_value"
            )
        ]
        assert categories == ["keyword", "multilingual", "rival", "synonym"]

        doc_rows = bench_db.execute(
            "SELECT COUNT(*) FROM document_metadata_values"
            " WHERE key = 'bench_doc' AND value_type = 'number'"
        ).fetchone()[0]
        assert doc_rows == 150

        synonym_filter = parse_filter(
            {"field": "bench_category", "operator": "eq", "value": "synonym"}
        )
        assert (
            count_matching_documents(bench_db, synonym_filter, None)
            == self._derived_distribution()["synonym"]
        )
