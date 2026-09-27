# ECommerceStorePayments

Python service responsible for the payment area of the ECommerce Store portfolio.

## Technology

- Python 3.14 (the development and CI patch version is pinned in `.python-version`)
- FastAPI
- Pydantic and pydantic-settings
- PyMongo Async API
- pytest, HTTPX2, and Testcontainers
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

The Domain layer must remain independent of FastAPI, Pydantic, PyMongo, and generated API clients. MongoDB documents are mapped explicitly to the Payment aggregate and reconstructed with `rehydrate`. See [ADR-0001](docs/adr/0001-payment-layers-and-mongodb-mapping.md).

The aggregate validates both new and rehydrated state, allows only defined status transitions, and treats an identical repeated transition as a no-op. Domain failures have typed, stable codes. Money stores integer minor units and an uppercase three-letter ASCII currency code; actual currency support and minor-unit conversion are handled at the integration boundary. See [ADR-0003](docs/adr/0003-payment-invariants-and-rehydration.md).

## Local setup

Install the Python version from `.python-version` and uv 0.12.18. The service supports Python 3.14; this repository pins an exact patch for development and CI. To deliberately update the pin, change `.python-version` and the matching CI install, check `uv.lock`, and run the full verification. Update `[tool.uv].required-version` and the workflow together when upgrading uv.

Install the locked project dependencies:

```bash
uv sync --locked --all-groups
```

Start the API with MongoDB available at the configured address:

```bash
uv run --locked uvicorn ecommerce_store_payments.main:app --reload
```

Open:

- Swagger UI: http://127.0.0.1:8000/swagger
- OpenAPI: http://127.0.0.1:8000/openapi.json
- Health: http://127.0.0.1:8000/health

## Quality checks

With Bash (Git Bash/WSL on Windows), run `bash scripts/verify.sh` for the same stages as CI. After `bash scripts/ci.sh sync`, run a focused stage using `bash scripts/ci.sh format`, `lint`, `types`, `test`, or `build`.

In PowerShell, the equivalent individual commands are:

```powershell
uv lock --check
uv sync --locked --all-groups
uv run --no-sync ruff format --check .
uv run --no-sync ruff check .
uv run --no-sync pyright
uv run --no-sync pytest
uv build --wheel --no-sources --clear
uv run --no-sync python scripts/verify_wheel.py
```

CI runs on pull requests and pushes to `main`. It checks the lockfile, formatting, lint, types, the current unit tests and installation of the built wheel. The current tests are unit tests; MongoDB Testcontainers integration, HTTP acceptance, separate coverage thresholds, image work and security gates remain in the [technical backlog](TECHNICAL_TODO.md).

## Generated API clients

Kiota-generated clients will live under
`src/ecommerce_store_payments/infrastructure/clients/<service>/generated`.
Kiota runtime packages will be added with the first generated client so the repository does not carry unused dependencies.

## Engineering documentation

- [Agent and contributor instructions](AGENTS.md)
- [Definition of done](docs/definition-of-done.md)
- [Technical backlog](TECHNICAL_TODO.md)
- [Architecture decisions](docs/adr/README.md)
