# ADR-0010: Safe public API errors

Status: Accepted

Date: 2026-09-28

## Context

Pay and Get exposed exception messages in FastAPI's default JSON error body. Those messages included order identifiers and could reveal implementation details. Readiness used a separate JSON shape, and request validation used FastAPI's default error representation. Clients need stable machine-readable codes and a correlation identifier.

## Decision

Return RFC 9457 `application/problem+json` for HTTP failures. The body contains `type` (`about:blank`), HTTP `title` and `status`, a fixed public `detail`, a stable `code`, and a generated `traceId`. `X-Trace-Id` carries the same identifier on every response, including successes. Generate the ID at the API boundary; log unexpected exceptions with it, never their details in the response. Do not reflect a caller-supplied trace header. Known application/repository errors map centrally; FastAPI path validation returns 422 `invalid_request` without echoing the submitted value. Unmatched routes return 404 `route_not_found`; wrong methods return 405 `method_not_allowed` with `Allow` preserved. Unexpected failures return 500 `internal_error`. MongoDB readiness failures return 503 `service_unavailable`. The API router documents the problem media type and schema for each applicable status in OpenAPI.

The public code is an API contract, distinct from domain validation codes and exception messages. A separate HTTP acceptance suite and exported OpenAPI lint remain PAY/11 and PAY/13.

## Consequences

Clients use the status and `code` to choose behavior and supply `traceId` when reporting failures. Existing consumers of FastAPI `detail` or readiness's `{ "status": "unhealthy" }` must update. `about:blank` uses HTTP status for the general problem type, while `code` distinguishes causes within it. Internal details stay in server logs.

## Alternatives considered

Keep FastAPI's default `detail` responses and wrap each route separately: rejected because representation and redaction would vary by endpoint. Return full validation errors: rejected because submitted values and internals can be exposed. Reuse domain codes directly: rejected because persistence and integration errors also need a stable public taxonomy.
