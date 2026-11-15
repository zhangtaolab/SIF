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

Typed semantics (D-10/D-11):
- ``eq``/``ne`` pin the operand's ``value_type``; there is no coercion.
- ``ne``/``nin`` compile as *presence* (a same-type value exists) AND the
  negation of the equality probe — never a bare ``NOT IN``, which would match
  documents missing the key.
- ``gt``/``gte``/``lt``/``lte`` compare the numeric column only.
- ``caseInsensitive`` folds ASCII only, on both the compared column (SQLite's
  ``lower()``) and the bound operand (``_ascii_lower``).
- ``path``/``mtime`` are the two reserved built-ins (D-03); their comparisons
  resolve against the ``documents`` columns and are never wrapped in an
  ``EXISTS``. ``path`` prefixes compile to a half-open range so
  ``idx_documents_path`` is usable (never ``LIKE``).
"""

from __future__ import annotations

import math
import sqlite3
from collections.abc import Callable
from typing import Any, Literal, NoReturn, cast

from sif.core.filters import (
    All,
    And,
    Condition,
    Contains,
    Eq,
    Exists,
    FilterNode,
    FilterValidationError,
    Gt,
    Gte,
    In,
    Lt,
    Lte,
    Ne,
    Nin,
    Not,
    Or,
    Prefix,
    Suffix,
    TypeCondition,
)


_KV_TABLE = "document_metadata_values"
_TYPED_COLUMNS = {
    "string": "text_value",
    "number": "number_value",
    "boolean": "boolean_value",
}
_ORDERING_SQL = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
_PATH_PREFIX_SENTINEL = "\U0010ffff"

# ASCII-only folding: never str.lower(), which folds non-ASCII (D-10). SQLite's
# built-in lower() folds ASCII only, so both sides of a comparison agree.
_ASCII_FOLD = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def _ascii_lower(value: str) -> str:
    """Fold ``A``-``Z`` to ``a``-``z`` and nothing else."""
    return value.translate(_ASCII_FOLD)


def _operator_name(node: Any) -> str:
    """Return a concrete node's operator tag for error messages."""
    return str(getattr(node, "operator", "?"))


def _compiler_error_path(node: Any) -> str:
    """Field-and-operator path for a compiler-time rejection (D-17 style)."""
    return f"{getattr(node, 'field', '?')}.{_operator_name(node)}"


def _reject(node: Any, reason: str) -> NoReturn:
    """Raise a field-and-operator addressed FilterValidationError."""
    raise FilterValidationError(_compiler_error_path(node), f'"{_operator_name(node)}" {reason}')


