#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

case "${1:-}" in
  sync)
    uv lock --check
    uv sync --locked --all-groups
    ;;
  format)
    uv run --no-sync ruff format --check .
    ;;
  lint)
    uv run --no-sync ruff check .
    ;;
  types)
    uv run --no-sync pyright
    ;;
  test)
    uv run --no-sync pytest tests/unit
    ;;
  integration)
    uv run --no-sync pytest tests/integration
    ;;
  acceptance)
    uv run --no-sync pytest tests/acceptance
    ;;
  build)
    uv build --wheel --no-sources --clear
    uv run --no-sync python scripts/verify_wheel.py
    ;;
  *)
    echo "Usage: bash scripts/ci.sh {sync|format|lint|types|test|integration|acceptance|build}" >&2
    exit 2
    ;;
esac
