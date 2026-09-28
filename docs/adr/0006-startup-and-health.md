# ADR-0006: Fail startup on unavailable MongoDB and separate liveness from readiness

Status: Accepted
Date: 2026-09-27

## Context

The API previously skipped MongoDB initialization in `test` and returned healthy from `/health` without checking the database. The async MongoDB client connects lazily, so a constructed client does not prove availability. A failed index build could also escape before startup entered its cleanup block.

## Decision

Validate connection URI shape, collection/database names, Orders URL, and positive bounded probe and server-selection timeouts in settings. Every startup, including tests, performs a bounded MongoDB `ping` then creates the named unique `order_id` index. MongoDB and Orders clients close on both startup failure and normal shutdown. HTTP unit tests inject a small fake adapter; MongoDB integration tests start the real application lifecycle with Testcontainers. Creating the FastAPI object and generating OpenAPI require no MongoDB connection.

Keep `/health` as a compatibility alias of liveness, returning HTTP 200 with `{"status":"healthy"}` without a database request. `/health/live` has the same behavior. `/health/ready` probes MongoDB on every request and responds with HTTP 200 and `{"status":"healthy"}` or HTTP 503 and `{"status":"unhealthy"}` on a driver error or timeout. Do not expose the connection failure details in this response. Readiness checks MongoDB only; Orders availability is not a startup dependency and is handled at the Orders boundary. ADR-0010 supersedes the HTTP 503 body with `application/problem+json` and code `service_unavailable`.

## Consequences

The process cannot report startup success with a missing database or conflicting index. Readiness can fail independently while liveness remains healthy. Startup/health checks are bounded by explicit settings; index building still follows MongoDB's index operation behavior. Deployments that relied on `/health` to indicate database availability should use `/health/ready` instead.

## Alternatives considered

- Keep the `test` bypass: it hides production startup failures from integration tests.
- Make `/health` a readiness endpoint: existing liveness probes would start failing during a temporary database outage.
- Probe Orders on every readiness request: the service can be operational while Orders is temporarily unavailable, and no Orders health contract is defined yet.
