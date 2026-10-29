# Checkout success — PAY-BDD-05

Task 5 strengthens the original new/repeated/card-and-BLIK checkout cases and adds
seven `PAY05-01`–`PAY05-07` scenarios. All 74 earlier cases and their original
matrix rows remain. The current source has 81 BDD cases across eight features,
seven operations and the same 26/42 declared status pairs; sixteen reviewed gaps
remain assigned to Task 11.

| Behavior | Evidence |
| --- | --- |
| New checkout | All four outer response fields and all ten nested payment fields match exact stored/provider values. Creation/update times use only the explicit BSON millisecond projection within the actual request window. |
| Provider parameters | The real Stripe SDK's complete encoded form, pinned API version, media type and payment/attempt idempotency key match executable Gherkin tables. Extra or duplicate form values fail. |
| Card and BLIK | New request-version-2 reservations enable exactly `card` and `blik`; one quantity-one line uses server-owned minor units/currency and the order name. |
| Existing Created payment | Its identity, money and creation time survive reservation and Pending state; both complete previous Created snapshots are archived. |
| Failed/Canceled payment | The same payment is retried, reset and reserved under a different attempt; each of the three version increments archives the complete actual previous state. |
| Open/complete/expired session reads | Exact provider expiry/status, provider URL for open and explicit null URL otherwise. Payment remains Pending and every stored field remains unchanged. |
| Repeated reads | Three further requests per provider status return the same complete body and only retrieve the same session. No new session, version, timestamp, history or receipt. |
| Return URLs and isolation | Configured success/cancel URLs, including their query parameters, survive SDK encoding. An equal-money unrelated order retains its distinct key/session and all populated state. |

## Executable expectations and durable state

`checkout_checks.py` requires exact outer/nested field sets, types, UUIDs, nulls,
minor units and UTC timestamps. The expected response table lists all thirteen
leaf fields. Dynamic stored IDs/session IDs and provider URL/Unix expiry use
explicit tokens; expected status and all fixed business values are authored
literals. Provider observations identify the actual captured Stripe exchanges.

The complete form table includes both session and payment-intent payment/order/
attempt metadata, client reference, mode, card/BLIK, line quantity/unit amount/
currency/name and return URLs. The expected idempotency key is derived from the
persisted payment and reserved attempt, independently of the production builder.
Only one new POST/session is allowed and all earlier provider sessions remain
identical. The controlled transport now returns a URL belonging to its generated
session rather than sharing a constant demo URL between orders.

Every successful write compares complete before/after payments, history and
receipts, checks every new archive independently of the production mapper, and
retains all older snapshots and unrelated documents. Reservation time equals the
archived reserved state's update time; all mutation/recorded times are bounded
by the real request window. Failed/Canceled checkout preserves the original
payment/order/money/creation time and uses a new attempt and request version 2.
The terminal snapshot, reset Created snapshot and reserved Created snapshot must
all be present at the exact next versions.

Reads allow exactly one Orders GET and one Stripe session GET, with no create or
idempotency key. A provider `complete` or `expired` status does not confirm or
cancel payment; webhook lifecycle remains separate. All supporting repeats use
the shared capture and retain their actual Then phase. Session state changes in
Given are explicit controlled-boundary inputs, not fabricated HTTP exchanges.

## Verification and remaining work

Implementation verification and the complete CI/archive/render audit are recorded
below after they pass. Thirty-seven new regressions exercise complete nested
responses, precise expiry/nullability, encoded form corruption, missing BLIK,
wrong metadata/keys, duplicate values, altered archives and unrelated state.

This package changes tests and documentation only. Application/API/persistence
code, dependencies, workflows, image pins, original frozen baseline/matrix rows,
coverage/security gates and Blob/LiveDocs publication paths are unchanged.
The captured card/BLIK configuration is controlled SDK-boundary evidence;
real hosted payment execution remains in the existing STRIPE rollout tasks.
Checkout failures/ambiguous recovery/legacy request versions remain Task 6;
dedicated races and rollback remain Task 12. Tasks 6–16 and overall PAY/22 stay
open. Selected LiveDocs refresh and Terraform deployment remain manual.
