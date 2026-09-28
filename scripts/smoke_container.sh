#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
project="payments-smoke-${GITHUB_RUN_ID:-local}-$$"
compose=(docker compose -p "$project" -f compose.yaml)

cleanup() {
  result=$?
  if (( result != 0 )); then
    "${compose[@]}" ps -a || true
    "${compose[@]}" logs --no-color api mongo-init || true
  fi
  "${compose[@]}" down --volumes --remove-orphans
}
trap cleanup EXIT

"${compose[@]}" up --build -d --wait --wait-timeout 180
address="$("${compose[@]}" port api 8080)"
base_url="http://$address"

curl --fail --silent --show-error "$base_url/health/live" > /dev/null
curl --fail --silent --show-error "$base_url/health/ready" > /dev/null
curl --fail --silent --show-error "$base_url/openapi.json" > /dev/null
test "$("${compose[@]}" exec -T api id -u | tr -d '\r')" = 10001
"${compose[@]}" exec -T api python -c 'import importlib.util; assert importlib.util.find_spec("pytest") is None'
echo 'PAY/17 container smoke passed: non-root API, liveness, MongoDB readiness, OpenAPI, no pytest.'
