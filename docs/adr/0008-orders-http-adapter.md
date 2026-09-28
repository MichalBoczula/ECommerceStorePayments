# ADR-0008: Validate Orders at the HTTP boundary

Status: Accepted
Date: 2026-09-27

## Context

Payments creates its own state using an order's total. An incorrect currency scale, wrong order ID, mixed-currency lines, or malformed response must never become a persisted payment. The previous Orders adapter multiplied all totals by 100 and passed transport failures through to the API.

The current Orders/Invoice contract declares `GET /orders/{orderId}` (`GetOrderById`) returning `OrderResponseDto` with `id`, `status`, `totalAmount`, `totalCurrency` and `lines`. Each line includes `lineTotalAmount` and `productVersion.priceCurrency`. Its documented failure responses include 400, 404 and 500. The contract was checked against the [generated OpenAPI artifact](https://github.com/MichalBoczula/ECommerceStoreInvoice/actions/runs/36257386063) (2026-09-26), the [Orders endpoint](https://github.com/MichalBoczula/ECommerceStoreInvoice/blob/master/src/ECommerceStoreInvoice.API/Endpoints/OrdersEndpoints.cs), [response DTO](https://github.com/MichalBoczula/ECommerceStoreInvoice/blob/master/src/ECommerceStoreInvoice.Application/Common/ResponsesDto/Orders/OrderResponseDto.cs) and [acceptance scenario](https://github.com/MichalBoczula/ECommerceStoreInvoice/blob/master/tests/ECommerceStoreInvoice.Acceptance.Tests/Features/Orders/GetOrdersByIdSuccess/GetOrdersByIdSuccess.feature) on 2026-09-27. OpenAPI declares these decimal amounts as JSON numbers; the adapter parses the received numeric tokens as `Decimal`.

## Decision

Keep a small typed HTTP adapter behind `OrderReader`. Parse numeric JSON tokens as `Decimal`, require the requested ID, a nonblank status, a positive total and nonempty lines, and check that line totals add exactly to the order total and all line currencies match its currency. Reject malformed or inconsistent responses before constructing `Money`.

Convert the total to integer minor units using an explicit ISO 4217 exponent table. Initially support PLN, EUR, USD, GBP, CHF (two), JPY, KRW (zero), and BHD, JOD, KWD, OMR, TND (three). Unknown codes and amounts that cannot be represented exactly fail closed. The table is an Orders boundary conversion policy, not a promise that a future Stripe integration can charge every listed currency; provider capabilities will be checked in STRIPE/1.

Set a bounded Orders timeout in configuration. A 404 becomes `OrderNotFoundError`. Timeouts become `OrderTimeoutError` (HTTP 504); transport failures, non-200/404 statuses and invalid payloads become typed errors (HTTP 502). Do not expose upstream bodies or connection information in those errors. Keep the existing 404 and business status mapping. The full problem+json error contract remains PAY/10.

## Consequences

The adapter makes one GET and creates no payment on a failed or inconsistent response. The payment domain remains independent of HTTP and the Orders DTO. Newly supported currencies require reviewing the ISO exponent and the eventual provider capability; there is no implicit two-decimal fallback. Both the API and the Orders boundary have focused failure tests.

## Alternatives considered

- Default all unknown currencies to two decimals: can silently charge the wrong amount.
- Add Kiota and its runtime for this single stable GET now: creates generated code and dependency overhead without removing currency, consistency, or failure-policy decisions. Revisit if the Orders contract grows.
- Read `totalAmount` as a binary float: risks a rounding mismatch during conversion to integer minor units.

## Later evolution

[ADR-0016](0016-invoice-kiota-orders-client.md) introduced a generated Kiota client behind this same `OrderReader` port after Invoice published a pinned contract and image. Its handwritten boundary still enforces this ADR's monetary conversion, consistency and error rules; the alternative of deferring Kiota describes the PAY/8 implementation, not the current transport.
