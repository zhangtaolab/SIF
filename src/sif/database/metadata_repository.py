"""Typed metadata derivation and the key-value store repository (Phase 20, D-05/D-07).

Typed rows are derived from the **canonical JSON string**, never from the
in-memory metadata dict: ``canonical_metadata_json`` uses ``default=str``, so
a YAML date is an ISO string in the stored blob but a ``datetime`` object in
the live dict — deriving from different sources would make the live write path
and the backfill disagree (research Pitfall 3). ``DocumentRepository.create``
and ``.update`` already compute that string; the backfill reads it back from
``documents.metadata``.

Resolution and shadowing happen in this derived view only (D-19/D-03), never
in ``parser.py`` and never in the checksum path:

- A ``qmd`` mapping whose ``metadata`` member is a mapping is the qmd
  namespace: the ``qmd`` key itself is dropped and every namespaced item is
  merged over the native keys, so the namespace wins on collision. Native
  top-level keys fill every key the namespace does not define, and a document
  with no namespace is unaffected.
- A frontmatter key named ``path`` or ``mtime`` is shadowed (not filterable,
  not a skipped key): the name is reserved, not invalid.

Every unindexable key is skipped **per key** with a bounded reason (D-07):
nested, null, mixed array, or one of the caps. The document still indexes and
its other keys remain filterable.
"""

from __future__ import annotations

import json
import math
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


# D-03: exactly two reserved built-in fields. A frontmatter key with either
# name is shadowed (not filterable, not a skipped key).
RESERVED_FIELDS = frozenset({"path", "mtime"})

# D-07 caps. The key budget doubles as the per-document skip-row budget so a
# hostile document cannot amplify the sidecar.
MAX_KEYS_PER_DOCUMENT = 64
MAX_KEY_BYTES = 128
MAX_STRING_CHARS = 1024
MAX_ARRAY_ELEMENTS = 128
MAX_FRONTMATTER_BYTES = 65_536

# D-07 skip reasons for keys that cannot enter the typed store.
SKIP_NESTED = "nested"
SKIP_NULL = "null"
SKIP_MIXED_ARRAY = "mixed_array"
SKIP_CAP_KEY = "cap_key"
SKIP_CAP_STRING = "cap_string"
SKIP_CAP_ARRAY = "cap_array"
SKIP_CAP_KEYS = "cap_keys"
SKIP_CAP_FRONTMATTER = "cap_frontmatter"
# CR-01: JSON numbers do not fit SQLite's REAL column. ``json.loads`` accepts
# bare ``NaN``/``Infinity`` literals and arbitrary-precision integers, but
# binding a NaN stores NULL (violating the typed-column CHECK) and
# ``float(10**400)`` raises OverflowError. Both shapes are bounded per-key
# skips (D-07) so one value can never abort indexing or brick an upgrade.
SKIP_NON_FINITE = "non_finite"
SKIP_CAP_NUMBER = "cap_number"
# CR-01: a stored blob that is not JSON cannot be decomposed key by key; the
# backfill records one document-level skip instead of failing every future open.
SKIP_INVALID_JSON = "invalid_json"
UNPARSEABLE_METADATA_KEY = "<metadata>"


@dataclass(frozen=True)
class TypedRow:
    """One stored scalar value: exactly one typed column is populated."""

    key: str
    ordinal: int
    value_type: str
    text_value: str | None = None
    number_value: float | None = None
    boolean_value: int | None = None


@dataclass(frozen=True)
class SkippedKey:
    """One frontmatter key that could not be stored, with its D-07 reason."""

    key: str
    reason: str


def _scalar_type(value: Any) -> str | None:
    """Classify one JSON scalar; ``None`` for non-scalars.

    ``bool`` is checked before ``int`` because ``bool`` is an ``int`` subclass:
    ``True`` must never be stored or compared as a number (D-10).
    """
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return None


def _number_skip_reason(value: int | float) -> str | None:
    """Return the D-07 reason a JSON number cannot enter the REAL typed store.

    ``json.loads`` preserves arbitrary-precision integers and its default
    ``parse_constant`` accepts bare ``NaN``/``Infinity``. ``float(10**400)``
    raises ``OverflowError`` and a NaN bound to SQLite becomes NULL (failing
    the typed-column CHECK), so both shapes are skipped per key instead of
    escaping derivation (CR-01).
    """
    try:
        converted = float(value)
    except (OverflowError, ValueError):
        return SKIP_CAP_NUMBER
    if not math.isfinite(converted):
        return SKIP_NON_FINITE
    return None


