# Complete Pay and payment reads — PAY-BDD-03

Task 3 strengthens the four original creation/read/repeat/missing cases and adds
nine scenarios (`PAY03-01`–`PAY03-09`). All 51 original identities and matrix rows
are preserved. There are now 60 BDD cases across six features, with the same
seven operations, 26/42 declared status pairs and sixteen reviewed gaps.

| Behavior | Evidence |
| --- | --- |
| Create | Original PLN creation plus exact `90071992547409.91 USD` → `9007199254740991` minor units; complete new document and preservation of unrelated data. |
| Read | Complete Created, Pending, Succeeded, Failed and Canceled snapshots; exact provider/null fields; no dependency calls, writes or retries. |
| Repeat Pay | Created, Pending and Succeeded return the remembered complete response, with unavailable Orders and all three collections populated by an unrelated order. |
| Missing read | Empty and populated storage return the complete safe not-found problem for the requested order; unrelated data remains private and unchanged. |

## Complete payload and stored state

The executable **complete payment response** tables explicitly list all ten public
fields: ID, order ID, minor-unit amount, currency, status, both provider IDs,
failure code, creation time and nullable update time. Exact key sets reject
missing nullable fields and leaked internal version/checkout members. Literal
Gherkin money, status, currency, provider and failure values are checked against
both HTTP JSON and the real stored document. UUIDs must be canonical and nonzero.
The helper builds its assertions independently of the production response mapper.

Dynamic `{stored.id}` and timestamp references use the remembered pre-request
document for reads/repeats, and the newly stored document for creation. Timestamps
must be RFC 3339 UTC. A new creation time must fall within the actual request
window. MongoDB stores milliseconds while Python's create response can retain
microseconds: only that creation response uses an explicit floor to the exact
stored millisecond. Read timestamps must match stored timestamps exactly. Update
time is explicitly null for new Created state and is checked against stored UTC
for prepared states. No broad timing tolerance or frozen application clock is used.

Order fixture amounts stay `Decimal` and are emitted as unquoted JSON number
tokens. The large USD case distinguishes the previous lossy float conversion.
It exercises the real precise Kiota parser, service, repository, MongoDB and HTTP
response in acceptance. Original amounts and all application behavior remain
unchanged. Raw HTTP bytes/text remain authoritative for decimal tokens; JSON
viewer number rendering may round fractional values. Canonical BSON evidence
retains exact int64, UUID and millisecond values.

## Isolation and effects

An unrelated order, client and amount go through actual checkout and a signed
successful webhook. This populates current payments, history and receipts before
the target operation. The target's Pending/Succeeded/Failed/Canceled setup uses
legal domain transitions and the real transactional repository after API creation;
its explicit setup action does not claim a live provider confirmation.

Before a target operation, capture every field of every document in all three
collections and, for an existing target, its full GET response. Reads/repeats must
preserve those full snapshots and the exact response body. Dependency call counts
include all controlled Orders/Invoice requests, failed transports and Stripe SDK
calls. Creation must add exactly its complete version-0 payment, issue one Orders
read and make no Stripe call; all unrelated documents, history and receipts remain
unchanged. Different order/client IDs and provider/money values expose accidental
cross-order selection. This verifies order-key isolation, not an authentication or
client authorization policy.

Task 2's immutable HTTP/JSON/action capture and native Gherkin tables remain in
use. Additional JSON observations include complete response comparisons, request
windows, canonical collection snapshots and the verified write/no-write effect.
The frozen baseline file is unchanged; only current-inventory expectations grow.

## Verification and remaining work

Regression checks reject partial payloads, wrong money/types/provider values,
internal fields, invalid UTC/date precision and out-of-window creation times.
They verify exact fixture numbers through the real Kiota parser, lossless BSON
capture and changed unrelated fields at unchanged collection counts. Source checks
keep complete response and effect assertions on all eleven success cases in scope.

Local verification and full CI/archive/render inspection are in progress. Docker
is unavailable locally, so CI supplies real MongoDB/Invoice/container evidence.
The Task 3 checkbox remains open until those checks pass. Tasks 4–16, the sixteen
Task 11 status gaps and overall PAY/22 remain open. Public contracts, application
and persistence code, dependencies, coverage/security gates and LiveDocs/Blob
publication paths are unchanged. Selected LiveDocs refresh remains manual.
