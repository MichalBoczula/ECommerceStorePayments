# ADR-0021: Verified Stripe webhook receipt and payment confirmation

Status: Accepted

Date: 2026-10-01

## Context

STRIPE/1 reserves an attempt before creating a provider session. A provider response or its local save can fail after Stripe accepted the request. Webhooks can arrive before that save, be delivered repeatedly, or arrive concurrently and out of order. Recording an event ID alone would lose work after a crash between receipt and processing. Payment success must leave durable work for STRIPE/3 without performing Orders/invoice calls during webhook delivery.

The user selected hosted Checkout with card and BLIK enabled in their Stripe account. Changing the request parameters of an unresolved STRIPE/1 attempt would break recovery with its existing idempotency key.

## Decision

- Publish `POST /payments/webhooks/stripe`, accepting original JSON bytes and one `Stripe-Signature` header. Limit the body to 1 MiB. Infrastructure uses the pinned Stripe SDK's signature verifier with a 300-second tolerance before parsing; duplicate JSON keys are rejected. The endpoint-specific `whsec_...` is separate from the API secret. Verification remains available when new checkout creation is disabled so active attempts can finish.
- Support own-account test-mode snapshot events. The endpoint signing secret binds the account; reject live, Connect (`account`) and organization (`context`) events. Subscribe to `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed` and `checkout.session.expired`. Validate session mode, test ID, PLN amount, metadata UUIDs and client reference. Unknown signed test events are recorded and ignored.
- Application matches Payment ID, order, Money, reserved attempt and any saved session ID. Paid completion requires a provider PaymentIntent ID. Unpaid completion remains pending; decline events for an individual card/BLIK attempt do not fail an open Checkout. Explicit session expiry/async failure marks the matching Payment Failed without canceling Orders. Stale attempts cannot change a newer attempt.
- Add a dedicated `Payment.confirm_checkout` domain command. It accepts success for the same reserved attempt, including recovery from Created or late confirmation after Failed/Canceled. Success is monotonic; repeated confirmation cannot replace provider IDs. Existing `mark_as_succeeded` transition rules are unchanged. Retry resets attempt identity, so old success is ignored after a new attempt starts. Money and rehydration invariants remain enforced.
- Store normalized receipts in `stripe_webhooks`, uniquely identified by `_id = event ID`, with a SHA-256 digest of the original bytes. Store only identifiers, Money, event/outcome, receipt/completion timestamps, state/reason and fulfillment marker. Do not store the raw event, signature, customer details, card details or BLIK code. A reused event ID with different bytes returns a safe 400 for investigation.
- Majority-acknowledge Pending receipt before processing. In one MongoDB transaction, compare the Payment version, update current state and history when changed, and complete the receipt as Applied/Ignored/Rejected. Applied success also sets `fulfillment_status=pending` in that transaction. Separate event IDs reporting the same success do not create another logical transition or work marker. No Orders, Invoice or Stripe calls occur here.
- HTTP processing has a 10-second deadline. A crash or transaction failure leaves the receipt Pending; redelivery resumes it. Optimistic conflicts reload state with a bounded retry. Failed processing returns non-2xx, rather than acknowledging unfinished work. The bounded replay command processes persisted Pending receipts without rechecking an expired delivery signature or requiring provider credentials. A scale-to-zero retry trigger and fulfillment processor remain STRIPE/3.
- Add indexes on `(state, received_at)` and `(fulfillment_status, received_at)`. Keep ledger records without TTL so replay is not silently lost. Preserve the existing payment/history indexes and transaction requirement.
- Persist an optional positive `checkout_request_version` with each reserved attempt. Missing fields mean version 1 (card only); new requests reserve version 2 (card and BLIK). The provider preserves version 1 parameters during recovery. This field is internal, mapped through current/history and reset on retry; public Pay/Get contracts remain unchanged.

## Consequences

Success establishes authoritative Payment state and durable fulfillment intent, not Paid Orders or generated invoices. Those calls and retries belong to STRIPE/3. A browser return URL never proves success. A stale, mismatched or unrelated event is acknowledged only after its completed receipt is persisted, with its disposition available for operators.

Use the same webhook URL, API version and signing secret for a given endpoint; CLI and Dashboard signing secrets differ. An API key or enabled Dashboard payment method alone does not configure webhook delivery. Hosted Checkout requires no frontend publishable key in this flow. Real card/BLIK test-account smoke evidence remains separate from deterministic CI fixtures.

The separate sandbox card workflow uses a checksum-pinned Stripe CLI and its Checkout completion fixture on the session created by Payments. The actual account event is forwarded with the listener's ephemeral signing secret; the probe verifies receipt, runs the durable worker against the published Invoice image and replays the original signed delivery to check idempotence. Ordinary CI retains controlled boundaries. BLIK, hosted browser/3DS and deployed Dashboard endpoint checks remain separate.

## Alternatives considered

- Marking IDs processed before work: rejected because a crash would suppress unprocessed events.
- Updating payment and receipt separately: rejected because retries could leave inconsistent state or lose fulfillment intent.
- Relying on event timestamps or browser redirects: rejected because delivery order and redirect completion are insufficient evidence.
- Adding a broker or in-process background task now: deferred; local transaction and replay preserve durable work, and STRIPE/3 selects its runtime retry trigger.
- Reusing changed parameters under existing idempotency keys: rejected; request version preserves safe migration to card/BLIK.

References: [Stripe webhooks](https://docs.stripe.com/webhooks), [Checkout fulfillment](https://docs.stripe.com/checkout/fulfillment), [BLIK](https://docs.stripe.com/payments/blik), [API idempotency](https://docs.stripe.com/api/idempotent_requests).
