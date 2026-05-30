---
name: venv-setup
description: Ensure a Python virtual environment exists in this repo and is used before running tests, installing dependencies, or executing Python code.
argument-hint: (optional) action to perform — "check", "create", or "install-deps"
allowed-tools: Bash(python*) Bash(pip*) Read Edit
tags: [python, venv, setup, dependencies]
---

Before running tests, installing packages, or executing any Python code in this workspace, ensure a Python virtual environment is configured and active.

## When to invoke

Invoke this skill **before any Python-related operation** when:
- The user asks to run tests (`pytest`).
- The user asks to install dependencies (`pip install`).
- The user asks to run the server or any Python script.
- You detect that `.venv/` does not exist or Python commands are using the system interpreter.

Do **not** invoke if:
- The user explicitly says they already activated a venv and you confirmed it.

## Requirements

- This project requires **Python 3.13+**.
- The virtual environment must live at `.venv/` in the repo root.
- All `python` and `pip` commands must use the venv interpreter after setup.

## Step 1 — Check existing environment

Run these commands (repo root) to determine the current state:

```bash
ls -la .venv/bin/python 2>/dev/null || echo "NO_VENV"
python3 --version
python3 -m pip --version
```

If `.venv/bin/python` exists, retrieve its version:

```bash
.venv/bin/python --version
```

## Step 2 — Create venv if missing

If `NO_VENV` or the directory does not exist:

```bash
# Ensure Python 3.13+ is available
python3 --version  # verify ≥ 3.13

# Create the virtual environment
python3 -m venv .venv
```

If Python < 3.13 is the default, attempt to find a newer interpreter:

```bash
python3.13 --version || python3.14 --version
```

Then create the venv with the correct binary:

```bash
python3.13 -m venv .venv  # or python3.14, etc.
```

## Step 3 — Use venv for all subsequent commands

After `.venv/` exists, **always** use the venv interpreter explicitly. Do **not** rely on global `python` or `pip`.

| Global command | Venv equivalent |
|----------------|-----------------|
| `python …` | `.venv/bin/python …` |
| `pip install …` | `.venv/bin/pip install …` |
| `pytest …` | `.venv/bin/python -m pytest …` |
| `python -m connectlife_mcp` | `.venv/bin/python -m connectlife_mcp` |

## Step 4 — Install dependencies (when needed)

If `pyproject.toml` or a lock file changed, or on first setup:

```bash
.venv/bin/pip install -e ".[dev]"   # editable install with dev extras
```

If a plain install is sufficient:

```bash
.venv/bin/pip install -e .
```

## Step 5 — Verify the setup

Confirm the environment works:

```bash
.venv/bin/python --version
.venv/bin/python -c "import connectlife_mcp; print('OK')"
```

## Rationale

- Isolates project dependencies from the system Python.
- Prevents permission issues with system-site-packages.
- Ensures reproducible builds and CI parity.
- The `.venv/` path is git-ignored by convention and matches many tooling defaults.
