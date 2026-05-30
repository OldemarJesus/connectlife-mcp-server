---
name: update-docs
description: Update README, ARCH, PRD, AGENTS, and tests when MCP tools change.
argument-hint: (optional) tool or change summary
allowed-tools: Read Edit Bash(git diff --stat)
tags: [documentation, tools]
---
# Skill: Update Documentation for New Tools

## When to invoke

Whenever a new `@mcp.tool()` is added, modified, or removed in `src/connectlife_mcp/tools/`, this skill ensures all product artefacts stay in sync.

## Checklist

1. **README.md** — Update the "Available tools" table:
   - Add / remove the tool row.
   - Keep rows alphabetically sorted by tool name.
   - For auth tools, mention `auto_login` behaviour in the "Authentication flow" section if relevant.

2. **ARCH.md** — Update the "Tools Packages" table in §2.4:
   - List the new tool under the correct file.
   - If the tool is a new category, add a new row or file reference.

3. **PRD.md** — Add or update Functional Requirements in §4.3:
   - Assign the next `FR-Tn` ID.
   - Describe what the tool does, its parameters, and its return value.
   - Mention optimistic-update behaviour if it is a write tool.
   - Mention `session_id` optional behaviour if default-session aware.

4. **AGENTS.md** — If the new tool changes coding patterns (e.g. new error format, new session resolution pattern), update §"Adding a New Tool".

5. **Tests** — Ensure a corresponding test module exists under `tests/`. See existing `test_tools_*.py` files as templates.

## Return format

After editing, produce the list of files changed and a one-line diff summary (`git diff --stat`).
