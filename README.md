# ECommerceStorePayments

Python service responsible for the payment area of the ECommerce Store portfolio.

## Technology

- Python 3.14
- FastAPI
- Pydantic and pydantic-settings
- PyMongo Async API
- pytest, HTTPX, and Testcontainers
- pytest-bdd and Allure
- Ruff and Pyright
- uv for dependency and environment management

## Architecture

```text
src/ecommerce_store_payments/
├── api/              # HTTP transport, routers, and API contracts
├── application/      # use cases, application services, and ports
├── domain/           # entities, value objects, and domain rules
└── infrastructure/   # configuration, persistence, and external clients
```

The Domain layer must remain independent of FastAPI, Pydantic, PyMongo, and generated API clients.

## Local setup

Install Python 3.14 and uv, then run:

```bash
uv sync --all-groups
```

Start the API:

```bash
uv run uvicorn ecommerce_store_payments.main:app --reload
```

Open:

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json
- Health: http://127.0.0.1:8000/health

## Quality checks

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
```

## Generated API clients

Kiota-generated clients will live under
`src/ecommerce_store_payments/infrastructure/clients/<service>/generated`.
Kiota runtime packages will be added with the first generated client so the repository does not carry unused dependencies.
