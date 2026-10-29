# Checkout failure and recovery — PAY-BDD-06

Task 6 strengthens seven original checkout cases and adds eighteen
`PAY06-01`–`PAY06-18` scenarios. All 81 earlier BDD identities and original matrix
rows remain. There are 99 current BDD cases across nine features. The safe
interrupted-persistence scenarios cover checkout's declared HTTP 500 response,
raising operation/status coverage from 26/42 to 27/42; its one reviewed gap is
removed, leaving fifteen for Task 11.

| Situation | Expected durable and HTTP behavior |
| --- | --- |
| Provider rejection | Complete safe 502 problem; Created reservation and its complete original snapshot survive. Repeated failures reuse the same form/key and preserve all fields. |
| Timeout before acceptance | Safe 504, no accepted session; recovery creates one session under the original reservation. |
| Timeout after acceptance | Safe 504, one accepted session, Created reservation; recovery replays the identical form/key and persists that same session as Pending. |
| Invalid response or connection failure | Safe 502; preserve the durable attempt and exact state. A mismatched amount cannot confirm Pending. Recovery preserves any already accepted session. |
| Interruption before reservation persistence | Safe 500; only the initial version-zero Created payment exists, with no attempt, history or provider request. Recovery reserves and completes it safely. |
| Interruption before Pending persistence | Safe 500; provider accepted but the reservation remains Created. Recovery replays the same request and adds exactly the reserved previous snapshot. |
| Lost acknowledgment after Pending commit | Safe 500; the real current/history transaction already committed. Recovery only GETs the stored provider session and changes no durable field. |
| Legacy request version | A physically absent request-version field defaults to version 1; recovery remains card-only with the same attempt. Version 2 retains card/BLIK. Positive unsupported version 3 fails before provider HTTP without changing state. |
| Attempt age | Under the application comparison clock, 82,799.999 seconds succeeds; exactly 82,800 and 82,800.001 seconds require reconciliation without Stripe or writes. |
| Legacy Pending without attempt identity | Physically absent identity fields stay absent; reconciliation is required before any provider call. |
| Provider GET failure | Rejection/timeout preserves complete Pending/history/receipt state and provider sessions. Recovery reads the same session. |
| Preflight rejection | Disabled, nonpayable/missing/changed order and Succeeded payment retain the complete empty or populated state with exactly the allowed external calls. |

## Evidence and independent assertions

Every primary error table specifies status/media/code and all fixed problem
fields; trace IDs are present, hexadecimal and correlated with the response
header. Expected details, instance, empty errors/missing-properties and exact
field sets reject partial or leaking problems. The original ambiguous timeout's
setup response also has an explicit native expectation table and HTTP witness.

`checkout_recovery_checks.py` compares every current/history/receipt document,
including unrelated populated orders. Prepared states require exact versions,
null/provider/attempt fields, bounded UTC times and complete prior snapshots.
Recovery preserves reservation identity, start time and request version, appends
only the exact previous state, and retains every older snapshot. A committed
Pending acknowledgment loss permits no additional write. Full nested response
checks retain Task 5's explicit BSON precision rules.

The real Stripe SDK form and pinned API/media/idempotency headers are checked
against authored native tables for failed and recovered POSTs. Replays compare
actual encoded request bytes and keys. GET recovery has its own empty-body,
absent-idempotency-key contract. Actual exchange IDs join expectations to the
shared immutable HTTP evidence, including transport failures and supporting calls.

Recovery uses a fresh FastAPI composition root, lifespan, provider adapter and
MongoDB repository against the same database and controlled Stripe boundary.
Persistence faults are one-shot, target-order-scoped wrappers. The after-commit
fault calls the real transactional repository before raising; action evidence
records both actual collection snapshots and the commit result. Before-save
faults interrupt orchestration before the update. In-transaction rollback and
competing-writer/claim tests remain Task 12.

