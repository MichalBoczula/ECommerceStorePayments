# ADR-0016: Generate the Orders client from the published Invoice contract

Status: Accepted
Date: 2026-09-28

## Context

PAY/8 introduced a small handwritten HTTP reader for `GET /orders/{orderId}` and deferred Kiota. Invoice now publishes a Docker Hub image and an OpenAPI artifact. Its Products integration uses a generated Kiota client inside Infrastructure, behind a handwritten adapter. Payments needs that same separation for Orders without changing the public Pay/Get behavior or silently rounding monetary JSON numbers.

The source is the `generated-openapi` artifact from Invoice [CI run 36437924085](https://github.com/MichalBoczula/ECommerceStoreInvoice/actions/runs/36437924085), commit `03a0ce67d55091c8593a078f3b8977e4cd836dfd`. Its SHA-256 is recorded by `scripts/verify_orders_client.py`. The matching published image is `mb0101/ecommerce-store-invoice-api@sha256:35059e4b5e3af8e3a89d61dd34d1453f9096c3892b026004d0b904b58f8be598`. The contract declares money as `number/double`, while the C# DTOs hold decimal values.

## Decision

Generate only `GET /orders/{orderId}` and its DTOs with Kiota 1.34.1 from the pinned complete Invoice OpenAPI snapshot. Commit the generated sources and lock file. `scripts/check_orders_client.sh` verifies the Kiota download SHA-256 and regenerates into a temporary sibling directory, comparing bytes with committed output in local verification and PR CI. Reviewing a new Invoice contract means updating the snapshot, pinned hash and regenerated client together.

The generated client lives in Infrastructure. `HttpOrderReader` uses its request builder and typed `OrderResponseDto` behind the unchanged `OrderReader` port. An anonymous Kiota HTTPX adapter shares the application's bounded HTTP client and base URL. A narrow JSON parse factory preserves numeric wire tokens as `Decimal`, then assigns exact total and line amounts to the generated DTO. The reader rejects non-Decimal money, inconsistent lines, currencies, IDs and statuses; it retains minor-unit conversion and maps 404, timeout, outage and invalid responses to existing application errors. The generated Python source is excluded from lint, strict type and coverage denominators; the handwritten reader, factory and request adapter remain measured and tested.

An Infrastructure integration test pulls the pinned Invoice image, starts an isolated MongoDB replica set, seeds an actual order and product snapshot, compares the served Orders schema to the pinned snapshot and calls the image through Kiota. It also checks the missing-order response. Unit/acceptance boundary tests continue to exercise malformed and adverse responses with controlled transports.

STRIPE/3 expands this same generated client to status PATCH, invoice creation and invoice lookup by order. The new complete snapshot is generated from Invoice PR #217; [ADR-0022](0022-durable-order-invoice-fulfillment.md) records its source revision and fulfillment ports. The original published-image Orders read check remains, and a source-pinned Invoice container exercises the new operations.

## Consequences

No Payments HTTP operation, persistence document/index or domain policy changes. Python adds the pinned Kiota runtime and standard HTTPX as runtime dependencies; `httpx2` remains only in tests that use the FastAPI test client. The Kiota generated model annotates money as `float` because the upstream OpenAPI uses `double`; the isolated parse factory supplies runtime `Decimal` values, and the reader checks them before doing any arithmetic. A Kiota or Invoice contract upgrade must revisit that adapter and its precision tests. The image test needs Docker and an accessible Docker Hub; a clean PR runner verifies it when local Docker is unavailable.

## Alternatives considered

Using the stock Kiota JSON factory converts monetary values to binary floats and can change minor units for large or precise amounts. Keeping the handwritten HTTP request would not exercise the generated client. Editing generated DTOs by hand would make regeneration unreliable. Changing Invoice's published schema is a separate upstream decision; this adapter preserves the current wire behavior.
