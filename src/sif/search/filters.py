"""Compile the metadata filter AST into parameterized SQL predicates (Phase 20).

The compiler is the only place that knows the typed key-value table shape and
the ``documents`` columns. Fragments are appended to an existing ``WHERE``:
search legs use ``scope="candidates"`` (a correlated ``EXISTS`` probe per
candidate document), while the selectivity pre-count and discovery coverage
use ``scope="corpus"`` (an uncorrelated ``IN (SELECT document_id ...)`` that
SQLite evaluates once).

Parameterization contract (T-20-01): identifiers, aliases, table names, and
``?, `` placeholder lists are the only interpolated text; every operand is
bound. A ``None`` filter is the ONLY unfiltered signal — any non-``None`` AST
compiles to a non-empty predicate, so an empty match set returns zero rows
instead of silently degrading to "no filter".
"""

from __future__ import annotations

import sqlite3
from typing import Any, Literal

from sif.core.filters import Condition, Eq, FilterNode, FilterValidationError


_KV_TABLE = "document_metadata_values"
_TYPED_COLUMNS = {
    "string": "text_value",
    "number": "number_value",
    "boolean": "boolean_value",
}


def _operator_name(condition: Condition) -> str:
    """Return the concrete condition's operator tag for error messages."""
    return str(getattr(condition, "operator", "?"))


def _pin_operand(condition: Condition) -> tuple[str, Any]:
    """Resolve a scalar operand to ``(value_type, bound_value)``.

    Typed exact match with no coercion (D-10): ``bool`` is checked before
    ``int`` so ``True`` is never stored or compared as a number, and strings
    never compare against numeric columns.
    """
    value = condition.value
    if isinstance(value, bool):
        return "boolean", int(value)
    if isinstance(value, (int, float)):
        return "number", value
    if isinstance(value, str):
        return "string", value
    raise FilterValidationError(
        condition.field,
        f'"{_operator_name(condition)}" does not accept {type(value).__name__} values',
    )


def _inner_condition(condition: Condition, params: list[Any]) -> str:
    """Return the ``mv``-scoped predicate for one leaf, appending bound params."""
    if isinstance(condition, Eq):
        value_type, bound = _pin_operand(condition)
        params.extend([condition.field, value_type, bound])
        column = _TYPED_COLUMNS[value_type]
        return f"mv.key = ? AND mv.value_type = ? AND mv.{column} = ?"
    raise FilterValidationError(
        condition.field,
        f'"{_operator_name(condition)}" has no compiled form',
    )


def _wrap_scope(inner: str, alias: str, scope: str) -> str:
    """Wrap a leaf predicate in the scope's kv-table probe."""
    if scope == "corpus":
        return f"{alias}.id IN (SELECT mv.document_id FROM {_KV_TABLE} mv WHERE {inner})"
    return f"EXISTS (SELECT 1 FROM {_KV_TABLE} mv WHERE mv.document_id = {alias}.id AND {inner})"


def compile_filter(
    node: FilterNode | None,
    alias: str = "d",
    scope: Literal["candidates", "corpus"] = "candidates",
) -> tuple[str, list[Any]]:
    """Compile a filter AST into ``(sql_fragment, params)``.

    ``None`` returns ``("", [])``. Every non-``None`` AST returns a non-empty
    predicate; params are appended in SQL order.
    """
    if node is None:
        return "", []
    params: list[Any] = []
    return _wrap_scope(_inner_condition(node, params), alias, scope), params


def _collection_predicate(
    collection_ids: list[str] | None, alias: str = "d"
) -> tuple[str, list[Any]]:
    """Build the collection scope predicate (``None`` = unfiltered)."""
    if not collection_ids:
        return "", []
    placeholders = ", ".join(["?"] * len(collection_ids))
    return f"AND {alias}.collection_id IN ({placeholders})", list(collection_ids)


def count_matching_documents(
    db: sqlite3.Connection,
    filter_node: FilterNode | None,
    collection_ids: list[str] | None,
) -> int:
    """Count documents admitted by the filter and collection scope (D-08).

    The compiled filter uses corpus scope so SQLite evaluates the kv lookup
    once. The collection predicate is part of the count so the selectivity
    estimate is the true admitted set, not the whole corpus.
    """
    if collection_ids is not None and not collection_ids:
        return 0
    if filter_node is None:
        return count_documents_in_scope(db, collection_ids)

    predicate, filter_params = compile_filter(filter_node, alias="d", scope="corpus")
    collection_predicate, collection_params = _collection_predicate(collection_ids)
    sql = f"SELECT COUNT(*) FROM documents d WHERE 1 = 1 {collection_predicate} AND {predicate}"
    row = db.execute(sql, [*collection_params, *filter_params]).fetchone()
    return int(row[0])


def count_documents_in_scope(
    db: sqlite3.Connection,
    collection_ids: list[str] | None,
) -> int:
    """Count documents in the collection scope (the pre-count denominator)."""
    if collection_ids is not None and not collection_ids:
        return 0
    predicate, params = _collection_predicate(collection_ids)
    row = db.execute(f"SELECT COUNT(*) FROM documents d WHERE 1 = 1 {predicate}", params).fetchone()
    return int(row[0])


def count_vectors_in_scope(
    db: sqlite3.Connection,
    collection_ids: list[str] | None,
) -> int:
    """Count stored chunk vectors in the collection scope (D-08 ceiling test)."""
    if collection_ids is not None and not collection_ids:
        return 0
    predicate, params = _collection_predicate(collection_ids)
    row = db.execute(
        "SELECT COUNT(*) FROM document_embeddings de "
        f"JOIN documents d ON de.document_id = d.id WHERE 1 = 1 {predicate}",
        params,
    ).fetchone()
    return int(row[0])
