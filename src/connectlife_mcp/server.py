"""Shared FastMCP server instance and session manager singleton."""

import fastmcp
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .session import SessionManager

mcp = fastmcp.FastMCP(
    "ConnectLife MCP Server",
    instructions=(
        "Multi-tenant MCP server for ConnectLife smart appliances. "
        "If MCP_CONNECTLIFE_USERNAME and MCP_CONNECTLIFE_PASSWORD "
        "environment variables are set, authentication is automatic "
        "and tools can be called directly without a session_id. "
        "Otherwise, call 'login' first to obtain a session_id, "
        "then pass it to every other tool. "
        "Call 'logout' when done to free server resources."
    ),
)

session_manager = SessionManager()


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_: Request) -> Response:
    """Container health check endpoint."""
    return JSONResponse({"status": "ok"})
