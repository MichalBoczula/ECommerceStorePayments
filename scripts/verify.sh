#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

for stage in sync format lint types test integration acceptance build; do
  echo "Running $stage"
  bash scripts/ci.sh "$stage"
done
