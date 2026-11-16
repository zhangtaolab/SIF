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

from collections.abc import AsyncGenerator, Callable, Sequence
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from sif._version import __version__
from sif.config.settings import Settings
from sif.mcp.backend import SearchBackend
from sif.mcp.tools import register_resource, register_tools
from sif.mcp.watch_host import (
    mcp_session_lifespan,
    start_embedded_watch,
    stop_embedded_watch,
)
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


def _merge_allowlist(defaults: Sequence[str], extra: Sequence[str] | None) -> list[str]:
    """Loopback defaults first, then explicit values; a literal ``*`` never widens.

    D-13: the loopback defaults are always present, so passing
    ``--allowed-hosts`` can only add names — it can never replace the
    loopback allowlist or turn the check off. A wildcard entry is dropped
    rather than honored; there is no code path that produces ``["*"]``.
    """
    entries = [*defaults, *(extra or ())]
    allowed: list[str] = []
    for entry in entries:
        if not entry or entry == "*":
            continue
        if entry not in allowed:
            allowed.append(entry)
    return allowed


def build_transport_security(
    allowed_hosts: Sequence[str] | None = None,
    allowed_origins: Sequence[str] | None = None,
) -> TransportSecuritySettings:
    """Build explicit DNS-rebinding settings — never ``None``, never ``*``.

    ``allowed_hosts`` values are UNIONED with the loopback defaults (D-13):
    a caller can add a bind name but can never remove loopback or disable
    the check. ``allowed_origins=None`` falls back to the existing CORS
    origins; an explicit sequence replaces them (an empty sequence stays
    fail-closed). A literal ``*`` in either list is dropped, never honored.
    """
    hosts = _merge_allowlist(DEFAULT_ALLOWED_HOSTS, allowed_hosts)
    if allowed_origins is None:
        origins = _merge_allowlist((), DEFAULT_CORS_ORIGINS)
    else:
        origins = _merge_allowlist((), allowed_origins)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


def _host_is_allowed(host: str, allowed: Sequence[str]) -> bool:
    """Exact host match, or a ``:*`` entry matching any port on that host."""
    return any(
        host == entry or (entry.endswith(":*") and host.startswith(entry[:-1])) for entry in allowed
    )


def _make_health_host_guard(allowed: Sequence[str]) -> Callable[[str | None], None]:
    """Build the narrow parent-level ``/health`` Host dependency (C2).

    ``/health`` sits outside the SDK mount, so the SDK's transport security
    never sees it; this guard shares the same allowlist and answers a bad
    ``Host`` with 421, matching the SDK's status. A missing Host fails closed.
    """

    def guard(host: str | None = Header(default=None)) -> None:
        if host is None or not _host_is_allowed(host, allowed):
            raise HTTPException(status_code=421, detail="Invalid Host header")

    return guard


def _resolve_transport_security(
    server: MCPServer,
    allowed_hosts: Sequence[str] | None,
    allowed_origins: Sequence[str] | None,
) -> TransportSecuritySettings:
    """Merge overrides per dimension with the server's recorded policy.

    An override on one allowlist must not drop the other recorded one: a
    partial override that rebuilt both from the caller's arguments would
    silently lose the operator's host allowlist or widen a fail-closed
    ``allowed_origins=[]`` back to the defaults (WR-05).
    """
    existing = getattr(server, _TRANSPORT_SECURITY_ATTR, None)
    if isinstance(existing, TransportSecuritySettings):
        if allowed_hosts is None and allowed_origins is None:
            return existing
        hosts = existing.allowed_hosts if allowed_hosts is None else allowed_hosts
        origins = existing.allowed_origins if allowed_origins is None else allowed_origins
        return build_transport_security(hosts, origins)
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
    redirect is introduced (22-RESEARCH.md Pattern 1). The lifespan composes
    the SDK session manager with the watch host in the D-18 order.
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

    app = FastAPI(lifespan=mcp_session_lifespan(db_path, mcp.session_manager, settings))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # C2: /health is a parent route outside the SDK mount; it gets a narrow
    # Host guard over the same allowlist (bad Host -> 421, like the SDK).
    health_host_guard = _make_health_host_guard(security.allowed_hosts)

    @app.get("/health", dependencies=[Depends(health_host_guard)])
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
    watch = start_embedded_watch(db_path, settings)
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
