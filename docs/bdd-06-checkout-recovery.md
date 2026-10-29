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

Implementation verification and the full CI/archive/render audit are recorded
here after they pass. Forty-five new regressions check complete failed/recovered
state, safe problems, one-shot persistence fault behavior, accepted-session
retention, exact SDK replay, explicit legacy request version and source tables.

Application/API/persistence code, dependencies, workflow/image pins, original
frozen baseline/matrix rows, security/coverage floors and publication paths are
unchanged. Only the genuinely covered checkout-500 gap is retired. Tasks 7–16
and overall PAY/22 remain open. Controlled provider evidence does not close the
separate real hosted card/BLIK rollout. Main Blob publication remains automatic;
selected LiveDocs refresh and Terraform deployment remain manual.
