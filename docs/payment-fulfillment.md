# Payment fulfillment runbook

A verified checkout success commits Succeeded Payment plus Pending fulfillment intent. The one-shot worker reads the ledger, marks the matching order Paid, then creates or retrieves its completed invoice. Browser returns do not drive this process; no retry charges Stripe again.

## Requirements and command

Use the same MongoDB replica-set database as the Payments API, and `PAYMENTS_ORDERS_API_BASE_URL` pointing to the Invoice service with [PR #217](https://github.com/MichalBoczula/ECommerceStoreInvoice/pull/217). Invoice must have the client's data version; it selects that version and owns PDF generation/lease recovery. Previously verified receipts need neither `sk_test_...` nor `whsec_...` to replay. New HTTP webhook delivery still needs the signing secret.

```bash
uv run --locked python -m ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments --limit 100
# From Compose, independently of a running API process:
docker compose run --rm --no-deps api python -m ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments --limit 100
```

The command replays at most `limit` Pending receipts, then claims at most `limit` due fulfillment items. Valid limits are 1–1000. It exits after the batch; no in-process recurring task runs. Downstream errors are saved for retry, so a successful process exit does not assert every order is fulfilled. Database/receipt batch errors exit nonzero. A killed worker leaves work recoverable after its five-minute lease expires.

## Inspect and resume

```bash
uv run --locked python -m ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments --inspect --limit 100
uv run --locked python -m ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments --resume evt_example
```

Inspection prints bounded unfinished records with event/payment/order IDs, status, attempt count, next retry, lease expiry, safe error code, Paid progress and invoice ID. It does not print raw Stripe payloads, signatures, keys or customer data. `--resume` accepts only Failed work: investigate/fix the cause first; it resets attempts and schedules work now, retaining already Paid progress. It cannot steal active leases or reopen Completed work. Run the batch after resuming.

| State | Behavior |
| --- | --- |
| pending | Ready for first claim; supports STRIPE/2 documents without new optional fields. |
| processing | Active fenced lease; after expiry a new worker can claim/reconcile. |
| retry | Eligible at `fulfillment_next_attempt`; exponential delay starts at 60 seconds, caps at one hour. |
| failed | Ten attempts exhausted, or association/configuration needs repair; explicit resume required. |
| completed | Invoice ID/data-version ID recorded; no further downstream writes. |

Safe reasons include `order_unavailable`, `order_update_unavailable`, `invoice_create_unavailable`, `invoice_lookup_unavailable`, `attempt_timeout`, `fulfillment_unavailable`, `payment_mismatch`, `order_mismatch`, `order_owner_changed`, `order_not_payable`, `order_state_regressed`, `invoice_mismatch`, `*_invalid_response`, `*_unauthorized` and `retry_exhausted`. Never infer Paid/completed from an error status alone. A missing client data version or a failed/active invoice reservation can be fixed upstream; retry is bounded and preserves the successful Payment. A Cancelled order after payment requires manual business repair; refunds remain outside scope.

## Azure deployment contract for DEP/2 and DEP/6

Deploy a **scheduled Container Apps Job**, using the same verified Payments image digest, private environment/network and Mongo/Orders configuration. Override the image command:

```text
python -m ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments --limit 100
```

Initial settings: UTC cron `*/5 * * * *`, parallelism 1, completion count 1, replica retry limit 1, replica timeout 1800 seconds. Workers also have a 120-second attempt deadline and a 300-second lease; overlapping executions remain fenced. Job timeout can interrupt a large batch safely; a later execution resumes it. DEP/6 must wire the job identity/network/secrets and monitoring for Failed work and job failures. No Stripe API key is needed by this job. Five-minute cadence gives eventual completion and incurs recurring execution/cold-start costs; DEP/2 must validate that cost, and the job schedule must be disabled when the portfolio demo is off. An HTTP in-process timer alone is insufficient.

## Verification and account smoke

Ordinary CI uses controlled Stripe boundary fixtures and real MongoDB. The Infrastructure suite builds the exact Invoice source revision, runs its real API/PDF container and checks signed webhook → Paid → one completed invoice across normal execution, lost Paid reply, lost invoice reply and a transient injected invoice error. Invoice's own acceptance tests cover its generation failures/leases. No real Stripe credentials enter CI.

For local focused container checks:

```bash
bash scripts/prepare_fulfillment_image.sh
uv run --locked pytest tests/integration/infrastructure/test_mongo_fulfillment.py tests/integration/infrastructure/test_real_invoice_fulfillment.py
```

For the real card/BLIK account smoke, follow [the webhook runbook](stripe-webhooks.md), then run the worker against the same database. Confirm Payment Succeeded, order Paid and the completed invoice lookup by order. Deliver the same signed notification again and rerun: one logical invoice must remain. Deliberately stop Invoice once, verify Retry plus Paid progress, restart it and let the due worker recover. Local PDFs still use `file://`; durable Azure downloads belong to DEP/7.
