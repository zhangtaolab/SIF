"""Personal-bench domain battery (Phase 18, Plan 02: EVAL-01/EVAL-02).

Pure domain tests: no Click, no Rich, no real index. SearchResult/metric
plumbing is pinned elsewhere (``test_benchmark.py``); this file owns
synthesis determinism, the per-leg overlap budget, classification, splitting,
grouping, and the replay leg.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from sif.core.models import SearchResult
from sif.search.benchmark import QueryEvaluation
from sif.search.personal_bench import (
    EXACT_TERM_LEGS,
    HELDOUT_MIN,
    INITIAL_SAMPLE_DOCUMENTS,
    LANGUAGES,
    LEG_BUDGETS,
    LEGS,
    LENGTH_BUCKETS,
    MAX_SAVED_FILE_BYTES,
    MAX_SAVED_RECORDS,
    MIN_QUERIES,
    OVERLAP_BUDGET,
    SAVED_RUN_VERSION,
    SUPPRESS_BELOW,
    CorpusSummary,
    DocumentRecord,
    GroupMetrics,
    PersonalQueryRecord,
    PersonalReport,
    ReplayResult,
    SavedQueryRecord,
    SavedRun,
    SynthesisResult,
    SynthesizedQuery,
    apply_overlap_budget,
    assign_split,
    body_candidate,
    build_personal_report,
    build_query_records,
    classify_language,
    compare_saved_run,
    corpus_fingerprint,
    dedupe_queries,
    ensure_heldout,
    group_metrics,
    jaccard,
    length_bucket,
    load_replay_queries,
    load_sampled_content,
    load_saved_run,
    noise_gate,
    normalize_text,
    paired_bootstrap,
    replay_leg,
    replay_stability,
    require_matching_corpus,
    require_minimum_queries,
    resolve_saved_targets,
    run_to_saved,
    saved_run_to_dict,
    split_queries,
    strip_markup,
    synthesize_body_queries,
    synthesize_known_item_queries,
    token_set,
    validate_saved_run,
    write_saved_run,
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


# --- Task 3: query_log replay leg ------------------------------------------


def _query_log_db(queries: list[str]) -> sqlite3.Connection:
    """In-memory query_log with the production columns (history() source)."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE query_log (id TEXT PRIMARY KEY, query TEXT NOT NULL,"
        " result_count INTEGER NOT NULL DEFAULT 0,"
        " collections TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL)"
    )
    conn.executemany(
        "INSERT INTO query_log (id, query, result_count, collections, created_at)"
        " VALUES (?, ?, 0, '[]', ?)",
        [
            (f"log-{index}", query, f"2026-11-14T00:{index % 60:02d}:00+00:00")
            for index, query in enumerate(queries)
        ],
    )
    conn.commit()
    return conn


def _path_result(path: str) -> object:
    from sif.core.models import SearchResult

    return SearchResult(
        document_id=f"id-{path}",
        title="title",
        path=path,
        collection_name="collection",
        score=1.0,
    )


class TestReplay:
    def test_empty_query_log_yields_an_unavailable_leg(self) -> None:
        conn = _query_log_db([])

        assert load_replay_queries(conn) == []
        replay = replay_leg([], lambda _query: [])

        assert replay.available is False
        assert replay.num_queries == 0
        assert replay.baseline_available is False
        assert replay.top_k_paths == {}
        assert "stability" in replay.bias
        assert "CLI" in replay.bias

    def test_queries_are_normalized_deduped_and_sorted(self) -> None:
        conn = _query_log_db(["Zeta", "alpha", "  ALPHA  ", "beta"])

        assert load_replay_queries(conn) == ["alpha", "beta", "zeta"]

    def test_replay_queries_are_capped_at_500(self) -> None:
        conn = _query_log_db([f"query {index:04d}" for index in range(600)])

        queries = load_replay_queries(conn)

        assert len(queries) == 500
        assert queries[0] == "query 0000"
        assert queries[-1] == "query 0499"

    def test_one_search_per_query_with_rank_ordered_paths(self) -> None:
        calls: list[str] = []

        def search(query: str) -> list:
            calls.append(query)
            return [_path_result(f"/p/{query}/{index}.md") for index in range(12)]

        replay = replay_leg(["alpha", "beta"], search, k=10)

        assert calls == ["alpha", "beta"]
        assert replay.available is True
        assert replay.num_queries == 2
        assert replay.top_k_paths["alpha"] == [f"/p/alpha/{index}.md" for index in range(10)]
        assert replay.top_k_paths["beta"] == [f"/p/beta/{index}.md" for index in range(10)]

    def test_duplicate_text_collapses_to_one_search_and_record(self) -> None:
        calls: list[str] = []

        def search(query: str) -> list:
            calls.append(query)
            return [_path_result(f"/p/{query}.md")]

        replay = replay_leg([" Alpha ", "alpha"], search, k=10)

        assert calls == ["alpha"]
        assert list(replay.top_k_paths) == ["alpha"]
        assert replay.num_queries == 1

    def test_group_metrics_never_include_replay_records(self) -> None:
        records = [_record("title", "en", "long") for _ in range(10)]
        records.append(_record("replay", "en", "long"))

        groups, suppressed = group_metrics(records)

        assert [(g.leg, g.language, g.length_bucket) for g in groups] == [("title", "en", "long")]
        assert suppressed == []

    def test_known_item_report_sections_ignore_replay(self) -> None:
        def make(replay: ReplayResult) -> dict:
            records = [_record("title", "en", "long") for _ in range(10)]
            report = PersonalReport(
                retrieval="hybrid",
                top_k=10,
                corpus=CorpusSummary(60, 50, "f" * 16, False),
                model=None,
                metrics={"ndcg_at_10": 1.0, "hit_at_10": 1.0, "num_queries": 10},
                splits={"tuning": 10, "heldout": 0},
                groups=[GroupMetrics("title", "en", "long", 10, 1.0, 1.0)],
                suppressed=[],
                queries={"accepted": 10, "by_leg": {}},
                records=records,
                replay=replay,
                notes=[],
            )
            return report.to_dict()

        without = make(ReplayResult(False, 0, False, {}, "bias"))
        with_replay = make(ReplayResult(True, 1, False, {"alpha": ["/p/a.md"]}, "bias"))

        assert without["metrics"] == with_replay["metrics"]
        assert without["splits"] == with_replay["splits"]
        assert without["groups"] == with_replay["groups"]
        assert without["queries"] == with_replay["queries"]
        assert without["replay"] != with_replay["replay"]


