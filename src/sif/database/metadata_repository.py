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
    rows = [_typed_row(key, ordinal, item, value_type) for ordinal, item in enumerate(value)]
    return rows, None


def _classify_value(key: str, value: Any) -> tuple[list[TypedRow], str | None]:
    """Classify one resolved value; returns (rows, skip reason or ``None``).

    Rules 4-9 of :func:`typed_rows`, in order. ``None`` as the reason means the
    value is filterable; the rows may still be empty (an empty array).
    """
    if isinstance(value, Mapping) or _contains_mapping(value):
        return [], SKIP_NESTED
    if value is None:
        return [], SKIP_NULL
    if isinstance(value, list):
        return _classify_array(key, value)
    if isinstance(value, str) and len(value) > MAX_STRING_CHARS:
        return [], SKIP_CAP_STRING
    value_type = _scalar_type(value)
    if value_type is None:  # pragma: no cover - JSON scalar types are exhaustive
        return [], SKIP_MIXED_ARRAY
    return [_typed_row(key, 0, value, value_type)], None


def typed_rows(canonical_json: str) -> tuple[list[TypedRow], list[SkippedKey]]:
    """Derive typed rows and skipped keys from the canonical metadata JSON.

    The canonical string is the only input (D-05) and its ``sort_keys=True``
    order makes caps deterministic. Classification (D-07), in order:

    1. A >64 KB canonical blob skips every key as ``cap_frontmatter``
       (at most the first 64 recorded).
    2. Keys after the first 64 are skipped as ``cap_keys``.
    3. Keys over 128 bytes are skipped as ``cap_key``.
    4. Objects, and arrays containing an object, are skipped as ``nested``.
    5. ``None`` is skipped as ``null``.
    6. Arrays that are not flat homogeneous scalar lists (including arrays of
       arrays, and ``[true, 1]``-style mixes) are skipped as ``mixed_array``.
    7. Strings over 1024 characters are skipped as ``cap_string``.
    8. Arrays over 128 elements are skipped as ``cap_array``.
    9. Otherwise one row per scalar (``ordinal`` 0), or one row per array
       element (``ordinal`` 0..n-1) so arrays behave as sets.

    At most 64 skip rows are ever returned per document.
    """
    raw = json.loads(canonical_json) if canonical_json else {}
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
