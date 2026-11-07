"""Text processing utilities for SIF."""

import re
from typing import Any


def count_tokens(text: str, tokenizer: Any | None = None) -> int:
    """Count tokens in text.

    Uses a rough estimate if no tokenizer is provided.

    Args:
        text: Input text
        tokenizer: Optional tokenizer to use

    Returns:
        Estimated token count
    """
    if tokenizer is not None:
        try:
            return len(tokenizer.encode(text))
        except Exception:
            pass

    # Rough estimate: 1 token ~= 4 characters for English text
    return len(text) // 4


def extract_code_blocks(text: str) -> list[tuple[str, str]]:
    """Extract code blocks from markdown text.

    Args:
        text: Markdown text

    Returns:
        List of (language, code) tuples
    """
    pattern = r"```(\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return [(lang or "text", code.strip()) for lang, code in matches]
