# ConnectLife MCP Server

A standalone [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes ConnectLife smart appliance control as MCP tools over HTTP.

> This project was inspired by and initially based on the ConnectLife integration for Home Assistant by [oyvindwe](https://github.com/oyvindwe/connectlife-ha.git).

It is published as a separate container image to GHCR and has **no dependency on Home Assistant**.

## Quick start (Docker / Podman)

### Recommended: environment variable authentication

The safest and easiest way to run the server is to pass your ConnectLife credentials as environment variables. The server authenticates automatically on startup, so you can call tools directly without a manual `login`.

```bash
# Pull the latest image
docker pull ghcr.io/<owner>/connectlife-mcp-server:latest

# Run with credentials (recommended)
docker run --rm -p 127.0.0.1:8000:8000 \
  -e MCP_CONNECTLIFE_USERNAME="your@email.com" \
  -e MCP_CONNECTLIFE_PASSWORD="yourpassword" \
  ghcr.io/<owner>/connectlife-mcp-server:latest
```

> ⚠️ **Why env vars?** LLM backends (OpenAI, Claude, Copilot, etc.) routinely log the parameters of every tool call. If you use the `login` tool, your username and password may be captured in plaintext in those logs. Passing credentials via environment variables keeps them out of tool-call telemetry.

### Without environment variables (manual login)

If you prefer not to store credentials in env vars, start the container without them and authenticate via the `login` tool each time:

```bash
docker run --rm -p 127.0.0.1:8000:8000 \
  ghcr.io/<owner>/connectlife-mcp-server:latest
```

The server binds to `0.0.0.0:8000` inside the container.

## MCP endpoint

```
http://localhost:8000/mcp
```

Use this URL in your MCP client (e.g., Claude Desktop, Copilot Chat) with transport `streamable-http`.

## Authentication flow

When **environment variables are set**, authentication is fully automatic:

1. The server calls the ConnectLife API on startup.
2. A default session is created and maintained for the lifetime of the container.
3. If the session token expires, the server silently re-authenticates in the background.
4. All tools work without passing a `session_id`.

When **environment variables are NOT set** (multi-tenant or testing mode):

1. Call the `login` tool with your ConnectLife `username` and `password`.
2. Use the returned `session_id` as a parameter in every subsequent tool call.
3. Call `logout` when done to release server resources.

> ⚠️ **Do not expose this server publicly** without an additional authentication proxy.

## Available tools

| Tool | Description |
|---|---|
| `login` | Log in and obtain a `session_id` |
| `logout` | Invalidate a session |
| `whoami` | Return session info |
| `list_appliances` | List all linked appliances |
| `get_appliance` | Get details for one appliance |
| `get_status` | Get all current property values |
| `get_daily_energy` | Get today's energy usage in kWh |
| `update_property` | Update a single property |
| `update_properties` | Update multiple properties at once |

When a default session is configured, the `session_id` parameter is optional for all tools.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `FASTMCP_HOST` | `127.0.0.1` | Bind host (`0.0.0.0` for container use) |
| `FASTMCP_PORT` | `8000` | Bind port |
| `MCP_CONNECTLIFE_USERNAME` | *(none)* | ConnectLife username for auto-login |
| `MCP_CONNECTLIFE_PASSWORD` | *(none)* | ConnectLife password for auto-login |
| `CONNECTLIFE_SESSION_TTL` | `86400` | Session idle TTL in seconds (24 h) |
| `CONNECTLIFE_POLL_INTERVAL` | `60` | Appliance poll interval in seconds |
| `CONNECTLIFE_MAX_SESSIONS` | `100` | Max concurrent sessions |
| `LOG_LEVEL` | `INFO` | Python log level |

## Session lifecycle

- The default auto-login session is created on server startup and persists for the full lifetime of the container.
- If the ConnectLife auth token expires, the server automatically re-authenticates using the stored credentials.
- Each explicit `login` call starts a background polling task that refreshes appliance state every `CONNECTLIFE_POLL_INTERVAL` seconds.
- Explicit sessions expire after `CONNECTLIFE_SESSION_TTL` seconds of inactivity.
- `logout` cancels polling immediately.

## Credentials

- Only **username + password** login is supported — the same restriction as the Home Assistant integration.
- SSO (Google, Apple, etc.) is **not** supported.
- If you use SSO, create a separate ConnectLife account and share your devices with it.

## Rootless container

The image runs as a non-root user (`uid 1000`). It is compatible with rootless Docker and Podman without any special configuration.

```bash
# Podman rootless example with env vars
podman run --rm -p 127.0.0.1:8000:8000 \
  -e MCP_CONNECTLIFE_USERNAME="your@email.com" \
  -e MCP_CONNECTLIFE_PASSWORD="yourpassword" \
  ghcr.io/<owner>/connectlife-mcp-server:latest
```

## Building locally

```bash
cd mcp_server
docker build -t connectlife-mcp-server .
docker run --rm -p 127.0.0.1:8000:8000 \
  -e MCP_CONNECTLIFE_USERNAME="your@email.com" \
  -e MCP_CONNECTLIFE_PASSWORD="yourpassword" \
  connectlife-mcp-server
```

## Versioning

This project follows [Semantic Versioning 2.0.0](https://semver.org/):

| Change type | Version bump | Example |
|-------------|--------------|---------|
| Bug fix | **PATCH** (`x.x.Y`) | `1.0.1` |
| New tool or feature | **MINOR** (`x.Y.0`) | `1.1.0` |
| Breaking change | **MAJOR** (`Y.0.0`) | `2.0.0` |

See [`RELEASE.md`](RELEASE.md) for the full release policy and automation details.
