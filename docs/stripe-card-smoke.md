# Real sandbox card payment smoke

The separate **Stripe sandbox card smoke** workflow completes a real sandbox Visa payment on the Checkout Session created by Payments, receives the real account event through Stripe CLI, and runs the production fulfillment worker against the published Invoice image. It requires the existing `STRIPE_SECRET` sandbox secret; no Dashboard webhook registration or extra signing-secret repository secret is needed.

## Run and evidence

After merge, use **Actions → Stripe sandbox card smoke → Run workflow**. Owner-authored same-repository PRs touching the smoke files also run it; forks and other authors do not use the account secret. Ordinary CI stays deterministic. For local use, install Docker and Stripe CLI **1.53.0**, privately set `PAYMENTS_STRIPE_SECRET_KEY`, then run:

```bash
bash scripts/ci.sh sync
uv run --no-sync python -m scripts.stripe_card_smoke
```

The shared sandbox setup rejects live/missing/publishable keys before starting containers or making requests. It seeds a synthetic PLN 12.99 Created order and client data version in disposable MongoDB, then starts the immutable Invoice image from `contracts/invoice/source.json`.

1. Start a loopback Payments server and a test-mode `stripe listen` subscription for this account's `checkout.session.completed` events. Capture its ephemeral `whsec_...` privately and configure the actual Payments signature verifier.
2. Create the session through bodyless `POST /payments/<order ID>/checkout`; verify the exact amount, card/BLIK methods and durable payment/order/attempt metadata.
3. Adapt Stripe CLI 1.53.0's own [Checkout completion fixture](https://github.com/stripe/stripe-cli/blob/v1.53.0/pkg/fixtures/triggers/checkout.session.completed.json) to this existing session. The CLI creates a Visa payment method from `tok_visa` and confirms the payment page with expected amount 1299. It does not create an unrelated Checkout fixture. Payment-page fixture endpoints belong only to this CLI-based sandbox test; production still redirects to hosted Checkout.
4. Receive the real CLI-forwarded original body/signature through `/payments/webhooks/stripe`. Check HTTP 200, Succeeded Payment, the matching complete/paid test session, and a succeeded PLN 12.99 Visa charge/PaymentIntent in Stripe.
5. Check the Applied receipt/Pending fulfillment intent, run the production one-shot worker, and assert the order is Paid with exactly one completed PDF invoice and matching recorded invoice ID.
6. Replay the acknowledged delivery's unchanged bytes/signature while within the normal timestamp tolerance. Run the worker again; verify no extra work, Payment version/history change or second invoice.

The job summary exposes only synthetic IDs, amount/currency, test-mode status, method, receipt HTTP status, invoice/count evidence and Stripe request IDs. CLI output, keys, signing secret, original body/signature, customer data and the usable checkout URL are never printed or uploaded. The delivery recorder passes ASGI messages unchanged, bounds its buffer, and keeps only the matching acknowledged event in memory for the duplicate check.

Known open sessions are expired in cleanup. Completed sandbox charges remain visible in Stripe as evidence; these test payments move no real funds. The listener/server stop and containers/databases are removed on exit. A killed runner or lost creation response can leave unpaid sessions to expire naturally. A completed card payment followed by a failed webhook/fulfillment assertion is reported as a failed smoke, not silently retried as a new purchase.

This proves account card payment, CLI-signed webhook receipt and real Orders/PDF fulfillment. The [scenario harness](stripe-scenario-smoke.md) adds real BLIK, declined-card recovery, expiry and local webhook outage/replay checks, plus executable guided hosted 3DS tests. Delivery through a deployed Dashboard webhook endpoint remains an Azure deployment check. Stripe [documents security measures that prevent automated frontend testing](https://docs.stripe.com/automated-testing); this probe uses its official CLI fixture rather than automating hosted Checkout.

Related: [session-only smoke](stripe-sandbox-smoke.md), [webhook runbook](stripe-webhooks.md), [fulfillment runbook](payment-fulfillment.md), [Stripe test values](https://docs.stripe.com/testing).
