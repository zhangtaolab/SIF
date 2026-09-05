r"""Shared stem-tolerant, word-boundary term matching for search snippets.

BM25 highlights and snippet extraction both need to decide "does this query
term match this text?" against text that FTS5 matched with a stemming
tokenizer. Plain ``term in text`` misses stem variants (``ranking`` vs
``rank``) and false-positives inside longer words (``table`` inside
``notable``). This module centralizes that decision:

- ASCII alphabetic terms get a light stem plus an optional-suffix pattern
  bracketed by ``(?<![a-z0-9])`` / ``(?![a-z0-9])`` lookarounds. The
  lookarounds (rather than ``\\b``) treat underscores as boundaries, so each
  ``snake_case`` segment is individually matchable while matches strictly
  inside a longer alphabetic run stay impossible.
- ASCII terms with hyphens/digits/dots match literally (no stemming), with
  boundary lookarounds attached only where the edge character is alphanumeric.
- Non-ASCII (CJK) terms skip regex entirely: full-run substring match, with a
  per-character fallback that credits text sharing enough distinct term
  characters (向量搜索 highlights 向量检索).

All functions are case-insensitive internally.
"""

from __future__ import annotations

import re
from functools import lru_cache


# Optional suffixes an over-stripped base may re-match after (longest-first
# ordering inside the alternation is irrelevant for correctness because the
# trailing lookaround rejects partial expansions).
_SUFFIXES = ("ing", "ed", "es", "s", "e")

# Word-boundary lookarounds. Unlike \b these treat "_" as a boundary, which
# makes each SNAKE_CASE segment individually matchable.
_LOOKBEHIND = r"(?<![a-z0-9])"
_LOOKAHEAD = r"(?![a-z0-9])"

# Minimum base length for a stripped alphabetic stem ("ties" keeps its "es").
_MIN_BASE_LEN = 3

# Minimum term length for the ies -> y rule ("ties" keeps its "ies").
_IES_MIN_TERM_LEN = 4


@lru_cache(maxsize=512)
def _compile(term: str) -> re.Pattern[str] | None:
    """Compile a match pattern for one term (cached; None for non-regex)."""
    if not term:
        return None
    if not term.isascii():
        # CJK and other non-ASCII scripts use the substring fallback path.
        return None
    if term.isalpha():
        return _compile_stemmed(term)
    return _compile_literal(term)


def _ascii_stem(term: str) -> str:
    """Compute a light stem for a lowercase ASCII alphabetic term."""
    if len(term) > _IES_MIN_TERM_LEN and term.endswith("ies"):
        return term[:-3] + "y"
    for suffix in _SUFFIXES:
        if term.endswith(suffix) and len(term) - len(suffix) >= _MIN_BASE_LEN:
            return term[: -len(suffix)]
    return term


def _compile_stemmed(term: str) -> re.Pattern[str]:
    """Compile the stem-tolerant pattern for an ASCII alphabetic term."""
    base = re.escape(_ascii_stem(term.lower()))
    pattern = rf"{_LOOKBEHIND}{base}(?:s|es|ed|ing|e)?{_LOOKAHEAD}"
    return re.compile(pattern, re.IGNORECASE)


def _compile_literal(term: str) -> re.Pattern[str]:
    """Compile a literal pattern for ASCII terms with non-alphabetic chars."""
    escaped = re.escape(term)
    lead = _LOOKBEHIND if term[0].isalnum() else ""
    trail = _LOOKAHEAD if term[-1].isalnum() else ""
    return re.compile(rf"{lead}{escaped}{trail}", re.IGNORECASE)


def term_matches(text: str, term: str) -> bool:
    """Return True when term matches text (stem-tolerant, boundary-aware)."""
    if not text or not term:
        return False
    pattern = _compile(term)
    if pattern is not None:
        return pattern.search(text) is not None
    return _cjk_gate(text, term)


def count_matches(text: str, term: str) -> int:
    """Count matches of term in text.

    CJK terms without a full-run hit report the distinct term characters
    present instead, as secondary scoring credit.
    """
    if not text or not term:
        return 0
    pattern = _compile(term)
    if pattern is not None:
        return len(pattern.findall(text))
    lowered_text = text.lower()
    lowered_term = term.lower()
    run_count = lowered_text.count(lowered_term)
    if run_count:
        return run_count
    return len(_distinct_term_chars_present(lowered_text, lowered_term))


def distinct_terms_matched(text: str, terms: list[str]) -> int:
    """Return how many of terms match text at least once."""
    return sum(1 for term in terms if term_matches(text, term))


def find_first_match(text: str, terms: list[str]) -> tuple[int, int] | None:
    """Find the earliest match of any term in text.

    Returns (start, length) for the match with the smallest start position
    (longest match wins ties), or None when no term matches. CJK fallback
    matches report length 1 at the first shared term character.
    """
    best: tuple[int, int] | None = None
    for term in terms:
        candidate = _find_one(text, term)
        if candidate is None:
            continue
        if best is None or (candidate[0], -candidate[1]) < (best[0], -best[1]):
            best = candidate
    return best


def _find_one(text: str, term: str) -> tuple[int, int] | None:
    """Find the first match of a single term in text."""
    if not text or not term:
        return None
    pattern = _compile(term)
    if pattern is not None:
        match = pattern.search(text)
        if match is None:
            return None
        return match.start(), match.end() - match.start()
    return _cjk_find(text, term)


def _cjk_find(text: str, term: str) -> tuple[int, int] | None:
    """Locate a non-ASCII term: full run when present, else a shared char."""
    lowered_text = text.lower()
    lowered_term = term.lower()
    pos = lowered_text.find(lowered_term)
    if pos >= 0:
        return pos, len(lowered_term)
    if _cjk_gate(text, term):
        first = min(
            (lowered_text.find(ch) for ch in set(lowered_term) if ch in lowered_text),
            default=-1,
        )
        if first >= 0:
            return first, 1
    return None


def _cjk_gate(text: str, term: str) -> bool:
    """Non-ASCII match gate: full run present, or enough shared characters.

    The fallback passes when the count of distinct term characters present in
    text reaches max(2, half the term's distinct characters), so 向量搜索
    credits 向量检索 while a lone shared character fails.
    """
    lowered_text = text.lower()
    lowered_term = term.lower()
    if lowered_term in lowered_text:
        return True
    if len(lowered_term) <= 1:
        return False
    present = _distinct_term_chars_present(lowered_text, lowered_term)
    threshold = max(2, len(set(lowered_term)) // 2)
    return len(present) >= threshold


def _distinct_term_chars_present(lowered_text: str, lowered_term: str) -> set[str]:
    """Return the distinct term characters that appear in text."""
    return {ch for ch in set(lowered_term) if ch in lowered_text}
