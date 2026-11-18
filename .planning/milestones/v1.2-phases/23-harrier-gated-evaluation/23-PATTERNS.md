# Phase 23: Harrier Gated Evaluation - Pattern Map

**Mapped:** 2026-11-16
**Files analyzed:** 18 (6 new, 7 modified, 4 conditional-on-pass, 1 planning doc)
**Analogs found:** 18 / 18

## Phase-Specific Invariants (from CONTEXT/RESEARCH)

- **No new runtime dependency and no new public CLI command** (D-11). The only CLI surface change is the additive `--require-language` flag on the existing `eval` group.
- **Two isolated DBs, one per arm** (D-01). Never one vec0 table for two models — both candidates are 1024-dim, last-token pooled.
- **Identity is the guard, not width** (D-01/Phase 21): the runbook must assert `read_identity(conn).source == "verified"` and `check_identity(conn, current, mode="search").status == "ok"` before each eval.
- **Reuse Phase 18 instrumentation verbatim** (D-06): `noise_gate`/`paired_bootstrap`/`GateResult.winner`/`SUPPRESS_BELOW`/`EPSILON`; do not reimplement bootstrap or gate arithmetic.
- **Every `sif` subprocess must pass `-q`** or ModelScope pollutes stdout even on a cache hit, breaking JSON parsing (Research Pitfall 7).
- **Generated docs are never hand-edited**: `make docs-generate` runs `scripts/generate_cli_ref.py` + `scripts/generate_config_ref.py`; CI gates the diff (`Makefile:73-76`).
- **The committed artifact is phase-local**: `.planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json` (Phase 19 precedent; no repo-root `bench/` exists).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sif/search/embedder_verdict.py` (new) | service (domain policy) | transform | `src/sif/search/benchmark.py` | role-match |
| `src/sif/search/personal_bench.py` (modify) | service (domain) | transform | itself: `leg_noise_gates`, `ensure_heldout`, `ComparisonReport` | exact |
| `src/sif/cli/commands/eval.py` (modify) | controller | request-response | itself: `eval_group`, `_run_fresh`, `_run_compare` | exact |
| `scripts/harrier_eval.py` (new) | utility (orchestrator script) | batch / subprocess | `scripts/windows_smoke.py` | exact (structure), partial (stage machine) |
| `tests/unit/scripts/__init__.py` (new) | test | n/a | `tests/unit/cli/__init__.py` | exact |
| `tests/unit/scripts/test_harrier_eval.py` (new) | test | n/a | `tests/test_windows_smoke_script.py`; `tests/unit/mcp/test_registry_script.py` | exact |
| `tests/unit/search/test_embedder_verdict.py` (new) | test | n/a | `tests/unit/search/test_bench_snapshot.py::TestWarrantsDefaultChange` | exact |
| `tests/unit/search/test_personal_bench.py` (modify) | test | n/a | itself: `TestNoiseGate`, `TestEnsureHeldout` | exact |
| `tests/unit/cli/test_eval.py` (modify) | test | n/a | itself: `TestCompareCli`, `test_compare_warns_on_model_identity_mismatch` | exact |
| `tests/support/eval.py` (modify) | test support | file-I/O | itself: `build_personal_db` | exact |
| `docs/benchmarking.md` (modify) | config (hand-maintained evidence doc) | static | itself: "Held-Out Evidence..." + D-12 section | exact |
| `docs/cli-reference.md` (regenerate) | config (generated doc) | static | `scripts/generate_cli_ref.py` via `make docs-generate` | exact |
| `.planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json` (new) | config (committed evidence artifact) | static | `.planning/phases/19-search-correctness/bench/d12-verdict.json` | exact |
| `src/sif/config/settings.py` (only on pass) | config | static | itself: model settings block | exact |
| `src/sif/models/embedding.py` (only on pass) | config | static | itself: `EmbeddingConfig` | exact |
| `tests/unit/config/test_settings.py` (only on pass) | test | n/a | itself: default-pinning tests | exact |
| `tests/unit/search/test_bench_snapshot.py` (only on pass) | test | n/a | itself: `TestDefaultEmbedderBaseline` (D-19) | exact |
| `.planning/phases/23-harrier-gated-evaluation/23-VALIDATION.md` (new) | config (planning doc) | static | `.planning/phases/18-.../18-VALIDATION.md` | exact |

---

## Pattern Assignments

### `src/sif/search/embedder_verdict.py` (service, transform)

**Analog:** `src/sif/search/benchmark.py` (pure policy module) + the gate semantics it consumes from `personal_bench.py`.

**Module skeleton / imports** (`src/sif/search/benchmark.py:1-16`) — pure module, no Click/Rich, module-level logger only if it logs:
```python
"""Benchmark evaluation for search quality."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sif.core.models import SearchResult
from sif.utils.logging import get_logger


logger = get_logger(__name__)
```

**Pure policy-rule shape** (`src/sif/search/benchmark.py:33`, `414-427`) — the precedent for a small, dependency-free rule returning a bool from gate values:
```python
EPSILON = 0.01

def warrants_default_change(
    baseline_ndcg: float,
    candidate_ndcg: float,
    delta: float = EPSILON,
) -> bool:
    """Held-out evidence rule (EVAL-04): does a candidate justify new defaults?
    ...
    """
    return round(candidate_ndcg - baseline_ndcg, 6) >= delta
```

**Gate inputs to consume** (`src/sif/search/personal_bench.py:387-399`) — do not re-derive; read these fields:
```python
n: int
baseline_mean: float
current_mean: float
mean_delta: float
ci_low: float
ci_high: float
helped: int
hurt: int
unchanged: int
noise_floor: float
winner: bool
regression: bool
sufficient: bool
```

**What `.winner` already means** (`src/sif/search/personal_bench.py:1824-1846`) — the verdict module must not reimplement this arithmetic:
```python
bootstrap = paired_bootstrap(deltas)
mean_delta = bootstrap.mean
noise_floor = 1.0 / len(deltas)
excludes_zero = bootstrap.ci_low > 0 or bootstrap.ci_high < 0
improvement = round(mean_delta, 6) >= EPSILON
regression = round(mean_delta, 6) <= -EPSILON
sufficient = len(deltas) >= SUPPRESS_BELOW
exceeds_floor = abs(mean_delta) > noise_floor
...
winner=sufficient and excludes_zero and improvement and exceeds_floor,
```

**Prescriptive decision shape (RESEARCH.md Pattern 2; no existing three-way policy analog in the codebase)** — implement this as the new module's public API:
```python
from sif.search.personal_bench import EPSILON, SUPPRESS_BELOW, GateResult

DECISION_ADOPT = "adopt-harrier"
DECISION_KEEP = "keep-qwen3"
DECISION_INSUFFICIENT = "insufficient-evidence"

def decide(
    comparison: "ComparisonReport",
    *,
    required_languages: tuple[str, ...] = ("en", "zh"),
    min_language_n: int = SUPPRESS_BELOW,
) -> "VerdictDecision":
    heldout = comparison.splits["heldout"]
    language_heldout = {
        language: comparison.language_splits.get(language, {}).get("heldout")
        for language in required_languages
    }
    adequate = all(
        gate is not None and gate.n >= min_language_n
        for gate in language_heldout.values()
    )
    floor_ok = all(
        gate is not None and round(gate.mean_delta, 6) >= -EPSILON
        for gate in language_heldout.values()
    )
    if not adequate:
        decision = DECISION_INSUFFICIENT
    else:
        decision = DECISION_ADOPT if (heldout.winner and floor_ok) else DECISION_KEEP
    # Record literal booleans (ci_excludes_zero, mean_delta_at_least_epsilon,
    # above_noise_floor) so a rejection is auditable even though `.winner`
    # bundles four conditions.
    return VerdictDecision(decision=decision, ...)
```

Return a frozen dataclass with the three-way decision plus the literal rule booleans, so the runbook writes a machine-readable reason block. Use `dataclass(frozen=True)` and a `to_dict()` with a fixed key order, matching `GateResult.to_dict` (`personal_bench.py:401-417`).

---

### `src/sif/search/personal_bench.py` (service, transform) — MODIFY

**Analog:** this file. Extend by copying the existing grouping/gate and widening patterns; do not invent new metric math.

**Imports** (`personal_bench.py:22-47`) — note `field` is **not** currently imported; adding defaulted dict fields requires changing line 32:
```python
from dataclasses import dataclass, replace
```
to
```python
from dataclasses import dataclass, field, replace
```
`EPSILON` already comes from `sif.search.benchmark` (line 40-47); `LANGUAGES` is line 53 and `SUPPRESS_BELOW` line 64.

**`ComparisonReport` fields + `to_dict`** (`personal_bench.py:470-535`) — add defaulted fields at the end so the existing constructor and tests stay valid:
```python
    replay: ReplayStability
    retrieval: dict[str, str]
    top_k: int
    warrants_default_change: bool
    model_mismatch: bool
    # NEW (added after all required fields):
    language_splits: dict[str, dict[str, GateResult]] = field(default_factory=dict)
    leg_language_splits: dict[str, dict[str, dict[str, GateResult]]] = field(
        default_factory=dict
    )
```
Extend `to_dict()` (`497-535`) beside the existing `"leg_splits"` block with the same nested-comprehension style:
```python
"leg_splits": {
    leg: {split: gate.to_dict() for split, gate in splits.items()}
    for leg, splits in self.leg_splits.items()
},
```
New keys should be emitted in a stable order after `leg_splits`, each gate through `gate.to_dict()`.

**Per-axis gate helper to copy** (`personal_bench.py:1895-1928`, `leg_noise_gates`) — `language_noise_gates` is the same function with `record.leg` replaced by `record.language`; `leg_language_noise_gates` nests both axes:
```python
def leg_noise_gates(
    saved_queries: Sequence[SavedQueryRecord],
    baseline_values: Sequence[float],
    current_values: Sequence[float],
) -> tuple[dict[str, GateResult], dict[str, dict[str, GateResult]]]:
    """Per-leg and per-leg x split paired gates for the D-12 rule.
    ...
    """
    if not (len(saved_queries) == len(baseline_values) == len(current_values)):
        raise ValueError("saved queries and both metric series must have equal lengths")
    indices: dict[str, dict[str, list[int]]] = {}
    for index, record in enumerate(saved_queries):
        per_split = indices.setdefault(record.leg, {"tuning": [], "heldout": []})
        per_split.setdefault(record.split, []).append(index)
    legs: dict[str, GateResult] = {}
    leg_splits: dict[str, dict[str, GateResult]] = {}
    for leg, per_split in indices.items():
        all_indices = [index for split_indices in per_split.values() for index in split_indices]
        legs[leg] = noise_gate(
            [baseline_values[index] for index in all_indices],
            [current_values[index] for index in all_indices],
        )
        leg_splits[leg] = {
            split: noise_gate(
                [baseline_values[index] for index in per_split.get(split, [])],
                [current_values[index] for index in per_split.get(split, [])],
            )
            for split in ("tuning", "heldout")
        }
    return legs, leg_splits
```

**Declared order + suppression** (`personal_bench.py:1849-1892`, `group_noise_gates`) — new language gates must follow declared `LANGUAGES` order and never fabricate a zero row; an absent language should yield no key rather than a `0.0` gate. The verdict reads `language_splits.get(language, {}).get("heldout")` and treats `None` as inadequate.

**Language-aware widening** (`personal_bench.py:1027-1082`, `ensure_heldout`) — add an opt-in keyword-only parameter with a `()` default so every existing call/test is byte-identical:
```python
def ensure_heldout(
    metadata: Sequence[DocumentRecord],
    conn: sqlite3.Connection,
    *,
    initial: int = INITIAL_SAMPLE_DOCUMENTS,
    cap: int = MAX_SAMPLE_DOCUMENTS,
    required_languages: Sequence[str] = (),
) -> tuple[list[DocumentRecord], SynthesisResult]:
```
Inside the existing loop, add the language term:
```python
while (
    len(accepted) < MIN_QUERIES
    or heldout < HELDOUT_MIN
    or _language_floor_unmet(accepted, required_languages)
) and limit < hard_cap:
```
At the cap, extend the counted `ValueError` (`1074-1081`) with per-language held-out counts (`en=31, zh=6`) so the runbook can record exact evidence. Add a public helper for tests/artifact:
```python
def heldout_language_counts(queries: Sequence[SynthesizedQuery]) -> dict[str, int]:
    """Held-out query counts per language, in LANGUAGES order (absent = 0)."""
```

**Wiring in `compare_saved_run`** (`personal_bench.py:2117-2133`) — add the new grouping calls right after `leg_noise_gates`, using the same `baseline_ndcg`/`current_ndcg` series (already in hand; no re-derivation of baseline grades):
```python
legs, leg_splits = leg_noise_gates(saved.queries, baseline_ndcg, current_ndcg)
groups, suppressed = group_noise_gates(
    saved.queries,
    baseline_ndcg,
    current_ndcg,
)
```
and pass the results in the `ComparisonReport(...)` constructor (`2169-2194`). Keep `warrants_default_change=splits["heldout"].winner` unchanged; the two-sided gate lives in `embedder_verdict.py`, not here.

**Fingerprint style** (`personal_bench.py:1106-1115`, `corpus_fingerprint`) — the script's query-set fingerprint should mirror this 16-hex-char truncated sha256 over sorted/ordered lines:
```python
lines = sorted(f"{doc.path}\0{doc.checksum}\0{doc.file_size}" for doc in metadata)
return hashlib.sha256("\n".join(lines).encode()).hexdigest()[:16]
```

---

### `src/sif/cli/commands/eval.py` (controller, request-response) — MODIFY

**Analog:** this file. The new flag is additive and pass-through only.

**Controller imports** (`eval.py:43-66`) — add `LANGUAGES` to the existing `sif.search.personal_bench` import block; no new module imports beyond the verdict module if rendering is added.

**Option declaration style** (`eval.py:954-980`) — follow the existing `eval_group` decorator stack; `--collection` shows the `multiple=True` idiom, `-n` shows `click.Choice`-style validation:
```python
@click.option(
    "-n",
    "--limit",
    default=10,
    type=click.IntRange(1, MAX_TOP_K),
    help=f"Number of results per query (1-{MAX_TOP_K})",
)
@click.option("-c", "--collection", multiple=True, help="Collection to evaluate")
@click.option("--all", "search_all", is_flag=True, help="Evaluate all collections")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
```
New flag (D-07):
```python
@click.option(
    "--require-language",
    "require_language",
    type=click.Choice(LANGUAGES),
    multiple=True,
    default=(),
    help="Widen sampling until each required language has >= 10 held-out queries",
)
```
Thread it through `eval_group` -> `run_personal(..., require_language=require_language)` -> `_run_fresh` only. `_run_compare` must **not** synthesize or resample; the saved run defines the query set, so the flag has no effect in compare mode (warn or ignore, matching the existing `-n`/retrieval-mode warnings at `840-851`).

**Error translation boundary** (`eval.py:741-746`) — the domain raises `ValueError`, the CLI converts it; preserve this exact shape:
```python
    try:
        sampled, synthesis = ensure_heldout(metadata, db.connection)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    except (sqlite3.Error, OSError) as e:
        raise click.ClickException(f"Personal eval failed: {e}") from e
```
For the new flag, call `ensure_heldout(metadata, db.connection, required_languages=require_language)`.

**Compare path / strict stdout** (`eval.py:815-881` and module header `70-74`) — warnings go to `console_err`; JSON goes through `click.echo` in `_render_personal`; the comparison is attached as `extra={"comparison": comparison.to_dict()}` (`875-881`). Follow this for any new verdict/rendering keys.

---

### `scripts/harrier_eval.py` (utility, batch/subprocess) — NEW

**Analog:** `scripts/windows_smoke.py` is the closest tracked script (explicit argv, per-run env, subprocess, pure builders, `main() -> int`). `scripts/publish_registry.py` supplies the `argparse` + exit-code shape.

**Script header + project root** (`scripts/windows_smoke.py:1-28`):
```python
#!/usr/bin/env python3
"""Windows degradation smoke: assert the CLI degrades honestly without POSIX semantics.
...
"""
from __future__ import annotations

import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
_VERSION_FILE = PROJECT_ROOT / "src" / "sif" / "_version.py"
_STEP_TIMEOUT_SECONDS = 120
```

**Pure argv builder (the `--dry-run`/test seam)** (`windows_smoke.py:65-84`) — keep all command construction in a pure function returning `list[list[str]]` or `list[ArmCommand]`, so tests assert the exact per-arm argv/env without running anything:
```python
def build_cli_invocations(python: str, docs_dir: Path, expected_version: str) -> list[list[str]]:
    """Build the argv-only invocation table in assertion order.
    ...
    """
    if not expected_version:
        raise ValueError("expected_version must be the repo version literal")
    base = [python, "-m", "sif.cli.main"]
    return [
        [*base, "--version"],
        [*base, "collection", "add", str(docs_dir), "--name", "smoke"],
        ...
    ]
```

**Subprocess runner with pinned env** (`windows_smoke.py:92-102`):
```python
def _run(argv: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run one argv list from the project root; never a shell, always bounded."""
    return subprocess.run(
        argv,
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=_STEP_TIMEOUT_SECONDS,
    )
