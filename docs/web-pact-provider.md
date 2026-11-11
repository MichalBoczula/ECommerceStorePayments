# PACT/10 Web → Payments provider verification

The required `pact-provider` job checks the
[pinned Web Pact](../contracts/pact/web-payments.json) against the Payments
candidate over TCP. The [source record](../contracts/pact/web-source.json)
identifies the Web commit, workflow artifact, registry publication and SHA-256.
The verifier checks the bytes before replay. [Web consumer artifact](https://github.com/MichalBoczula/ecommerce-store-web/actions/runs/43080998727/artifacts/13884172245) · [Web publication receipt](https://github.com/MichalBoczula/ecommerce-store-web/actions/runs/43080998727/artifacts/13883683603)

| Provider scenario | Expected result |
| --- | --- |
| An order with a succeeded payment | `GET /payments/order/{order_id}` returns HTTP 200 with the payment and order IDs, succeeded status, integer amount and currency. |
| An order without a payment | The same route returns HTTP 404 with `application/problem+json`. |

The test uses the existing disposable MongoDB replica-set fixture. Provider
setup rehydrates a succeeded Payment and stores it through the production
document mapper. It leaves the second order without a payment. Teardown clears
both IDs, and the test drops its database. Stripe is disabled during replay.

With Docker available, run from the repository root.

```bash
bash scripts/ci.sh sync
bash scripts/ci.sh suite pact-provider
```

CI uploads the raw Pact report, JUnit and the normalized result as
`web-payments-verification`. On a Payments `main` push, the existing
Payments publisher checks the exact Web publication and its stored bytes
before posting the provider result. The
`web-payments-verification-receipt` artifact identifies the registry record.