class TestMinimumGuard:
    def test_below_the_floor_raises_with_the_counted_breakdown(self) -> None:
        synthesis = SynthesisResult(
            queries=[_query("alpha", doc=1), _query("beta", doc=2)],
            rejected_empty={"title": 1, "body": 2},
            rejected_duplicate={"title": 1, "body": 0},
            rejected_overlap={"title": 0, "body": 3},
        )

        with pytest.raises(ValueError, match="accepted 2") as excinfo:
            require_minimum_queries(synthesis)

        message = str(excinfo.value)
        assert "rejected 7" in message
        assert "3 empty" in message
        assert "1 duplicate" in message
        assert "3 overlap" in message

    def test_at_the_floor_passes(self) -> None:
        synthesis = SynthesisResult(
            queries=[_query(f"query {index}", doc=index) for index in range(MIN_QUERIES)],
            rejected_empty={"title": 0, "body": 0},
            rejected_duplicate={"title": 0, "body": 0},
            rejected_overlap={"title": 0, "body": 0},
        )

        require_minimum_queries(synthesis)


class TestOrchestratorContentLoading:
    def test_bodies_load_only_for_the_given_records(self) -> None:
        content = _long_prose("candidate sentence about retrieval quality")
        conn = _RecordingConnection({"doc-1": content})
        metadata = [_doc(1, title="Alpha", content=None)]

        result = synthesize_known_item_queries(metadata, conn)  # type: ignore[arg-type]

        assert conn.calls[0][1] == ["doc-1"]
        assert [query.leg for query in result.queries] == ["title", "body"]


# --- Task 1: versioned saved runs -------------------------------------------


def _saved_record(
    *,
    query: str = "alpha beta",
    target_doc_id: str = "doc-1",
    target_path: str = "/corpus/1.md",
    leg: str = "title",
    split: str = "tuning",
    retrieved: list[str] | None = None,
    retrieved_doc_ids: list[str] | None = None,
) -> PersonalQueryRecord:
    """One report record with rank-aligned retrieval arrays for saving."""
    return PersonalQueryRecord(
        query=query,
        target_doc_id=target_doc_id,
        target_path=target_path,
        leg=leg,
        language="en",
        length_bucket="long",
        split=split,
        ndcg_at_10=1.0,
        hit_at_10=1.0,
        retrieved_doc_ids=(
            retrieved_doc_ids if retrieved_doc_ids is not None else [target_doc_id, ""]
        ),
        retrieved_paths=(retrieved if retrieved is not None else [target_path, "/corpus/9.md"]),
    )


def _report_for_saved_runs() -> PersonalReport:
    """A two-query report carrying every field ``run_to_saved`` consumes."""
    records = [
        _saved_record(),
        _saved_record(
            query="gamma delta",
            target_doc_id="doc-2",
            target_path="/corpus/2.md",
            leg="body",
            split="heldout",
        ),
    ]
    return PersonalReport(
        retrieval="hybrid",
        top_k=10,
        corpus=CorpusSummary(
            documents=60,
            sampled=50,
            fingerprint="0123456789abcdef",
            widened=False,
        ),
        model={"model_name": "m", "model_type": "t", "dimension": 8},
        metrics={"ndcg_at_10": 1.0, "hit_at_10": 1.0, "num_queries": 2},
        splits={"tuning": 1, "heldout": 1},
        groups=[],
        suppressed=[],
        queries={
            "accepted": 2,
            "rejected_empty": 0,
            "rejected_duplicate": 0,
            "rejected_overlap": 0,
            "by_leg": {},
        },
        records=records,
        replay=ReplayResult(
            available=True,
            num_queries=1,
            baseline_available=False,
            top_k_paths={"alpha": ["/p/a.md", "/p/b.md"]},
            bias="bias",
        ),
        notes=["note"],
    )


def _saved_dict() -> dict:
    """The canonical serialized saved run (validated by construction)."""
    return saved_run_to_dict(run_to_saved(_report_for_saved_runs()))


def _all_keys(value: object) -> set[str]:
    """Every dict key anywhere in a JSON-shaped payload."""
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            keys |= _all_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            keys |= _all_keys(nested)
    return keys


