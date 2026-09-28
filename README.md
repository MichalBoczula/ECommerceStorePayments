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

The `architecture` verification stage scans Python imports: Domain depends only on Domain, Application on Domain/Application, Infrastructure on the inner layers, and API on Domain/Application/API. `api/app.py` composes concrete adapters; the readiness route has a narrow exception to probe MongoDB. MongoDB documents stay inside Infrastructure, and driver imports stay in MongoDB persistence apart from the readiness error type. A negative fixture proves that forbidden imports fail the same CI command. See [ADR-0014](docs/adr/0014-python-architecture-gate.md).

The aggregate validates both new and rehydrated state, allows only defined status transitions, and treats an identical repeated transition as a no-op. Domain failures have typed, stable codes. Money stores integer minor units and an uppercase three-letter ASCII currency code; actual currency support and minor-unit conversion are handled at the integration boundary. See [ADR-0003](docs/adr/0003-payment-invariants-and-rehydration.md).

Each payment has a nonnegative storage version. A new payment starts at version 0; repository updates atomically match the payment ID, order ID and expected version. `update` returns a new aggregate with the next version, which callers must use for later writes. A versionless legacy document reads as version 0 and receives version 1 on its first successful update. Missing records, stale updates and duplicate creates produce separate typed errors. See [ADR-0005](docs/adr/0005-payment-optimistic-concurrency.md).

The `payments` collection holds current state. Each update transactionally stores the previous snapshot in `payment_history`, with its payment ID, version and recording time. `get_history(payment_id)` reads prior snapshots in version order; a newly created payment has no history. MongoDB must be configured as a replica set or sharded cluster to support transactions, including for local development. See [ADR-0007](docs/adr/0007-payment-history.md).

The Orders adapter reads `GET /orders/{orderId}` and validates the returned ID, total, status and line consistency before creating a payment. It converts exact decimal totals using explicit currency minor units: PLN/EUR/USD/GBP/CHF (2), JPY/KRW (0), BHD/JOD/KWD/OMR/TND (3). Unknown currencies and unrepresentable amounts are rejected. A missing order yields 404; a bad upstream response or outage yields 502; an Orders timeout yields 504. See [ADR-0008](docs/adr/0008-orders-http-adapter.md). Stripe support for individual currencies is decided separately.

`POST /payments/{order_id}/pay` returns 201 only when it creates a Payment. It returns 200 for an existing `Created`, `Pending` or `Succeeded` Payment. A `Failed` or `Canceled` Payment can be retried on the same ID after Orders confirms the original amount/currency and `Created` status; this resets provider data, archives the previous state and returns 200. Changed totals or incompatible order status return 409. Parallel creates/retries resolve to one persisted state and do not duplicate payment history. `GET /payments/order/{order_id}` reads current state (200) or returns 404. See [ADR-0009](docs/adr/0009-pay-get-semantics.md). Starting a provider session is future STRIPE work.

## Local setup

Install the Python version from `.python-version` and uv 0.12.18. The service supports Python 3.14; this repository pins an exact patch for development and CI. To deliberately update the pin, change `.python-version` and the matching CI install, check `uv.lock`, and run the full verification. Update `[tool.uv].required-version` and the workflow together when upgrading uv.

Install the locked project dependencies:

```bash
uv sync --locked --all-groups
```

Start the API with a MongoDB replica set available at the configured address:

```bash
uv run --locked uvicorn ecommerce_store_payments.main:app --reload
```

Startup validates the settings, probes MongoDB with a bounded timeout and ensures the named `ux_payments_order_id` unique index and `ix_payment_history_payment_id` lookup index. A failed probe or index build prevents the API from starting; both the MongoDB and Orders clients are closed on failure. Relevant environment variables use the `PAYMENTS_` prefix:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PAYMENTS_MONGODB_CONNECTION_STRING` | `mongodb://localhost:27017` | MongoDB URI. |
| `PAYMENTS_MONGODB_DATABASE_NAME` | `ecommerce_store_payments` | Database name. |
| `PAYMENTS_MONGODB_PAYMENTS_COLLECTION_NAME` | `payments` | Payments collection name. |
| `PAYMENTS_MONGODB_PAYMENT_HISTORY_COLLECTION_NAME` | `payment_history` | Prior payment snapshots collection. |
| `PAYMENTS_MONGODB_PROBE_TIMEOUT_SECONDS` | `5.0` | Wall-clock deadline for the MongoDB ping. |
| `PAYMENTS_MONGODB_SERVER_SELECTION_TIMEOUT_MS` | `5000` | Driver's server-selection deadline. |
| `PAYMENTS_ORDERS_API_BASE_URL` | `http://localhost:5000` | Orders service base URL. |
| `PAYMENTS_ORDERS_API_TIMEOUT_SECONDS` | `5.0` | Orders request timeout, at most 30 seconds. |

Open:

- Swagger UI: http://127.0.0.1:8000/swagger
- OpenAPI: http://127.0.0.1:8000/openapi.json
- Liveness: http://127.0.0.1:8000/health/live
- Readiness: http://127.0.0.1:8000/health/ready

