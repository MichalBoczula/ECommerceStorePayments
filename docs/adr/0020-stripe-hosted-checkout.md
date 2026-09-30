# ADR-0020: Reserve and recover Stripe test checkout attempts

Status: Accepted
Date: 2026-10-01

## Context

The existing Pay command prepares or renews a Payment, and WEB/12 depends on that contract. Stripe creation is an external write that cannot participate in a MongoDB transaction. Concurrent calls, a lost provider response or a failed database save must not create additional sessions for one attempt. Stripe idempotency keys have a finite retention period.

## Decision

Keep Pay/Get responses unchanged and add bodyless `POST /payments/{order_id}/checkout`, operation ID `createOrderCheckout`. It returns HTTP 200 with a nested Payment response, nullable `checkout_url`, `checkout_status` and `expires_at`. Application orchestrates the use case through `CheckoutProvider`; Infrastructure owns the pinned Stripe Python SDK 15.6.1 and explicit API version `2026-08-26.dahlia`.

Use hosted Checkout in test mode with card payments. The initial provider policy supports PLN, a 200-minor-unit minimum and a conservative demo maximum of 99,999,999 minor units. This is a demo policy, not a catalogue of every Stripe currency or maximum. Orders remains the source of the amount, with the existing exact-decimal/currency validation. Stripe uses one aggregate order line with quantity one, preserving the server total without re-reading current product prices. Discounts, shipping and automatic tax are not enabled. Return URLs are fixed server configuration, with HTTPS outside loopback hosts. Live secret keys are rejected.

Before each checkout request, re-read Orders and require Created status and matching Money. Unsupported money fails before creating a Payment. The existing service has no authenticated customer principal and Orders' payment port has no ownership field: this task preserves that boundary and does not claim production customer authorization. BFF/UI identity work remains separate.

Reserve a UUID `checkout_attempt_id` and `checkout_started_at` on the Created aggregate, then persist the reservation using the existing optimistic transaction/history mechanism before calling Stripe. Repeated reservations are no-ops. A provider key `checkout:<payment ID>:<attempt UUID>` and metadata on both Session and PaymentIntent link the provider objects to that attempt. Concurrent reservation losers use the persisted winner. SDK requests use a bounded timeout and at most one network retry. A lost response or failed session save leaves a recoverable Created reservation; retry replays the same key and request. Successful session creation persists Pending and the session ID. Concurrent session-save losers accept only the matching Pending winner.

For Pending, retrieve and validate the existing session instead of creating another. Validate test mode, session identity, amount, currency, reference and attempt metadata. Expose only an open hosted checkout URL on `checkout.stripe.com`; complete/expired sessions return no checkout URL. Neither retrieval nor browser navigation changes Payment to Succeeded or Orders to Paid. A verified webhook will establish success in STRIPE/2.

Created reservations older than 23 hours require reconciliation rather than another provider write, preventing replay after Stripe may prune an idempotency key. Legacy Pending records without attempt identity also require reconciliation. Do not reset an ambiguous attempt automatically. Failed/canceled retry uses the existing Payment ID and clears the old reservation so the next checkout reserves a fresh UUID.

The new fields are optional on legacy current/history documents and default to None. Snapshot validation requires the attempt UUID and its aware timestamp together, with a valid timestamp range. Mapper/history updates preserve the reservation; existing indexes are sufficient. Internal attempt fields remain absent from the public Payment contract.

## Consequences

Checkout is disabled by default, keeping existing consumers and CI independent of Stripe credentials. Enabling it requires an explicit test secret. The lifespan closes owned Stripe transport along with other clients. Stable safe problem codes distinguish disabled checkout, unsupported money, reconciliation, unavailable state, provider failure and timeout.

Ordinary tests use the actual Stripe SDK with a controlled HTTP boundary, plus real MongoDB transactions in integration/acceptance. A real-account test-mode smoke check is documented separately and requires the operator's account configuration. No real credentials are committed.

Keep return URLs, API version, SDK behavior and request parameters unchanged while an unresolved reservation is being recovered. Stripe rejects a reused key with different parameters; reconcile outstanding attempts before changing that configuration. A permanently rejected request or expired session cannot be automatically renewed by this task; verified terminal transitions/reconciliation belong to STRIPE/2. Signature handling, fulfillment, Angular checkout UI and deployment remain STRIPE/2-4 and DEP work.

## Alternatives considered

- Change Pay to create sessions: changes existing WEB/BFF behavior before STRIPE/4.
- Generate a random key on every HTTP call: duplicates sessions after retries.
- Derive a key from the current storage version alone: later writes change that version and do not preserve attempt identity.
- Trust return URLs or amounts from the browser: lets the caller alter payment destinations or pricing.
- Retry an unresolved attempt indefinitely: a pruned provider key can create a new session.
- Confirm payment from Checkout return/retrieval: skips the verified webhook state policy.

References: [Checkout creation](https://docs.stripe.com/api/checkout/sessions/create), [idempotency](https://docs.stripe.com/api/idempotent_requests), [currency rules](https://docs.stripe.com/currencies), [Stripe Python](https://github.com/stripe/stripe-python).
