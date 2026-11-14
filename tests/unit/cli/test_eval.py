"""Tests for the personal-eval CLI (Phase 18, EVAL-01)."""

from __future__ import annotations

import hashlib
import json
from contextlib import ExitStack
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner, Result

from sif.cli.commands.eval import eval_group
from sif.config.settings import Settings
from sif.core.models import SearchOptions, SearchResult
from sif.search.benchmark import SearchEvaluator
from sif.search.hybrid import SearchPipeline
from sif.search.personal_bench import (
    HELDOUT_MIN,
    INITIAL_SAMPLE_DOCUMENTS,
    MAX_TOP_K,
    SAVED_RUN_VERSION,
    DocumentRecord,
    assign_split,
    load_saved_run,
    normalize_text,
    sample_documents,
)
from tests.support.bench import EMBEDDING_DIM, ConceptEmbedder
from tests.support.eval import build_personal_db, rewrite_saved_run


_UNSET = object()


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    """Real Settings pinned to the fixture's embedding dimension.

    ``Database.init_schema`` reads ``sif.config.settings.get_settings`` and
    validates the on-disk vec0 dimension against ``embedding_dim``; the same
    real Settings object is patched at both import sites.
    """
    fields: dict[str, Any] = {
        "cache_dir": tmp_path,
        "embedding_dim": EMBEDDING_DIM,
        "model_type": "sentence_transformers",
    }
    fields.update(overrides)
    return Settings(_env_file=None, **fields)


def _manager(embedder: ConceptEmbedder | None = None) -> MagicMock:
    """EmbeddingManager stand-in exposing the concept embedder and its dim."""
    model = embedder or ConceptEmbedder()
    manager = MagicMock()
    manager.model = model
    manager.get_model_info.return_value = {"loaded": True, "embedding_dim": EMBEDDING_DIM}
    return manager


class _SpyPipeline:
    """SearchPipeline stand-in recording every query in call order."""

    seen: ClassVar[list[str]] = []

    def __init__(
        self,
        _connection: object,
        embedder: object | None = None,
        _embedding_dim: int = EMBEDDING_DIM,
        **_kwargs: object,
    ) -> None:
        self.embedder = embedder

    def search(self, query: str, _options: object) -> list:
        _SpyPipeline.seen.append(query)
        return []


