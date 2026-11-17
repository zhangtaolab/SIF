"""Unit battery for the Phase 24 title-breadcrumb runbook (QUAL-03).

Pure-function tests for the single-arm dry-run plan: the modelscope Qwen3/512
breadcrumb contract, the per-arm env isolation, the ordered
index/embed/identity/eval stage plan, the expected cache identity, the
corpus-root guard, and the no-subprocess dry run. Nothing here loads a model
or runs the ``sif`` CLI: real breadcrumb evidence is a recorded manual run,
never a CI test.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from sif.search import personal_bench


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_module(name: str) -> Any:
    """Load one scripts module by file location, registering it in sys.modules."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


harrier_eval = _load_module("harrier_eval")
chunk_sweep = _load_module("chunk_sweep")
breadcrumb_eval = _load_module("breadcrumb_eval")


def _payload(tmp_path: Path, roots: list[Path] | None = None) -> dict[str, Any]:
    """A dry-run payload for throwaway corpus roots and scratch root."""
    corpus_roots = roots if roots is not None else [tmp_path / "corpus-a"]
    return breadcrumb_eval.build_dry_run_payload(tmp_path, corpus_roots)


class TestDryRunArm:
    """The dry run proves the single breadcrumb arm's fixed contract."""

    def test_exactly_one_arm_with_the_breadcrumb_contract(self, tmp_path: Path) -> None:
        arm = _payload(tmp_path)["arm"]

        assert arm["name"] == "breadcrumb-512-128"
        assert arm["embed_breadcrumb"] is True
        assert arm["chunk_size"] == 512
        assert arm["chunk_overlap"] == 128
        assert arm["max_tokens"] == 512
        assert arm["embedding_dim"] == 1024
        assert arm["model_type"] == "modelscope"
        assert arm["model_name"] == "Qwen/Qwen3-Embedding-0.6B"

    def test_env_pins_modelscope_qwen3_and_the_breadcrumb(self, tmp_path: Path) -> None:
        env = _payload(tmp_path)["env"]

        assert env["SIF_MODEL_TYPE"] == "modelscope"
        assert env["SIF_MODEL_NAME"] == "Qwen/Qwen3-Embedding-0.6B"
        assert env["SIF_MAX_TOKENS"] == "512"
        assert env["SIF_EMBEDDING_DIM"] == "1024"
        assert env["SIF_EMBED_BREADCRUMB"] == "1"
        assert env["SIF_CACHE_EMBEDDINGS"] == "1"
        assert env["SIF_CHUNK_SIZE"] == "512"
        assert env["SIF_CHUNK_OVERLAP"] == "128"

    def test_removed_overrides_never_leak_into_the_arm(self, tmp_path: Path) -> None:
        arm_spec = breadcrumb_eval.build_arm_spec(tmp_path)
        base = {
            "SIF_API_KEY": "secret",
            "SIF_API_BASE": "https://example.invalid",
            "SIF_MODEL_PATH": "/tmp/model",
            "SIF_DB_PATH": "/tmp/other.db",
            "SIF_EMBED_BREADCRUMB": "0",
            "SIF_QUERY_PROMPT_NAME": "query",
            "SIF_DOCUMENT_PROMPT_NAME": "document",
        }

        env = breadcrumb_eval.build_arm_env(base, arm_spec)

        for key in ("SIF_MODEL_PATH", "SIF_DB_PATH", "SIF_API_BASE", "SIF_API_KEY"):
            assert key not in env
        assert env["SIF_EMBED_BREADCRUMB"] == "1"

    def test_baseline_twin_uses_the_same_env_with_the_breadcrumb_off(self, tmp_path: Path) -> None:
        arm_spec = breadcrumb_eval.build_arm_spec(tmp_path, baseline=True)

        env = breadcrumb_eval.build_arm_env({}, arm_spec)

        assert arm_spec.embed_breadcrumb is False
        assert env["SIF_EMBED_BREADCRUMB"] == "0"
        assert env["SIF_MODEL_TYPE"] == "modelscope"
        assert env["SIF_MAX_TOKENS"] == "512"

    def test_expected_identity_and_selection_rule(self, tmp_path: Path) -> None:
        payload = _payload(tmp_path)

        assert payload["expected_identity"] == {
            "cache_model_id": "modelscope:Qwen/Qwen3-Embedding-0.6B",
            "dimension": 1024,
            "query_prompt": None,
            "document_prompt": None,
        }
        assert payload["selection_rule"] == "overall-heldout-plus-body-leg-veto"
        assert payload["min_heldout_for_epsilon_win"] == 101


