# ADR-0017: Runtime image and local Compose stack

Status: Accepted
Date: 2026-09-28

## Context

PAY/17 needs a deployable image and a local path that exercises startup with MongoDB. Payment history uses transactions, so MongoDB must be initialized as a replica set. Runtime images should exclude development dependencies and local configuration files.

## Decision

Build on the Python patch pinned in `.python-version`. A separate stage installs the committed `uv.lock` with uv 0.12.18, excludes the dev dependency group, and installs the application as a wheel into a virtual environment. The final stage copies only that environment into the matching slim Python runtime. Run the final container as numeric UID/GID 10001, serve HTTP on port 8080, and use the liveness endpoint for the image health check. No credentials or `.env` files are copied into the image.

`compose.yaml` starts MongoDB 8, waits for an elected replica-set primary, then starts Payments. The API exposes only a localhost port. Compose is for local development: MongoDB has no authentication or published port. The Orders URL can point to a separately running Invoice service. The API filesystem is read-only with a temporary `/tmp` mount.

`scripts/smoke_container.sh` creates a unique Compose project, removes its containers and volume on exit, and verifies live/ready/OpenAPI endpoints, non-root UID and absence of pytest. CI runs it after the quality job and requires it in the final gate.

## Consequences

The image contains runtime dependencies but no test tools. Docker is required for the smoke stage, and an Orders API must be available for successful `pay` requests. Scanning and publishing the image are PAY/18 and PAY/19 tasks.

## Alternatives considered

Installing the dev group or copying the project directory into the final image would add unnecessary tools and local files. A standalone MongoDB would allow startup but fail payment history transactions. Publishing MongoDB's port is unnecessary for the API smoke test.
