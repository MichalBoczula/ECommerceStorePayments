# PAY-BDD-08 — Complete webhook lifecycle and replay

Task 8 strengthens nine original webhook cases and adds 35 scenarios, preserving
all 144 prior BDD identities and the original frozen baseline. There are **179
current BDD cases**. Native Gherkin tables describe event inputs, complete HTTP
responses, all sixteen receipt fields, full stored-state deltas and all ten fields
of a supporting payment read. Every new case populates unrelated payment,
history and receipt collections before the primary delivery.

## Receipt decisions and immutable state

Real signed HTTP delivery runs the Stripe SDK verifier, application service and
MongoDB repositories. Cases cover completed and asynchronous success, asynchronous
failure, expiry and unpaid completion. Expected receipts name their exact outcome,
state, reason, provider references, original-byte digest, UTC millisecond dates
and fulfillment marker. Receipt documents contain no raw event, signature or
customer/card/BLIK data; their exact sixteen-field shape is asserted.

A successful or failed transition compares every current-payment field, adds one
version and checks every field in its one previous-state archive. A notification
can finish a Created reservation before its session save; Pending/Failed domain
changes still commit as one stored version. Late success for the same Failed or
Canceled attempt follows existing policy, clears any failure and schedules one
durable fulfillment marker. Already successful payments cannot be downgraded or
assigned another provider payment.

Explicit completed receipts cover `payment_not_found`, `payment_mismatch`,
`session_mismatch`, `provider_payment_mismatch`, `stale_attempt`,
`awaiting_payment`, `already_succeeded`, `already_terminal` and
`unsupported_event`, alongside `payment_succeeded` and `payment_failed`.
Old success/expiry/failure after a real API retry preserve the new attempt.
A historical Pending document physically missing attempt fields remains unchanged.
Every older archive, unrelated payment and unrelated receipt is retained.

## Duplicates, collisions and recovery

Identical applied, ignored and rejected deliveries preserve their complete stored
receipt, including both dates. Distinct success event IDs for the same provider
payment do not create another transition or work marker. Reusing an applied,
pending or ignored event ID with different correctly signed bytes returns a full
safe `webhook_collision` problem. Signed trailing whitespace demonstrates that
semantic JSON equality does not imply digest equality. Original pending work is
never replaced by the conflicting delivery.

Controlled completion-boundary faults leave durable Pending work or simulate a
lost acknowledgement after the real transaction committed. One and four injected
optimistic conflicts check bounded reload/retry behavior with explicit action
observations and interruption counts. These are controlled application-boundary
faults; deterministic competing transactions and in-transaction rollback remain
Task 12. The original concurrent duplicate case is preserved.

A fresh FastAPI application instance redelivers identical bytes, then another
fresh instance repeats the acknowledgement while all three collections remain
unchanged. The real operator `replay` entry point opens a fresh MongoDB client and
event loop without Stripe API or signing credentials. It resumes success,
unsupported, mismatched and stale normalized Pending receipts. A second invocation
processes zero and preserves every field. These are fresh in-process application/
operator invocations, not claims of a separate OS process or unsigned HTTP replay.
No Stripe, Orders or Invoice request occurs during receipt processing or replay.

## Verification and scope

The implementation adds 51 evidence/source regressions. Local verification and
full CI/archive/render audit results are recorded after execution below.

No application/API/persistence/dependency/workflow/image policy changes are made.
Operation/status coverage remains 27/42 with fifteen reviewed gaps. Existing
future-timestamp verification behavior, coverage/security gates, automatic main
Blob publication and selected manual LiveDocs/Terraform refresh remain unchanged.
Fulfillment processing is Task 9; framework/atomicity/technical/contracts/RAG/final
packages and overall PAY/22 stay open.
