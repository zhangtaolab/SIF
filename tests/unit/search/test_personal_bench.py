"""Personal-bench domain battery (Phase 18, Plan 02: EVAL-01/EVAL-02).

Pure domain tests: no Click, no Rich, no real index. SearchResult/metric
plumbing is pinned elsewhere (``test_benchmark.py``); this file owns
synthesis determinism, the per-leg overlap budget, classification, splitting,
grouping, and the replay leg.
"""

from __future__ import annotations

import sqlite3

import pytest

from sif.search.personal_bench import (
    EXACT_TERM_LEGS,
    LEG_BUDGETS,
    OVERLAP_BUDGET,
    DocumentRecord,
    SynthesizedQuery,
    apply_overlap_budget,
    body_candidate,
    classify_language,
    dedupe_queries,
    jaccard,
    length_bucket,
    load_sampled_content,
    strip_markup,
    synthesize_body_queries,
    synthesize_known_item_queries,
    token_set,
)


def _doc(
    index: int,
    *,
    title: str = "",
    content: str = "",
    path: str | None = None,
) -> DocumentRecord:
    """One metadata record; content is pre-loaded (bounded-subset contract)."""
    return DocumentRecord(
        id=f"doc-{index}",
        path=path or f"/corpus/{index}.md",
        title=title,
        checksum=str(index),
        file_size=index,
        content=content,
    )


def _query(
    text: str,
    *,
    leg: str = "body",
    doc: int = 1,
) -> SynthesizedQuery:
    """Minimal synthesized query for budget/dedupe unit tests."""
    return SynthesizedQuery(
        query=text,
        target_doc_id=f"doc-{doc}",
        target_path=f"/corpus/{doc}.md",
        leg=leg,
    )


def _long_prose(candidate: str) -> str:
    """Content whose candidate sentence starts beyond the 200-char window."""
    filler = "Background context without punctuation " * 8
    return f"Opening sentence within the window.\n\n{filler}.\n\n{candidate}"


class TestStripMarkup:
    def test_fenced_code_urls_headings_emphasis_and_comments_are_removed(self) -> None:
        raw = (
            "# Heading\n"
            "Some **bold** and _italic_ text.\n\n"
            "```python\nsecret_code()\n```\n\n"
            "<!-- hidden -->\n"
            "Visit https://example.com/page for context.\n"
        )

        stripped = strip_markup(raw)

        assert "secret_code" not in stripped
        assert "https://example.com" not in stripped
        assert "<!--" not in stripped
        assert "# Heading" not in stripped
        assert "**" not in stripped
        assert "bold" in stripped


class TestBodyCandidate:
    def test_skips_sentences_inside_the_opening_window(self) -> None:
        content = _long_prose(
            "Second candidate sentence discusses retrieval quality and ranking signals.",
        )

        candidate = body_candidate(content)

        assert candidate is not None
        assert candidate.startswith("second candidate sentence discusses retrieval")

    def test_takes_at_most_ten_tokens(self) -> None:
        content = _long_prose(
            "one two three four five six seven eight nine ten eleven twelve thirteen",
        )

        candidate = body_candidate(content)

        assert candidate is not None
        assert len(candidate.split()) == 10

    def test_returns_none_when_every_sentence_is_under_four_tokens(self) -> None:
        assert body_candidate("tiny. words here. ok.") is None
        assert body_candidate("") is None

    def test_short_candidate_sentence_is_never_emitted(self) -> None:
        content = _long_prose("only three tokens")

        candidate = body_candidate(content)

        assert candidate is not None
        assert len(candidate.split()) >= 4
        assert candidate != "only three tokens"

    def test_cjk_ideographs_count_as_one_length_unit_each(self) -> None:
        assert length_bucket("如何配置") == "medium"
        assert length_bucket("你好") == "short"
        assert length_bucket("如何配置混合搜索引擎的权重") == "long"

    def test_token_set_keeps_contiguous_cjk_runs_whole(self) -> None:
        assert token_set("如何配置 混合 Search") == {"如何配置", "混合", "search"}


class TestOverlapBudget:
    def test_exactly_sixty_percent_is_accepted(self) -> None:
        assert jaccard({"a", "b", "c"}, {"a", "b", "c", "d", "e"}) == pytest.approx(0.60)
        query = _query("alpha beta gamma")
        doc = _doc(1, title="alpha beta", content="gamma delta epsilon")

        kept, rejected = apply_overlap_budget([query], {"doc-1": doc})

        assert [q.query for q in kept] == ["alpha beta gamma"]
        assert rejected.get("body", 0) == 0

    def test_over_budget_is_rejected_and_counted(self) -> None:
        assert jaccard({"a", "b", "c", "d"}, {"a", "b", "c", "d", "e", "f"}) > OVERLAP_BUDGET
        query = _query("alpha beta gamma delta")
        doc = _doc(1, title="alpha beta", content="gamma delta epsilon zeta")

        kept, rejected = apply_overlap_budget([query], {"doc-1": doc})

        assert kept == []
        assert rejected == {"body": 1}

    def test_title_leg_is_exact_term_and_never_budgeted(self) -> None:
        query = _query("alpha beta", leg="title")
        doc = _doc(1, title="alpha beta", content="alpha beta gamma")

        kept, rejected = apply_overlap_budget([query], {"doc-1": doc})

        assert kept == [query]
        assert rejected.get("title", 0) == 0

    def test_per_leg_budgets_are_declared(self) -> None:
        assert LEG_BUDGETS["title"] is None
        assert LEG_BUDGETS["body"] == OVERLAP_BUDGET
        assert "title" in EXACT_TERM_LEGS
        assert "replay" not in EXACT_TERM_LEGS


