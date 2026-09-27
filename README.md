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

Each payment has a nonnegative storage version. A new payment starts at version 0; repository updates atomically match the payment ID, order ID and expected version. `update` returns a new aggregate with the next version, which callers must use for later writes. A versionless legacy document reads as version 0 and receives version 1 on its first successful update. Missing records, stale updates and duplicate creates produce separate typed errors. See [ADR-0005](docs/adr/0005-payment-optimistic-concurrency.md).

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

Startup validates the settings, probes MongoDB with a bounded timeout and ensures the named unique `ux_payments_order_id` index. A failed probe or index build prevents the API from starting; both the MongoDB and Orders clients are closed on failure. Relevant environment variables use the `PAYMENTS_` prefix:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PAYMENTS_MONGODB_CONNECTION_STRING` | `mongodb://localhost:27017` | MongoDB URI. |
| `PAYMENTS_MONGODB_DATABASE_NAME` | `ecommerce_store_payments` | Database name. |
| `PAYMENTS_MONGODB_PAYMENTS_COLLECTION_NAME` | `payments` | Payments collection name. |
| `PAYMENTS_MONGODB_PROBE_TIMEOUT_SECONDS` | `5.0` | Wall-clock deadline for the MongoDB ping. |
| `PAYMENTS_MONGODB_SERVER_SELECTION_TIMEOUT_MS` | `5000` | Driver's server-selection deadline. |
| `PAYMENTS_ORDERS_API_BASE_URL` | `http://localhost:5000` | Orders service base URL. |

Open:

- Swagger UI: http://127.0.0.1:8000/swagger
- OpenAPI: http://127.0.0.1:8000/openapi.json
- Liveness: http://127.0.0.1:8000/health/live
- Readiness: http://127.0.0.1:8000/health/ready

`/health` remains a compatibility alias of liveness and responds without querying MongoDB. `/health/ready` probes MongoDB for each request; it returns HTTP 200 with `{"status":"healthy"}` when available and HTTP 503 with `{"status":"unhealthy"}` when unavailable. The response does not include connection details. OpenAPI can be generated without starting the API or connecting to MongoDB. See [ADR-0006](docs/adr/0006-startup-and-health.md).

## Quality checks

With Bash (Git Bash/WSL on Windows), run `bash scripts/verify.sh` for the same stages as CI. Docker must be running for the integration stage. After `bash scripts/ci.sh sync`, run a focused stage using `bash scripts/ci.sh format`, `lint`, `types`, `test`, `integration`, or `build`.

In PowerShell, the equivalent individual commands are:

```powershell
uv lock --check
uv sync --locked --all-groups
uv run --no-sync ruff format --check .
uv run --no-sync ruff check .
uv run --no-sync pyright
uv run --no-sync pytest tests/unit
uv run --no-sync pytest tests/integration # requires Docker
uv build --wheel --no-sources --clear
uv run --no-sync python scripts/verify_wheel.py
```

CI runs on pull requests and pushes to `main`. It checks the lockfile, formatting, lint, types, unit tests, real MongoDB integration tests via Testcontainers, and installation of the built wheel. Integration tests share one MongoDB container, give each test a separate database, and remove each database after use. HTTP acceptance, separate coverage thresholds, image work and security gates remain in the [technical backlog](TECHNICAL_TODO.md).

## Generated API clients

Kiota-generated clients will live under
`src/ecommerce_store_payments/infrastructure/clients/<service>/generated`.
Kiota runtime packages will be added with the first generated client so the repository does not carry unused dependencies.

## Engineering documentation

- [Agent and contributor instructions](AGENTS.md)
- [Definition of done](docs/definition-of-done.md)
- [Technical backlog](TECHNICAL_TODO.md)
- [Architecture decisions](docs/adr/README.md)
