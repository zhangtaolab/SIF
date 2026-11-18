"""Strict JSON output helpers for machine-facing CLI/MCP payloads (20 REVIEW WR-06)."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any


def json_safe(value: Any) -> Any:
    """Return ``value`` with every non-finite float stringified.

    RFC 8259 has no ``NaN``/``Infinity`` token. New writes cannot produce one —
    the canonical metadata serializer stringifies non-finite floats before
    storing them — but legacy ``documents.metadata`` blobs are never rewritten
    by the backfill, so a machine-facing serializer must still be total.
    Stringifying matches the canonical form (``"nan"``/``"inf"``/``"-inf"``)
    and keeps the value visible instead of dropping it.
    """
    if isinstance(value, Mapping):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def json_dumps_strict(value: Any, **kwargs: Any) -> str:
    """Serialize ``value`` as strict RFC 8259 JSON (``allow_nan=False``)."""
    return json.dumps(json_safe(value), allow_nan=False, **kwargs)
