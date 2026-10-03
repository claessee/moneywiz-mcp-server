.PHONY: install test lint format type-check security build ci-local
install:
	uv sync --frozen --all-extras
test:
	uv run --frozen pytest
lint:
	uv run --frozen ruff check .
format:
	uv run --frozen ruff format .
type-check:
	uv run --frozen mypy src/
security:
	uv run --frozen bandit -r src/
	uv run --frozen pip-audit --local --skip-editable
build:
	uv build --no-sources
	uv run --frozen twine check dist/*
ci-local:
	./scripts/check-ci.sh
