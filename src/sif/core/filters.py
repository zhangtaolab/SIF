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
surfacing pydantic's ``recursion_loop`` at ~900 depth.
"""

from __future__ import annotations

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

# The operator tags a shape error can land on. Used only to name the offending
# operator in a converted pydantic message; expanded with the grammar in
# Task 2 (20-01).
_OPERATOR_TAGS = frozenset({"eq"})


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
    membership lists) are validated by the shared semantic pass so every
    violation carries its dotted AST path.
    """

    field: str = Field(min_length=1, max_length=MAX_FILTER_FIELD_BYTES)
    value: Any
    # D-10: ASCII-only case folding for string / string-array operands.
    caseInsensitive: bool | None = None  # noqa: N815


class Eq(Condition):
    """Typed exact match (D-10: no coercion)."""

    operator: Literal["eq"]


FilterNode = Annotated[Eq, Field(discriminator="operator")]

_FILTER: TypeAdapter[Any] = TypeAdapter(FilterNode)


def _check_budgets(raw: Any) -> None:
    """Enforce the D-13 budgets on the raw payload before pydantic recursion.

    Iterative by design: a recursive walk would itself raise ``RecursionError``
    on the inputs the budget exists to reject. Depth and node count are
    checked here; Task 2 adds the operand budgets.
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
            raise FilterValidationError(
                "", f"filter exceeds the maximum node budget of {MAX_FILTER_NODES}"
            )
        if depth > MAX_FILTER_DEPTH:
            raise FilterValidationError(
                "", f"filter exceeds the maximum nesting depth of {MAX_FILTER_DEPTH}"
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


def parse_filter(payload: Any) -> FilterNode:
    """Validate a raw JSON payload into the shared filter AST.

    Raises:
        FilterValidationError: when the payload violates a budget or the
            grammar. The message names the operator, the field, and the
            dotted path inside the AST (D-17).
    """
    _check_budgets(payload)
    try:
        node: FilterNode = _FILTER.validate_python(payload)
    except ValidationError as exc:
        raise _pydantic_error_to_filter_error(exc) from exc
    _check_field_bytes(node)
    return node


def _check_field_bytes(node: FilterNode) -> None:
    """Reject a ``field`` longer than 128 UTF-8 bytes (qmd's maxKeyBytes)."""
    if len(node.field.encode("utf-8")) > MAX_FILTER_FIELD_BYTES:
        raise FilterValidationError(
            "field", f"field exceeds the maximum of {MAX_FILTER_FIELD_BYTES} bytes"
        )
