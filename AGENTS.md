# ConnectLife MCP Server — Agent Instructions

> These instructions automatically apply to all AI agents working in this workspace. For product requirements, see `PRD.md`. For architecture details, see `ARCH.md`.

---

## Project Origin

This project was inspired by and initially based on the ConnectLife integration for Home Assistant by [oyvindwe](https://github.com/oyvindwe/connectlife-ha.git). It re-uses the underlying `connectlife` PyPI package but exposes control as a standalone MCP server over HTTP.

---

## Code Style

- **Python:** `3.13+`, strict type hints encouraged, `async`/`await` throughout.
- **Return contract:** All `@mcp.tool()` functions return a `dict`. Never raise exceptions across the MCP boundary.
- **Session resolution pattern:** Every tool starts with:
  ```python
  try:
      session = await session_manager.resolve_session(session_id or None)
  except SessionError as err:
      return {"error": str(err)}
  ```
- **Logging:** Use the module-level `_LOGGER` (from `logging.getLogger(__name__)`). Levels:
  - `INFO` — session creation, removal, re-authentication.
  - `WARNING` — auth expiry during poll.
  - `DEBUG` — poll failures, internal cache hits/misses.
- **Docstrings:** Every tool has a docstring; FastMCP uses it as the tool description exposed to clients.

---

## Architecture

- **Server singleton:** `src/connectlife_mcp/server.py` exports `mcp` (FastMCP instance) and `session_manager` (SessionManager). All tool modules import from here.
- **Tool registration:** `src/connectlife_mcp/__main__.py` imports `tools` solely to trigger `@mcp.tool()` decorators. No explicit registration needed.
- **Session lifecycle:** See `src/connectlife_mcp/session.py`.
  - `SessionManager` holds `_sessions: dict[str, Session]` protected by an `asyncio.Lock`.
  - Default session (`__default__`) auto-re-authenticates on expiry; explicit sessions TTL-out.
  - Each session has a background `asyncio.Task` (`_poll_loop`) that refreshes appliance state.
- **Tool modules (read/write split):**
  - `tools/devices.py` — read-only: `list_appliances`, `get_appliance`, `get_status`, `get_daily_energy`
  - `tools/commands.py` — write: `update_property`, `update_properties` (optimistic local update after success)
  - `tools/auth.py` — auth: `login`, `logout`, `whoami`

---

## Build and Test

```bash
# Install in editable mode
pip install -e .

# Run the server locally (requires env vars for auto-login)
python -m connectlife_mcp

# Build container image
docker build -t connectlife-mcp-server .
```

> There is no test suite yet. If you add tests, place them in `tests/` and use `pytest`. Update these instructions.

---

## Conventions

1. **Environment variables for secrets only:** ConnectLife credentials (`MCP_CONNECTLIFE_USERNAME`, `MCP_CONNECTLIFE_PASSWORD`) MUST be read via `os.environ.get()` in `session.py`, never hard-coded or passed through tool parameters in production.
2. **Optimistic updates:** After a successful `api.update_appliance()`, immediately mutate `appliance.status_list[property_name] = value` so subsequent `get_status` calls reflect the change before the next poll.
3. **Session ID optional when default is configured:** All tool signatures define `session_id: str = ""`; tools resolve to the default session when the parameter is falsy.
4. **Error dictionary format:** On any failure, return `{"error": "human-readable message"}`. Do not leak stack traces or internal identifiers to the MCP client.
5. **Container-first:** The server binds to `0.0.0.0` inside the container (`FASTMCP_HOST` env var). Keep the rootless Dockerfile (`uid 1000`) unchanged unless security requirements shift.
6. **Third-party API client:** Do not modify `connectlife` package internals. If the package breaks, pin or vendor it — do not monkey-patch.

---

## Adding a New Tool

1. Choose the appropriate sub-module under `src/connectlife_mcp/tools/` (read → `devices.py`, write → `commands.py`, auth → `auth.py`).
2. Import `from ..server import mcp, session_manager`.
3. Define `async def my_tool(session_id: str = "", ...) -> dict:` decorated with `@mcp.tool()`.
4. Resolve session, look up appliance (if needed), call API, handle errors, return dict.
5. Update `README.md` tool table, `ARCH.md` §2.4 tools table, and `PRD.md` §4.3 requirements if product scope changes. Use the `update-docs` skill to stay consistent.
