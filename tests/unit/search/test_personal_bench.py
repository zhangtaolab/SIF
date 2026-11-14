"""Personal-bench domain battery (Phase 18, Plan 02: EVAL-01/EVAL-02).

Pure domain tests: no Click, no Rich, no real index. SearchResult/metric
plumbing is pinned elsewhere (``test_benchmark.py``); this file owns
synthesis determinism, the per-leg overlap budget, classification, splitting,
grouping, and the replay leg.
"""

from __future__ import annotations

import hashlib
import sqlite3

import pytest

from sif.search.benchmark import QueryEvaluation
from sif.search.personal_bench import (
    EXACT_TERM_LEGS,
    HELDOUT_MIN,
    INITIAL_SAMPLE_DOCUMENTS,
    LANGUAGES,
    LEG_BUDGETS,
    LEGS,
    LENGTH_BUCKETS,
    MIN_QUERIES,
    OVERLAP_BUDGET,
    SUPPRESS_BELOW,
    CorpusSummary,
    DocumentRecord,
    GroupMetrics,
    PersonalQueryRecord,
    PersonalReport,
    ReplayResult,
    SynthesisResult,
    SynthesizedQuery,
    apply_overlap_budget,
    assign_split,
    body_candidate,
    build_personal_report,
    build_query_records,
    classify_language,
    dedupe_queries,
    ensure_heldout,
    group_metrics,
    jaccard,
    length_bucket,
    load_sampled_content,
    normalize_text,
    split_queries,
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


# --- Task 2: deterministic split, held-out widening, groups, report ---------


def _long_body(index: int, candidate: str) -> str:
    """Body whose candidate sentence starts beyond the 200-char window."""
    filler = (
        "Introductory context for this note spans several sentences of background "
        "material so the candidate prose sits beyond the opening synthesis window. "
        "Additional context keeps the note realistic and moves the useful sentence "
        "further down the document body. "
    )
    return f"Intro note {index}. {filler}{candidate}."


def _body_candidate_text(index: int) -> str:
    """The body query text a ``_long_body`` document synthesizes."""
    return f"candidate query {index} discusses retrieval quality sampling metrics"


def _tuning_bodies(count: int) -> list[str]:
    """Bodies whose body-leg query text lands in the tuning split."""
    bodies: list[str] = []
    index = 0
    while len(bodies) < count:
        candidate = _body_candidate_text(index)
        if assign_split(candidate) == "tuning":
            bodies.append(_long_body(index, candidate))
        index += 1
    return bodies


def _titles_with_split(count: int, split: str, start: int = 0) -> list[str]:
    """Distinct titles whose title-leg query text lands in ``split``."""
    titles: list[str] = []
    index = start
    while len(titles) < count:
        candidate = f"Note group {index} about topic {index * 7}"
        if assign_split(candidate) == split:
            titles.append(candidate)
        index += 1
    return titles


def _records_for_metadata(
    bodies: list[str],
    *,
    path_prefix: str = "/corpus",
) -> list[DocumentRecord]:
    """Metadata records with the checksum the DB builder will store."""
    return [
        DocumentRecord(
            id=f"doc-{index:03d}",
            path=f"{path_prefix}/{index:03d}.md",
            title="",
            checksum=hashlib.sha256(body.encode()).hexdigest(),
            file_size=len(body.encode()),
        )
        for index, body in enumerate(bodies)
    ]


class TestSplit:
    def test_assign_split_is_stable_and_matches_the_sha256_rule(self) -> None:
        texts = ["alpha beta", "gamma", "如何配置检索", "note 1", "another query"]
        for text in texts:
            digest = hashlib.sha256(normalize_text(text).encode("utf-8")).digest()
            expected = "tuning" if digest[0] < 128 else "heldout"
            assert assign_split(text) == expected
            assert assign_split(f"  {text.upper()}  ") == expected

    def test_split_queries_leaves_replay_splitless(self) -> None:
        title = _query("alpha beta", leg="title")
        body = _query("gamma delta epsilon four", leg="body")
        replay = _query("logged query", leg="replay")

        split = split_queries([title, body, replay])

        assert split[0].split == assign_split("alpha beta")
        assert split[1].split == assign_split("gamma delta epsilon four")
        assert split[2].split is None


class TestEnsureHeldout:
    def test_widens_to_the_cap_when_the_initial_slice_has_too_few_held_out(self) -> None:
        bodies = _tuning_bodies(60)
        metadata = _records_for_metadata(bodies)
        initial_ids = {
            doc.id
            for doc in __import__(
                "sif.search.personal_bench", fromlist=["sample_documents"]
            ).sample_documents(metadata, limit=INITIAL_SAMPLE_DOCUMENTS)
        }
        initial = [doc for doc in metadata if doc.id in initial_ids]
        outside = [doc for doc in metadata if doc.id not in initial_ids]

        heldout_titles = _titles_with_split(24, "heldout", start=1000)
        tuning_titles = _titles_with_split(len(initial) - 24, "tuning", start=2000)
        outside_titles = _titles_with_split(len(outside), "heldout", start=3000)
        title_by_id: dict[str, str] = {}
        for doc, title in zip(initial[: len(heldout_titles)], heldout_titles, strict=False):
            title_by_id[doc.id] = title
        for doc, title in zip(initial[len(heldout_titles) :], tuning_titles, strict=False):
            title_by_id[doc.id] = title
        for doc, title in zip(outside, outside_titles, strict=False):
            title_by_id[doc.id] = title
        titled = [
            DocumentRecord(
                id=doc.id,
                path=doc.path,
                title=title_by_id[doc.id],
                checksum=doc.checksum,
                file_size=doc.file_size,
            )
            for doc in metadata
        ]
        conn = _RecordingConnection(
            {doc.id: bodies[int(doc.id.split("-")[1])] for doc in titled},
        )

        sampled, synthesis = ensure_heldout(titled, conn)  # type: ignore[arg-type]

        assert len(sampled) == 60
        assert sum(1 for q in synthesis.queries if q.split == "heldout") >= HELDOUT_MIN
        # Bodies were loaded for the initial slice, then only for the 10 new docs.
        assert [len(call[1]) for call in conn.calls] == [50, 10]

    def test_impossible_floor_at_the_cap_raises_a_counted_value_error(self) -> None:
        bodies = _tuning_bodies(50)
        metadata = _records_for_metadata(bodies)
        titles = _titles_with_split(50, "tuning", start=0)
        titled = [
            DocumentRecord(
                id=doc.id,
                path=doc.path,
                title=title,
                checksum=doc.checksum,
                file_size=doc.file_size,
            )
            for doc, title in zip(metadata, titles, strict=True)
        ]
        conn = _RecordingConnection({doc.id: bodies[int(doc.id.split("-")[1])] for doc in titled})

        with pytest.raises(ValueError, match="held-out") as excinfo:
            ensure_heldout(titled, conn)  # type: ignore[arg-type]

        message = str(excinfo.value)
        assert "held-out" in message
        assert "tuning" in message
        assert "accepted" in message

    def test_no_widening_when_the_floors_are_met(self) -> None:
        bodies = _tuning_bodies(50)
        metadata = _records_for_metadata(bodies)
        titles = _titles_with_split(24, "tuning", start=0) + _titles_with_split(
            26, "heldout", start=5000
        )
        titled = [
            DocumentRecord(
                id=doc.id,
                path=doc.path,
                title=title,
                checksum=doc.checksum,
                file_size=doc.file_size,
            )
            for doc, title in zip(metadata, titles, strict=True)
        ]
        conn = _RecordingConnection({doc.id: bodies[int(doc.id.split("-")[1])] for doc in titled})

        sampled, synthesis = ensure_heldout(titled, conn)  # type: ignore[arg-type]

        assert len(sampled) == 50
        assert len(conn.calls) == 1
        assert len(synthesis.queries) >= MIN_QUERIES
        assert sum(1 for q in synthesis.queries if q.split == "heldout") >= HELDOUT_MIN


def _record(
    leg: str,
    language: str,
    length_bucket: str,
    *,
    ndcg: float = 1.0,
    hit: float = 1.0,
) -> PersonalQueryRecord:
    return PersonalQueryRecord(
        query="query",
        target_doc_id="doc-1",
        target_path="/corpus/1.md",
        leg=leg,
        language=language,
        length_bucket=length_bucket,
        split="tuning",
        ndcg_at_10=ndcg,
        hit_at_10=hit,
        retrieved_doc_ids=["doc-1"],
        retrieved_paths=["/corpus/1.md"],
    )


class TestGroups:
    def test_nine_query_group_is_suppressed_and_named(self) -> None:
        records = [_record("title", "en", "long") for _ in range(9)]
        records += [_record("body", "zh", "short") for _ in range(10)]

        groups, suppressed = group_metrics(records)

        assert [(g.leg, g.language, g.length_bucket) for g in groups] == [("body", "zh", "short")]
        assert suppressed == ["leg=title/language=en/length=long"]

    def test_groups_follow_declared_order_and_are_means(self) -> None:
        records = [_record("title", "en", "short") for _ in range(10)]
        records += [_record("title", "zh", "medium") for _ in range(10)]
        records += [_record("body", "en", "long") for _ in range(10)]
        records += [_record("body", "mixed", "short") for _ in range(10)]
        records[0] = _record("title", "en", "short", ndcg=0.0, hit=0.0)

        groups, suppressed = group_metrics(records)

        assert suppressed == []
        assert [(g.leg, g.language, g.length_bucket) for g in groups] == [
            ("title", "en", "short"),
            ("title", "zh", "medium"),
            ("body", "en", "long"),
            ("body", "mixed", "short"),
        ]
        assert groups[0].count == 10
        assert groups[0].ndcg_at_10 == pytest.approx(0.9)

    def test_declared_axes_are_the_report_vocabulary(self) -> None:
        assert LEGS == ("title", "body", "replay")
        assert LANGUAGES == ("en", "zh", "mixed")
        assert LENGTH_BUCKETS == ("short", "medium", "long")
        assert SUPPRESS_BELOW == 10


class TestPersonalReport:
    def test_records_are_rank_aligned_with_the_evaluation(self) -> None:
        query = _query("alpha beta", leg="title")
        split = split_queries([query])[0]
        evaluation = QueryEvaluation(
            query=query.query,
            retrieved_keys=["doc-1", ""],
            retrieved_paths=["/corpus/1.md", "/corpus/9.md"],
            grades=[1, 0],
            ndcg_at_10=1.0,
            hit_at_10=1.0,
        )

        records = build_query_records([split], [evaluation])

        assert records[0].retrieved_doc_ids == ["doc-1", ""]
        assert len(records[0].retrieved_doc_ids) == len(records[0].retrieved_paths)

    def test_to_dict_keeps_plan_01_keys_and_adds_the_new_sections(self) -> None:
        records = [_record("title", "en", "long") for _ in range(10)]
        records += [_record("body", "en", "long") for _ in range(10)]
        replay = ReplayResult(
            available=False,
            num_queries=0,
            baseline_available=False,
            top_k_paths={},
            bias="Replay measures stability.",
        )
        report = PersonalReport(
            retrieval="hybrid",
            top_k=10,
            corpus=CorpusSummary(
                documents=60,
                sampled=50,
                fingerprint="0123456789abcdef",
                widened=False,
            ),
            model={"model_name": "m", "model_type": "t", "dimension": 8},
            metrics={"ndcg_at_10": 0.5, "hit_at_10": 0.5, "num_queries": 20},
            splits={"tuning": 20, "heldout": 0},
            groups=[GroupMetrics("title", "en", "long", 10, 1.0, 1.0)],
            suppressed=["leg=body/language=zh/length=short"],
            queries={
                "accepted": 20,
                "rejected_empty": 0,
                "rejected_duplicate": 0,
                "rejected_overlap": 0,
                "by_leg": {},
            },
            records=records,
            replay=replay,
            notes=["note"],
        )

        data = report.to_dict()

        for key in (
            "mode",
            "retrieval",
            "corpus.documents",
            "corpus.sampled",
            "corpus.fingerprint",
            "queries.accepted",
            "queries.rejected_empty",
            "queries.rejected_duplicate",
            "metrics",
            "notes",
            "model",
        ):
            cursor: object = data
            for part in key.split("."):
                cursor = cursor[part]  # type: ignore[index]
        for key in ("top_k", "splits", "groups", "suppressed", "replay"):
            assert key in data
        assert data["groups"] == [
            {
                "leg": "title",
                "language": "en",
                "length_bucket": "long",
                "count": 10,
                "ndcg_at_10": 1.0,
                "hit_at_10": 1.0,
            }
        ]

    def test_build_report_splits_groups_and_metrics_come_from_records(self) -> None:
        queries = [_query("alpha beta", leg="title", doc=1)]
        queries += [_query("gamma delta epsilon four", leg="body", doc=1)]
        split = split_queries(queries)
        evaluations = [
            QueryEvaluation(
                query=q.query,
                retrieved_keys=["doc-1"],
                retrieved_paths=["/corpus/1.md"],
                grades=[1],
                ndcg_at_10=1.0,
                hit_at_10=1.0,
            )
            for q in split
        ]
        synthesis = SynthesisResult(
            queries=split,
            rejected_empty={"title": 0, "body": 0},
            rejected_duplicate={"title": 0, "body": 0},
            rejected_overlap={"title": 0, "body": 0},
        )
        replay = ReplayResult(False, 0, False, {}, "bias")
        metadata = _records_for_metadata(["body one", "body two"])

        report = build_personal_report(
            retrieval="bm25",
            top_k=10,
            metadata=metadata,
            sampled=metadata,
            model=None,
            synthesis=synthesis,
            evaluations=evaluations,
            replay=replay,
            notes=[],
        )

        assert report.metrics["num_queries"] == 2
        assert report.metrics["ndcg_at_10"] == 1.0
        assert sum(report.splits.values()) == 2
        assert report.corpus.documents == 2
        assert report.corpus.sampled == 2
        assert report.corpus.widened is False
        assert report.queries["by_leg"]["title"]["budget"] is None
        assert report.queries["by_leg"]["title"]["exact_term"] is True
        assert report.queries["by_leg"]["body"]["budget"] == pytest.approx(0.60)
