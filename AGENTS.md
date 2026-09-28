# Agent instructions

Read this file and [the definition of done](docs/definition-of-done.md) before editing. ECommerceStorePayments and the other portfolio services are equal reference implementations: reuse useful practices where they fit Python and this service's storage model.

## Scope and architecture

- Preserve the FastAPI `api`, `application`, `domain`, and `infrastructure` layers under `src/ecommerce_store_payments`.
- `domain` owns the Payment aggregate, Money, status transitions, and the repository contract. It must not depend on FastAPI, Pydantic, PyMongo, or generated clients.
- Preserve `PaymentPolicy` checks in both creation and rehydration. New domain validation and transitions need typed error codes, tests for invalid snapshots and repeats, and an ADR update when the state policy changes.
- `application` owns use-case orchestration and the OrderReader port. It may depend on Domain, but not on concrete HTTP/MongoDB adapters.
- `infrastructure` owns settings, the HTTP Orders adapter, MongoDB documents, mapper, repository implementation, and indexes. Persist Payment through the mapper and `Payment.rehydrate`; do not put BSON or driver details into the aggregate.
- `api` owns FastAPI routes/contracts and the composition root (`api/app.py`); it wires concrete adapters to the application service. Keep business decisions in the service and aggregate.
- Inspect an existing feature before adding abstractions or packages. Explain public API, persistence-schema, dependency, and architectural changes in the PR. Keep a change within its backlog item unless a dependency is necessary.

## Contracts and tests

- For an endpoint change, consider validation, status codes, public error representation, generated OpenAPI, affected use cases, and success/failure HTTP scenarios together.
- Test pure domain rules in `tests/unit/domain`; use-case decisions in `tests/unit/application`; mapping in `tests/unit/infrastructure`. Test real MongoDB behavior, indexes, and concurrency with Testcontainers in `tests/integration`. When acceptance scenarios are introduced, exercise the public API and real persistence in `tests/acceptance`.
- Existing repository tests with fake collections remain unit tests; the MongoDB Testcontainers suite checks actual database behavior. pytest-bdd scenarios in `tests/acceptance/features` run the public API against an isolated database per scenario. Update `docs/acceptance-matrix.tsv` when adding an HTTP scenario.
- Do not skip failing tests or weaken gates for a green PR. Ordinary warnings may remain visible; quality and security gates have explicit policies when implemented.

## Local verification

Use the versions pinned in `.python-version` and `[tool.uv].required-version` in `pyproject.toml`. With Bash available, run the same stages as CI:

```bash
bash scripts/verify.sh
```

To focus on one stage, run `bash scripts/ci.sh sync` first and then `bash scripts/ci.sh {format|lint|types|links|openapi|test|integration|acceptance|build}`. The latter stages use the synced environment without changing the lockfile. The workflow in `.github/workflows/ci.yml` calls these same stages. The integration and acceptance stages require Docker. `openapi` exports and checks `artifacts/verification/openapi.json` without starting MongoDB.

Running the API: `uv run --locked uvicorn ecommerce_store_payments.main:app --reload`; Swagger UI: `/swagger`. Integration tests start MongoDB with Testcontainers and require Docker. Coverage and security gates are later backlog items. Report only commands actually run.

## Handoff

Use [the PR template](.github/pull_request_template.md). State the backlog ID, resulting behavior, files/contracts affected, verification performed, anything not verified and why, and remaining risks. Update [the technical backlog](TECHNICAL_TODO.md) only after meeting the stated criteria. Accepted ADRs describe implemented decisions; proposed work belongs in the backlog until implemented.
