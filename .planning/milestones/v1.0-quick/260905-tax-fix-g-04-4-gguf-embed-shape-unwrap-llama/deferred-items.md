# Deferred Items — 260905-tax (G-04-4 GGUF embed shape unwrap)

## 1. Full-suite caplog pollution: test_docs.py poisons later log-assertion tests

**Discovered during:** Task 2 (full quality suite gate), 2026-09-05.

**Status:** Pre-existing, unrelated to this plan (proven — see repro), out of scope per the
plan's Task 2 boundary ("edits to files outside this plan's scope are out of scope").

**Symptom:** Full `pytest -q` run ends `2 failed, 627 passed, 11 skipped`:

- `tests/unit/embedding/test_openai_embedder.py::TestOpenAIEmbedderBehavior::test_import_error_logs_install_hint`
- `tests/unit/embedding/test_openai_embedder.py::TestOpenAIEmbedderDimensionCache::test_corrupt_cache_treated_as_miss`

Both fail with `caplog.text == ''` — the log records never reach pytest's root capture
handler.

**Minimal repro (none of this plan's files involved):**

```bash
env -u FORCE_COLOR NO_COLOR=1 .venv/bin/python -m pytest \
  tests/test_docs.py tests/unit/embedding/test_openai_embedder.py -q
# 2 failed, 28 passed
```

Each file passes standalone (`test_openai_embedder.py` alone: 18 passed).

**Root cause:** `setup_logging()` in `src/sif/utils/logging.py` (line ~130) permanently sets
`logging.getLogger("sif").propagate = False` (and replaces its handlers). `tests/test_docs.py`
invokes the CLI in-process (CliRunner), which calls `setup_logging()`; from that point on,
no `"sif.*"` logger record propagates to the real root logger, so pytest's `caplog` fixture
(attached at root) captures nothing for the remainder of the run. The two OpenAI-embedder
tests above are the only tests that assert on `caplog.text` for a `sif.*` logger, so only
they fail — and only when something earlier in the run triggered the CLI logging setup.

**Suggested fix (for a follow-up quick task):** an autouse fixture in `tests/conftest.py`
that snapshots and restores the `"sif"` logger's `propagate`/`handlers`/`level` around each
test — or have the log-assertion tests locally force `propagate = True`. Verify the full
suite after either change: other tests may currently depend on the leaked quiet-stderr
state (e.g., CliRunner output assertions), so a global fixture needs a full-suite check.

**Also repaired this session (environmental, no code change, per Task 2 precondition
pattern):** `pytest-asyncio` was missing from `.venv` (env drift after a `uv sync`; not
declared in `pyproject.toml` or `uv.lock` despite committed `@pytest.mark.asyncio` tests).
Restored via `.venv/bin/python -m pip install pytest-asyncio` (1.4.0) — fixed 25 MCP async
failures. `httpx` was still present, precondition satisfied. Consider declaring
`pytest-asyncio` and `httpx` in the dev test extras so the suite does not depend on
hand-installed venv state.