def _value_type_of(node: Condition, value: Any) -> str:
    """Map one operand to its typed-store category (bool before number)."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            _reject(node, "requires a finite numeric value")
        return "number"
    if isinstance(value, str) and value != "":
        return "string"
    _reject(node, f"does not accept {type(value).__name__} values")


def _pin_scalar(node: Condition) -> tuple[str, Any]:
    """Resolve a scalar operand to ``(value_type, bound_value)``."""
    value_type = _value_type_of(node, node.value)
    if value_type == "boolean":
        return "boolean", int(cast("bool", node.value))
    return value_type, node.value


def _pin_membership(node: Condition) -> tuple[str, list[Any]]:
    """Resolve a membership operand to ``(value_type, bound_values)``.

    Every element must share one category; the validator rejects mixed raw
    types, so this is the defensive backstop for directly-constructed ASTs.
    """
    values = node.value
    if not isinstance(values, list) or not values:
        _reject(node, "requires a non-empty homogeneous list")
    categories = [_value_type_of(node, element) for element in values]
    if len(set(categories)) != 1:
        _reject(node, "requires a non-empty homogeneous list")
    category = categories[0]
    if category == "boolean":
        return category, [int(element) for element in values]
    return category, list(values)


def _require_text(node: Condition) -> str:
    """Require a non-empty string operand."""
    value = node.value
    if not isinstance(value, str) or value == "":
        _reject(node, "requires a non-empty string value")
    return value


def _require_text_list(node: Condition) -> list[str]:
    """Require a non-empty homogeneous ``list[str]`` operand."""
    values = node.value
    if (
        not isinstance(values, list)
        or not values
        or not all(isinstance(element, str) and element != "" for element in values)
    ):
        _reject(node, "requires a non-empty string list")
    return cast("list[str]", values)


def _require_number(node: Condition) -> int | float:
    """Require a finite int/float operand (``bool`` is never a number)."""
    value = node.value
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        _reject(node, "requires a numeric value")
    if not math.isfinite(value):
        _reject(node, "requires a finite numeric value")
    return value


def _require_number_list(node: Condition) -> list[int | float]:
    """Require a non-empty homogeneous numeric list operand."""
    values = node.value
    if not isinstance(values, list) or not values:
        _reject(node, "requires a non-empty numeric list")
    if not all(
        isinstance(element, (int, float)) and not isinstance(element, bool) for element in values
    ):
        _reject(node, "requires a non-empty numeric list")
    return cast("list[int | float]", values)


def _placeholders(count: int) -> str:
    """Render ``?, ?, ...`` for ``count`` bound values."""
    return ", ".join(["?"] * count)


def _byte_length(text: str) -> int:
    """UTF-8 byte length, matching the BLOB ``substr`` semantics."""
    return len(text.encode("utf-8"))


def _wrap(inner: str, alias: str, scope: str, *, negative: bool = False) -> str:
    """Wrap a kv-row predicate in the scope's probe against ``alias``."""
    if scope == "corpus":
        operator = "NOT IN" if negative else "IN"
        return f"{alias}.id {operator} (SELECT mv.document_id FROM {_KV_TABLE} mv WHERE {inner})"
    prefix = "NOT EXISTS" if negative else "EXISTS"
    return f"{prefix} (SELECT 1 FROM {_KV_TABLE} mv WHERE mv.document_id = {alias}.id AND {inner})"


# ---------------------------------------------------------------------------
# Typed kv predicates, shared by the document scopes and the entry-scope match
# compiler. ``include_key`` is False for a match ``value`` entry, whose key is
# the row itself.
# ---------------------------------------------------------------------------


def _eq_inner(node: Condition, row: str, params: list[Any], *, include_key: bool) -> str:
    """Equality probe on one typed kv row."""
    value_type, bound = _pin_scalar(node)
    column = _TYPED_COLUMNS[value_type]
    if include_key:
        params.append(node.field)
    params.append(value_type)
    if value_type == "string" and node.caseInsensitive:
        params.append(_ascii_lower(bound))
        text = f"lower({row}.text_value) = ?"
    else:
        params.append(bound)
        text = f"{row}.{column} = ?"
    prefix = f"{row}.key = ? AND " if include_key else ""
    return f"{prefix}{row}.value_type = ? AND {text}"


def _presence_inner(row: str, *, include_key: bool) -> str:
    """Same-type presence probe: a value of the operand's type exists."""
    prefix = f"{row}.key = ? AND " if include_key else ""
    return f"{prefix}{row}.value_type = ?"


def _in_inner(
    node: Condition, row: str, params: list[Any], *, include_key: bool, negative: bool
) -> str:
    """Membership probe on one typed kv row."""
    category, values = _pin_membership(node)
    placeholders = _placeholders(len(values))
    if category == "string" and node.caseInsensitive:
        column_expr = f"lower({row}.text_value)"
        bound_values = [_ascii_lower(value) for value in values]
    else:
        column_expr = f"{row}.{_TYPED_COLUMNS[category]}"
        bound_values = values
    operator = "NOT IN" if negative else "IN"
    prefix = f"{row}.key = ? AND " if include_key else ""
    if include_key:
        params.append(node.field)
    params.append(category)
    params.extend(bound_values)
    return f"{prefix}{row}.value_type = ? AND {column_expr} {operator} ({placeholders})"


