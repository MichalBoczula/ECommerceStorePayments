# ADR-0013: Validate generated OpenAPI against HTTP behavior

Status: Accepted

Date: 2026-09-28

## Context

The service already generates OpenAPI without opening MongoDB, but the contract had no reproducible export, lint or CI artifact. FastAPI automatically advertised a 422 validation response even though the API's handler returns 400. The acceptance matrix checks observed statuses and content types but did not validate response bodies against the generated schemas.

## Decision

`scripts/export_openapi.py` exports the actual FastAPI OpenAPI 3.1 document without running the application lifespan. The shared `openapi` CI/local stage validates the document with the `openapi-spec-validator` release pinned in `uv.lock`, checks every published operation and all status/media/schema declarations against generated PAY/12 operation links and acceptance cases, then writes `artifacts/verification/openapi.json`. CI uploads this generated JSON as `payments-openapi`; it is ignored in Git.

An OpenAPI wrapper removes FastAPI's automatic 422 entries from generated operations because the application's validation handler maps those failures to 400. The PAY/11 acceptance response step also validates the actual JSON body against the OpenAPI 3.1 JSON Schema for its operation and observed status, including date and UUID formats. The unmatched-route 404 has no operation; its body is validated against the same problem schema declared on Pay. Wrong-method 405 is checked against the known route's operation. Unit tests prove that missing statuses, wrong media, missing schemas, duplicate operation IDs and invalid observed bodies fail.

## Consequences

The API contract and its CI artifact reflect public status, media type and schema behavior without adding a runtime dependency. `jsonschema` and `openapi-spec-validator` are pinned development dependencies. New routes and acceptance cases need matching operation declarations and schema-valid responses. The acceptance suite validates the exercised cases; it does not claim exhaustive coverage of untested branches. A future intentional 422 response would require revisiting the OpenAPI wrapper and public validation policy.

## Alternatives considered

Committing a generated document would create a second source that can drift. Running the service or MongoDB during export would couple contract verification to infrastructure. Validating only HTTP status and media type would miss response body schema drift.
