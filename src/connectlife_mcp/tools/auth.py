"""Authentication MCP tools: login, logout, whoami, auto_login."""

from connectlife.api import LifeConnectAuthError

from ..server import mcp, session_manager
from ..session import SessionError


@mcp.tool()
async def login(username: str, password: str) -> dict:
    """Log in to ConnectLife and obtain a session token.

    The returned ``session_id`` must be passed to all other tools.
    Only username + password authentication is supported (no SSO).

    Returns a dict with ``session_id`` on success, or ``error`` on failure.

    Note: If ``MCP_CONNECTLIFE_USERNAME`` and ``MCP_CONNECTLIFE_PASSWORD``
    environment variables are set, the server auto-authenticates and this
    tool is not required.
    """
    try:
        session_id = await session_manager.create(username, password)
    except LifeConnectAuthError:
        return {"error": "Invalid username or password"}
    except ConnectionError as err:
        return {"error": str(err)}
    except RuntimeError as err:
        return {"error": str(err)}
    return {"session_id": session_id, "username": username}


@mcp.tool()
async def logout(session_id: str = "") -> dict:
    """Log out and invalidate the session.

    Cancels background polling and frees all server-side resources.
    When a default session is configured (via env vars), calling this
    without a ``session_id`` will log out the default session.
    """
    sid = session_id or session_manager._default_session_id
    if sid is None:
        return {"error": "Session not found"}
    removed = await session_manager.remove(sid)
    if not removed:
        return {"error": "Session not found"}
    return {"message": "Logged out successfully"}


@mcp.tool()
async def auto_login() -> dict:
    """Return the default session ID, creating one from environment variables if needed.

    If ``MCP_CONNECTLIFE_USERNAME`` and ``MCP_CONNECTLIFE_PASSWORD`` are
    configured, the server ensures a default session exists (re-authenticating
    if necessary) and returns its ID.

    Returns ``error`` when no default credentials are configured.
    """
    if session_manager._default_credentials is None:
        return {
            "error": "No credentials configured. Set MCP_CONNECTLIFE_USERNAME and "
            "MCP_CONNECTLIFE_PASSWORD environment variables, or call login() first."
        }

    try:
        session = await session_manager.resolve_session(None)
    except SessionError as err:
        return {"error": str(err)}
    except Exception as err:
        return {"error": str(err)}
    return {"session_id": session.session_id}


@mcp.tool()
async def whoami(session_id: str = "") -> dict:
    """Return information about the current session.

    Includes username, session age, and number of linked appliances.
    When a default session is configured, calling this without a
    ``session_id`` returns info for the default session.
    """
    try:
        session = await session_manager.resolve_session(session_id or None)
    except SessionError as err:
        return {"error": str(err)}
    return {
        "username": session.username,
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "last_used": session.last_used.isoformat(),
        "appliance_count": len(session.appliances),
    }
