"""Unit battery for the Phase 23 two-arm evaluation runbook (MODEL-01/MODEL-02).

Pure-function tests for the dry-run command plan, corpus-root guard, identity
gate, probe argv, run-state machine, adequacy preflight, artifact builder, and
cleanup guard. Nothing here loads a model, downloads a snapshot, or runs the
``sif`` CLI: real two-arm evidence is a recorded manual run, never a CI test
(D-13).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

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
    HARRIER_QUERY_PROMPT,
    MAX_TOKENS,
    QWEN3_CACHE_MODEL_ID,
    QWEN3_MODEL_NAME,
    QWEN3_MODEL_TYPE,
    ArmCommand,
    IdentityGateError,
    build_arm,
    build_arm_commands,
    build_arm_env,
    build_arms,
    build_dry_run_payload,
    load_run_state,
    main,
    mark_stage,
    parse_json_stdout,
    probe_arm_command,
    require_probe_ok,
    resolve_corpus_roots,
    run_command,
    save_run_state,
    scope_key,
    scope_state,
    stage_done,
    verify_arm_identity,
    verify_arm_pair,
)
from sif.embedding.identity import EmbedderIdentity


def _qwen3_identity(**overrides: Any) -> EmbedderIdentity:
    """The documented Qwen3 baseline identity (prompt-free, verified)."""
    fields: dict[str, Any] = {
        "schema_version": 1,
        "cache_model_id": QWEN3_CACHE_MODEL_ID,
        "model_name": QWEN3_MODEL_NAME,
        "model_type": QWEN3_MODEL_TYPE,
        "api_base": None,
        "dimension": EMBEDDING_DIM,
        "pooling": "last_token",
        "normalized": True,
        "query_prompt": None,
        "document_prompt": None,
        "prompt_supported": True,
        "revision": None,
        "source": "verified",
    }
    fields.update(overrides)
    return EmbedderIdentity(**fields)


def _harrier_identity(**overrides: Any) -> EmbedderIdentity:
    """The documented Harrier identity (web_search_query, no document prompt)."""
    fields: dict[str, Any] = {
        "schema_version": 1,
        "cache_model_id": f"{HARRIER_MODEL_TYPE}:{HARRIER_MODEL_NAME}",
        "model_name": HARRIER_MODEL_NAME,
        "model_type": HARRIER_MODEL_TYPE,
        "api_base": None,
        "dimension": EMBEDDING_DIM,
        "pooling": "last_token",
        "normalized": True,
        "query_prompt": HARRIER_QUERY_PROMPT,
        "document_prompt": None,
        "prompt_supported": True,
        "revision": "f9b9dc8d367d443f2479d27aa5d8d2850c0774ee",
        "source": "verified",
    }
    fields.update(overrides)
    return EmbedderIdentity(**fields)


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


class TestIdentityGate:
    """Every wrong-arm, unverified, or wrong-prompt identity is rejected."""

    def test_accepts_the_documented_qwen3_identity(self, tmp_path: Path) -> None:
        verify_arm_identity(_qwen3_identity(), build_arm("qwen3", tmp_path))

    def test_accepts_the_documented_harrier_identity(self, tmp_path: Path) -> None:
        verify_arm_identity(_harrier_identity(), build_arm("harrier", tmp_path))

    def test_rejects_a_missing_identity(self, tmp_path: Path) -> None:
        with pytest.raises(IdentityGateError, match="no stored embedder identity"):
            verify_arm_identity(None, build_arm("qwen3", tmp_path))

    def test_rejects_an_unverified_source(self, tmp_path: Path) -> None:
        with pytest.raises(IdentityGateError, match="source"):
            verify_arm_identity(
                _qwen3_identity(source="legacy-assumed"),
                build_arm("qwen3", tmp_path),
            )

    def test_rejects_a_swapped_model_name(self, tmp_path: Path) -> None:
        with pytest.raises(IdentityGateError, match="model_name"):
            verify_arm_identity(
                _harrier_identity(model_name=QWEN3_MODEL_NAME),
                build_arm("harrier", tmp_path),
            )

    def test_rejects_a_prompt_free_harrier_identity(self, tmp_path: Path) -> None:
        with pytest.raises(IdentityGateError, match="query_prompt"):
            verify_arm_identity(
                _harrier_identity(query_prompt=None),
                build_arm("harrier", tmp_path),
            )

    def test_rejects_a_harrier_document_prompt(self, tmp_path: Path) -> None:
        with pytest.raises(IdentityGateError, match="document_prompt"):
            verify_arm_identity(
                _harrier_identity(document_prompt="web_search_document"),
                build_arm("harrier", tmp_path),
            )

    def test_rejects_the_wrong_dimension(self, tmp_path: Path) -> None:
        with pytest.raises(IdentityGateError, match="dimension"):
            verify_arm_identity(
                _qwen3_identity(dimension=768),
                build_arm("qwen3", tmp_path),
            )

    def test_rejects_a_qwen3_prompt(self, tmp_path: Path) -> None:
        with pytest.raises(IdentityGateError, match="query_prompt"):
            verify_arm_identity(
                _qwen3_identity(query_prompt="web_search_query"),
                build_arm("qwen3", tmp_path),
            )

    def test_pair_rejects_identical_fingerprints(self) -> None:
        identity = _qwen3_identity()

        with pytest.raises(IdentityGateError, match="identical identity fingerprints"):
            verify_arm_pair(identity, identity)

    def test_pair_rejects_a_shared_cache_model_id(self) -> None:
        harrier = _harrier_identity(cache_model_id=QWEN3_CACHE_MODEL_ID)

        with pytest.raises(IdentityGateError, match="cache_model_id"):
            verify_arm_pair(_qwen3_identity(), harrier)

    def test_pair_accepts_the_documented_pair(self) -> None:
        verify_arm_pair(_qwen3_identity(), _harrier_identity())


class TestProbe:
    """The probe argv/env is the arm-isolated identity proof."""

    def test_probe_argv_names_the_probe_and_arm(self, tmp_path: Path) -> None:
        arm = build_arm("harrier", tmp_path)

        argv = probe_arm_command("python", arm)

        assert "--probe" in argv
        assert "--arm" in argv
        assert arm.name in argv
        assert argv[-2] == "--scratch-root"
        assert argv[-1] == str(tmp_path)

    def test_probe_env_is_the_arm_env(self, tmp_path: Path) -> None:
        arm = build_arm("harrier", tmp_path)
        env = build_arm_env(
            {
                "SIF_API_BASE": "https://example.invalid",
                "SIF_API_KEY": "secret",
                "SIF_QUERY_PROMPT_NAME": "wrong",
            },
            arm,
        )

        assert "SIF_API_BASE" not in env
        assert "SIF_API_KEY" not in env
        assert "SIF_QUERY_PROMPT_NAME" not in env
        assert env["SIF_MODEL_NAME"] == HARRIER_MODEL_NAME

    def test_require_probe_ok_accepts_an_ok_status(self, tmp_path: Path) -> None:
        arm = build_arm("qwen3", tmp_path)
        payload = {
            "identity": json.loads(_qwen3_identity().to_json()),
            "check_identity_status": "ok",
        }

        require_probe_ok(payload, arm)

    def test_require_probe_ok_rejects_a_mismatch_status(self, tmp_path: Path) -> None:
        arm = build_arm("qwen3", tmp_path)
        payload = {
            "identity": json.loads(_qwen3_identity().to_json()),
            "check_identity_status": "mismatch",
        }

        with pytest.raises(IdentityGateError, match="check_identity status"):
            require_probe_ok(payload, arm)


class TestStageMachine:
    """Run-state is scope-keyed, atomic, resumable, and timeout-bounded."""

    def _scope(self, tmp_path: Path) -> dict[str, Any]:
        return scope_state([tmp_path / "corpus"], tmp_path / "scratch", "personal")

    def test_round_trips_run_state_json(self, tmp_path: Path) -> None:
        scope = self._scope(tmp_path)
        key = scope_key(scope)
        state_path = tmp_path / "run-state.json"
        state = load_run_state(state_path, scope_key=key, scope=scope)
        mark_stage(state, "arm_a_index", {"documents": 12})
        save_run_state(state_path, state)

        loaded = load_run_state(state_path, scope_key=key, scope=scope)

        assert loaded["scope_key"] == key
        assert loaded["scope"] == scope
        assert stage_done(loaded, "arm_a_index")
        assert loaded["stages"]["arm_a_index"]["detail"] == {"documents": 12}

    def test_completed_stage_is_skipped_and_a_new_stage_marks(self, tmp_path: Path) -> None:
        scope = self._scope(tmp_path)
        key = scope_key(scope)
        state = load_run_state(tmp_path / "run-state.json", scope_key=key, scope=scope)

        assert not stage_done(state, "arm_a_index")
        mark_stage(state, "arm_a_index")
        assert stage_done(state, "arm_a_index")
        assert not stage_done(state, "adequacy")
        mark_stage(state, "adequacy", {"adequate": True})
        assert stage_done(state, "adequacy")

    def test_resume_preserves_prior_markers_after_a_failure(self, tmp_path: Path) -> None:
        scope = self._scope(tmp_path)
        key = scope_key(scope)
        state_path = tmp_path / "run-state.json"
        state = load_run_state(state_path, scope_key=key, scope=scope)
        mark_stage(state, "arm_a_index")
        save_run_state(state_path, state)

        resumed = load_run_state(state_path, scope_key=key, scope=scope)

        assert stage_done(resumed, "arm_a_index")
        assert not stage_done(resumed, "adequacy")

    def test_changed_scope_key_discards_every_marker(self, tmp_path: Path) -> None:
        original = self._scope(tmp_path)
        state_path = tmp_path / "run-state.json"
        state = load_run_state(state_path, scope_key=scope_key(original), scope=original)
        mark_stage(state, "arm_a_index")
        save_run_state(state_path, state)
        changed = scope_state(
            [tmp_path / "other-corpus"],
            tmp_path / "scratch",
            "personal",
        )

        fresh = load_run_state(state_path, scope_key=scope_key(changed), scope=changed)

        assert fresh["stages"] == {}
        assert fresh["scope_key"] == scope_key(changed)
        assert fresh["scope"] == changed

    def test_timeout_is_a_named_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _timeout(*_args: object, **_kwargs: object) -> None:
            raise subprocess.TimeoutExpired("cmd", 5)

        monkeypatch.setattr(harrier_eval.subprocess, "run", _timeout)
        command = ArmCommand(stage="index_embed", argv=["false"], env={})

        with pytest.raises(RuntimeError, match="index_embed timed out after 5"):
            run_command(command, timeout=5)

    def test_parse_accepts_the_compare_model_notice(self) -> None:
        proc = subprocess.CompletedProcess(
            ["cmd"],
            0,
            '{"ok": true}',
            "Model identity differs: the saved run used ...",
        )

        assert parse_json_stdout(proc, "arm_b_eval") == {"ok": True}

    def test_parse_rejects_the_identity_mismatch_guard(self) -> None:
        proc = subprocess.CompletedProcess(
            ["cmd"],
            0,
            '{"ok": true}',
            "WARNING: Embedder identity mismatch: index vectors were produced by ...",
        )

        with pytest.raises(RuntimeError, match="identity mismatch"):
            parse_json_stdout(proc, "arm_a_eval")

    def test_parse_rejects_a_nonzero_exit(self) -> None:
        proc = subprocess.CompletedProcess(["cmd"], 2, "", "boom")

        with pytest.raises(RuntimeError, match="exit 2"):
            parse_json_stdout(proc, "arm_a_eval")

    def test_parse_rejects_non_json_stdout(self) -> None:
        proc = subprocess.CompletedProcess(["cmd"], 0, "not json", "")

        with pytest.raises(RuntimeError, match="did not emit JSON"):
            parse_json_stdout(proc, "arm_a_eval")
