"""Unit battery for the Phase 23 two-arm evaluation runbook (MODEL-01/MODEL-02).

Pure-function tests for the dry-run command plan, corpus-root guard, identity
gate, probe argv, run-state machine, adequacy preflight, artifact builder, and
cleanup guard. Nothing here loads a model, downloads a snapshot, or runs the
``sif`` CLI: real two-arm evidence is a recorded manual run, never a CI test
(D-13).
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace
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
    MIN_FREE_DISK_BYTES,
    QWEN3_CACHE_MODEL_ID,
    QWEN3_MODEL_NAME,
    QWEN3_MODEL_TYPE,
    ArmCommand,
    IdentityGateError,
    assert_disk_headroom,
    assert_within_scratch,
    build_arm,
    build_arm_commands,
    build_arm_env,
    build_arms,
    build_artifact,
    build_dry_run_payload,
    cleanup_arms,
    load_run_state,
    main,
    mark_stage,
    parse_json_stdout,
    probe_arm_command,
    query_set_fingerprint,
    require_probe_ok,
    resolve_corpus_roots,
    run_command,
    save_run_state,
    scope_key,
    scope_state,
    stage_done,
    verify_arm_identity,
    verify_arm_pair,
    write_artifact,
)
from sif.embedding.identity import EmbedderIdentity
from sif.search.embedder_verdict import decide_from_gates
from sif.search.personal_bench import noise_gate


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


_OPENING_EN = (
    "Padding words are repeated here to move the later sentence beyond the "
    "opening window so the body query is not rejected by the overlap budget. "
) * 2
_OPENING_ZH = "填充内容用于把后面的句子推到开头窗口之外这样正文查询不会被重叠预算拒绝。" * 6


def _write_documents_db(db_path: Path, *, english: int, chinese: int) -> None:
    """Write (or rewrite) a minimal documents table with deterministic bodies."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, path TEXT, title TEXT, "
            "checksum TEXT, file_size INTEGER, content TEXT)"
        )
        conn.execute("DELETE FROM documents")
        rows: list[tuple[str, str, str, str, int, str]] = [
            (
                f"en-{index}",
                f"/notes/en-{index}.md",
                f"English note number {index}",
                f"sum-en-{index}",
                10,
                _OPENING_EN + f"Gardening weather patterns describe evening observations {index}.",
            )
            for index in range(english)
        ]
        rows.extend(
            (
                f"zh-{index}",
                f"/notes/zh-{index}.md",
                f"中文笔记第{index}号",
                f"sum-zh-{index}",
                10,
                _OPENING_ZH + f"{index} 号园艺天气模式描述无关观。",
            )
            for index in range(chinese)
        )
        conn.executemany("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?)", rows)
        conn.commit()
    finally:
        conn.close()


def _install_noop_run(
    monkeypatch: pytest.MonkeyPatch,
    stages: list[str],
) -> None:
    """Replace the subprocess runner with one that records stage names."""

    def _run(
        command: ArmCommand,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        stages.append(command.stage)
        return subprocess.CompletedProcess(command.argv, 0, "", "")

    monkeypatch.setattr(harrier_eval, "run_command", _run)


def _adopt_decision() -> Any:
    """A real adopt-harrier verdict over Phase 18 gates."""
    return decide_from_gates(
        noise_gate([0.5] * 101, [0.52] * 101),
        {
            "en": noise_gate([0.5] * 12, [0.52] * 12),
            "zh": noise_gate([0.5] * 12, [0.51] * 12),
        },
    )


def _gate_payload(baseline: float, current: float, n: int) -> dict[str, Any]:
    """One real GateResult serialized leaf."""
    return noise_gate([baseline] * n, [current] * n).to_dict()


def _write_saved_run(path: Path, query: str = "alpha") -> str:
    """Write one minimal saved run and return its query-set fingerprint."""
    payload = {
        "queries": [{"leg": "title", "language": "en", "split": "heldout", "query": query}]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))
    return query_set_fingerprint(payload)


