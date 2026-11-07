"""Real-subprocess e2e battery for the MCP-embedded watch host (LIVE-08, SC1).

Every test drives the REAL stdio MCP server (``sif mcp stdio``) over its own
seeded tmp collection with ``SIF_MCP_WATCH=1``, speaking the JSON-RPC line
protocol over the subprocess pipes, and asserts OUTCOMES: refresh (a file
created after server start becomes findable through a ``query`` tools/call
with no manual update), responsiveness (a query issued while a write burst
settles still gets its response inside the deadline), protocol-clean stdout
(every stdout line parses as JSON — Pitfall 1: stdout is the protocol
channel), and an initialize handshake that never waits on the startup
reconcile (Pitfall 4: serve first, reconcile on the watch worker).

Queries use the ``lex:`` prefix so the search routes to pure BM25 and never
loads an embedding model inside the e2e. All reads are deadline-bounded
through a reader thread; the spawner's ``finally`` never leaks a server
process (Phase 12 e2e culture).
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.indexing.incremental import IncrementalIndexer


_SEED_BODY = "# Seed Note\n\n" + ("Seed paragraph text. " * 30)
_LIVE_BODY = "# Live Note\n\n" + ("Live paragraph text. " * 30)
_BURST_BODY = "# Burst Note\n\n" + ("Burst paragraph text. " * 30)
_DRIFT_BODY = "# Drifted Note\n\n" + ("Drifted paragraph text. " * 30)

_BOOT_DEADLINE_S = 30.0
_HANDSHAKE_DEADLINE_S = 15.0
_RESPONSE_DEADLINE_S = 10.0
_RESPONSIVE_DEADLINE_S = 5.0
_INDEX_DEADLINE_S = 30.0
_SHUTDOWN_DEADLINE_S = 20.0
_SETTLE_S = 2.5
_POLL_INTERVAL_S = 0.1


def _child_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Child environment: SIF_-stripped, FORCE_COLOR unset, NO_COLOR on."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SIF_")}
    env.pop("FORCE_COLOR", None)
    env["NO_COLOR"] = "1"
    if extra is not None:
        env.update(extra)
    return env


def _seed_db(db_path: Path, notes_dir: Path, files: dict[str, str]) -> None:
    """Build a real index with one collection pointing at the seeded tree."""
    notes_dir.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        (notes_dir / name).write_text(body, encoding="utf-8")
    db = Database(db_path)
    try:
        db.init_schema()
        with db.connection:
            CollectionRepository(db.connection).create(
                Collection(name="notes", path=str(notes_dir))
            )
    finally:
        db.close()


def _preindex(db_path: Path) -> None:
    """Index every seeded file in-process so later edits become real drift."""
    db = Database(db_path)
    try:
        coll = CollectionRepository(db.connection).list_all()[0]
        IncrementalIndexer(db.connection).update_collection(coll)
    finally:
        db.close()


class _StdioServer:
    """Line-protocol client for the real stdio MCP server subprocess.

    stdout is pumped by a daemon thread into ``stdout_lines`` (the
    protocol-clean corpus) plus a queue ``wait_response`` polls under explicit
    deadlines — no naked blocking reads anywhere. stderr is pumped separately
    so a chatty server can never fill the pipe and block. The context-manager
    exit is the safety net: a still-running child is terminated, so a failing
    assertion can never leak a server process.
    """

    def __init__(self, db_path: Path, cwd: Path) -> None:
        """Spawn ``sif mcp stdio`` with SIF_MCP_WATCH=1 and start the pumps."""
        # SIF_MODEL_TYPE=gguf (with no model path) makes SearchBackend's
        # embedder construction fail fast into its caught-warning path — no
        # real model load inside the e2e (queries are lex:/BM25-only anyway).
        self._proc = subprocess.Popen(
            [
                sys.executable,
                "-u",
                "-m",
                "sif.cli.main",
                "--index",
                str(db_path),
                "mcp",
                "stdio",
            ],
            cwd=cwd,
            env=_child_env({"SIF_MCP_WATCH": "1", "SIF_MODEL_TYPE": "gguf"}),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.stdout_lines: list[str] = []
        self.stderr_text = ""
        self._pending: queue.Queue[str] = queue.Queue()
        self._stderr_chunks: list[str] = []
        self._readers = [
            threading.Thread(target=self._pump_stdout, daemon=True),
            threading.Thread(target=self._pump_stderr, daemon=True),
        ]
        for reader in self._readers:
            reader.start()

    def _pump_stdout(self) -> None:
        """Collect every stdout line (protocol channel) into list + queue."""
        assert self._proc.stdout is not None
        for raw in self._proc.stdout:
            line = raw.decode("utf-8", errors="replace").strip()
            if line:
                self.stdout_lines.append(line)
                self._pending.put(line)

    def _pump_stderr(self) -> None:
        """Collect stderr (watcher logs live here — never on stdout)."""
        assert self._proc.stderr is not None
        for raw in self._proc.stderr:
            self._stderr_chunks.append(raw.decode("utf-8", errors="replace"))
            self.stderr_text = "".join(self._stderr_chunks[-200:])

    def send(self, message: dict[str, Any]) -> None:
        """Write one JSON-RPC message line to the server's stdin."""
        assert self._proc.stdin is not None
        self._proc.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
        self._proc.stdin.flush()

    def send_request(
        self, msg_id: int, method: str, params: dict[str, Any] | None = None
    ) -> None:
        """Send a request with the given id."""
        self.send({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}})

    def send_notification(self, method: str) -> None:
        """Send a notification (no id, no response expected)."""
        self.send({"jsonrpc": "2.0", "method": method})

    def wait_response(self, msg_id: int, deadline_s: float, description: str) -> dict[str, Any]:
        """Poll the reader queue until the response for ``msg_id`` arrives."""
        deadline = time.monotonic() + deadline_s
        while time.monotonic() < deadline:
            try:
                line = self._pending.get(timeout=_POLL_INTERVAL_S)
            except queue.Empty:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                # A non-JSON stdout line corrupts the protocol — surfaced by
                # _assert_protocol_clean with the full corpus, not here.
                continue
            if message.get("id") == msg_id:
                return message
        raise AssertionError(
            f"{description} not received within {deadline_s}s "
            f"(stdout lines so far: {len(self.stdout_lines)}; "
            f"stderr tail:\n{self.stderr_text[-2000:]})"
        )

    def finish(self) -> None:
        """Graceful shutdown: stdin EOF ends the serve loop; the host's
        finally stops the watcher (flush + checkpoint) before exit."""
        if self._proc.stdin is not None:
            self._proc.stdin.close()
        self._proc.wait(timeout=_SHUTDOWN_DEADLINE_S)

    @property
    def returncode(self) -> int | None:
        """The child's exit status, or None while still running."""
        return self._proc.returncode

    def __enter__(self) -> _StdioServer:
        """Enter the client context."""
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Safety net: a still-running child is terminated, never leaked."""
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=_SHUTDOWN_DEADLINE_S)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=_SHUTDOWN_DEADLINE_S)
        for stream in (self._proc.stdin, self._proc.stdout, self._proc.stderr):
            if stream is not None:
                stream.close()


def _initialize(server: _StdioServer) -> None:
    """Complete the initialize handshake and the initialized notification."""
    server.send_request(1, "initialize")
    response = server.wait_response(1, _BOOT_DEADLINE_S, "initialize response")
    result = response.get("result", {})
    assert result.get("protocolVersion") == "2024-11-05", f"unexpected handshake: {response}"
    server.send_notification("notifications/initialized")


def _query(
    server: _StdioServer, msg_id: int, text: str, deadline_s: float = _RESPONSE_DEADLINE_S
) -> list[dict[str, Any]]:
    """Run one ``query`` tools/call and return its result rows."""
    server.send_request(
        msg_id,
        "tools/call",
        {"name": "query", "arguments": {"query": text, "limit": 5}},
    )
    response = server.wait_response(msg_id, deadline_s, f"query response for {text!r}")
    assert "error" not in response, f"query tool errored: {response}"
    content = response["result"]["content"]
    payload = json.loads(content[0]["text"])
    return payload["results"]


def _poll_findable(
    server: _StdioServer, path: str, needle_query: str, deadline_s: float
) -> None:
    """Poll query results until ``path`` is findable — no manual update ever."""
    # Nonlocal-free mutable id: each poll gets a fresh request id.
    _msg_id = [100]
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        if any(row.get("path") == path for row in _query(server, _msg_id[0], needle_query)):
            return
        _msg_id[0] += 1
        time.sleep(_POLL_INTERVAL_S)
    raise AssertionError(
        f"{path} not findable via query {needle_query!r} within {deadline_s}s "
        f"(stdout lines: {len(server.stdout_lines)}; stderr tail:\n{server.stderr_text[-2000:]})"
    )


def _assert_protocol_clean(server: _StdioServer) -> None:
    """Pitfall 1: every captured stdout line must parse as JSON."""
    bad: list[str] = []
    for line in server.stdout_lines:
        try:
            json.loads(line)
        except json.JSONDecodeError:
            bad.append(line)
    assert not bad, (
        f"non-JSON stdout lines corrupt the stdio JSON-RPC stream (Pitfall 1): {bad!r}"
    )


def _doc_path(notes_dir: Path, name: str) -> str:
    """Stored-path spelling for a file under the collection (resolved)."""
    return str((notes_dir / name).resolve())


def _assert_clean_exit(server: _StdioServer) -> None:
    """The graceful EOF shutdown exits 0 and leaves stdout protocol-clean."""
    assert server.returncode == 0, (
        f"mcp stdio exited {server.returncode}; stderr tail:\n{server.stderr_text[-2000:]}"
    )
    _assert_protocol_clean(server)


def test_stdio_watch_refreshes_index_while_serving(tmp_path: Path) -> None:
    """SC1/LIVE-08/D-01: with SIF_MCP_WATCH=1, a file created AFTER server
    start becomes findable through a query tools/call — no manual update, no
    restart, while the server keeps answering every request."""
    db_path = tmp_path / "mcp.db"
    notes = tmp_path / "notes"
    _seed_db(db_path, notes, {"seed.md": _SEED_BODY})
    live_path = _doc_path(notes, "live-note.md")

    with _StdioServer(db_path, tmp_path) as server:
        _initialize(server)
        # The queued startup reconcile (Pitfall 4) makes the seed findable —
        # proof the watch host armed and its first worker jobs drained.
        _poll_findable(
            server, _doc_path(notes, "seed.md"), "lex: seed paragraph", _INDEX_DEADLINE_S
        )
        # NOW the live proof: a brand-new file under the collection root.
        (notes / "live-note.md").write_text(_LIVE_BODY, encoding="utf-8")
        _poll_findable(server, live_path, "lex: live paragraph", _INDEX_DEADLINE_S)
        server.finish()

    _assert_clean_exit(server)


def test_stdio_watch_query_responsive_during_burst(tmp_path: Path) -> None:
    """SC1: a query issued while a multi-file write burst is settling gets
    its JSON-RPC response inside the deadline — event handling never starves
    query handling."""
    db_path = tmp_path / "mcp.db"
    notes = tmp_path / "notes"
    _seed_db(db_path, notes, {"seed.md": _SEED_BODY})
    burst_paths = [_doc_path(notes, f"burst-{i}.md") for i in range(1, 6)]

    with _StdioServer(db_path, tmp_path) as server:
        _initialize(server)
        _poll_findable(
            server, _doc_path(notes, "seed.md"), "lex: seed paragraph", _INDEX_DEADLINE_S
        )
        # The burst: five files land at once...
        for i in range(1, 6):
            (notes / f"burst-{i}.md").write_text(_BURST_BODY, encoding="utf-8")
        # ...and while it settles, this query must still answer in 5s.
        results = _query(server, 50, "lex: burst paragraph", _RESPONSIVE_DEADLINE_S)
        assert isinstance(results, list)
        # The burst eventually lands (event handling worked, just not at the
        # expense of query handling).
        deadline = time.monotonic() + _INDEX_DEADLINE_S
        found = False
        msg_id = 60
        while time.monotonic() < deadline and not found:
            rows = _query(server, msg_id, "lex: burst paragraph")
            found = any(row.get("path") == path for path in burst_paths for row in rows)
            msg_id += 1
            if not found:
                time.sleep(_POLL_INTERVAL_S)
        assert found, "burst files were never indexed by the embedded watcher"
        server.finish()

    _assert_clean_exit(server)


def test_stdio_stdout_protocol_clean_during_burst(tmp_path: Path) -> None:
    """Pitfall 1: every stdout line the server emits while the watcher runs
    parses as JSON — watch output lives on stderr only (the logger's
    handlers), stdout stays the JSON-RPC protocol channel."""
    db_path = tmp_path / "mcp.db"
    notes = tmp_path / "notes"
    _seed_db(db_path, notes, {f"seed-{i}.md": _SEED_BODY for i in range(3)})

    with _StdioServer(db_path, tmp_path) as server:
        _initialize(server)
        _poll_findable(
            server, _doc_path(notes, "seed-1.md"), "lex: seed paragraph", _INDEX_DEADLINE_S
        )
        # A burst + queries while the watcher is actively working.
        for i in range(3):
            (notes / f"live-{i}.md").write_text(_LIVE_BODY, encoding="utf-8")
        _query(server, 70, "lex: live paragraph")
        time.sleep(_SETTLE_S)
        _query(server, 71, "lex: live paragraph")
        server.finish()

    _assert_clean_exit(server)


def test_stdio_initialize_not_blocked_by_pending_drift(tmp_path: Path) -> None:
    """Pitfall 4: the initialize handshake answers within the deadline even
    though the server started over a collection with drifted files — the
    reconcile runs as the watcher's first queued jobs, never before serving."""
    db_path = tmp_path / "mcp.db"
    notes = tmp_path / "notes"
    _seed_db(db_path, notes, {f"seed-{i}.md": _SEED_BODY for i in range(3)})
    # Pre-index, then rewrite every file: real drift pending at server start.
    _preindex(db_path)
    for i in range(3):
        (notes / f"seed-{i}.md").write_text(_DRIFT_BODY, encoding="utf-8")

    with _StdioServer(db_path, tmp_path) as server:
        started = time.monotonic()
        server.send_request(1, "initialize")
        response = server.wait_response(
            1, _HANDSHAKE_DEADLINE_S, "initialize response under pending drift"
        )
        elapsed = time.monotonic() - started
        result = response.get("result", {})
        assert result.get("protocolVersion") == "2024-11-05", f"unexpected handshake: {response}"
        assert elapsed < _HANDSHAKE_DEADLINE_S
        server.send_notification("notifications/initialized")
        # The queued reconcile still completes — drifted content findable —
        # proving the work happened on the worker, not before the handshake.
        _poll_findable(
            server, _doc_path(notes, "seed-2.md"), "lex: drifted paragraph", _INDEX_DEADLINE_S
        )
        server.finish()

    _assert_clean_exit(server)
