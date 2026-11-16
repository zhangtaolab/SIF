"""Unit battery for the Phase 23 two-arm evaluation runbook (MODEL-01/MODEL-02).

Pure-function tests for the dry-run command plan, corpus-root guard, identity
gate, probe argv, run-state machine, adequacy preflight, artifact builder, and
cleanup guard. Nothing here loads a model, downloads a snapshot, or runs the
``sif`` CLI: real two-arm evidence is a recorded manual run, never a CI test
(D-13).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import harrier_eval
from scripts.harrier_eval import (
    ARTIFACT_PATH,
    BATCH_SIZE,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_DIM,
    HARRIER_MODEL_NAME,
    HARRIER_MODEL_TYPE,
    MAX_TOKENS,
    QWEN3_MODEL_NAME,
    QWEN3_MODEL_TYPE,
    build_arm,
    build_arm_commands,
    build_arm_env,
    build_arms,
    build_dry_run_payload,
    main,
    resolve_corpus_roots,
)


class TestDryRun:
    """The exact two-arm plan is inspectable before any model download."""

    def test_both_arm_command_tables_exist(self, tmp_path: Path) -> None:
        arms = build_arms(tmp_path)
        payload = build_dry_run_payload("python", arms, [tmp_path], ARTIFACT_PATH)

        assert set(payload["commands"]) == {"qwen3", "harrier"}
        assert payload["commands"]["qwen3"]
        assert payload["commands"]["harrier"]
        assert payload["planned_artifact"]["min_heldout_for_epsilon_win"] == 101

    def test_every_command_is_an_argv_list_with_quiet_and_index(self, tmp_path: Path) -> None:
        for arm in build_arms(tmp_path).values():
            for command in build_arm_commands("python", arm, [tmp_path]):
                assert isinstance(command.argv, list)
                assert command.argv[:5] == [
                    "python",
                    "-m",
                    "sif.cli.main",
                    "-q",
                    "--index",
                ]
                assert command.argv[5] == str(arm.db_path)
                assert all(isinstance(item, str) for item in command.argv)

    def test_arm_envs_remove_api_keys_and_prompt_overrides(self, tmp_path: Path) -> None:
        base = {
            "SIF_API_BASE": "https://example.invalid",
            "SIF_API_KEY": "secret",
            "SIF_QUERY_PROMPT_NAME": "wrong_query_prompt",
            "SIF_DOCUMENT_PROMPT_NAME": "wrong_document_prompt",
            "SIF_MODEL_PATH": "/tmp/model.gguf",
            "SIF_DB_PATH": "/tmp/other.db",
        }
        for arm in build_arms(tmp_path).values():
            env = build_arm_env(base, arm)
            for key in (
                "SIF_API_BASE",
                "SIF_API_KEY",
                "SIF_QUERY_PROMPT_NAME",
                "SIF_DOCUMENT_PROMPT_NAME",
                "SIF_MODEL_PATH",
                "SIF_DB_PATH",
            ):
                assert key not in env

    def test_arms_pin_identical_chunk_and_batch_values(self, tmp_path: Path) -> None:
        arms = build_arms(tmp_path)
        qwen3_env = build_arm_env({}, arms["qwen3"])
        harrier_env = build_arm_env({}, arms["harrier"])

        assert qwen3_env["SIF_MODEL_TYPE"] == QWEN3_MODEL_TYPE
        assert qwen3_env["SIF_MODEL_NAME"] == QWEN3_MODEL_NAME
        assert harrier_env["SIF_MODEL_TYPE"] == HARRIER_MODEL_TYPE
        assert harrier_env["SIF_MODEL_NAME"] == HARRIER_MODEL_NAME
        pinned = {
            "SIF_EMBEDDING_DIM": EMBEDDING_DIM,
            "SIF_MAX_TOKENS": MAX_TOKENS,
            "SIF_BATCH_SIZE": BATCH_SIZE,
            "SIF_CHUNK_SIZE": CHUNK_SIZE,
            "SIF_CHUNK_OVERLAP": CHUNK_OVERLAP,
        }
        for key, value in pinned.items():
            assert qwen3_env[key] == str(value)
            assert harrier_env[key] == str(value)

    def test_no_command_passes_a_prompt_override(self, tmp_path: Path) -> None:
        for arm in build_arms(tmp_path).values():
            for command in build_arm_commands("python", arm, [tmp_path]):
                joined = " ".join(command.argv)
                assert "--query-prompt" not in joined
                assert "--document-prompt" not in joined
                assert "default_prompt_name" not in joined

    def test_baseline_eval_requires_both_languages(self, tmp_path: Path) -> None:
        arm = build_arm("qwen3", tmp_path)
        commands = build_arm_commands("python", arm, [tmp_path])
        eval_command = next(command for command in commands if command.stage == "eval")

        assert eval_command.argv.count("--require-language") == 2
        assert "--compare" not in eval_command.argv

    def test_candidate_eval_compares_without_resampling(self, tmp_path: Path) -> None:
        arm = build_arm("harrier", tmp_path)
        saved_run = tmp_path / "saved-runs" / "qwen3.json"
        commands = build_arm_commands(
            "python",
            arm,
            [tmp_path],
            saved_run_path=saved_run,
        )
        eval_command = next(command for command in commands if command.stage == "eval")

        assert "--compare" in eval_command.argv
        assert str(saved_run) in eval_command.argv
        assert "--require-language" not in eval_command.argv

    def test_main_dry_run_invokes_no_subprocess(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def _fail(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("dry run must not call subprocess.run")

        monkeypatch.setattr(harrier_eval.subprocess, "run", _fail)

        assert main(["--dry-run", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["version"] == 1
        assert [arm["name"] for arm in payload["arms"]] == ["qwen3", "harrier"]


class TestCorpusRootsGuard:
    """Duplicate and nested corpus roots are refused before indexing."""

    def test_duplicate_resolved_roots_are_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="duplicate corpus root"):
            resolve_corpus_roots([tmp_path, tmp_path])

    def test_same_directory_spelled_twice_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="duplicate corpus root"):
            resolve_corpus_roots([tmp_path, tmp_path / "."])

    def test_parent_child_pair_is_refused_in_either_order(self, tmp_path: Path) -> None:
        child = tmp_path / "child"
        child.mkdir()

        with pytest.raises(ValueError, match="nested corpus roots"):
            resolve_corpus_roots([tmp_path, child])
        with pytest.raises(ValueError, match="nested corpus roots"):
            resolve_corpus_roots([child, tmp_path])

    def test_disjoint_roots_are_returned_in_supplied_order(self, tmp_path: Path) -> None:
        first = tmp_path / "first"
        second = tmp_path / "second"

        assert resolve_corpus_roots([second, first]) == (
            second.resolve(),
            first.resolve(),
        )

    def test_main_refuses_a_duplicate_before_building_any_command(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def _fail(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("no command plan may be built after a refusal")

        monkeypatch.setattr(harrier_eval, "build_arm_commands", _fail)
        monkeypatch.setattr(harrier_eval, "build_dry_run_payload", _fail)

        code = main(
            [
                "--dry-run",
                "--corpus",
                str(tmp_path),
                "--corpus",
                str(tmp_path / "."),
            ]
        )
        captured = capsys.readouterr()

        assert code == 2
        assert captured.err.startswith("REFUSED:")
        assert len(captured.err.strip().splitlines()) == 1

    def test_dry_run_applies_the_same_guard(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        code = main(["--dry-run", "--corpus", str(tmp_path), "--corpus", str(tmp_path)])

        assert code == 2
        assert "REFUSED" in capsys.readouterr().err
