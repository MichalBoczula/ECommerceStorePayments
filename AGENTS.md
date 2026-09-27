# Agent instructions

Read this file and [the definition of done](docs/definition-of-done.md) before editing. ECommerceStorePayments and the other portfolio services are equal reference implementations: reuse useful practices where they fit Python and this service's storage model.

## Scope and architecture

- Preserve the FastAPI `api`, `application`, `domain`, and `infrastructure` layers under `src/ecommerce_store_payments`.
- `domain` owns the Payment aggregate, Money, status transitions, and the repository contract. It must not depend on FastAPI, Pydantic, PyMongo, or generated clients.
- `application` owns use-case orchestration and the OrderReader port. It may depend on Domain, but not on concrete HTTP/MongoDB adapters.
- `infrastructure` owns settings, the HTTP Orders adapter, MongoDB documents, mapper, repository implementation, and indexes. Persist Payment through the mapper and `Payment.rehydrate`; do not put BSON or driver details into the aggregate.
- `api` owns FastAPI routes/contracts and the composition root (`api/app.py`); it wires concrete adapters to the application service. Keep business decisions in the service and aggregate.
- Inspect an existing feature before adding abstractions or packages. Explain public API, persistence-schema, dependency, and architectural changes in the PR. Keep a change within its backlog item unless a dependency is necessary.

## Contracts and tests

- For an endpoint change, consider validation, status codes, public error representation, generated OpenAPI, affected use cases, and success/failure HTTP scenarios together.
- Test pure domain rules in `tests/unit/domain`; use-case decisions in `tests/unit/application`; mapping in `tests/unit/infrastructure`. Test real MongoDB behavior, indexes, and concurrency with Testcontainers in `tests/integration`. When acceptance scenarios are introduced, exercise the public API and real persistence in `tests/acceptance`.
- Existing repository tests with fake collections are unit tests; they do not establish actual MongoDB behavior. Empty integration/acceptance packages are placeholders, not implemented suites.
- Do not skip failing tests or weaken gates for a green PR. Ordinary warnings may remain visible; quality and security gates have explicit policies when implemented.

## Local verification

With Python 3.14 and uv installed, use the commands currently available:

```bash
uv sync --all-groups
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
```

Running the API: `uv run uvicorn ecommerce_store_payments.main:app --reload`; Swagger UI: `/swagger`. Tests that exercise MongoDB require a running MongoDB service or Testcontainers fixture; current `tests/unit` are the only implemented test suite. Local verification scripts and CI are tracked in [PAY/2](TECHNICAL_TODO.md); do not describe them as available yet. Report only commands actually run.

## Handoff

Use [the PR template](.github/pull_request_template.md). State the backlog ID, resulting behavior, files/contracts affected, verification performed, anything not verified and why, and remaining risks. Update [the technical backlog](TECHNICAL_TODO.md) only after meeting the stated criteria. Accepted ADRs describe implemented decisions; proposed work belongs in the backlog until implemented.
