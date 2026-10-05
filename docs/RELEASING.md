# Releasing

The maintained 2.x line is a breaking, hardened continuation of the upstream 1.x project. Version 2.0.0 is the first public release of this line.

## Before a release

Run the complete locked quality suite:

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

Confirm that documentation matches the actual MCP tool surface and configuration. Review `git status` and ensure no real database, reconciliation output, financial CSV, credentials, private local paths, or other personal financial material is tracked.

For changes that affect MoneyWiz schema interpretation, monetary calculations, transaction classification, date semantics, or balances, repeat a focused independent comparison with MoneyWiz itself.

## Versioning

Use semantic versioning for the public 2.x line.

A major release is appropriate for incompatible MCP tool/configuration contracts or fundamental financial semantics changes. A minor release may add backwards-compatible tools or supported schema capabilities. A patch release should contain compatible fixes, documentation, or hardening.

The MCP SDK version is independently pinned in `pyproject.toml` and `uv.lock`.

## GitHub release

After all checks pass on the intended release commit:

```sh
git tag -a v2.1.0 -m "MoneyWiz MCP Server v2.1.0"
git push origin main
git push origin v2.1.0
```

Then create a GitHub Release from the tag and use `docs/RELEASE_NOTES_v2.1.0.md` as the basis for the release notes. Tagging and publishing a GitHub Release are separate from committing and pushing source updates.

Do not publish to the upstream PyPI project from this repository. The distribution name `moneywiz-mcp-server` originated with the upstream project. GitHub source/releases are sufficient for this maintained derivative unless a distinct PyPI distribution identity is deliberately chosen later.

## Rollback

Do not modify a MoneyWiz database to accommodate the adapter. If a release introduces a regression, return to a previously reconciled tag/commit, restore its locked environment, and restart the MCP client.

Unsupported new MoneyWiz schema observations should be handled with evidence, explicit schema errors, and regression tests rather than compatibility guesses.
