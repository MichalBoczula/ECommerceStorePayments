# Retries and immutable history — PAY-BDD-04

Task 4 strengthens the three original Failed/Canceled retry and changed-total
rejection cases, and adds fourteen `PAY04-01`–`PAY04-14` scenarios. All 60 earlier
cases and every original matrix row remain. There are 74 BDD cases across seven
features, seven operations, the same 26/42 declared status pairs and sixteen
reviewed gaps.

| Behavior | Evidence |
| --- | --- |
| Failed/Canceled retry | Complete ten-field HTTP response, one version increment, exact archived previous state, reset provider/checkout data and preserved identity/money/creation time. |
| Repeated retry | The resulting Created payment is returned unchanged; no new Orders/Stripe call, history row, version or timestamp. |
| Later failed attempt | The same payment reaches version 8 through another reservation, Pending, Failed and retry cycle; each transition appends its actual previous snapshot and preserves all older history fields, including recorded times. |
| Historical records | Physically absent version/checkout fields remain absent on a Created read; terminal retries normalize their prior snapshot to version 0 and advance the current payment to version 1. |
| Rejected retries | Changed amount/currency, Paid/Canceled orders, missing/invalid Orders responses, timeouts and outages preserve every document in populated collections and return complete safe problems. |

## State and archive checks

`retry_checks.py` compares complete actual before/after collections independently
of the production history mapper. A transition must preserve payment/order IDs,
exact minor units/currency and creation time, increment the version once and add
one archive with deterministic payment/version identity. Every previous business,
provider and checkout field is compared. The archive's only new observation is its
UTC `recorded_at`, bounded by the actual operation window at BSON millisecond
precision. All existing history entries and unrelated current/receipt documents
must remain identical; count-only checks cannot satisfy these assertions.

After retry, provider session/payment IDs, failure code, checkout attempt/start
are null and checkout request version is 1. The rich fixtures have non-null
session/attempt metadata and Failed failure codes before retry. Provider payment
ID is already null in Failed/Canceled under existing domain policy; it stays null.
A later reservation must use a different attempt ID. Its session/failure values
are distinct, and the version-0–7 timeline retains the correct complete snapshots.

The full-response checker has an explicit update-window option for mutating retry
responses. Like creation responses, a retry can retain Python microseconds while
MongoDB stores milliseconds. Only the updated timestamp uses that exact BSON
projection; creation time remains the original stored value. Read/repeat responses
still match stored UTC exactly. No clock freeze or broad timing tolerance is used.

## Fixtures, isolation and failures

Normal target states use API creation and legal domain transitions through the
real transactional repository. An unrelated order/client/amount goes through
checkout and a signed successful webhook, populating payments, history and receipts
before the new scenarios. Every accepted/rejected target request preserves that
unrelated state. Rejections allow exactly the attempted Orders read and no Stripe
call, including when the controlled Orders transport throws.

Historical fixtures are the deliberate exception to ordinary repository setup:
they use legal domain creation/transitions, then raw insertion of a historical
schema with four fields physically removed. A repository insertion would add the
fields and fail to test compatibility. The fixture records its omitted fields and
stored BSON, and verifies the production rehydration defaults. There is no existing
target history to collide with its normalized version-zero identity. This does
not relax application validation or change a persistence schema.

Task 2's stable identities, native Gherkin tables and immutable HTTP/JSON/action
capture remain. Additional observations include full retry responses, every
collection before/after, the complete new archive, repeated-body evidence and
later-transition windows. Supporting reads/repeats are labeled by their actual
Then phase; the original primary response witness is retained.

## Verification and remaining work

All 617 local unit tests pass, including 37 new assertion regressions for altered
archive fields, identities, versions, old recorded times, unrelated state,
provider/checkout resets, legacy normalization and update timestamp precision.
Formatting/Ruff/strict Pyright, source projection, generated contracts and
architecture checks pass. Full CI and independent archive/render verification are
pending; Docker is unavailable locally and CI supplies real database/Invoice/
container evidence. Task 4 remains open until those checks pass.

Application/API/persistence code, dependencies, workflow/image pins, security and
coverage gates, original baseline/matrix rows and Blob/LiveDocs publication paths
are unchanged. Tasks 5–16 and overall PAY/22 remain open. Task 12 retains dedicated
competing-write/rollback fault injection; observing successful transactions here
does not claim that coverage. Selected LiveDocs refresh remains manual.
