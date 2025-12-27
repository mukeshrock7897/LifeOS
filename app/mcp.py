from __future__ import annotations

import os

from app.config import settings

# FastMCP reads .env on import; an empty PORT entry breaks int parsing.
if os.getenv("FASTMCP_PORT") in (None, "") and os.getenv("PORT", "") == "":
    os.environ["FASTMCP_PORT"] = str(settings.http_port)

from fastmcp import FastMCP
from app.utils.logger import configure_logging, logger

from app.services.notes import register_notes_tools
from app.services.calendar import register_calendar_tools
from app.services.filesystem import register_filesystem_tools
from app.services.tasks import register_tasks_tools

from app.mcp_ext.ping import register_ping
from app.mcp_ext.prompts import register_prompts
from app.mcp_ext.templates import register_templates
from app.mcp_ext.sampling import register_sampling
from app.mcp_ext.elicitations import register_elicitations
from app.mcp_ext.resources import register_resources

configure_logging()

mcp = FastMCP(name=settings.APP_NAME)


# --- HTTP helpers (only used when running in HTTP transport) ---
# FastMCP supports "custom_route" to add extra endpoints alongside /mcp.
if hasattr(mcp, "custom_route"):
    from starlette.requests import Request
    from starlette.responses import JSONResponse, PlainTextResponse

    @mcp.custom_route("/", methods=["GET"])
    async def root(request: Request):
        return PlainTextResponse(f"{settings.APP_NAME} is running. MCP endpoint: /mcp")

    @mcp.custom_route("/health", methods=["GET"])
    async def health_route(request: Request):
        return JSONResponse({"status": "ok", "service": settings.APP_NAME})


# --- MCP tools/resources ---
@mcp.tool()
def health():
    """Tool-level health payload (works in both STDIO and HTTP modes)."""
    return {"status": "ok", "service": settings.APP_NAME}


def register_all() -> None:
    logger.info("Registering MCP tools & resources")

    register_notes_tools(mcp)
    register_calendar_tools(mcp)
    register_filesystem_tools(mcp)
    register_tasks_tools(mcp)

    register_ping(mcp)
    register_prompts(mcp)
    register_templates(mcp)
    register_sampling(mcp)
    register_elicitations(mcp)
    register_resources(mcp)

    logger.info(f"{settings.APP_NAME} ready")


register_all()
