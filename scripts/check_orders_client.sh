#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ -n "${KIOTA_BIN:-}" ]]; then
  kiota_bin="$KIOTA_BIN"
elif command -v kiota >/dev/null; then
  kiota_bin="$(command -v kiota)"
else
  scratch="$(mktemp -d)"
  trap 'rm -rf "$scratch"' EXIT
  curl --fail --location --retry 3 --silent --show-error \
    https://github.com/microsoft/kiota/releases/download/v1.34.1/linux-x64.zip \
    --output "$scratch/kiota.zip"
  printf '%s  %s\n' \
    682416ab85c07bb3152e4c2c54293ae51f582aebde381699d8999f7b076755dd \
    "$scratch/kiota.zip" | sha256sum --check --status
  unzip -q "$scratch/kiota.zip" -d "$scratch"
  chmod +x "$scratch/kiota"
  kiota_bin="$scratch/kiota"
fi
uv run --no-sync python scripts/verify_orders_client.py --kiota "$kiota_bin" --check
