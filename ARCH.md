# ConnectLife MCP Server — Architecture Document

> AI-relevant orientation: this file explains HOW the system is built — modules, data flow, concurrency model, and deployment. For the product vision, see `PRD.md`. For open work, see `AGENDA.md`.

---

## 1. High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP Client                                   │
│   (Claude Desktop, Copilot Chat, custom script, curl...)            │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ streamable-http
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   ConnectLife MCP Server                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  FastMCP HTTP Router (fastmcp.FastMCP)                         │  │
│  │  • POST /mcp  (MCP protocol endpoint)                          │  │
│  │  • GET  /health (custom_route, starlette)                      │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│         ┌────────────────────┼────────────────────┐                 │
│         ▼                    ▼                    ▼                 │
│  ┌─────────────┐    ┌─────────────┐      ┌─────────────┐           │
│  │  auth tools │    │ device tools│      │ command tools│          │
│  │  auth.py    │    │ devices.py  │      │ commands.py  │          │
│  │  login      │    │ list_...    │      │ update_...   │          │
│  │  logout     │    │ get_...     │      └─────────────┘           │
│  │  whoami     │    │ get_status  │                                │
│  └─────────────┘    │ get_energy  │                                │
│                     └─────────────┘                                │
│                              │                                       │
│                              ▼                                       │
│              ┌───────────────────────────────┐                      │
│              │      SessionManager           │                      │
│              │      session.py               │                      │
│              │  • _sessions: dict[str, Session]                    │
│              │  • asyncio.Lock for mutations │                      │
│              │  • background poll_loop tasks │                      │
│              └───────────────────────────────┘                      │
│                              │                                       │
│                              ▼                                       │
│              ┌───────────────────────────────┐                      │
│              │   connectlife.ConnectLifeApi    │                    │
│              │   (third-party package)         │                    │
│              └───────────────────────────────┘                      │
│                              │                                       │
└──────────────────────────────┼───────────────────────────────────────┘
                               │ HTTPS
                               ▼
                  ┌─────────────────────────┐
                  │   ConnectLife Cloud API  │
                  └─────────────────────────┘
```

---

## 2. Module Breakdown

### 2.1 Entry Point — `__main__.py`

- **Responsibility:** bootstrap logging, initialise the default session, start the FastMCP HTTP server.
- **Key behaviour:**
  - Imports `tools` package solely to trigger `@mcp.tool()` decorator side-effects.
  - Calls `session_manager.init_default_session()` before `mcp.run(transport="http")`.
  - Does **not** block startup if default session init fails — logs exception and continues.
- **Env vars consumed:** `LOG_LEVEL`, `MCP_CONNECTLIFE_USERNAME`, `MCP_CONNECTLIFE_PASSWORD`.

### 2.2 Server Singleton — `server.py`

- **Exports:**
  - `mcp` — single `fastmcp.FastMCP` instance used by all tool modules.
  - `session_manager` — single `SessionManager` instance.
- **Custom routes:**
  - `GET /health` — returns `{"status": "ok"}` (starlette JSONResponse).
- **Why singleton pattern:** FastMCP decorators (`@mcp.tool()`) require a module-level object. Importing `server.py` guarantees the same instance everywhere.

### 2.3 Session Management — `session.py`

- **Core class:** `SessionManager`
- **Data model:** `Session` dataclass
  ```python
  @dataclass
  class Session:
      session_id: str           # token or "__default__"
      username: str
      api: ConnectLifeApi       # mutable reference to live API client
      appliances: dict[str, ConnectLifeAppliance]
      created_at: datetime
      last_used: datetime
      poll_task: asyncio.Task | None   # background poller
  ```
- **Concurrency model:**
  - One `asyncio.Lock` (`self._lock`) protects `_sessions` dict mutations.
  - `get()` is synchronous (assumes dict access is safe for reads; lock not held).
  - `create()` and `remove()` acquire the lock.
  - Each session spawns one long-lived `asyncio.Task` (`_poll_loop`) that refreshes appliance state.
- **Default session lifecycle:**
  1. `init_default_session()` reads env vars → creates session with `session_id = "__default__"`.
  2. On expiry or missing token, `resolve_session()` calls `_relogin_default()` which mutates `session.api` and `session.appliances` in-place under the lock.
  3. Poll loop for default session never self-terminates; it re-authenticates indefinitely.
- **Explicit session lifecycle:**
  1. `login` tool → `SessionManager.create()` → new `Session` + `poll_task`.
  2. TTL check on every `get()`; expired sessions are async-removed.
  3. `logout` tool → `SessionManager.remove()` → cancels `poll_task`, drops from dict.

### 2.4 Tools Packages — `tools/`

All tool modules import `mcp` from `server.py` and register functions with `@mcp.tool()`.

| File | Tools | Write or Read |
|------|-------|---------------|
| `auth.py` | `login`, `logout`, `whoami` | n/a (auth) |
| `devices.py` | `list_appliances`, `get_appliance`, `get_status`, `get_daily_energy` | Read |
| `commands.py` | `update_property`, `update_properties` | Write |

- **Session resolution pattern:** Every tool calls `session_manager.resolve_session(session_id or None)`.
  - If `session_id` is truthy and not `"__default__"`, calls `get()` (validates TTL).
  - If falsy, resolves to default session (auto-relogin on expiry).
- **Error contract:** All tools return `dict`. On failure the dict contains `"error": "<message>"`. Never raises exceptions across the MCP boundary.
- **Optimistic updates:** `commands.py` mutates `appliance.status_list` immediately after a successful API call, so `get_status` reflects the new state without waiting for the next poll.

---

## 3. Data Flow

### 3.1 Read Appliance Status

```
MCP Client
   │ POST /mcp  { "tool": "get_status", "params": { "device_id": "..." } }
   ▼