class TestDryRunStages:
    """The stage plan is ordered and carries no shell strings."""

    def test_stage_order_is_index_embed_identity_eval(self, tmp_path: Path) -> None:
        stages = _payload(tmp_path)["stages"]

        assert [stage["stage"] for stage in stages] == [
            "arm:index",
            "arm:embed",
            "arm:identity",
            "arm:eval",
        ]

    def test_index_stage_adds_one_collection_per_root_then_updates(self, tmp_path: Path) -> None:
        roots = [tmp_path / "corpus-a", tmp_path / "corpus-b"]
        stages = _payload(tmp_path, roots)["stages"]
        commands = stages[0]["commands"]

        assert len(commands) == 3
        assert commands[0][-4:] == ["add", str(roots[0]), "--name", "phase24b-1"]
        assert commands[1][-4:] == ["add", str(roots[1]), "--name", "phase24b-2"]
        assert commands[2][-2:] == ["index", "update"]
        assert all(argv[:3] == [sys.executable, "-m", "sif.cli.main"] for argv in commands)

    def test_embed_stage_forces_a_rechunk_and_reembed(self, tmp_path: Path) -> None:
        stages = _payload(tmp_path)["stages"]
        command = stages[1]["commands"][0]

        assert command[-5:] == [
            "index",
            "embed",
            "--force",
            "--chunk-strategy",
            "auto",
        ]

    def test_identity_stage_runs_this_script_against_the_arm_db(self, tmp_path: Path) -> None:
        arm_spec = breadcrumb_eval.build_arm_spec(tmp_path)
        stages = _payload(tmp_path)["stages"]
        command = stages[2]["commands"][0]

        assert command[0] == sys.executable
        assert command[1].endswith("breadcrumb_eval.py")
        assert command[2] == "--probe-identity"
        assert command[3] == "--index"
        assert command[4] == str(arm_spec.db_path)

    def test_eval_stage_compares_against_the_supplied_saved_run(self, tmp_path: Path) -> None:
        saved_run = tmp_path / "qwen3-baseline.json"
        payload = breadcrumb_eval.build_dry_run_payload(tmp_path, [tmp_path / "corpus"], saved_run)
        command = payload["stages"][3]["commands"][0]

        assert "--compare" in command
        assert command[command.index("--compare") + 1] == str(saved_run)
        assert command[-1] == "--json"

    def test_baseline_stages_carry_the_breadcrumb_off_and_no_compare(self, tmp_path: Path) -> None:
        baseline = _payload(tmp_path)["baseline"]

        assert [stage["stage"] for stage in baseline["stages"]] == [
            "baseline:index",
            "baseline:embed",
            "baseline:identity",
            "baseline:eval",
        ]
        assert all(stage["env"]["SIF_EMBED_BREADCRUMB"] == "0" for stage in baseline["stages"])
        eval_command = baseline["stages"][3]["commands"][0]
        assert "--compare" not in eval_command


