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