`/health` remains a compatibility alias of liveness and responds without querying MongoDB. `/health/ready` probes MongoDB for each request; it returns HTTP 200 with `{"status":"healthy"}` when available and HTTP 503 with a problem response (`service_unavailable`) when unavailable. OpenAPI can be generated without starting the API or connecting to MongoDB. See [ADR-0006](docs/adr/0006-startup-and-health.md) and [ADR-0010](docs/adr/0010-safe-public-errors.md).

API errors use `application/problem+json` with `type`, `title`, `status`, fixed public `detail`, path-only `instance`, stable `code`, `traceId`, `errors` and `missingProperties`. The last two fields are empty unless validation has safe structured details. The `X-Trace-Id` response header matches `traceId` and is also present on successful requests. Example (IDs vary):

```json
{"type":"about:blank","title":"Not Found","status":404,"detail":"Payment was not found.","instance":"/payments/order/00000000-0000-0000-0000-000000000000","code":"payment_not_found","traceId":"0123456789abcdef0123456789abcdef","errors":[],"missingProperties":[]}
```

Invalid path parameters return 400 `invalid_request`; malformed JSON returns 400 `invalid_json`; unsupported request media returns 415 `unsupported_media_type`. Pay accepts no request body. Unknown routes return 404 `route_not_found`; wrong methods return 405 `method_not_allowed`. Internal errors return a generic 500 `internal_error` without exception details. Orders failures map to 502 or 504 with distinct codes. The [ADR-0010](docs/adr/0010-safe-public-errors.md) records the public error policy.

## Quality checks

With Bash (Git Bash/WSL on Windows), run `bash scripts/verify.sh` for the same stages as CI. Docker must be running for the integration and acceptance stages. After `bash scripts/ci.sh sync`, run a focused stage using `bash scripts/ci.sh format`, `lint`, `types`, `architecture`, `links`, `openapi`, `test`, `integration`, `acceptance`, or `build`.

In PowerShell, the equivalent individual commands are:

```powershell
uv lock --check
uv sync --locked --all-groups
uv run --no-sync ruff format --check .
uv run --no-sync ruff check .
uv run --no-sync pyright
uv run --no-sync python scripts/check_architecture.py
uv run --no-sync python scripts/generate_operation_links.py --check
uv run --no-sync python -m scripts.export_openapi
uv run --no-sync pytest tests/unit
uv run --no-sync pytest tests/integration # requires Docker
uv run --no-sync pytest tests/acceptance # requires Docker
uv build --wheel --no-sources --clear
uv run --no-sync python scripts/verify_wheel.py
```

CI runs on pull requests and pushes to `main`. It checks the lockfile, formatting, lint, types, architecture boundaries, operation links, generated OpenAPI, unit tests, real MongoDB integration and HTTP acceptance scenarios via Testcontainers, and installation of the built wheel. MongoDB suites share a single-node replica set container, give each test or scenario a separate database, and remove each database after use. Acceptance uses a controlled Orders HTTP transport while exercising the real adapter and FastAPI lifecycle. The [acceptance matrix](docs/acceptance-matrix.tsv) links source scenarios to operation, cause, status, code and requirement; see [ADR-0011](docs/adr/0011-acceptance-isolation.md).

Generate the operation projection with `uv run --no-sync python scripts/generate_operation_links.py --output operation-links.json`. The JSON links each published operation ID to its source service flow (including called branches), reachable domain policies and acceptance scenario IDs. The generator reads routes, method bodies, policy docstrings, the acceptance matrix and feature scenarios; the `links` CI stage fails on missing, duplicate or stale links. The generated JSON is an on-demand artifact for documentation tooling and is not checked in. See [ADR-0012](docs/adr/0012-generated-operation-links.md).

Run `bash scripts/ci.sh openapi` to export and lint the database-free OpenAPI at `artifacts/verification/openapi.json` (or `uv run --no-sync python -m scripts.export_openapi --output <path>`). OpenAPI 3.1 validation and operation/scenario status, media and schema checks use pinned development dependencies in `uv.lock`. Acceptance tests validate each observed HTTP body against its declared JSON Schema, with the unmatched-route response checked against the shared problem schema. CI uploads the generated JSON as `payments-openapi`. The API documents path validation as 400, matching runtime, instead of FastAPI's default 422. See [ADR-0013](docs/adr/0013-generated-openapi-contract.md). Separate coverage thresholds, image work and security gates remain in the [technical backlog](TECHNICAL_TODO.md).

## Generated API clients

Kiota-generated clients will live under
`src/ecommerce_store_payments/infrastructure/clients/<service>/generated`.
Kiota runtime packages will be added with the first generated client so the repository does not carry unused dependencies.

## Engineering documentation

- [Agent and contributor instructions](AGENTS.md)
- [Definition of done](docs/definition-of-done.md)
- [Technical backlog](TECHNICAL_TODO.md)
- [Architecture decisions](docs/adr/README.md)
