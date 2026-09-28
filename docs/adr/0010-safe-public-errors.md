# ADR-0010: Safe public API errors

Status: Accepted

Date: 2026-09-28

## Context

Pay and Get exposed exception messages in FastAPI's default JSON error body. Those messages included order identifiers and could reveal implementation details. Readiness used a separate JSON shape, and request validation used FastAPI's default error representation. Clients need stable machine-readable codes and a correlation identifier.

## Decision

Return RFC 9457 `application/problem+json` for HTTP failures. The body contains `type` (`about:blank`), HTTP `title` and `status`, a fixed public `detail`, path-only `instance`, a stable `code`, a generated `traceId`, and `errors` and `missingProperties` arrays. The arrays remain empty when there are no safe structured validation details. When FastAPI detects missing members of a JSON body model, `missingProperties` contains only names from the request contract. `X-Trace-Id` carries the same identifier on every response, including successes. Generate the ID at the API boundary; log unexpected exceptions with it, never their details in the response. Do not reflect a caller-supplied trace header. Known domain/application/repository errors map centrally. FastAPI path validation returns 400 `invalid_request` without echoing the submitted value. Malformed JSON returns 400 `invalid_json`; unsupported request media returns 415 `unsupported_media_type`. Pay has no body contract and rejects a supplied body, classifying malformed JSON and unsupported media separately. Unmatched routes return 404 `route_not_found`; wrong methods return 405 `method_not_allowed` with `Allow` preserved. Unexpected failures return 500 `internal_error`. MongoDB readiness failures return 503 `service_unavailable`. The API router documents the problem media type and schema for each applicable status in OpenAPI.

The public code is an API contract, distinct from domain validation codes and exception messages. A separate HTTP acceptance suite and exported OpenAPI lint remain PAY/11 and PAY/13.

## Consequences

Clients use the status and `code` to choose behavior and supply `traceId` when reporting failures. Existing consumers of FastAPI `detail`, validation status 422, or readiness's `{ "status": "unhealthy" }` must update. `about:blank` uses HTTP status for the general problem type, while `code` distinguishes causes within it. Internal details stay in server logs.

## Alternatives considered

Keep FastAPI's default `detail` responses and wrap each route separately: rejected because representation and redaction would vary by endpoint. Return full validation errors: rejected because submitted values and internals can be exposed. Reuse domain codes directly: rejected because persistence and integration errors also need a stable public taxonomy.
