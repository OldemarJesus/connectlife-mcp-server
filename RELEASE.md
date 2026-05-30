# Release Management & Versioning

This project follows [Semantic Versioning 2.0.0](https://semver.org/) (SemVer).

---

## Version Format

```
MAJOR.MINOR.PATCH
```

| Position | Name     | When to bump                                                                |
|----------|----------|------------------------------------------------------------------------------|
| First    | **MAJOR** | Breaking changes — incompatible API changes, removed/renamed tools, changed config schema, dropped Python version support. |
| Second   | **MINOR** | New features — new tools, new capabilities, additive API changes, new environment variables, new optional parameters. |
| Third    | **PATCH** | Bug fixes — backwards-compatible fixes, security patches, documentation corrections, internal refactors with no user-visible change. |

### Examples for this project

| Scenario                                      | Version change |
|-----------------------------------------------|----------------|
| Fix a bug in `get_status` cache handling      | `1.0.1`        |
| Add `get_weekly_energy` tool                  | `1.1.0`        |
| Rename `update_property` → `set_property`     | `2.0.0`        |
| Add support for a new ConnectLife auth method | `1.2.0`        |
| Security patch in token handling              | `1.0.2`        |

---

## Commit Convention → Version Mapping

This project uses [Conventional Commits](https://www.conventionalcommits.org/). Each prefix maps directly to a SemVer bump:

| Prefix       | SemVer impact | Description                                                |
|--------------|---------------|------------------------------------------------------------|
| `feat:`      | **MINOR**     | New tool, new capability, additive API change              |
| `fix:`       | **PATCH**     | Bug fix                                                    |
| `docs:`      | **PATCH**     | Documentation-only change                                  |
| `refactor:`  | **PATCH**     | Code change with no user-visible behavioral change         |
| `test:`      | *(none)*      | Adding or updating tests                                   |
| `chore:`     | *(none)*      | Dependency updates, CI tweaks, build changes               |
| `perf:`      | **PATCH**     | Performance improvement (no API change)                    |
| `BREAKING CHANGE:` / `!` | **MAJOR** | Incompatible change — always document in commit footer     |

> **Commit message with breaking change:**
> ```
> feat!: remove legacy login tool
>
> BREAKING CHANGE: The legacy `login` tool has been removed. Use env-var auth instead.
> ```

---

## Release Workflow

### 1. Automated container releases (GHCR)

Pushing a Git tag `v*` (e.g., `v1.0.0`) automatically triggers the [publish-ghcr.yaml](.github/workflows/publish-ghcr.yaml) workflow, which:

- Builds and pushes the multi-platform container image to `ghcr.io/<owner>/connectlife-mcp-server`
- Generates SBOM and provenance attestations
- Tags the image with the version and `latest`

### 2. Automated PyPI releases

Creating a GitHub Release (or pushing a version tag) triggers the [publish-pypi.yaml](.github/workflows/publish-pypi.yaml) workflow, which:

- Builds the Python wheel and source distribution
- Publishes to [PyPI](https://pypi.org/project/connectlife-mcp-server/) using OIDC trusted publishing

### 3. Manual release checklist

If creating a release manually rather than via CI:

1. **Bump version** in:
   - `src/connectlife_mcp/__init__.py` — `__version__`
   - `pyproject.toml` — `version` field (kept in sync for visibility)
2. **Update `RELEASE.md`** — add a dated entry to the [Changelog](#changelog) below.
3. **Commit**: `git commit -am "release: v1.X.Y"`
4. **Tag**: `git tag -a v1.X.Y -m "Release v1.X.Y"`
5. **Push**: `git push origin main && git push origin v1.X.Y`
6. **GitHub Release**: Create a release from the tag with auto-generated notes.

---

## Changelog

### 1.0.0 — 2026-05-30

- **Initial stable release** following Semantic Versioning.
- Established release management guidelines (`RELEASE.md`).
- Added automated PyPI publishing via GitHub Actions.
- Added version constant (`__version__`) for programmatic access.
