# ECommerceStorePayments technical backlog

This tracks the Payments work compared with the reference practices in ECommerceStoreUsers, adapted to Python. `[x]` means implemented and checked; `[ ]` means open. A code skeleton or dependency alone does not close a task. Each PAY item is a cohesive feature/configuration change, with relevant tests and documentation in the same PR. Review the [definition of done](docs/definition-of-done.md).

## Current baseline

- [x] FastAPI service with `/swagger`, Pay and Get by order ID, and a basic `/health` endpoint.
- [x] Domain Payment aggregate and Money; application PaymentService and OrderReader port.
- [x] MongoDB document/mapper/repository, unique order ID index, HTTP Orders adapter.
- [x] uv dependency configuration and lockfile, Ruff, Pyright, pytest unit tests.
- [x] Real MongoDB integration and HTTP acceptance suites, full CI/security gates, and a published runtime image.
- [ ] Production provider charge/webhook, Orders completion callback, application deployment and end-to-end UI integration (STRIPE backlog).

## Repository and repeatable verification

- [x] **PAY/1 — Repository standard.** AGENTS.md, Definition of Done, PR template, ADR index and first implemented architecture decision, this backlog, and README links. Close after paths and instructions match current code and proposed decisions are clearly marked.
- [x] **PAY/2 — Reproducible Python environment and basic CI.** Define Python/uv pin policy, locked dependency install, Ruff/Pyright, wheel build/install check, existing tests, shared local/CI entry points and PR/push workflow. Verified with `bash scripts/verify.sh` locally and the clean PR runner.

## Domain and persistence

- [x] **PAY/3 — Payment/Money invariants.** Typed domain errors, valid transitions, repeat-call semantics, payment/provider identifiers, currency validation, and domain unit tests. Verified locally and by the clean PR runner; the accepted behavior is in ADR-0003.
- [x] **PAY/4 — MongoDB Testcontainers.** Isolated databases, real indexes, create/update/read/uniqueness, mapper roundtrip, UUID/time preservation and cleanup. Fake collection tests remain unit tests. Verified by the clean PR runner with real MongoDB.
- [x] **PAY/5 — Optimistic concurrency.** Persisted version, compare-and-update, explicit missing/conflict/duplicate errors, concurrent-create handling and policy for existing versionless documents; real MongoDB tests. Verified on the clean PR runner; see ADR-0005.
- [x] **PAY/6 — Startup and health.** Configuration validation, bounded database probe, named indexes, cleanup after startup failure, liveness/readiness with an explicit `/health` compatibility decision, and OpenAPI generation without a live database. Verified on the clean PR runner with real MongoDB; see ADR-0006.
- [x] **PAY/7 — Payment history decision.** Previous snapshots are archived in `payment_history` during the same MongoDB transaction as each current-state update; rollback, concurrency, indexes and versionless migration were verified against a real single-node replica set in the clean PR runner. The decision is in ADR-0007. A webhook event ledger is a separate concern.

## Application and Orders integration

- [x] **PAY/8 — Orders contract adapter.** Verified the generated Orders/Invoice OpenAPI and DTOs; the HTTP boundary validates ID, line totals and currency, converts exact decimals using explicit minor-unit exponents, and maps timeout/404/invalid response/upstream failure. MockTransport boundary tests and real-MongoDB PR CI passed. ADR-0008 records the original handwritten transport; PAY/16 later introduced Kiota behind the same port.
- [x] **PAY/9 — Pay/Get semantics.** New Pay returns 201; existing and retried payments return 200. Failed/canceled retries keep one Payment ID and check Orders status and Money; repeats are read-only. Unit and real MongoDB tests verify parallel create/retry, optimistic conflicts and history. Verified by the clean PR runner; see ADR-0009.

## API contract, acceptance, and architecture

- [x] **PAY/10 — Safe public errors.** Central problem+json mapping, stable codes, trace ID, status and media type, route/framework errors, validation policy and no leaked internal details; HTTP tests. Verified locally and on the clean PR runner, including MongoDB integration tests; see ADR-0010.
- [x] **PAY/11 — Acceptance BDD.** 22 current pytest-bdd source scenarios exercise real FastAPI and isolated MongoDB replica-set databases with a controlled Orders HTTP boundary. The status-by-cause matrix, scenario IDs, history assertions and cleanup run in the acceptance CI stage; PR CI passed.
- [x] **PAY/12 — Flow and policy sources.** A generated projection links all five published operation IDs to source flows, reachable domain rules and acceptance scenarios; checks reject missing, duplicate and stale links. The clean PR runner passed the link stage, unit tests, real MongoDB integration and HTTP acceptance; see ADR-0012.
- [x] **PAY/13 — Generated OpenAPI contract.** Database-free export, locked OpenAPI 3.1 lint, status/media/schema validation against acceptance responses and an uploaded CI artifact. The clean PR runner passed unit, real MongoDB integration, HTTP acceptance and wheel checks; see ADR-0013.
- [x] **PAY/14 — Architecture checks.** Source import direction and MongoDB persistence boundaries are enforced in the shared CI gate. Negative fixtures, including a subprocess invocation, prove forbidden imports fail; full PR CI passed unit, real MongoDB integration, HTTP acceptance and wheel stages. See ADR-0014.

## Full CI, container, and documentation

- [x] **PAY/15 — Suite reporting and coverage.** Five independently run suites publish JUnit and scoped XML/HTML coverage reports. Domain, Application and the entire Infrastructure each enforce 70% line coverage; ExternalProviders and Acceptance report coverage. Missing reports, failed tests and low coverage fail the gate; full PR CI passed. See ADR-0015.
- [x] **PAY/16 — Invoice Orders via Kiota.** Pin the published Invoice image and generated OpenAPI, generate a reproducible Python Kiota client, use it behind OrderReader while preserving exact monetary and error semantics, and verify the live image with MongoDB. PR CI passed, including the published Invoice image integration test.
- [x] **PAY/17 — Runtime container.** Lockfile-based non-root image without dev dependencies or secrets, Docker Compose with MongoDB and a smoke test for the API. PR CI passed the image smoke, all five suites and final gate; see ADR-0017.
- [x] **PAY/18 — Security and quality gate.** Locked dependency audit, PR dependency review, secret scan, Trivy image scan and explicit severity policy all passed the full PR gate; see ADR-0018.
- [x] **PAY/19 — CI graph and Docker Hub publication.** Five named suite jobs, quality gate and image scan passed on `main`; commit `4818fab380506b9b88eb2e154bdd4eee276960be` published both full-SHA and `latest` tags with matching digest `sha256:a5d3f5709a7332fb9d351d0ab4e1c17be9ae4d8a67eee2523d229acdb4e53b54`. See ADR-0019.
- [x] **PAY/20 — Operational docs review.** README startup, API/health, MongoDB indexes/transactions, verification, suites and CI match the code; historical ADRs identify later changes. Local documentation/source checks and full PR CI passed.

## Later functional stage

- [ ] **STRIPE/1 — Provider session/intent.** Angular-compatible flow, idempotency, persisted provider identifiers, retries and boundary tests.
- [ ] **STRIPE/2 — Verified webhook.** Signature validation, durable deduplication, ordering/retries and payment transitions.
- [ ] **STRIPE/3 — Orders and invoice completion.** Durable progress and retry for the MVP HTTP callback after successful payment; prevent double update/invoice. Event transport can follow later.
- [ ] **STRIPE/4 — End-to-end Angular/BFF flow.** Connect UI and backend contracts after the payment and order APIs stabilize.

Next sequence: STRIPE/1–4. Update checkboxes only after the criterion is actually met.