class TestSavedRunContract:
    def test_round_trips_with_version_fixed_order_and_no_content(self) -> None:
        run = run_to_saved(_report_for_saved_runs())
        data = saved_run_to_dict(run)

        assert data["version"] == SAVED_RUN_VERSION == 1
        assert list(data) == [
            "version",
            "created_at",
            "top_k",
            "corpus",
            "retrieval",
            "model",
            "queries",
            "replay",
        ]
        assert list(data["corpus"]) == ["fingerprint", "documents", "sampled"]
        assert list(data["queries"][0]) == [
            "query",
            "target_path",
            "target_doc_id",
            "leg",
            "language",
            "length_bucket",
            "split",
            "grade",
            "retrieved",
            "retrieved_doc_ids",
        ]
        assert list(data["replay"]) == ["available", "queries"]
        assert validate_saved_run(data) == run
        assert not ({"content", "body", "snippet", "embedding"} & _all_keys(data))

    def test_created_at_is_a_utc_iso_timestamp_stamped_by_run_to_saved(self) -> None:
        run = run_to_saved(_report_for_saved_runs())

        assert run.created_at.endswith("+00:00")
        assert "T" in run.created_at

    def test_top_k_and_retrieved_arrays_are_rank_aligned(self) -> None:
        report = _report_for_saved_runs()
        run = run_to_saved(report)

        assert run.top_k == report.top_k == 10
        for record in run.queries:
            assert len(record.retrieved) == len(record.retrieved_doc_ids)

    def test_write_and_load_round_trip(self, tmp_path: Path) -> None:
        run = run_to_saved(_report_for_saved_runs())
        path = tmp_path / "eval" / "eval-run.json"

        write_saved_run(run, path)

        assert path.exists()
        assert load_saved_run(path) == run

    def test_saved_file_contains_no_document_body_text(self, tmp_path: Path) -> None:
        run = run_to_saved(_report_for_saved_runs())
        path = tmp_path / "eval-run.json"

        write_saved_run(run, path)
        text = path.read_text(encoding="utf-8")

        assert '"content"' not in text
        assert '"body":' not in text
        assert "Document body" not in text


_ENVELOPE_DEFECTS = [
    ("root-not-object", lambda _data: [], "root"),
    (
        "missing-version",
        lambda data: {key: value for key, value in data.items() if key != "version"},
        "version",
    ),
    ("version-not-int", lambda data: {**data, "version": "1"}, "version"),
    ("version-bool", lambda data: {**data, "version": True}, "version"),
    ("wrong-version", lambda data: {**data, "version": 2}, "version"),
    ("created-at-not-str", lambda data: {**data, "created_at": 5}, "created_at"),
    (
        "corpus-missing",
        lambda data: {key: value for key, value in data.items() if key != "corpus"},
        "corpus",
    ),
    ("corpus-not-dict", lambda data: {**data, "corpus": []}, "corpus"),
    (
        "fingerprint-not-str",
        lambda data: {**data, "corpus": {**data["corpus"], "fingerprint": 5}},
        "corpus.fingerprint",
    ),
    (
        "fingerprint-empty",
        lambda data: {**data, "corpus": {**data["corpus"], "fingerprint": ""}},
        "corpus.fingerprint",
    ),
    (
        "fingerprint-too-long",
        lambda data: {**data, "corpus": {**data["corpus"], "fingerprint": "x" * 65}},
        "corpus.fingerprint",
    ),
    (
        "documents-not-int",
        lambda data: {**data, "corpus": {**data["corpus"], "documents": "60"}},
        "corpus.documents",
    ),
    (
        "documents-bool",
        lambda data: {**data, "corpus": {**data["corpus"], "documents": True}},
        "corpus.documents",
    ),
    (
        "sampled-not-int",
        lambda data: {**data, "corpus": {**data["corpus"], "sampled": 1.5}},
        "corpus.sampled",
    ),
    (
        "sampled-nan",
        lambda data: {
            **data,
            "corpus": {**data["corpus"], "sampled": float("nan")},
        },
        "corpus.sampled",
    ),
    (
        "sampled-negative",
        lambda data: {**data, "corpus": {**data["corpus"], "sampled": -1}},
        "corpus.sampled",
    ),
    (
        "sampled-exceeds-documents",
        lambda data: {
            **data,
            "corpus": {
                **data["corpus"],
                "sampled": data["corpus"]["documents"] + 1,
            },
        },
        "corpus.sampled",
    ),
    ("retrieval-unknown", lambda data: {**data, "retrieval": "vector"}, "retrieval"),
    (
        "top-k-missing",
        lambda data: {key: value for key, value in data.items() if key != "top_k"},
        "top_k",
    ),
    ("top-k-not-int", lambda data: {**data, "top_k": "10"}, "top_k"),
    ("top-k-bool", lambda data: {**data, "top_k": True}, "top_k"),
    ("top-k-zero", lambda data: {**data, "top_k": 0}, "top_k"),
    ("top-k-infinity", lambda data: {**data, "top_k": float("inf")}, "top_k"),
    ("model-not-dict", lambda data: {**data, "model": []}, "model"),
    (
        "model-name-not-str",
        lambda data: {**data, "model": {**data["model"], "model_name": 5}},
        "model.model_name",
    ),
    (
        "model-dimension-zero",
        lambda data: {**data, "model": {**data["model"], "dimension": 0}},
        "model.dimension",
    ),
    ("queries-not-list", lambda data: {**data, "queries": {}}, "queries"),
    ("queries-empty", lambda data: {**data, "queries": []}, "queries"),
    (
        "queries-too-many",
        lambda data: {
            **data,
            "queries": [data["queries"][0]] * (MAX_SAVED_RECORDS + 1),
        },
        "queries",
    ),
    ("replay-not-dict", lambda data: {**data, "replay": []}, "replay"),
    (
        "replay-available-not-bool",
        lambda data: {**data, "replay": {"available": "yes", "queries": []}},
        "replay.available",
    ),
    (
        "replay-queries-not-list",
        lambda data: {**data, "replay": {"available": True, "queries": {}}},
        "replay.queries",
    ),
    (
        "replay-entry-not-dict",
        lambda data: {
            **data,
            "replay": {"available": True, "queries": ["alpha"]},
        },
        "replay.queries[0]",
    ),
    (
        "replay-entry-missing-top-k-paths",
        lambda data: {
            **data,
            "replay": {"available": True, "queries": [{"query": "alpha"}]},
        },
        "replay.queries[0].top_k_paths",
    ),
    (
        "replay-path-not-str",
        lambda data: {
            **data,
            "replay": {
                "available": True,
                "queries": [{"query": "alpha", "top_k_paths": [1]}],
            },
        },
        "replay.queries[0].top_k_paths[0]",
    ),
]