def _typed_row(key: str, ordinal: int, value: Any, value_type: str) -> TypedRow:
    """Build one typed row for an already-classified scalar value."""
    if value_type == "boolean":
        return TypedRow(key, ordinal, "boolean", boolean_value=int(bool(value)))
    if value_type == "number":
        return TypedRow(key, ordinal, "number", number_value=float(value))
    return TypedRow(key, ordinal, "string", text_value=str(value))


def _contains_mapping(value: Any) -> bool:
    """True when an array contains an object (a nested frontmatter shape)."""
    return isinstance(value, list) and any(isinstance(item, Mapping) for item in value)


def _append_skip(skipped: list[SkippedKey], key: str, reason: str) -> None:
    """Record one skip while the per-document 64-row budget lasts."""
    if len(skipped) < MAX_KEYS_PER_DOCUMENT:
        skipped.append(SkippedKey(key, reason))


def filterable_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve the filterable metadata view over a canonical mapping (D-19/D-03).

    A shallow copy: values are not transformed here. When ``qmd.metadata`` is
    present as a mapping, the ``qmd`` block is dropped and every namespaced
    item is merged over the native keys (the namespace wins on collision);
    native keys fill the rest. Reserved built-in names are then shadowed —
    never counted as skips.
    """
    resolved = {str(key): value for key, value in metadata.items()}
    qmd = metadata.get("qmd")
    if isinstance(qmd, Mapping):
        namespaced = qmd.get("metadata")
        if isinstance(namespaced, Mapping):
            resolved.pop("qmd", None)
            for key, value in namespaced.items():
                resolved[str(key)] = value
    for reserved in RESERVED_FIELDS:
        resolved.pop(reserved, None)
    return resolved


def _classify_array(key: str, value: list[Any]) -> tuple[list[TypedRow], str | None]:
    """Classify one array value; returns (rows, skip reason or ``None``)."""
    if not value:
        return [], None
    value_type = _scalar_type(value[0])
    if value_type is None or any(_scalar_type(item) != value_type for item in value):
        return [], SKIP_MIXED_ARRAY
    if len(value) > MAX_ARRAY_ELEMENTS:
        return [], SKIP_CAP_ARRAY
    if value_type == "number":
        for item in value:
            reason = _number_skip_reason(item)
            if reason is not None:
                return [], reason
    rows = [_typed_row(key, ordinal, item, value_type) for ordinal, item in enumerate(value)]
    return rows, None


def _classify_scalar(key: str, value: Any) -> tuple[list[TypedRow], str | None]:
    """Classify one non-mapping, non-array value; returns (rows, skip reason)."""
    if isinstance(value, str) and len(value) > MAX_STRING_CHARS:
        return [], SKIP_CAP_STRING
    value_type = _scalar_type(value)
    if value_type is None:  # pragma: no cover - JSON scalar types are exhaustive
        return [], SKIP_MIXED_ARRAY
    if value_type == "number":
        reason = _number_skip_reason(value)
        if reason is not None:
            return [], reason
    return [_typed_row(key, 0, value, value_type)], None


def _classify_value(key: str, value: Any) -> tuple[list[TypedRow], str | None]:
    """Classify one resolved value; returns (rows, skip reason or ``None``).

    Rules 4-10 of :func:`typed_rows`, in order. ``None`` as the reason means
    the value is filterable; the rows may still be empty (an empty array).
    """
    if isinstance(value, Mapping) or _contains_mapping(value):
        return [], SKIP_NESTED
    if value is None:
        return [], SKIP_NULL
    if isinstance(value, list):
        return _classify_array(key, value)
    return _classify_scalar(key, value)


def typed_rows(canonical_json: str) -> tuple[list[TypedRow], list[SkippedKey]]:
    """Derive typed rows and skipped keys from the canonical metadata JSON.

    The canonical string is the only input (D-05) and its ``sort_keys=True``
    order makes caps deterministic. Classification (D-07), in order:

    1. A blob that is not JSON yields one document-level ``invalid_json``
       skip (CR-01): the backfill must never abort every future open because
       one stored value is undecomposable.
    2. A >64 KB canonical blob skips every key as ``cap_frontmatter``
       (at most the first 64 recorded).
    3. Keys after the first 64 are skipped as ``cap_keys``.
    4. Keys over 128 bytes are skipped as ``cap_key``.
    5. Objects, and arrays containing an object, are skipped as ``nested``.
    6. ``None`` is skipped as ``null``.
    7. Arrays that are not flat homogeneous scalar lists (including arrays of
       arrays, and ``[true, 1]``-style mixes) are skipped as ``mixed_array``.
    8. Strings over 1024 characters are skipped as ``cap_string``.
    9. Arrays over 128 elements are skipped as ``cap_array``.
    10. Numbers that are non-finite or outside the double range are skipped as
        ``non_finite`` / ``cap_number`` (CR-01) — derivation is total over
        every shape JSON can express.
    11. Otherwise one row per scalar (``ordinal`` 0), or one row per array
        element (``ordinal`` 0..n-1) so arrays behave as sets.

    At most 64 skip rows are ever returned per document (the document-level
    ``invalid_json`` skip is the only row in that case).
    """
    try:
        raw = json.loads(canonical_json) if canonical_json else {}
    except (json.JSONDecodeError, TypeError):
        return [], [SkippedKey(UNPARSEABLE_METADATA_KEY, SKIP_INVALID_JSON)]
    if not isinstance(raw, Mapping):
        return [], []

    resolved = filterable_metadata(raw)
    keys = sorted(resolved)
    skipped: list[SkippedKey] = []

    if len(canonical_json.encode("utf-8")) > MAX_FRONTMATTER_BYTES:
        for key in keys[:MAX_KEYS_PER_DOCUMENT]:
            _append_skip(skipped, key, SKIP_CAP_FRONTMATTER)
        return [], skipped

    rows: list[TypedRow] = []
    for index, key in enumerate(keys):
        if index >= MAX_KEYS_PER_DOCUMENT:
            _append_skip(skipped, key, SKIP_CAP_KEYS)
            continue
        if len(key.encode("utf-8")) > MAX_KEY_BYTES:
            _append_skip(skipped, key, SKIP_CAP_KEY)
            continue
        value_rows, reason = _classify_value(key, resolved[key])
        if reason is None:
            rows.extend(value_rows)
        else:
            _append_skip(skipped, key, reason)

    return rows, skipped


_TYPE_ORDER = {"string": 0, "number": 1, "boolean": 2}


def _collection_clause(collection_ids: list[str] | None) -> tuple[str, list[Any]]:
    """Build the collection scope predicate (``None`` = every collection).

    ``[]`` is the exclude-all sentinel (the same contract as
    ``SearchOptions.collection_ids``): it renders an always-false predicate
    rather than the invalid ``IN ()``.
    """
    if collection_ids is None:
        return "", []
    if not collection_ids:
        return "AND 0 = 1", []
    placeholders = ", ".join(["?"] * len(collection_ids))
    return f"AND d.collection_id IN ({placeholders})", list(collection_ids)


def _median(values: list[float]) -> float:
    """Midpoint of the middle one or two sorted values (D-15)."""
    return sum(values) / len(values)


def _typed_value(value_type: str, text: Any, number: Any, boolean: Any) -> Any:
    """Render one stored value in its typed JSON form."""
    if value_type == "number":
        return float(number)
    if value_type == "boolean":
        return bool(boolean)
    return text


@dataclass(frozen=True)
class _DiscoveryQuery:
    """Compiled discovery SQL fragments and their bound parameters (D-15/D-20).

    ``region`` is the eligible-document CTE: the collection scope and the
    caller-compiled filter predicate only. ``match`` narrows the reported
    frontmatter entries, never the region.
    """

    region: str
    scope_params: list[Any]
    match_sql: str
    match_params: list[Any]


def _key_entries(
    key_rows: list[tuple[Any, ...]],
    type_rows: list[tuple[Any, ...]],
    value_rows: list[tuple[Any, ...]],
    medians: dict[str, float],
    value_limit: int,
) -> list[dict[str, Any]]:
    """Assemble the ordered ``keys`` list from one page's batched aggregates."""
    types_by_key: dict[str, list[dict[str, Any]]] = {str(row[0]): [] for row in key_rows}
    for key, value_type, documents, multi_valued, minimum, maximum in type_rows:
        entry: dict[str, Any] = {
            "type": value_type,
            "multiValued": bool(multi_valued),
            "documents": int(documents),
            "distinctValues": 0,
            "values": [],
            "remainingValues": 0,
        }
        if value_type == "number" and minimum is not None and maximum is not None:
            entry["range"] = {
                "min": float(minimum),
                "median": float(medians.get(key, (minimum + maximum) / 2.0)),
                "max": float(maximum),
            }
        types_by_key[str(key)].append(entry)

    values_by_type: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for key, value_type, text, number, boolean, documents in value_rows:
        values_by_type.setdefault((str(key), value_type), []).append(
            {
                "value": _typed_value(value_type, text, number, boolean),
                "documents": int(documents),
            }
        )

    for key, entries in types_by_key.items():
        for entry in entries:
            candidates = sorted(
                values_by_type.get((key, entry["type"]), []),
                key=lambda item: (-item["documents"], str(item["value"])),
            )
            entry["distinctValues"] = len(candidates)
            entry["values"] = candidates[:value_limit]
            entry["remainingValues"] = max(0, len(candidates) - len(entry["values"]))
        entries.sort(key=lambda entry: _TYPE_ORDER[entry["type"]])
    return [
        {"key": key, "documents": int(documents), "types": types_by_key[key]}
        for key, documents in key_rows
    ]


