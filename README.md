# ECommerceStorePayments

Python service responsible for the payment area of the ECommerce Store portfolio.

## Technology

- Python 3.14 (the development and CI patch version is pinned in `.python-version`)
- FastAPI
- Stripe Python SDK (test-mode hosted Checkout)
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

The Orders adapter uses a Kiota Python client generated from the pinned Invoice `GET /orders/{orderId}` OpenAPI contract. The generated client stays inside Infrastructure behind `OrderReader`; a handwritten mapper validates the returned ID, total, status and line consistency. The Invoice schema declares money as `number/double`, so our Kiota JSON factory reads wire tokens as exact `Decimal` values and the mapper rejects anything else. It converts exact decimal totals using explicit currency minor units: PLN/EUR/USD/GBP/CHF (2), JPY/KRW (0), BHD/JOD/KWD/OMR/TND (3). Unknown currencies and unrepresentable amounts are rejected. A missing order yields 404; a bad upstream response or outage yields 502; an Orders timeout yields 504. See [ADR-0008](docs/adr/0008-orders-http-adapter.md) and [ADR-0016](docs/adr/0016-invoice-kiota-orders-client.md). The Stripe checkout supports PLN card and BLIK payments; the broader Orders conversion table is unchanged.

`POST /payments/{order_id}/pay` returns 201 only when it creates a Payment. It returns 200 for an existing `Created`, `Pending` or `Succeeded` Payment. A `Failed` or `Canceled` Payment can be retried on the same ID after Orders confirms the original amount/currency and `Created` status; this resets provider data, archives the previous state and returns 200. Changed totals or incompatible order status return 409. Parallel creates/retries resolve to one persisted state and do not duplicate payment history. `GET /payments/order/{order_id}` reads current state (200) or returns 404. See [ADR-0009](docs/adr/0009-pay-get-semantics.md). Provider session creation is a separate checkout command; see [ADR-0020](docs/adr/0020-stripe-hosted-checkout.md).

The current public API has seven operations: `POST /payments/webhooks/stripe`, `POST /payments/{order_id}/pay`, `POST /payments/{order_id}/checkout`, `GET /payments/order/{order_id}`, `GET /health`, `GET /health/live` and `GET /health/ready`. The Pay response contains `id`, `order_id`, `amount_minor`, `currency`, `status`, nullable provider IDs and failure code, `created_at` and nullable `updated_at`. The internal storage version and payment history are not exposed in this response. A newly created Payment starts in `Created`; a repeated Pay can return its existing status. Pay/Get do not initiate a provider charge or notify Orders.

The bodyless Checkout command returns 200 with `payment`, nullable `checkout_url`, `checkout_status` and `expires_at`. It checks Orders, reserves a durable attempt, creates/replays a Stripe test session and persists Pending. Repeats retrieve the same session; they do not confirm payment. Hosted card/BLIK checkout supports PLN, minimum PLN 2 and a conservative 99,999,999-minor-unit maximum. Verified confirmation is provided by STRIPE/2; downstream completion remains STRIPE/3. See the [checkout runbook](docs/stripe-checkout.md) for configuration, errors, recovery and real-account smoke steps.

`POST /payments/webhooks/stripe` verifies original snapshot bytes with the endpoint signing secret, durably records receipt, and atomically confirms matching payments with their history and fulfillment work marker. Duplicate/concurrent notifications are idempotent, old attempts cannot complete new ones, and success wins over expiry within the same attempt. Unpaid completion stays pending; failure/expiry does not cancel Orders. No external calls occur during receipt. Pending work survives interruption and has a bounded replay command. See [ADR-0021](docs/adr/0021-verified-stripe-webhooks.md) and the [webhook runbook](docs/stripe-webhooks.md).

New reservations persist request version 2 for card/BLIK. Missing version means the previous card-only request; recovery preserves original Stripe parameters. Payment/history mapping remains compatible and the request version is internal.

## Local setup

Install uv 0.12.18 and the Python version from `.python-version` (`uv python install` can install the pinned interpreter). The service supports Python 3.14; this repository pins an exact patch for development and CI. To deliberately update the pin, change `.python-version` and the matching CI install, check `uv.lock`, and run the full verification. Update `[tool.uv].required-version` and the workflow together when upgrading uv.

Install the locked project dependencies:

