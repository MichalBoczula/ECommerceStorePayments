# ADR-0009: Pay and Get semantics for one payment per order

Status: Accepted
Date: 2026-09-28

## Context

The unique order ID index permits one Payment per order, but Pay previously returned HTTP 201 even when it merely returned an existing record. Failed and canceled attempts could not be retried, despite retaining a stable payment ID and history. Concurrent requests must not create extra payments or reset a state written by another request.

## Decision

For an order without a payment, Pay requires the Orders status `Created`, stores a new Payment in `Created` and returns HTTP 201. A simultaneous create that loses the unique-index race reloads the winner and returns HTTP 200. A duplicate error with no payment for this order remains HTTP 409.

For an existing Payment in `Created`, `Pending`, or `Succeeded`, Pay returns its current snapshot with HTTP 200, without contacting Orders or writing again. Get by order ID returns the same current snapshot with HTTP 200, or HTTP 404 if absent. A provider operation that changes the payment later is outside this endpoint's current scope.

For `Failed` or `Canceled`, Pay fetches the order again. If Orders is no longer `Created`, or its money differs from the stored Payment, it returns HTTP 409 and leaves the payment untouched. Otherwise `Payment.retry()` resets the same aggregate to `Created`, clears previous provider IDs/failure code, preserves its ID, order, money and creation time, then updates it with optimistic concurrency. A retry returns HTTP 200 because no new Payment resource was created. The previous snapshot is archived in `payment_history` transactionally by PAY/7. A retried `Created` snapshot has a positive version and update time; a newly created version-0 snapshot has no update time. Repeating Pay on the retried `Created` state is a read with no additional version or history entry.

If two retries see the same terminal version, one update wins. The loser reloads the current state and returns HTTP 200 when a newer nonterminal or successful state exists; if it remains terminal or no progress is visible, the conflict stays HTTP 409. The repository's compare-and-replace and unique order index arbitrate these races. Orders timeouts and invalid responses keep PAY/8's 504/502 mapping. Full problem+json and stable public error codes belong to PAY/10.

## Consequences

Payment ID stays stable across attempts; provider metadata is specific to the attempt that created it, while archived snapshots retain prior values. Pay is idempotent for active/completed records, and a repeated retry does not archive duplicate versions. The endpoint currently prepares the new attempt only: session creation/charging, provider idempotency and webhook handling remain STRIPE/1–2.

## Alternatives considered

- Create a second Payment per retry: conflicts with the unique order ID constraint and splits history across payment IDs.
- Treat every Pay call as HTTP 201: falsely reports a new resource on reads and retries.
- Retry without rechecking Orders: could resume an amount that no longer matches the order or retry a paid order.
