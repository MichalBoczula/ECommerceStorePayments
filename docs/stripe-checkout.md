# Stripe test checkout runbook

STRIPE/1 creates hosted Checkout sessions. STRIPE/2 adds card/BLIK support and signed webhook confirmation; STRIPE/3 adds durable Orders/invoice fulfillment. See [ADR-0020](adr/0020-stripe-hosted-checkout.md).

For a real account request without completing a payment, run the separate [sandbox request smoke](stripe-sandbox-smoke.md). It uses `STRIPE_SECRET` in GitHub Actions and exercises the actual Payments checkout adapter.

## Configuration

Keep `PAYMENTS_STRIPE_ENABLED=false` for baseline Pay/Get usage. For checkout, set these values through a local ignored `.env` or secret configuration:

- `PAYMENTS_STRIPE_ENABLED=true`
- `PAYMENTS_STRIPE_SECRET_KEY`: your account's `sk_test_...` secret, never a live/publishable key.
- `PAYMENTS_STRIPE_SUCCESS_URL`: fixed frontend return URL; default `http://localhost:4200/orders?checkout=success`.
- `PAYMENTS_STRIPE_CANCEL_URL`: fixed frontend return URL; default `http://localhost:4200/orders?checkout=cancel`.
- `PAYMENTS_STRIPE_TIMEOUT_SECONDS`: per-request timeout, default 5 seconds, maximum 15; the SDK retries at most once.

URLs must use HTTPS outside loopback hosts, without embedded credentials or fragments. These defaults return to the existing orders screen; displaying provider return state is STRIPE/4. No browser-provided destination or amount is accepted. Do not change return URL/request configuration while recovering an unresolved attempt.

Use a reachable Invoice/Orders API and a MongoDB replica set. Local Compose can receive the Stripe variables from its environment; its optional env example contains no key. An existing order must be Created, use consistent PLN snapshots and total at least PLN 2. Configure your Stripe test account for the selected currency; provider/account restrictions may still reject a request.

## Real-account smoke check

This check requires your Stripe test account, configured credentials and a running local stack. The ordinary CI provider tests use a controlled HTTP boundary and do not establish this real-account evidence.

1. Create a customer and verify registration created its cart. Add a PLN product and create an order using the existing portfolio flow.
2. Start Payments with the configuration above. Call bodyless `POST /payments/<order UUID>/checkout` through Swagger or your HTTP client; the Payments API route is available now, BFF/frontend checkout wiring comes in STRIPE/4.
3. Expect HTTP 200, nested Payment status `pending`, a test session ID and an HTTPS `checkout_url`. Verify the amount matches the order snapshot.
4. Repeat the call and verify the same Payment/session ID and checkout URL; inspect Stripe's test dashboard for one session.
5. Open the returned URL manually and confirm the expected amount/currency is shown. Stop at checkout creation when validating STRIPE/1. For signed card/BLIK completion checks, continue with the [webhook runbook](stripe-webhooks.md).
6. Record only nonsecret evidence (commit, order/session IDs, response status, displayed amount). Never paste an API key, secret-bearing configuration or payment details into a PR.

## Failure and recovery

| Code | Meaning and action |
| --- | --- |
| `checkout_disabled` (503) | Enable checkout with a valid test secret if you need this feature. Baseline Pay/Get stays available. |
| `checkout_money_unsupported` (409) | Initial policy supports PLN, minimum 200 and conservative maximum 99,999,999 minor units. Correct the demo order; never override its total in Payments. |
| `order_not_payable` / `order_total_changed` (409) | Check the authoritative order and its original payment amount. |
| `checkout_provider_error` (502) | Inspect provider diagnostics privately. A reservation may remain Created; retry with unchanged configuration. Permanent rejection needs reconciliation. |
| `checkout_timeout` (504) | The provider may have accepted creation. Retry the same endpoint; the persisted attempt key is reused. |
| `payment_conflict` (409) | Concurrent state changed. Read the current payment and retry only if its state allows checkout. |
| `checkout_recovery_required` (409) | Created reservation is too old or a legacy Pending record lacks identity. Reconcile with Stripe before any replacement; do not delete/reset it to bypass the guard. |
| `checkout_unavailable` (409) | The current Payment state does not allow checkout. |

The reservation and Pending save are separate atomic MongoDB/history transactions around the provider call. Read the current record and history to distinguish a Created reservation from a saved Pending session. Preserve attempt identity across restart. A completed or expired provider session has `checkout_url=null`; provider retrieval does not infer a domain terminal state or generate a new session. STRIPE/2 confirms terminal state through verified webhooks. Legacy request version 1 remains card-only during recovery; new version 2 reservations request card and BLIK.

Readiness remains a MongoDB check. Checkout availability and outbound Stripe access are tested by the feature and are not included in health probes. Existing authentication/ownership limitations of the demo remain; do not use real customer data.

## Automated verification

`bash scripts/ci.sh suite externalproviders` exercises SDK request encoding, idempotency headers, provider mapping and safe failures. Application/Infrastructure/Acceptance suites additionally require Docker and verify actual transaction/history behavior, restart recovery, concurrent calls and HTTP/OpenAPI responses. No Stripe account credentials are required by CI.
