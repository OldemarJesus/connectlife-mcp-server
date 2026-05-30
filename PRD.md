# ConnectLife MCP Server — Product Requirements Document

> AI-relevant orientation: this file explains WHAT the product is, WHO it is for, and WHY it exists. For implementation details (modules, data flow, threading model), see `ARCH.md`. For open work, see `AGENDA.md`.

---

## 1. Overview

**Product Name:** ConnectLife MCP Server  
**Tagline:** Standalone MCP server that exposes ConnectLife smart appliance control as HTTP tools.  
**Repository:** `github-repos/connectlife-mcp`

This project was inspired by and initially based on the ConnectLife integration for Home Assistant by [oyvindwe](https://github.com/oyvindwe/connectlife-ha.git). Where that project is a Home Assistant custom component, this product is a **stand-alone, containerised MCP server** with no dependency on Home Assistant.

---

## 2. Target Users

| Persona | Context | How they interact |
|---------|---------|-------------------|
| AI Agent / LLM Backend | Needs to control smart appliances via tool calls | Calls MCP tools over HTTP |
| Developer / Tinkerer | Wants to script appliance behaviour outside Home Assistant | Runs container locally, hits `/mcp` endpoint |
| DevOps / Platform Engineer | Needs a stateless, horizontally-scalable IoT bridge | Deploys container image to K8s / Docker Swarm |

---

## 3. Value Proposition

1. **Protocol-native:** Speaks the Model Context Protocol (MCP) natively so LLM frameworks (Claude Desktop, Copilot Chat, etc.) can discover and invoke tools automatically.
2. **Credential-safe:** Supports environment-variable auto-login so passwords never travel through tool-call telemetry.
3. **Container-first:** Single rootless image, no host dependencies, runs under Docker/Podman without privileges.
4. **Multi-tenant capable:** Optional explicit session model supports testing, shared servers, or per-user contexts.

---

## 4. Functional Requirements

### 4.1 Authentication
- **FR-A1** The server MUST support automatic login from `MCP_CONNECTLIFE_USERNAME` and `MCP_CONNECTLIFE_PASSWORD` environment variables on startup.
- **FR-A2** When auto-login env vars are absent, the server MUST provide a `login` tool that returns a `session_id`.
- **FR-A3** The server MUST re-authenticate silently when the ConnectLife token expires (default session only).
- **FR-A4** Only username + password authentication is supported; SSO (Google, Apple) is explicitly out of scope.

### 4.2 Session Management
- **FR-S1** Default sessions MUST persist for the lifetime of the container and never idle-expire.
- **FR-S2** Explicit sessions MUST expire after `CONNECTLIFE_SESSION_TTL` seconds of inactivity.
- **FR-S3** The server MUST enforce a maximum concurrent session limit (`CONNECTLIFE_MAX_SESSIONS`).
- **FR-S4** Each active session MUST maintain a background polling task that refreshes appliance state every `CONNECTLIFE_POLL_INTERVAL` seconds.

### 4.3 Appliance Control (Tools)
- **FR-T1** `list_appliances` — return all linked appliances with metadata (id, name, model, online state).
- **FR-T2** `get_appliance` — return metadata for a single appliance by `device_id`.
- **FR-T3** `get_status` — return the full raw property map for an appliance.
- **FR-T4** `get_daily_energy` — return today’s energy consumption in kWh (nullable if unsupported).
- **FR-T5** `update_property` — write a single property value (stringly typed, optimistic local update).
- **FR-T6** `update_properties` — write multiple property values in a single API call.
- **FR-T7** All state-mutating tools MUST perform an optimistic local update so subsequent reads reflect the change before the next poll cycle.
- **FR-T8** When a default session is active, `session_id` MUST be optional for every tool.

### 4.4 Deployment
- **FR-D1** The server MUST ship as an OCI image runnable with `docker run` or `podman run`.
- **FR-D2** The image MUST run as a non-root user (`uid 1000`).
- **FR-D3** The server MUST expose a `GET /health` endpoint for container orchestration health checks.
- **FR-D4** Bind host and port MUST be configurable via `FASTMCP_HOST` and `FASTMCP_PORT`.

---

## 5. Non-Functional Requirements

| ID | Requirement | How Measured |
|----|-------------|--------------|
| NFR-1 | Stateless container — no required host volumes | Image runs without `-v` flags |
| NFR-2 | Telemetry-safe credentials | Password never appears in tool-call parameters when env vars are used |
| NFR-3 | Graceful degradation | If ConnectLife API is unreachable, server stays up and returns errors via tool results, not crashes |
| NFR-4 | Resource bounded | `MAX_SESSIONS` + TTL prevents unbounded memory growth |
| NFR-5 | Python 3.13+ compatibility | CI matrix / local test on `3.13` |

---

## 6. Out of Scope (Explicitly)

- Home Assistant integration or custom component packaging.
- SSO authentication methods (Google, Apple, Facebook).
- Real-time bidirectional push from appliances (poll-only until ConnectLife offers webhooks).
- Discovery mechanism beyond `list_appliances`.
- On-device rule engine or automation scheduler.

---

## 7. Dependencies

| Package | Version Constraint | Role |
|---------|-------------------|------|
| `fastmcp` | `>=3.2.0` | MCP protocol server framework |
| `connectlife` | `>=0.7.1` | Third-party ConnectLife API client (community) |
| `starlette` | transitive | HTTP request/response utilities |

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `connectlife` PyPI package breaks API | Medium | High | Pin upper bound in `pyproject.toml`; vendor fork if needed |
| ConnectLife cloud API rate-limits | Medium | Medium | Exponential backoff in poll loop; configurable poll interval |
| Token expiry during active tool call | Low | Medium | `resolve_session` re-authenticates default session on demand |
| Credential leakage in LLM logs | Low | High | Document env-var auth as default; warn against `login` tool for production |

---

*Last updated: 2026-05-30*