@pytest.mark.parametrize(
    ("mutator", "field"),
    [(mutator, field) for _label, mutator, field in _ENVELOPE_DEFECTS],
    ids=[label for label, _mutator, _field in _ENVELOPE_DEFECTS],
)
def test_envelope_defects_raise_value_error_naming_the_field(
    mutator: object,
    field: str,
) -> None:
    data = mutator(_saved_dict())  # type: ignore[operator]

    with pytest.raises(ValueError, match=re.escape(field)):
        validate_saved_run(data)


_RECORD_DEFECTS = [
    ("query-not-str", lambda record: {**record, "query": 5}, "queries[0].query"),
    (
        "query-too-long",
        lambda record: {**record, "query": "x" * 10_001},
        "queries[0].query",
    ),
    (
        "target-path-not-str",
        lambda record: {**record, "target_path": 5},
        "queries[0].target_path",
    ),
    (
        "target-doc-id-not-str",
        lambda record: {**record, "target_doc_id": 5},
        "queries[0].target_doc_id",
    ),
    ("grade-zero", lambda record: {**record, "grade": 0}, "queries[0].grade"),
    ("grade-bool", lambda record: {**record, "grade": True}, "queries[0].grade"),
    ("grade-two", lambda record: {**record, "grade": 2}, "queries[0].grade"),
    (
        "split-unknown",
        lambda record: {**record, "split": "validation"},
        "queries[0].split",
    ),
    ("leg-replay", lambda record: {**record, "leg": "replay"}, "queries[0].leg"),
    ("leg-bogus", lambda record: {**record, "leg": "bogus"}, "queries[0].leg"),
    (
        "language-unknown",
        lambda record: {**record, "language": "fr"},
        "queries[0].language",
    ),
    (
        "length-unknown",
        lambda record: {**record, "length_bucket": "tiny"},
        "queries[0].length_bucket",
    ),
    (
        "retrieved-not-list",
        lambda record: {**record, "retrieved": {}},
        "queries[0].retrieved",
    ),
    (
        "retrieved-element-not-str",
        lambda record: {**record, "retrieved": [1]},
        "queries[0].retrieved[0]",
    ),
    (
        "retrieved-path-too-long",
        lambda record: {**record, "retrieved": ["x" * 4_097]},
        "queries[0].retrieved[0]",
    ),
    (
        "retrieved-doc-ids-not-list",
        lambda record: {**record, "retrieved_doc_ids": {}},
        "queries[0].retrieved_doc_ids",
    ),
    (
        "retrieved-doc-ids-element-not-str",
        lambda record: {**record, "retrieved_doc_ids": [1]},
        "queries[0].retrieved_doc_ids[0]",
    ),
    (
        "retrieved-doc-ids-too-long",
        lambda record: {**record, "retrieved_doc_ids": ["x" * 513]},
        "queries[0].retrieved_doc_ids[0]",
    ),
    (
        "retrieved-not-rank-aligned",
        lambda record: {
            **record,
            "retrieved_doc_ids": record["retrieved_doc_ids"][:-1],
        },
        "queries[0].retrieved_doc_ids",
    ),
    (
        "content-key",
        lambda record: {**record, "content": "secret body"},
        "queries[0].content",
    ),
    (
        "snippet-key",
        lambda record: {**record, "snippet": "secret body"},
        "queries[0].snippet",
    ),
]


@pytest.mark.parametrize(
    ("mutator", "field"),
    [(mutator, field) for _label, mutator, field in _RECORD_DEFECTS],
    ids=[label for label, _mutator, _field in _RECORD_DEFECTS],
)
def test_record_defects_raise_value_error_naming_the_field(
    mutator: object,
    field: str,
) -> None:
    data = _saved_dict()
    data["queries"] = [mutator(dict(data["queries"][0]))]  # type: ignore[operator]

    with pytest.raises(ValueError, match=re.escape(field)):
        validate_saved_run(data)


