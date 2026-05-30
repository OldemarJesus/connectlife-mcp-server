---
name: bump-version
description: Bump the version, create a branch, commit, push, and open a PR.
argument-hint: <version>
allowed-tools: Read Edit Bash(git *) Bash(gh *) Bash(uv sync)
---

Bump the version of this ConnectLife MCP Server.

## Steps

1. Determine the new version:
   - If `$ARGUMENTS` is provided, it must be a valid semver version (e.g., `1.2.0`). Use it as the new version.
   - If not provided, determine the next version via semver by analyzing commits since the last release:
     1. Read the current version from `src/connectlife_mcp/__init__.py` (`__version__`) and `pyproject.toml`.
     2. List commits since the last version bump:
        ```
        git log --oneline "$(git log --grep='^release:' -n 1 --format=%H)..HEAD"
        ```
        (Falls back to `git log --oneline -n 20` if no prior version commit is found.)
     3. Classify the bump based on the commit subjects and diffs. **This project is on `1.x.y` and follows strict SemVer.**
        - **MAJOR** (`X.0.0`): breaking changes — renamed/removed tools, incompatible config schema changes, dropped Python version support, changed default behavior that breaks existing usage.
        - **MINOR** (`x.Y.0`): new tools, new capabilities, additive API changes, new environment variables, new optional parameters, new features.
        - **PATCH** (`x.x.Z`): bug fixes, backwards-compatible fixes, documentation corrections, internal refactors with no user-visible change, performance improvements.
        When in doubt between MINOR and PATCH, pick MINOR.
     4. Compute the next version and show the user: the current version, the classification (major/minor/patch) with a one-line justification referencing the commits, and the proposed new version. Ask for confirmation before proceeding.

2. Verify the working tree is clean:
   ```
   git status --porcelain
   ```
   If there are uncommitted changes, stop and tell the user.

3. Make sure main is up to date:
   ```
   git checkout main
   git pull
   ```

4. Create a version branch:
   ```
   git checkout -b bump/v<new_version>
   ```

5. Update the version in these files:
   - `src/connectlife_mcp/__init__.py` — `__version__`
   - `pyproject.toml` — `version` field

6. Run `uv sync` (or `pip install -e ".[dev]"`) to ensure lock files are up to date.

7. Stage and commit:
   ```
   git add src/connectlife_mcp/__init__.py pyproject.toml
   git commit -m "release: v<new_version>"
   ```

8. Push and create PR:
   ```
   git push -u origin bump/v<new_version>
   gh pr create --title "release: v<new_version>" --body "Bump version to v<new_version>."
   ```

9. Report the PR URL to the user.
