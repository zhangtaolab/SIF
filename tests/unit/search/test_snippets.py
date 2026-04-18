"""Tests for smart snippet extraction."""

from docsift.search.snippets import SmartSnippetExtractor


class TestSmartSnippetExtractor:
    def test_extract_finds_query_terms(self):
        extractor = SmartSnippetExtractor()
        text = (
            "This is about machine learning. "
            "Neural networks are part of ML. "
            "Deep learning is a subset."
        )
        query_terms = ["machine", "learning"]
        snippet = extractor.extract(text, query_terms)
        assert "machine" in snippet.lower()
        assert "learning" in snippet.lower()

    def test_extract_fallback_when_no_match(self):
        extractor = SmartSnippetExtractor()
        text = "Some unrelated text without matching terms."
        query_terms = ["quantum"]
        snippet = extractor.extract(text, query_terms)
        assert snippet  # Should return beginning of text
        assert "unrelated" in snippet

    def test_extract_empty_text(self):
        extractor = SmartSnippetExtractor()
        snippet = extractor.extract("", ["test"])
        assert snippet == ""

    def test_extract_empty_query(self):
        extractor = SmartSnippetExtractor()
        text = "Some content here."
        snippet = extractor.extract(text, [])
        assert "Some content" in snippet

    def test_extract_respects_max_length(self):
        extractor = SmartSnippetExtractor(max_length=50)
        text = "A. " * 100  # Very long text
        query_terms = ["a"]
        snippet = extractor.extract(text, query_terms)
        assert len(snippet) <= 60  # Allow for ellipsis

    def test_extract_prefers_high_term_density(self):
        extractor = SmartSnippetExtractor()
        text = (
            "First sentence has one match. "
            "Second sentence has machine learning and machine learning again. "
            "Third sentence has no matches."
        )
        query_terms = ["machine", "learning"]
        snippet = extractor.extract(text, query_terms)
        # Should prefer the sentence with more matches
        assert "machine learning" in snippet.lower()
        count = snippet.lower().count("machine")
        assert count >= 2

    def test_extract_window_includes_context(self):
        extractor = SmartSnippetExtractor(max_length=200)
        sentences = [f"Sentence {i} about python programming." for i in range(20)]
        text = " ".join(sentences)
        query_terms = ["python"]
        snippet = extractor.extract(text, query_terms)
        # Should include multiple sentences around the best match
        assert "python" in snippet.lower()
        assert len(snippet) > 30

    def test_extract_single_sentence(self):
        extractor = SmartSnippetExtractor()
        text = "Only one sentence here."
        query_terms = ["sentence"]
        snippet = extractor.extract(text, query_terms)
        assert "sentence" in snippet.lower()

    def test_extract_no_ellipsis_when_fits(self):
        extractor = SmartSnippetExtractor(max_length=500)
        text = "First sentence. Second sentence about python. Third sentence."
        query_terms = ["python"]
        snippet = extractor.extract(text, query_terms)
        # Should not have ellipsis if entire text fits
        assert "..." not in snippet

    def test_score_sentence_weighted_by_term_length(self):
        extractor = SmartSnippetExtractor()
        text = "Short term here. Longer terminology appears here with more weight."
        query_terms = ["term", "terminology"]
        snippet = extractor.extract(text, query_terms)
        # Should prefer sentence with longer matching term
        assert "terminology" in snippet.lower()
