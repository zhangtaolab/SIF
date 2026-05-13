"""Text processing utilities for SIF."""

import re
from re import Pattern
from typing import Any


# Compile regex patterns once
WHITESPACE_PATTERN: Pattern[str] = re.compile(r"\s+")
NON_ALPHANUMERIC_PATTERN: Pattern[str] = re.compile(r"[^\w\s-]")


def normalize_text(text: str) -> str:
    """Normalize text by cleaning whitespace and special characters.

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    # Replace multiple whitespace with single space
    text = WHITESPACE_PATTERN.sub(" ", text)
    # Strip leading/trailing whitespace
    return text.strip()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length.

    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    truncated = text[: max_length - len(suffix)]
    return truncated + suffix


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


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences.

    Args:
        text: Input text

    Returns:
        List of sentences
    """
    # Simple sentence splitting on punctuation
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


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


def remove_code_blocks(text: str) -> str:
    """Remove code blocks from markdown text.

    Args:
        text: Markdown text

    Returns:
        Text without code blocks
    """
    pattern = r"```.*?```"
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug.

    Args:
        text: Input text

    Returns:
        Slugified text
    """
    # Convert to lowercase
    text = text.lower()
    # Remove non-alphanumeric characters except hyphens
    text = NON_ALPHANUMERIC_PATTERN.sub("", text)
    # Replace spaces with hyphens
    text = text.replace(" ", "-")
    # Remove multiple hyphens
    text = re.sub(r"-+", "-", text)
    # Strip leading/trailing hyphens
    return text.strip("-")