class TestCLI:
    """The CLI resolves roots before planning and writes nothing on a dry run."""

    def test_dry_run_invokes_no_subprocess_and_writes_no_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def _fail(*_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("dry run must not invoke a subprocess")

        monkeypatch.setattr(subprocess, "run", _fail)
        code = breadcrumb_eval.main(
            [
                "--dry-run",
                "--json",
                "--corpus",
                str(tmp_path / "corpus-a"),
                "--scratch-root",
                str(tmp_path / "scratch"),
            ]
        )

        assert code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["arm"]["embed_breadcrumb"] is True
        assert not (tmp_path / "scratch").exists()

    def test_parent_child_corpus_roots_are_refused(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = breadcrumb_eval.main(
            [
                "--dry-run",
                "--corpus",
                str(tmp_path / "corpus"),
                "--corpus",
                str(tmp_path / "corpus" / "nested"),
            ]
        )

        assert code == 2
        assert "REFUSED" in capsys.readouterr().err

    def test_scratch_root_equal_to_home_is_refused(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = breadcrumb_eval.main(
            ["--dry-run", "--corpus", str(tmp_path / "corpus"), "--scratch-root", str(Path.home())]
        )

        assert code == 2
        assert "REFUSED" in capsys.readouterr().err

    def test_no_corpus_defaults_to_the_example_corpus(self, tmp_path: Path) -> None:
        payload = breadcrumb_eval.build_dry_run_payload(
            tmp_path, [harrier_eval.EXAMPLE_CORPUS_ROOT]
        )

        first_add = payload["stages"][0]["commands"][0]
        assert str(harrier_eval.EXAMPLE_CORPUS_ROOT) in first_add


IDENTITY = {
    "cache_model_id": "modelscope:Qwen/Qwen3-Embedding-0.6B",
    "dimension": 1024,
    "source": "verified",
    "query_prompt": None,
    "document_prompt": None,
    "check_identity_status": "ok",
}


def _decision(**overrides: Any) -> Any:
    """A breadcrumb decision from mapping gates, defaulting to a body-leg win."""
    from sif.search.tuning_verdict import decide_breadcrumb_default

    confirmation = overrides.get(
        "confirmation", {"n": 101, "mean_delta": 0.02, "winner": True, "sufficient": True}
    )
    legs = overrides.get(
        "legs",
        {
            "body": {"n": 101, "mean_delta": 0.02, "winner": True, "sufficient": True},
            "title": {"n": 101, "mean_delta": 0.03, "winner": True, "sufficient": True},
        },
    )
    duplicates = overrides.get(
        "duplicates",
        {"chunks": 100, "documents": 10, "title_share": 1.0, "in_content_share": 0.545},
    )
    return decide_breadcrumb_default(confirmation, legs, duplicates)


class TestRunState:
    """A scope-key change discards every prior stage marker."""

    def test_changed_scope_key_starts_a_fresh_state(self, tmp_path: Path) -> None:
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        state_path = scratch / "run-state.json"
        state_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "scope_key": "deadbeefdeadbeef",
                    "scope": {"corpus_label": "old"},
                    "stages": {"arm:index": {"status": "complete"}},
                }
            ),
            encoding="utf-8",
        )

        state, path = breadcrumb_eval.prepare_run_state([tmp_path / "corpus"], scratch, "new-label")

        assert path == state_path
        assert state["stages"] == {}
        assert state["scope_key"] != "deadbeefdeadbeef"
        assert state["scope"]["corpus_label"] == "new-label"

    def test_same_scope_key_resumes_prior_markers(self, tmp_path: Path) -> None:
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        scope = breadcrumb_eval.scope_state([tmp_path / "corpus"], scratch, "label")
        key = breadcrumb_eval.scope_key(scope)
        (scratch / "run-state.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "scope_key": key,
                    "scope": scope,
                    "stages": {"arm:index": {"status": "complete", "detail": {}}},
                }
            ),
            encoding="utf-8",
        )

        state, _path = breadcrumb_eval.prepare_run_state([tmp_path / "corpus"], scratch, "label")

        assert "arm:index" in state["stages"]

    def test_unknown_stage_label_is_refused(self) -> None:
        with pytest.raises(ValueError, match="unknown stage"):
            breadcrumb_eval.mark_stage({}, "arm:unknown")


