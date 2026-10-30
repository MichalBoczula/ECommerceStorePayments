# PAY-BDD-12 — Concurrency and atomicity

Task 12 adds **28 BDD cases** and strengthens the two original Pay/duplicate-webhook
races while retaining all **342 previous scenario identities and matrix outcomes**.
There are **370 BDD cases**, sixteen features, and 381 exported HTTP outcomes.
All seven operations and **42/42 declared status pairs** retain scenario intent;
there are no reviewed gaps. Fifty-four negative evidence/source checks supplement
the ordinary suites. No application, API, persistence schema, dependency, image,
workflow or security/coverage gate changes are required.

## Deterministic real writes

Native Gherkin tables specify the operation, selected participant, complete
responses/receipts and exact stored effects. Test-only scoped decorators call
the real repositories and adapters. Both participants reach the declared boundary
before either proceeds; finite 15-second gates release the selected winner, then
the stale operation. Requests drain before the patches and database are cleaned
up. No sleep selects a winner and no fake persistence call returns success.

An actual `X-Bdd-Attempt` request header identifies each concurrent API request.
A scoped ContextVar carries that identity through the async request into actual
Orders/Stripe capture. Worker identities use the same scoped provenance on their
outbound exchanges, without inventing an API request. Canonical request/response
pairs and the evidence index remain centrally captured. Scope/header mismatch
fails before sending, and parent scope is restored even after exceptions.

| Cases | Real boundary and complete outcome |
| --- | --- |
| PAY12-01/02 | Both repository commands load version zero; Pending or Canceled commits, the actual stale update throws PaymentConflictError, and one exact archive survives |
| PAY12-03/04, strengthened PAY11-13 | Both first Pay requests reach insertion with distinct candidates; the selected insert wins and the actual unique-order rejection returns the complete existing payment |
| PAY12-05/06 | Competing Failed/Canceled retries reset one version and archive once; the stale actual update reloads the full winner |
| PAY12-07/08 | Distinct Checkout reservations compete; both SDK creates use the winning attempt's complete identical form/key, one session and two exact archives survive, and both stale writes are observed |
| PAY12-09–14, strengthened PAY22-09 | Same/distinct signed events and both success/expiry orders start from the same Pending version; exact receipts, immutable archives, final success and one fulfillment marker follow the real duplicate/conflict/retry policy |

Every new race starts with an unrelated Succeeded payment, its complete history
and signed receipt. The two original races retain their original setup and count
assertions. Full before/winning/after collections prove isolation and losing
attempt cleanup. Complete public fields, UUIDs, exact 1,299 minor units/PLN,
nullability, dates and versions match actual stored values. Supporting reads and
signed duplicate deliveries preserve the final state and add no dependency call.
Repository conflicts are explicit command evidence; no public update endpoint or
HTTP 409 is invented. Their operation-linked HTTP evidence is the complete Get.

## Actual transaction rollback

PAY12-15/16 interrupt Checkout after the actual Payment replacement or history
insert. PAY12-17–19 interrupt webhook completion after the actual Payment
replacement, history insert or receipt replacement. A real SDK-verified pending
receipt is durably received before those webhook transactions; its original
received time/digest/normalized fields remain part of the populated baseline.

Each decorator awaits the real MongoDB write before raising a documented
OperationFailure. All three session-visible collections prove the reached stage;
an independent reader still sees the complete original database. Every staged
Payment field, exact prior-state archive, receipt transition and unrelated document
is checked. The real transaction aborts, the session ends, and every populated
collection equals the full baseline. There is no pre-write stand-in or deliberate
duplicate archive used as a substitute for observing staged writes.

Checkout keeps the existing complete safe 500/internal_error; webhook completion
keeps 503/webhook_retry. No staged attempt/history/receipt marker or provider
session leaks. After removing the scoped fault, an actual HTTP retry succeeds.
Complete recovered Checkout/provider form or paid Payment/receipt contracts and
exact deltas are checked, followed by unchanged supporting requests.

## Claims, leases and old workers

PAY12-20/21 coordinate eight actual fulfillment command instances. Each reaches
the real atomic claim boundary. The selected worker holds the real active lease
while the seven competitors each execute the actual claim and return no work.
Only then does the winner continue through the real Kiota HTTP adapters. Complete
winning receipt/progress/lease fields and all three collections survive, with one
logical Paid write and one controlled invoice. Unrelated work has already been
completed through the actual worker and cannot steal the main claim.

PAY12-22–24 explicitly exercise real repository claims at 299,999, 300,000 and
300,001 milliseconds. The boundary is inclusive: no reclaim before expiry; a new
lease/attempt at exact expiry or after. Actual old save_order_paid, complete and
fail commands cannot overwrite the replacement. PAY12-28 proves those three
commands also reject an expired lease before anyone reclaims it. These actions
are honestly identified as repository commands, not HTTP calls or worker batches.
The complete active receipt remains processing where that is the authored result.

PAY12-25–27 pause an actual old worker just before save_order_paid, complete or
fail, after any earlier downstream effects have really occurred. At exact lease
expiry a second actual worker reclaims and completes through the adapters. The
resumed old command uses its originally captured time and lease: its real write
fails by lease identity even with that stale clock. The complete new winner and
all upstream state remain unchanged. Both worker runs are counted, while exactly
one logical Paid mutation/invoice exists. Final completion clears both lease
fields and retains exact client/invoice/data-version references.

Worker operation links select the real signed setup acknowledgement; worker
execution is an explicit action with separately captured outgoing exchanges.
Controlled HTTP adapters demonstrate orchestration and fencing; they do not
claim hosted Stripe, deployed Azure transaction behavior, or actual concurrent
remote invoice generation. The four retained published Invoice/PDF scenarios
continue to supply that service-boundary evidence separately.

## Verification and scope

The 54 new guards reject scope/header drift, blocking/unreleased coordination,
missing arrivals, duplicate retry witnesses, changed participant/version/order,
wrong conflict type/owner, incomplete winners, outside visibility and corruption
of staged Payment/archive/receipt/unrelated state. Source checks require full
native contracts and explicit actions for all 28 cases. Eight real-SDK regressions
verify both participant labels and both success/expiry schedules cross payload
validation before reaching the write gate.

Full local/CI results and immutable archive/render evidence are recorded after
verification. Docker is unavailable locally; actual MongoDB transaction/claim
proof, the published Invoice/PDF cases and container/image checks come from CI.

Task 12 and Tasks 13–16 remain open until their own verification completes.
Overall PAY/22, hosted Stripe rollout and the first LiveDocs deployment remain
separate. Successful-main image/Blob publication and selected manual LiveDocs
refresh/Terraform deployment are unchanged. No runtime branch tracing or new RAG
retrieval behavior is claimed.