```bash
uv sync --locked --all-groups
```

Start the API with a MongoDB replica set available at the configured address:

```bash
uv run --locked uvicorn ecommerce_store_payments.main:app --reload
```

Startup validates the settings, probes MongoDB with a bounded timeout and ensures the indexes below. A failed probe or index build prevents the API from starting; MongoDB, Orders and any owned Stripe client are closed on failure. Settings can come from environment variables or a local `.env` file (excluded from the runtime image); variables use the `PAYMENTS_` prefix:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PAYMENTS_APP_NAME` | `ECommerce Store Payments API` | OpenAPI title. |
| `PAYMENTS_ENVIRONMENT` | `local` | One of `local`, `test`, `development`, `staging`, `production`. |
| `PAYMENTS_MONGODB_CONNECTION_STRING` | `mongodb://localhost:27017` | MongoDB URI. |
| `PAYMENTS_MONGODB_DATABASE_NAME` | `ecommerce_store_payments` | Database name. |
| `PAYMENTS_MONGODB_PAYMENTS_COLLECTION_NAME` | `payments` | Payments collection name. |
| `PAYMENTS_MONGODB_PAYMENT_HISTORY_COLLECTION_NAME` | `payment_history` | Prior payment snapshots collection. |
| `PAYMENTS_MONGODB_WEBHOOK_COLLECTION_NAME` | `stripe_webhooks` | Verified receipts and pending fulfillment work. |
| `PAYMENTS_MONGODB_PROBE_TIMEOUT_SECONDS` | `5.0` | Wall-clock deadline for the MongoDB ping. |
| `PAYMENTS_MONGODB_SERVER_SELECTION_TIMEOUT_MS` | `5000` | Driver's server-selection deadline. |
| `PAYMENTS_ORDERS_API_BASE_URL` | `http://localhost:5000` | Orders service base URL. |
| `PAYMENTS_ORDERS_API_TIMEOUT_SECONDS` | `5.0` | Orders request timeout, at most 30 seconds. |
| `PAYMENTS_STRIPE_ENABLED` | `false` | Enable the separate test checkout command. |
| `PAYMENTS_STRIPE_SECRET_KEY` | unset | Test secret, required when checkout is enabled; live keys are rejected. |
| `PAYMENTS_STRIPE_WEBHOOK_SECRET` | unset | Endpoint-specific signing secret; independently enables receipt. |
| `PAYMENTS_STRIPE_SUCCESS_URL` | `http://localhost:4200/orders?checkout=success` | Fixed checkout success destination. |
| `PAYMENTS_STRIPE_CANCEL_URL` | `http://localhost:4200/orders?checkout=cancel` | Fixed checkout cancel destination. |
| `PAYMENTS_STRIPE_TIMEOUT_SECONDS` | `5.0` | Per-provider-request timeout, at most 15 seconds; one SDK retry. |

Payment, history and webhook collection names must be distinct. The database and collection names accept letters, digits, `_` and `-`. The MongoDB connection string must use `mongodb://` or `mongodb+srv://`; the Orders URL must use HTTP(S). Orders is contacted when a new or failed/canceled Pay needs an order lookup and on every Checkout command; startup and health do not call Orders or Stripe.

| Collection | Index | Purpose |
| --- | --- | --- |
| `payments` | `_id` (MongoDB default) | Payment identity and compare-and-update. |
| `payments` | `ux_payments_order_id`, unique on `order_id` | One current Payment per order; concurrent creates cannot duplicate it. |
| `payment_history` | `_id` (MongoDB default) | Snapshot key `<payment UUID>:<previous version>`. |
| `payment_history` | `ix_payment_history_payment_id` on `payment_id` | Read previous versions for a Payment. |
| `stripe_webhooks` | `_id_` | Unique provider event identity. |
| `stripe_webhooks` | `ix_webhooks_pending` | Pending state and receipt time for replay. |
| `stripe_webhooks` | `ix_webhooks_fulfillment` | Fulfillment status and receipt time for STRIPE/3. |

An update matches the stored version and archives the previous snapshot in the same MongoDB transaction. This requires a replica set or sharded cluster; a standalone `mongod` can pass startup and readiness but cannot complete an update transaction. There is no public history endpoint; `get_history` is a repository operation. See [ADR-0005](docs/adr/0005-payment-optimistic-concurrency.md) and [ADR-0007](docs/adr/0007-payment-history.md).

