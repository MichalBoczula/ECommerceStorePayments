# Real Stripe sandbox scenarios

The **Stripe sandbox scenarios** workflow extends the [Visa payment smoke](stripe-card-smoke.md) with four actual-account checks. Each job starts its own disposable MongoDB replica set, the digest-pinned Invoice service, production Payments API, and checksum-pinned Stripe CLI 1.53.0. The existing `STRIPE_SECRET` repository secret is used only in the smoke step. Owner-authored same-repository PRs touching the harness run the checks; forks and other authors do not receive it. After merge, use Actions → Stripe sandbox scenarios → Run workflow.

| Scenario | Actual provider action | Assertions |
| --- | --- | --- |
| `blik` | Create a BLIK PaymentMethod and confirm Payments' own Checkout with sandbox code `000000`. | Exact PLN 12.99 succeeded test BLIK charge, real signed event, Succeeded Payment, Paid order, one completed PDF invoice; duplicate delivery changes neither history nor invoice count. |
| `decline-retry` | Use `tok_visa_chargeDeclined`, then retry the same session with `tok_visa`. | Stripe reports `card_declined/generic_decline` with zero received. Payment stays Pending, order Created, no invoice or fulfillment work. Repeated checkout retains Payment/session/attempt; Visa retry succeeds on the same PaymentIntent and creates one invoice. |
| `expiry` | Expire Payments' real open test Checkout through the Stripe SDK. | Stripe session expired/unpaid; actual `checkout.session.expired` delivery establishes Failed/`checkout_expired`; order stays Created, no invoice/work. Replaying the same signed event changes no history. |
| `webhook-retry` | Pay Visa while a test-only ASGI wrapper rejects the first matching account event with HTTP 503; resend its original body/signature locally. | Before resend, Payment Pending/order Created/no invoice. Resend acknowledged with 200 establishes success and one invoice; another resend is idempotent. |

These are infrequent sandbox probes, not load tests. CLI payment-page endpoints are a test seam based on Stripe's official Checkout fixture; production continues to redirect to hosted Checkout. The decline fixture permits only `card_error`, then independently checks the exact Stripe PaymentIntent error: an unrelated CLI/network failure never counts as a passed decline. BLIK uses Stripe's documented six-digit sandbox code; the code is never added to the production API or stored in MongoDB.

The retry scenario proves local recovery using a genuine account event and the listener's original signature. It explicitly resends the failed delivery; it does **not** prove Stripe's automatic retry scheduler or delivery to Azure. The CLI and a Dashboard endpoint have different signing secrets.

## Run locally

Install Docker, Stripe CLI 1.53.0 and the locked Python environment; privately configure `PAYMENTS_STRIPE_SECRET_KEY` with a sandbox `sk_test_` key. The shared guard rejects live, publishable and missing keys before containers or requests. Run one independent scenario:

```bash
bash scripts/ci.sh sync
uv run --no-sync python -m scripts.stripe_scenario_smoke blik
uv run --no-sync python -m scripts.stripe_scenario_smoke decline-retry
uv run --no-sync python -m scripts.stripe_scenario_smoke expiry
uv run --no-sync python -m scripts.stripe_scenario_smoke webhook-retry
```

Logs/summaries contain synthetic IDs, safe status/count evidence and request IDs. They never contain keys, CLI output, raw event/signature, customer data or a usable Checkout URL. Matching deliveries are held only in bounded memory. Open sessions are expired on normal exit; completed sandbox charges remain visible in Workbench. Containers, listener and server stop on exit. A failed assertion fails the job and retains safe diagnostics; it is not silently replaced with a fixture or skipped.

## Guided hosted 3DS tests

Stripe [documents that frontend security measures prevent automated testing](https://docs.stripe.com/automated-testing). The following executable tests therefore ask you to complete the actual hosted challenge in a browser, then verify account state and downstream behavior. They require a private interactive terminal and fail before account requests in CI/noninteractive use. The Checkout URL appears only in that terminal; do not record/share its output.

```bash
uv run --no-sync python -m scripts.stripe_scenario_smoke 3ds-success
uv run --no-sync python -m scripts.stripe_scenario_smoke 3ds-failure
uv run --no-sync python -m scripts.stripe_scenario_smoke 3ds-cancel
```

Use Stripe's test card **4000 0000 0000 3220**, any future expiry, any three-digit CVC and synthetic billing details. In the hosted test challenge choose the requested outcome, then return to the terminal and press Enter:

- Success must have a succeeded test Visa charge with `three_d_secure.result=authenticated` and `authentication_flow=challenge`, real signed success, Paid order and one PDF invoice. A plain Visa payment or frictionless bypass cannot pass this test.
- Failure must have zero received and Stripe's `payment_intent_authentication_failure`; Payment stays Pending, order Created, no invoice. The harness then retries the same session with Visa and verifies one successful invoice.
- Cancel/close must remain unpaid with an outstanding `use_stripe_sdk` authentication action, or the same explicit authentication-failure result. Browser cancellation itself is the operator's observation: Stripe need not expose a separate cancellation flag. The harness checks that no success or fulfillment occurred, then verifies Visa recovery.

These guided tests are implemented but require actual browser execution; unit tests of their safeguards do not establish real 3DS evidence.

## Deployed endpoint checks after Azure deployment

Keep this item open until a reachable sandbox deployment and its registered test webhook endpoint exist. Use the [webhook runbook](stripe-webhooks.md) to configure the endpoint's own secret and pinned API version with all four Checkout event types. The fulfillment worker must use the same Payments database and Invoice boundary as that deployment.

1. Create a synthetic Created order in the deployed test Orders service, initiate its checkout through Payments, and pay with a documented test card or BLIK. Record only order/payment/session/intent/event IDs. Check Workbench's delivery attempt for **this endpoint**, HTTP 200, the applied receipt, Succeeded Payment, Paid order and exactly one completed invoice.
2. Resend the actual event to that endpoint with `stripe events resend evt_YOUR_EVENT --webhook-endpoint we_YOUR_TEST_ENDPOINT` using a privately configured sandbox CLI key. This creates a new endpoint signature; do not reuse the local listener signature. Check HTTP 200, unchanged Payment version/history and one invoice.
3. In a disposable Azure test environment, make the endpoint temporarily return 503 for the matching delivery, restore availability, and observe Stripe's automatic retry in Workbench. Verify recovery and exactly one invoice. Manual resend proves redelivery/idempotence; only the observed scheduled retry proves automatic retry. Do not count a locally forwarded event as a deployed delivery.

No Azure resource changes or Dashboard endpoint registration are made by the sandbox workflow. References: [Stripe test values](https://docs.stripe.com/testing), [BLIK direct API sandbox behavior](https://docs.stripe.com/payments/blik/accept-a-payment?payment-ui=direct-api), [Stripe CLI fixtures](https://docs.stripe.com/cli/fixtures), [Stripe webhook retry and resend behavior](https://docs.stripe.com/webhooks).
