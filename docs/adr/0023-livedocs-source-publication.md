# ADR-0023: Publish Payments BDD sources for LiveDocs

Status: Accepted
Date: 2026-10-25

## Context

PAY/21 connects Payments to the existing Products, Users and Orders/Invoices
LiveDocs flow. Payments uses pytest-bdd and already derives operation, flow and
policy data from executable sources. CI does not yet produce or archive the
source bundle consumed by the portal.

## Decision

Replace the unused development `allure-pytest` adapter with pinned
`allure-pytest-bdd` 2.16.1, retaining the same Allure commons version.
It emits BDD scenarios, outline examples and steps during
the existing Acceptance suite, without rerunning tests or reporting its regular
pytest cases as BDD. Clear stale Allure results on that invocation. Existing
JUnit, coverage and all five suite/security gates remain.

The existing dependency audit also requires fixes for the baseline lockfile:
PyMongo 4.18.2, certifi 2026.10.19, Mako 1.4.2 and OpenTelemetry API/SDK 1.45.1
with its matching semantic-conventions 0.66b1. Limit updates to these findings and
required companion pins. The MongoDB, HTTP/Stripe and container checks must pass
with the patched lockfile; do not bypass the audit. See the
[PyMongo release](https://www.mongodb.com/community/forums/t/pymongo-4-18-2-released/343732),
[certifi advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2),
[Mako changelog](https://docs.makotemplates.org/en/latest/changelog.html) and
[OpenTelemetry advisory](https://github.com/open-telemetry/opentelemetry-python/security/advisories/GHSA-xcq7-p3pf-p88h).

Extend the database-free OpenAPI export to write the validated operation links,
per-operation flows and deduplicated reachable policies into the shared four-file
source contract. These are generated projections; source remains authoritative.
Keep the existing OpenAPI artifact and publish `generated-contract` for the pinned
LiveDocs producer workflow. The quality gate requires successful bundle validation.

Only after the successful main container publication and final gate, upload the
ZIP and receipt to the existing private `stecproductsdevmb261013/livedocs` container
under `reports/payments/<commit>/<sha256>.zip` and
`candidates/<version>/payments/<run-id>-<sha256>.json`. Authenticate with repository
secret `LIVEDOCS_STORAGE_SAS_TOKEN`. Verify existing bytes on retry, refuse
replacement, never upload from PRs, and fail on missing credentials or upload errors.

LiveDocs selects the actual archive reference in a manifest PR, generates Allure
before image creation, and retains the other reports. Its runtime stays stateless.
Deployment remains an image digest update and apply in ECommerceStore.Terraform.
The optional automated importer and Stripe rollout are outside this change.

## Consequences

The source commit, CI run and ZIP digest identify the BDD evidence. Allure HTML,
results and credentials stay outside Git; no new Azure resources, runtime Blob
connection or deployment scripts are required. The adapter change is development
tooling only; the targeted audit fixes also patch existing runtime dependencies.
Real MongoDB/Orders and production-container checks still run in CI.
Unavailable archives block rebuilds while a deployed image keeps serving its snapshot.

The publisher SAS needs read/create/write on `livedocs`; the LiveDocs build reader
needs read access. Source URLs contain no SAS. Only synthetic acceptance data may
appear in attachments. The archive is private; reports baked into a public image
or served at public ACA are public. Retain bundles selected by supported versions.

## Alternatives considered

- Keep the general pytest adapter: does not provide the BDD-specific scenario/step report needed here.
- Run BDD a second time just for Allure: duplicates real database scenarios and can report a different execution.
- Commit generated HTML or handwritten flow JSON: duplicates rebuildable/source-derived data in Git.
- Download documentation in running replicas: introduces storage credentials and mutable runtime content.
