"""Unit battery for the Phase 24 chunk-sweep runbook (QUAL-02).

Pure-function tests for the six-arm dry-run plan: grid order, the fixed
modelscope Qwen3/512 embed contract, per-arm env isolation, the ordered
index/embed/identity/eval stage plan, the baseline language gate, and the
no-subprocess dry run. Nothing here loads a model or runs the ``sif`` CLI:
real sweep evidence is a recorded manual run, never a CI test.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from sif.search import personal_bench
from sif.search.tuning_verdict import SWEEP_GRID


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

EXPECTED_GRID = [
    ("baseline-512-128", 512, 128),
    ("overlap-64", 512, 64),
    ("overlap-0", 512, 0),
    ("near-default-448-112", 448, 112),
    ("smaller-384-96", 384, 96),
    ("smallest-256-64", 256, 64),
]


def _payload(tmp_path: Path) -> dict[str, Any]:
    """A dry-run payload for one throwaway corpus root and scratch root."""
    return chunk_sweep.build_dry_run_payload(tmp_path, [tmp_path / "corpus-a"])


class TestDryRunGrid:
    """The dry-run plan proves the six-arm grid and fixed embed contract."""

    def test_six_arms_in_declared_order(self, tmp_path: Path) -> None:
        payload = _payload(tmp_path)

        assert len(payload["arms"]) == 6
        assert [
            (arm["name"], arm["chunk_size"], arm["chunk_overlap"]) for arm in payload["arms"]
        ] == EXPECTED_GRID
        assert payload["grid"] == [
            {"name": name, "chunk_size": size, "chunk_overlap": overlap}
            for name, size, overlap in EXPECTED_GRID
        ]

    def test_every_arm_pins_modelscope_qwen3_and_max_tokens(self, tmp_path: Path) -> None:
        for arm in _payload(tmp_path)["arms"]:
            assert arm["max_tokens"] == 512
            assert arm["model_name"] == "Qwen/Qwen3-Embedding-0.6B"
            assert arm["model_type"] == "modelscope"

    def test_every_arm_has_its_own_db_under_the_scratch_root(self, tmp_path: Path) -> None:
        db_paths = [arm["db_path"] for arm in _payload(tmp_path)["arms"]]
        assert len(set(db_paths)) == 6
        assert all(not Path(path).is_absolute() for path in db_paths)
        assert all(path.endswith(".db") for path in db_paths)

    def test_only_chunk_settings_vary_between_arm_envs(self, tmp_path: Path) -> None:
        payload = _payload(tmp_path)
        envs: list[dict[str, str]] = []
        for entry in payload["commands"]:
            for stage in entry["stages"]:
                env = stage["env"]
                assert env["SIF_MAX_TOKENS"] == "512"
                assert env["SIF_EMBEDDING_DIM"] == "1024"
                assert env["SIF_MODEL_NAME"] == "Qwen/Qwen3-Embedding-0.6B"
                assert env["SIF_MODEL_TYPE"] == "modelscope"
                envs.append(env)

        chunk_pairs = {(env["SIF_CHUNK_SIZE"], env["SIF_CHUNK_OVERLAP"]) for env in envs}
        assert chunk_pairs == {(str(size), str(overlap)) for _name, size, overlap in EXPECTED_GRID}

        fixed_envs = {
            tuple(
                sorted(
                    (key, value)
                    for key, value in env.items()
                    if key not in ("SIF_CHUNK_SIZE", "SIF_CHUNK_OVERLAP")
                )
            )
            for env in envs
        }
        assert len(fixed_envs) == 1

    def test_removed_overrides_never_leak_into_an_arm(self, tmp_path: Path) -> None:
        arm_spec = chunk_sweep.build_sweep_arms(tmp_path)[0]
        base = {
            "SIF_API_KEY": "secret",
            "SIF_API_BASE": "https://example.invalid",
            "SIF_MODEL_PATH": "/tmp/model",
            "SIF_DB_PATH": "/tmp/other.db",
            "SIF_EMBED_BREADCRUMB": "1",
            "SIF_QUERY_PROMPT_NAME": "query",
            "SIF_DOCUMENT_PROMPT_NAME": "document",
        }

        env = chunk_sweep.build_arm_env(base, arm_spec)

        for key in base:
            assert key not in env
        assert env["SIF_CHUNK_SIZE"] == "512"
        assert env["SIF_CHUNK_OVERLAP"] == "128"

    def test_expected_identity_and_selection_rule(self, tmp_path: Path) -> None:
        payload = _payload(tmp_path)

        assert payload["expected_identity"] == {
            "cache_model_id": "modelscope:Qwen/Qwen3-Embedding-0.6B",
            "dimension": 1024,
            "query_prompt": None,
            "document_prompt": None,
        }
        assert payload["selection_rule"] == "tuning-select-then-heldout-confirm"


class TestDryRunCommands:
    """Every arm carries the ordered index/embed/identity/eval stage plan."""

    def test_stage_order_per_arm(self, tmp_path: Path) -> None:
        for entry in _payload(tmp_path)["commands"]:
            name = entry["arm"]
            assert [stage["stage"] for stage in entry["stages"]] == [
                f"arm:{name}:index",
                f"arm:{name}:embed",
                f"arm:{name}:identity",
                f"arm:{name}:eval",
            ]

    def test_every_sif_argv_is_quiet_and_index_scoped(self, tmp_path: Path) -> None:
        for entry in _payload(tmp_path)["commands"]:
            for stage in entry["stages"]:
                for argv in stage["commands"]:
                    assert isinstance(argv, list)
                    if "sif.cli.main" in argv:
                        assert "-q" in argv
                        assert "--index" in argv

    def test_index_stage_adds_every_root_then_updates(self, tmp_path: Path) -> None:
        payload = chunk_sweep.build_dry_run_payload(
            tmp_path, [tmp_path / "corpus-a", tmp_path / "corpus-b"]
        )
        index_stage = payload["commands"][0]["stages"][0]

        assert len(index_stage["commands"]) == 3
        assert index_stage["commands"][0][-3:] == [
            str(tmp_path / "corpus-a"),
            "--name",
            "phase24-1",
        ]
        assert index_stage["commands"][1][-3:] == [
            str(tmp_path / "corpus-b"),
            "--name",
            "phase24-2",
        ]
        assert index_stage["commands"][2][-2:] == ["index", "update"]

    def test_embed_is_a_forced_rechunk(self, tmp_path: Path) -> None:
        embed_stage = _payload(tmp_path)["commands"][0]["stages"][1]
        assert embed_stage["commands"][0][-5:] == [
            "index",
            "embed",
            "--force",
            "--chunk-strategy",
            "auto",
        ]

    def test_identity_stage_uses_the_probe_mode(self, tmp_path: Path) -> None:
        for entry in _payload(tmp_path)["commands"]:
            identity_argv = entry["stages"][2]["commands"][0]
            assert "--probe-identity" in identity_argv
            assert identity_argv[identity_argv.index("--index") + 1].endswith(".db")

    def test_baseline_requires_both_languages_without_a_saved_run(self, tmp_path: Path) -> None:
        payload = _payload(tmp_path)
        baseline_argv = payload["commands"][0]["stages"][3]["commands"][0]

        assert baseline_argv.count("--require-language") == 2
        assert baseline_argv.count("--min-heldout") == 1
        assert baseline_argv[baseline_argv.index("--min-heldout") + 1] == "101"
        assert "--compare" not in baseline_argv

        for entry in payload["commands"][1:]:
            compare_argv = entry["stages"][3]["commands"][0]
            assert "--compare" in compare_argv
            assert compare_argv[compare_argv.index("--compare") + 1].endswith("baseline.json")


class TestDryRunInvocation:
    """``--dry-run`` invokes no subprocess and writes nothing."""

    def test_dry_run_json_invokes_no_subprocess(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def _fail(*_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("dry run must not invoke a subprocess")

        monkeypatch.setattr(subprocess, "run", _fail)

        code = chunk_sweep.main(
            [
                "--dry-run",
                "--json",
                "--scratch-root",
                str(tmp_path),
                "--corpus",
                str(tmp_path / "corpus-a"),
            ]
        )

        assert code == 0
        payload = json.loads(capsys.readouterr().out)
        assert len(payload["commands"]) == 6
        assert not any(tmp_path.iterdir())

    def test_dry_run_human_table(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        code = chunk_sweep.main(
            ["--dry-run", "--scratch-root", str(tmp_path), "--corpus", str(tmp_path / "corpus-a")]
        )

        assert code == 0
        output = capsys.readouterr().out
        assert "baseline-512-128" in output
        assert "modelscope:Qwen/Qwen3-Embedding-0.6B" in output

    def test_nested_corpus_roots_are_refused(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = chunk_sweep.main(
            [
                "--dry-run",
                "--scratch-root",
                str(tmp_path),
                "--corpus",
                str(tmp_path / "corpus-a"),
                "--corpus",
                str(tmp_path / "corpus-a" / "nested"),
            ]
        )

        assert code == 2
        assert "REFUSED" in capsys.readouterr().err

    def test_nested_roots_are_refused_before_any_command_is_built(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        built: list[int] = []
        monkeypatch.setattr(
            chunk_sweep,
            "build_arm_commands",
            lambda *_args, **_kwargs: built.append(1) or [],
        )

        code = chunk_sweep.main(
            [
                "--dry-run",
                "--scratch-root",
                str(tmp_path),
                "--corpus",
                str(tmp_path / "corpus-a"),
                "--corpus",
                str(tmp_path / "corpus-a" / "nested"),
            ]
        )

        assert code == 2
        assert built == []

    def test_every_arm_stage_carries_the_arm_chunk_env(self, tmp_path: Path) -> None:
        payload = _payload(tmp_path)
        for entry in payload["commands"]:
            arm = next(item for item in payload["arms"] if item["name"] == entry["arm"])
            for stage in entry["stages"]:
                assert stage["env"]["SIF_CHUNK_SIZE"] == str(arm["chunk_size"])
                assert stage["env"]["SIF_CHUNK_OVERLAP"] == str(arm["chunk_overlap"])

    def test_home_scratch_root_is_refused(self, tmp_path: Path) -> None:
        code = chunk_sweep.main(
            [
                "--dry-run",
                "--scratch-root",
                str(Path.home()),
                "--corpus",
                str(tmp_path / "corpus-a"),
            ]
        )

        assert code == 2


class TestScopeResume:
    """Resume is keyed on the corpus roots, label, and scratch root."""

    def test_changed_scope_discards_prior_markers(self, tmp_path: Path) -> None:
        state_path = tmp_path / "run-state.json"
        scope_a = chunk_sweep.scope_state([tmp_path / "a"], tmp_path, "label")
        key_a = chunk_sweep.scope_key(scope_a)
        state = chunk_sweep.load_run_state(state_path, scope_key=key_a, scope=scope_a)
        chunk_sweep.mark_stage(state, "arm:baseline-512-128:index", {"documents": 498})
        chunk_sweep.save_run_state(state_path, state)

        resumed = chunk_sweep.load_run_state(state_path, scope_key=key_a, scope=scope_a)
        assert harrier_eval.stage_done(resumed, "arm:baseline-512-128:index")

        scope_b = chunk_sweep.scope_state([tmp_path / "b"], tmp_path, "label")
        fresh = chunk_sweep.load_run_state(
            state_path, scope_key=chunk_sweep.scope_key(scope_b), scope=scope_b
        )
        assert not harrier_eval.stage_done(fresh, "arm:baseline-512-128:index")

    def test_unknown_stage_is_refused(self) -> None:
        state = {"stages": {}}
        with pytest.raises(ValueError, match="unknown stage"):
            chunk_sweep.mark_stage(state, "arm:not-an-arm:rollup")

    def test_state_writes_are_atomic_and_sorted(self, tmp_path: Path) -> None:
        state_path = tmp_path / "run-state.json"
        chunk_sweep.save_run_state(state_path, {"b": 2, "a": 1, "stages": {}})

        text = state_path.read_text()
        assert text.endswith("\n")
        assert text.index('"a"') < text.index('"b"')
        assert not list(tmp_path.glob("*.tmp"))


class TestStageFailure:
    """A failing stage is recorded and stops before every later stage."""

    def test_nonzero_exit_records_the_failing_stage(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        arm_spec = chunk_sweep.build_sweep_arms(tmp_path)[0]
        stages = chunk_sweep.build_arm_commands(arm_spec, [tmp_path / "corpus"], None)
        state_path = tmp_path / "run-state.json"
        state = chunk_sweep.load_run_state(state_path, scope_key="k", scope={})
        proc = subprocess.CompletedProcess(args=[], returncode=7, stdout="", stderr="boom")
        monkeypatch.setattr(chunk_sweep.subprocess, "run", lambda *_a, **_k: proc)

        status = chunk_sweep._execute_arm_arm_stage(
            state,
            state_path,
            stages[0],
            arm_spec,
            {},
            cache_db_path=tmp_path / "cache.db",
        )

        assert status == 1
        assert state["failed_stage"] == stages[0]["stage"]
        assert json.loads(state_path.read_text())["failed_stage"] == stages[0]["stage"]
        assert not harrier_eval.stage_done(state, stages[0]["stage"])


class TestIdentityGate:
    """Every arm must persist the fixed modelscope Qwen3 identity."""

    def _stored(self, **overrides: Any) -> SimpleNamespace:
        fields: dict[str, Any] = {
            "cache_model_id": chunk_sweep.QWEN3_CACHE_MODEL_ID,
            "dimension": 1024,
            "source": "verified",
            "query_prompt": None,
            "document_prompt": None,
        }
        fields.update(overrides)
        return SimpleNamespace(**fields)

    def test_valid_identity_passes(self) -> None:
        assert chunk_sweep.identity_failures(self._stored()) == []

    def test_wrong_backend_cache_id_fails(self) -> None:
        stored = self._stored(cache_model_id="sentence_transformers:microsoft/harrier-oss-v1-0.6b")

        failures = chunk_sweep.identity_failures(stored)

        assert len(failures) == 1
        assert "cache_model_id" in failures[0]

    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"dimension": 768}, "dimension"),
            ({"source": "declared"}, "source"),
            ({"query_prompt": "web_search_query"}, "query_prompt"),
            ({"document_prompt": "passage"}, "document_prompt"),
        ],
    )
    def test_other_mismatches_name_the_field(self, overrides: dict[str, Any], field: str) -> None:
        failures = chunk_sweep.identity_failures(self._stored(**overrides))

        assert any(field in failure for failure in failures)

    def test_probe_payload_with_harrier_identity_is_refused(self) -> None:
        payload = {
            "cache_model_id": "sentence_transformers:microsoft/harrier-oss-v1-0.6b",
            "dimension": 1024,
            "source": "verified",
            "query_prompt": "web_search_query",
            "document_prompt": None,
        }

        with pytest.raises(ValueError, match="cache_model_id"):
            chunk_sweep.require_probe_identity(payload)


class TestBaselineRule:
    """A saved run from another corpus or backend is never the baseline."""

    def _patch_saved_run(
        self, monkeypatch: pytest.MonkeyPatch, *, fingerprint: str, model: dict[str, Any]
    ) -> None:
        saved = SimpleNamespace(corpus={"fingerprint": fingerprint}, model=model)
        monkeypatch.setattr(personal_bench, "load_saved_run", lambda _path: saved)

    def test_usable_saved_run_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_saved_run(
            monkeypatch,
            fingerprint="live123",
            model={"model_type": "modelscope", "model_name": chunk_sweep.MODEL_NAME},
        )

        assert chunk_sweep.baseline_rejection_reason(Path("saved.json"), "live123") is None

    def test_sentence_transformers_backend_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._patch_saved_run(
            monkeypatch,
            fingerprint="live123",
            model={
                "model_type": "sentence_transformers",
                "model_name": chunk_sweep.MODEL_NAME,
            },
        )

        assert (
            chunk_sweep.baseline_rejection_reason(Path("saved.json"), "live123")
            == "model-type-mismatch"
        )

    def test_different_model_name_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_saved_run(
            monkeypatch,
            fingerprint="live123",
            model={"model_type": "modelscope", "model_name": "Qwen/Qwen2.5-0.5B-Instruct"},
        )

        assert (
            chunk_sweep.baseline_rejection_reason(Path("saved.json"), "live123")
            == "model-name-mismatch"
        )

    def test_fingerprint_mismatch_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_saved_run(
            monkeypatch,
            fingerprint="recorded999",
            model={"model_type": "modelscope", "model_name": chunk_sweep.MODEL_NAME},
        )

        assert (
            chunk_sweep.baseline_rejection_reason(Path("saved.json"), "live123")
            == "corpus-fingerprint-mismatch"
        )

    def test_missing_saved_run_is_rejected(self) -> None:
        assert chunk_sweep.baseline_rejection_reason(None, "live123") == "no-saved-run"

    def test_unreadable_saved_run_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(_path: Path) -> None:
            raise ValueError("bad payload")

        monkeypatch.setattr(personal_bench, "load_saved_run", _raise)

        assert (
            chunk_sweep.baseline_rejection_reason(Path("saved.json"), "live123")
            == "invalid-saved-run"
        )


def _artifact_results(
    *, candidate: str | None = None, heldout_winner: bool = False
) -> dict[str, Any]:
    """Six-arm results with one optional tuning candidate and held-out gate."""
    results: dict[str, Any] = {}
    for arm in SWEEP_GRID:
        is_candidate = arm.name == candidate
        results[arm.name] = {
            "costs": {
                "documents": 498,
                "chunks": 100,
                "embedded_documents": 498,
                "embed_wall_seconds": 10.0 if is_candidate else 20.0,
                "cache_rows_before": 5,
                "cache_rows_after": 6,
                "cache_hits": 94,
            },
            "identity": {
                "cache_model_id": chunk_sweep.QWEN3_CACHE_MODEL_ID,
                "dimension": 1024,
                "source": "verified",
                "query_prompt": None,
                "document_prompt": None,
                "check_identity_status": "ok",
            },
            "tuning": {
                "n": 42,
                "mean_delta": 0.02 if is_candidate else 0.0,
                "winner": False,
                "sufficient": True,
            },
            "heldout": {
                "n": 56,
                "mean_delta": 0.02 if is_candidate else 0.0,
                "winner": heldout_winner and is_candidate,
                "sufficient": True,
            },
        }
    return results


class TestLimitation:
    """The limitation text is corpus-scoped and names the measured N."""

    def test_above_the_epsilon_floor_reports_an_admissible_sample(self) -> None:
        text = chunk_sweep.build_limitation("books-markdown-papers-2026-11", 239)

        assert "books-markdown-papers-2026-11" in text
        assert "239" in text
        assert "101" in text
        assert "at or above" in text

    def test_below_the_epsilon_floor_names_the_shortfall(self) -> None:
        text = chunk_sweep.build_limitation("books-markdown-papers-2026-11", 43)

        assert "43" in text
        assert "101" in text
        assert "below" in text


class TestArtifact:
    """The committed artifact is aggregate-only and in grid order."""

    def test_declared_keys_and_grid_order(self) -> None:
        artifact = chunk_sweep.build_sweep_artifact(
            grid=SWEEP_GRID,
            results=_artifact_results(candidate="smaller-384-96"),
            corpus_label="phase23-zh-heavy",
            corpus_fingerprint="b5d50ce0c696ab3d",
            baseline_source="saved-run",
        )

        assert set(artifact) == {
            "schema_version",
            "decision",
            "selected_arm",
            "tuning_mean_delta",
            "confirmation",
            "arms",
            "grid",
            "model_name",
            "model_type",
            "embedding_dim",
            "max_tokens",
            "corpus_label",
            "corpus_fingerprint",
            "baseline_source",
            "selection_rule",
            "min_heldout_for_epsilon_win",
            "limitation",
        }
        assert [arm["name"] for arm in artifact["arms"]] == [arm.name for arm in SWEEP_GRID]
        assert artifact["model_type"] == "modelscope"
        assert artifact["max_tokens"] == 512
        assert artifact["min_heldout_for_epsilon_win"] == 101
        assert artifact["selection_rule"] == "tuning-select-then-heldout-confirm"
        assert "56" in artifact["limitation"]
        assert "101" in artifact["limitation"]
        for arm in artifact["arms"]:
            assert set(arm["identity"]) == set(chunk_sweep.IDENTITY_KEYS)
            for cost_key in (
                "documents",
                "chunks",
                "embedded_documents",
                "embed_wall_seconds",
                "cache_rows_before",
                "cache_rows_after",
                "cache_hits",
            ):
                assert isinstance(arm[cost_key], int | float)

    def test_no_absolute_paths_or_query_text(self, tmp_path: Path) -> None:
        artifact = chunk_sweep.build_sweep_artifact(
            grid=SWEEP_GRID,
            results=_artifact_results(candidate="smaller-384-96"),
            corpus_label="phase23-zh-heavy",
            corpus_fingerprint="b5d50ce0c696ab3d",
            baseline_source="fresh-baseline (no-saved-run)",
        )

        serialized = json.dumps(artifact)
        assert str(tmp_path) not in serialized
        assert str(Path.home()) not in serialized
        assert "query_text" not in serialized
        assert '"query":' not in serialized

    def test_tuning_candidate_is_selected_then_heldout_confirmed(self) -> None:
        keep = chunk_sweep.build_sweep_artifact(
            grid=SWEEP_GRID,
            results=_artifact_results(candidate="smaller-384-96"),
            corpus_label="phase23-zh-heavy",
            corpus_fingerprint="b5d50ce0c696ab3d",
            baseline_source="saved-run",
        )
        assert keep["selected_arm"] == "smaller-384-96"
        assert keep["decision"] == "keep-default"

        adopt = chunk_sweep.build_sweep_artifact(
            grid=SWEEP_GRID,
            results=_artifact_results(candidate="smaller-384-96", heldout_winner=True),
            corpus_label="phase23-zh-heavy",
            corpus_fingerprint="b5d50ce0c696ab3d",
            baseline_source="saved-run",
        )
        assert adopt["decision"] == "adopt-chunking"

    def test_empty_results_are_insufficient_and_countable(self, tmp_path: Path) -> None:
        artifact_path = tmp_path / "chunk-sweep.json"

        code, artifact = chunk_sweep.finalize_sweep(
            grid=SWEEP_GRID,
            results={},
            corpus_label="phase23-zh-heavy",
            corpus_fingerprint="b5d50ce0c696ab3d",
            baseline_source="fresh-baseline (no-saved-run)",
            artifact_path=artifact_path,
        )

        assert code == 3
        assert artifact["decision"] == "insufficient-evidence"
        written = json.loads(artifact_path.read_text())
        assert len(written["arms"]) == 6
        assert written["decision"] == "insufficient-evidence"


class TestArtifactGuard:
    """A different decision or corpus is refused without ``--force``."""

    def _write(self, path: Path, *, decision: str, fingerprint: str) -> None:
        path.write_text(
            json.dumps({"decision": decision, "corpus_fingerprint": fingerprint}) + "\n"
        )

    def test_same_run_rewrite_is_allowed(self, tmp_path: Path) -> None:
        path = tmp_path / "artifact.json"
        self._write(path, decision="keep-default", fingerprint="b5d50ce0c696ab3d")

        chunk_sweep.write_committed_artifact(
            {"decision": "keep-default", "corpus_fingerprint": "b5d50ce0c696ab3d"},
            path=path,
        )

        assert json.loads(path.read_text())["decision"] == "keep-default"

    def test_different_decision_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "artifact.json"
        self._write(path, decision="keep-default", fingerprint="b5d50ce0c696ab3d")

        with pytest.raises(RuntimeError, match="refusing to overwrite"):
            chunk_sweep.write_committed_artifact(
                {"decision": "adopt-chunking", "corpus_fingerprint": "b5d50ce0c696ab3d"},
                path=path,
            )

    def test_force_replaces_a_different_run(self, tmp_path: Path) -> None:
        path = tmp_path / "artifact.json"
        self._write(path, decision="keep-default", fingerprint="b5d50ce0c696ab3d")

        chunk_sweep.write_committed_artifact(
            {"decision": "adopt-chunking", "corpus_fingerprint": "aaaaaaaaaaaaaaaa"},
            force=True,
            path=path,
        )

        written = json.loads(path.read_text())
        assert written["decision"] == "adopt-chunking"
        assert written["corpus_fingerprint"] == "aaaaaaaaaaaaaaaa"