For the local Compose database, inspect the created indexes with `docker compose exec mongo mongosh --quiet --eval 'db.getSiblingDB("ecommerce_store_payments").payments.getIndexes()'` (substitute `payment_history` for the history index).

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

Invalid path parameters return 400 `invalid_request`; malformed JSON returns 400 `invalid_json`; unsupported request media returns 415 `unsupported_media_type`. Pay and Checkout accept no request body. Unknown routes return 404 `route_not_found`; wrong methods return 405 `method_not_allowed`. Internal errors return a generic 500 `internal_error` without exception details. Orders failures map to 502 or 504 with distinct codes. The [ADR-0010](docs/adr/0010-safe-public-errors.md) records the public error policy.

## Runtime container

From the repository root with Docker Compose available:

```bash
docker compose up --build -d --wait
docker compose port api 8080
# Open the printed localhost address with /health/ready or /swagger.
docker compose down --volumes
```

Compose starts MongoDB 8 as a single-node replica set, waits for a primary and then starts the API. MongoDB has no published port or authentication in this local stack. The API port is assigned dynamically on localhost. `down --volumes` removes local payment data. To serve actual Pay requests, run Invoice separately and set `PAYMENTS_ORDERS_API_BASE_URL` to its reachable URL (the default from the container is `http://host.docker.internal:8080`). No Orders connection is required for startup or health checks.

`bash scripts/ci.sh container` builds and smoke tests an isolated Compose project, checks `/health/live`, `/health/ready` and `/openapi.json`, and removes its test volume. The image uses locked runtime dependencies, a pinned Python patch and a non-root UID; development tools and `.env` are excluded. See [ADR-0017](docs/adr/0017-runtime-container-and-local-compose.md).

For a quick API probe after startup, use the localhost address printed by `docker compose port api 8080` (or `http://127.0.0.1:8000` for the uvicorn command above):

```bash
base_url=http://127.0.0.1:8000 # use http://$(docker compose port api 8080) for Compose
order_id=00000000-0000-0000-0000-000000000001 # replace with an existing Created order in Invoice
curl --fail --show-error "$base_url/health/ready"
curl --show-error -i -X POST "$base_url/payments/$order_id/pay"
curl --show-error -i "$base_url/payments/order/$order_id"
```

The Pay command needs an Invoice API reachable at `PAYMENTS_ORDERS_API_BASE_URL`, with the requested order in `Created` state. A 404 for an unknown order, 409 for a nonpayable order, 502 for an invalid/unavailable Orders response or 504 for an Orders timeout is expected; check the safe `code` in the problem response. If the process fails at startup, check the MongoDB URI, reachability and index creation. If readiness changes from 200 to 503, check MongoDB connectivity; liveness deliberately does not probe it. A standalone MongoDB may pass readiness but fails transaction-backed payment retries, so use the replica-set Compose stack for local writes. With Compose, `docker compose logs api mongo mongo-init` shows startup and replica-set errors.

## Quality checks

