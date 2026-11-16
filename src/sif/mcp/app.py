"""Composition root for the SIF MCP server (Phase 22 D-01).

One ``MCPServer`` per process, one ``streamable_http_app()`` call, one mount.
The SDK owns protocol negotiation, sessions, and era routing; this module only
composes SIF's preserved backend, tool set, and watch host around it.

Ordering rules that are load-bearing (22-RESEARCH.md Pattern 1/Pattern 4):

- ``SearchBackend`` is constructed inside the SDK lifespan, never at import
  time, so a cold ``sif mcp stdio`` process opens no model and no schema until
  the transport has diverted stdout (Pitfall 8/Pitfall 9).
- ``streamable_http_app()`` is called exactly once per server; calling it twice
  orphans the first session manager and the lifespan then raises
  ``RuntimeError: Task group is not initialized`` (Pitfall 3).
- The SDK app is mounted at ``/`` with the inner path ``/mcp`` so ``/mcp``
  serves without a 307 redirect, and ``/health`` is registered on the parent
  BEFORE the mount.
- Transport security is always an explicit ``TransportSecuritySettings``; the
  SDK only auto-enables DNS-rebinding protection for loopback binds and
  silently disables it for ``0.0.0.0``/non-loopback hosts (Pitfall 4).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from sif._version import __version__
from sif.config.settings import Settings
from sif.mcp.backend import SearchBackend
from sif.mcp.tools import register_resource, register_tools
from sif.mcp.watch_host import start_embedded_watch, stop_embedded_watch
from sif.utils.logging import get_logger, set_quiet


logger = get_logger(__name__)

# Wire identity seam (open question 1, resolved): the handshake keeps the
# historical name while the plugin/marketplace identity stays ``sif``.
SERVER_NAME = "sif-mcp-server"

# The existing browser origins, moved here because ``app.py`` must not import
# from ``transports/`` (that package is deleted in 22-02). No ``*`` ever.
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080

# D-13: loopback-only defaults, bare and wildcard-port forms so both a
# default-port request and an explicit-port request match.
DEFAULT_ALLOWED_HOSTS = [
    "127.0.0.1",
    "127.0.0.1:*",
    "localhost",
    "localhost:*",
    "[::1]",
    "[::1]:*",
]

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

# Attribute carrying the server's resolved transport policy so a server built
# here and mounted by ``create_http_app`` applies the same allowlists.
_TRANSPORT_SECURITY_ATTR = "sif_transport_security"


def build_transport_security(
    allowed_hosts: Sequence[str] | None = None,
    allowed_origins: Sequence[str] | None = None,
) -> TransportSecuritySettings:
    """Build explicit DNS-rebinding settings — never ``None``, never ``*``.

    ``allowed_hosts=None`` falls back to the loopback defaults and
    ``allowed_origins=None`` to the existing CORS origins. An explicit empty
    sequence is honored (a fail-closed allowlist), not replaced by a default.
    """
    hosts = list(allowed_hosts) if allowed_hosts is not None else list(DEFAULT_ALLOWED_HOSTS)
    origins = list(allowed_origins) if allowed_origins is not None else list(DEFAULT_CORS_ORIGINS)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


def _resolve_transport_security(
    server: MCPServer,
    allowed_hosts: Sequence[str] | None,
    allowed_origins: Sequence[str] | None,
) -> TransportSecuritySettings:
    """Reuse the server's policy unless the caller overrides an allowlist."""
    if allowed_hosts is None and allowed_origins is None:
        existing = getattr(server, _TRANSPORT_SECURITY_ATTR, None)
        if isinstance(existing, TransportSecuritySettings):
            return existing
    return build_transport_security(allowed_hosts, allowed_origins)


