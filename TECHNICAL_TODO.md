# ECommerceStorePayments technical backlog

This tracks the Payments work compared with the reference practices in ECommerceStoreUsers, adapted to Python. `[x]` means implemented and checked; `[ ]` means open. A code skeleton or dependency alone does not close a task. Each PAY item is a cohesive feature/configuration change, with relevant tests and documentation in the same PR. Review the [definition of done](docs/definition-of-done.md).

## Current baseline

- [x] FastAPI service with `/swagger`, Pay and Get by order ID, and a basic `/health` endpoint.
- [x] Domain Payment aggregate and Money; application PaymentService and OrderReader port.
- [x] MongoDB document/mapper/repository, unique order ID index, HTTP Orders adapter.
- [x] uv dependency configuration and lockfile, Ruff, Pyright, pytest unit tests.
- [ ] Production payment flow, real MongoDB integration/acceptance suites, full CI/security gates, and deployment.

## Repository and repeatable verification

- [x] **PAY/1 — Repository standard.** AGENTS.md, Definition of Done, PR template, ADR index and first implemented architecture decision, this backlog, and README links. Close after paths and instructions match current code and proposed decisions are clearly marked.
- [x] **PAY/2 — Reproducible Python environment and basic CI.** Define Python/uv pin policy, locked dependency install, Ruff/Pyright, wheel build/install check, existing tests, shared local/CI entry points and PR/push workflow. Verified with `bash scripts/verify.sh` locally and the clean PR runner.

## Domain and persistence

- [x] **PAY/3 — Payment/Money invariants.** Typed domain errors, valid transitions, repeat-call semantics, payment/provider identifiers, currency validation, and domain unit tests. Verified locally and by the clean PR runner; the accepted behavior is in ADR-0003.
- [x] **PAY/4 — MongoDB Testcontainers.** Isolated databases, real indexes, create/update/read/uniqueness, mapper roundtrip, UUID/time preservation and cleanup. Fake collection tests remain unit tests. Verified by the clean PR runner with real MongoDB.
- [x] **PAY/5 — Optimistic concurrency.** Persisted version, compare-and-update, explicit missing/conflict/duplicate errors, concurrent-create handling and policy for existing versionless documents; real MongoDB tests. Verified on the clean PR runner; see ADR-0005.
- [ ] **PAY/6 — Startup and health.** Configuration validation, bounded database probe, named indexes, cleanup after startup failure, liveness/readiness with an explicit `/health` compatibility decision, and OpenAPI generation without a live database.
- [ ] **PAY/7 — Payment history decision.** Decide if separate change history is needed now and record it in ADR. If adopted, implement consistent state/history writes with MongoDB transactions and rollback tests. A webhook event ledger is a separate concern.

## Application and Orders integration

- [ ] **PAY/8 — Orders contract adapter.** Confirm current Orders/Invoice OpenAPI, map order ID/amount/currency correctly without assuming every currency has two decimal places, handle timeout/404/invalid response/upstream failure, and test the HTTP boundary. If Kiota is adopted, generate reproducibly behind the adapter.
- [ ] **PAY/9 — Pay/Get semantics.** Define behavior per order and payment status, repeat/parallel request handling, retry of failed/cancelled payments, and 201-created versus 200-existing response semantics. Exercise use cases and persistence conflicts.

## API contract, acceptance, and architecture

- [ ] **PAY/10 — Safe public errors.** Central problem+json mapping, stable codes, trace ID, status and media type, route/framework errors, validation policy and no leaked internal details; HTTP tests.
- [ ] **PAY/11 — Acceptance BDD.** pytest-bdd source features, real FastAPI + MongoDB, controlled Orders boundary, scenario isolation and status-by-cause coverage matrix.
- [ ] **PAY/12 — Flow and policy sources.** Link endpoint operation IDs to executed service flows, domain rules, and acceptance scenario IDs; verify missing and duplicate links.
- [ ] **PAY/13 — Generated OpenAPI contract.** Database-free export, pinned lint, actual HTTP status/media/schema checks and CI artifact.
- [ ] **PAY/14 — Architecture checks.** Enforce import direction and persistence boundaries with a negative fixture/test that proves a forbidden import fails.

## Full CI, container, and documentation

- [ ] **PAY/15 — Suite reporting and coverage.** Separate Domain, Application, Infrastructure, ExternalProviders and Acceptance runs; JUnit + coverage reports; separate 70% Domain/Application targets and a proposed 70% Infrastructure target subject to current reference-repo review. Missing reports and failed tests fail correctly.
- [ ] **PAY/16 — Runtime container.** Lockfile-based non-root image without dev dependencies or secrets, Docker Compose with MongoDB and a smoke test for the API.
- [ ] **PAY/17 — Security and final gate.** Locked dependency audit, PR dependency review, secret scan, Trivy image scan, defined severity policies, minimal permissions, and a final gate that includes Docker build/scan. CI builds an image; registry publication/deployment require a separate decision.
- [ ] **PAY/18 — Operational docs review.** Complete README, local startup/verification, API/health, tests, CI, indexes and ADR documentation; reconcile descriptions with working behavior.

## Later functional stage

- [ ] **STRIPE/1 — Provider session/intent.** Angular-compatible flow, idempotency, persisted provider identifiers, retries and boundary tests.
- [ ] **STRIPE/2 — Verified webhook.** Signature validation, durable deduplication, ordering/retries and payment transitions.
- [ ] **STRIPE/3 — Orders and invoice completion.** Durable progress and retry for the MVP HTTP callback after successful payment; prevent double update/invoice. Event transport can follow later.
- [ ] **STRIPE/4 — End-to-end Angular/BFF flow.** Connect UI and backend contracts after the payment and order APIs stabilize.

Recommended sequence: PAY/1, PAY/2, then the Domain/persistence, application, API/acceptance and CI blocks according to dependencies. PAY/7 starts with a decision; PAY/17 follows PAY/16. Update checkboxes only after the criterion is actually met.