The Invoice OpenAPI snapshot in `contracts/invoice/openapi.json` came from its successful CI artifact at commit `03a0ce67d55091c8593a078f3b8977e4cd836dfd`. After syncing, run `bash scripts/ci.sh orders-client` to verify that Kiota 1.34.1 regenerates exactly the committed client. The script downloads the pinned Linux binary when Kiota is absent and checks its SHA-256; set `KIOTA_BIN` to use a local executable. The Infrastructure integration suite pulls the [matching Invoice image](https://hub.docker.com/r/mb0101/ecommerce-store-invoice-api) by digest and checks a seeded order against MongoDB. Docker is required for that test. Unit and acceptance tests keep a controlled Orders transport for adverse responses.

With Bash (Git Bash/WSL on Windows), run `bash scripts/verify.sh` for the same stages as CI. Docker must be running for Application, Infrastructure, Acceptance and container smoke. The audit needs access to the OSV vulnerability service. After `bash scripts/ci.sh sync`, run a focused source/build stage with `bash scripts/ci.sh format`, `lint`, `types`, `architecture`, `orders-client`, `links`, `openapi`, `build`, `audit`, or `container`; run a test suite with `bash scripts/ci.sh suite domain` (or `application`, `infrastructure`, `externalproviders`, `acceptance`).

| Suite | Tests exercised | Coverage |
| --- | --- | --- |
| `domain` | Payment and Money unit tests | Domain, minimum 70% line coverage. |
| `application` | Service unit tests and real MongoDB Pay flow | Application, minimum 70% line coverage. |
| `infrastructure` | Mapper/settings/repository and Orders boundary unit tests; real MongoDB and pinned Invoice image integration | Entire handwritten Infrastructure, minimum 70% line coverage. |
| `externalproviders` | Orders HTTP boundary unit tests, also included in Infrastructure | Infrastructure clients, report only. |
| `acceptance` | API and architecture unit tests, health integration and pytest-bdd HTTP scenarios with real MongoDB | API, report only. |

Each suite writes `junit.xml`, `coverage.xml`, `htmlcov/` and `summary.md` to `artifacts/verification/<suite>/`. The runner removes stale reports first, fails on zero tests or missing/invalid reports, and writes the Markdown summary into the CI job summary. The Invoice image integration test additionally needs Docker Hub access; `orders-client` needs the pinned Kiota binary or a download from GitHub. A focused unit suite can run without Docker, while the full `verify.sh` also runs container smoke and the network-backed dependency audit.

In PowerShell, the equivalent individual commands are:

```powershell
uv lock --check
uv sync --locked --all-groups
uv run --no-sync ruff format --check .
uv run --no-sync ruff check .
uv run --no-sync pyright
uv run --no-sync python scripts/check_architecture.py
bash scripts/ci.sh orders-client # Bash/WSL and pinned Kiota binary
uv run --no-sync python scripts/generate_operation_links.py --check
uv run --no-sync python -m scripts.export_openapi
uv run --no-sync python -m scripts.run_suite domain
uv run --no-sync python -m scripts.run_suite application # requires Docker
uv run --no-sync python -m scripts.run_suite infrastructure # requires Docker
uv run --no-sync python -m scripts.run_suite externalproviders
uv run --no-sync python -m scripts.run_suite acceptance # requires Docker
uv build --wheel --no-sources --clear
uv run --no-sync python scripts/verify_wheel.py
```

CI runs on pull requests and pushes to `main`. Its source/build job checks the lockfile, formatting, lint, types, architecture boundaries, regenerated Orders client, operation links, generated OpenAPI and wheel installation. Five named jobs run Domain, Application, Infrastructure, ExternalProviders and Acceptance with JUnit, Cobertura XML, HTML coverage and Markdown summaries under ignored `artifacts/verification/<suite>/` directories, uploaded as separate CI artifacts. Domain, Application and the full Infrastructure package each require at least 70% **line** coverage; ExternalProviders and Acceptance publish coverage without a threshold. The Infrastructure suite includes Orders adapter tests, repeated independently in ExternalProviders for its boundary report. The quality gate requires all five suites, source checks, dependency audit, secret scan and the PR dependency review; only then does the container job build, smoke test against a local MongoDB replica set and scan the same runtime image. A failed check, zero tests, missing/wrong report, failed coverage gate or failed container smoke/scan fails the final CI gate. See [ADR-0015](docs/adr/0015-suite-reporting-and-coverage.md), [ADR-0017](docs/adr/0017-runtime-container-and-local-compose.md), [ADR-0018](docs/adr/0018-security-and-image-gate.md) and [ADR-0019](docs/adr/0019-ci-graph-and-dockerhub-publication.md).

MongoDB suites use Testcontainers, give each test or scenario a separate database, and remove each database after use. Acceptance uses controlled Orders and Stripe HTTP transports while exercising the real adapters, SDK and FastAPI lifecycle. The [acceptance matrix](docs/acceptance-matrix.tsv) links source scenarios to operation, cause, status, code and requirement; see [ADR-0011](docs/adr/0011-acceptance-isolation.md).

Generate the operation projection with `uv run --no-sync python scripts/generate_operation_links.py --output operation-links.json`. The JSON links each published operation ID to its source service flow (including called branches), reachable domain policies and acceptance scenario IDs. The generator reads routes, method bodies, policy docstrings, the acceptance matrix and feature scenarios; the `links` CI stage fails on missing, duplicate or stale links. The generated JSON is an on-demand artifact for documentation tooling and is not checked in. See [ADR-0012](docs/adr/0012-generated-operation-links.md).

Run `bash scripts/ci.sh openapi` to export and lint the database-free OpenAPI at `artifacts/verification/openapi.json` (or `uv run --no-sync python -m scripts.export_openapi --output <path>`). OpenAPI 3.1 validation and operation/scenario status, media and schema checks use pinned development dependencies in `uv.lock`. Acceptance tests validate each observed HTTP body against its declared JSON Schema, with the unmatched-route response checked against the shared problem schema. CI uploads the generated JSON as `payments-openapi`. The API documents path validation as 400, matching runtime, instead of FastAPI's default 422. See [ADR-0013](docs/adr/0013-generated-openapi-contract.md).

After the full quality gate, container smoke and Trivy scan succeed on a `main` push, CI publishes the scanned image to [Docker Hub](https://hub.docker.com/r/mb0101/ecommerce-store-payments-api) as `mb0101/ecommerce-store-payments-api:<full commit SHA>` and `:latest`. It checks both tags reference the scanned local image and that Docker Hub reports the same digest for each push. Pull requests build and scan but never log in or publish. Configure repository secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` with Docker Hub push rights; an absent or invalid credential fails the main push. The image digest and tag are recorded in the job summary. See [ADR-0019](docs/adr/0019-ci-graph-and-dockerhub-publication.md).

## Security policy

`bash scripts/ci.sh audit` checks the entire locked dependency set, including development tools, and fails on any reported vulnerability or audit error. On pull requests, Dependency Review rejects newly introduced HIGH/CRITICAL vulnerabilities; GitHub Dependency Graph must be enabled in the repository's [security settings](https://github.com/MichalBoczula/ECommerceStorePayments/settings/security_analysis). On `main` pushes that PR-only job is expected to be skipped. Gitleaks scans Git history and blocks detected secrets. Trivy scans the smoke-tested image for OS and library HIGH/CRITICAL vulnerabilities with available fixes (`ignore-unfixed: true`); a scan failure also blocks. All of these results are required by the final CI gate. The exact policy and the pytest security update are in [ADR-0018](docs/adr/0018-security-and-image-gate.md).

## Generated API clients

The Orders Kiota client lives under `src/ecommerce_store_payments/infrastructure/clients/orders/generated` and is regenerated from the pinned Invoice OpenAPI. Its generated files are excluded from Ruff, Pyright and coverage; the handwritten adapter, decimal parser, request adapter and all other Infrastructure source remain inside the 70% gate. Regeneration uses `bash scripts/ci.sh orders-client` after `sync`; see ADR-0016 for source provenance and version pins.

## Engineering documentation

- [Agent and contributor instructions](AGENTS.md)
- [Definition of done](docs/definition-of-done.md)
- [Technical backlog](TECHNICAL_TODO.md)
- [Stripe checkout runbook](docs/stripe-checkout.md)
- [Real Stripe sandbox request smoke](docs/stripe-sandbox-smoke.md)
- [Real sandbox Visa payment, webhook and invoice smoke](docs/stripe-card-smoke.md)
- [Stripe webhook runbook](docs/stripe-webhooks.md)
- [Architecture decisions](docs/adr/README.md)

## Verified payment fulfillment

After a verified Stripe success, a separate durable worker marks the matching order Paid and creates or retrieves its completed invoice. Webhook responses remain fast; receipt processing does not call Orders or Invoice. Progress, leases, retry times and safe failure codes are stored in the webhook ledger. Payments public Pay/Get/Checkout contracts are unchanged.

Run a bounded batch with:

```bash
uv run --locked python -m ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments --limit 100
```

Use the same Payments database and a reachable Invoice base URL. No Stripe API key is needed for already-verified receipts. See the [fulfillment runbook](docs/payment-fulfillment.md) for inspect/resume, retry limits and the scheduled Container Apps Job deployment contract. Azure provisioning is DEP/6. Existing local `file://` PDFs require DEP/7 for durable cloud downloads.

The Infrastructure suite pulls the scanned, published Invoice STRIPE/3 image by immutable digest for its real API/PDF fulfillment test. Image provenance is recorded in `contracts/invoice/source.json`; Invoice CI run 36797439907 verified and published the merged revision. The original published-image Orders contract test remains pinned separately. No upstream source build or new Python dependency is required.
