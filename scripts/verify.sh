#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

for stage in sync format lint types architecture orders-client links openapi build audit; do
  echo "Running $stage"
  bash scripts/ci.sh "$stage"
done

for suite in domain application infrastructure externalproviders acceptance; do
  echo "Running $suite suite"
  bash scripts/ci.sh suite "$suite"
done

echo "Running container smoke"
bash scripts/ci.sh container