class TestBaselineRule:
    """A backend- or corpus-mismatched saved run is never compared."""

    def _use_saved_run(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        fingerprint: str = "live123",
        model: dict[str, Any] | None = None,
    ) -> None:
        saved = SimpleNamespace(
            corpus={"fingerprint": fingerprint},
            model=model
            if model is not None
            else {"model_type": "modelscope", "model_name": "Qwen/Qwen3-Embedding-0.6B"},
        )
        monkeypatch.setattr(personal_bench, "load_saved_run", lambda _path: saved)

    def test_matching_saved_run_is_used(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._use_saved_run(monkeypatch)
        saved = Path("saved.json")

        assert breadcrumb_eval.choose_baseline(saved, "live123") == ("saved-run", saved)

    @pytest.mark.parametrize(
        ("model", "reason"),
        [
            (
                {
                    "model_type": "sentence_transformers",
                    "model_name": "Qwen/Qwen3-Embedding-0.6B",
                },
                "model-type-mismatch",
            ),
            ({"model_type": "modelscope", "model_name": "BAAI/bge-m3"}, "model-name-mismatch"),
        ],
    )
    def test_backend_or_model_mismatch_regenerates_the_baseline(
        self,
        monkeypatch: pytest.MonkeyPatch,
        model: dict[str, Any],
        reason: str,
    ) -> None:
        self._use_saved_run(monkeypatch, model=model)

        source, path = breadcrumb_eval.choose_baseline(Path("saved.json"), "live123")

        assert path is None
        assert source == f"fresh-baseline ({reason})"

    def test_fingerprint_mismatch_regenerates_the_baseline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._use_saved_run(monkeypatch, fingerprint="other")

        source, path = breadcrumb_eval.choose_baseline(Path("saved.json"), "live123")

        assert path is None
        assert source == "fresh-baseline (corpus-fingerprint-mismatch)"

    def test_invalid_saved_run_regenerates_the_baseline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(_path: Path) -> None:
            raise ValueError("not a saved run")

        monkeypatch.setattr(personal_bench, "load_saved_run", _raise)

        source, path = breadcrumb_eval.choose_baseline(Path("saved.json"), "live123")

        assert path is None
        assert source == "fresh-baseline (invalid-saved-run)"

    def test_missing_saved_run_regenerates_the_baseline(self) -> None:
        source, path = breadcrumb_eval.choose_baseline(None, "live123")

        assert path is None
        assert source == "fresh-baseline (no-saved-run)"


class TestIdentityGate:
    """The arm's persisted identity must be the pinned Qwen3 vector space."""

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("cache_model_id", "sentence_transformers:Qwen/Qwen3-Embedding-0.6B"),
            ("query_prompt", "web_search_query"),
            ("document_prompt", "document"),
        ],
    )
    def test_identity_mismatch_names_the_failing_field(self, field: str, value: object) -> None:
        payload = {**IDENTITY, field: value}

        with pytest.raises(ValueError, match=field):
            breadcrumb_eval.require_probe_identity(payload)

    def test_matching_identity_passes(self) -> None:
        breadcrumb_eval.require_probe_identity(IDENTITY)

    def test_identity_failures_include_dimension_and_source(self) -> None:
        stored = SimpleNamespace(
            cache_model_id="modelscope:Qwen/Qwen3-Embedding-0.6B",
            dimension=768,
            source="configured",
            query_prompt=None,
            document_prompt=None,
        )

        failures = chunk_sweep.identity_failures(stored)

        assert any("dimension" in failure for failure in failures)
        assert any("source" in failure for failure in failures)


