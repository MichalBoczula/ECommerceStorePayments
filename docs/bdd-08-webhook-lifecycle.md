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
A historical Pending document physically missing attempt and request-version
fields remains unchanged.
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

All **805 local unit tests** pass (754 retained plus 51 new evidence/source
regressions), with ordinary warnings visible. Pinned lock/sync, formatting/Ruff,
strict Pyright, architecture, operation links, 7-operation/180-outcome OpenAPI
export, three unchanged non-link exports, wheel build/install, changed Markdown
links and git checks pass. Docker is unavailable locally; CI supplies real
MongoDB/Invoice/container/image evidence.

[Implementation CI 40965165937](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/40965165937)
passes every source/contract/wheel/security check, all five suites, documentation
packaging, quality gate, real Mongo-backed container smoke, Trivy and final gate.
Frozen implementation head: `1f41f6cac19cc305d6cc69e61d055e4b0f77135a`;
tested merge: `85dc59e44c79c9966f338a575afeef0a62eb6802`;
exact tree: `2c5633d424c396c38c6993f51895f0710edbb4c1`.
The merge parents/tree match Task 7's merged base and this implementation head.

- **1,194 passing suite executions, zero failures/skips:** Domain 97, Application
  82, Infrastructure 250, ExternalProviders 175, Acceptance 590. Acceptance is
  **179 BDD + 411 ordinary**. Every Task 7 member survives; 35 BDD and 51 ordinary
  checks are added. There are **1,019 distinct members**, retaining the intentional
  175-member provider-suite overlap.
- Coverage remains 96.88% / 96.16% / 90.90% for Domain/Application/Infrastructure,
  with separate unchanged 70% floors. ExternalProviders/Acceptance report
  96.35% / 98.06%. No generated-client exclusion or security gate changes.
- All seven official outer artifact digests and closed inventory/path/size/hash/
  source/export/JUnit checks pass. Frozen inner bundle: **7,385,444 bytes**,
  SHA-256 `0d6042323fb400cfa30dea352cf0c1810020b9b6aef90c143edb3329750bc220`,
  with **6,303 verified manifest entries**: 179 results, eleven features, four
  exports and **6,109 attachments** (5,080 JSON, 1,026 native CSV tables and three
  retained expected-fault logs).
- Pinned Allure 2.46.1 renders every case, authored description, ordered/nested
  step and attachment matching raw bytes. Every case/attachment/entry asset passes
  local HTTP reads. All prior full names/history/test identities/title paths
  survive. OpenAPI/flows/validation-policy bytes match Task 7; operation links add
  only 35 scenarios and current counts, preserving the fifteen reviewed gaps.
- Independent raw HTTP/HMAC/BSON checks verify **44 lifecycle cases and fifty
  complete receipt/state/read evidence sets**, all eleven completion reasons and
  five outcomes. Compare each complete current record and prior-state archive,
  all old/unrelated documents, normalized fields and original-byte digests.
  Reconstruct authored signed events and old-attempt references. Verify four
  unchanged collision rejections, four credential-free operator replays, two
  repeated fresh-app recoveries and twelve explicit controlled completion faults.
  All earlier Pay/read/retry/history/checkout/recovery/verification audits pass.
- Captures contain **1,705 HTTP request/outcome pairs:** 1,694 responses and eleven
  intentional transport failures, plus **79 explicit action start/result pairs**.
  Every BDD case passed. The three plain logs are the prior expected persistence
  faults; no new unexpected failure or skipped case is hidden.

Task 8 is complete. The documentation-only completion head is checked again in
full CI and with fresh archive/render audits before PR handoff.

No application/API/persistence/dependency/workflow/image policy changes are made.
Operation/status coverage remains 27/42 with fifteen reviewed gaps. Existing
future-timestamp verification behavior, coverage/security gates, automatic main
Blob publication and selected manual LiveDocs/Terraform refresh remain unchanged.
Fulfillment processing is Task 9; framework/atomicity/technical/contracts/RAG/final
packages and overall PAY/22 stay open.
