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
architecture checks pass. Docker is unavailable locally and CI supplies real
database/Invoice/container evidence.

[Implementation CI 40937816237](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/40937816237)
passes all source/contract/wheel/security checks, all five suites, documentation
packaging, real Mongo-backed container smoke, Trivy scanning and the final gate.
Frozen implementation head: `8f5dc7c24703b3c6aec6f1bbe9e4907d78b1c362`;
tested merge: `063380df35c3e2090235a6919eaa41e173fbe81e`;
exact tree: `49b2694c485b5dab838eb04848198c82394af1a1`.
Parents/tree were checked against Task 3's merged base and this head.

- **901 passing suite executions, zero failures/skips:** Domain 97, Application 82,
  Infrastructure 250, ExternalProviders 175, Acceptance 297. There are 726 distinct
  members, retaining the intentional 175-member external-provider overlap.
  Acceptance is **74 BDD + 223 ordinary**. Every Task 3 member survives, with
  fourteen BDD and 37 ordinary regressions added.
- Line coverage remains 96.88% / 96.16% / 90.90% for Domain/Application/
  Infrastructure and 96.35% / 98.06% for ExternalProviders/Acceptance. The three
  separate 70% floors remain unchanged.
- All seven official outer artifact digests match. The frozen inner archive is
  **1,796,223 bytes**, SHA-256
  `066b819861b19ec4ca7df9a06c11f6901e942f1f086435f069132cb3100cf03d`, with
  **1,666 verified manifest entries**: 74 results, 7 feature sources, 4 exports and
  **1,581 attachments** (1,362 JSON and 219 native Gherkin CSV tables).
- Independent closed-inventory/path/size/hash, source/export, JUnit and raw-result
  audits pass. Pinned Allure 2.46.1 renders every case, description, ordered/nested
  step and attachment matching raw results; all case/attachment/entry assets pass
  local HTTP reads. Prior names/full names/history/test identities/title paths
  survive. OpenAPI/flows/validation-policy bytes match Task 3; operation-links adds
  only fourteen scenarios and current case counts.
- Independent Task 4 checks verify seven primary complete retry/archive deltas,
  six no-op repeats, nine unchanged rejections, three physical legacy fixtures and
  the later version-4–8 cycle. Every previous archive field, recorded timestamp,
  protected identity/money/time and unrelated document is checked. Current evidence
  contains 445 HTTP request/outcome pairs (437 responses, 8 transport failures) and
  33 explicit action start/result pairs. Earlier Task 3 money/full-read checks also
  pass on the same archive.
- Local pinned lock/sync, 617 unit tests, format/Ruff/strict Pyright, architecture,
  exact links/OpenAPI commands, wheel build/install, Markdown links and git checks
  pass. Full real MongoDB/Invoice/container/image verification comes from CI.

Task 4 is complete. A final documentation-only completion head is checked again
in full CI and with fresh artifacts before PR handoff.

Application/API/persistence code, dependencies, workflow/image pins, security and
coverage gates, original baseline/matrix rows and Blob/LiveDocs publication paths
are unchanged. Tasks 5–16 and overall PAY/22 remain open. Task 12 retains dedicated
competing-write/rollback fault injection; observing successful transactions here
does not claim that coverage. Selected LiveDocs refresh remains manual.