```
For phase 23, build each arm's env by copying `os.environ` and explicitly **unsetting** `SIF_QUERY_PROMPT_NAME`, `SIF_DOCUMENT_PROMPT_NAME`, `SIF_MODEL_PATH`, `SIF_DB_PATH`, then setting the arm's pinned values (`SIF_MODEL_TYPE`, `SIF_MODEL_NAME`, `SIF_EMBEDDING_DIM=1024`, `SIF_MAX_TOKENS=512`, `SIF_BATCH_SIZE=32`, `SIF_CHUNK_SIZE=512`, `SIF_CHUNK_OVERLAP=128`, `SIF_CACHE_EMBEDDINGS=1`). Every argv must include `-q` and `--index <scratch-db>`.

**PASS/FAIL reporting** (`windows_smoke.py:105-115`) — use the same line-oriented report convention for the dry-run and probe output:
```python
def _report(step: str, argv: list[str], proc: subprocess.CompletedProcess[str], ok: bool) -> bool:
    """Print one PASS/FAIL line, including argv/exit/streams on failure."""
    if ok:
        _emit(f"PASS {step}")
        return True
    _emit(f"FAIL {step}")
    _emit(f"  argv: {argv}")
    _emit(f"  exit: {proc.returncode}")
    _emit(f"  stdout: {proc.stdout!r}")
    _emit(f"  stderr: {proc.stderr!r}")
    return False