def _invoke(
    db_path: Path,
    args: list[str],
    *,
    settings: Settings,
    manager: object = _UNSET,
    manager_side_effect: BaseException | None = None,
    pipeline: object | None = None,
) -> Result:
    """Invoke eval_group with the eval module's seams patched.

    By default ``EmbeddingManager.from_settings`` raises if constructed, so
    ``--bm25-only`` paths prove they never touch the embedder. Pass
    ``manager`` for hybrid runs or ``manager_side_effect`` for failure paths.
    """
    runner = CliRunner()
    with ExitStack() as stack:
        stack.enter_context(
            patch("sif.cli.commands.eval.get_settings", return_value=settings),
        )
        stack.enter_context(
            patch("sif.config.settings.get_settings", return_value=settings),
        )
        if manager_side_effect is not None:
            stack.enter_context(
                patch(
                    "sif.cli.commands.eval.EmbeddingManager.from_settings",
                    side_effect=manager_side_effect,
                ),
            )
        elif manager is not _UNSET:
            stack.enter_context(
                patch(
                    "sif.cli.commands.eval.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
            )
        else:
            stack.enter_context(
                patch(
                    "sif.cli.commands.eval.EmbeddingManager.from_settings",
                    side_effect=AssertionError("embedder constructed on a bm25-only path"),
                ),
            )
        if pipeline is not None:
            stack.enter_context(
                patch("sif.cli.commands.eval.SearchPipeline", pipeline),
            )
        return runner.invoke(eval_group, args, obj={"index_path": db_path})


def _result(document_id: str, path: str = "/p/result.md") -> SearchResult:
    """Minimal SearchResult for direct evaluator tests."""
    return SearchResult(
        document_id=document_id,
        title="title",
        path=path,
        collection_name="collection",
        score=1.0,
    )


_TWO_QUERY_FIXTURE = {
    "queries": [
        {"query": "first", "relevant_docids": ["doc-1"]},
        {"query": "second", "relevant_docids": ["doc-2"]},
    ],
}


def _two_query_search(query: str) -> list[SearchResult]:
    """Target retrieved at rank 1 for 'first'; absent for 'second'."""
    if query == "first":
        return [_result("doc-1")]
    return [_result("doc-9")]


class TestEvaluatePerQuery:
    def test_two_query_fixture_returns_records_in_fixture_order(self) -> None:
        evaluator = SearchEvaluator(_TWO_QUERY_FIXTURE)
        evaluations = evaluator.evaluate_per_query(_two_query_search, k=1)

        assert [evaluation.query for evaluation in evaluations] == ["first", "second"]
        # Target at rank 1 => perfect nDCG@1 and Hit@1; target absent => 0.0.
        assert evaluations[0].ndcg_at_10 == 1.0
        assert evaluations[0].hit_at_10 == 1.0
        assert evaluations[1].ndcg_at_10 == 0.0
        assert evaluations[1].hit_at_10 == 0.0
        assert evaluations[0].retrieved_keys == ["doc-1"]
        assert evaluations[0].grades == [1]
        assert evaluations[1].retrieved_keys == ["doc-9"]
        assert evaluations[1].grades == [0]

    def test_report_to_dict_keeps_exactly_its_pre_change_keys(self) -> None:
        evaluator = SearchEvaluator(_TWO_QUERY_FIXTURE)
        data = evaluator.report(_two_query_search).to_dict()

        assert set(data) == {
            "ndcg_at_10",
            "hit_at_10",
            "num_queries",
            "cold_start_ms",
            "p50_ms",
            "p95_ms",
            "categories",
            "mrr",
            "precision@1",
            "precision@5",
            "precision@10",
            "recall@1",
            "recall@5",
            "recall@10",
        }
        assert "per_query" not in data
        assert data["ndcg_at_10"] == 0.5
        assert data["hit_at_10"] == 0.5
        assert data["num_queries"] == 2
        assert data["mrr"] == 0.5
        assert data["precision@1"] == 0.5
        assert data["recall@1"] == 0.5


class TestSampling:
    def test_sampling_is_order_independent_and_deterministic(self) -> None:
        docs = [
            DocumentRecord(
                id=f"id-{index}",
                path=f"/corpus/{index % 3}.md",
                title=f"Title {index}",
                checksum=str(index),
                file_size=index,
            )
            for index in range(12)
        ]
        first = sample_documents(docs, limit=6)
        second = sample_documents(list(reversed(docs)), limit=6)

        assert [doc.id for doc in first] == [doc.id for doc in second]
        assert len({doc.id for doc in first}) == 6

    def test_shared_path_documents_get_distinct_stable_positions(self) -> None:
        shared = [
            DocumentRecord(
                id="doc-a",
                path="/corpus/shared.md",
                title="A",
                checksum="same",
                file_size=1,
            ),
            DocumentRecord(
                id="doc-b",
                path="/corpus/shared.md",
                title="B",
                checksum="same",
                file_size=1,
            ),
        ]
        assert [doc.id for doc in sample_documents(shared)] == ["doc-a", "doc-b"]
        assert [doc.id for doc in sample_documents(list(reversed(shared)))] == ["doc-a", "doc-b"]

    def test_load_document_metadata_selects_no_content(self) -> None:
        from sif.search.personal_bench import load_document_metadata

        class _RecordingConnection:
            sql = ""

            def execute(self, sql: str, _params: object = ()) -> list:
                _RecordingConnection.sql = sql
                return []

        assert load_document_metadata(_RecordingConnection(), None) == []  # type: ignore[arg-type]
        assert "content" not in _RecordingConnection.sql.lower()


class TestPersonalEvalCli:
    def test_personal_run_renders_table(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        result = _invoke(
            db_path,
            ["--personal"],
            settings=_settings(tmp_path),
            manager=_manager(),
        )

        assert result.exit_code == 0, result.output
        assert "NDCG@10" in result.output
        assert "Hit@10" in result.output
        assert "Documents" in result.output
        assert "Per-leg synthesis" in result.output
        assert "Groups (leg x language x length)" in result.output
        assert "Replay (stability, not quality)" in result.output
        # Bodies never reach output: only counts and metrics are rendered.
        assert "Document body" not in result.output

    def test_personal_json_is_strict_and_shaped(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        result = _invoke(
            db_path,
            ["--personal", "--json"],
            settings=_settings(tmp_path),
            manager=_manager(),
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["mode"] == "personal"
        assert payload["retrieval"] == "hybrid"
        assert payload["top_k"] == 10
        assert payload["corpus"]["documents"] == 60
        # Plan 02 starts from the deterministic 50-document slice; this
        # fixture meets both floors without widening.
        assert payload["corpus"]["sampled"] == INITIAL_SAMPLE_DOCUMENTS
        assert payload["corpus"]["widened"] is False
        assert len(payload["corpus"]["fingerprint"]) == 16
        assert payload["model"] == {
            "model_name": "Qwen/Qwen3-Embedding-0.6B",
            "model_type": "sentence_transformers",
            "dimension": EMBEDDING_DIM,
        }
        # Both known-item legs are synthesized by default.
        assert payload["queries"]["accepted"] == 100
        assert payload["queries"]["rejected_empty"] == 0
        assert payload["queries"]["rejected_duplicate"] == 0
        assert payload["queries"]["rejected_overlap"] == 0
        assert payload["queries"]["by_leg"]["title"]["accepted"] == 50
        assert payload["queries"]["by_leg"]["body"]["accepted"] == 50
        assert payload["queries"]["by_leg"]["title"]["budget"] is None
        assert payload["queries"]["by_leg"]["title"]["exact_term"] is True
        assert payload["queries"]["by_leg"]["body"]["budget"] == pytest.approx(0.60)
        assert payload["metrics"]["num_queries"] == payload["queries"]["accepted"]
        assert isinstance(payload["metrics"]["ndcg_at_10"], float)
        assert isinstance(payload["metrics"]["hit_at_10"], float)
        assert sum(payload["splits"].values()) == 100
        assert payload["splits"]["heldout"] >= HELDOUT_MIN
        # Both 50-query groups are above the suppression floor.
        assert [
            (g["leg"], g["language"], g["length_bucket"], g["count"]) for g in payload["groups"]
        ] == [
            ("title", "en", "long", 50),
            ("body", "en", "long", 50),
        ]
        assert payload["suppressed"] == []
        assert payload["replay"]["available"] is False
        assert payload["replay"]["num_queries"] == 0
        assert "stability" in payload["replay"]["bias"]
        assert payload["notes"]
        assert "content" not in payload
        assert "Document body" not in result.stdout

    def test_two_runs_emit_the_identical_query_order(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path)

        _SpyPipeline.seen = []
        first = _invoke(
            db_path,
            ["--personal", "--bm25-only"],
            settings=settings,
            pipeline=_SpyPipeline,
        )
        first_queries = list(_SpyPipeline.seen)

        _SpyPipeline.seen = []
        second = _invoke(
            db_path,
            ["--personal", "--bm25-only"],
            settings=settings,
            pipeline=_SpyPipeline,
        )

        assert first.exit_code == 0, first.output
        assert second.exit_code == 0, second.output
        assert len(first_queries) == 100
        assert _SpyPipeline.seen == first_queries

    def test_bm25_only_reports_bm25_and_never_builds_embedder(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=_settings(tmp_path),
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["retrieval"] == "bm25"
        assert payload["model"] is None

    def test_eval_without_personal_is_a_usage_error(self) -> None:
        result = CliRunner().invoke(
            eval_group,
            [],
            obj={"index_path": Path("does-not-exist.db")},
        )

        assert result.exit_code == 2
        assert "--personal is required" in result.output

    def test_missing_index_exits_one(self, tmp_path: Path) -> None:
        result = _invoke(
            tmp_path / "missing.db",
            ["--personal"],
            settings=_settings(tmp_path),
        )

        assert result.exit_code == 1
        assert "No index found. Run 'sif index update' first." in result.output

    @pytest.mark.parametrize("bad_limit", ["0", "-1", str(MAX_TOP_K + 1)])
    def test_limit_outside_the_supported_range_is_a_usage_error(
        self,
        tmp_path: Path,
        bad_limit: str,
    ) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "-n", bad_limit],
            settings=_settings(tmp_path),
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 2
        assert "Invalid value" in result.output
        # The command never ran, so nothing was auto-saved.
        assert not (tmp_path / "eval").exists()


def test_personal_help_lists_options() -> None:
    """The group exposes the declared option surface (docs generator input)."""
    result = CliRunner().invoke(eval_group, ["--help"])
    assert result.exit_code == 0
    for option in (
        "--personal",
        "--compare",
        "--no-save",
        "--bm25-only",
        "--limit",
        "--collection",
        "--all",
        "--json",
    ):
        assert option in result.output


class TestPersonalEvalEdges:
    """Threshold, degradation, and collision rules (D-11, EVAL-01 edges)."""

    def test_fewer_than_min_documents_exits_one_with_count_and_remedy(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "small.db", documents=49)

        result = _invoke(db_path, ["--personal"], settings=_settings(tmp_path))

        assert result.exit_code == 1
        assert "49" in result.output
        assert "sif index update" in result.output
        assert "Traceback" not in result.output

    def test_missing_embed_backend_names_the_install_remedy(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        result = _invoke(
            db_path,
            ["--personal"],
            settings=_settings(tmp_path),
            manager_side_effect=ImportError("No module named 'sentence_transformers'"),
        )

        assert result.exit_code == 1
        assert 'pip install "docsif[embed]"' in result.output
        assert "--bm25-only" in result.output
        assert "Traceback" not in result.output

    def test_embed_model_load_failure_names_the_cause(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        result = _invoke(
            db_path,
            ["--personal"],
            settings=_settings(tmp_path),
            manager_side_effect=RuntimeError("weights download failed"),
        )

        assert result.exit_code == 1
        assert "weights download failed" in result.output
        assert "--bm25-only" in result.output

    def test_empty_title_is_rejected_and_never_emitted(self, tmp_path: Path) -> None:
        # Exactly 50 documents: the initial slice IS the corpus, so the
        # empty-title document is always sampled (no path-dependent flake).
        titles = [""] + [f"Unique title {index}" for index in range(1, 50)]
        db_path = build_personal_db(
            tmp_path / "personal.db",
            documents=50,
            titles=titles,
        )

        _SpyPipeline.seen = []
        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=_settings(tmp_path),
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["queries"]["rejected_empty"] == 1
        assert payload["queries"]["by_leg"]["title"]["accepted"] == 49
        assert payload["queries"]["by_leg"]["body"]["accepted"] == 50
        assert payload["queries"]["accepted"] == 99
        assert "" not in _SpyPipeline.seen
        assert all(query.strip() for query in _SpyPipeline.seen)

    def test_duplicate_normalized_title_keeps_the_first_and_counts_it(self, tmp_path: Path) -> None:
        # Exactly 50 documents: both duplicate-title documents are sampled.
        titles = [
            "  Same  TITLE  ",
            "same title",
            *[f"Unique title {index}" for index in range(2, 50)],
        ]
        db_path = build_personal_db(
            tmp_path / "personal.db",
            documents=50,
            titles=titles,
        )

        _SpyPipeline.seen = []
        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=_settings(tmp_path),
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["queries"]["rejected_duplicate"] == 1
        assert payload["queries"]["by_leg"]["title"]["accepted"] == 49
        assert payload["queries"]["accepted"] == 99
        assert len([q for q in _SpyPipeline.seen if normalize_text(q) == "same title"]) == 1

    def test_insufficient_accepted_queries_exits_one_with_counts(self, tmp_path: Path) -> None:
        # Both legs must fail to reach the floor: 11 empty titles and 60
        # empty bodies leave exactly 49 accepted title queries.
        titles = [f"Unique title {index}" for index in range(49)] + [""] * 11
        db_path = build_personal_db(
            tmp_path / "personal.db",
            documents=60,
            titles=titles,
            bodies=[""] * 60,
        )

        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=_settings(tmp_path),
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 1
        assert "accepted 49" in result.output
        assert "rejected 71" in result.output
        assert "71 empty" in result.output
        assert "sif index update" in result.output
        assert "Traceback" not in result.output


def test_normalize_text_is_nfc_casefolded_and_whitespace_collapsed() -> None:
    import unicodedata

    assert normalize_text("  Same\t TITLE\n\n") == "same title"
    decomposed = unicodedata.normalize("NFD", "Café")
    assert normalize_text(decomposed) == normalize_text("Café")


class TestDisclosureAndMarkup:
    """T-18-15 provider disclosure and T-18-01 markup escaping."""

    def test_remote_model_type_discloses_on_stderr_only(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path, model_type="modelscope")

        result = _invoke(
            db_path,
            ["--personal", "--json"],
            settings=settings,
            manager=_manager(),
        )

        assert result.exit_code == 0, result.output
        # The stderr console notice names the provider and the local alternative.
        assert "Embedding provider 'modelscope' is remote-capable" in result.stderr
        assert "--bm25-only" in result.stderr
        # Stdout is strict JSON; the report itself names the provider too.
        payload = json.loads(result.stdout)
        assert payload["model"]["model_type"] == "modelscope"
        assert any("remote-capable" in note for note in payload["notes"])

    def test_bm25_only_prints_no_remote_disclosure(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path, model_type="modelscope")

        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=settings,
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 0, result.output
        assert "remote-capable" not in result.stderr

    def test_model_name_markup_is_escaped_in_the_table(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path, model_name="[bold]evil[/bold]")

        result = _invoke(
            db_path,
            ["--personal"],
            settings=settings,
            manager=_manager(),
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 0, result.output
        # Escaped markup renders literally; unescaped markup would print "evil".
        assert "[bold]evil[/bold]" in result.output


# --- Task 2: two-leg default, widening, suppression -------------------------


def _long_body(index: int, candidate: str) -> str:
    """Body whose candidate sentence starts beyond the 200-char window."""
    filler = (
        "Introductory context for this note spans several sentences of background "
        "material so the candidate prose sits beyond the opening synthesis window. "
        "Additional context keeps the note realistic and moves the useful sentence "
        "further down the document body. "
    )
    return f"Intro note {index}. {filler}{candidate}."


def _tuning_body(index: int) -> str:
    """A body whose body-leg query text hashes into the tuning split."""
    candidate_index = index * 1000
    while True:
        candidate = (
            f"candidate query {candidate_index} discusses retrieval quality sampling metrics"
        )
        if assign_split(candidate) == "tuning":
            return _long_body(index, candidate)
        candidate_index += 1


def _titles_with_split(count: int, split: str, start: int = 0) -> list[str]:
    """Distinct titles whose title-leg query text hashes into ``split``."""
    titles: list[str] = []
    index = start
    while len(titles) < count:
        candidate = f"Note group {index} about topic {index * 7}"
        if assign_split(candidate) == split:
            titles.append(candidate)
        index += 1
    return titles


def _widening_fixture(db_path: Path) -> tuple[Path, set[str], dict[str, str]]:
    """60 docs whose initial 50-doc slice has only 24 held-out queries.

    Every body query is tuning; the initial slice gets 24 held-out titles,
    and the 10 documents outside the slice get held-out titles. The initial
    slice is computed with the exact absolute paths the DB builder stores, so
    the deterministic sample order is reproduced.
    """
    bodies = [_tuning_body(index) for index in range(60)]
    corpus_dir = db_path.parent / "corpus"
    records = [
        DocumentRecord(
            id=f"doc-{index:03d}",
            path=str(corpus_dir / f"{index:03d}.md"),
            title="",
            checksum=hashlib.sha256(body.encode()).hexdigest(),
            file_size=len(body.encode()),
        )
        for index, body in enumerate(bodies)
    ]
    initial_ids = {doc.id for doc in sample_documents(records, limit=INITIAL_SAMPLE_DOCUMENTS)}
    initial = [doc for doc in records if doc.id in initial_ids]
    outside = [doc for doc in records if doc.id not in initial_ids]
    heldout_titles = _titles_with_split(24, "heldout", start=1000)
    tuning_titles = _titles_with_split(len(initial) - 24, "tuning", start=2000)
    outside_titles = _titles_with_split(len(outside), "heldout", start=3000)
    title_by_id: dict[str, str] = {}
    for doc, title in zip(initial[:24], heldout_titles, strict=False):
        title_by_id[doc.id] = title
    for doc, title in zip(initial[24:], tuning_titles, strict=False):
        title_by_id[doc.id] = title
    for doc, title in zip(outside, outside_titles, strict=False):
        title_by_id[doc.id] = title
    titles = [title_by_id[f"doc-{index:03d}"] for index in range(60)]
    db_path = build_personal_db(
        db_path,
        documents=60,
        titles=titles,
        bodies=bodies,
    )
    return db_path, initial_ids, title_by_id


class TestTwoLegDefault:
    def test_default_run_evaluates_title_and_body_queries(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        _SpyPipeline.seen = []
        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=_settings(tmp_path),
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["queries"]["by_leg"]["title"]["accepted"] > 0
        assert payload["queries"]["by_leg"]["body"]["accepted"] > 0
        # The pipeline sees both legs' query text (not a title-only set).
        assert any(query.startswith("Personal note") for query in _SpyPipeline.seen)
        assert any(query.startswith("document body") for query in _SpyPipeline.seen)

    def test_held_out_widening_reaches_the_floor_and_evaluates_outside_docs(
        self,
        tmp_path: Path,
    ) -> None:
        db_path, initial_ids, title_by_id = _widening_fixture(tmp_path / "personal.db")
        outside_titles = {
            title for doc_id, title in title_by_id.items() if doc_id not in initial_ids
        }

        _SpyPipeline.seen = []
        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=_settings(tmp_path),
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["corpus"]["sampled"] == 60
        assert payload["corpus"]["widened"] is True
        assert payload["splits"]["heldout"] >= HELDOUT_MIN
        assert outside_titles & set(_SpyPipeline.seen)

    def test_impossible_held_out_floor_exits_one_with_counts(self, tmp_path: Path) -> None:
        titles = _titles_with_split(50, "tuning", start=0)
        bodies = [_tuning_body(index) for index in range(50)]
        db_path = build_personal_db(
            tmp_path / "personal.db",
            documents=50,
            titles=titles,
            bodies=bodies,
        )

        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=_settings(tmp_path),
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 1
        assert "held-out" in result.output
        assert "tuning" in result.output
        assert "sif index update" in result.output
        assert "Traceback" not in result.output

    def test_small_group_is_suppressed_and_named_in_json_and_table(
        self,
        tmp_path: Path,
    ) -> None:
        zh_titles = [f"如何配置 {index}" for index in range(9)]
        en_titles = [f"Unique title {index}" for index in range(9, 50)]
        db_path = build_personal_db(
            tmp_path / "personal.db",
            documents=50,
            titles=zh_titles + en_titles,
        )
        settings = _settings(tmp_path)
        suppressed_name = "leg=title/language=zh/length=medium"

        json_result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=settings,
            pipeline=_SpyPipeline,
        )
        assert json_result.exit_code == 0, json_result.output
        payload = json.loads(json_result.stdout)
        assert suppressed_name in payload["suppressed"]
        assert not any(
            group["leg"] == "title" and group["language"] == "zh" for group in payload["groups"]
        )

        table_result = _invoke(
            db_path,
            ["--personal", "--bm25-only"],
            settings=settings,
            pipeline=_SpyPipeline,
        )
        assert table_result.exit_code == 0, table_result.output
        assert "Suppressed groups" in table_result.output
        assert suppressed_name in table_result.output


class _LiteralRecordingPipeline(SearchPipeline):
    """Real pipeline that records the literal query text the eval sends."""

    seen: ClassVar[list[str]] = []

    def search(
        self,
        query: str,
        options: SearchOptions | None = None,
    ) -> list[SearchResult]:
        _LiteralRecordingPipeline.seen.append(query)
        return super().search(query, options)


class TestLiteralPrefixedQueries:
    """CR-01: eval text is searched literally, never as a reserved operator."""

    def test_vec_and_hyde_titles_and_history_run_as_literal_text(
        self,
        tmp_path: Path,
    ) -> None:
        # A title is synthesized verbatim, so it can begin with a reserved
        # operator prefix. Every title carries one of the two prefixes, so the
        # deterministic 50-document sample necessarily includes both kinds;
        # with prefix parsing active they would route to vector/HyDE search
        # and abort the whole run in --bm25-only mode.
        titles = [
            f"vec: embedding notes {index}" if index % 2 == 0 else f"hyde: retrieval notes {index}"
            for index in range(60)
        ]
        bodies = [
            _long_body(
                index,
                (
                    "hyde: retrieval notes discuss local search quality and evaluation"
                    if index == 1
                    else f"document body {index:03d} discusses local search quality retrieval"
                ),
            )
            for index in range(60)
        ]
        db_path = build_personal_db(
            tmp_path / "personal.db",
            documents=60,
            titles=titles,
            bodies=bodies,
        )
        _seed(db_path, ["vec: history query", "hyde: history query", "alpha beta"])

        _LiteralRecordingPipeline.seen = []
        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=_settings(tmp_path),
            pipeline=_LiteralRecordingPipeline,
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["queries"]["accepted"] >= 50
        # The reserved-prefix title and replay text reached the searcher as
        # literal query text (and the run completed instead of aborting).
        assert any(
            query.startswith("vec: embedding notes") for query in _LiteralRecordingPipeline.seen
        )
        assert any(
            query.startswith("hyde: retrieval notes") for query in _LiteralRecordingPipeline.seen
        )
        assert {"vec: history query", "hyde: history query"} <= set(_LiteralRecordingPipeline.seen)


# --- Task 3: query_log replay leg ------------------------------------------


class _ReplaySpyPipeline:
    """Pipeline stand-in returning fixed paths and recording every query."""

    seen: ClassVar[list[str]] = []

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def search(self, query: str, _options: object) -> list:
        _ReplaySpyPipeline.seen.append(query)
        return [
            SearchResult(
                document_id=f"rid-{index}",
                title="title",
                path=f"/p/{index}.md",
                collection_name="collection",
                score=1.0,
            )
            for index in range(3)
        ]


def _seed(db_path: Path, queries: list[str]) -> None:
    """Seed query_log into an existing on-disk index."""
    import sqlite3

    from tests.support.eval import seed_query_log

    conn = sqlite3.connect(str(db_path))
    try:
        seed_query_log(conn, queries)
        conn.commit()
    finally:
        conn.close()


class TestReplayCli:
    def test_empty_history_is_unavailable_and_never_fails_the_run(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path)

        json_result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=settings,
            pipeline=_SpyPipeline,
        )

        assert json_result.exit_code == 0, json_result.output
        payload = json.loads(json_result.stdout)
        assert payload["replay"]["available"] is False
        assert payload["replay"]["num_queries"] == 0
        assert payload["replay"]["baseline_available"] is False
        assert payload["replay"]["queries"] == {}
        assert "stability" in payload["replay"]["bias"]
        assert "CLI" in payload["replay"]["bias"]

        table_result = _invoke(
            db_path,
            ["--personal", "--bm25-only"],
            settings=settings,
            pipeline=_SpyPipeline,
        )

        assert table_result.exit_code == 0, table_result.output
        assert "Replay (stability, not quality)" in table_result.output
        assert "queries 0" in table_result.output
        assert "CLI-biased" in table_result.output

    def test_query_log_replays_normalized_sorted_unique_queries(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        _seed(db_path, ["Zeta", "alpha", "  ALPHA  ", "beta"])

        _ReplaySpyPipeline.seen = []
        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=_settings(tmp_path),
            pipeline=_ReplaySpyPipeline,
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["replay"]["available"] is True
        assert payload["replay"]["num_queries"] == 3
        assert list(payload["replay"]["queries"]) == ["alpha", "beta", "zeta"]
        assert payload["replay"]["queries"]["alpha"] == ["/p/0.md", "/p/1.md", "/p/2.md"]
        # One search per unique replay query ran through the hoisted pipeline.
        assert [
            query for query in _ReplaySpyPipeline.seen if query in {"alpha", "beta", "zeta"}
        ] == [
            "alpha",
            "beta",
            "zeta",
        ]

    def test_replay_never_changes_known_item_metrics_splits_or_groups(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path)

        fresh = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=settings,
            pipeline=_ReplaySpyPipeline,
        )
        _seed(db_path, ["alpha", "beta"])
        replayed = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=settings,
            pipeline=_ReplaySpyPipeline,
        )

        assert fresh.exit_code == 0, fresh.output
        assert replayed.exit_code == 0, replayed.output
        without = json.loads(fresh.stdout)
        with_replay = json.loads(replayed.stdout)
        for key in (
            "metrics",
            "splits",
            "groups",
            "suppressed",
            "queries",
            "corpus",
            "top_k",
            "model",
            "retrieval",
        ):
            assert without[key] == with_replay[key]
        assert without["replay"]["available"] is False
        assert with_replay["replay"]["available"] is True


# --- Task 1: auto-saved runs ------------------------------------------------


def _saved_files(root: Path) -> list[Path]:
    """Every auto-saved run under ``<cache_dir>/eval`` (sorted, stable)."""
    return sorted((root / "eval").glob("eval-*.json"))


class TestSavedRunsCli:
    def test_personal_run_writes_exactly_one_versioned_run(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        _ReplaySpyPipeline.seen = []
        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=_settings(tmp_path),
            pipeline=_ReplaySpyPipeline,
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        files = _saved_files(tmp_path)
        assert len(files) == 1
        assert payload["run_path"] == str(files[0])

        saved = load_saved_run(files[0])
        assert saved.version == SAVED_RUN_VERSION == 1
        assert saved.top_k == 10
        assert saved.corpus["fingerprint"] == payload["corpus"]["fingerprint"]
        assert len(saved.queries) == payload["queries"]["accepted"]
        assert [record.query for record in saved.queries] == _ReplaySpyPipeline.seen
        for record in saved.queries:
            assert len(record.retrieved) == len(record.retrieved_doc_ids)
        text = files[0].read_text(encoding="utf-8")
        assert '"content"' not in text
        assert "Document body" not in text
        assert "snippet" not in text

    def test_no_save_writes_no_run_and_reports_none(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json", "--no-save"],
            settings=_settings(tmp_path),
            pipeline=_ReplaySpyPipeline,
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["run_path"] is None
        assert _saved_files(tmp_path) == []

    def test_saved_path_is_announced_on_stderr_only(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        result = _invoke(
            db_path,
            ["--personal", "--bm25-only"],
            settings=_settings(tmp_path),
            pipeline=_ReplaySpyPipeline,
        )

        assert result.exit_code == 0, result.output
        files = _saved_files(tmp_path)
        assert len(files) == 1
        assert str(files[0]) in result.stderr
        assert str(files[0]) not in result.stdout

    def test_saved_run_is_built_from_the_report_contract(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=_settings(tmp_path),
            pipeline=_ReplaySpyPipeline,
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        saved = load_saved_run(_saved_files(tmp_path)[0])
        assert saved.corpus["documents"] == payload["corpus"]["documents"]
        assert saved.corpus["sampled"] == payload["corpus"]["sampled"]
        assert saved.retrieval == payload["retrieval"]
        assert saved.model == payload["model"]
        assert {record.split for record in saved.queries} == {"tuning", "heldout"}

    def test_non_default_depth_round_trips_through_the_loader(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "-n", "3", "--json"],
            settings=_settings(tmp_path),
            pipeline=_ReplaySpyPipeline,
        )

        assert result.exit_code == 0, result.output
        saved = load_saved_run(_saved_files(tmp_path)[0])
        assert saved.top_k == 3
        assert all(len(record.retrieved) <= 3 for record in saved.queries)
        assert all(len(record.retrieved_doc_ids) <= 3 for record in saved.queries)

    def test_unserializable_query_fails_before_any_file_is_written(
        self,
        tmp_path: Path,
    ) -> None:
        # The saved-run loader caps query text at 10,000 characters; the
        # writer must validate first instead of emitting a file it rejects.
        # Every title is long so the deterministic 50-document sample cannot
        # exclude the offending query by chance (tmp paths vary per session).
        titles = [f"{'x' * 10_001} {index}" for index in range(60)]
        db_path = build_personal_db(
            tmp_path / "personal.db",
            documents=60,
            titles=titles,
        )

        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=_settings(tmp_path),
            pipeline=_ReplaySpyPipeline,
        )

        assert result.exit_code == 1
        assert "Could not save the personal eval run" in result.output
        assert "queries" in result.output
        assert "Traceback" not in result.output
        assert _saved_files(tmp_path) == []


# --- Task 2: --compare pairing, refusal, and the noise gate -----------------


class _OptionsSpyPipeline:
    """Pipeline stand-in recording every query and its search depth."""

    seen: ClassVar[list[str]] = []
    limits: ClassVar[list[int]] = []

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def search(self, query: str, options: object) -> list:
        _OptionsSpyPipeline.seen.append(query)
        _OptionsSpyPipeline.limits.append(int(options.limit))  # type: ignore[attr-defined]
        return [
            SearchResult(
                document_id=f"rid-{index}",
                title="title",
                path=f"/p/{index}.md",
                collection_name="collection",
                score=1.0,
            )
            for index in range(3)
        ]


def _fresh_saved_run(
    db_path: Path,
    settings: Settings,
    *,
    pipeline: object | None = None,
    manager: object = _UNSET,
    extra_args: tuple[str, ...] = ("--bm25-only",),
) -> tuple[Path, dict]:
    """Run a fresh personal eval and return its auto-saved run path + payload."""
    result = _invoke(
        db_path,
        ["--personal", *extra_args, "--json"],
        settings=settings,
        pipeline=pipeline,
        manager=manager,
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["run_path"] is not None
    return Path(payload["run_path"]), payload


class TestCompareCli:
    def test_compare_evaluates_exactly_the_saved_queries_in_saved_order(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path)
        _ReplaySpyPipeline.seen = []
        saved_path, _payload = _fresh_saved_run(
            db_path,
            settings,
            pipeline=_ReplaySpyPipeline,
        )
        saved_queries = [record.query for record in load_saved_run(saved_path).queries]

        _SpyPipeline.seen = []
        result = _invoke(
            db_path,
            ["--personal", "--compare", str(saved_path), "--bm25-only", "--json"],
            settings=settings,
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 0, result.output
        # No synthesized title/body text that is not in the saved file.
        assert _SpyPipeline.seen == saved_queries
        payload = json.loads(result.stdout)
        assert payload["comparison"]["baseline"]["num_queries"] == len(saved_queries)
        assert payload["comparison"]["current"]["num_queries"] == len(saved_queries)
        assert payload["comparison"]["top_k"] == 10

    def test_compare_fingerprint_mismatch_exits_one_with_both_values(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path)
        saved_path, payload = _fresh_saved_run(
            db_path,
            settings,
            pipeline=_ReplaySpyPipeline,
        )
        current_fingerprint = payload["corpus"]["fingerprint"]
        rewrite_saved_run(
            saved_path,
            lambda data: data["corpus"].__setitem__(
                "fingerprint",
                "deadbeefdeadbeef",
            ),
        )

        result = _invoke(
            db_path,
            ["--personal", "--compare", str(saved_path), "--bm25-only", "--json"],
            settings=settings,
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 1
        assert "deadbeefdeadbeef" in result.output
        assert current_fingerprint in result.output
        assert "refusing" in result.output
        assert "Traceback" not in result.output

    def test_compare_missing_target_exits_one_naming_the_path(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path)
        saved_path, _payload = _fresh_saved_run(
            db_path,
            settings,
            pipeline=_ReplaySpyPipeline,
        )

        def _stale_target(data: dict) -> None:
            data["queries"][0]["target_doc_id"] = "missing-doc"
            data["queries"][0]["target_path"] = "/no/such/path.md"

        rewrite_saved_run(saved_path, _stale_target)

        result = _invoke(
            db_path,
            ["--personal", "--compare", str(saved_path), "--bm25-only", "--json"],
            settings=settings,
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 1
        assert "/no/such/path.md" in result.output
        assert "Traceback" not in result.output

    def test_compare_autosaves_one_new_run_and_no_save_writes_none(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path)
        saved_path, _payload = _fresh_saved_run(
            db_path,
            settings,
            pipeline=_ReplaySpyPipeline,
        )
        saved = load_saved_run(saved_path)

        result = _invoke(
            db_path,
            ["--personal", "--compare", str(saved_path), "--bm25-only", "--json"],
            settings=settings,
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 0, result.output
        files = _saved_files(tmp_path)
        assert len(files) == 2
        new_path = next(path for path in files if path != saved_path)
        assert json.loads(result.stdout)["run_path"] == str(new_path)
        new_run = load_saved_run(new_path)
        assert [record.query for record in new_run.queries] == [
            record.query for record in saved.queries
        ]
        assert [record.split for record in new_run.queries] == [
            record.split for record in saved.queries
        ]
        assert new_run.top_k == saved.top_k
        # The current arm supplied the retrieval arrays (empty for this spy).
        assert all(record.retrieved == [] for record in new_run.queries)

        skipped = _invoke(
            db_path,
            [
                "--personal",
                "--compare",
                str(saved_path),
                "--bm25-only",
                "--json",
                "--no-save",
            ],
            settings=settings,
            pipeline=_SpyPipeline,
        )

        assert skipped.exit_code == 0, skipped.output
        assert json.loads(skipped.stdout)["run_path"] is None
        assert len(_saved_files(tmp_path)) == 2

    def test_compare_uses_saved_depth_and_warns_when_limit_differs(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path)
        _ReplaySpyPipeline.seen = []
        saved_path, _payload = _fresh_saved_run(
            db_path,
            settings,
            pipeline=_ReplaySpyPipeline,
            extra_args=("--bm25-only", "-n", "5"),
        )
        assert load_saved_run(saved_path).top_k == 5

        _OptionsSpyPipeline.seen = []
        _OptionsSpyPipeline.limits = []
        result = _invoke(
            db_path,
            [
                "--personal",
                "--compare",
                str(saved_path),
                "--bm25-only",
                "-n",
                "20",
                "--json",
            ],
            settings=settings,
            pipeline=_OptionsSpyPipeline,
        )

        assert result.exit_code == 0, result.output
        assert _OptionsSpyPipeline.limits == [5] * len(_OptionsSpyPipeline.seen)
        assert "top_k=5" in result.stderr
        assert "ignoring" in result.stderr

    def test_compare_retrieval_mode_difference_warns_and_still_reports(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path)
        _ReplaySpyPipeline.seen = []
        saved_path, _payload = _fresh_saved_run(
            db_path,
            settings,
            pipeline=_ReplaySpyPipeline,
            manager=_manager(),
            extra_args=(),
        )
        assert load_saved_run(saved_path).retrieval == "hybrid"

        result = _invoke(
            db_path,
            ["--personal", "--compare", str(saved_path), "--bm25-only", "--json"],
            settings=settings,
            pipeline=_OptionsSpyPipeline,
        )

        assert result.exit_code == 0, result.output
        assert "hybrid" in result.stderr
        assert "bm25" in result.stderr
        payload = json.loads(result.stdout)
        assert payload["comparison"]["retrieval"] == {
            "saved": "hybrid",
            "current": "bm25",
        }

    def test_compare_reports_group_gates_and_suppressed_names(
        self,
        tmp_path: Path,
    ) -> None:
        zh_titles = [f"如何配置 {index}" for index in range(9)]
        en_titles = [f"Unique title {index}" for index in range(9, 50)]
        db_path = build_personal_db(
            tmp_path / "personal.db",
            documents=50,
            titles=zh_titles + en_titles,
        )
        settings = _settings(tmp_path)
        _ReplaySpyPipeline.seen = []
        saved_path, _payload = _fresh_saved_run(
            db_path,
            settings,
            pipeline=_ReplaySpyPipeline,
        )
        suppressed_name = "leg=title/language=zh/length=medium"

        result = _invoke(
            db_path,
            ["--personal", "--compare", str(saved_path), "--bm25-only", "--json"],
            settings=settings,
            pipeline=_OptionsSpyPipeline,
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        comparison = payload["comparison"]
        assert suppressed_name in comparison["suppressed"]
        assert suppressed_name in result.stderr
        groups = {
            (group["leg"], group["language"], group["length_bucket"]): group
            for group in comparison["groups"]
        }
        assert ("title", "en", "medium") in groups
        assert ("body", "en", "long") in groups
        assert not any(
            group["leg"] == "title" and group["language"] == "zh" for group in comparison["groups"]
        )
        for key in (
            "n",
            "mean_delta",
            "ci_low",
            "ci_high",
            "helped",
            "hurt",
            "unchanged",
            "winner",
        ):
            assert key in groups[("title", "en", "medium")]
        assert set(comparison["splits"]) == {"tuning", "heldout"}
        assert comparison["splits"]["tuning"]["diagnostic"] is True
        assert comparison["splits"]["heldout"]["diagnostic"] is False
        assert "noise_floor" in comparison["delta"]
        assert "warrants_default_change" in comparison["gate"]

    def test_compare_over_an_empty_query_list_exits_one(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path)
        saved_path, _payload = _fresh_saved_run(
            db_path,
            settings,
            pipeline=_ReplaySpyPipeline,
        )
        rewrite_saved_run(saved_path, lambda data: data.__setitem__("queries", []))

        result = _invoke(
            db_path,
            ["--personal", "--compare", str(saved_path), "--bm25-only", "--json"],
            settings=settings,
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 1
        assert "queries" in result.output
        assert "Traceback" not in result.output

    def test_compare_warns_on_model_identity_mismatch(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path)
        _ReplaySpyPipeline.seen = []
        saved_path, _payload = _fresh_saved_run(
            db_path,
            settings,
            pipeline=_ReplaySpyPipeline,
            manager=_manager(),
            extra_args=(),
        )
        rewrite_saved_run(
            saved_path,
            lambda data: data.__setitem__(
                "model",
                {
                    "model_name": "different-model",
                    "model_type": "sentence_transformers",
                    "dimension": EMBEDDING_DIM,
                },
            ),
        )

        result = _invoke(
            db_path,
            ["--personal", "--compare", str(saved_path), "--json"],
            settings=settings,
            manager=_manager(),
            pipeline=_OptionsSpyPipeline,
        )

        assert result.exit_code == 0, result.output
        assert "different-model" in result.stderr
        assert "model" in result.stderr.lower()


# --- Task 3: comparison rendering -------------------------------------------


class TestCompareRendering:
    def _fixture(self, tmp_path: Path) -> tuple[Path, Settings, Path]:
        """50-document corpus with a 9-query suppressed group and a saved run."""
        zh_titles = [f"如何配置 {index}" for index in range(9)]
        en_titles = [f"Unique title {index}" for index in range(9, 50)]
        db_path = build_personal_db(
            tmp_path / "personal.db",
            documents=50,
            titles=zh_titles + en_titles,
        )
        settings = _settings(tmp_path)
        _ReplaySpyPipeline.seen = []
        saved_path, _payload = _fresh_saved_run(
            db_path,
            settings,
            pipeline=_ReplaySpyPipeline,
        )
        return db_path, settings, saved_path

    def test_compare_table_renders_summary_context_and_group_rows(
        self,
        tmp_path: Path,
    ) -> None:
        db_path, settings, saved_path = self._fixture(tmp_path)

        result = _invoke(
            db_path,
            ["--personal", "--compare", str(saved_path), "--bm25-only"],
            settings=settings,
            pipeline=_OptionsSpyPipeline,
        )

        assert result.exit_code == 0, result.output
        for expected in (
            "Personal Search Comparison",
            "Overall",
            "Tuning",
            "Held-out",
            "diagnostic",
            "Noise floor",
            "Corpus fingerprint match",
            "Replay stability",
            "Groups",
            "Suppressed groups",
            "Winner",
            "Baseline",
            "Current",
            "Mean",
            "delta",
        ):
            assert expected in result.stdout, expected
        suppressed_name = "leg=title/language=zh/length=medium"
        assert suppressed_name in result.stderr
        assert suppressed_name not in result.stdout

    def test_compare_table_reports_replay_unavailable_on_stderr(
        self,
        tmp_path: Path,
    ) -> None:
        db_path, settings, saved_path = self._fixture(tmp_path)

        result = _invoke(
            db_path,
            ["--personal", "--compare", str(saved_path), "--bm25-only"],
            settings=settings,
            pipeline=_OptionsSpyPipeline,
        )

        assert result.exit_code == 0, result.output
        assert "Replay stability unavailable" in result.stderr
        assert "unavailable" in result.stdout

    def test_compare_json_carries_the_full_comparison_object(
        self,
        tmp_path: Path,
    ) -> None:
        db_path, settings, saved_path = self._fixture(tmp_path)

        result = _invoke(
            db_path,
            ["--personal", "--compare", str(saved_path), "--bm25-only", "--json"],
            settings=settings,
            pipeline=_OptionsSpyPipeline,
        )

        assert result.exit_code == 0, result.output
        comparison = json.loads(result.stdout)["comparison"]
        assert set(comparison) >= {
            "baseline",
            "current",
            "delta",
            "ci",
            "gate",
            "splits",
            "groups",
            "suppressed",
            "replay",
            "retrieval",
            "top_k",
        }
        assert set(comparison["baseline"]) == {
            "ndcg_at_10",
            "hit_at_10",
            "num_queries",
        }
        assert set(comparison["delta"]) >= {
            "mean",
            "helped",
            "hurt",
            "unchanged",
            "n",
            "noise_floor",
        }
        assert set(comparison["ci"]) == {"low", "high"}
        assert comparison["gate"]["warrants_default_change"] is False
        assert isinstance(comparison["replay"]["available"], bool)
        assert isinstance(comparison["top_k"], int)
