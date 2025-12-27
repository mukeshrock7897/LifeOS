from __future__ import annotations

from app.config import settings


def register_ping(mcp) -> None:
    @mcp.tool()
    def ping():
        """Simple connectivity check."""
        return {"result": "pong"}

    @mcp.tool()
    def server_info():
        """Return basic server metadata."""
        return {
            "name": settings.APP_NAME,
            "transport": settings.MCP_TRANSPORT,
            "host": settings.MCP_HOST,
            "port": settings.http_port,
        }