```

**argparse + `main() -> int`** (`scripts/publish_registry.py:244-275`):
```python
def build_parser() -> argparse.ArgumentParser:
    """Build the mutually exclusive ``--check``/``--publish`` parser."""
    parser = argparse.ArgumentParser(
        description="Preflight and publish the SIF MCP Registry listing.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="run the read-only preflight")
    ...

def main(argv: list[str] | None = None) -> int:
    """Run the requested mode and return the process exit status."""
    args = build_parser().parse_args(argv)
    ...
    return 0

if __name__ == "__main__":
    sys.exit(main())
```
Use this for `--dry-run`, `--keep-arms`, and the hidden `probe` mode; return 0 only when the stage machine completes, 1 on failure, 2 on a guard refusal (the windows-smoke precedent at `main()` `256-296`).

**JSON artifact writing** (`scripts/generate_bench_fixture.py:459`, `503-540`) — deterministic, sorted, trailing newline:
```python
files["queries.json"] = json.dumps(pack, indent=2, sort_keys=True) + "\n"
```
Write the verdict artifact and run-state JSON the same way. The verdict artifact should embed `GateResult.to_dict()` values verbatim (see `d12-verdict.json` below), not a bespoke metric blob.

**Identity read/assert** (`src/sif/embedding/identity.py:166-171`, `385-392`, `452-494`) — the runbook may import `sif` only for read-only identity helpers, never to run the CLI in-process:
```python
def to_json(self) -> str:
    """Serialize payload plus ``source`` and ``fingerprint``."""
    payload = self._payload()
    payload["source"] = self.source
    payload["fingerprint"] = self.fingerprint()
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def read_identity(conn: sqlite3.Connection) -> EmbedderIdentity | None:
    """Read the stored identity, or ``None`` when absent/corrupt."""
    from sif.database.repositories import IndexMetaRepository  # noqa: PLC0415
    raw = IndexMetaRepository(conn).get(IDENTITY_KEY)
    if raw is None:
        return None
    return EmbedderIdentity.from_json(raw)
```
Required assertions (from RESEARCH Pattern 1):
```python
stored_a = read_identity(conn_a)
stored_b = read_identity(conn_b)
assert stored_a is not None and stored_a.source == "verified"
assert stored_b is not None and stored_b.source == "verified"
assert stored_a.dimension == stored_b.dimension == 1024
assert stored_a.cache_model_id == "modelscope:Qwen/Qwen3-Embedding-0.6B"
assert stored_b.model_name == "microsoft/harrier-oss-v1-0.6b"
assert stored_b.model_type == "sentence_transformers"
assert stored_b.query_prompt == "web_search_query"
assert stored_b.document_prompt is None
assert stored_a.fingerprint() != stored_b.fingerprint()
```
Before each eval: load the arm model in the arm's env (via the `probe` subprocess) and require `check_identity(conn, current, mode="search").status == "ok"`.

**Strict JSON stdout parsing** (research-verified; pattern matches `windows_smoke.py:176-184`) — every `sif eval --json` call is `-q`, `capture_output=True`, `check=False`:
```python
proc = subprocess.run(cmd, env=arm_env, capture_output=True, text=True, check=False)
if proc.returncode != 0:
    raise RuntimeError(f"eval failed for {arm}: {proc.stderr[-4000:]}")
payload = json.loads(proc.stdout)   # strict JSON; run_path is in the payload
```

**Stage machine** — no exact codebase analog (windows_smoke is a fixed linear table). Follow its linear assertion-table structure, but persist stage markers to a run-state JSON so a partial embed can resume. Guard cleanup by resolving the scratch root and refusing `/`, the home directory, or any path outside the declared root; `--keep-arms` disables deletion.

---

### `tests/unit/scripts/__init__.py` (test) — NEW

**Analog:** `tests/unit/cli/__init__.py`
```python
"""CLI unit tests."""
```
Use `"""Script unit tests."""`.

### `tests/unit/scripts/test_harrier_eval.py` (test) — NEW

**Analog:** `tests/test_windows_smoke_script.py` (pure-function script tests, import via `from scripts.<name> import ...`) and `tests/unit/mcp/test_registry_script.py` (module-loading fixture + monkeypatch).

**File docstring + direct import** (`tests/test_windows_smoke_script.py:1-21`):
```python
"""Unit battery for the Windows degradation smoke matchers (ENG-02, plan 17-04).

Pure-function tests only: nothing here invokes sif, touches a database, or
starts a subprocess. The script itself is exercised on hc yoga by
``make windows-smoke``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.windows_smoke import (
    build_cli_invocations,
    looks_like_traceback,
    ...
)
```

**Pure-builder assertions** (`tests/test_windows_smoke_script.py:97-116`):
```python
def test_commands_are_argv_lists_without_model_loading(tmp_path: Path) -> None:
    """Every invocation is an argv list and none names a model-loading subcommand."""
    invocations = build_cli_invocations("python", tmp_path, "1.1.2")

    assert len(invocations) == 8
    for argv in invocations:
        assert isinstance(argv, list)
        assert argv
        assert all(isinstance(item, str) for item in argv)
```
Apply this to the runbook: assert the Harrier arm has no `--query-prompt`/`--document-prompt` overrides and no `SIF_QUERY_PROMPT_NAME` in its env; assert both arms have `-q`, `--index`, the pinned chunk/batch values; assert `--dry-run` invokes no subprocess and prints the planned artifact.

**Script main / refusal test** (`tests/test_windows_smoke_script.py:119-126`):
```python
def test_main_refuses_on_non_windows(monkeypatch, capsys) -> None:
    """CR-01: never fork a daemon or install a service on a POSIX host."""
    import scripts.windows_smoke as smoke

    monkeypatch.setattr(smoke.sys, "platform", "darwin")

    assert smoke.main() == 2
    assert "REFUSED" in capsys.readouterr().out
```
Use the equivalent for the cleanup guard (path outside the scratch root -> exit 2 plus a refusal line).

**Module-loader fallback** (`tests/unit/mcp/test_registry_script.py:32-53`) — use only if a direct `from scripts.harrier_eval import ...` import proves awkward:
```python
def _load_registry_script() -> Any:
    """Load scripts/publish_registry.py as a module (it is not a package)."""
    spec = importlib.util.spec_from_file_location("publish_registry", SCRIPT_PATH)
    assert spec is not None, "could not create an import spec"
    assert spec.loader is not None, "import spec has no loader"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
```

Required test classes per RESEARCH Validation Architecture: `TestDryRun`, `TestIdentityGate`, `TestArtifact`, `TestCleanupGuard`.

---

### `tests/unit/search/test_embedder_verdict.py` (test) — NEW

**Analog:** `tests/unit/search/test_bench_snapshot.py::TestWarrantsDefaultChange` — the existing battery for a pure defaults rule. Copy its boundary-value style: exact-threshold inclusive/exclusive cases, representation-noise case, zero/negative case.

**Excerpt** (`test_bench_snapshot.py:213-232`):
```python
class TestWarrantsDefaultChange:
    def test_inclusive_at_exactly_delta(self) -> None:
        assert warrants_default_change(0.500, 0.510) is True

    def test_rejects_sub_delta_noise(self) -> None:
        assert warrants_default_change(0.500, 0.5099) is False

    def test_rejects_zero_and_negative_deltas(self) -> None:
        assert warrants_default_change(0.500, 0.500) is False
        assert warrants_default_change(0.510, 0.500) is False

    def test_representation_noise_at_nominal_0_01_still_warrants(self) -> None:
        """0.29 - 0.28 is raw 0.009999999999999953; the rounded-delta
        arithmetic (the same rule rank_sweep uses) must count it as 0.01."""
        assert 0.29 - 0.28 < 0.01
        assert warrants_default_change(0.28, 0.29) is True
```

Required cases (MODEL-02): adopt only when `heldout.winner` AND both language floors pass AND adequacy holds; `Δ=0.01` at N=100 is not a winner (1/N floor equality), N=101 with a larger delta can be; CI including 0 is never a winner; a language mean of `-0.02` vetoes; absent language -> `insufficient-evidence`; present language with `n < 10` -> `insufficient-evidence`; every rejection names its reason in the record. Build `GateResult`/`ComparisonReport` stubs directly (frozen dataclasses) — no database or embedder.

---

### `tests/unit/search/test_personal_bench.py` (test) — MODIFY

**Analog:** itself.

**Import block** (`test_personal_bench.py:21-56`) — add `language_noise_gates`, `leg_language_noise_gates`, `heldout_language_counts` to the existing `sif.search.personal_bench` import tuple; keep alphabetical order inside the tuple (ruff isort `combine-as-imports`).

**Gate test style** (`test_personal_bench.py:1563-1624`, `TestNoiseGate`) — table-like, exact boundary values, `pytest.approx`:
```python
class TestNoiseGate:
    def test_exactly_one_hundredth_above_the_noise_floor_declares_a_winner(self) -> None:
        # N=200 -> floor 0.005, so the 0.01 tie rule is strictly above noise.
        gate = noise_gate([0.0] * 200, [0.01] * 200)

        assert gate.n == 200
        assert gate.noise_floor == pytest.approx(0.005)
        assert gate.mean_delta == pytest.approx(0.01)
        assert gate.ci_low > 0
        assert gate.sufficient is True
        assert gate.winner is True
        assert gate.regression is False
```
New cases needed: per-language counts sum to split totals; absent language is not fabricated; declared `LANGUAGES` order; `language_splits`/`leg_language_splits` appear in `to_dict()`; `leg_language_splits` shape.

**Widening test style** (`test_personal_bench.py:457-524`, `TestEnsureHeldout`) — use a recording connection double (`_RecordingConnection`) and assert the exact body-load sizes:
```python
    conn = _RecordingConnection(
        {doc.id: bodies[int(doc.id.split("-")[1])] for doc in titled},
    )

    sampled, synthesis = ensure_heldout(titled, conn)  # type: ignore[arg-type]

    assert len(sampled) == 60
    assert sum(1 for q in synthesis.queries if q.split == "heldout") >= HELDOUT_MIN
    # Bodies were loaded for the initial slice, then only for the 10 new docs.
    assert [len(call[1]) for call in conn.calls] == [50, 10]
```
New cases: `required_languages=()` preserves the current behavior byte-for-byte; a late Chinese block is reached by widening; at the cap the error names per-language held-out counts; an English-only corpus raises `ValueError` naming `zh=0`.

### `tests/unit/cli/test_eval.py` (test) — MODIFY

**Analog:** itself.

**Settings/fixture helpers** (`test_eval.py:40-55`, `_settings`) — reuse; the real `Settings` object is patched at both import sites because `Database.init_schema` reads `get_settings()`:
```python
def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    """Real Settings pinned to the fixture's embedding dimension.
    ...
    """
    fields: dict[str, Any] = {
        "cache_dir": tmp_path,
        "embedding_dim": EMBEDDING_DIM,
        "model_type": "sentence_transformers",
    }
    fields.update(overrides)
    return Settings(_env_file=None, **fields)
```

**Compare CLI test shape** (`test_eval.py:1386-1415`, `TestCompareCli`) — build a real fixture DB, run a fresh saved run, then invoke `--compare` and parse strict JSON:
```python
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path)
        saved_path, _payload = _fresh_saved_run(db_path, settings, pipeline=_ReplaySpyPipeline)
        saved_queries = [record.query for record in load_saved_run(saved_path).queries]

        _SpyPipeline.seen = []
        result = _invoke(
            db_path,
            ["--personal", "--compare", str(saved_path), "--bm25-only", "--json"],
            settings=settings,
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 0, result.output
        assert _SpyPipeline.seen == saved_queries
        payload = json.loads(result.stdout)
```
New tests: `--require-language en --require-language zh` parses, forwards, and appears in help; repeatable flag; invalid language is a usage error; compare mode with a different model identity still emits `language_splits`/`leg_language_splits` and `model_mismatch: true`.

**Cross-model comparison test** (`test_eval.py:1703-1739`, `test_compare_warns_on_model_identity_mismatch`) — the rewrite pattern for the saved run's `model` dict is the template for a harness-arm saved-run fixture: rewrite `model` to a different name/type, invoke with a manager double, assert exit 0 and the warning on stderr.

### `tests/support/eval.py` (test support, file-I/O) — MODIFY (Wave 0)

**Analog:** itself (`build_personal_db`, `tests/support/eval.py:55-90`). It already accepts explicit `titles` and `bodies` overrides:
```python
def build_personal_db(
    db_path: Path,
    *,
    documents: int = 60,
    titles: list[str] | None = None,
    bodies: list[str] | None = None,
    embedder: ConceptEmbedder | None = None,
    embedding_dim: int = EMBEDDING_DIM,
) -> Path:
```
Add a bilingual fixture helper (for example `bilingual_titles_and_bodies(count, zh_count)`) that returns deterministic `titles`/`bodies` with a deliberate Chinese share. Do not add a runtime dependency and do not change `build_personal_db`'s defaults (existing tests depend on them). Reuse `_default_titles`/`_body` (`33-53`) for the English entries and use CJK strings in the same shape for the Chinese ones.

---

### `docs/benchmarking.md` (config, static) — MODIFY

**Analog:** itself. Two sections define the recording style to copy.

**Defaults rule vocabulary** (`docs/benchmarking.md:124-143`) — state the rule, its inclusive boundary, and the verdict vocabulary:
```markdown
## Held-Out Evidence and the Defaults Rule

Tuning-set results alone never change shipped defaults. ...
A `change-warranted` verdict is recorded (snapshot + this document) and names its follow-up route: ...
```

**Rejection-with-numbers style** (`docs/benchmarking.md:227-249`, D-12) — record the decision, every gate's N/deltas, the artifact path, and that the code constant did not move:
```markdown
Every candidate produced 0 helped / 0 hurt and all queries unchanged, with 95% CI `[0.0, 0.0]` on both legs. ...
D-12 therefore **rejected the band with numbers** rather than claiming a win inside noise, and `_TITLE_WEIGHT` stays pinned at 1.0.
`bench/d12-verdict.json` records every candidate's `GateResult` fields plus the accept/reject decision.
```
New Phase 23 section must include: arm identities (including prompt scheme/revision), corpus fingerprint, query-set/saved-run fingerprint, per-leg x per-language gates with N, deltas, CIs, the two-sided decision, the adequacy counts, the noise-floor minimum detectable delta (`min_heldout_for_epsilon_win = 101`), and the artifact path. Cross-reference the artifact at `.planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json`.

### `docs/cli-reference.md` (config, generated) — REGENERATE, never hand-edit

**Analog:** the generator pipeline. `Makefile:73-76`:
```make
docs-generate:
	@echo "Regenerating CLI and configuration reference docs..."
	python scripts/generate_cli_ref.py
	python scripts/generate_config_ref.py
```
Run `make docs-generate` after adding `--require-language`; CI gates `git diff --exit-code docs/cli-reference.md docs/configuration.md`. Do not apply a manual edit even if the diff looks trivial.

---

### `.planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json` (config, committed artifact) — NEW

**Analog:** `.planning/phases/19-search-correctness/bench/d12-verdict.json` (tracked; `git ls-files` verified).

**Shape** (`d12-verdict.json:1-36`) — top-level decision + per-candidate gate dicts copied verbatim from `GateResult.to_dict()`:
```json
{
  "decision": "rejected",
  "pinned_title_weight": 1.0,
  "candidates": [
    {
      "title_weight": 2.0,
      "title_heldout": {
        "n": 23,
        "baseline_mean": 1.0,
        "current_mean": 1.0,
        "mean_delta": 0.0,
        "ci_low": 0.0,
        "ci_high": 0.0,
        "helped": 0,
        "hurt": 0,
        "unchanged": 23,
        "noise_floor": 0.043478260869565216,
        "winner": false,
        "regression": false,
        "sufficient": true
      },
      ...
    }
  ]
}
```
For Phase 23 replace `candidates` with `arms` and add the envelope: `decision` (three-way), `rule` (literal booleans: `ci_excludes_zero`, `mean_delta_at_least_epsilon`, `above_noise_floor`, `per_language_floor_ok`, `adequate`), `arms` (full identity JSON incl. `fingerprint`, doc/chunk counts, wall time, cache hits before/after), `corpus_fingerprint`, `query_set_fingerprint`, `environment` (stack, device, git HEAD/dirty), `gates` (`splits`, `language_splits`, `leg_splits`, `leg_language_splits`, `replay.available`). Write with `json.dumps(..., indent=2, sort_keys=True) + "\n"` (`scripts/generate_bench_fixture.py:459`) and never include personal query text, paths, or the arm DBs.

---

### `src/sif/config/settings.py` (config, static) — ONLY ON `adopt-harrier`

**Analog:** itself (`settings.py:110-137`). The arm defaults live here:
```python
    model_name: str = Field(
        default="Qwen/Qwen3-Embedding-0.6B",
        description="Embedding model name",
    )
    embedding_dim: int = Field(default=1024, ge=1, description="Embedding dimension")
    ...
    model_type: str = Field(
        default="modelscope",
        description="Embedding model type (gguf, sentence_transformers, openai, modelscope)",
    )
```
On a pass, change `model_name` -> `microsoft/harrier-oss-v1-0.6b` and `model_type` -> `sentence_transformers`; leave `embedding_dim`/`max_tokens`/`batch_size` unchanged; leave `query_prompt_name`/`document_prompt_name` as `None` so the known-model table supplies `web_search_query` (Research D-03). Qwen3 must remain selectable via env/`EmbeddingConfig`.

### `src/sif/models/embedding.py` (config, static) — ONLY ON `adopt-harrier`

**Analog:** itself (`models/embedding.py:18-30`):
```python
class EmbeddingConfig(BaseModel):
    """Configuration for embedding models."""

    model_type: ModelType = Field(default=ModelType.MODELSCOPE, description="Model type")
    model_path: str | None = Field(default=None, description="Path to model file")
    model_name: str = Field(
        default="Qwen/Qwen3-Embedding-0.6B", description="Model name or identifier"
    )
```
Keep this default consistent with `Settings` on a flip (Research A11); no other field changes.

### `tests/unit/config/test_settings.py` (test) — ONLY ON `adopt-harrier`

**Analog:** itself (`test_settings.py:11-17`):
```python
def test_default_model_type_is_modelscope(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that default model_type is modelscope."""
    ...
    assert settings.model_type == "modelscope"
```
Update the pinned literal and its docstring/name on a flip; leave the validation tests (`20-38`) unchanged. Also sweep the `EmbeddingConfig` assertions if any exist.

### `tests/unit/search/test_bench_snapshot.py` (test) — ONLY ON `adopt-harrier`

**Analog:** itself (`test_bench_snapshot.py:84-87`, `357-386`):
```python
# D-19: the shipped default embedder. These literals are the pre-Phase-21
DEFAULT_QWEN3_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
DEFAULT_MODEL_TYPE = "modelscope"
...
class TestDefaultEmbedderBaseline:
    """D-19: the committed held-out snapshot was recorded on the pre-phase
    prompt-free ModelScope Qwen3 default and the plain, role-less embed path."""

    def test_shipped_defaults_are_prompt_free_modelscope_qwen3(self) -> None:
        """No env override may masquerade as a changed default (D-19 lock)."""
        ...
        assert settings.model_type == DEFAULT_MODEL_TYPE
        assert settings.model_name == DEFAULT_QWEN3_MODEL_NAME
        assert settings.query_prompt_name is None
        assert settings.document_prompt_name is None
```
On a flip, update the literals/assertions and regenerate the committed snapshot only if the snapshot's metrics depend on the embedder path. The explicit-Qwen3 byte-identical proof is a manual run (same arm DB, pre-flip saved run, every delta exactly 0.0), recorded in the verdict artifact; do not weaken this D-19 lock silently.

### `.planning/phases/23-harrier-gated-evaluation/23-VALIDATION.md` (planning doc, static) — NEW

**Analog:** `.planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-VALIDATION.md` (tracked). Follow its Validation Architecture sections: test framework, requirement -> test map, sampling rate, Wave 0 gaps, manual-only verifications. The Phase 23 content is already specified in `23-RESEARCH.md` "Validation Architecture".

---

## Shared Patterns

### Domain error -> CLI error translation
**Source:** `src/sif/search/personal_bench.py:1074-1081` raises counted `ValueError`; `src/sif/cli/commands/eval.py:741-746` translates:
```python
    try:
        sampled, synthesis = ensure_heldout(metadata, db.connection)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    except (sqlite3.Error, OSError) as e:
        raise click.ClickException(f"Personal eval failed: {e}") from e
```
**Apply to:** `personal_bench.py` (raise `ValueError` with per-language counts), `eval.py` (translate at the boundary), runbook script (turn non-zero/`ValueError` into a FAIL line and exit 1, never a traceback).

### Strict stdout / warnings on stderr
**Source:** `src/sif/cli/commands/eval.py:70-74`:
```python
console = Console()
# stderr contract (bench.py precedent): warnings and disclosures must never
# pollute stdout, which stays clean for `sif eval --personal --json | jq`.
console_err = Console(stderr=True)
```
**Apply to:** every new warning in `eval.py`; the runbook's JSON parsing (always pass `-q`; treat non-JSON stdout as a hard failure). Never print Rich markup from the domain modules.

### Determinism and fingerprints
**Source:** `personal_bench.py:1106-1115` (truncated sha256 over sorted `path\0checksum\0file_size`), `personal_bench.py:1748` (`paired_bootstrap`, seeded `random.Random(0)`, 10,000 resamples), `personal_bench.py:85` (`BOOTSTRAP_RESAMPLES = 10_000`).
**Apply to:** the new query-set fingerprint (`leg\0language\0split\0query` lines, 16 hex chars, target ids deliberately excluded because they are per-arm UUIDs); the verdict artifact's corpus/query fingerprints; all report ordering (declared `LANGUAGES`/`LEGS`/`LENGTH_BUCKETS` order, never dict iteration order).

### Identity provenance
**Source:** `src/sif/embedding/identity.py:166-171` (`to_json` includes `source` + `fingerprint`), `385-392` (`read_identity`), `437-449` (`identity_matches`), `452-494` (`check_identity`: `init` width-only, `embed` may write legacy-assumed, `search` never writes).
**Apply to:** runbook preflight and post-embed assertions; artifact `arms[].identity`; the Harrier arm must record `query_prompt: "web_search_query"`, `document_prompt: null`, `revision` non-null (or a recorded HF sha fallback), `source: "verified"`.

### Generated-doc gate
**Source:** `Makefile:73-76`.
**Apply to:** `docs/cli-reference.md` after adding `--require-language`; `docs/configuration.md` only if a default flips. `docs/benchmarking.md` is hand-maintained and is **not** generated.

### Committed-artifact JSON style
**Source:** `.planning/phases/19-search-correctness/bench/d12-verdict.json` + `scripts/generate_bench_fixture.py:459`.
**Apply to:** `harrier-verdict.json` — `GateResult.to_dict()` verbatim, `indent=2, sort_keys=True`, trailing newline, aggregate evidence only.

### Test conventions
**Source:** `tests/unit/search/test_personal_bench.py:1-7` (module docstring says "pure domain tests: no Click, no Rich, no real index"), `tests/unit/search/test_bench_snapshot.py:213-232` (`TestWarrantsDefaultChange` boundary style), `tests/unit/cli/test_eval.py` (real fixture DB + `CliRunner`), `tests/test_windows_smoke_script.py` (pure builders, no subprocess).
**Apply to:** `test_embedder_verdict.py` (pure, table-driven, stub `ComparisonReport`/`GateResult` objects), `test_harrier_eval.py` (dry-run/identity/artifact/cleanup with stubs; no model load, no network), extended personal-bench/CLI tests (deterministic fixture DBs from `tests/support/eval.py`).

---

## No Analog Found

| File / element | Role | Data Flow | Reason / fallback |
|----------------|------|-----------|-------------------|
| `embedder_verdict.py` three-way decision policy (adopt / keep / insufficient) | service | transform | No existing module returns a policy decision over multiple gate objects. `benchmark.warrants_default_change` is a one-condition bool analog; use RESEARCH.md Pattern 2 for the three-way shape and the `GateResult` fields for inputs. |
| `scripts/harrier_eval.py` resumable stage machine (stage markers, probe mode, cleanup guard) | utility | batch | `scripts/windows_smoke.py` is a fixed linear assertion table, not resumable. Copy its argv/env/subprocess/report structure and add a persisted run-state JSON; RESEARCH.md Pattern 4 defines the stages. |
| `harrier-verdict.json` envelope (arms/identity/environment keys) | config | static | The D-12 artifact supplies the decision + verbatim gate dict shape; the Phase 23 envelope is new. Build it from the documented schema in RESEARCH.md D-09/D-12 and keep gate leaves identical to `GateResult.to_dict()`. |

---

## Metadata

**Analog search scope:** `src/sif/search/`, `src/sif/cli/commands/`, `src/sif/embedding/`, `src/sif/config/`, `src/sif/models/`, `scripts/`, `tests/`, `docs/`, `.planning/phases/19-search-correctness/bench/`
**Files read (analog extraction):** `personal_bench.py` (targeted), `benchmark.py` (targeted), `eval.py` (targeted), `identity.py` (targeted), `settings.py` (targeted), `models/embedding.py`, `scripts/windows_smoke.py`, `scripts/publish_registry.py`, `scripts/generate_bench_fixture.py` (targeted), `tests/unit/search/test_personal_bench.py` (targeted), `tests/unit/cli/test_eval.py` (targeted), `tests/unit/mcp/test_registry_script.py`, `tests/test_windows_smoke_script.py`, `tests/support/eval.py` (targeted), `tests/unit/search/test_bench_snapshot.py` (targeted), `docs/benchmarking.md` (targeted), `d12-verdict.json`, `Makefile` (targeted)
**Tracked-source verification:** all named analog paths return non-empty `git ls-files` output; no gitignored capability mirror paths were used.
**Pattern extraction date:** 2026-11-16