class MetadataValueRepository:
    """Typed kv rows for one document; mutations never commit (caller owns it).

    ``replace_from_canonical`` is delete-then-insert: the PK
    ``(document_id, key, ordinal)`` makes rebuilds idempotent, and the write
    runs on the caller's transaction so the kv view can never disagree with
    the document row it was derived from (D-05).
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        """Initialize the metadata value repository."""
        self.db = db

    def replace_from_canonical(self, document_id: str, canonical_json: str) -> tuple[int, int]:
        """Rebuild one document's typed rows and skips from canonical JSON.

        Returns ``(rows_written, keys_skipped)``. Never commits.
        """
        rows, skipped = typed_rows(canonical_json)
        self.delete_by_document(document_id)
        if rows:
            self.db.executemany(
                """
                INSERT INTO document_metadata_values (
                    document_id, key, ordinal, value_type,
                    text_value, number_value, boolean_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        document_id,
                        row.key,
                        row.ordinal,
                        row.value_type,
                        row.text_value,
                        row.number_value,
                        row.boolean_value,
                    )
                    for row in rows
                ],
            )
        if skipped:
            self.db.executemany(
                """
                INSERT INTO document_metadata_skips (document_id, key, reason)
                VALUES (?, ?, ?)
                """,
                [(document_id, skip.key, skip.reason) for skip in skipped],
            )
        return len(rows), len(skipped)

    def delete_by_document(self, document_id: str) -> int:
        """Delete one document's typed rows and skips; returns value rows removed."""
        cursor = self.db.execute(
            "DELETE FROM document_metadata_values WHERE document_id = ?",
            (document_id,),
        )
        removed = cursor.rowcount
        self.db.execute(
            "DELETE FROM document_metadata_skips WHERE document_id = ?",
            (document_id,),
        )
        return removed

    def discover(  # noqa: PLR0913 — one keyword per the frozen D-15 input contract
        self,
        *,
        collection_ids: list[str] | None,
        filter_predicate: tuple[str, list[Any]] | None,
        match_predicate: tuple[str, list[Any]] | None,
        min_count: int = 1,
        sort: str = "count",
        limit: int = 50,
        value_limit: int = 10,
    ) -> dict[str, Any]:
        """Report what metadata exists, over the same store the filters read (D-16).

        The caller compiles the predicates (this layer never imports the
        compiler): ``compile_filter(node, alias="d", scope="corpus")`` for the
        filter and ``compile_match(node, alias="mv")`` for the entry-scope
        match. An absent filter or match MUST be passed as ``None`` — a
        non-``None`` empty fragment would falsely signal a supplied filter and
        leak ``filteredDocuments`` into the no-filter envelope.

        Envelope (frozen Phase 22 contract, D-15 + D-20): ``documents`` is the
        scope denominator (collection predicate only — never narrowed by the
        filter); ``filteredDocuments`` is present only when a filter was
        supplied; ``totalKeys``/``remainingKeys`` window the frontmatter key
        list; ``skippedKeys`` counts D-07 skips in the region; ``builtIns``
        always carries exactly ``path`` then ``mtime`` computed from the
        ``documents`` columns over the same filter-aware region, never from
        ``document_metadata_values`` and never counted in ``keys``/
        ``totalKeys``. ``match`` narrows only the frontmatter entries.

        Every aggregate is bounded: at most the page's keys are aggregated and
        each type's values are windowed at ``value_limit`` with an exact
        remainder. Median positions use integer division so odd cohorts yield
        one row and even cohorts two; the midpoint is computed in Python.
        """
        collection_sql, collection_params = _collection_clause(collection_ids)
        filter_sql = ""
        filter_params: list[Any] = []
        if filter_predicate is not None:
            predicate, filter_params = filter_predicate
            filter_sql = f" AND {predicate}"
        match_sql = ""
        match_params: list[Any] = []
        if match_predicate is not None:
            predicate, match_params = match_predicate
            match_sql = f" AND {predicate}"
        query = _DiscoveryQuery(
            region=(
                "WITH region AS (SELECT d.id AS id, d.path AS path, d.mtime AS mtime "
                f"FROM documents d WHERE 1 = 1 {collection_sql}{filter_sql})"
            ),
            scope_params=[*collection_params, *filter_params],
            match_sql=match_sql,
            match_params=list(match_params),
        )

        documents = self._count(
            f"SELECT COUNT(*) FROM documents d WHERE 1 = 1 {collection_sql}",
            collection_params,
        )
        result: dict[str, Any] = {"documents": documents}
        if filter_predicate is not None:
            result["filteredDocuments"] = self._count(
                f"SELECT COUNT(*) FROM documents d WHERE 1 = 1 {collection_sql}{filter_sql}",
                query.scope_params,
            )

        total_keys = self._count(
            f"{query.region} SELECT COUNT(DISTINCT mv.key) FROM document_metadata_values mv "
            f"JOIN region r ON mv.document_id = r.id WHERE 1 = 1{query.match_sql}",
            [*query.scope_params, *query.match_params],
        )
        order = "documents DESC, key ASC" if sort == "count" else "key ASC"
        key_rows = self.db.execute(
            f"{query.region} SELECT mv.key AS key, "
            f"COUNT(DISTINCT mv.document_id) AS documents "
            f"FROM document_metadata_values mv JOIN region r ON mv.document_id = r.id "
            f"WHERE 1 = 1{query.match_sql} GROUP BY mv.key ORDER BY {order} LIMIT ?",
            [*query.scope_params, *query.match_params, limit],
        ).fetchall()
        keys = [str(row[0]) for row in key_rows]
        type_rows, value_rows, medians = self._key_aggregates(query, keys, min_count)

        result["totalKeys"] = total_keys
        result["remainingKeys"] = max(0, total_keys - len(keys))
        result["skippedKeys"] = self._count(
            f"{query.region} SELECT COUNT(*) FROM document_metadata_skips s "
            f"JOIN region r ON s.document_id = r.id",
            query.scope_params,
        )
        result["builtIns"] = self._built_in_entries(query)
        result["keys"] = _key_entries(key_rows, type_rows, value_rows, medians, value_limit)
        return result

    def _count(self, sql: str, params: list[Any]) -> int:
        """Run one ``COUNT(*)``-shaped statement and return its integer result."""
        row = self.db.execute(sql, params).fetchone()
        return int(row[0]) if row is not None else 0

    def _key_aggregates(
        self, query: _DiscoveryQuery, keys: list[str], min_count: int
    ) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]], dict[str, float]]:
        """Batch the page's type split, value counts, and numeric medians."""
        if not keys:
            return [], [], {}
        placeholders = ", ".join(["?"] * len(keys))
        params = [*query.scope_params, *keys, *query.match_params]
        type_rows = self.db.execute(
            f"{query.region} SELECT mv.key, mv.value_type, "
            f"COUNT(DISTINCT mv.document_id), MAX(mv.ordinal) > 0, "
            f"MIN(mv.number_value), MAX(mv.number_value) "
            f"FROM document_metadata_values mv JOIN region r ON mv.document_id = r.id "
            f"WHERE mv.key IN ({placeholders}){query.match_sql} "
            f"GROUP BY mv.key, mv.value_type",
            params,
        ).fetchall()
        value_rows = self.db.execute(
            f"{query.region} SELECT mv.key, mv.value_type, mv.text_value, "
            f"mv.number_value, mv.boolean_value, COUNT(DISTINCT mv.document_id) "
            f"FROM document_metadata_values mv JOIN region r ON mv.document_id = r.id "
            f"WHERE mv.key IN ({placeholders}){query.match_sql} "
            f"GROUP BY mv.key, mv.value_type, mv.text_value, mv.number_value, "
            f"mv.boolean_value HAVING COUNT(DISTINCT mv.document_id) >= ?",
            [*params, min_count],
        ).fetchall()
        numeric_keys = sorted({str(row[0]) for row in type_rows if row[1] == "number"})
        return type_rows, value_rows, self._medians(query, numeric_keys)

    def _medians(self, query: _DiscoveryQuery, keys: list[str]) -> dict[str, float]:
        """Exact medians over numeric VALUE rows (array elements each count)."""
        if not keys:
            return {}
        placeholders = ", ".join(["?"] * len(keys))
        rows = self.db.execute(
            f"{query.region} SELECT key, number_value FROM ("
            f"SELECT mv.key AS key, mv.number_value AS number_value, "
            f"ROW_NUMBER() OVER (PARTITION BY mv.key ORDER BY mv.number_value) AS position, "
            f"COUNT(*) OVER (PARTITION BY mv.key) AS total "
            f"FROM document_metadata_values mv JOIN region r ON mv.document_id = r.id "
            f"WHERE mv.value_type = 'number' AND mv.key IN ({placeholders}){query.match_sql}"
            f") WHERE position IN ((total + 1) / 2, (total + 2) / 2) "
            f"ORDER BY key, number_value",
            [*query.scope_params, *keys, *query.match_params],
        ).fetchall()
        positions: dict[str, list[float]] = {}
        for key, number in rows:
            positions.setdefault(str(key), []).append(float(number))
        return {key: _median(values) for key, values in positions.items()}

    def _built_in_entries(self, query: _DiscoveryQuery) -> list[dict[str, Any]]:
        """The fixed D-20 ``builtIns`` list: ``path`` then ``mtime`` (D-03).

        Both are computed from the ``documents`` columns over the same
        filter-aware region, never from the typed store, so a frontmatter key
        with either reserved name can never masquerade as a built-in. Each
        reports no inline values (``remainingValues == distinctValues``).
        """
        row = self.db.execute(
            f"{query.region} SELECT COUNT(*), COUNT(DISTINCT path), COUNT(DISTINCT mtime), "
            f"MIN(mtime), MAX(mtime) FROM region",
            query.scope_params,
        ).fetchone()
        documents = int(row[0]) if row is not None else 0
        path_values = int(row[1]) if row is not None else 0
        mtime_values = int(row[2]) if row is not None else 0
        path_type: dict[str, Any] = {
            "type": "string",
            "multiValued": False,
            "documents": documents,
            "distinctValues": path_values,
            "values": [],
            "remainingValues": path_values,
        }
        mtime_type: dict[str, Any] = {
            "type": "number",
            "multiValued": False,
            "documents": documents,
            "distinctValues": mtime_values,
            "values": [],
            "remainingValues": mtime_values,
        }
        if documents and row is not None and row[3] is not None and row[4] is not None:
            mtime_type["range"] = {
                "min": float(row[3]),
                "median": self._mtime_median(query),
                "max": float(row[4]),
            }
        return [
            {"key": "path", "documents": documents, "types": [path_type]},
            {"key": "mtime", "documents": documents, "types": [mtime_type]},
        ]

    def _mtime_median(self, query: _DiscoveryQuery) -> float:
        """Median of the region's ``mtime`` values (same integer-division shape)."""
        rows = self.db.execute(
            f"{query.region} SELECT mtime FROM ("
            f"SELECT mtime, ROW_NUMBER() OVER (ORDER BY mtime) AS position, "
            f"COUNT(*) OVER () AS total FROM region"
            f") WHERE position IN ((total + 1) / 2, (total + 2) / 2)",
            query.scope_params,
        ).fetchall()
        return _median([float(row[0]) for row in rows])