def build_server(
    db_path: str,
    settings: Settings | None = None,
    *,
    allowed_hosts: Sequence[str] | None = None,
    cors_origins: Sequence[str] | None = None,
) -> MCPServer:
    """Build the one ``MCPServer`` for this process.

    The name/version pair is readable as ``server.name``/``server.version``
    without entering the lifespan, which is what the identity tests assert.
    ``SearchBackend`` and the tool/resource registrations happen inside the
    lifespan — constructing a backend at import would open the index (and the
    embedding cache) before the stdio transport diverts stdout.

    The allowlist arguments resolve the transport policy recorded on the
    server; ``create_http_app`` reuses it for the mounted SDK app.
    """
    registered = False

    @asynccontextmanager
    async def _lifespan(server: MCPServer) -> AsyncGenerator[SearchBackend, None]:
        nonlocal registered
        backend = SearchBackend(db_path, settings=settings)
        # One registration per server: the lifespan can be entered more than
        # once in tests (one in-process client per mode), and re-registering
        # a tool only logs a duplicate warning. Production enters it once.
        if not registered:
            register_tools(server, backend)
            register_resource(server, backend)
            registered = True
        yield backend

    server = MCPServer(SERVER_NAME, version=__version__, lifespan=_lifespan)
    setattr(server, _TRANSPORT_SECURITY_ATTR, build_transport_security(allowed_hosts, cors_origins))
    return server


def create_http_app(
    db_path: str,
    settings: Settings | None = None,
    *,
    cors_origins: Sequence[str] | None = None,
    allowed_hosts: Sequence[str] | None = None,
    server: MCPServer | None = None,
) -> FastAPI:
    """Build the FastAPI parent app hosting the SDK Streamable HTTP app.

    ``/health`` is registered before the root mount so it stays a parent
    route; the SDK app is mounted at ``/`` with inner path ``/mcp`` so no
    redirect is introduced (22-RESEARCH.md Pattern 1). The lifespan enters
    ``session_manager.run()`` exactly once (D-18); the watch composition is
    layered on in Task 3 via ``mcp_session_lifespan``.
    """
    mcp = (
        server
        if server is not None
        else build_server(
            db_path,
            settings,
            allowed_hosts=allowed_hosts,
            cors_origins=cors_origins,
        )
    )
    security = _resolve_transport_security(mcp, allowed_hosts, cors_origins)
    origins = list(cors_origins) if cors_origins is not None else list(DEFAULT_CORS_ORIGINS)

    # Exactly one call: it creates the session manager as a side effect.
    sdk_app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        transport_security=security,
    )

    @asynccontextmanager
    async def _app_lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        async with mcp.session_manager.run():
            yield

    app = FastAPI(lifespan=_app_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # AFTER /health: a root mount swallows every path registered later.
    app.mount("/", sdk_app)
    return app


def run_stdio(db_path: str, settings: Settings | None = None) -> None:
    """Serve MCP over the SDK stdio transport (blocking).

    ``set_quiet`` runs before any model-capable import so diagnostics cannot
    reach the protocol channel (D-16). The embedded watcher keeps the Phase 12
    wiring: it starts before serving and stops in the ``finally`` with the
    D-14 flush -> checkpoint -> close order.
    """
    set_quiet(True)
    server = build_server(db_path, settings)
    watch = start_embedded_watch(db_path)
    try:
        server.run(transport="stdio")
    finally:
        stop_embedded_watch(watch)


def run_http_app(app: FastAPI, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Serve a pre-built app with uvicorn (lazy import keeps module load light)."""
    import uvicorn  # noqa: PLC0415

    uvicorn.run(app, host=host, port=port, log_level="info")


def run_http(  # noqa: PLR0913 — one parameter per `mcp http` CLI flag
    db_path: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    cors_origins: Sequence[str] | None = None,
    allowed_hosts: Sequence[str] | None = None,
    settings: Settings | None = None,
) -> None:
    """Serve MCP over Streamable HTTP on the FastAPI parent app (blocking)."""
    set_quiet(True)
    if allowed_hosts is None and host not in _LOOPBACK_HOSTS:
        # D-13: never widen silently. The bind stays loopback-only for Host
        # validation; pass explicit allowed hosts to serve a non-loopback name.
        logger.warning(
            "MCP HTTP bind host %s is not loopback; allowed hosts stay loopback-only "
            "(pass --allowed-hosts to widen it)",
            host,
        )
    app = create_http_app(
        db_path,
        settings,
        cors_origins=cors_origins,
        allowed_hosts=allowed_hosts,
    )
    run_http_app(app, host=host, port=port)
