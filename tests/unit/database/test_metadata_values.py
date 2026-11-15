"""Typed metadata derivation and the typed kv store (Phase 20, D-05/D-07/D-19).

The derived view is the migration contract: ``qmd.metadata`` resolution,
reserved-name shadowing, the D-07 caps, and bounded skip accounting must all
produce the same rows from the live canonical string and from the stored
``documents.metadata`` blob — otherwise the backfill and the write path
disagree (research Pitfall 3).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from sif.core.filters import parse_filter, parse_match
from sif.core.models import Collection, Document, canonical_metadata_json
from sif.database.metadata_repository import (
    SKIP_CAP_NUMBER,
    SKIP_INVALID_JSON,
    SKIP_NON_FINITE,
    UNPARSEABLE_METADATA_KEY,
    MetadataValueRepository,
    SkippedKey,
    TypedRow,
    filterable_metadata,
    typed_rows,
)
from sif.database.repositories import CollectionRepository, DocumentRepository
from sif.database.schema import SchemaManager
from sif.search.filters import compile_filter, compile_match, count_matching_documents


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
    mtime: float | None = None,
) -> Document:
    """Write one document through the production repository path."""
    document = Document(
        id=document_id,
        collection_id="coll-meta-values",
        path=path,
        content="body",
        metadata=metadata,
        mtime=mtime if mtime is not None else datetime.now().timestamp(),
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


def _reject_json_constant(token: str) -> None:
    """``json.loads`` parse_constant hook that refuses NaN/Infinity tokens."""
    raise AssertionError(f"non-standard JSON token: {token}")


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
            ({"tags": ["x" * 1025]}, "tags", "cap_string"),
            ({"tags": ["ok", "x" * 1025]}, "tags", "cap_string"),
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

    def test_empty_array_is_a_skip_not_a_silent_drop(self):
        """WR-05: ``tags: []`` records an ``empty_array`` skip (D-07 accounting)."""
        rows, skipped = typed_rows('{"tags":[],"status":"ok"}')

        assert rows == [TypedRow("status", 0, "string", text_value="ok")]
        assert skipped == [SkippedKey("tags", "empty_array")]

    def test_array_element_string_length_boundary(self):
        """WR-04: an element exactly at the 1024-character cap is still stored."""
        rows, skipped = typed_rows(canonical_metadata_json({"tags": ["x" * 1024]}))

        assert skipped == []
        assert rows == [TypedRow("tags", 0, "string", text_value="x" * 1024)]

    def test_non_mapping_canonical_payload_derives_nothing(self):
        """A JSON array (never produced by the serializer) yields no rows or skips."""
        assert typed_rows("[]") == ([], [])
        assert typed_rows("") == ([], [])

    @pytest.mark.parametrize(
        ("canonical", "key", "reason"),
        [
            ('{"big":' + "9" * 400 + "}", "big", SKIP_CAP_NUMBER),
            ('{"big":[' + "9" * 400 + "]}", "big", SKIP_CAP_NUMBER),
            ('{"bad":NaN}', "bad", SKIP_NON_FINITE),
            ('{"bad":Infinity}', "bad", SKIP_NON_FINITE),
            ('{"bad":-Infinity}', "bad", SKIP_NON_FINITE),
        ],
    )
    def test_unrepresentable_numbers_skip_per_key(
        self, canonical: str, key: str, reason: str
    ) -> None:
        """CR-01: huge integers and bare NaN/Infinity skip that key, never raise.

        ``json.loads`` preserves arbitrary-precision integers and accepts the
        non-standard constants ``json.dumps`` used to emit. ``float(10**400)``
        raises OverflowError and a NaN bound to SQLite is NULL, so derivation
        must be total over both shapes (D-07 per-key skip).
        """
        rows, skipped = typed_rows(canonical)

        assert rows == []
        assert skipped == [SkippedKey(key, reason)]

    def test_unrepresentable_number_does_not_hide_other_keys(self) -> None:
        """CR-01: a skipped huge integer leaves the document's other keys filterable."""
        rows, skipped = typed_rows('{"big":' + "9" * 400 + ',"status":"ok"}')

        assert rows == [TypedRow("status", 0, "string", text_value="ok")]
        assert skipped == [SkippedKey("big", SKIP_CAP_NUMBER)]

    def test_unparseable_stored_blob_records_one_document_level_skip(self) -> None:
        """CR-01: an undecomposable blob is a skip, so the backfill can complete."""
        rows, skipped = typed_rows('{"broken"')

        assert rows == []
        assert skipped == [SkippedKey(UNPARSEABLE_METADATA_KEY, SKIP_INVALID_JSON)]

    def test_canonical_serializer_stringifies_non_finite_floats(self) -> None:
        """CR-01/WR-06: ``.nan``/``.inf`` never enter documents.metadata as tokens."""
        canonical = canonical_metadata_json(
            {"inf": float("inf"), "neg": float("-inf"), "nan": float("nan")}
        )

        parsed = json.loads(canonical, parse_constant=_reject_json_constant)

        assert parsed == {"inf": "inf", "nan": "nan", "neg": "-inf"}
        # The store derives a filterable string row, matching the stored blob.
        rows, skipped = typed_rows(canonical)
        assert skipped == []
        assert {row.key: row.text_value for row in rows} == {
            "inf": "inf",
            "nan": "nan",
            "neg": "-inf",
        }

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


