# Real Stripe sandbox request smoke

This probe calls the real Stripe API with the account's sandbox/test secret key. It exercises Payments through its FastAPI HTTP routes, a real isolated MongoDB replica set, the published Invoice/Orders image and the production Stripe adapter. The Orders and Stripe boundaries are not mocked.

## GitHub Actions

Use repository secret `STRIPE_SECRET` containing the sandbox's `sk_test_...` key. The separate **Stripe sandbox smoke** workflow explicitly maps it to `PAYMENTS_STRIPE_SECRET_KEY` for its smoke step. It rejects missing, live and publishable keys before starting containers or making requests. Ordinary CI remains deterministic and does not use account credentials.

After merge, select **Actions → Stripe sandbox smoke → Run workflow**. While developing this probe, the workflow also runs on the repository owner's same-repository PRs changing its script, workflow or safeguard tests. Fork PRs and other authors do not receive this job's secret. It does not run for unrelated application changes or on a schedule.

For local use, configure `PAYMENTS_STRIPE_SECRET_KEY` privately in your process environment, install Docker, and run:

```bash
bash scripts/ci.sh sync
uv run --no-sync python -m scripts.stripe_sandbox_smoke
```

## What it proves

1. Start an ephemeral MongoDB replica set and the immutable Invoice image recorded in `contracts/invoice/source.json`; seed one synthetic Created order for PLN 12.99.
2. Call the actual Payments `/payments/{order_id}/pay` and `/payments/{order_id}/checkout` routes. The real adapter creates a hosted sandbox session requesting card and BLIK.
3. Repeat checkout and read Payment; verify the same persisted Pending payment/session and checkout URL are returned.
4. Retrieve the session through Stripe's SDK and verify `livemode=false`, unpaid/open state, PLN 12.99, both methods and the payment/order/attempt association.
5. Expire the known unpaid session in `finally`, including when verification fails. Remove ephemeral containers/databases on exit. A lost creation response or killed runner may leave an unidentified unpaid session to expire automatically; no charge is attempted.

The job summary reports only synthetic order/payment/attempt IDs, the `cs_test_...` session ID, Stripe retrieval/expiration request IDs, amount, methods and cleanup result. It does not publish keys, full provider responses, customer data or a usable checkout URL. Errors fail the job; no fallback fixtures turn a provider failure into a pass.

In the matching Stripe sandbox/test environment, search API logs for the session ID or the reported `req_...` identifiers. Expect Checkout Session creation, retrieval and expiration requests. The session ends Expired, not Paid; the Payments database is disposable, so the probe does not need a registered webhook endpoint.

This closes the real-account **session creation/request** check in STRIPE/1. It does not establish card/BLIK payment completion, signed webhook delivery, Paid order or invoice fulfillment. Those remain the separate [account payment/webhook smoke](stripe-webhooks.md) and [fulfillment runbook](payment-fulfillment.md), plus the STRIPE/4 UI integration.

References: [create Checkout Session](https://docs.stripe.com/api/checkout/sessions/create), [expire Checkout Session](https://docs.stripe.com/api/checkout/sessions/expire), [request IDs](https://docs.stripe.com/api/request_ids).
