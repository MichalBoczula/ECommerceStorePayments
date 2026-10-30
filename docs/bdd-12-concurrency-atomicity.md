# PAY-BDD-12 — Concurrency and atomicity

Task 12 adds **28 BDD cases** and strengthens the two original Pay/duplicate-webhook
races while retaining all **342 previous scenario identities and matrix outcomes**.
There are **370 BDD cases**, sixteen features, and 381 exported HTTP outcomes.
All seven operations and **42/42 declared status pairs** retain scenario intent;
there are no reviewed gaps. Fifty-four evidence/source checks supplement
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

[Implementation CI 41009200575](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/41009200575)
passes all source/contract/wheel/security checks, five suites, documentation and
quality gates, the real Mongo-backed container smoke, Trivy and final gate.
Frozen head: `f2dc7dccfa71033032ff4cb900ae3e10295f8c97`;
tested merge: `e653d366c44c1944e3553c3ba1bebd978c20ff79`;
exact tree: `9efdb34df35dd73abfeefaf580bb6b56ac3efba2`.
Merge parents/tree match the merged Task 11 base and this exact source head.

- **1,639 passing executions, zero failures/skips:** Domain 134, Application 82,
  Infrastructure 274, ExternalProviders 175, Acceptance 974 (**370 BDD + 604
  ordinary**). All Task 11 members survive, adding 28 BDD and 54 ordinary checks.
  There are **1,464 distinct members**, retaining the intentional 175-member
  provider-suite overlap. All 342 prior Allure identities survive; the two original
  races gain coordinated steps/descriptions while the other 340 retain theirs.
- Domain/Application/Infrastructure coverage is 96.88% / 96.16% / 91.03%,
  with separate unchanged 70% floors. Provider/Acceptance report 96.35% / 98.45%.
  Generated-client exclusions and dependency/security/workflow pins remain.
- Seven official outer artifact digests and the closed inventory/path/size/hash/
  source/export/JUnit checks pass. Frozen inner bundle: **18,324,512 bytes**,
  SHA-256 `ed4efd0b796127a8f3fec564d61ba0cf1d922ef85adbbba6da78fcc2754d6c72`,
  **15,300 manifest entries** and **14,910 attachments**
  (12,488 JSON, 2,406 native CSV tables, four retained
  actual Invoice PDFs and twelve expected-fault logs).
- Allure 2.46.1 renders every case, authored description, ordered nested step and
  attachment matching raw bytes. Every case/attachment/entry asset passes local
  HTTP reads. All prior full names/history/test IDs/title paths survive.
- Independent wire/BSON audits join **sixteen coordinated races** (fourteen new
  and both originals), **five actual post-write transaction abort/retry sets** and
  **nine claim/lease/fencing cases**. Complete proposals/winners, exact actual
  conflict types, native full responses/normalized receipts/provider forms/keys,
  immutable archives, session visibility/outside invisibility/session end,
  exact lease clocks, actual worker HTTP sequences and complete unchanged
  supporting/unrelated state all pass.
- Earlier Task 3–11 audits pass. Four actual Invoice PDFs match stored bytes;
  text extraction verifies invoice IDs, client/product and PLN amounts. Twelve
  expected-fault logs match exact exception types/messages and API trace IDs
  without fixture-key/auth leaks. Captures have **4,220 HTTP pairs**
  (4,207 responses and thirteen intentional transport failures), plus
  **330 explicit action start/result pairs**.
- Locally, **1,059 unit tests pass**. Pinned format/lint, strict Pyright,
  architecture, links, seven-operation/381-outcome export, wheel build/install,
  Markdown links and git checks pass. OpenAPI/flows/validation policies are
  byte-identical to Task 11; operation links add only the 28 new cases/counts.
  Docker is unavailable locally; actual MongoDB/container/published Invoice/PDF
  proof comes from the successful CI run above.

Task 12 is complete. The documentation-only completion head receives full CI and
fresh archive/render/PDF audits before PR handoff. The frozen/final comparison
requires all test identities/outcomes, Gherkin/exports, Allure descriptions/steps
and every per-case attachment type count to match, including the two coordinated
original races.

Tasks 13–16 remain open until their own verification completes.
Overall PAY/22, hosted Stripe rollout and the first LiveDocs deployment remain
separate. Successful-main image/Blob publication and selected manual LiveDocs
refresh/Terraform deployment are unchanged. No runtime branch tracing or new RAG
retrieval behavior is claimed.
