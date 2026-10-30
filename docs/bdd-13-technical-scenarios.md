# PAY-BDD-13 — Technical scenarios

Task 13 adds 21 technical BDD cases and strengthens the four existing health
cases. All 370 previous identities and named matrix outcomes remain. There are
391 BDD cases across seventeen features; seven named API operations retain
42/42 declared status pairs and 381 exported HTTP outcomes. A separate
`technical-scenarios.tsv` projection keeps documentation, lifecycle, cancellation
and command evidence distinct from declared API coverage.

Native Gherkin tables describe inputs, populated state, outcome kind and complete
HTTP expectations where a response exists. Shared JSON capture retains all setup,
primary, supporting and controlled-boundary exchanges. Actions and cancellations
have no invented HTTP status. Fifty-seven ordinary checks validate source links,
tables, witnesses and actual ASGI cancellation.

| Cases | Verified boundary |
| --- | --- |
| Existing PAY11-19–22 | Populated collections, actual probe/ping counts, complete problems, headers, provider sessions and full supporting read |
| PAY13-01–04 | Exact repeated Swagger/ReDoc/OAuth HTML, complete OpenAPI, cold export without lifespan or Mongo allocation, four generated exports |
| PAY13-05 | Stop/restart only the scenario-owned replica, same container/endpoint, safe readiness failure, live/docs/independent service remain available, exact preserved state |
| PAY13-06 | Real standalone ping readiness succeeds; actual transaction-dependent checkout fails safely without Stripe or stored mutation |
| PAY13-07 | Cancel real ASGI readiness inside a Mongo driver await; retain CancelledError and recovery, no completed response |
| PAY13-08/09 | Cancel actual fulfillment during Orders read or after controlled Paid mutation before acknowledgement; active lease retained, exact-expiry recovery, one logical Paid write and invoice |
| PAY13-10 | Separate hosts/databases with shared business IDs and different full values; scoped peer deletion leaves primary state/readiness intact |
| PAY13-11–13 | Real index option conflict, duplicate unique-key build failure or bounded unreachable startup; no host yield, actual resource closure, targeted repair/restart where possible |
| PAY13-14–17 | Actual fulfill/replay CLI rejects limits 0/1001 before allocation; fulfillment library guard is also exercised |
| PAY13-18–21 | Actual CLI limits 1/1000 over two eligible records, explicit oldest fixture, exact processed counts/stdout/full state, drain and zero-work repeat |

Mongo clients are actual clients. Close proof requires a closed client to reject
an actual ping, Orders clients report closed and actual Stripe provider close
returns. Batch commands use stored SDK-verified work without live credentials.
Controlled invoice/Orders responses prove the local adapters and durable recovery,
not a deployed external system or live Stripe behavior. Standalone readiness
reflects the implemented ping-only policy, not transaction readiness.

The service source, persistence schema, dependencies, images, workflows and
coverage/security gates are unchanged. Task 14 contract hardening, Task 15
flows/rules/RAG and Task 16 final audit remain separate. Overall PAY/22 and
first LiveDocs rollout stay open.

## Verification

[Implementation CI 41018107293](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/41018107293)
passes source/contract/wheel/security checks, all five suites, documentation and
quality gates, real Mongo-backed container smoke, Trivy and the final gate.
Frozen head: `74a9a103452d13aa82c83e37947d15fb92ca1b7d`;
tested merge: `7cce68f438fb185429b04fdae3fe77d95b0c5f56`;
exact tree: `422aed9dec71cba079e96e34091be0339b384ec1`.
The tested merge has the merged Task 12 base and this source head as its parents,
and its tree matches the source head exactly.

- **1,717 passing executions, zero failures/skips:** Domain 134, Application 82,
  Infrastructure 274, ExternalProviders 175, Acceptance 1,052 (**391 BDD + 661
  ordinary**). All previous members remain; additions are 21 BDD and 57 ordinary
  checks. There are **1,542 distinct members**, retaining the intentional
  175-member provider overlap. All 370 previous Allure identities/descriptions
  survive; four health cases gain steps and the other 366 retain their steps.
- Domain/Application/Infrastructure coverage is 96.88% / 96.16% / 91.03%
  with separate unchanged 70% floors. Provider/Acceptance coverage is
  96.35% / 98.45%. Generated-client exclusions and all dependency,
  image, workflow and security/coverage pins remain unchanged.
- Seven official outer artifact digests and the complete archive inventory,
  paths, sizes, hashes, sources, exports and JUnit checks pass. The frozen inner
  bundle is **20,114,089 bytes**, SHA-256
  `4a3dc527754478747ab353bc0466f50b49f83bf11446312b2c624caa87a3486b`,
  with **16,609 entries** and **16,197 attachments**
  (13,647 JSON, 2,533 native CSV tables,
  four actual Invoice PDFs and thirteen expected-fault logs).
- Allure 2.46.1 renders every case, authored description, ordered nested step and
  attachment with bytes matching the raw evidence. Every rendered case,
  attachment and entry asset passes local HTTP reads. All test identity fields
  remain intact.
- Independent native-table/wire/BSON audits verify all 21 new technical cases
  and four strengthened health cases: exact HTML/schema/export bytes and headers,
  real probe/ping counts, full populated state/indexes, owned same-container and
  same-endpoint restart, actual standalone transaction failure, cancelled driver
  and worker exchanges, complete active/recovered receipts, exact-expiry recovery,
  one logical Paid mutation/invoice, actual resource closure, startup rejection
  and targeted repair, two-database isolation, actual CLI limits/counts/stdout,
  full batch changes and unchanged zero-work repeats. Commands/cancellations
  retain actual outcomes without invented HTTP statuses.
- All prior Task 3–12 semantic audits pass. Four Invoice PDFs match captured and
  stored bytes; text extraction verifies invoice IDs, client/product and PLN
  amounts. Thirteen expected-fault logs match real exception boundaries and
  API trace IDs without fixture-key/auth leaks. Captures include
  **4,654 HTTP pairs**, **4,638 completed responses**,
  **16 intentional transport failures** and
  **366 explicit action pairs**.
- Locally, **1,116 unit tests pass**. Pinned sync/format/lint, strict Pyright,
  architecture, links, seven-operation/381-outcome export, wheel build/install,
  Markdown links and git checks pass. OpenAPI/flows/validation policies are
  byte-identical to Task 12; named HTTP matrix rows are unchanged and operation
  links add only the separate technical projection/current counts. Docker is
  unavailable locally; CI supplies native Mongo/container/published Invoice proof.

Task 13 is complete. The documentation-only completion head receives full CI and
fresh archive/render/PDF audits before PR handoff. Frozen/final comparison requires
identical JUnit/Allure identities, outcomes, descriptions, ordered steps, all
seventeen features, four exports and every per-case attachment type count.
PR image publication/Blob upload skip as designed. Main archival and the selected
manual LiveDocs/Terraform refresh process remain unchanged. Tasks 14–16, overall
PAY/22, hosted Stripe and the first LiveDocs rollout remain open.
