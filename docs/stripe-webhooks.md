# Stripe test webhook runbook

STRIPE/2 confirms Payments using verified Checkout notifications and stores durable fulfillment work. Orders remains Created until the separate STRIPE/3 fulfillment worker runs. See [ADR-0021](adr/0021-verified-stripe-webhooks.md).

## Secrets and configuration

| Source | Payments runtime setting | Purpose |
| --- | --- | --- |
| GitHub secret `STRIPE_SECRET` or your local test API key | `PAYMENTS_STRIPE_SECRET_KEY` | `sk_test_...` for creating hosted checkout. |
| Stripe CLI listener or Dashboard test endpoint secret | `PAYMENTS_STRIPE_WEBHOOK_SECRET` | `whsec_...` for verifying deliveries to this endpoint. |
| GitHub `STRIPE_PUBLISHABLE_KEY` | Unused in the current hosted URL redirect | Required only if a future frontend integration uses Stripe.js. |

Ordinary CI uses the real SDK with controlled responses and signed fixtures, never account secrets. GitHub secret names are not runtime environment variables automatically. The separate [sandbox request smoke](stripe-sandbox-smoke.md) explicitly maps `PAYMENTS_STRIPE_SECRET_KEY: ${{ secrets.STRIPE_SECRET }}` for real session creation/retrieval/expiration. It does not test webhook delivery; the account payment smoke needs an appropriate endpoint signing secret. Do not add these credentials to ordinary unit/container suites. Azure runtime secret injection belongs to deployment/Key Vault work.

Compose forwards `PAYMENTS_STRIPE_WEBHOOK_SECRET` from your ignored `.env` or shell. An empty value disables webhook verification with 503. The signing secret alone enables receipt; it does not require an API key or enable checkout creation. Keeping receipt independent permits outstanding checkouts to finish while creation is disabled. New checkouts explicitly request `card` and `blik`, in PLN, with automatic capture. BLIK is already enabled in the user's account; no account settings are changed by this code.

## CLI and real-account card/BLIK smoke

1. Run the portfolio stack with a reachable Payments URL and a Created PLN order. Follow [checkout setup](stripe-checkout.md). With Compose's random port, find it using `docker compose port api 8080`; substitute the printed port below.
2. Run `stripe login`, then forward the four subscribed snapshot events:

   ```bash
   stripe listen --events checkout.session.completed,checkout.session.async_payment_succeeded,checkout.session.async_payment_failed,checkout.session.expired --forward-to http://localhost:8080/payments/webhooks/stripe
   ```