class TestDedupe:
    def test_duplicate_across_title_and_body_keeps_title_and_counts_body(self) -> None:
        body = _query("  Shared   TITLE ", leg="body", doc=2)
        title = _query("Shared Title", leg="title", doc=1)

        kept, rejected = dedupe_queries([body, title])

        assert [query.leg for query in kept] == ["title"]
        assert rejected == {"body": 1}

    def test_dedupe_is_independent_of_input_order(self) -> None:
        body = _query("  Shared   TITLE ", leg="body", doc=2)
        title = _query("Shared Title", leg="title", doc=1)

        first_kept, first_rejected = dedupe_queries([body, title])
        second_kept, second_rejected = dedupe_queries([title, body])

        assert [q.query for q in first_kept] == [q.query for q in second_kept]
        assert first_rejected == second_rejected == {"body": 1}


class TestClassification:
    def test_language_thresholds_are_pinned(self) -> None:
        assert classify_language("hello world") == "en"
        assert classify_language("如何配置") == "zh"
        assert classify_language("hello 世界") == "mixed"

    def test_language_boundaries_are_pinned_at_ten_and_fifty_percent(self) -> None:
        # 1 CJK / 10 non-whitespace chars == 0.1 -> not "en" (< 0.1).
        assert classify_language("abcdefghi世") == "mixed"
        # 2 CJK / 4 non-whitespace chars == 0.5 -> "zh" (>= 0.5).
        assert classify_language("ab世界") == "zh"

    def test_length_buckets_are_pinned_at_two_and_six_units(self) -> None:
        assert length_bucket("one two") == "short"
        assert length_bucket("one two three") == "medium"
        assert length_bucket("one two three four five") == "medium"
        assert length_bucket("one two three four five six") == "long"


class TestBodySynthesis:
    def test_one_body_query_per_document_with_counts(self) -> None:
        docs = [
            _doc(1, title="Alpha", content=_long_prose("first candidate sentence about ranking")),
            _doc(2, title="Beta", content=""),
        ]

        result = synthesize_body_queries(docs)

        assert [query.leg for query in result.queries] == ["body"]
        assert result.queries[0].target_doc_id == "doc-1"
        assert result.rejected_empty == {"body": 1}
        assert result.rejected_duplicate == {}
        assert result.rejected_overlap == {}

    def test_language_and_length_are_populated_on_every_query(self) -> None:
        doc = _doc(
            1,
            title="Alpha",
            content=_long_prose("如何配置混合搜索引擎的权重"),
        )

        result = synthesize_body_queries([doc])

        assert result.queries[0].language == "zh"
        assert result.queries[0].length_bucket == "long"

    def test_orchestrator_emits_title_then_body_and_merges_rejections(self) -> None:
        docs = [
            _doc(
                1,
                title="Alpha note",
                content=_long_prose("candidate sentence about retrieval quality"),
            ),
            _doc(2, title="", content=""),
        ]

        result = synthesize_known_item_queries(docs)

        assert [query.leg for query in result.queries] == ["title", "body"]
        assert result.rejected_empty == {"title": 1, "body": 1}
        assert result.rejected_duplicate == {"title": 0, "body": 0}
        assert result.rejected_overlap == {"title": 0, "body": 0}
        assert result.queries[0].split is None


class _RecordingConnection:
    """sqlite3.Connection stand-in recording every parameterized statement."""

    def __init__(self, rows: dict[str, str]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, list[str]]] = []

    def execute(self, sql: str, params: object = ()) -> list[tuple[str, str]]:
        self.calls.append((sql, list(params)))  # type: ignore[arg-type]
        return [(doc_id, self.rows[doc_id]) for doc_id in params if doc_id in self.rows]  # type: ignore[union-attr]


class TestLoadSampledContent:
    def test_content_is_loaded_in_bounded_chunks(self) -> None:
        conn = _RecordingConnection({"a": "body a", "b": "body b", "c": "body c"})

        loaded = load_sampled_content(conn, ["a", "b", "c"], chunk_size=2)  # type: ignore[arg-type]

        assert loaded == {"a": "body a", "b": "body b", "c": "body c"}
        assert len(conn.calls) == 2
        assert all(call[1] for call in conn.calls)
        assert all("content" in call[0].lower() for call in conn.calls)

    def test_duplicate_ids_are_queried_once(self) -> None:
        conn = _RecordingConnection({"a": "body a"})

        loaded = load_sampled_content(conn, ["a", "a"], chunk_size=2)  # type: ignore[arg-type]

        assert loaded == {"a": "body a"}
        assert conn.calls[0][1] == ["a"]

    def test_real_sqlite_round_trip(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE documents (id TEXT PRIMARY KEY, content TEXT NOT NULL)")
        conn.executemany(
            "INSERT INTO documents (id, content) VALUES (?, ?)",
            [("doc-1", "first body"), ("doc-2", "second body")],
        )

        assert load_sampled_content(conn, ["doc-2", "missing"]) == {"doc-2": "second body"}