FastMCP router → dispatches to devices.py::get_status()
   │ await session_manager.resolve_session(None)
   ▼
SessionManager.get("__default__")  or  _relogin_default()
   │
   ▼
Returns Session (with cached appliances dict)
   │
   ▼
Look up appliance in session.appliances → return status_list
   │
   ▼
JSON response to client
```

No ConnectLife cloud call happens on the read path unless the session is expired/default missing.

### 3.2 Write Property

```
MCP Client
   │ POST /mcp  { "tool": "update_property", "params": { "device_id": "...", ... } }
   ▼
FastMCP router → commands.py::update_property()
   │ await session_manager.resolve_session(None)
   ▼
Session + appliance lookup (same as read)
   │
   ▼
api.update_appliance(puid, {property: value})  → HTTPS → ConnectLife Cloud
   │
   ▼
On success: appliance.status_list[property] = value   (optimistic)
   │
   ▼
JSON response to client
```

### 3.3 Background Polling

```
_poll_loop(session_id)
   │ every POLL_INTERVAL_SECONDS (default 60s)
   ▼
session.api.get_appliances()  → HTTPS → ConnectLife Cloud
   │
   ▼
Update session.appliances = {a.device_id: a for a in api.appliances}
   │
   ▼
On LifeConnectAuthError for default session → _relogin_default()
   │
   ▼
On generic exception → _LOGGER.debug(..., exc_info=True)  (swallowed)
```

---

## 4. Concurrency & Threading

- **Runtime:** `asyncio` only — no threading, no multiprocessing.
- **Server:** FastMCP runs on `uvicorn` under the hood (async).
- **Shared mutable state:** `SessionManager._sessions` dict.
  - Reads outside lock (`get()`, `_poll_loop`) are considered safe because:
    - Dict replacements are atomic in CPython.
    - `Session` objects are mutated only under lock or by the owning poll task.
- **Lock granularity:**Coarse — one lock for the whole sessions map. Acceptable because session count is bounded (`MAX_SESSIONS` ≤ 100).

---

## 5. Deployment Architecture

### 5.1 Container Image

- **Builder stage:** `python:3.13-slim`
  - Installs `pip` deps from `pyproject.toml` + `src/`.
- **Runtime stage:** `python:3.13-slim`
  - Copies installed site-packages and the `connectlife-mcp` CLI binary.
  - Creates non-root user `connectlife` (`uid 1000`).
  - Healthcheck hits `GET /health` via `urllib` inside the container.

### 5.2 Network Surface

| Port | Path | Purpose | Auth |
|------|------|---------|------|
| `8000` | `/mcp` | MCP streamable-http endpoint | ConnectLife session |
| `8000` | `/health` | Container orchestration health | None |

### 5.3 Environment Configuration Reference

| Variable | Default | Consumers |
|----------|---------|-----------|
| `FASTMCP_HOST` | `127.0.0.1` | `__main__.py` → `mcp.run()` |
| `FASTMCP_PORT` | `8000` | `__main__.py` → `mcp.run()` |
| `MCP_CONNECTLIFE_USERNAME` | *(none)* | `SessionManager.init_default_session()` |
| `MCP_CONNECTLIFE_PASSWORD` | *(none)* | `SessionManager.init_default_session()` |
| `CONNECTLIFE_SESSION_TTL` | `86400` | `SessionManager.get()`, `_poll_loop()` |
| `CONNECTLIFE_POLL_INTERVAL` | `60` | `_poll_loop()` |
| `CONNECTLIFE_MAX_SESSIONS` | `100` | `SessionManager.create()` |
| `LOG_LEVEL` | `INFO` | `__main__.py` logging setup |

---

## 6. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| FastMCP 3.x + streamable-http | Native MCP protocol with minimal boilerplate; HTTP is firewall-friendly. |
| Stringly-typed `value` in `update_property` | The underlying `connectlife` library accepts strings for all property values; keeping the same contract avoids translation bugs. |
| Optimistic local updates | Reduces latency for read-after-write sequences inside a single conversation turn. |
| Singleton `mcp` + `session_manager` | Required by FastMCP decorator pattern; simplifies inter-module access without heavy DI. |
| Separate `tools/` sub-package | Allows splitting read vs write vs auth tools into independently reviewable files. |
| Default session never expires | Prevents a container that is healthy from becoming useless because an idle default session was evicted. |

---

## 7. Extension Points

If you need to add a new tool:

1. Create or edit a file in `src/connectlife_mcp/tools/`.
2. Import `from ..server import mcp, session_manager`.
3. Define an async function decorated with `@mcp.tool()`.
4. Follow the session resolution pattern:
   ```python
   try:
       session = await session_manager.resolve_session(session_id or None)
   except SessionError as err:
       return {"error": str(err)}
   ```
5. Return a `dict`. On success include the data; on failure include `"error"`.
6. Add the tool to the table in `README.md` and update `PRD.md` if requirements change.

If you need to add a new route (non-MCP):

1. Open `server.py`.
2. Add a new `@mcp.custom_route(...)` decorated async function.

---

*Last updated: 2026-05-30*
