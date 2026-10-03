# Publishing checklist

This repository is a maintained derivative of `jcvalerio/moneywiz-mcp-server`. Keep the full Git history and upstream attribution visible.

## Repository settings

Recommended GitHub description:

> Unofficial, permanently read-only MCP v2 server for local MoneyWiz data on macOS, with dynamic Core Data schema discovery and deterministic financial semantics.

Recommended topics:

`mcp`, `model-context-protocol`, `moneywiz`, `personal-finance`, `sqlite`, `macos`, `python`, `read-only`, `mcp-server`

Enable Issues and GitHub Actions. GitHub Discussions are optional. Enable private vulnerability reporting if available before inviting security reports.

## Before making the repository public

Confirm:

- `README.md`, `ATTRIBUTION.md`, `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, and `CODE_OF_CONDUCT.md` are present.
- package/version metadata says `2.0.0`.
- all client examples contain generic paths only.
- no real MoneyWiz database, WAL/SHM file, financial export, reconciliation JSON, account data, credentials, or private local paths are tracked.
- the locked quality suite passes on the exact public release commit.
- the release commit still contains the upstream Git history.

## Final quality commands

```sh
uv lock --check
uv run --frozen pytest
uv run --frozen python scripts/check_critical_coverage.py
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy src/
uv run --frozen bandit -r src/
uv run --frozen pip-audit --local --skip-editable
uv build --no-sources
uv run --frozen twine check dist/*
git diff --check
```

If `pyproject.toml` was changed after the current lock was generated, refresh `uv.lock` deliberately before the final check and review the resulting dependency diff.

## GitHub release

After the intended release commit passes all checks, tag it as `v2.0.0` and create a GitHub Release using [`RELEASE_NOTES_v2.0.0.md`](RELEASE_NOTES_v2.0.0.md).

Do not publish this derivative under the upstream PyPI project identity. The existing distribution name originated with the upstream project. GitHub source/releases are sufficient unless a distinct package identity is selected later.

## Artwork

The README artwork is stored under [`assets/`](assets/):

- `moneywiz-mcp-hero.svg`
- `moneywiz-mcp-icon.svg`

The artwork is original to this repository and does not reproduce the MoneyWiz/SILVERWIZ logo or trade dress.

## Attribution

Do not remove upstream history or attribution when publishing. See [`../ATTRIBUTION.md`](../ATTRIBUTION.md).

## Trademark statement

MoneyWiz™ is a registered trademark and property of SILVERWIZ LLC. The project must remain clearly described as independent and unofficial.