def test_load_rejects_an_oversized_file_before_decoding(tmp_path: Path) -> None:
    path = tmp_path / "oversized.json"
    path.write_text("x" * (MAX_SAVED_FILE_BYTES + 1), encoding="utf-8")

    with pytest.raises(ValueError, match="cap"):
        load_saved_run(path)


def test_load_translates_corrupt_and_missing_files_to_value_error(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError, match="saved run"):
        load_saved_run(corrupt)
    with pytest.raises(ValueError, match="saved run"):
        load_saved_run(tmp_path / "missing.json")


def test_load_treats_saved_paths_as_opaque_values(tmp_path: Path) -> None:
    data = _saved_dict()
    data["queries"][0]["target_path"] = "/nonexistent/target.md"
    data["queries"][0]["retrieved"] = ["/nonexistent/retrieved.md"]
    data["queries"][0]["retrieved_doc_ids"] = ["doc-1"]
    path = tmp_path / "opaque.json"
    path.write_text(__import__("json").dumps(data), encoding="utf-8")

    assert load_saved_run(path).queries[0].target_path == "/nonexistent/target.md"


class TestCorpusFingerprint:
    def test_same_corpus_is_stable_and_order_independent(self) -> None:
        docs = [_doc(index) for index in range(5)]

        assert corpus_fingerprint(docs) == corpus_fingerprint(list(reversed(docs)))

    def test_checksum_and_file_size_changes_move_the_fingerprint(self) -> None:
        docs = [_doc(index) for index in range(3)]
        base = corpus_fingerprint(docs)

        changed_checksum = [replace(docs[0], checksum="different"), *docs[1:]]
        changed_size = [replace(docs[0], file_size=docs[0].file_size + 1), *docs[1:]]
        same_content_identity = [
            replace(docs[0], title="A different title", content="a body"),
            *docs[1:],
        ]

        assert corpus_fingerprint(changed_checksum) != base
        assert corpus_fingerprint(changed_size) != base
        # Title/content (and therefore mtime-like metadata) are excluded.
        assert corpus_fingerprint(same_content_identity) == base


# --- Task 2: paired bootstrap, noise gate, comparison ------------------------


def _saved_query(
    query: str,
    *,
    target_doc_id: str = "doc-1",
    target_path: str = "/corpus/1.md",
    leg: str = "title",
    language: str = "en",
    length_bucket: str = "long",
    split: str = "heldout",
    retrieved: list[str] | None = None,
    retrieved_doc_ids: list[str] | None = None,
) -> SavedQueryRecord:
    """One saved query record with rank-aligned retrieval arrays."""
    return SavedQueryRecord(
        query=query,
        target_path=target_path,
        target_doc_id=target_doc_id,
        leg=leg,
        language=language,
        length_bucket=length_bucket,
        split=split,
        grade=1,
        retrieved=retrieved if retrieved is not None else [target_path],
        retrieved_doc_ids=(retrieved_doc_ids if retrieved_doc_ids is not None else [target_doc_id]),
    )


def _saved_run(
    queries: list[SavedQueryRecord],
    *,
    fingerprint: str,
    retrieval: str = "hybrid",
    top_k: int = 10,
    replay: list[dict] | None = None,
    model: dict | None = None,
) -> SavedRun:
    """A minimal valid saved run for comparison tests."""
    return SavedRun(
        version=SAVED_RUN_VERSION,
        created_at="2026-11-14T00:00:00+00:00",
        top_k=top_k,
        corpus={"fingerprint": fingerprint, "documents": 50, "sampled": 50},
        retrieval=retrieval,
        model=model,
        queries=queries,
        replay={"available": bool(replay), "queries": list(replay or [])},
    )


def _metadata(*pairs: tuple[str, str]) -> list[DocumentRecord]:
    """Current-corpus metadata records (id, path) with stable checksums."""
    return [
        DocumentRecord(
            id=doc_id,
            path=path,
            title=doc_id,
            checksum=doc_id,
            file_size=1,
        )
        for doc_id, path in pairs
    ]


