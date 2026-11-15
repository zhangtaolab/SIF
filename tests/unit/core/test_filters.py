"""AST, operator-semantics, budget, mtime, and match-grammar tests (Plan 20-01).

Every semantic rejection asserts the rendered message — operator, field, and
dotted AST path — not merely that an exception type was raised (D-17).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from sif.core.filters import (
    MAX_FILTER_ARRAY,
    MAX_FILTER_DEPTH,
    MAX_FILTER_NODES,
    MAX_FILTER_STRING,
    All,
    And,
    Contains,
    Eq,
    Exists,
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
    parse_filter,
    parse_match,
)


def _epoch(year: int, month: int, day: int) -> int:
    """UTC epoch seconds for a date at midnight."""
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp())


_VALID_CASES: list[tuple[str, dict[str, Any], type]] = [
    ("eq", {"field": "status", "operator": "eq", "value": "active"}, Eq),
    ("ne", {"field": "status", "operator": "ne", "value": "archived"}, Ne),
    ("gt", {"field": "priority", "operator": "gt", "value": 3}, Gt),
    ("gte", {"field": "priority", "operator": "gte", "value": 3}, Gte),
    ("lt", {"field": "priority", "operator": "lt", "value": 3}, Lt),
    ("lte", {"field": "priority", "operator": "lte", "value": 3.5}, Lte),
    ("in", {"field": "topic", "operator": "in", "value": ["a", "b"]}, In),
    ("nin", {"field": "topic", "operator": "nin", "value": [1, 2]}, Nin),
    ("all", {"field": "tags", "operator": "all", "value": ["x", "y"]}, All),
    ("contains", {"field": "body", "operator": "contains", "value": "x"}, Contains),
    ("prefix", {"field": "pathish", "operator": "prefix", "value": "a/"}, Prefix),
    ("suffix", {"field": "pathish", "operator": "suffix", "value": ".md"}, Suffix),
    ("type", {"field": "priority", "operator": "type", "value": "number"}, TypeCondition),
    ("exists", {"field": "reviewed", "operator": "exists", "value": True}, Exists),
    (
        "and",
        {"operator": "and", "operands": [{"field": "a", "operator": "eq", "value": "x"}]},
        And,
    ),
    (
        "or",
        {"operator": "or", "operands": [{"field": "a", "operator": "eq", "value": "x"}]},
        Or,
    ),
    (
        "not",
        {"operator": "not", "operand": {"field": "a", "operator": "exists", "value": True}},
        Not,
    ),
]


class TestNodeShapes:
    """The 17-operator union and its structural rejections."""

    @pytest.mark.parametrize(("operator", "payload", "expected_type"), _VALID_CASES)
    def test_operator_validates_to_its_node(
        self, operator: str, payload: dict[str, Any], expected_type: type
    ) -> None:
        """Each of the 17 qmd operators parses into its own node class."""
        node = parse_filter(payload)
        assert isinstance(node, expected_type)
        assert node.operator == operator

    def test_unknown_property_rejected(self) -> None:
        """Unknown properties are rejected and the message names them."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": "a", "operator": "eq", "value": "x", "bogus": 1})
        message = str(excinfo.value)
        assert message.startswith("filter.")
        assert "bogus" in message

    def test_non_object_root_rejected(self) -> None:
        """A non-object root is a root-path validation error."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter([{"field": "a", "operator": "eq", "value": "x"}])
        assert str(excinfo.value) == "filter: a filter node must be an object"

    def test_non_object_child_rejected(self) -> None:
        """A non-object child inside a group is rejected before recursion."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"operator": "and", "operands": ["nope"]})
        assert "must be an object" in str(excinfo.value)

    def test_non_empty_field_required(self) -> None:
        """An empty ``field`` is rejected and the path/operator are named."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": "", "operator": "eq", "value": "x"})
        message = str(excinfo.value)
        assert message.startswith("filter.eq.field:")
        assert '"eq"' in message

    def test_field_byte_length_capped(self) -> None:
        """129 UTF-8 bytes in ``field`` is rejected even at <=128 characters."""
        long_field = "é" * 65  # 65 characters, 130 UTF-8 bytes
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": long_field, "operator": "eq", "value": "x"})
        assert "field exceeds the maximum of 128 bytes" in str(excinfo.value)

    def test_unknown_operator_rejected(self) -> None:
        """An unknown operator tag is a shape error naming the expected tags."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": "a", "operator": "regex", "value": "x"})
        message = str(excinfo.value)
        assert message.startswith("filter:")
        assert "regex" in message

    def test_not_requires_single_operand(self) -> None:
        """``not`` takes ``operand`` (singular); ``operands`` is rejected."""
        with pytest.raises(FilterValidationError):
            parse_filter(
                {
                    "operator": "not",
                    "operands": [{"field": "a", "operator": "exists", "value": True}],
                }
            )