def _contains_operand(node: Condition) -> list[str]:
    """Return the ``contains`` operand as a list of non-empty strings."""
    value = node.value
    if isinstance(value, str) and value != "":
        return [value]
    if (
        isinstance(value, list)
        and value
        and all(isinstance(element, str) and element != "" for element in value)
    ):
        return cast("list[str]", value)
    _reject(node, "requires a non-empty string or string list")


def _contains_element_inner(
    node: Condition, text: str, row: str, params: list[Any], *, include_key: bool
) -> str:
    """One substring probe (``instr``) on a typed kv row."""
    operand = _ascii_lower(text) if node.caseInsensitive else text
    column_expr = f"lower({row}.text_value)" if node.caseInsensitive else f"{row}.text_value"
    prefix = f"{row}.key = ? AND " if include_key else ""
    if include_key:
        params.append(node.field)
    params.extend(["string", operand])
    return f"{prefix}{row}.value_type = ? AND instr({column_expr}, ?) > 0"


def _affix_inner(
    node: Condition, row: str, params: list[Any], *, include_key: bool, suffix: bool
) -> str:
    """BLOB ``substr`` prefix/suffix probe on one typed kv row."""
    text = _require_text(node)
    operand = _ascii_lower(text) if node.caseInsensitive else text
    column_expr = f"lower({row}.text_value)" if node.caseInsensitive else f"{row}.text_value"
    prefix = f"{row}.key = ? AND " if include_key else ""
    if include_key:
        params.append(node.field)
    params.extend(["string", _byte_length(operand), operand])
    if suffix:
        return (
            f"{prefix}{row}.value_type = ? AND "
            f"substr(CAST({column_expr} AS BLOB), -?) = CAST(? AS BLOB)"
        )
    return (
        f"{prefix}{row}.value_type = ? AND "
        f"substr(CAST({column_expr} AS BLOB), 1, ?) = CAST(? AS BLOB)"
    )


def _type_inner(node: Condition, row: str, params: list[Any], *, include_key: bool) -> str:
    """Value-type probe on one typed kv row."""
    value = node.value
    if not isinstance(value, str) or value not in _TYPED_COLUMNS:
        _reject(node, "requires one of string, number, boolean")
    prefix = f"{row}.key = ? AND " if include_key else ""
    if include_key:
        params.append(node.field)
    params.append(value)
    return f"{prefix}{row}.value_type = ?"


# ---------------------------------------------------------------------------
# Document-scope kv compilation (EXISTS / IN wrapping).
# ---------------------------------------------------------------------------


def _kv_eq(node: Condition, alias: str, scope: str, params: list[Any]) -> str:
    return _wrap(_eq_inner(node, "mv", params, include_key=True), alias, scope)


def _kv_ne(node: Condition, alias: str, scope: str, params: list[Any]) -> str:
    """Presence of a same-type value AND no equal value (never bare NOT IN)."""
    value_type, _ = _pin_scalar(node)
    params.extend([node.field, value_type])
    present = _wrap(_presence_inner("mv", include_key=True), alias, scope)
    equal = _wrap(_eq_inner(node, "mv", params, include_key=True), alias, scope, negative=True)
    return f"{present} AND {equal}"


def _kv_membership(
    node: Condition, alias: str, scope: str, params: list[Any], *, negative: bool
) -> str:
    if not negative:
        return _wrap(_in_inner(node, "mv", params, include_key=True, negative=False), alias, scope)
    value_type, _ = _pin_membership(node)
    params.extend([node.field, value_type])
    present = _wrap(_presence_inner("mv", include_key=True), alias, scope)
    excluded = _wrap(
        _in_inner(node, "mv", params, include_key=True, negative=False),
        alias,
        scope,
        negative=True,
    )
    return f"{present} AND {excluded}"