def _compare_conn(*pairs: tuple[str, str]) -> sqlite3.Connection:
    """In-memory current ``documents`` table for target resolution."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE documents (id TEXT PRIMARY KEY, path TEXT NOT NULL)")
    conn.executemany("INSERT INTO documents (id, path) VALUES (?, ?)", list(pairs))
    conn.commit()
    return conn


def _hit(doc_id: str, path: str = "/corpus/1.md") -> SearchResult:
    """A SearchResult carrying the document id both arms grade through."""
    return SearchResult(
        document_id=doc_id,
        title="title",
        path=path,
        collection_name="collection",
        score=1.0,
    )


class TestPairedBootstrap:
    def test_is_deterministic_for_a_fixed_list(self) -> None:
        deltas = [0.1, 0.2, 0.4, 0.0, 0.3]

        first = paired_bootstrap(deltas)
        second = paired_bootstrap(deltas)

        assert first.sufficient is True
        assert (first.mean, first.ci_low, first.ci_high) == (
            second.mean,
            second.ci_low,
            second.ci_high,
        )
        assert first.mean == pytest.approx(0.2)
        assert first.ci_low <= first.mean <= first.ci_high

    def test_zero_variance_positive_list_excludes_zero(self) -> None:
        result = paired_bootstrap([0.1] * 5)

        assert result.mean == pytest.approx(0.1)
        assert result.ci_low == pytest.approx(0.1)
        assert result.ci_high == pytest.approx(0.1)
        assert result.ci_low > 0

    def test_empty_list_is_insufficient(self) -> None:
        result = paired_bootstrap([])

        assert result.sufficient is False
        assert (result.mean, result.ci_low, result.ci_high) == (0.0, 0.0, 0.0)


class TestNoiseGate:
    def test_exactly_one_hundredth_with_a_positive_ci_declares_a_winner(self) -> None:
        gate = noise_gate([0.0] * 10, [0.01] * 10)

        assert gate.n == 10
        assert gate.mean_delta == pytest.approx(0.01)
        assert gate.ci_low > 0
        assert gate.winner is True
        assert gate.regression is False

    def test_below_the_tie_rule_never_declares_a_winner(self) -> None:
        gate = noise_gate([0.0] * 10, [0.0099] * 10)

        assert gate.mean_delta == pytest.approx(0.0099)
        assert gate.ci_low > 0
        assert gate.winner is False

    def test_ci_containing_zero_never_declares_a_winner(self) -> None:
        gate = noise_gate([0.0, 0.0], [0.0, 0.02])

        assert gate.mean_delta == pytest.approx(0.01)
        assert gate.ci_low <= 0 <= gate.ci_high
        assert gate.winner is False

    def test_helped_hurt_unchanged_and_the_one_over_n_floor(self) -> None:
        gate = noise_gate([0.0, 0.5, 0.2], [0.02, 0.49, 0.2])

        assert gate.n == 3
        assert gate.helped == 1
        assert gate.hurt == 1
        assert gate.unchanged == 1
        assert gate.noise_floor == pytest.approx(1 / 3)
        assert gate.sufficient is True

    def test_a_negative_delta_flags_regression_but_never_wins(self) -> None:
        gate = noise_gate([0.5] * 10, [0.4] * 10)

        assert gate.mean_delta == pytest.approx(-0.1)
        assert gate.ci_high < 0
        assert gate.regression is True
        assert gate.winner is False

    def test_empty_series_is_insufficient_and_has_no_floor(self) -> None:
        gate = noise_gate([], [])

        assert gate.sufficient is False
        assert gate.winner is False
        assert gate.regression is False
        assert gate.n == 0
        assert gate.noise_floor == 0.0


class TestReplayStability:
    def test_jaccard_and_top_one_stability_against_the_snapshot(self) -> None:
        saved_replay = {
            "available": True,
            "queries": [{"query": "alpha", "top_k_paths": ["/p/a.md", "/p/b.md"]}],
        }
        current = {"alpha": ["/p/b.md", "/p/c.md"]}

        stability = replay_stability(saved_replay, current)

        assert stability.available is True
        assert stability.baseline_available is True
        assert stability.num_queries == 1
        assert stability.jaccard_at_10 == pytest.approx(1 / 3)
        assert stability.top1_stability == 0.0

    def test_no_saved_snapshot_is_unavailable(self) -> None:
        stability = replay_stability(
            {"available": False, "queries": []},
            {"alpha": ["/p/a.md"]},
        )

        assert stability.available is False
        assert stability.baseline_available is False
        assert "saved" in stability.note.lower()

    def test_no_current_top_k_is_unavailable(self) -> None:
        stability = replay_stability(
            {
                "available": True,
                "queries": [{"query": "alpha", "top_k_paths": ["/p/a.md"]}],
            },
            {},
        )

        assert stability.available is False
        assert stability.baseline_available is True


class TestCompareSavedRun:
    def test_evaluates_exactly_the_saved_queries_in_saved_order(self) -> None:
        pairs = (("doc-1", "/corpus/1.md"), ("doc-2", "/corpus/2.md"))
        metadata = _metadata(*pairs)
        saved = _saved_run(
            [
                _saved_query(
                    "second",
                    target_doc_id="doc-2",
                    target_path="/corpus/2.md",
                    split="heldout",
                ),
                _saved_query(
                    "first",
                    target_doc_id="doc-1",
                    target_path="/corpus/1.md",
                    split="tuning",
                ),
            ],
            fingerprint=corpus_fingerprint(metadata),
        )
        targets = {
            "first": ("doc-1", "/corpus/1.md"),
            "second": ("doc-2", "/corpus/2.md"),
        }
        calls: list[str] = []

        def search(query: str) -> list[SearchResult]:
            calls.append(query)
            doc_id, path = targets[query]
            return [_hit(doc_id, path)]

        comparison = compare_saved_run(
            saved,
            metadata,
            search,
            conn=_compare_conn(*pairs),
            retrieval="bm25",
            model=None,
        )

        assert calls == ["second", "first"]
        assert [record.query for record in comparison.current_report.records] == [
            "second",
            "first",
        ]
        assert [record.split for record in comparison.current_report.records] == [
            "heldout",
            "tuning",
        ]
        assert comparison.current_report.top_k == saved.top_k
        assert comparison.current_metrics["ndcg_at_10"] == pytest.approx(1.0)
        assert comparison.baseline_metrics["ndcg_at_10"] == pytest.approx(1.0)
        assert comparison.overall.mean_delta == pytest.approx(0.0)

    def test_fingerprint_mismatch_refuses_and_names_both_values(self) -> None:
        pairs = (("doc-1", "/corpus/1.md"),)
        metadata = _metadata(*pairs)
        saved = _saved_run(
            [_saved_query("note")],
            fingerprint="savedfingerprint",
        )

        with pytest.raises(ValueError, match="refusing") as excinfo:
            compare_saved_run(
                saved,
                metadata,
                lambda _query: [],
                conn=_compare_conn(*pairs),
                retrieval="bm25",
                model=None,
            )

        message = str(excinfo.value)
        assert "savedfingerprint" in message
        assert corpus_fingerprint(metadata) in message

    def test_target_resolves_by_document_id_before_path(self) -> None:
        pairs = (("doc-a", "/shared.md"), ("doc-b", "/shared.md"))
        metadata = _metadata(*pairs)
        saved = _saved_run(
            [
                _saved_query(
                    "note",
                    target_doc_id="doc-a",
                    target_path="/shared.md",
                    retrieved=["/shared.md"],
                    retrieved_doc_ids=["doc-b"],
                )
            ],
            fingerprint=corpus_fingerprint(metadata),
        )

        comparison = compare_saved_run(
            saved,
            metadata,
            lambda _query: [_hit("doc-b", "/shared.md")],
            conn=_compare_conn(*pairs),
            retrieval="bm25",
            model=None,
        )

        # The current arm grades the other copy as a miss against doc-a, so a
        # shared path cannot turn one arm's retrieval into a hit for the other.
        assert comparison.baseline_metrics["ndcg_at_10"] == 0.0
        assert comparison.current_metrics["ndcg_at_10"] == 0.0
        assert comparison.overall.mean_delta == 0.0

    def test_stale_id_with_an_ambiguous_path_is_a_loud_error(self) -> None:
        pairs = (("doc-a", "/shared.md"), ("doc-b", "/shared.md"))
        metadata = _metadata(*pairs)
        saved = _saved_run(
            [
                _saved_query(
                    "note",
                    target_doc_id="stale",
                    target_path="/shared.md",
                )
            ],
            fingerprint=corpus_fingerprint(metadata),
        )

        with pytest.raises(ValueError, match=re.escape("/shared.md")) as excinfo:
            compare_saved_run(
                saved,
                metadata,
                lambda _query: [],
                conn=_compare_conn(*pairs),
                retrieval="bm25",
                model=None,
            )

        assert "refusing" in str(excinfo.value)

    def test_unique_path_is_the_only_fallback(self) -> None:
        pairs = (("doc-u", "/unique.md"),)
        metadata = _metadata(*pairs)
        saved = _saved_run(
            [
                _saved_query(
                    "note",
                    target_doc_id="stale",
                    target_path="/unique.md",
                    retrieved=["/unique.md"],
                    retrieved_doc_ids=["other"],
                )
            ],
            fingerprint=corpus_fingerprint(metadata),
        )

        comparison = compare_saved_run(
            saved,
            metadata,
            lambda _query: [_hit("doc-u", "/unique.md")],
            conn=_compare_conn(*pairs),
            retrieval="bm25",
            model=None,
        )

        assert comparison.current_metrics["ndcg_at_10"] == pytest.approx(1.0)
        assert comparison.baseline_metrics["ndcg_at_10"] == 0.0
        assert comparison.overall.winner is True
        assert comparison.warrants_default_change is True

    def test_repeated_target_id_counts_once_and_never_exceeds_one(self) -> None:
        pairs = (("doc-1", "/corpus/1.md"),)
        metadata = _metadata(*pairs)
        saved = _saved_run(
            [
                _saved_query(
                    "note",
                    retrieved=["/a", "/b", "/c"],
                    retrieved_doc_ids=["doc-1", "doc-1", "doc-1"],
                )
            ],
            fingerprint=corpus_fingerprint(metadata),
        )

        comparison = compare_saved_run(
            saved,
            metadata,
            lambda _query: [_hit("doc-1", "/corpus/1.md")],
            conn=_compare_conn(*pairs),
            retrieval="bm25",
            model=None,
        )

        assert comparison.baseline_metrics["ndcg_at_10"] == 1.0

    def test_groups_are_declared_order_and_small_groups_are_named(self) -> None:
        pairs = (("doc-1", "/corpus/1.md"),)
        metadata = _metadata(*pairs)
        records = [
            _saved_query(
                f"title {index}",
                leg="title",
                language="en",
                length_bucket="long",
                split="tuning",
                retrieved=["/corpus/1.md"],
                retrieved_doc_ids=["missing"],
            )
            for index in range(5)
        ]
        records += [
            _saved_query(
                f"body {index}",
                leg="body",
                language="zh",
                length_bucket="short",
                split="heldout",
                retrieved=["/corpus/1.md"],
                retrieved_doc_ids=["missing"],
            )
            for index in range(10)
        ]
        saved = _saved_run(records, fingerprint=corpus_fingerprint(metadata))

        comparison = compare_saved_run(
            saved,
            metadata,
            lambda _query: [_hit("doc-1", "/corpus/1.md")],
            conn=_compare_conn(*pairs),
            retrieval="bm25",
            model=None,
        )

        assert [
            (group.leg, group.language, group.length_bucket, group.gate.n)
            for group in comparison.groups
        ] == [("body", "zh", "short", 10)]
        assert comparison.suppressed == ["leg=title/language=en/length=long"]
        assert comparison.groups[0].gate.winner is True
        data = comparison.to_dict()
        assert data["groups"][0]["diagnostic"] is True
        assert data["groups"][0]["n"] == 10
        assert set(data["groups"][0]) >= {
            "mean_delta",
            "ci_low",
            "ci_high",
            "helped",
            "hurt",
            "unchanged",
            "winner",
        }
        assert data["splits"]["tuning"]["diagnostic"] is True
        assert data["splits"]["heldout"]["diagnostic"] is False

    def test_only_the_held_out_gate_warrants_a_defaults_change(self) -> None:
        pairs = (("doc-1", "/corpus/1.md"),)
        metadata = _metadata(*pairs)
        tuning_only = [
            _saved_query(
                f"tuning {index}",
                split="tuning",
                retrieved=["/corpus/1.md"],
                retrieved_doc_ids=["missing"],
            )
            for index in range(10)
        ]
        saved = _saved_run(tuning_only, fingerprint=corpus_fingerprint(metadata))

        comparison = compare_saved_run(
            saved,
            metadata,
            lambda _query: [_hit("doc-1", "/corpus/1.md")],
            conn=_compare_conn(*pairs),
            retrieval="bm25",
            model=None,
        )

        assert comparison.overall.winner is True
        assert comparison.splits["tuning"].winner is True
        assert comparison.splits["heldout"].sufficient is False
        assert comparison.warrants_default_change is False

    def test_replay_stability_uses_the_saved_snapshot(self) -> None:
        pairs = (("doc-1", "/corpus/1.md"),)
        metadata = _metadata(*pairs)
        saved = _saved_run(
            [
                _saved_query(
                    "known",
                    retrieved=["/corpus/1.md"],
                    retrieved_doc_ids=["doc-1"],
                )
            ],
            fingerprint=corpus_fingerprint(metadata),
            replay=[
                {
                    "query": "alpha",
                    "top_k_paths": ["/p/a.md", "/p/b.md"],
                }
            ],
        )

        def search(query: str) -> list[SearchResult]:
            if query == "known":
                return [_hit("doc-1", "/corpus/1.md")]
            return [_hit("rid-0", "/p/b.md"), _hit("rid-1", "/p/c.md")]

        comparison = compare_saved_run(
            saved,
            metadata,
            search,
            conn=_compare_conn(*pairs),
            retrieval="bm25",
            model=None,
        )

        assert comparison.replay.available is True
        assert comparison.replay.baseline_available is True
        assert comparison.replay.jaccard_at_10 == pytest.approx(1 / 3)
        assert comparison.replay.top1_stability == 0.0
        assert comparison.current_report.replay.top_k_paths["alpha"] == [
            "/p/b.md",
            "/p/c.md",
        ]

    def test_no_saved_replay_snapshot_reports_unavailable(self) -> None:
        pairs = (("doc-1", "/corpus/1.md"),)
        metadata = _metadata(*pairs)
        saved = _saved_run(
            [_saved_query("known")],
            fingerprint=corpus_fingerprint(metadata),
        )

        comparison = compare_saved_run(
            saved,
            metadata,
            lambda _query: [_hit("doc-1", "/corpus/1.md")],
            conn=_compare_conn(*pairs),
            retrieval="bm25",
            model=None,
        )

        assert comparison.replay.available is False
        assert comparison.replay.baseline_available is False
        assert comparison.current_report.replay.available is False

    def test_saved_depth_retrieval_and_model_identity_are_carried(self) -> None:
        pairs = (("doc-1", "/corpus/1.md"),)
        metadata = _metadata(*pairs)
        saved = _saved_run(
            [_saved_query("note")],
            fingerprint=corpus_fingerprint(metadata),
            top_k=5,
            retrieval="hybrid",
            model={"model_name": "saved", "model_type": "sentence_transformers", "dimension": 8},
        )

        comparison = compare_saved_run(
            saved,
            metadata,
            lambda _query: [_hit("doc-1")],
            conn=_compare_conn(*pairs),
            retrieval="bm25",
            model={"model_name": "current", "model_type": "sentence_transformers", "dimension": 8},
        )

        assert comparison.top_k == 5
        assert comparison.current_report.top_k == 5
        assert comparison.retrieval == {"saved": "hybrid", "current": "bm25"}
        assert comparison.model_mismatch is True
        data = comparison.to_dict()
        assert data["top_k"] == 5
        assert data["retrieval"] == {"saved": "hybrid", "current": "bm25"}

    def test_empty_saved_query_set_is_refused(self) -> None:
        pairs = (("doc-1", "/corpus/1.md"),)
        metadata = _metadata(*pairs)
        saved = _saved_run([], fingerprint=corpus_fingerprint(metadata))

        with pytest.raises(ValueError, match="empty"):
            compare_saved_run(
                saved,
                metadata,
                lambda _query: [],
                conn=_compare_conn(*pairs),
                retrieval="bm25",
                model=None,
            )

    def test_require_matching_corpus_and_target_resolution_are_shared(self) -> None:
        pairs = (("doc-1", "/corpus/1.md"),)
        metadata = _metadata(*pairs)
        saved = _saved_run(
            [_saved_query("note")],
            fingerprint=corpus_fingerprint(metadata),
        )

        assert require_matching_corpus(saved, metadata) == corpus_fingerprint(metadata)
        assert resolve_saved_targets(saved, _compare_conn(*pairs)) == ["doc-1"]
