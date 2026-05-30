---
name: propose-commit
description: After making code changes, propose the correct git branch, commit message, and PR title/description following this repo's standards.
argument-hint: (optional) brief description of the change, e.g. "add new tool"
allowed-tools: Read Edit Bash(git *) Bash(gh *)
---

After you (the agent) have finished editing files in this workspace, use this skill to propose the correct git workflow — branch name, commit message, and PR — before asking the user to execute commands.

## When to invoke

Invoke this skill **immediately after completing code changes** when:
- The user asked you to implement/fix something and the edits are done.
- There are uncommitted changes in the working tree.
- You want to propose the next step (commit → branch → PR) following repo conventions.

Do **not** invoke if:
- The user explicitly told you to just save files and stop.
- There are no uncommitted changes.

## Step 1 — Inspect the current git state

Run these commands to understand context:

```bash
git status --porcelain          # list modified/new/deleted files
git branch --show-current       # current branch
git remote get-url origin       # repo URL (extract owner if needed)
git log --oneline -n 5          # recent commits for tone reference
```

## Step 2 — Classify the change

Based on the files changed and the nature of the edits, classify using Conventional Commits:

| Prefix | Use when… | Example branch segment |
|--------|-----------|------------------------|
| `feat` | New tool, new capability, additive API | `feature-...` |
| `fix` | Bug fix | `fix-...` |
| `docs` | Documentation-only | `docs-...` |
| `refactor` | Code restructuring, no behavior change | `refactor-...` |
| `test` | New or updated tests | `test-...` |
| `chore` | CI, deps, build, formatting | `chore-...` |
| `perf` | Performance improvement | `perf-...` |

Also determine **scope** if obvious (e.g. `auth`, `devices`, `session`, `ci`).

## Step 3 — Derive branch name

If the **current branch is `main`** (or `master`), propose a **new feature branch**:

```
<github-username>/<type>-<short-description>
```

Rules:
- `<github-username>`: use the repo owner (e.g. `oldemar`) extracted from `git remote get-url origin`.
- `<type>`: `feature` for `feat`, otherwise use the conventional prefix (`fix`, `docs`, `refactor`, `test`, `chore`, `perf`).
- `<short-description>`: 2–5 kebab-case words summarizing the change.

Examples:
- `oldemar/feature-add-weekly-energy-tool`
- `oldemar/fix-session-timeout-edge-case`
- `oldemar/docs-release-management-guide`
- `oldemar/chore-update-ci-actions`

If the **current branch is already a feature branch** (not `main`/`master`), reuse it — do not suggest switching unless the user asks.

## Step 4 — Derive commit message

Propose a single Conventional Commit subject line (≤ 72 chars):

```
<type>(<scope>): <imperative description>
```

- Use the **imperative mood** ("add", "fix", "update", not "added" / "fixes").
- Include scope only if it adds clarity.
- If the change is breaking, append `!` after the type/scope: `feat(auth)!: ...`

Examples:
- `feat: add get_weekly_energy tool`
- `fix(session): handle token expiry during poll`
- `docs: add release management guide`
- `chore(ci): bump actions/checkout to v6`

If the change spans multiple logical concerns, suggest **splitting into multiple commits** instead of one giant commit.

## Step 5 — Derive PR title and description

### PR Title

Use the same Conventional Commit format as the commit subject:

```
<type>(<scope>): <imperative description>
```

### PR Description

Follow the repo's [pull request template](.github/pull_request_template.md). Fill in relevant sections:

```markdown
## Description

<!-- 1–3 sentences summarizing what changed and why. -->

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature / tool (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing behavior to not work as expected)
- [x] Documentation update
- [ ] Refactor / code cleanup
- [ ] Dependency update
- [x] CI / build changes

## Checklist

- [x] My branch is up to date with `main`.
- [x] All CI checks pass (`ruff`, `pyright`, `pytest`, `bandit`).
- [ ] I have added tests that cover my changes (if applicable).
- [x] I have updated relevant documentation (`README.md`, `PRD.md`, etc.) if the product scope changed.
- [x] My commits follow a clear, descriptive style.
- [x] I have verified that no secrets or credentials are present in my changes.

## Testing

<!-- Describe how you tested or validated the change. -->
```

Mark the **Type of Change** and **Checklist** boxes that apply based on the actual edits.

## Step 6 — Present the proposal to the user

Output a concise markdown block:

```markdown
## Proposed git workflow

| Step | Command / Value |
|------|-----------------|
| **Branch** | `oldemar/feature-add-weekly-energy` |
| **Commit** | `feat: add get_weekly_energy tool` |
| **PR title** | `feat: add get_weekly_energy tool` |

### PR description

```markdown
## Description
Add a new `get_weekly_energy` tool that returns...

## Type of Change
- [x] New feature / tool ...
...
```
```

If the user is on `main`, provide the full sequence:

```bash
# 1. Create and switch to feature branch
git checkout -b oldemar/feature-add-weekly-energy

# 2. Stage and commit
git add <files>
git commit -m "feat: add get_weekly_energy tool"

# 3. Push
git push -u origin oldemar/feature-add-weekly-energy

# 4. Open PR
gh pr create --title "feat: add get_weekly_energy tool" --body-file /tmp/pr_body.md
```

If the user is already on a feature branch, provide only:

```bash
git add <files>
git commit -m "feat: add get_weekly_energy tool"
git push
```

> **Ask the user** whether to run these commands or if they'd like to adjust the commit message / branch name first.
