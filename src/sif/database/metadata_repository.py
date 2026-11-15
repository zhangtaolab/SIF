"""Typed metadata derivation and the key-value store repository (Phase 20, D-05/D-07).

Typed rows are derived from the **canonical JSON string**, never from the
in-memory metadata dict: ``canonical_metadata_json`` uses ``default=str``, so
a YAML date is an ISO string in the stored blob but a ``datetime`` object in
the live dict — deriving from different sources would make the live write path
and the backfill disagree (research Pitfall 3). ``DocumentRepository.create``
and ``.update`` already compute that string; the backfill reads it back from
``documents.metadata``.

Reserved built-in names (``path``/``mtime``, D-03) are shadowed here, at the
derived view, so discovery never reports them as frontmatter keys and the
compiler always resolves the built-in column. Shadowing is not a skip: the
name is reserved, not invalid.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


# D-03: exactly two reserved built-in fields. A frontmatter key with either
# name is shadowed (not filterable, not a skipped key).
RESERVED_FIELDS = frozenset({"path", "mtime"})

# D-07 skip reasons for keys that cannot enter the typed store.
SKIP_NESTED = "nested"
SKIP_NULL = "null"
SKIP_MIXED_ARRAY = "mixed_array"


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


def _scalar_row(key: str, ordinal: int, value: Any) -> TypedRow | None:
    """Map one scalar JSON value to a typed row; ``None`` for non-scalars.

    ``bool`` is checked before ``int`` because ``bool`` is an ``int`` subclass:
    ``True`` must never be stored or compared as a number (D-10).
    """
    if isinstance(value, bool):
        return TypedRow(key, ordinal, "boolean", boolean_value=int(value))
    if isinstance(value, (int, float)):
        return TypedRow(key, ordinal, "number", number_value=float(value))
    if isinstance(value, str):
        return TypedRow(key, ordinal, "string", text_value=value)
    return None


def _is_nested(value: Any) -> bool:
    """True for a value that is an object or contains one."""
    if isinstance(value, Mapping):
        return True
    if isinstance(value, list):
        return any(isinstance(item, (Mapping, list)) for item in value)
    return False


def filterable_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Return the metadata mapping minus the reserved built-in names.

    A shallow copy: values are not transformed here. The ``qmd.metadata``
    namespace merge is a storage-layer concern completed by plan 20-02.
    """
    return {str(key): value for key, value in metadata.items() if str(key) not in RESERVED_FIELDS}


def typed_rows(canonical_json: str) -> tuple[list[TypedRow], list[SkippedKey]]:
    """Derive typed rows and skipped keys from the canonical metadata JSON.

    Classification (D-07): ``bool`` -> boolean, ``int``/``float`` -> number,
    ``str`` -> string, and a flat homogeneous array -> one row per element
    with ``ordinal`` 0..n-1. Nested objects (and arrays containing them) are
    skipped as ``nested``; ``None`` as ``null``; mixed-type arrays as
    ``mixed_array``. The document still indexes and its other keys remain
    filterable.
    """
    raw = json.loads(canonical_json) if canonical_json else {}
    if not isinstance(raw, Mapping):
        return [], []

    rows: list[TypedRow] = []
    skipped: list[SkippedKey] = []
    for key, value in filterable_metadata(raw).items():
        if value is None:
            skipped.append(SkippedKey(key, SKIP_NULL))
            continue
        if _is_nested(value):
            skipped.append(SkippedKey(key, SKIP_NESTED))
            continue
        if isinstance(value, list):
            array_rows = [_scalar_row(key, ordinal, item) for ordinal, item in enumerate(value)]
            if any(row is None for row in array_rows):
                # A None inside a flat array (or an unsupported element) makes
                # the whole key un-typed rather than partially typed.
                skipped.append(SkippedKey(key, SKIP_MIXED_ARRAY))
                continue
            rows.extend(row for row in array_rows if row is not None)
            continue
        row = _scalar_row(key, 0, value)
        if row is None:
            skipped.append(SkippedKey(key, SKIP_MIXED_ARRAY))
            continue
        rows.append(row)

    return rows, skipped


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
