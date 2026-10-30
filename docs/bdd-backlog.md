# Payments BDD documentation backlog

One scoped package per PR. Preserve the FastAPI layers, existing domain behavior,
three MongoDB collections and transactional history/receipt/fulfillment semantics.
`[x]` means implemented and verified; `[ ]` remains. Full applicable CI is required
before merge. Source publication remains automatic after successful main CI;
selected LiveDocs refresh and Terraform deployment remain manual.

- [x] **PAY-BDD-01 — Baseline and coverage guard.** Preserve the original 51 BDD
  and 89 ordinary Acceptance cases, existing suites and reproducible dependency
  inputs. Freeze scenario/runtime identities, guard operation/status/cause links,
  classify the initial sixteen gaps and reject tracked verification output.
  See [baseline and verification](bdd-01-baseline.md).
- [x] **PAY-BDD-02 — Shared BDD structure and evidence.** Readable descriptions,
  stable IDs, meaningful input/expected Gherkin tables and centralized immutable
  JSON/HTTP/action evidence for setup, primary, concurrent and supporting work.
  See [structure and evidence](bdd-02-evidence.md).
- [x] **PAY-BDD-03 — Pay and payment reads.** Complete responses, exact money,
  provider/null/date fields, existing-state repeats and unrelated-order isolation.
  See [Pay and payment reads](bdd-03-pay-reads.md).
- [x] **PAY-BDD-04 — Retries and history.** Failed/Canceled retries, provider
  resets, versions, immutable snapshots, legacy records and rejected-state retention.
  See [retries and history](bdd-04-retries-history.md).
- [x] **PAY-BDD-05 — Checkout success.** Complete nested responses, provider
  request/idempotency parameters, card/BLIK and repeated-session behavior.
  See [checkout success](bdd-05-checkout-success.md).
- [x] **PAY-BDD-06 — Checkout failure and recovery.** Rejection, ambiguous
  timeouts, interrupted persistence, legacy attempts, age and request-version limits.
  See [checkout failure and recovery](bdd-06-checkout-recovery.md).
- [x] **PAY-BDD-07 — Webhook verification.** Actual signed bytes/headers,
  signature/payload/media/size boundaries and unchanged rejected state.
  See [webhook verification](bdd-07-webhook-verification.md).
- [x] **PAY-BDD-08 — Webhook lifecycle and replay.** Full receipts/reasons,
  transitions, async outcomes, stale attempts, collisions, duplicates and recovery.
  See [webhook lifecycle and replay](bdd-08-webhook-lifecycle.md).
- [x] **PAY-BDD-09 — Fulfillment and invoice recovery.** Explicit worker actions,
  complete durable progress/retries and Paid/invoice/PDF acknowledgement recovery.
  See [fulfillment and invoice recovery](bdd-09-fulfillment-recovery.md).
- [x] **PAY-BDD-10 — Business validation.** Isolated values, exact currency
  conversion and accepted boundaries; distinguish HTTP inputs from standalone rules.
  See [business validation](bdd-10-business-validation.md).
- [x] **PAY-BDD-11 — Framework failures.** Close reviewed status gaps, cover
  routes/methods/bodies/media and complete safe problems with populated-state checks.
  See [framework failures](bdd-11-framework-failures.md).
- [x] **PAY-BDD-12 — Concurrency and atomicity.** Deterministic races, full
  winners, real rollback, competing claims, lease expiry and stale-worker fencing.
  See [concurrency and atomicity](bdd-12-concurrency-atomicity.md).
- [x] **PAY-BDD-13 — Technical scenarios.** Health/readiness, startup/index
  failure, cancellation, isolation, command limits and documentation endpoints.
  See [technical scenarios](bdd-13-technical-scenarios.md).
- [x] **PAY-BDD-14 — Request/response contracts.** Source-derived types,
  presence/nullability/formats, descriptions/examples and captured-response checks.
  See [request and response contracts](bdd-14-contracts.md).
- [ ] **PAY-BDD-15 — Flows, rules and RAG links.** Stable identities and authored
  meanings, observed versus declared knowledge and validated HTTP/worker evidence joins.
- [ ] **PAY-BDD-16 — Final audit.** Full CI, original-case retention, every
  rendered case/attachment, archive integrity and the manual LiveDocs refresh handoff.

These packages improve tests and documentation. Existing STRIPE rollout and
application-deployment tasks in [the technical backlog](../TECHNICAL_TODO.md)
remain separate. No package claims runtime branch tracing or implemented RAG retrieval.