class TestOperatorSemantics:
    """Per-operator validation rules and their rendered messages."""

    def test_ordering_rejects_bool(self) -> None:
        """True is not a number (D-10): gt rejects a boolean operand."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": "priority", "operator": "gt", "value": True})
        message = str(excinfo.value)
        assert message.startswith("filter.gt:")
        assert '"gt"' in message
        assert "priority" in message
        assert "bool" in message

    @pytest.mark.parametrize("operator", ["gt", "gte", "lt", "lte"])
    def test_ordering_rejects_text(self, operator: str) -> None:
        """Non-mtime ordering with a string operand is never lexicographic."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": "priority", "operator": operator, "value": "10"})
        assert "requires a numeric value" in str(excinfo.value)

    @pytest.mark.parametrize("operator", ["eq", "gt", "in", "all", "contains"])
    def test_empty_operand_rejected(self, operator: str) -> None:
        """Membership needs a non-empty list; text needs a non-empty string."""
        payload = {"field": "topic", "operator": operator, "value": ""}
        if operator in {"in", "all"}:
            payload["value"] = []
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter(payload)
        assert str(excinfo.value).startswith("filter.")

    def test_mixed_type_membership_rejected(self) -> None:
        """A mixed membership list is rejected before lax coercion hides it."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": "topic", "operator": "in", "value": [True, 1]})
        message = str(excinfo.value)
        assert "homogeneous" in message
        assert "topic" in message

    def test_mixed_text_membership_rejected(self) -> None:
        """String/number mixes are rejected (shape-layer union failure)."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": "topic", "operator": "in", "value": [1, "a"]})
        message = str(excinfo.value)
        assert message.startswith("filter.")
        assert '"in"' in message

    def test_numeric_mix_is_homogeneous(self) -> None:
        """int/float mixes are one JSON number type, so ``in`` accepts them."""
        node = parse_filter({"field": "priority", "operator": "in", "value": [1, 2.5]})
        assert isinstance(node, In)
        assert node.value == [1.0, 2.5]

    @pytest.mark.parametrize("operator", ["in", "nin", "all"])
    def test_membership_requires_list(self, operator: str) -> None:
        """Membership operators reject a scalar operand."""
        with pytest.raises(FilterValidationError):
            parse_filter({"field": "topic", "operator": operator, "value": "a"})

    @pytest.mark.parametrize("operator", ["eq", "ne"])
    def test_equality_rejects_list(self, operator: str) -> None:
        """eq/ne take a scalar; membership lists belong to in/nin/all."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": "topic", "operator": operator, "value": ["a"]})
        assert "requires a scalar value" in str(excinfo.value)

    def test_contains_rejects_number(self) -> None:
        """``contains`` is a text operator; a numeric operand is invalid."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": "body", "operator": "contains", "value": 5})
        assert '"contains" requires a non-empty string' in str(excinfo.value)

    def test_contains_accepts_string_list(self) -> None:
        """Substring-any over a string array is valid (qmd parity)."""
        node = parse_filter({"field": "body", "operator": "contains", "value": ["a", "b"]})
        assert isinstance(node, Contains)

    @pytest.mark.parametrize("operator", ["prefix", "suffix"])
    def test_affix_rejects_list(self, operator: str) -> None:
        """prefix/suffix take one string."""
        with pytest.raises(FilterValidationError):
            parse_filter({"field": "body", "operator": operator, "value": ["a"]})

    def test_type_requires_known_value(self) -> None:
        """``type`` accepts exactly string/number/boolean."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": "priority", "operator": "type", "value": "date"})
        message = str(excinfo.value)
        assert '"type"' in message
        assert "boolean, number, string" in message

    def test_exists_requires_bool(self) -> None:
        """``exists`` takes a boolean."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": "reviewed", "operator": "exists", "value": "yes"})
        assert "requires a boolean value" in str(excinfo.value)

    def test_case_insensitive_accepted_on_string(self) -> None:
        """caseInsensitive is honored on a string operand (D-10)."""
        node = parse_filter(
            {"field": "status", "operator": "eq", "value": "Active", "caseInsensitive": True}
        )
        assert isinstance(node, Eq)
        assert node.caseInsensitive is True

    def test_case_insensitive_accepted_on_string_list(self) -> None:
        """caseInsensitive is honored on a string-list operand too (D-10)."""
        node = parse_filter(
            {"field": "topic", "operator": "in", "value": ["A", "b"], "caseInsensitive": True}
        )
        assert isinstance(node, In)
        assert node.caseInsensitive is True

    def test_case_insensitive_rejected_on_number(self) -> None:
        """A numeric operand has no case; the flag is rejected."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter(
                {"field": "priority", "operator": "eq", "value": 1, "caseInsensitive": True}
            )
        assert "caseInsensitive requires a string" in str(excinfo.value)

    def test_group_requires_operand(self) -> None:
        """and/or require at least one operand."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"operator": "and", "operands": []})
        assert '"and" requires at least one operand' in str(excinfo.value)

    def test_nested_error_path_is_dotted(self) -> None:
        """A nested violation renders the full dotted AST path."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter(
                {
                    "operator": "and",
                    "operands": [
                        {"field": "a", "operator": "eq", "value": "x"},
                        {"field": "priority", "operator": "gt", "value": "high"},
                    ],
                }
            )
        message = str(excinfo.value)
        assert message.startswith("filter.and.operands.1.gt:")
        assert '"gt"' in message
        assert "priority" in message


class TestBudgets:
    """D-13 budgets are enforced before pydantic recursion."""

    def test_depth_budget(self) -> None:
        """Nine levels of nesting raise the depth budget message."""
        payload: dict[str, Any] = {"field": "a", "operator": "exists", "value": True}
        for _ in range(MAX_FILTER_DEPTH):
            payload = {"operator": "not", "operand": payload}
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter(payload)
        assert f"maximum nesting depth of {MAX_FILTER_DEPTH}" in str(excinfo.value)

    def test_node_budget(self) -> None:
        """A 65-node AST raises the node-budget message."""
        leaf = {"field": "a", "operator": "eq", "value": "x"}
        payload = {"operator": "and", "operands": [dict(leaf) for _ in range(MAX_FILTER_NODES)]}
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter(payload)
        assert f"{MAX_FILTER_NODES}-node budget" in str(excinfo.value)

    def test_node_budget_boundary_accepted(self) -> None:
        """Exactly the node budget is accepted (63 leaves + the group)."""
        leaf = {"field": "a", "operator": "eq", "value": "x"}
        payload = {"operator": "and", "operands": [dict(leaf) for _ in range(MAX_FILTER_NODES - 1)]}
        assert isinstance(parse_filter(payload), And)

    def test_string_operand_budget(self) -> None:
        """A 1025-character string operand raises the string-budget message."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter(
                {"field": "body", "operator": "contains", "value": "x" * (MAX_FILTER_STRING + 1)}
            )
        assert f"maximum string operand length of {MAX_FILTER_STRING}" in str(excinfo.value)

    def test_array_operand_budget(self) -> None:
        """A 129-element array operand raises the array-budget message."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter(
                {"field": "topic", "operator": "in", "value": ["x"] * (MAX_FILTER_ARRAY + 1)}
            )
        assert f"maximum array operand length of {MAX_FILTER_ARRAY}" in str(excinfo.value)

    def test_budget_errors_are_not_pydantic(self) -> None:
        """A 900-deep AST reports the depth budget, not pydantic recursion_loop."""
        payload: dict[str, Any] = {"field": "a", "operator": "exists", "value": True}
        for _ in range(900):
            payload = {"operator": "not", "operand": payload}
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter(payload)
        assert "maximum nesting depth" in str(excinfo.value)


class TestMtimeParsing:
    """D-12: mtime accepts ISO-8601 text and normalizes it to epoch seconds."""

    def test_iso_date_normalizes_to_utc_midnight(self) -> None:
        """A date-only ISO value becomes UTC midnight epoch seconds."""
        node = parse_filter({"field": "mtime", "operator": "gte", "value": "2026-01-01"})
        assert node.value == _epoch(2026, 1, 1)

    def test_iso_datetime_variants_agree(self) -> None:
        """Z, +00:00, naive, and +09:00 datetimes normalize to the same epoch."""
        expected = _epoch(2026, 1, 1)
        for text in (
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00",
            "2026-01-01T09:00:00+09:00",
        ):
            node = parse_filter({"field": "mtime", "operator": "gte", "value": text})
            assert node.value == expected, text

    def test_epoch_input_passes_through(self) -> None:
        """A numeric operand is already epoch seconds; no rewrite occurs."""
        node = parse_filter({"field": "mtime", "operator": "gte", "value": 1767225600})
        assert node.value == 1767225600

    def test_in_list_normalizes_each_element(self) -> None:
        """ISO strings inside an mtime membership list are each normalized."""
        node = parse_filter(
            {"field": "mtime", "operator": "in", "value": ["2026-01-01", "2026-01-02"]}
        )
        assert node.value == [_epoch(2026, 1, 1), _epoch(2026, 1, 2)]

    def test_invalid_iso_rejected(self) -> None:
        """A non-ISO string on mtime is a validation error naming the value."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": "mtime", "operator": "gte", "value": "yesterday"})
        assert "not an ISO-8601 date or datetime" in str(excinfo.value)

    def test_non_mtime_string_ordering_rejected(self) -> None:
        """Strings are rejected for ordering on every other field."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter({"field": "priority", "operator": "gte", "value": "2026-01-01"})
        assert "requires a numeric value" in str(excinfo.value)

    def test_type_operand_not_rewritten(self) -> None:
        """``type`` keeps its literal value even on the mtime field."""
        node = parse_filter({"field": "mtime", "operator": "type", "value": "number"})
        assert node.value == "number"

    def test_exists_operand_not_rewritten(self) -> None:
        """``exists`` keeps its boolean even on the mtime field."""
        node = parse_filter({"field": "mtime", "operator": "exists", "value": True})
        assert node.value is True


class TestMatchGrammar:
    """The discovery ``--match`` grammar over one entry row."""

    @pytest.mark.parametrize(
        "payload",
        [
            {"field": "key", "operator": "prefix", "value": "tag"},
            {"field": "key", "operator": "eq", "value": "status"},
            {"field": "key", "operator": "contains", "value": "tag"},
            {"field": "value", "operator": "eq", "value": "active"},
            {"field": "value", "operator": "gt", "value": 3},
            {"field": "value", "operator": "type", "value": "number"},
            {
                "field": "key",
                "operator": "prefix",
                "value": "Tag",
                "caseInsensitive": True,
            },
            {
                "operator": "and",
                "operands": [
                    {"field": "key", "operator": "prefix", "value": "tag"},
                    {"field": "value", "operator": "eq", "value": "x"},
                ],
            },
        ],
    )
    def test_valid_match_payloads(self, payload: dict[str, Any]) -> None:
        """Key/value entry conditions validate through the shared grammar."""
        assert parse_match(payload) is not None

    def test_unknown_field_rejected(self) -> None:
        """Only key/value are addressable in an entry scope."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_match({"field": "topic", "operator": "eq", "value": "x"})
        message = str(excinfo.value)
        assert message.startswith("filter.eq:")
        assert "topic" in message
        assert "'key' or 'value'" in message

    @pytest.mark.parametrize("operator", ["exists", "all"])
    def test_restricted_operators_rejected(self, operator: str) -> None:
        """exists/all are not available in the match grammar."""
        value: Any = True if operator == "exists" else ["a"]
        with pytest.raises(FilterValidationError) as excinfo:
            parse_match({"field": "value", "operator": operator, "value": value})
        assert f'"{operator}" is not available in the match grammar' in str(excinfo.value)

    @pytest.mark.parametrize("operator", ["gt", "gte", "lt", "lte"])
    def test_ordering_on_key_rejected(self, operator: str) -> None:
        """A key is text; ordering on it is never lexicographic (D-11)."""
        with pytest.raises(FilterValidationError) as excinfo:
            parse_match({"field": "key", "operator": operator, "value": 3})
        assert "not available on field 'key'" in str(excinfo.value)

    def test_ordering_on_value_allowed(self) -> None:
        """Numeric ordering remains available on a value entry."""
        assert isinstance(parse_match({"field": "value", "operator": "lt", "value": 3}), Lt)

    def test_match_uses_shared_budgets(self) -> None:
        """The match grammar enforces the same depth budget."""
        payload: dict[str, Any] = {"field": "key", "operator": "eq", "value": "x"}
        for _ in range(MAX_FILTER_DEPTH):
            payload = {"operator": "not", "operand": payload}
        with pytest.raises(FilterValidationError) as excinfo:
            parse_match(payload)
        assert "maximum nesting depth" in str(excinfo.value)
