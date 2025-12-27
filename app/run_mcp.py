from __future__ import annotations

import argparse
import inspect
import os

import uvicorn

from app.config import settings
from app.health_server import start_health_server

# Some shells export PORT as an empty string, which breaks fastmcp settings parsing.
if os.getenv("PORT", "") == "":
    os.environ.pop("PORT", None)

from app.mcp import mcp
from app.utils.logger import logger


def _call_run_stdio() -> None:
    """Run MCP with STDIO transport (best-effort across fastmcp versions)."""
    # Optional sidecar health server for container orchestrators
    if settings.HEALTH_ENABLED:
        start_health_server(port=settings.HEALTH_PORT, host=settings.MCP_HOST)

    # Try most explicit -> most permissive
    if hasattr(mcp, "run_stdio"):
        return mcp.run_stdio()  # type: ignore[attr-defined]

    if hasattr(mcp, "run"):
        try:
            return mcp.run(transport="stdio")
        except TypeError:
            # Older API: no transport param, defaults to stdio
            return mcp.run()

    raise RuntimeError("FastMCP instance does not expose a runnable stdio method")


def _get_asgi_app():
    """Return an ASGI app from FastMCP if available."""
    for attr in ("asgi_app", "http_app", "app"):
        if hasattr(mcp, attr):
            obj = getattr(mcp, attr)
            # Some APIs provide a callable that builds the app
            return obj() if callable(obj) else obj
    return None


def _call_run_http(host: str, port: int) -> None:
    """Run MCP over HTTP (best-effort across fastmcp versions)."""
    # Preferred path: FastMCP provides a built-in runner
    if hasattr(mcp, "run_http"):
        return mcp.run_http(host=host, port=port)  # type: ignore[attr-defined]

    if hasattr(mcp, "run"):
        try:
            return mcp.run(transport="http", host=host, port=port)
        except TypeError:
            pass

    # Fallback: mount ASGI app in Uvicorn
    app = _get_asgi_app()
    if app is None:
        raise RuntimeError(
            "Could not determine an ASGI app to serve. "
            "Your fastmcp version may be incompatible; upgrade fastmcp>=0.4.0."
        )

    logger.info(f"Starting MCP HTTP server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LifeOS MCP (stdio or http).")
    parser.add_argument(
        "--transport",
        choices=["auto", "stdio", "http"],
        default=settings.MCP_TRANSPORT or "auto",
        help="Transport to use (default: auto).",
    )
    parser.add_argument("--host", default=settings.MCP_HOST, help="Bind host for HTTP.")
    parser.add_argument(
        "--port",
        type=int,
        default=settings.http_port,
        help="Bind port for HTTP.",
    )

    args = parser.parse_args()

    transport = (args.transport or "auto").strip().lower()
    if transport == "auto":
        transport = settings.transport

    if transport == "http":
        _call_run_http(host=args.host, port=int(args.port))
    else:
        _call_run_stdio()


if __name__ == "__main__":
    main()
