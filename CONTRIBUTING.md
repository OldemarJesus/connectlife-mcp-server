# Contributing to ConnectLife MCP Server

Thank you for your interest in improving this project! Whether you're fixing a bug, adding a feature, or improving documentation, we appreciate your time.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Code Style](#code-style)
- [Testing](#testing)
- [Adding a New Tool](#adding-a-new-tool)
- [Pull Request Checklist](#pull-request-checklist)
- [Reporting Issues](#reporting-issues)
- [Security](#security)
- [Community Guidelines](#community-guidelines)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/<owner>/connectlife-mcp.git
cd connectlife-mcp

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# 3. Install in editable mode with dev dependencies
pip install -e ".[dev]"

# 4. Run the server locally (requires env vars for auto-login)
python -m connectlife_mcp
```

---

## Development Setup

### Requirements

- **Python:** `>=3.13`
- **Dependencies:** managed via `pyproject.toml`

### IDE / Editor

We recommend VS Code with the following extensions:
- Python
- Pylance
- Ruff

The project uses `ruff` for linting/formatting and `pyright` for type checking — both are enforced in CI.

### Environment Variables for Local Dev

To test with a real ConnectLife account, export:

```bash
export MCP_CONNECTLIFE_USERNAME="your@email.com"
export MCP_CONNECTLIFE_PASSWORD="yourpassword"
```

For safe test mode (no real credentials), leave these unset and use the `login` tool manually.

---

## Project Structure

```
connectlife-mcp/
├── src/connectlife_mcp/          # Main source code
│   ├── __init__.py
│   ├── __main__.py               # Entry point
│   ├── server.py                 # FastMCP singleton + SessionManager
│   ├── session.py                # Session lifecycle + polling
│   └── tools/
│       ├── auth.py               # login / logout / whoami
│       ├── devices.py            # read-only device queries
│       └── commands.py           # write / update commands
├── tests/                        # Test suite (pytest)
├── .github/workflows/            # CI / CD
├── AGENTS.md                     # AI agent instructions
├── ARCH.md                       # Architecture document
├── PRD.md                        # Product requirements
├── pyproject.toml                # Project metadata + tool config
└── Dockerfile                    # Container image
```

- **Architecture decisions** live in `ARCH.md`
- **Product requirements** live in `PRD.md`
- **AI-agent instructions** (coding conventions) live in `AGENTS.md`

---

## Code Style

We enforce style automatically via CI. Run the same checks locally before pushing:

```bash
# Lint + format check
ruff check src tests
ruff format --check src tests

# Type check
pyright

# Run tests with coverage
pytest

# Security scan
bandit -r src
```

### Key Conventions

1. **Python 3.13+ features** are encouraged (modern syntax, `async`/`await`).
2. **Type hints** should be used on all public functions.
3. **Docstrings** are required on every `@mcp.tool()` function — FastMCP uses them as tool descriptions.
4. **Return contract:** All tool functions return a `dict`. Never raise exceptions across the MCP boundary.
5. **Session resolution pattern:** Every tool starts with:
   ```python
   try:
       session = await session_manager.resolve_session(session_id or None)
   except SessionError as err:
       return {"error": str(err)}
   ```
6. **Logging:** Use the module-level `_LOGGER` with appropriate levels (`INFO`, `WARNING`, `DEBUG`).
7. **Error format:** Always return `{"error": "human-readable message"}` on failures.

See `AGENTS.md` for the full coding conventions used by AI agents in this repo.

---

## Testing

We use `pytest` with `pytest-asyncio` and `pytest-cov`.

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov-report=term-missing

# Run a specific test file
pytest tests/test_session.py
```

### Writing Tests

- All new tools should have corresponding tests in `tests/`.
- Use `respx` for mocking HTTP calls to the ConnectLife API.
- Keep tests isolated — do not rely on external network calls or real credentials.
- Aim to maintain or improve the current coverage threshold (configured in `pyproject.toml`).

---

## Adding a New Tool

1. **Choose the right module:**
   - Read-only queries → `src/connectlife_mcp/tools/devices.py`
   - Write / mutating → `src/connectlife_mcp/tools/commands.py`
   - Auth-related → `src/connectlife_mcp/tools/auth.py`

2. **Implement the tool:**
   ```python
   from ..server import mcp, session_manager

   @mcp.tool()
   async def my_tool(session_id: str = "", ...) -> dict:
       """Human-readable description used by MCP clients."""
       try:
           session = await session_manager.resolve_session(session_id or None)
       except SessionError as err:
           return {"error": str(err)}
       # ... tool logic ...
   ```

3. **Update docs:**
   - Add the tool to the README table.
   - If it changes product scope, update `PRD.md`.

4. **Add tests:**
   - Create or extend the relevant `test_tools_*.py` file.

---

## Pull Request Checklist

Before opening a PR, please make sure:

- [ ] Your branch is up to date with `main`.
- [ ] All CI checks pass (`ruff`, `pyright`, `pytest`, `bandit`).
- [ ] New code has tests (if applicable).
- [ ] Documentation is updated (`README.md`, `PRD.md`, etc., if scope changes).
- [ ] Commit messages are clear and descriptive.
- [ ] No hard-coded secrets or credentials.

### PR Title Format

Use a conventional prefix so changelogs can be generated automatically:

| Prefix | Use when... |
|--------|-------------|
| `feat:` | Adding a new tool or capability |
| `fix:` | Bug fix |
| `docs:` | Documentation-only change |
| `refactor:` | Code change that neither fixes a bug nor adds a feature |
| `test:` | Adding or updating tests |
| `chore:` | Dependency updates, CI tweaks, build changes |

Examples:
- `feat: add get_weekly_energy tool`
- `fix: handle missing appliance in get_status`
- `docs: update README with Podman instructions`

---

## Reporting Issues

### Bug Reports

When reporting a bug, please include:

1. **What you expected to happen**
2. **What actually happened**
3. **Steps to reproduce**
4. **Environment:**
   - Python version (`python --version`)
   - OS / platform
   - Container or native?
   - Server version or commit SHA
5. **Logs or error messages** (redact credentials!)

Use the [Bug report issue template](https://github.com/<owner>/connectlife-mcp/issues/new?template=bug_report.md).

### Feature Requests

When requesting a feature, please include:

1. **Use case** — who needs this and why?
2. **Proposed solution** — how should it work?
3. **Alternatives considered** — what else did you think of?

Use the [Feature request issue template](https://github.com/<owner>/connectlife-mcp/issues/new?template=feature_request.md).

---

## Security

If you discover a security vulnerability, **do not open a public issue**. Instead, email the maintainers directly or use GitHub's private vulnerability reporting feature.

Never commit credentials, session tokens, or API keys to the repository. The CI runs `bandit` to catch common security pitfalls.

---

## Community Guidelines

- Be respectful and constructive in all interactions.
- Assume good intent.
- Focus on what is best for the project and its users.
- We welcome contributors of all experience levels — questions are encouraged!

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see `LICENSE` or `pyproject.toml`).
