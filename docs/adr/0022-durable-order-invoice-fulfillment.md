# ADR-0022: Durable Orders and invoice fulfillment

Status: Accepted

Date: 2026-10-01

## Context

STRIPE/2 confirms Payment and atomically records fulfillment intent. Orders and Invoice are independent HTTP services: a timeout can occur after a committed downstream write. Repeated Paid is 400 and invoice creation conflicts are 409, including active generation leases. A process timer cannot recover work when the HTTP service scales to zero.

## Decision

- Keep the existing Applied success receipt as the durable work record; do not add another queue or collection. Add optional fulfillment fields for attempts, lease identity/expiry, next retry, safe error, Paid progress/client association, completed invoice/client-data-version IDs and completion time. Older pending markers remain claimable; missing attempts start at zero.
- Application `FulfillmentService` orchestrates Payment reads and two new ports: `FulfillmentOrders` and `FulfillmentInvoices`. Infrastructure adapters use the same regenerated Kiota client and exact decimal parser. No SDK, HTTP, BSON or container dependency enters Application/Domain. No Payment domain transition or Payments public DTO changes.
- A worker atomically claims Applied successful work with a majority-acknowledged MongoDB update. The 300-second lease has a fresh UUID fencing token; every progress/failure/completion write requires the matching unexpired lease. The application bounds each attempt to 120 seconds. A killed worker's lease expires; another run can claim and reconcile. Leases coordinate local state; Invoice's unique order reservation and order transition policy protect downstream writes if workers overlap after an expired lease.
- Validate the Succeeded payment/attempt/order/Money association before downstream calls. Read the authoritative order, validate exact total and owner, then mark Created as Paid. Always read back Paid, including after 400/409/timeout/5xx. Created after a rejected write remains a failure; Cancelled, changed total/owner and regressed Paid state require repair. Save Paid progress before invoice work. Never cancel orders or call Stripe to charge again.
- Read the completed invoice by order before creation and after ambiguous creation errors. Invoice PR [#217](https://github.com/MichalBoczula/ECommerceStoreInvoice/pull/217) exposes `GET /invoices/by-order/{orderId}` through its existing completed-only repository/descriptor policy. Missing/Generating/Failed returns 404. Creation still enforces order owner and selects the client's latest data version under existing Invoice semantics; Payments passes the order's client ID, validates invoice/order/UUIDs, and persists the returned `clietDataVersionId` (the existing wire spelling). Invoice leases, unique OrderId and PDF recovery remain authoritative.
- Retry recoverable failure with persisted delays 60, 120, 240, 480, 960, 1920, then at most 3600 seconds. Ten attempts exhaust into Failed; configuration/association errors fail immediately. Persist safe codes only. Completion records the invoice ID; webhook redelivery cannot reopen it. A failed work item can be explicitly resumed after operator repair, retaining Paid progress.
- Use a bounded one-shot CLI command that first recovers verified Pending receipts, then fulfills due work. It uses the existing runtime image without Stripe API credentials, closes resources and exits. Receipt failures do not starve other receipts or fulfillment; they cause a nonzero exit after the batch. Persisted downstream retries are normal batch outcomes and require inspection/monitoring of Failed work.
- Choose a scheduled Azure Container Apps Job every five minutes while the demo is enabled, one replica/parallelism, same private network, database and downstream configuration, with the CLI command override. Scheduled UTC execution can start independently of the HTTP app's replicas. Infrastructure creation and cost validation stay in DEP/2/6; no Azure resource is created here. The schedule adds idle executions and downstream cold starts, so it must be included in the portfolio budget and disabled with the demo when unused.
- Add due-time and lease-expiry indexes alongside the existing ledger indexes. No TTL removes recovery state. Source-pin Invoice `3b66b6b856773ca9cae0ac59647fd8b73cffd08f` in the container verification helper. The OpenAPI snapshot is generated from the matching API routes/DTOs (image-only OpenSSL update does not change the contract), hash-pinned and regenerated with Kiota 1.34.1. Keep the older published-image Orders read test as independent backward compatibility evidence.

## Consequences

Fulfillment is eventually consistent. The webhook can return 200 while the order still awaits the next worker run; the browser must poll authoritative state in STRIPE/4. A failed invoice cannot undo payment success, and a restart cannot lose work. Manual inspect/resume uses database/operator access without an unsigned public retry endpoint. Downstream state reconciliation and existing uniqueness rules provide one logical Paid order/invoice; HTTP requests may repeat.

Local `file://` invoice storage and current authentication limitations remain. Cancellation racing a successful payment requires operator repair; automatic refunds and live payments are outside this MVP. Ten-minute Invoice leases can outlive a Payments worker; 409 plus a missing completed invoice remains retryable until the upstream lease is recoverable.

## Alternatives considered

- Fulfill inside the webhook: slows acknowledgment and couples provider delivery to PDF/network availability.
- Add only an in-process background timer: does not recover at zero replicas or after process loss.
- Treat 400/409 as unconditional success: cannot distinguish Paid/completed state from an invalid order or active invoice lease.
- Add a broker now: the existing atomic ledger and independently scheduled worker meet the MVP's recovery needs.

References: [Stripe fulfillment](https://docs.stripe.com/checkout/fulfillment), [Container Apps Jobs](https://learn.microsoft.com/azure/container-apps/jobs), [Invoice recovery ADR](https://github.com/MichalBoczula/ECommerceStoreInvoice/blob/master/docs/adr/0003-invoice-pdf-and-recovery.md).
