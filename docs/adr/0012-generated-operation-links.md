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

PAY-BDD-01 additionally freezes the original scenario/cause/outcome inventory,
parses expanded source cases with pytest-bdd and reports bidirectional declared
status coverage in the existing projection. Sixteen explicitly reviewed gaps
remain; new or stale gaps fail. Wrong-method and unmatched-route evidence stays
distinct from execution of a named handler. See [the baseline](../bdd-01-baseline.md).

Documentation and later retrieval tooling can use a deterministic source-derived index without adding an API endpoint or connecting to MongoDB. The flow steps show possible call and raise sites with source guards, not a single runtime trace. The analyzer supports the service's explicit call forms and concrete composition bindings; new indirection or dependency wiring may require extending its resolver alongside the code. Acceptance coverage describes tested behavior but does not prove that every possible branch has a scenario.

## Alternatives considered

A manually maintained operation catalog was rejected because the links would duplicate source and drift. Runtime tracing was rejected because exporting documentation should not require startup, MongoDB or live Orders. The generated OpenAPI contract alone supplies endpoint metadata but not service calls, domain rules or scenario IDs.

## PAY-BDD-15 semantic source contract

[Task 15](../bdd-15-flows-rules-rag-links.md) extends the existing projection with
stable authored aliases checked against executable predicates/sites, human
conditions/effects/failures, canonical method/site references and flow-qualified
steps. Concrete command composition adds fulfillment/replay roots. Typed source
references distinguish policies, rejection sites, declared outcomes and receipt
reasons. The [description contract](../source-description-contract.md) defines
supported source forms and limits; possible sites are not runtime branch telemetry.

The existing four generated exports carry the catalogue, without an extra
application endpoint or committed generated index. Expanded Gherkin When bindings
join each scenario to actual HTTP or explicitly tagged worker/repository actions.
References prepare future retrieval tooling without claiming RAG ingestion or
retrieval. Source, runtime API, dependency and persistence boundaries stay intact.
