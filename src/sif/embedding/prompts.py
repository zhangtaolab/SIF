"""Prompt-scheme resolution for role-aware embedding (EMB-02, D-07).

A prompt scheme says which instruction (if any) each embedding role should
pass to the backend. Settings are the override surface; a tiny known-model
table supplies the correct default for instruction-tuned models so a model
arm cannot be silently crippled by a missing query instruction. Unknown
models resolve to no prompt, which keeps the default Qwen3 path unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from sif.utils.logging import get_logger


logger = get_logger(__name__)

# Backends whose concrete embedders expose sentence-transformers'
# ``encode(..., prompt_name=...)``. Every other backend records
# ``prompt_supported: false`` in the identity and takes no prompt.
_PROMPT_SUPPORTED_TYPES = frozenset({"sentence_transformers", "modelscope"})

# Known instruction-tuned models: (query prompt, document prompt). Qwen3 is
# deliberately absent: its own config defines query/document prompts, but the
# Phase 23 Harrier gate requires its vectors and cache keys to stay
# byte-identical to the pre-Phase-21 baseline until a model arm wins.
_KNOWN_PROMPT_SCHEMES: dict[str, tuple[str | None, str | None]] = {
    "microsoft/harrier-oss-v1-0.6b": ("web_search_query", None),
}


@dataclass(frozen=True)
class PromptScheme:
    """Effective per-role prompt names for one embedding model."""

    query_prompt: str | None
    document_prompt: str | None
    supported: bool


def _resolve_role(override: str | None, table_value: str | None) -> str | None:
    """Apply the D-07 precedence: non-empty override > table > no prompt.

    ``None`` means "use the known-model default"; an empty string is the
    explicit disable value, so it wins over the table and yields no prompt.
    """
    if override is None:
        return table_value
    if override == "":
        return None
    return override


def resolve_prompt_scheme(
    model_name: str,
    model_type: str,
    query_override: str | None,
    document_override: str | None,
) -> PromptScheme:
    """Resolve the effective prompt scheme for a model.

    Args:
        model_name: Configured model name/identifier.
        model_type: Backend type (e.g. ``modelscope``, ``openai``).
        query_override: ``SIF_QUERY_PROMPT_NAME`` value, if set.
        document_override: ``SIF_DOCUMENT_PROMPT_NAME`` value, if set.

    Returns:
        The effective scheme; an unsupported backend reports no prompts even
        when overrides are configured (one warning is logged when they are).
    """
    if model_type not in _PROMPT_SUPPORTED_TYPES:
        if query_override or document_override:
            logger.warning(
                "Embedding backend '%s' does not support prompt names; "
                "ignoring SIF_QUERY_PROMPT_NAME/SIF_DOCUMENT_PROMPT_NAME",
                model_type,
            )
        return PromptScheme(query_prompt=None, document_prompt=None, supported=False)

    table_query, table_document = _KNOWN_PROMPT_SCHEMES.get(model_name.lower(), (None, None))
    return PromptScheme(
        query_prompt=_resolve_role(query_override, table_query),
        document_prompt=_resolve_role(document_override, table_document),
        supported=True,
    )