class TestDuplicateAggregation:
    """Duplicate shares aggregate per chunk, never per document average."""

    def test_two_document_chunk_set_matches_weighted_shares(self, tmp_path: Path) -> None:
        db_path = tmp_path / "arm.db"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("CREATE TABLE documents (id TEXT PRIMARY KEY, title TEXT)")
            conn.execute(
                "CREATE TABLE document_chunks ("
                "id TEXT PRIMARY KEY, document_id TEXT, sequence INTEGER, content TEXT)"
            )
            conn.executemany(
                "INSERT INTO documents (id, title) VALUES (?, ?)",
                [("a", "Doc"), ("b", "Other")],
            )
            conn.executemany(
                "INSERT INTO document_chunks (id, document_id, sequence, content) "
                "VALUES (?, ?, ?, ?)",
                [
                    ("a0", "a", 0, "# Doc\n\nbody"),
                    ("a1", "a", 1, "sub"),
                    ("b0", "b", 0, "## Head\n\nbody"),
                ],
            )
            conn.commit()
        finally:
            conn.close()

        summary = breadcrumb_eval.collect_duplicate_summary(db_path)

        assert summary == {
            "chunks": 3,
            "documents": 2,
            "title_share": 1.0,
            "in_content_share": 0.666667,
            "subchunk_share": 0.333333,
            "title_equals_heading_share": 0.666667,
        }

    def test_weighting_uses_chunk_counts_not_document_counts(self) -> None:
        entries = [
            {
                "chunks": 2,
                "documents": 1,
                "title_share": 1.0,
                "in_content_share": 0.5,
                "subchunk_share": 0.5,
                "title_equals_heading_share": 0.5,
            },
            {
                "chunks": 1,
                "documents": 1,
                "title_share": 1.0,
                "in_content_share": 1.0,
                "subchunk_share": 0.0,
                "title_equals_heading_share": 0.0,
            },
        ]

        aggregated = breadcrumb_eval.aggregate_duplicate_metrics(entries)

        assert aggregated["chunks"] == 3
        assert aggregated["documents"] == 2
        assert aggregated["in_content_share"] == 0.666667
        assert aggregated["subchunk_share"] == 0.333333
        assert aggregated["title_equals_heading_share"] == 0.333333

    def test_empty_input_returns_zero_shares(self) -> None:
        aggregated = breadcrumb_eval.aggregate_duplicate_metrics([])

        assert aggregated == {
            "chunks": 0,
            "documents": 0,
            "title_share": 0.0,
            "in_content_share": 0.0,
            "subchunk_share": 0.0,
            "title_equals_heading_share": 0.0,
        }


