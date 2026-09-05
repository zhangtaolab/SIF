"""Tests for the shared stem-tolerant, word-boundary term matcher."""

from sif.search.term_match import (
    count_matches,
    distinct_terms_matched,
    find_first_match,
    term_matches,
)


class TestAsciiStemTolerance:
    """Stem variants of alphabetic terms must match (G-04-1 empty cells)."""

    def test_term_ranking_matches_rank_forms(self) -> None:
        """"ranking" matches rank, ranking, ranked, Rank (case-insensitive)."""
        for text in ("rank", "ranking", "ranked", "Rank"):
            assert term_matches(f"The system {text} documents", "ranking"), text

    def test_term_tokens_matches_token_forms(self) -> None:
        """"tokens" matches both token and tokens."""
        assert term_matches("a token here", "tokens")
        assert term_matches("two tokens here", "tokens")

    def test_find_first_match_returns_earliest_across_terms(self) -> None:
        """Earliest (start, length) wins across all query terms."""
        text = "alpha token beta rank gamma"
        result = find_first_match(text, ["rank", "token"])
        assert result is not None
        start, length = result
        assert start == text.index("token")
        assert length == len("token")

    def test_find_first_match_returns_none_when_nothing_matches(self) -> None:
        assert find_first_match("nothing relevant", ["table"]) is None


class TestWordBoundaryStrictness:
    """Matches must not land strictly inside a longer alphanumeric run."""

    def test_term_table_matches_table_forms(self) -> None:
        assert term_matches("a table row", "table")
        assert term_matches("two tables here", "table")

    def test_term_table_no_match_inside_notable(self) -> None:
        """"table" must not match inside the longer word notable (G-04-1)."""
        for text in ("a notable change", "NOTABLE CHANGE", "Notable: intro"):
            assert not term_matches(text, "table"), text
            assert count_matches(text, "table") == 0

    def test_term_chunk_matches_snake_case_segment(self) -> None:
        """Underscores count as boundaries: CHUNK inside SIF_CHUNK_OVERLAP."""
        text = "| SIF_CHUNK_OVERLAP | Tokens of overlap between chunks |"
        assert term_matches(text, "chunk")
        # Both the identifier segment and the plain word count.
        assert count_matches(text, "chunk") == 2

    def test_match_length_covers_stemmed_surface(self) -> None:
        """An over-stripped base re-matches the original surface form."""
        text = "documents ranked by frequency"
        result = find_first_match(text, ["ranking"])
        assert result is not None
        start, length = result
        assert start == text.index("ranked")
        assert length == len("ranked")


class TestLiteralTerms:
    """Hyphenated/digit terms match literally — no stemming applied."""

    def test_hyphenated_term_matches_literally(self) -> None:
        assert term_matches("powered by sqlite-vec extension", "sqlite-vec")
        # No stem tolerance: sqlite-vec followed by more word chars misses.
        assert not term_matches("sqlite-vecx extension", "sqlite-vec")

    def test_digit_term_matches_literally(self) -> None:
        assert term_matches("version 3.5 released", "3.5")
        assert not term_matches("version 13.5 released", "3.5")

    def test_digit_term_count(self) -> None:
        assert count_matches("3.5 and 3.5 and 3.5", "3.5") == 3


class TestCjkFallback:
    """CJK terms use substring + per-character fallback (G-04-1 zero highlights)."""

    def test_full_run_present_matches_with_position(self) -> None:
        text = "支持向量搜索能力"
        assert term_matches(text, "向量搜索")
        result = find_first_match(text, ["向量搜索"])
        assert result is not None
        start, length = result
        assert start == text.index("向量搜索")
        assert length == len("向量搜索")

    def test_shared_characters_pass_the_gate(self) -> None:
        """向量搜索 highlights 向量检索 via per-character credit."""
        assert term_matches("支持 向量检索 能力", "向量搜索")
        result = find_first_match("支持 向量检索 能力", ["向量搜索"])
        assert result is not None
        start, _length = result
        assert start == "支持 向量检索 能力".index("向")

    def test_single_shared_character_fails_gate(self) -> None:
        """One shared term character is not enough credit to match."""
        assert not term_matches("只有搜索功能", "向量搜索")

    def test_count_matches_full_run(self) -> None:
        assert count_matches("向量搜索与向量搜索", "向量搜索") == 2

    def test_count_matches_falls_back_to_distinct_chars(self) -> None:
        """Run absent: count is the distinct term characters present."""
        assert count_matches("向量检索", "向量搜索") == 3


class TestDistinctTermsMatched:
    def test_counts_only_matching_terms(self) -> None:
        text = "chunk overlap configuration"
        terms = ["chunk", "overlap", "tokens"]
        assert distinct_terms_matched(text, terms) == 2

    def test_zero_when_none_match(self) -> None:
        assert distinct_terms_matched("notable intro", ["table"]) == 0
