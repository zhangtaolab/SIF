"""Metadata filter AST, validation, and budgets (Phase 20, FILT-01/FILT-02).

One pydantic discriminated union on ``operator`` is the single grammar shared
by the CLI ``--filter`` flag, the MCP search inputs, and the discovery
``--match`` grammar (D-10/D-18). The wire grammar is qmd-compatible and pinned
to the ``[Unreleased]`` era verified 2026-11-15 (``qmd@86d2365``): conditions
carry ``field`` (D-18), groups carry ``operands``, and ``not`` carries
``operand``. The module never knows SQL — compilation lives in
``sif.search.filters``.

Budgets (D-13) are enforced by an iterative raw-dict pre-walk *before* pydantic
recursion, so an over-budget payload reports the budget by name instead of
surfacing pydantic's ``recursion_loop`` at ~900 depth. Per-operator semantics
are validated against the RAW payload (not the coerced model) so a
``[true, 1]`` array is still recognised as mixed-type before pydantic's lax
``bool -> int`` coercion can hide it.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


# D-13: explicit AST budgets. Generous enough that no hand-written filter hits
# them; they are the only defense against a hostile or runaway agent-authored
# filter. There is deliberately no "unbounded" escape.
MAX_FILTER_DEPTH = 8
MAX_FILTER_NODES = 64
MAX_FILTER_STRING = 1024
MAX_FILTER_ARRAY = 128
MAX_FILTER_FIELD_BYTES = 128

# All 17 qmd operators (D-10/D-18): 14 conditions + 3 groups.
_OPERATOR_TAGS = frozenset(
    {
        "and",
        "or",
        "not",
        "eq",
        "ne",
        "gt",
        "gte",
        "lt",
        "lte",
        "in",
        "nin",
        "all",
        "contains",
        "prefix",
        "suffix",
        "type",
        "exists",
    }
)
_GROUP_OPERATORS = frozenset({"and", "or", "not"})
_MEMBERSHIP_OPERATORS = frozenset({"in", "nin", "all"})
_TYPE_VALUES = frozenset({"string", "number", "boolean"})
# Operators whose operand is compared against an ``mtime`` value and may
# therefore carry an ISO-8601 string normalized to epoch seconds (D-12).
_MTIME_TEXT_OPERATORS = frozenset({"eq", "ne", "gt", "gte", "lt", "lte", "in", "nin"})
# D-03 reserved-field compatibility (WR-02): the compiler owns SQL and rejects
# these pairings defensively, but the shared grammar must reject them first so
# every surface reports the same ``filter.<field>.<operator>`` user error.
_RESERVED_FIELDS = frozenset({"path", "mtime"})
_ORDERING_OPERATORS = frozenset({"gt", "gte", "lt", "lte"})
_TEXT_OPERATORS = frozenset({"contains", "prefix", "suffix"})


class FilterValidationError(Exception):
    """Invalid filter input, addressed by its dotted path inside the AST.

    ``str()`` renders ``filter.<path>: <message>`` for nested errors and
    ``filter: <message>`` for root errors (D-17: name the operator, the
    field, and the path).
    """

    def __init__(self, path: str, message: str) -> None:
        """Store the AST path and message; render the user-facing form."""
        self.path = path
        self.message = message
        location = f"filter.{path}" if path else "filter"
        super().__init__(f"{location}: {message}")


class _Node(BaseModel):
    """Base node: unknown properties are rejected (qmd parity)."""

    model_config = ConfigDict(extra="forbid")


class Condition(_Node):
    """A leaf condition: ``field`` + ``operator`` + ``value`` (+ optional flag).

    ``value`` is intentionally permissive at the shape layer; per-operator
    semantics (numeric-only ordering, non-empty text operands, homogeneous
    membership lists) are validated against the raw payload so every violation
    carries its dotted AST path.
    """

    field: str = Field(min_length=1, max_length=MAX_FILTER_FIELD_BYTES)
    value: str | int | float | bool | list[str] | list[int] | list[float] | list[bool]
    # D-10: ASCII-only case folding for string / string-array operands.
    caseInsensitive: bool | None = None  # noqa: N815


class Eq(Condition):
    """Typed exact match (D-10: no coercion)."""

    operator: Literal["eq"]


class Ne(Condition):
    """Typed exact non-match; missing keys do not match (presence-aware)."""

    operator: Literal["ne"]


class Gt(Condition):
    """Numeric-only greater-than (D-11)."""

    operator: Literal["gt"]


class Gte(Condition):
    """Numeric-only greater-or-equal (D-11)."""

    operator: Literal["gte"]


class Lt(Condition):
    """Numeric-only less-than (D-11)."""

    operator: Literal["lt"]


class Lte(Condition):
    """Numeric-only less-or-equal (D-11)."""

    operator: Literal["lte"]


class In(Condition):
    """Scalar membership in a non-empty homogeneous list."""

    operator: Literal["in"]


class Nin(Condition):
    """Scalar non-membership; missing keys do not match (presence-aware)."""

    operator: Literal["nin"]


class All(Condition):
    """Array-contains-every-operand: the stored array is a set."""

    operator: Literal["all"]


class Contains(Condition):
    """Substring on a string, evaluated per element (substring-any) on arrays."""

    operator: Literal["contains"]


class Prefix(Condition):
    """String prefix match."""

    operator: Literal["prefix"]


class Suffix(Condition):
    """String suffix match."""

    operator: Literal["suffix"]


class TypeCondition(Condition):
    """Value-type test: ``string``, ``number``, or ``boolean``."""

    operator: Literal["type"]


class Exists(Condition):
    """Key-presence test."""

    operator: Literal["exists"]


class And(_Node):
    """Conjunction of one or more operand nodes."""

    operator: Literal["and"]
    operands: list[FilterNode]


class Or(_Node):
    """Disjunction of one or more operand nodes."""

    operator: Literal["or"]
    operands: list[FilterNode]


class Not(_Node):
    """Negation of a single operand node."""

    operator: Literal["not"]
    operand: FilterNode


FilterNode = Annotated[
    Eq
    | Ne
    | Gt
    | Gte
    | Lt
    | Lte
    | In
    | Nin
    | All
    | Contains
    | Prefix
    | Suffix
    | TypeCondition
    | Exists
    | And
    | Or
    | Not,
    Field(discriminator="operator"),
]

And.model_rebuild()
Or.model_rebuild()
Not.model_rebuild()

_FILTER: TypeAdapter[Any] = TypeAdapter(FilterNode)


def _check_budgets(raw: Any) -> None:
    """Enforce the D-13 budgets on the raw payload before pydantic recursion.

    Iterative by design: a recursive walk would itself raise ``RecursionError``
    on the inputs the budget exists to reject. Depth, node count, string
    operand length, and array operand length are checked here.
    """
    if not isinstance(raw, dict):
        raise FilterValidationError("", "a filter node must be an object")

    stack: list[tuple[Any, int]] = [(raw, 1)]
    nodes = 0
    while stack:
        node, depth = stack.pop()
        if not isinstance(node, dict):
            raise FilterValidationError("", "a filter node must be an object")
        nodes += 1
        if nodes > MAX_FILTER_NODES:
            raise FilterValidationError("", f"filter exceeds the {MAX_FILTER_NODES}-node budget")
        if depth > MAX_FILTER_DEPTH:
            raise FilterValidationError(
                "", f"filter exceeds the maximum nesting depth of {MAX_FILTER_DEPTH}"
            )
        value = node.get("value")
        if isinstance(value, str) and len(value) > MAX_FILTER_STRING:
            raise FilterValidationError(
                "",
                f"filter exceeds the maximum string operand length of {MAX_FILTER_STRING}",
            )
        if isinstance(value, list) and len(value) > MAX_FILTER_ARRAY:
            raise FilterValidationError(
                "",
                f"filter exceeds the maximum array operand length of {MAX_FILTER_ARRAY}",
            )
        children = _raw_children(node)
        stack.extend((child, depth + 1) for child in children)


def _raw_children(node: dict[str, Any]) -> list[Any]:
    """Return a raw node's child nodes (group operands or a single operand)."""
    operands = node.get("operands")
    if isinstance(operands, list):
        return operands
    if "operand" in node:
        return [node["operand"]]
    return []