def _kv_all(node: Condition, alias: str, scope: str, params: list[Any]) -> str:
    """One equality probe per operand element, AND-ed (array-contains-every)."""
    values = node.value
    if not isinstance(values, list) or not values:
        _reject(node, "requires a non-empty homogeneous list")
    parts: list[str] = []
    for element in values:
        value_type = _value_type_of(node, element)
        bound = int(element) if value_type == "boolean" else element
        column = _TYPED_COLUMNS[value_type]
        if value_type == "string" and node.caseInsensitive:
            params.extend([node.field, value_type, _ascii_lower(cast("str", bound))])
            inner = "mv.key = ? AND mv.value_type = ? AND lower(mv.text_value) = ?"
        else:
            params.extend([node.field, value_type, bound])
            inner = f"mv.key = ? AND mv.value_type = ? AND mv.{column} = ?"
        parts.append(_wrap(inner, alias, scope))
    return f"({' AND '.join(parts)})"


def _kv_contains(node: Condition, alias: str, scope: str, params: list[Any]) -> str:
    parts = [
        _wrap(
            _contains_element_inner(node, text, "mv", params, include_key=True),
            alias,
            scope,
        )
        for text in _contains_operand(node)
    ]
    return parts[0] if len(parts) == 1 else f"({' OR '.join(parts)})"


def _kv_affix(node: Condition, alias: str, scope: str, params: list[Any], *, suffix: bool) -> str:
    return _wrap(_affix_inner(node, "mv", params, include_key=True, suffix=suffix), alias, scope)


def _kv_type(node: Condition, alias: str, scope: str, params: list[Any]) -> str:
    return _wrap(_type_inner(node, "mv", params, include_key=True), alias, scope)


def _kv_exists(node: Condition, alias: str, scope: str, params: list[Any]) -> str:
    value = node.value
    if not isinstance(value, bool):
        _reject(node, "requires a boolean value")
    params.append(node.field)
    return _wrap("mv.key = ?", alias, scope, negative=not value)


def _kv_ordering(node: Condition, alias: str, scope: str, params: list[Any]) -> str:
    params.extend([node.field, "number", _require_number(node)])
    operator = _ORDERING_SQL[_operator_name(node)]
    return _wrap(
        f"mv.key = ? AND mv.value_type = ? AND mv.number_value {operator} ?",
        alias,
        scope,
    )


def _kv_text(node: Condition, alias: str, scope: str, params: list[Any]) -> str:
    """Dispatch the three text operators over a typed kv value."""
    if isinstance(node, Contains):
        sql = _kv_contains(node, alias, scope, params)
    elif isinstance(node, Prefix):
        sql = _kv_affix(node, alias, scope, params, suffix=False)
    elif isinstance(node, Suffix):
        sql = _kv_affix(node, alias, scope, params, suffix=True)
    else:
        _reject(node, "has no compiled form")
    return sql


def _compile_kv(node: Condition, alias: str, scope: str, params: list[Any]) -> str:
    """Dispatch one non-built-in leaf to its typed kv compilation."""
    if isinstance(node, Eq):
        sql = _kv_eq(node, alias, scope, params)
    elif isinstance(node, Ne):
        sql = _kv_ne(node, alias, scope, params)
    elif isinstance(node, (Gt, Gte, Lt, Lte)):
        sql = _kv_ordering(node, alias, scope, params)
    elif isinstance(node, (In, Nin)):
        sql = _kv_membership(node, alias, scope, params, negative=isinstance(node, Nin))
    elif isinstance(node, All):
        sql = _kv_all(node, alias, scope, params)
    elif isinstance(node, (Contains, Prefix, Suffix)):
        sql = _kv_text(node, alias, scope, params)
    elif isinstance(node, TypeCondition):
        sql = _kv_type(node, alias, scope, params)
    elif isinstance(node, Exists):
        sql = _kv_exists(node, alias, scope, params)
    else:
        _reject(node, "has no compiled form")
    return sql


# ---------------------------------------------------------------------------
# Built-in fields (D-03): path (TEXT) and mtime (REAL).
# ---------------------------------------------------------------------------


def _builtin_type_sql(node: Condition, matching: str) -> str:
    """``type`` on a built-in: only the column's own type matches."""
    value = node.value
    if not isinstance(value, str) or value not in _TYPED_COLUMNS:
        _reject(node, "requires one of string, number, boolean")
    return "1 = 1" if value == matching else "0 = 1"


