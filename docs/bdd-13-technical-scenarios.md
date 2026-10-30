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

Implementation verification is in progress. The Task 13 backlog remains open
until full CI and the complete raw/rendered artifact audit pass.
