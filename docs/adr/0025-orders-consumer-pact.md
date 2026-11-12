# ADR-0025: Consumer-owned Orders Pact through the production adapter

Status: Accepted
Date: 2026-11-03

## Context

PACT/08 starts the contract-registry pilot at Payments -> Invoice `GET /orders/{orderId}`.
The pinned provider OpenAPI used to generate Kiota describes the offered API. Payments must
also record what its own adapter actually consumes, independently of that provider schema.
A mock returning a DTO or a duplicate handwritten HTTP client would miss request-builder,
wire-deserialization, precise-number and application-mapping failures.

## Decision

Pin official `pact-python==4.2.0` as a development-only dependency; `uv.lock` also fixes the
native Pact FFI dependency. Use Pact specification 4 HTTP, consumer `payments`, provider
`invoice`, matching the registry's logical application IDs. Keep generated output ignored.
No runtime dependency, public endpoint, persistence schema or production adapter changes.

`test_orders_pact.py` began with five consumer-owned interactions for four Created orders in PLN,
JPY, KWD and USD, and a 404. Each state has a fixed requested UUID and explicit seed parameters.
Success bodies include only fields read by HttpOrderReader: id, status, totalAmount,
totalCurrency, lines[].lineTotalAmount and lines[].productVersion.priceCurrency. Exact fixture
values keep IDs, total/line arithmetic, currency and status consistent for provider states;
provider-only metadata is not a required field. The error contract only needs status 404,
problem+json and a parseable problem object; unrelated trace IDs and text are not constrained.

Every request uses the real OrdersClient, OrdersRequestAdapter, PreciseOrderJsonFactory and
HttpOrderReader with HTTPX over an ephemeral loopback Pact server. Tests assert the complete
OrderPaymentDetails, including exact minor-unit integer, currency and status, plus the typed
OrderNotFoundError. Pact rejects unmatched/missing requests on server exit. No Invoice,
registry, MongoDB, provider OpenAPI or replacement transport is used to generate expectations.

Run the complete interaction set twice on fresh servers and compare the official writer's
bytes. Publish only after all mappings, mock-server checks and reproducibility assertions
pass. A manifest records specification/tool versions, interaction count and SHA-256 of the
unmodified Pact file. GitHub's artifact/run identifies its source revision; this is separate
from content identity, which can stay identical across consumer commits.

The existing required ExternalProviders job generates and uploads `payments-invoice-pact`
(Pact plus manifest), while its existing report and quality/final gates remain mandatory.
The Infrastructure suite also executes these tests with its existing coverage policy.
The focused `bash scripts/ci.sh pact` command clears its output before running, preventing
old files from satisfying a failed generation. Suite outputs use separate Pact directories.

Malformed responses, missing consumed fields, timeout/outage and very large decimal precision
remain local HTTP boundary tests. In particular, Pact FFI's JSON number representation can
round very large decimal examples; the 29-digit preservation regression stays in the existing
precise-parser tests. It must not become a rounded example or a false provider obligation.

### PACT/10 fulfillment extension

The same artifact adds five interactions through `HttpFulfillmentOrders` and
`HttpFulfillmentInvoices`. Their provider states are independent.

| Request | Provider state and consumer requirement |
| --- | --- |
| `GET /orders/{orderId}` | Seed a Paid order with the supplied client and exact order money. Payments reads the order owner, Paid status and precise minor-unit amount. |
| `PATCH /orders/{orderId}/status` | Seed a Created order. Payments sends `{"status":"Paid"}` and expects HTTP 200. The worker reads the order separately to reconcile its status. |
| `GET /invoices/by-order/{orderId}` | Seed a completed invoice with the supplied invoice, order and client-data version IDs. The adapter validates the invoice response and maps it to `CompletedInvoice`. |
| `GET /invoices/by-order/{orderId}` | Keep the order without a completed invoice. The adapter maps HTTP 404 to `None`. |
| `POST /invoices/{clientId}/{orderId}` | Seed the supplied Paid order and its client-data version with no invoice. The bodyless request returns HTTP 200 and a completed invoice. |

Both invoice success responses require `id`, `orderId`, `clietDataVersionId`,
`storageUrl` and `createdAt`. The wire spelling `clietDataVersionId` matches
the existing DTO. The creation matcher accepts the generated invoice UUID.
Both responses require a nonblank storage URL and an ISO timestamp with an offset
or `Z`. The order and client-data version IDs match the supplied fixture.

## Consequences

The producer artifact contains ten deterministic interactions and detects mapping
and request changes in Payments CI. Invoice can pin the published artifact to
replay the expanded contract against its API and publish exact-version evidence.

## Alternatives considered

- Generate expectations from Invoice OpenAPI: shares the provider's assumptions and hides
  missing consumer requirements; retain OpenAPI for Kiota generation only.
- Direct DTO construction or MockTransport for the Pact pilot: bypasses the Pact HTTP server;
  retain controlled transports for local resilience tests only.
- Add a custom matching engine or a running central-registry dependency: official Pact owns
  matching, and consumer tests can run before registry deployment.

References: [official consumer guide](https://pact-foundation.github.io/pact-python/consumer/),
[Pact specification](https://docs.pact.io/getting_started/specification),
[registry backlog](https://github.com/MichalBoczula/ECommerceStore.Pact/blob/main/TECHNICAL_TODO.md).
