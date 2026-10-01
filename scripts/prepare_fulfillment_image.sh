#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
# Exact upstream source revision includes the completed invoice lookup (Invoice PR #217).
revision=3b66b6b856773ca9cae0ac59647fd8b73cffd08f
source_dir=artifacts/verification/invoice-source
mkdir -p "$source_dir"
git -C "$source_dir" init --quiet
git -C "$source_dir" fetch --quiet --depth=1 https://github.com/MichalBoczula/ECommerceStoreInvoice.git "$revision"
git -C "$source_dir" checkout --quiet --detach FETCH_HEAD
test "$(git -C "$source_dir" rev-parse HEAD)" = "$revision"
docker build --tag ecommerce-store-invoice:stripe3 --file "$source_dir/src/ECommerceStoreInvoice.API/Dockerfile" "$source_dir"