class TestArtifact:
    """The artifact is aggregate-only, guarded, and countable on insufficiency."""

    def _build(self, tmp_path: Path) -> dict[str, Any]:
        spec = breadcrumb_eval.build_arm_spec(tmp_path)
        return breadcrumb_eval.build_breadcrumb_artifact(
            decision=_decision(),
            spec=spec,
            identity=IDENTITY,
            confirmation={"n": 101, "mean_delta": 0.02, "winner": True, "sufficient": True},
            legs={
                "body": {"n": 101, "mean_delta": 0.02, "winner": True, "sufficient": True},
                "title": {"n": 101, "mean_delta": 0.03, "winner": True, "sufficient": True},
                "replay": {"n": 101, "mean_delta": 0.0, "winner": False, "sufficient": True},
            },
            duplicates={"chunks": 100, "documents": 10, "title_share": 1.0},
            corpus_label="phase23-zh-heavy",
            corpus_fingerprint="b5d50ce0c696ab3d",
            baseline_source="saved-run",
        )

    def test_declared_keys_and_identity_are_recorded(self, tmp_path: Path) -> None:
        artifact = self._build(tmp_path)

        assert artifact["schema_version"] == 1
        assert artifact["decision"] == "adopt-breadcrumb"
        assert artifact["model_type"] == "modelscope"
        assert artifact["model_name"] == "Qwen/Qwen3-Embedding-0.6B"
        assert artifact["embedding_dim"] == 1024
        assert artifact["max_tokens"] == 512
        assert artifact["chunk_size"] == 512
        assert artifact["chunk_overlap"] == 128
        assert artifact["embed_breadcrumb"] is True
        assert artifact["identity"] == IDENTITY
        assert artifact["corpus_fingerprint"] == "b5d50ce0c696ab3d"
        assert artifact["baseline_source"] == "saved-run"
        assert artifact["selection_rule"] == "overall-heldout-plus-body-leg-veto"
        assert artifact["min_heldout_for_epsilon_win"] == 101
        assert "N=56" in artifact["limitation"]
        assert set(artifact["legs"]) == {"body", "title", "replay"}

    def test_artifact_is_aggregate_only(self, tmp_path: Path) -> None:
        artifact = self._build(tmp_path)
        serialized = json.dumps(artifact)

        assert str(tmp_path) not in serialized
        assert "What is the capital" not in serialized
        assert not any(
            isinstance(value, str) and value.startswith("/") for value in artifact.values()
        )
        assert artifact["decision_record"]["duplicate_summary"]["chunks"] == 100

    def test_differing_decision_requires_force(self, tmp_path: Path) -> None:
        path = tmp_path / "artifact.json"
        breadcrumb_eval.write_committed_artifact(
            {"decision": "keep-breadcrumb-off", "corpus_fingerprint": "abc"}, path=path
        )

        with pytest.raises(RuntimeError, match="--force"):
            breadcrumb_eval.write_committed_artifact(
                {"decision": "adopt-breadcrumb", "corpus_fingerprint": "abc"}, path=path
            )

        breadcrumb_eval.write_committed_artifact(
            {"decision": "adopt-breadcrumb", "corpus_fingerprint": "abc"}, path=path, force=True
        )
        assert json.loads(path.read_text(encoding="utf-8"))["decision"] == "adopt-breadcrumb"

    def test_differing_fingerprint_requires_force(self, tmp_path: Path) -> None:
        path = tmp_path / "artifact.json"
        breadcrumb_eval.write_committed_artifact(
            {"decision": "keep-breadcrumb-off", "corpus_fingerprint": "abc"}, path=path
        )

        with pytest.raises(RuntimeError, match="--force"):
            breadcrumb_eval.write_committed_artifact(
                {"decision": "keep-breadcrumb-off", "corpus_fingerprint": "def"}, path=path
            )

    def test_insufficient_evidence_exits_three_and_still_writes(self, tmp_path: Path) -> None:
        spec = breadcrumb_eval.build_arm_spec(tmp_path)
        path = tmp_path / "insufficient.json"
        decision = _decision(
            confirmation={"n": 0, "mean_delta": 0.0, "winner": False, "sufficient": False},
            legs={"body": {"n": 0, "mean_delta": 0.0, "winner": False, "sufficient": False}},
            duplicates={},
        )

        code, artifact = breadcrumb_eval.finalize_breadcrumb(
            decision=decision,
            spec=spec,
            identity=IDENTITY,
            confirmation={"n": 0, "mean_delta": 0.0, "winner": False, "sufficient": False},
            legs={},
            duplicates={},
            corpus_label="phase23-zh-heavy",
            corpus_fingerprint="b5d50ce0c696ab3d",
            baseline_source="fresh-baseline (no-saved-run)",
            artifact_path=path,
        )

        assert code == 3
        assert path.is_file()
        assert artifact["decision"] == "insufficient-evidence"
        assert artifact["duplicates"] == {}
        assert json.loads(path.read_text(encoding="utf-8"))["decision"] == "insufficient-evidence"


class TestRunGuards:
    """Guards fire before any stage command exists."""

    def test_parent_child_corpus_roots_are_refused_before_a_command(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def _fail(*_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("no subprocess may start for a refused corpus set")

        monkeypatch.setattr(breadcrumb_eval.subprocess, "run", _fail)
        code = breadcrumb_eval.main(
            [
                "--corpus",
                str(tmp_path / "corpus"),
                "--corpus",
                str(tmp_path / "corpus" / "nested"),
                "--scratch-root",
                str(tmp_path / "scratch"),
            ]
        )

        assert code == 2
        assert "REFUSED" in capsys.readouterr().err
        assert not (tmp_path / "scratch").exists()

    def test_scratch_root_equal_to_home_is_refused_before_a_command(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def _fail(*_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("no subprocess may start for a refused scratch root")

        monkeypatch.setattr(breadcrumb_eval.subprocess, "run", _fail)
        code = breadcrumb_eval.main(
            ["--corpus", str(tmp_path / "corpus"), "--scratch-root", str(Path.home())]
        )

        assert code == 2
        assert "REFUSED" in capsys.readouterr().err

    def test_probe_identity_requires_an_index(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = breadcrumb_eval.main(["--probe-identity"])

        assert code == 2
        assert "--index" in capsys.readouterr().err