def _builtin_exists_sql(node: Condition) -> str:
    """``exists`` on a built-in: both reserved columns are NOT NULL."""
    value = node.value
    if not isinstance(value, bool):
        _reject(node, "requires a boolean value")
    return "1 = 1" if value else "0 = 1"


def _builtin_affix_sql(node: Condition, column: str, params: list[Any], *, suffix: bool) -> str:
    """BLOB ``substr`` prefix/suffix on a built-in text column."""
    text = _require_text(node)
    operand = _ascii_lower(text) if node.caseInsensitive else text
    column_expr = f"lower({column})" if node.caseInsensitive else column
    params.extend([_byte_length(operand), operand])
    if suffix:
        return f"substr(CAST({column_expr} AS BLOB), -?) = CAST(? AS BLOB)"
    return f"substr(CAST({column_expr} AS BLOB), 1, ?) = CAST(? AS BLOB)"


def _path_prefix_sql(node: Condition, column: str, params: list[Any]) -> str:
    """Half-open prefix range on ``path`` (never LIKE; uses idx_documents_path)."""
    text = _require_text(node)
    if node.caseInsensitive:
        lower_prefix = _ascii_lower(text)
        params.extend([lower_prefix, lower_prefix + _PATH_PREFIX_SENTINEL])
        return f"lower({column}) >= ? AND lower({column}) < ?"
    params.extend([text, text + _PATH_PREFIX_SENTINEL])
    return f"{column} >= ? AND {column} < ?"


def _path_text_sql(node: Condition, alias: str, params: list[Any]) -> str:
    """Compile a text comparison against the ``path`` column."""
    column = f"{alias}.path"
    if isinstance(node, (Eq, Ne)):
        text = _require_text(node)
        operator = "=" if isinstance(node, Eq) else "!="
        if node.caseInsensitive:
            params.append(_ascii_lower(text))
            sql = f"lower({column}) {operator} ?"
        else:
            params.append(text)
            sql = f"{column} {operator} ?"
    elif isinstance(node, (In, Nin)):
        values = _require_text_list(node)
        if node.caseInsensitive:
            params.extend([_ascii_lower(value) for value in values])
            compared = f"lower({column})"
        else:
            params.extend(values)
            compared = column
        operator = "NOT IN" if isinstance(node, Nin) else "IN"
        sql = f"{compared} {operator} ({_placeholders(len(values))})"
    elif isinstance(node, Contains):
        parts: list[str] = []
        for text in _contains_operand(node):
            operand = _ascii_lower(text) if node.caseInsensitive else text
            compared = f"lower({column})" if node.caseInsensitive else column
            params.append(operand)
            parts.append(f"instr({compared}, ?) > 0")
        sql = parts[0] if len(parts) == 1 else f"({' OR '.join(parts)})"
    elif isinstance(node, Prefix):
        sql = _path_prefix_sql(node, column, params)
    elif isinstance(node, Suffix):
        sql = _builtin_affix_sql(node, column, params, suffix=True)
    else:
        _reject(node, "has no compiled form on the path built-in")
    return sql


def _compile_path(node: Condition, alias: str, params: list[Any]) -> str:
    """Compile one ``path`` (reserved TEXT) comparison."""
    if isinstance(node, (Gt, Gte, Lt, Lte)):
        _reject(node, "does not support ordering on a text built-in")
    if isinstance(node, All):
        _reject(node, "is not available on a scalar built-in")
    if isinstance(node, TypeCondition):
        if node.caseInsensitive:
            _reject(node, "does not accept caseInsensitive")
        return _builtin_type_sql(node, "string")
    if isinstance(node, Exists):
        return _builtin_exists_sql(node)
    return _path_text_sql(node, alias, params)