class TestDiscovery:
    """D-15/D-20 discovery aggregates over the same store the filters read."""

    def _discover(self, db: sqlite3.Connection, **overrides: Any) -> dict[str, Any]:
        """Call ``discover`` with the explicit no-filter/no-match defaults."""
        params: dict[str, Any] = {
            "collection_ids": None,
            "filter_predicate": None,
            "match_predicate": None,
        }
        params.update(overrides)
        return MetadataValueRepository(db).discover(**params)

    @staticmethod
    def _key(result: dict[str, Any], name: str) -> dict[str, Any]:
        """Return one reported key entry by name."""
        return next(entry for entry in result["keys"] if entry["key"] == name)

    @staticmethod
    def _seed_docs(
        db: sqlite3.Connection, rows: list[tuple[str, dict[str, Any], float, str]]
    ) -> None:
        """Seed ``(document_id, metadata, mtime, path)`` rows through the repository."""
        _seed_collection(db)
        for document_id, metadata, mtime, path in rows:
            _seed_document(db, metadata, document_id=document_id, path=path, mtime=mtime)

    def test_envelope_is_frozen_and_omits_filtered_documents(self, db: sqlite3.Connection) -> None:
        """No filter means no ``filteredDocuments``; builtIns are always present."""
        self._seed_docs(db, [("d0", {"tag": "a"}, 100.0, "/notes/a.md")])
        result = self._discover(db)
        assert result["documents"] == 1
        assert "filteredDocuments" not in result
        assert list(result) == [
            "documents",
            "totalKeys",
            "remainingKeys",
            "skippedKeys",
            "builtIns",
            "keys",
        ]
        assert [entry["key"] for entry in result["builtIns"]] == ["path", "mtime"]

    def test_median_is_exact_for_an_odd_numeric_cohort(self, db: sqlite3.Connection) -> None:
        """Three numeric rows median to the middle value."""
        self._seed_docs(
            db,
            [
                ("d0", {"score": 30}, 100.0, "/notes/a.md"),
                ("d1", {"score": 10}, 200.0, "/notes/b.md"),
                ("d2", {"score": 20}, 300.0, "/notes/c.md"),
            ],
        )
        entry = self._key(self._discover(db), "score")
        assert entry["types"][0]["range"] == {"min": 10.0, "median": 20.0, "max": 30.0}

    def test_median_is_exact_for_an_even_numeric_cohort(self, db: sqlite3.Connection) -> None:
        """Four numeric rows median to the midpoint of positions two and three."""
        self._seed_docs(
            db,
            [
                ("d0", {"score": 10}, 100.0, "/notes/a.md"),
                ("d1", {"score": 20}, 200.0, "/notes/b.md"),
                ("d2", {"score": 30}, 300.0, "/notes/c.md"),
                ("d3", {"score": 40}, 400.0, "/notes/d.md"),
            ],
        )
        entry = self._key(self._discover(db), "score")
        assert entry["types"][0]["range"] == {"min": 10.0, "median": 25.0, "max": 40.0}

    def test_array_elements_each_contribute_one_numeric_row(self, db: sqlite3.Connection) -> None:
        """A five-element cohort over two documents medians to the third value."""
        self._seed_docs(
            db,
            [
                ("d0", {"score": [1, 2, 3]}, 100.0, "/notes/a.md"),
                ("d1", {"score": [4, 5]}, 200.0, "/notes/b.md"),
            ],
        )
        entry = self._key(self._discover(db), "score")
        type_entry = entry["types"][0]
        assert type_entry["range"] == {"min": 1.0, "median": 3.0, "max": 5.0}
        assert type_entry["documents"] == 2
        assert type_entry["multiValued"] is True
        assert type_entry["distinctValues"] == 5

    def test_counts_are_documents_not_values(self, db: sqlite3.Connection) -> None:
        """Key/type counts count documents; each value counts its documents."""
        self._seed_docs(
            db,
            [
                ("d0", {"topic": ["a", "b"]}, 100.0, "/notes/a.md"),
                ("d1", {"topic": ["a"]}, 200.0, "/notes/b.md"),
            ],
        )
        entry = self._key(self._discover(db), "topic")
        assert entry["documents"] == 2
        type_entry = entry["types"][0]
        assert type_entry["documents"] == 2
        assert type_entry["multiValued"] is True
        assert {item["value"]: item["documents"] for item in type_entry["values"]} == {
            "a": 2,
            "b": 1,
        }
        assert type_entry["distinctValues"] == 2
        assert type_entry["remainingValues"] == 0

    def test_key_and_value_windows_report_exact_remainders(self, db: sqlite3.Connection) -> None:
        """Window plus remainder equals the total at and beyond the boundary."""
        rows = []
        for index in range(5):
            metadata = {f"k{key_index}": f"v{index}" for key_index in range(index + 1)}
            rows.append((f"d{index}", metadata, 100.0 + index, f"/notes/d{index}.md"))
        self._seed_docs(db, rows)

        narrow = self._discover(db, limit=2, value_limit=1)
        assert narrow["totalKeys"] == 5
        assert narrow["remainingKeys"] == 3
        assert [entry["key"] for entry in narrow["keys"]] == ["k0", "k1"]
        k0 = self._key(narrow, "k0")
        assert k0["documents"] == 5
        assert k0["types"][0]["distinctValues"] == 5
        assert len(k0["types"][0]["values"]) == 1
        assert k0["types"][0]["remainingValues"] == 4

        wide = self._discover(db, limit=5, value_limit=10)
        assert wide["remainingKeys"] == 0
        assert self._key(wide, "k0")["types"][0]["remainingValues"] == 0

    def test_min_count_filters_values_and_keeps_distinct_counts_consistent(
        self, db: sqlite3.Connection
    ) -> None:
        """``min_count`` drops low-count values without narrowing type documents."""
        self._seed_docs(
            db,
            [
                ("d0", {"tag": "common"}, 100.0, "/notes/a.md"),
                ("d1", {"tag": "common"}, 200.0, "/notes/b.md"),
                ("d2", {"tag": "rare"}, 300.0, "/notes/c.md"),
            ],
        )
        narrow = self._key(self._discover(db, min_count=2), "tag")["types"][0]
        assert narrow["documents"] == 3
        assert narrow["values"] == [{"value": "common", "documents": 2}]
        assert narrow["distinctValues"] == 1
        assert narrow["remainingValues"] == 0

        wide = self._key(self._discover(db, min_count=1), "tag")["types"][0]
        assert wide["distinctValues"] == 2
        assert wide["remainingValues"] == 0

    def test_mixed_type_key_splits_with_a_range_only_on_number(
        self, db: sqlite3.Connection
    ) -> None:
        """A key stored as a number and a string yields one type entry each."""
        self._seed_docs(
            db,
            [
                ("d0", {"mixed": 10}, 100.0, "/notes/a.md"),
                ("d1", {"mixed": "ten"}, 200.0, "/notes/b.md"),
            ],
        )
        entry = self._key(self._discover(db), "mixed")
        assert entry["documents"] == 2
        types = {type_entry["type"]: type_entry for type_entry in entry["types"]}
        assert set(types) == {"number", "string"}
        assert types["number"]["range"] == {"min": 10.0, "median": 10.0, "max": 10.0}
        assert "range" not in types["string"]

    def test_match_narrows_entries_but_not_document_denominators(
        self, db: sqlite3.Connection
    ) -> None:
        """``match`` narrows keys/totalKeys; the denominators stay region-wide."""
        self._seed_docs(
            db,
            [
                ("d0", {"tag": "x"}, 100.0, "/notes/a.md"),
                ("d1", {"tag": "y"}, 200.0, "/notes/b.md"),
                ("d2", {"other": 1}, 300.0, "/notes/c.md"),
            ],
        )
        match = compile_match(parse_match({"field": "key", "operator": "prefix", "value": "ta"}))
        result = self._discover(db, match_predicate=match)
        assert [entry["key"] for entry in result["keys"]] == ["tag"]
        assert result["totalKeys"] == 1
        assert result["documents"] == 3
        assert [entry["documents"] for entry in result["builtIns"]] == [3, 3]

    def test_nested_key_is_skipped_and_never_reported(self, db: sqlite3.Connection) -> None:
        """A non-indexable key counts in ``skippedKeys`` and is absent from ``keys``."""
        self._seed_docs(db, [("d0", {"nested": {"a": 1}, "good": "yes"}, 100.0, "/notes/a.md")])
        result = self._discover(db)
        assert result["skippedKeys"] == 1
        assert [entry["key"] for entry in result["keys"]] == ["good"]

    def test_empty_array_key_is_counted_in_skipped_keys(self, db: sqlite3.Connection) -> None:
        """WR-05: ``tags: []`` appears in ``skippedKeys``, never as a filterable key."""
        self._seed_docs(db, [("d0", {"tags": [], "good": "yes"}, 100.0, "/notes/a.md")])
        result = self._discover(db)
        assert result["skippedKeys"] == 1
        assert [entry["key"] for entry in result["keys"]] == ["good"]

    def test_reserved_frontmatter_names_are_built_ins_not_keys(
        self, db: sqlite3.Connection
    ) -> None:
        """D-03: a native ``path``/``mtime`` key is shadowed, not a skip and not a key."""
        self._seed_docs(
            db, [("d0", {"path": "native", "mtime": 5, "tag": "x"}, 100.0, "/notes/a.md")]
        )
        result = self._discover(db)
        assert [entry["key"] for entry in result["keys"]] == ["tag"]
        assert result["skippedKeys"] == 0
        assert [entry["key"] for entry in result["builtIns"]] == ["path", "mtime"]

    def test_filter_predicate_narrows_counts_but_not_the_scope_denominator(
        self, db: sqlite3.Connection
    ) -> None:
        """The filter narrows coverage (built-ins included); ``documents`` does not move."""
        self._seed_docs(
            db,
            [
                ("d0", {"tag": "rare", "priority": 1}, 100.0, "/notes/a.md"),
                ("d1", {"tag": "common", "priority": 2}, 200.0, "/notes/b.md"),
                ("d2", {"tag": "common"}, 300.0, "/notes/c.md"),
            ],
        )
        predicate = compile_filter(
            parse_filter({"field": "tag", "operator": "eq", "value": "common"}),
            alias="d",
            scope="corpus",
        )
        result = self._discover(db, filter_predicate=predicate)
        assert result["documents"] == 3
        assert result["filteredDocuments"] == 2
        tag = self._key(result, "tag")
        assert tag["documents"] == 2
        assert tag["types"][0]["values"] == [{"value": "common", "documents": 2}]
        priority = self._key(result, "priority")
        assert priority["documents"] == 1
        assert priority["types"][0]["range"] == {"min": 2.0, "median": 2.0, "max": 2.0}
        path_entry, mtime_entry = result["builtIns"]
        assert path_entry["documents"] == 2
        assert mtime_entry["documents"] == 2
        assert mtime_entry["types"][0]["range"] == {
            "min": 200.0,
            "median": 250.0,
            "max": 300.0,
        }

    def test_built_ins_report_counts_distinct_values_and_no_values(
        self, db: sqlite3.Connection
    ) -> None:
        """Built-ins carry region counts, a numeric range, and no inline values."""
        self._seed_docs(
            db,
            [
                ("d0", {"tag": "x"}, 100.0, "/notes/a.md"),
                ("d1", {"tag": "x"}, 200.0, "/notes/b.md"),
                ("d2", {"tag": "x"}, 300.0, "/notes/c.md"),
            ],
        )
        path_entry, mtime_entry = self._discover(db)["builtIns"]
        assert (path_entry["documents"], mtime_entry["documents"]) == (3, 3)
        path_type = path_entry["types"][0]
        assert path_type["distinctValues"] == 3
        assert path_type["values"] == []
        assert path_type["remainingValues"] == 3
        mtime_type = mtime_entry["types"][0]
        assert mtime_type["range"] == {"min": 100.0, "median": 200.0, "max": 300.0}
        assert mtime_type["values"] == []
        assert mtime_type["remainingValues"] == mtime_type["distinctValues"]

    def test_match_leaves_built_ins_unchanged(self, db: sqlite3.Connection) -> None:
        """The built-in section is invariant under the entry-scope ``match`` (D-20)."""
        self._seed_docs(
            db,
            [
                ("d0", {"tag": "x"}, 100.0, "/notes/a.md"),
                ("d1", {"other": 1}, 200.0, "/notes/b.md"),
            ],
        )
        baseline = self._discover(db)
        matched = self._discover(
            db,
            match_predicate=compile_match(
                parse_match({"field": "key", "operator": "prefix", "value": "ta"})
            ),
        )
        assert matched["builtIns"] == baseline["builtIns"]
        assert [entry["key"] for entry in matched["keys"]] == ["tag"]