def _pydantic_error_to_filter_error(exc: ValidationError) -> FilterValidationError:
    """Convert a pydantic error into the project's path-addressed form.

    Pydantic's ``loc`` tuple is joined with dots (e.g.
    ``and.operands.0.eq.value``); the message names the offending operator and
    property so a caller can self-correct without seeing pydantic internals.
    """
    error = exc.errors()[0]
    loc = tuple(error.get("loc", ()))
    path = ".".join(str(part) for part in loc)
    message = str(error.get("msg", "invalid filter"))

    operator = next(
        (part for part in reversed(loc) if isinstance(part, str) and part in _OPERATOR_TAGS),
        None,
    )
    prop = loc[-1] if loc and isinstance(loc[-1], str) else None
    details: list[str] = []
    if operator is not None:
        details.append(f'"{operator}"')
    if prop is not None and prop != operator:
        details.append(f"property {prop!r}")
    if details:
        message = f"{' '.join(details)}: {message}"
    return FilterValidationError(path, message)


def _is_number(value: Any) -> bool:
    """True for a finite JSON number; ``bool`` is never a number (D-10).

    Total over arbitrary-precision integers (WR-01): ``math.isfinite(10**400)``
    raises ``OverflowError`` because the conversion to double overflows, and a
    validator must never raise anything but ``FilterValidationError`` for a
    well-formed JSON payload.
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _is_text(value: Any) -> bool:
    """True for a non-empty string."""
    return isinstance(value, str) and value != ""


def _array_category(value: list[Any]) -> str | None:
    """Return a homogeneous scalar array's type, else ``None``.

    Checked on the RAW array so ``[true, 1]`` is mixed rather than coerced.
    """
    if not value:
        return None
    if all(isinstance(item, bool) for item in value):
        return "boolean"
    if all(_is_number(item) for item in value):
        return "number"
    if all(_is_text(item) for item in value):
        return "string"
    return None


def _require_scalar(field: str, value: Any, path: str, operator: str) -> None:
    """``eq``/``ne``: one scalar; text must be non-empty, numbers finite."""
    if isinstance(value, bool) or _is_number(value) or _is_text(value):
        return
    raise FilterValidationError(
        path,
        f'"{operator}" requires a scalar value; field {field!r} got {type(value).__name__}',
    )


def _require_ordering(field: str, value: Any, path: str, operator: str) -> None:
    """``gt``/``gte``/``lt``/``lte``: numeric only, except ``mtime`` ISO text."""
    if _is_number(value):
        return
    if field == "mtime" and isinstance(value, str) and value != "":
        return
    raise FilterValidationError(
        path,
        f'"{operator}" requires a numeric value; field {field!r} got {type(value).__name__}',
    )


def _require_membership(field: str, value: Any, path: str, operator: str) -> None:
    """``in``/``nin``/``all``: non-empty homogeneous scalar list (qmd parity)."""
    if not isinstance(value, list) or not value:
        raise FilterValidationError(
            path, f'"{operator}" requires a non-empty homogeneous list; field {field!r}'
        )
    category = _array_category(value)
    if category is None:
        raise FilterValidationError(
            path,
            f'"{operator}" requires a non-empty homogeneous list; field {field!r} has '
            "mixed or invalid element types",
        )


def _require_contains_operand(field: str, value: Any, path: str, operator: str) -> None:
    """``contains``: a non-empty string, or a non-empty homogeneous string list."""
    if _is_text(value):
        return
    if isinstance(value, list) and value and _array_category(value) == "string":
        return
    raise FilterValidationError(
        path,
        f'"{operator}" requires a non-empty string or string list; field {field!r}',
    )


def _require_text(field: str, value: Any, path: str, operator: str) -> None:
    """``prefix``/``suffix``: one non-empty string."""
    if _is_text(value):
        return
    raise FilterValidationError(path, f'"{operator}" requires a non-empty string; field {field!r}')


def _require_type(field: str, value: Any, path: str, operator: str) -> None:
    """``type``: exactly ``string``, ``number``, or ``boolean``."""
    if isinstance(value, str) and value in _TYPE_VALUES:
        return
    allowed = ", ".join(sorted(_TYPE_VALUES))
    raise FilterValidationError(
        path, f'"{operator}" value must be one of {allowed}; field {field!r} got {value!r}'
    )


def _require_bool(field: str, value: Any, path: str, operator: str) -> None:
    """``exists``: a boolean."""
    if isinstance(value, bool):
        return
    raise FilterValidationError(
        path,
        f'"{operator}" requires a boolean value; field {field!r} got {type(value).__name__}',
    )


_OPERAND_VALIDATORS: dict[str, Callable[[str, Any, str, str], None]] = {
    "eq": _require_scalar,
    "ne": _require_scalar,
    "gt": _require_ordering,
    "gte": _require_ordering,
    "lt": _require_ordering,
    "lte": _require_ordering,
    "in": _require_membership,
    "nin": _require_membership,
    "all": _require_membership,
    "contains": _require_contains_operand,
    "prefix": _require_text,
    "suffix": _require_text,
    "type": _require_type,
    "exists": _require_bool,
}


def _check_case_insensitive(field: str, raw: dict[str, Any], path: str) -> None:
    """``caseInsensitive`` is accepted only when the operand is string data."""
    flag = raw.get("caseInsensitive")
    if flag is None:
        return
    value = raw.get("value")
    if isinstance(value, str) or (
        isinstance(value, list) and value and _array_category(value) == "string"
    ):
        return
    raise FilterValidationError(
        path,
        f"caseInsensitive requires a string or string-list operand; field {field!r}",
    )


def _is_text_operand(value: Any) -> bool:
    """True for a non-empty string or a non-empty homogeneous string list."""
    if isinstance(value, str):
        return value != ""
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item != "" for item in value)
    )


def _is_mtime_operand(value: Any) -> bool:
    """True for a number or ISO text (and their homogeneous lists) on ``mtime``."""
    scalars = value if isinstance(value, list) else [value]
    return bool(scalars) and all(
        (isinstance(item, str) and item != "")
        or (isinstance(item, (int, float)) and not isinstance(item, bool))
        for item in scalars
    )


def _check_path_field(raw: dict[str, Any], path: str) -> None:
    """Validate one condition against the reserved text built-in ``path``."""
    operator = str(raw.get("operator", ""))
    field = "path"
    value = raw.get("value")
    if operator in _ORDERING_OPERATORS:
        raise FilterValidationError(
            path,
            f'"{operator}" does not support ordering on a text built-in; field {field!r}',
        )
    if operator == "all":
        raise FilterValidationError(
            path, f'"{operator}" is not available on a scalar built-in; field {field!r}'
        )
    if raw.get("caseInsensitive") and operator == "type":
        raise FilterValidationError(
            path,
            f'"{operator}" does not accept caseInsensitive on a text built-in; field {field!r}',
        )
    if operator in {"eq", "ne", "in", "nin"} and not _is_text_operand(value):
        raise FilterValidationError(path, f'"{operator}" requires a string value; field {field!r}')


def _check_mtime_field(raw: dict[str, Any], path: str) -> None:
    """Validate one condition against the reserved numeric built-in ``mtime``."""
    operator = str(raw.get("operator", ""))
    field = "mtime"
    value = raw.get("value")
    if raw.get("caseInsensitive"):
        raise FilterValidationError(
            path,
            f'"{operator}" does not accept caseInsensitive on a numeric built-in; field {field!r}',
        )
    if operator in _TEXT_OPERATORS:
        raise FilterValidationError(
            path, f'"{operator}" is not available on a numeric built-in; field {field!r}'
        )
    if operator == "all":
        raise FilterValidationError(
            path, f'"{operator}" is not available on a scalar built-in; field {field!r}'
        )
    if operator in {"eq", "ne", "in", "nin"} and not _is_mtime_operand(value):
        raise FilterValidationError(
            path,
            f'"{operator}" requires a numeric or ISO-8601 value; field {field!r}',
        )


def _check_reserved_field(field: str, raw: dict[str, Any], path: str) -> None:
    """Reject built-in/operator pairings the SQL compiler cannot render (WR-02).

    ``path`` is text and ``mtime`` is numeric (D-03) and ordering is
    numeric-only (D-11). This matrix used to live only in
    ``sif.search.filters``, which runs after the CLI's ClickException boundary
    and after the MCP handler's ``isError`` mapping — so a well-formed payload
    such as ``{"field": "path", "operator": "lt"}`` surfaced a traceback
    instead of the D-17 message. Making it a parse-time rule gives the CLI,
    MCP, and discovery one taxonomy; the compiler keeps its defensive checks
    for directly constructed ASTs.

    ``caseInsensitive: false`` is treated exactly like an absent flag (WR-03),
    and an ``mtime`` string operand is allowed here because
    :func:`_normalize_mtime` validates it as ISO-8601 immediately after.
    """
    if field == "path":
        _check_path_field(raw, path)
    elif field == "mtime":
        _check_mtime_field(raw, path)


def _check_field_bytes(field: str, path: str) -> None:
    """Reject a ``field`` longer than 128 UTF-8 bytes (qmd's maxKeyBytes)."""
    if len(field.encode("utf-8")) > MAX_FILTER_FIELD_BYTES:
        raise FilterValidationError(
            path, f"field exceeds the maximum of {MAX_FILTER_FIELD_BYTES} bytes"
        )


def _validate_semantics(raw: Any, path: str = "") -> None:
    """Validate per-operator semantics on the raw payload (with AST paths)."""
    operator = str(raw.get("operator", ""))
    node_path = f"{path}.{operator}" if path else operator

    if operator in {"and", "or"}:
        operands = raw.get("operands")
        if not isinstance(operands, list) or not operands:
            raise FilterValidationError(node_path, f'"{operator}" requires at least one operand')
        for index, child in enumerate(operands):
            _validate_semantics(child, f"{node_path}.operands.{index}")
        return
    if operator == "not":
        _validate_semantics(raw.get("operand"), f"{node_path}.operand")
        return

    field = str(raw.get("field", ""))
    _check_field_bytes(field, node_path)
    validator = _OPERAND_VALIDATORS.get(operator)
    if validator is None:
        raise FilterValidationError(node_path, f'"{operator}" is not a known operator')
    validator(field, raw.get("value"), node_path, operator)
    _check_case_insensitive(field, raw, node_path)
    if field in _RESERVED_FIELDS:
        _check_reserved_field(field, raw, node_path)


def _parse_iso_epoch(value: str, path: str) -> int:
    """Parse an ISO-8601 date/datetime into integer UTC epoch seconds (D-12).

    Date-only values are UTC midnight; naive datetimes are UTC; aware
    datetimes convert to UTC. Python 3.10's ``fromisoformat`` does not accept
    a trailing ``Z``, so it is normalized first.
    """
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise FilterValidationError(
            path, f"mtime value {value!r} is not an ISO-8601 date or datetime"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return int(parsed.timestamp())


def _normalize_mtime(raw: Any, node: FilterNode, path: str) -> FilterNode:
    """Replace ``mtime`` ISO-8601 string operands with epoch integers (D-12).

    Runs after semantic validation and only for operators that compare the
    field value: ``type`` (``"number"``) and ``exists`` (a bool) are never
    rewritten.
    """
    operator = str(raw.get("operator", ""))
    node_path = f"{path}.{operator}" if path else operator
    if isinstance(node, (And, Or)):
        children = [
            _normalize_mtime(child_raw, child_node, f"{node_path}.operands.{index}")
            for index, (child_raw, child_node) in enumerate(
                zip(raw["operands"], node.operands, strict=True)
            )
        ]
        return node.model_copy(update={"operands": children})
    if isinstance(node, Not):
        return node.model_copy(
            update={"operand": _normalize_mtime(raw["operand"], node.operand, node_path)}
        )
    if raw.get("field") != "mtime" or operator not in _MTIME_TEXT_OPERATORS:
        return node
    value = raw.get("value")
    if isinstance(value, str):
        return node.model_copy(update={"value": _parse_iso_epoch(value, node_path)})
    if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
        return node.model_copy(
            update={"value": [_parse_iso_epoch(item, node_path) for item in value]}
        )
    return node


def _parse_ast(payload: Any) -> tuple[Any, FilterNode]:
    """Shape-validate a payload and return ``(raw, validated_node)``."""
    _check_budgets(payload)
    try:
        node: FilterNode = _FILTER.validate_python(payload)
    except ValidationError as exc:
        raise _pydantic_error_to_filter_error(exc) from exc
    _validate_semantics(payload)
    return payload, node


def parse_filter(payload: Any) -> FilterNode:
    """Validate a raw JSON payload into the shared filter AST.

    Raises:
        FilterValidationError: when the payload violates a budget or the
            grammar. The message names the operator, the field, and the
            dotted path inside the AST (D-17).
    """
    raw, node = _parse_ast(payload)
    return _normalize_mtime(raw, node, "")


def parse_match(payload: Any) -> FilterNode:
    """Validate the discovery ``--match`` grammar over one entry row.

    Same node classes and budgets as :func:`parse_filter`, restricted to the
    entry shape: leaves address ``key`` or ``value``, ``exists``/``all`` are
    rejected, and ordering on ``key`` is rejected (a key is text; ordering is
    never lexicographic, D-11).
    """
    raw, node = _parse_ast(payload)
    _validate_match_semantics(raw, "")
    return node


def _validate_match_semantics(raw: Any, path: str) -> None:
    """Enforce the entry-scope restrictions of the discovery match grammar."""
    operator = str(raw.get("operator", ""))
    node_path = f"{path}.{operator}" if path else operator
    if operator in {"and", "or"}:
        for index, child in enumerate(raw["operands"]):
            _validate_match_semantics(child, f"{node_path}.operands.{index}")
        return
    if operator == "not":
        _validate_match_semantics(raw["operand"], f"{node_path}.operand")
        return

    field = str(raw.get("field", ""))
    if field not in {"key", "value"}:
        raise FilterValidationError(
            node_path,
            f"field {field!r} is not available in the match grammar; use 'key' or 'value'",
        )
    if operator in {"exists", "all"}:
        raise FilterValidationError(
            node_path, f'"{operator}" is not available in the match grammar'
        )
    if operator in {"gt", "gte", "lt", "lte"} and field == "key":
        raise FilterValidationError(
            node_path,
            f"\"{operator}\" is not available on field 'key'; a key is text",
        )