def _mtime_comparison_sql(node: Condition, alias: str, params: list[Any]) -> str:
    """Compile a numeric comparison against the ``mtime`` column."""
    column = f"{alias}.mtime"
    if isinstance(node, (Eq, Ne)):
        operator = "=" if isinstance(node, Eq) else "!="
        params.append(_require_number(node))
        return f"{column} {operator} ?"
    if isinstance(node, (Gt, Gte, Lt, Lte)):
        params.append(_require_number(node))
        return f"{column} {_ORDERING_SQL[_operator_name(node)]} ?"
    if isinstance(node, (In, Nin)):
        values = _require_number_list(node)
        params.extend(values)
        operator = "NOT IN" if isinstance(node, Nin) else "IN"
        return f"{column} {operator} ({_placeholders(len(values))})"
    _reject(node, "has no compiled form on the mtime built-in")


def _compile_mtime(node: Condition, alias: str, params: list[Any]) -> str:
    """Compile one ``mtime`` (reserved REAL) comparison."""
    if node.caseInsensitive:
        _reject(node, "does not accept caseInsensitive on a numeric built-in")
    if isinstance(node, (Contains, Prefix, Suffix)):
        _reject(node, "is not available on a numeric built-in")
    if isinstance(node, All):
        _reject(node, "is not available on a scalar built-in")
    if isinstance(node, TypeCondition):
        return _builtin_type_sql(node, "number")
    if isinstance(node, Exists):
        return _builtin_exists_sql(node)
    return _mtime_comparison_sql(node, alias, params)


def _compile_leaf(node: FilterNode, alias: str, scope: str, params: list[Any]) -> str:
    """Compile one leaf: reserved built-ins resolve to ``documents`` columns."""
    condition = cast("Condition", node)
    if condition.field == "path":
        return _compile_path(condition, alias, params)
    if condition.field == "mtime":
        return _compile_mtime(condition, alias, params)
    return _compile_kv(condition, alias, scope, params)


_LeafCompiler = Callable[[Any, str, str, list[Any]], str]


def _compile_tree(
    node: FilterNode, alias: str, scope: str, params: list[Any], leaf: _LeafCompiler
) -> str:
    """Compile a node tree; groups are parenthesized AND/OR/NOT combinators."""
    if isinstance(node, And):
        parts = [_compile_tree(child, alias, scope, params, leaf) for child in node.operands]
        return f"({' AND '.join(parts)})" if parts else "0 = 1"
    if isinstance(node, Or):
        parts = [_compile_tree(child, alias, scope, params, leaf) for child in node.operands]
        return f"({' OR '.join(parts)})" if parts else "0 = 1"
    if isinstance(node, Not):
        return f"NOT ({_compile_tree(node.operand, alias, scope, params, leaf)})"
    return leaf(node, alias, scope, params)


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
    return _compile_tree(node, alias, scope, params, _compile_leaf), params


# ---------------------------------------------------------------------------
# Discovery entry-scope compiler (``--match``).
# ---------------------------------------------------------------------------


def _key_text_sql(node: Condition, alias: str, params: list[Any]) -> str:
    """Compile a text operator against the entry ``key`` column."""
    column = f"{alias}.key"
    if isinstance(node, (Eq, Ne)):
        text = _require_text(node)
        operator = "=" if isinstance(node, Eq) else "!="
        if node.caseInsensitive:
            params.append(_ascii_lower(text))
            sql = f"lower({column}) {operator} ?"
        else:
            params.append(text)
            sql = f"{column} {operator} ?"
    elif isinstance(node, (In, Nin)):
        values = _require_text_list(node)
        if node.caseInsensitive:
            params.extend([_ascii_lower(item) for item in values])
            compared = f"lower({column})"
        else:
            params.extend(values)
            compared = column
        operator = "NOT IN" if isinstance(node, Nin) else "IN"
        sql = f"{compared} {operator} ({_placeholders(len(values))})"
    elif isinstance(node, Contains):
        parts: list[str] = []
        for text in _contains_operand(node):
            operand = _ascii_lower(text) if node.caseInsensitive else text
            compared = f"lower({column})" if node.caseInsensitive else column
            params.append(operand)
            parts.append(f"instr({compared}, ?) > 0")
        sql = parts[0] if len(parts) == 1 else f"({' OR '.join(parts)})"
    elif isinstance(node, (Prefix, Suffix)):
        sql = _builtin_affix_sql(node, column, params, suffix=isinstance(node, Suffix))
    else:
        _reject(node, "has no compiled form in the match grammar")
    return sql


