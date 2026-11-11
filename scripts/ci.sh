#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

prepare_mongo_image() {
  docker info --format 'Mongo test Docker kernel: {{.KernelVersion}}'
  docker pull mongo:8.0
  docker run --rm --entrypoint mongosh mongo:8.0 --version
}

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
    case "${2:-}" in
      application|infrastructure|pact-provider|acceptance) prepare_mongo_image ;;
    esac
    uv run --no-sync python -m scripts.run_suite "${2:?Provide domain|application|infrastructure|externalproviders|pact-provider|acceptance}"
    ;;
  pact)
    rm -rf artifacts/verification/pact
    mkdir -p artifacts/verification/pact
    PAYMENTS_PACT_DIR="$PWD/artifacts/verification/pact/pacts" \
      uv run --no-sync pytest tests/unit/external_providers/test_orders_pact.py \
        --junitxml=artifacts/verification/pact/junit.xml
    test -s artifacts/verification/pact/pacts/payments-invoice.json
    test -s artifacts/verification/pact/pacts/manifest.json
    ;;
  build)
    uv build --wheel --no-sources --clear
    uv run --no-sync python scripts/verify_wheel.py
    ;;
  audit)
    uv audit --locked --preview-features audit-command
    ;;
  container)
    prepare_mongo_image
    bash scripts/smoke_container.sh
    ;;
  *)
    echo "Usage: bash scripts/ci.sh {sync|format|lint|types|architecture|orders-client|links|openapi|pact|build|audit|container|suite NAME}" >&2
    exit 2
    ;;
esac
