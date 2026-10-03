#!/bin/bash
# All checks are blocking; synthetic fixtures only.
set -euo pipefail
cd "$(dirname "$0")/.."
UV_BIN="${UV_BIN:-uv}"
"$UV_BIN" sync --frozen --all-extras
"$UV_BIN" run --frozen ruff check .
"$UV_BIN" run --frozen ruff format --check .
"$UV_BIN" run --frozen mypy src/
"$UV_BIN" run --frozen bandit -r src/ -q
"$UV_BIN" run --frozen pytest
"$UV_BIN" run --frozen python scripts/check_critical_coverage.py
"$UV_BIN" build --no-sources
"$UV_BIN" run --frozen twine check dist/*
