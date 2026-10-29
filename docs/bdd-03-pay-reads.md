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

[Implementation CI 40933885048](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/40933885048)
passes all source/contract/wheel/security checks, all five suites, documentation
packaging, real Mongo-backed container smoke, Trivy scanning and the final gate.
Frozen implementation head: `50a111ed0ee51b5abb7c2d20f7f670e8bcf46ce4`;
tested merge: `f6b3aede6516041209b63aed7b7ed96b9ecb7e3a`;
exact tree: `03d8cb59dc68452d016e198186c2e88910e82525`.
The merge parents and tested tree match Task 2's merged base and this head.

- **850 passing suite executions, zero failures/skips:** Domain 97, Application 82,
  Infrastructure 250, ExternalProviders 175, Acceptance 246. There are 675 distinct
  members, with the intentional 175-member external-provider overlap retained.
  Acceptance is **60 BDD + 186 ordinary**: every Task 2 member is retained, with
  nine new BDD and 27 regression cases. All 580 local unit tests pass.
- Line coverage remains 96.88% / 96.16% / 90.90% for the separately gated
  Domain/Application/Infrastructure layers, and 96.35% / 98.06% for
  ExternalProviders/Acceptance. The three separate 70% floors stay unchanged.
- All seven official outer artifact digests match. The frozen inner archive is
  **1,197,990 bytes**, SHA-256
  `f45d2fd76e68c5e66160d04f27208666ba27ea10e5aea00d92a1de57be4087ea`, with
  **1,130 verified manifest entries**: 60 results, 6 feature sources, 4 exports
  and **1,060 attachments** (913 JSON, 147 native Gherkin CSV tables).
- Independent closed-inventory/path/size/hash, source/export, JUnit and raw-result
  checks pass. Pinned Allure 2.46.1 renders all cases and attachments; original
  names/full names/history/test identities/title paths survive. Every rendered
  description, ordered/nested step and attachment matches its raw result. Every
  case/attachment/entry asset passes local HTTP reads.
- Independent Task 3 checks verify eleven complete success payloads, five read
  states, all three Pay repeat states, complete empty/populated missing problems,
  exact large decimal money, explicit timestamp precision/bounds and exact
  collection effects. The archive contains 295 actual request/outcome pairs
  (289 responses, 6 transport failures) and 18 explicit action start/result pairs.
- OpenAPI, flows and validation-policy exports are byte-identical to Task 2;
  operation-links adds only the nine scenario rows and current case counts. Original
  baseline/matrix rows and the sixteen reviewed gaps remain unchanged. Pinned
  lock/sync, format/Ruff/strict Pyright, architecture, exact links/OpenAPI commands,
  wheel build/install, local Markdown links and git checks pass. Docker is
  unavailable locally; CI supplies real MongoDB/Invoice/container/image evidence.

Task 3 is complete. The final documentation-only completion head is checked again
in full CI and with fresh artifacts before PR handoff. Tasks 4–16, the sixteen
Task 11 status gaps and overall PAY/22 remain open. Public contracts, application
and persistence code, dependencies, coverage/security gates and LiveDocs/Blob
publication paths are unchanged. Selected LiveDocs refresh remains manual.
