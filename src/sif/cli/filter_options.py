"""Shared CLI adapters for the ``--filter`` and ``--match`` JSON options (Phase 20).

Both adapters map parse/validation failures to ``click.ClickException`` the
same way on every command (D-17): invalid JSON names the option, and a
grammar/budget violation carries the shared validator's operator/field/path
message. ``None`` means the option was not supplied — the only unfiltered or
unmatched signal, never the compiler's empty ``("", [])`` fragment.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import click

from sif.core.filters import FilterNode, FilterValidationError, parse_filter, parse_match


def _parse_option(
    raw: str | None, label: str, parser: Callable[[Any], FilterNode]
) -> FilterNode | None:
    """Parse one JSON option into the shared AST, as a user error on failure."""
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"{label}: invalid JSON: {exc.msg}") from exc
    try:
        return parser(payload)
    except FilterValidationError as exc:
        raise click.ClickException(str(exc)) from exc


def parse_filter_option(raw: str | None) -> FilterNode | None:
    """Parse ``--filter`` JSON into the shared filter AST (D-01)."""
    return _parse_option(raw, "filter", parse_filter)


def parse_match_option(raw: str | None) -> FilterNode | None:
    """Parse ``--match`` JSON into the discovery entry-scope AST (D-14)."""
    return _parse_option(raw, "match", parse_match)