3. Privately configure `PAYMENTS_STRIPE_WEBHOOK_SECRET` with the `whsec_...` printed by that listener and restart Payments. Use the CLI listener secret for CLI forwarding, not the Dashboard endpoint secret. For a deployed endpoint, register the actual HTTPS URL for **Your account**, test mode, snapshot payloads, and API version `2026-08-26.dahlia`; configure its own signing secret.
4. Create a session through bodyless `POST /payments/<order ID>/checkout`. Open its hosted URL, verify the server amount, and complete a **test card** payment using Stripe's documented test values. Confirm CLI delivery receives 200, `GET /payments/order/<order ID>` returns Succeeded, and its PaymentIntent/session IDs match the dashboard. Inspect the receipt and one pending fulfillment marker.
5. Repeat with a new order and select **BLIK**. Use the test flow described in [Stripe's BLIK guide](https://docs.stripe.com/payments/blik/accept-a-payment); verify the same amount, signed delivery and Succeeded result. Check both methods are visible on newly created sessions. A previously reserved version 1 attempt remains card-only during recovery; use a new order for this check.
6. Redeliver an event using the CLI/Dashboard resend facility appropriate to the registered destination. Confirm 200 with no additional payment version/history or fulfillment marker. Test a rejected card/BLIK attempt while the Checkout remains open: it must not cancel the order or falsely establish success. Expire an abandoned session and check Payment Failed with `checkout_expired`, while Orders stays Created. Browser success/cancel navigation alone must not change Payment state.
7. Record nonsecret evidence (commit, event/order/session IDs, method, HTTP status, state/history counts) in review notes. Account smoke is not established by local signed fixtures. `stripe trigger` creates unrelated fixtures without our reserved Payment metadata and is insufficient to demonstrate our purchase flow.

BFF webhook proxy wiring remains STRIPE/4. Until then, forward directly to Payments; a future proxy must preserve the original body and signature header.

## Persistence, retry and inspection

Default collection: `stripe_webhooks`, configurable with `PAYMENTS_MONGODB_WEBHOOK_COLLECTION_NAME`. Its implicit `_id` index deduplicates events. Named pending/fulfillment indexes support inspection and bounded recovery. HTTP processing has a 10-second deadline; timeout returns a retryable 503 and can be safely redelivered. A receipt contains normalized identifiers/Money, digest, event outcome, Pending/Applied/Ignored/Rejected state, reason, receipt/completion times and optional `fulfillment_status=pending`; no raw event/customer/card/BLIK details are saved. Keep collections distinct and retain transaction-capable MongoDB.

Payment success, its history snapshot and Applied receipt/fulfillment marker commit together. Receipt-only interruption or transaction rollback remains Pending. Stripe redelivery resumes it. To recover pending work after interruption or exhausted provider delivery retries, run with the service's database configuration:

```bash
uv run --locked python -m ecommerce_store_payments.infrastructure.persistence.mongodb.replay_webhooks --limit 100
```

For a running Compose service:

```bash
docker compose exec api python -m ecommerce_store_payments.infrastructure.persistence.mongodb.replay_webhooks --limit 100
```

This is an operator recovery command, not a public unsigned endpoint. It reads only previously verified receipts, processes a bounded batch, makes no provider/Orders/Invoice calls, and exits nonzero on failure. It does not execute pending fulfillment. STRIPE/3 provides durable fulfillment through its separate worker; scheduled Azure provisioning remains DEP/6.

Applied success is monotonic within the reserved attempt. Expiry/failure after success is ignored; late success for the same attempt can recover failure. Old attempts are ignored after retry. Unknown events, unpaid completion and already-applied notifications are ignored; mismatched Money/order/session/payment IDs are rejected in the ledger without mutating Payments. Inspect reasons before manual reconciliation; do not delete state to force a second charge.

| HTTP / code | Action |
| --- | --- |
| 200 / `{"received":true}` | Receipt completed durably; inspect ledger for Applied/Ignored/Rejected. This does not promise Orders/invoice fulfillment. |
| 400 / `webhook_invalid` | Check original bytes, one signature header, timestamp, endpoint secret and supported test snapshot contract. No receipt is stored. |
| 400 / `webhook_collision` | Same event ID arrived with different bytes. Investigate delivery/API-version consistency; existing receipt is preserved. |
| 413 / `webhook_too_large` | Body exceeded 1 MiB; no receipt is stored. |
| 415 / `unsupported_media_type` | Send `application/json`; no receipt is stored. |
| 503 / `webhook_disabled` | Configure this endpoint's signing secret. |
| 503 / `webhook_retry`, or 500 | Retry delivery. A receipt may already be Pending; inspect/replay it after restoring persistence. |

## Automated evidence

Domain tests cover confirmation invariants, repeats and request-version migration. Application tests cover matching, stale attempts, ordering and interrupted receipt recovery. ExternalProviders tests verify actual SDK signatures, tampering, missing/expired signatures, live/wrong-account contracts and both Checkout method parameters. Real MongoDB tests cover receipt uniqueness, atomic rollback after current/history writes, recovery through a new database connection, concurrent duplicates/distinct success events and the provider-save race. BDD scenarios exercise public HTTP with real persistence and validate response schemas against generated OpenAPI. No real API or webhook secret is required by those suites.