def _artifact_corpus() -> dict[str, Any]:
    """Aggregate corpus input, including data build_artifact must not copy."""
    return {
        "fingerprint": "0123456789abcdef",
        "documents": 50,
        "sampled": 50,
        "adequacy": {"adequate": True, "sampled": 50, "counts": {"en": 27, "zh": 25}},
        "scope_labels": ["/Users/someone/notes/corpus-a", "corpus-b"],
        "records": [{"query": "secret query text"}],
    }


class TestPreflight:
    """EN+ZH adequacy gates the embed budget and is recorded honestly."""

    def _preflight(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        *,
        corpus_name: str,
        english: int,
        chinese: int,
    ) -> tuple[int, dict[str, Any], Path]:
        scratch = tmp_path / "scratch"
        scratch.mkdir(exist_ok=True)
        _write_documents_db(scratch / "qwen3.db", english=english, chinese=chinese)
        corpus = tmp_path / corpus_name
        monkeypatch.setattr(harrier_eval, "_cache_db_path", lambda: tmp_path / "cache.db")
        monkeypatch.setattr(harrier_eval, "ARTIFACT_PATH", tmp_path / "artifact.json")
        code = main(
            [
                "--preflight-only",
                "--corpus",
                str(corpus),
                "--scratch-root",
                str(scratch),
            ]
        )
        captured = capsys.readouterr()
        return code, json.loads(captured.out), scratch

    def test_bilingual_corpus_is_adequate(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _install_noop_run(monkeypatch, [])

        code, payload, scratch = self._preflight(
            tmp_path,
            monkeypatch,
            capsys,
            corpus_name="corpus",
            english=25,
            chinese=25,
        )

        assert code == 0
        assert payload["adequate"] is True
        assert payload["counts"]["en"] >= 10
        assert payload["counts"]["zh"] >= 10
        state = json.loads((scratch / "run-state.json").read_text())
        assert state["stages"]["adequacy"]["status"] == "complete"
        assert state["stages"]["arm_a_index"]["status"] == "complete"

    def test_english_only_corpus_is_inadequate_and_incomplete(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        stages: list[str] = []
        _install_noop_run(monkeypatch, stages)

        code, payload, scratch = self._preflight(
            tmp_path,
            monkeypatch,
            capsys,
            corpus_name="corpus",
            english=50,
            chinese=0,
        )

        assert code == 3
        assert payload["adequate"] is False
        assert payload["counts"]["zh"] == 0
        state = json.loads((scratch / "run-state.json").read_text())
        assert state["adequacy"]["adequate"] is False
        assert state["adequacy"]["counts"]["zh"] == 0
        assert "adequacy" not in state["stages"]
        assert state["stages"]["arm_a_index"]["status"] == "complete"
        assert "index_embed" not in stages

    def test_resumed_full_run_rechecks_adequacy_without_embedding(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        stages: list[str] = []
        _install_noop_run(monkeypatch, stages)
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        _write_documents_db(scratch / "qwen3.db", english=50, chinese=0)
        corpus = tmp_path / "corpus"
        calls: list[Path] = []
        real_preflight = harrier_eval.preflight_adequacy

        def _counted(db_path: Path, **kwargs: Any) -> dict[str, Any]:
            calls.append(Path(db_path))
            return real_preflight(db_path, **kwargs)

        monkeypatch.setattr(harrier_eval, "_cache_db_path", lambda: tmp_path / "cache.db")
        monkeypatch.setattr(harrier_eval, "ARTIFACT_PATH", tmp_path / "artifact.json")
        monkeypatch.setattr(harrier_eval, "preflight_adequacy", _counted)
        argv = ["--corpus", str(corpus), "--scratch-root", str(scratch)]

        assert main(argv) == 3
        assert main(argv) == 3
        capsys.readouterr()

        assert len(calls) == 2
        assert "index_embed" not in stages
        artifact = json.loads((tmp_path / "artifact.json").read_text())
        assert artifact["decision"] == "insufficient-evidence"
        assert artifact["query_set_fingerprint"] is None
        assert artifact["arms"] == {}
        assert artifact["gates"] == {}
        assert artifact["corpus"]["adequacy"]["counts"]["zh"] == 0
        state = json.loads((scratch / "run-state.json").read_text())
        assert "verdict" not in state["stages"]
        assert "artifact" not in state["stages"]

    def test_inadequate_then_adequate_rerun_reaches_the_full_flow(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        stages: list[str] = []
        _install_noop_run(monkeypatch, stages)
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        _write_documents_db(scratch / "qwen3.db", english=50, chinese=0)
        monkeypatch.setattr(harrier_eval, "_cache_db_path", lambda: tmp_path / "cache.db")
        monkeypatch.setattr(harrier_eval, "ARTIFACT_PATH", tmp_path / "artifact.json")
        argv = ["--corpus", str(tmp_path / "corpus"), "--scratch-root", str(scratch)]

        assert main(argv) == 3
        first = json.loads((tmp_path / "artifact.json").read_text())
        assert first["decision"] == "insufficient-evidence"
        capsys.readouterr()

        # Re-index the arm-A DB externally so the preflight becomes adequate.
        _write_documents_db(scratch / "qwen3.db", english=25, chinese=25)
        verdicts: list[str] = []
        monkeypatch.setattr(harrier_eval, "_run_embed_stage", lambda *a, **k: {})
        monkeypatch.setattr(harrier_eval, "_run_arm_b_index_stage", lambda *a, **k: None)
        monkeypatch.setattr(harrier_eval, "_run_pair_identity_stage", lambda *a, **k: None)
        monkeypatch.setattr(
            harrier_eval,
            "_run_probe_stage",
            lambda *a, **k: {"identity": {}, "device": "cpu"},
        )
        monkeypatch.setattr(harrier_eval, "_run_eval_stage", lambda *a, **k: {})

        def _verdict(*_args: object, **kwargs: object) -> dict[str, Any]:
            corpus_payload = kwargs["corpus_payload"]
            assert isinstance(corpus_payload, dict)
            verdicts.append(str(corpus_payload["fingerprint"]))
            return {"decision": "keep-qwen3"}

        monkeypatch.setattr(harrier_eval, "_run_verdict_stage", _verdict)

        assert main(argv) == 0
        assert verdicts
        capsys.readouterr()

    def test_changed_corpus_scope_rebuilds_the_baseline_arm(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        stages: list[str] = []
        _install_noop_run(monkeypatch, stages)
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        _write_documents_db(scratch / "qwen3.db", english=25, chinese=25)
        monkeypatch.setattr(harrier_eval, "_cache_db_path", lambda: tmp_path / "cache.db")
        monkeypatch.setattr(harrier_eval, "ARTIFACT_PATH", tmp_path / "artifact.json")

        first = main(
            [
                "--preflight-only",
                "--corpus",
                str(tmp_path / "first"),
                "--scratch-root",
                str(scratch),
            ]
        )
        second = main(
            [
                "--preflight-only",
                "--corpus",
                str(tmp_path / "second"),
                "--scratch-root",
                str(scratch),
            ]
        )
        capsys.readouterr()

        assert first == 0
        assert second == 0
        assert stages.count("index_update") == 2
        assert stages.count("collection_add_1") == 2


class TestVerdictStage:
    """A recorded artifact is reused only while its inputs still agree."""

    def _state(self, *, qfp: str, cfp: str, artifact_path: Path) -> dict[str, Any]:
        return {
            "version": 1,
            "scope_key": "scope",
            "scope": {},
            "stages": {
                "verdict": {"status": "complete", "detail": {}},
                "artifact": {
                    "status": "complete",
                    "detail": {
                        "path": str(artifact_path),
                        "query_set_fingerprint": qfp,
                        "corpus_fingerprint": cfp,
                    },
                },
            },
        }

    def test_returns_the_recorded_artifact_when_inputs_agree(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        artifact_path = tmp_path / "artifact.json"
        monkeypatch.setattr(harrier_eval, "ARTIFACT_PATH", artifact_path)
        saved_a = tmp_path / "qwen3.json"
        saved_b = tmp_path / "harrier.json"
        qfp = _write_saved_run(saved_a)
        _write_saved_run(saved_b)
        recorded = {
            "decision": "keep-qwen3",
            "query_set_fingerprint": qfp,
            "corpus": {"fingerprint": "abc"},
        }
        artifact_path.write_text(json.dumps(recorded))
        state = self._state(qfp=qfp, cfp="abc", artifact_path=artifact_path)

        result = harrier_eval._run_verdict_stage(
            state,
            tmp_path / "run-state.json",
            comparison_path=tmp_path / "missing-comparison.json",
            qwen3_saved_run=saved_a,
            harrier_saved_run=saved_b,
            arms_payload={},
            corpus_payload={"fingerprint": "abc"},
            device="cpu",
        )

        assert result == recorded

    def test_missing_inputs_are_not_shadowed_by_a_stale_marker(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        artifact_path = tmp_path / "artifact.json"
        monkeypatch.setattr(harrier_eval, "ARTIFACT_PATH", artifact_path)
        artifact_path.write_text(
            json.dumps(
                {
                    "decision": "insufficient-evidence",
                    "query_set_fingerprint": None,
                    "corpus": {"fingerprint": "old"},
                }
            )
        )
        state = self._state(qfp="", cfp="old", artifact_path=artifact_path)

        with pytest.raises(OSError):
            harrier_eval._run_verdict_stage(
                state,
                tmp_path / "run-state.json",
                comparison_path=tmp_path / "missing-comparison.json",
                qwen3_saved_run=tmp_path / "missing-a.json",
                harrier_saved_run=tmp_path / "missing-b.json",
                arms_payload={},
                corpus_payload={"fingerprint": "new"},
                device="cpu",
            )

        assert "artifact" not in state["stages"]
        assert "verdict" not in state["stages"]

    def test_changed_query_set_is_not_shadowed_by_a_stale_marker(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        artifact_path = tmp_path / "artifact.json"
        monkeypatch.setattr(harrier_eval, "ARTIFACT_PATH", artifact_path)
        saved_a = tmp_path / "qwen3.json"
        saved_b = tmp_path / "harrier.json"
        _write_saved_run(saved_a, query="beta")
        _write_saved_run(saved_b, query="beta")
        recorded = {
            "decision": "keep-qwen3",
            "query_set_fingerprint": "oldfingerprint",
            "corpus": {"fingerprint": "abc"},
        }
        artifact_path.write_text(json.dumps(recorded))
        state = self._state(
            qfp="oldfingerprint",
            cfp="abc",
            artifact_path=artifact_path,
        )

        with pytest.raises(OSError):
            harrier_eval._run_verdict_stage(
                state,
                tmp_path / "run-state.json",
                comparison_path=tmp_path / "missing-comparison.json",
                qwen3_saved_run=saved_a,
                harrier_saved_run=saved_b,
                arms_payload={},
                corpus_payload={"fingerprint": "abc"},
                device="cpu",
            )

        assert "artifact" not in state["stages"]
        assert "verdict" not in state["stages"]


class TestDiskHeadroom:
    """The env preflight refuses a run that could exhaust the disk."""

    def test_refuses_below_the_floor(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            harrier_eval.shutil,
            "disk_usage",
            lambda _path: SimpleNamespace(free=MIN_FREE_DISK_BYTES - 1),
        )

        with pytest.raises(RuntimeError, match="insufficient disk space"):
            assert_disk_headroom(tmp_path)

    def test_accepts_at_the_floor(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            harrier_eval.shutil,
            "disk_usage",
            lambda _path: SimpleNamespace(free=MIN_FREE_DISK_BYTES),
        )

        assert_disk_headroom(tmp_path)


class TestArtifact:
    """The committed envelope carries aggregate evidence only."""

    def test_key_order_and_verbatim_gate_leaves(self) -> None:
        overall = _gate_payload(0.5, 0.52, 101)
        heldout = _gate_payload(0.5, 0.52, 52)
        gates = {
            "overall": overall,
            "splits": {"tuning": _gate_payload(0.5, 0.5, 48), "heldout": heldout},
            "language_splits": {"en": {"heldout": _gate_payload(0.5, 0.52, 27)}},
            "legs": {"title": _gate_payload(0.5, 0.52, 50)},
            "leg_splits": {"title": {"heldout": _gate_payload(0.5, 0.52, 26)}},
            "leg_language_splits": {"title": {"en": {"heldout": _gate_payload(0.5, 0.52, 13)}}},
            "groups": [],
            "suppressed": ["body/zh/short"],
            "top_k": 10,
        }

        artifact = build_artifact(
            decision=_adopt_decision(),
            arms={
                "qwen3": {
                    "identity": {"model_name": QWEN3_MODEL_NAME},
                    "costs": {"chunks": 100},
                }
            },
            corpus=_artifact_corpus(),
            query_set_fingerprint="deadbeefdeadbeef",
            gates=gates,
            environment={"python": "3.13.9", "device": "mps"},
            replay_available=False,
            notes=["aggregate only"],
        )

        assert list(artifact) == [
            "version",
            "decision",
            "rule",
            "arms",
            "corpus",
            "query_set_fingerprint",
            "gates",
            "replay",
            "environment",
            "min_heldout_for_epsilon_win",
            "notes",
        ]
        assert artifact["decision"] == "adopt-harrier"
        assert artifact["gates"]["overall"] == overall
        assert artifact["gates"]["splits"]["heldout"]["n"] == 52
        assert artifact["min_heldout_for_epsilon_win"] == 101
        assert artifact["corpus"]["adequacy"]["counts"] == {"en": 27, "zh": 25}
        assert artifact["corpus"]["scope_labels"] == ["corpus-a", "corpus-b"]
        serialized = json.dumps(artifact, sort_keys=True)
        assert "/Users/someone" not in serialized
        assert "secret query text" not in serialized

    def test_write_is_sorted_atomic_and_newline_terminated(self, tmp_path: Path) -> None:
        artifact = build_artifact(
            decision=_adopt_decision(),
            arms={},
            corpus=_artifact_corpus(),
            query_set_fingerprint=None,
            gates={},
            environment={},
            replay_available=False,
            notes=[],
        )
        path = tmp_path / "bench" / "harrier-verdict.json"

        written = write_artifact(path, artifact)

        text = path.read_text()
        assert written == path
        assert text == json.dumps(artifact, indent=2, sort_keys=True) + "\n"
        assert json.loads(text) == artifact

    def test_insufficient_evidence_variant_carries_adequacy_only(self) -> None:
        artifact = build_artifact(
            decision=decide_from_gates(None, {}),
            arms={},
            corpus={
                "fingerprint": "abc123",
                "documents": 50,
                "sampled": 50,
                "adequacy": {
                    "adequate": False,
                    "sampled": 50,
                    "counts": {"en": 58, "zh": 0},
                },
                "scope_labels": ["corpus"],
            },
            query_set_fingerprint=None,
            gates={},
            environment={"python": "3.13.9"},
            replay_available=False,
            notes=["short"],
        )

        assert artifact["decision"] == "insufficient-evidence"
        assert artifact["query_set_fingerprint"] is None
        assert artifact["arms"] == {}
        assert artifact["gates"] == {}
        assert artifact["corpus"]["adequacy"] == {
            "adequate": False,
            "sampled": 50,
            "counts": {"en": 58, "zh": 0},
        }
        assert "missing overall held-out gate" in artifact["rule"]["reasons"]


class TestCleanupGuard:
    """Cleanup can never delete outside the declared scratch root."""

    def test_refuses_the_filesystem_root(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="filesystem root"):
            assert_within_scratch(Path("/"), tmp_path)

    def test_refuses_the_home_directory(self) -> None:
        home = Path.home()

        with pytest.raises(ValueError, match="scratch root"):
            assert_within_scratch(home, home)

    def test_refuses_a_nested_target_under_a_home_root(self) -> None:
        home = Path.home()

        with pytest.raises(ValueError, match="scratch root"):
            assert_within_scratch(home / "qwen3.db", home)
        with pytest.raises(ValueError, match="scratch root"):
            assert_within_scratch(home / "saved-runs" / "qwen3.json", home)

    def test_refuses_a_nested_target_under_the_filesystem_root(self) -> None:
        with pytest.raises(ValueError, match="scratch root"):
            assert_within_scratch(Path("/qwen3.db"), Path("/"))

    def test_refuses_a_symlinked_home_root(self, tmp_path: Path) -> None:
        link = tmp_path / "home-link"
        try:
            link.symlink_to(Path.home(), target_is_directory=True)
        except (NotImplementedError, OSError):
            pytest.skip("symlinks are unavailable on this platform")

        with pytest.raises(ValueError, match="scratch root"):
            assert_within_scratch(link / "qwen3.db", link)

    def test_cleanup_refuses_a_home_scratch_root(self) -> None:
        home = Path.home()

        with pytest.raises(ValueError, match="scratch root"):
            cleanup_arms(home, keep_arms=False)

    def test_stage_machine_refuses_a_home_scratch_root(self, tmp_path: Path) -> None:
        arms = build_arms(Path.home())

        with pytest.raises(ValueError, match="scratch root"):
            harrier_eval.run_stage_machine(
                arms,
                [tmp_path],
                Path.home(),
                corpus_label="personal",
                keep_arms=False,
                output_json=True,
            )

    def test_refuses_a_sibling_path(self, tmp_path: Path) -> None:
        scratch = tmp_path / "scratch"
        sibling = tmp_path / "elsewhere"
        scratch.mkdir()
        sibling.mkdir()

        with pytest.raises(ValueError, match="outside the scratch root"):
            assert_within_scratch(sibling, scratch)

    def test_accepts_a_nested_run_db(self, tmp_path: Path) -> None:
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        target = scratch / "qwen3.db"

        assert assert_within_scratch(target, scratch) == target.resolve()

    def test_keep_arms_preserves_every_file(self, tmp_path: Path) -> None:
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        db = scratch / "qwen3.db"
        db.write_text("x")

        assert cleanup_arms(scratch, keep_arms=True) == []
        assert db.exists()

    def test_removes_only_the_runs_own_files(self, tmp_path: Path) -> None:
        scratch = tmp_path / "scratch"
        saved_runs = scratch / "saved-runs"
        saved_runs.mkdir(parents=True)
        owned = [
            scratch / "qwen3.db",
            scratch / "qwen3.db-wal",
            scratch / "qwen3.db-shm",
            scratch / "qwen3.db.lock",
            scratch / "harrier.db",
            saved_runs / "qwen3.json",
        ]
        for path in owned:
            path.write_text("x")
        foreign = scratch / "notes.txt"
        foreign.write_text("keep")

        removed = cleanup_arms(scratch, keep_arms=False)

        assert set(removed) == {
            "qwen3.db",
            "qwen3.db-wal",
            "qwen3.db-shm",
            "qwen3.db.lock",
            "harrier.db",
            "qwen3.json",
        }
        assert all(not path.exists() for path in owned)
        assert foreign.exists()


class TestQueryFingerprint:
    """The query-set fingerprint ignores per-arm target ids."""

    def test_target_ids_are_excluded(self) -> None:
        base = {
            "queries": [
                {
                    "leg": "title",
                    "language": "en",
                    "split": "heldout",
                    "query": "alpha",
                    "target_doc_id": "arm-a-uuid",
                }
            ]
        }
        other = {
            "queries": [
                {
                    "leg": "title",
                    "language": "en",
                    "split": "heldout",
                    "query": "alpha",
                    "target_doc_id": "arm-b-uuid",
                }
            ]
        }

        assert query_set_fingerprint(base) == query_set_fingerprint(other)

    def test_different_query_sets_hash_differently(self) -> None:
        alpha = {
            "queries": [{"leg": "title", "language": "en", "split": "tuning", "query": "alpha"}]
        }
        beta = {"queries": [{"leg": "title", "language": "en", "split": "tuning", "query": "beta"}]}

        assert query_set_fingerprint(alpha) != query_set_fingerprint(beta)

    def test_malformed_saved_run_is_refused(self) -> None:
        with pytest.raises(ValueError, match="queries"):
            query_set_fingerprint({})
