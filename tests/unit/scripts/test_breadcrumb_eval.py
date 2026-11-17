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
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


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