def _match_key_leaf(node: Condition, alias: str, params: list[Any]) -> str:
    """Compile a text ``key`` entry condition (never a value_type test)."""
    if isinstance(node, (Gt, Gte, Lt, Lte)):
        _reject(node, "is not available on field 'key'; a key is text")
    if isinstance(node, (All, Exists)):
        _reject(node, "is not available in the match grammar")
    if isinstance(node, TypeCondition):
        sql = _builtin_type_sql(node, "string")
    else:
        sql = _key_text_sql(node, alias, params)
    return sql


def _match_value_leaf(node: Condition, alias: str, params: list[Any]) -> str:
    """Compile a typed ``value`` entry condition against one entry row."""
    if isinstance(node, (All, Exists)):
        _reject(node, "is not available in the match grammar")
    if isinstance(node, Eq):
        sql = _eq_inner(node, alias, params, include_key=False)
    elif isinstance(node, Ne):
        value_type, bound = _pin_scalar(node)
        if value_type == "string" and node.caseInsensitive:
            params.extend([value_type, _ascii_lower(bound)])
            sql = f"{alias}.value_type = ? AND lower({alias}.text_value) != ?"
        else:
            params.extend([value_type, bound])
            sql = f"{alias}.value_type = ? AND {alias}.{_TYPED_COLUMNS[value_type]} != ?"
    elif isinstance(node, (Gt, Gte, Lt, Lte)):
        params.extend(["number", _require_number(node)])
        sql = (
            f"{alias}.value_type = ? AND {alias}.number_value "
            f"{_ORDERING_SQL[_operator_name(node)]} ?"
        )
    elif isinstance(node, (In, Nin)):
        sql = _in_inner(node, alias, params, include_key=False, negative=isinstance(node, Nin))
    elif isinstance(node, Contains):
        parts = [
            _contains_element_inner(node, text, alias, params, include_key=False)
            for text in _contains_operand(node)
        ]
        sql = parts[0] if len(parts) == 1 else f"({' OR '.join(parts)})"
    elif isinstance(node, (Prefix, Suffix)):
        sql = _affix_inner(node, alias, params, include_key=False, suffix=isinstance(node, Suffix))
    elif isinstance(node, TypeCondition):
        sql = _type_inner(node, alias, params, include_key=False)
    else:
        _reject(node, "has no compiled form in the match grammar")
    return sql


def _compile_match_leaf(node: Any, alias: str, _scope: str, params: list[Any]) -> str:
    """Compile one entry-scope leaf against ``key`` or ``value``."""
    condition = cast("Condition", node)
    if condition.field == "key":
        return _match_key_leaf(condition, alias, params)
    if condition.field == "value":
        return _match_value_leaf(condition, alias, params)
    _reject(condition, "has no compiled form in the match grammar")


def compile_match(node: FilterNode | None, alias: str = "mv") -> tuple[str, list[Any]]:
    """Compile the discovery ``--match`` grammar over one entry row.

    ``None`` returns ``("", [])``. Groups reuse the same combinators; a leaf
    compares ``{alias}.key`` (text operators) or the typed value columns.
    """
    if node is None:
        return "", []
    params: list[Any] = []
    return _compile_tree(node, alias, "", params, _compile_match_leaf), params


# ---------------------------------------------------------------------------
# Scoped document counts (selectivity pre-count, D-08).
# ---------------------------------------------------------------------------


def _collection_predicate(
    collection_ids: list[str] | None, alias: str = "d"
) -> tuple[str, list[Any]]:
    """Build the collection scope predicate (``None`` = unfiltered)."""
    if not collection_ids:
        return "", []
    placeholders = _placeholders(len(collection_ids))
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
