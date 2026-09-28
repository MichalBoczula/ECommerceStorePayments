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
  architecture)
    uv run --no-sync python scripts/check_architecture.py
    ;;
  orders-client)
    bash scripts/check_orders_client.sh
    ;;
  links)
    uv run --no-sync python scripts/generate_operation_links.py --check
    ;;
  openapi)
    uv run --no-sync python -m scripts.export_openapi
    ;;
  suite)
    uv run --no-sync python -m scripts.run_suite "${2:?Provide domain|application|infrastructure|externalproviders|acceptance}"
    ;;
  build)
    uv build --wheel --no-sources --clear
    uv run --no-sync python scripts/verify_wheel.py
    ;;
  *)
    echo "Usage: bash scripts/ci.sh {sync|format|lint|types|architecture|orders-client|links|openapi|build|suite NAME}" >&2
    exit 2
    ;;
esac
