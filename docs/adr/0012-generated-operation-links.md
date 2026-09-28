# ADR-0012: Generate operation links from executable sources

Status: Accepted

Date: 2026-09-28

## Context

PAY/12 needs a traceable connection from each HTTP operation to its executed application flow, reachable domain rules and acceptance scenarios. A hand-maintained catalog of these links can drift as endpoints and branches change. Payments also has health routes without an application service and a `route_not_found` scenario without a matching operation.

## Decision

`scripts/generate_operation_links.py` builds an on-demand JSON projection. It reads operation IDs, methods and paths from the FastAPI routers and checks them against the database-free OpenAPI schema. It inspects endpoint and service method calls to identify the service entry point and branch-dependent calls and raises. It follows known repository, mapper, adapter and aggregate call edges to collect reachable `PaymentPolicy` and `Money` validation methods, extracting descriptions and guard expressions from those methods. Health endpoints retain their endpoint source as a technical flow.

The acceptance matrix supplies each scenario's operation, cause, status, code and requirement. The generator cross-checks scenario IDs against the feature files and requirement IDs against the backlog. A missing route is recorded separately; a wrong-method scenario links to the known path's operation. Every published operation must have a unique operation ID, a source flow and at least one acceptance scenario. Duplicate or stale matrix links, unknown requirements and unresolved calls within the supported source graph fail generation. `/health` has an explicit compatibility-alias scenario.

Run `bash scripts/ci.sh links` to validate the projection or `uv run --no-sync python scripts/generate_operation_links.py --output operation-links.json` to export it. The shared local verification and PR CI run the validation. Generated JSON is not committed; source and tests remain authoritative.

## Consequences

Documentation and later retrieval tooling can use a deterministic source-derived index without adding an API endpoint or connecting to MongoDB. The flow steps show possible call and raise sites with source guards, not a single runtime trace. The analyzer supports the service's explicit call forms and concrete composition bindings; new indirection or dependency wiring may require extending its resolver alongside the code. Acceptance coverage describes tested behavior but does not prove that every possible branch has a scenario.

## Alternatives considered

A manually maintained operation catalog was rejected because the links would duplicate source and drift. Runtime tracing was rejected because exporting documentation should not require startup, MongoDB or live Orders. The generated OpenAPI contract alone supplies endpoint metadata but not service calls, domain rules or scenario IDs.