Temporal reserved fixtures are valid domain rehydrations inserted through the
repository. Only the application's age comparison is frozen; domain mutation
timestamps, HTTP windows and provider times remain real. Legacy fixtures
explicitly remove the historically absent fields and verify production
rehydration defaults. Ordinary repository writes would normalize those fields
and would not exercise physical absence. These fixtures change no schema or
application policy.

The controlled transport keeps accepted sessions separate from rejected or
malformed response payloads, preventing a failed response from poisoning later
replay. Its captures still use the real SDK request and shared collector.

## Verification and remaining work

All **699 local unit tests** pass, including 45 new assertion/source regressions.
Pinned lock/sync, formatting/Ruff/strict Pyright, architecture, exact links/OpenAPI
export, wheel build/install, changed Markdown links and git checks pass. Ordinary
warnings remain visible. Docker is unavailable locally; CI supplies real database,
Invoice, container and image evidence.

[Implementation CI 40946548030](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/40946548030)
passes all source/contract/wheel/security checks, all five suites, documentation
packaging, quality gate, real Mongo-backed container smoke, Trivy and final gate.
Frozen implementation head: `8c3359d2f8032f5b87b98327d73576172ead676c`;
tested merge: `b84f24bc477600394f78b06c901f2837872c4bfd`;
exact tree: `08d1034d949556f09a6c6d4e04aab412d32be9ba`.
Exact parents/tree were checked against Task 5's merged base and this head.

- **1,008 passing suite executions, zero failures/skips:** Domain 97, Application
  82, Infrastructure 250, ExternalProviders 175, Acceptance 404. There are **833
  distinct members**, retaining the intentional 175-member provider-suite overlap.
  Acceptance is **99 BDD + 305 ordinary**. Every Task 5 member survives, with
  eighteen BDD and 45 ordinary regressions added.
- Coverage remains 96.88% / 96.16% / 90.90% for Domain/Application/Infrastructure
  and 96.35% / 98.06% for ExternalProviders/Acceptance. The separate 70% floors,
  generated client exclusions and security gates remain unchanged.
- All seven official outer artifact digests match. The frozen inner bundle is
  **3,151,587 bytes**, SHA-256
  `a31f42bef9079d2283bf14396c2f20b7479cb375e6476e678dbd677e5073fdc8`, with **2,832 verified
  manifest entries**: 99 results, 9 features, 4 exports and **2,720 attachments**
  (2,326 JSON, 391 native CSV tables and 3 automatically captured fault logs).
- Pinned Allure 2.46.1 renders every case, authored description, ordered/nested
  step and attachment matching raw bytes. All case/attachment/entry assets pass
  local HTTP reads. Every prior name/full name/history/test identity/title path
  survives. OpenAPI/flows/validation-policy bytes match Task 5; operation-links
  adds only eighteen scenarios/current counts and retires the covered 500 gap.
- Independent raw HTTP/BSON checks verify **22 complete safe failure/state
  outcomes, 15 complete recoveries through 11 fresh app instances, three persistence
  fault points including committed acknowledgment loss, exact form/key replay,
  repeated rejected state, physical legacy fields, card-only/unsupported versions
  and all three millisecond age boundaries**. Earlier Pay/read/retry/history/
  checkout success audits pass on the same bundle.
- Captures contain **774 HTTP request/outcome pairs**: 763 responses and 11
  intentional transport failures, plus **57 explicit action start/result pairs**.
  All BDD cases passed; the three automatic logs belong to the expected injected
  server-failure scenarios and the API problems remain complete and safe.

Task 6 is complete. A final documentation-only completion head is checked again
in full CI and with fresh archive/render audits before PR handoff.

Application/API/persistence code, dependencies, workflow/image pins, original
frozen baseline/matrix rows, security/coverage floors and publication paths are
unchanged. Only the genuinely covered checkout-500 gap is retired. Tasks 7–16
and overall PAY/22 remain open. Controlled provider evidence does not close the
separate real hosted card/BLIK rollout. Main Blob publication remains automatic;
selected LiveDocs refresh and Terraform deployment remain manual.
