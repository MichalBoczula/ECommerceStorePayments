# ADR-0024: Scenario-local immutable BDD evidence

Status: Accepted

Date: 2026-10-29

## Context

The original BDD results contained readable steps but no descriptions, executable
input/expected tables or HTTP attachments. A latest-response field cannot preserve
setup, concurrent and supporting work or explain fulfillment recovery.

## Decision

Use the existing pytest-bdd adapter and scenario IDs with shared, scenario-local
capture in test infrastructure. Serialize observations when they occur, correlate
HTTP request/outcome pairs and explicit actions, and publish queued JSON on the
scenario thread. Preserve native table attachments, exact body bytes and safe
headers. Failed steps retain earlier evidence. The normal source and Acceptance
entry points enforce the evidence structure before publication.

Follow the Products, Users and Invoice collectors while using Python Gherkin title
IDs and pytest hooks. Keep scenario instances independent of generated resource
identifiers. Mark controlled downstream transports explicitly and preserve real
FastAPI/MongoDB acceptance execution. No new package or application change is
needed. See [the structure and verification contract](../bdd-02-evidence.md).

## Consequences

LiveDocs receives larger archives containing actual per-scenario observations.
Preserving full oversized-webhook bytes is intentional. Stable identities support
later source/evidence joins; source flows remain declared metadata, with richer
RAG links deferred to Task 15. Later packages extend body/state assertions without
replacing the shared collector or weakening the baseline.

## Physical header evidence

[PAY-BDD-07](../bdd-07-webhook-verification.md) adds ordered `headerItems` to the
current capture alongside the header mapping. API requests/responses preserve
physical duplicate fields, including Stripe-Signature; each sensitive item is
redacted. Publication validates shape, redaction and mapping agreement while
preserving exchange/index association checks. The JSON remains an ordinary
Allure attachment within the existing immutable bundle format.

## Receipt and replay evidence

[PAY-BDD-08](../bdd-08-webhook-lifecycle.md) uses native tables for complete
normalized receipts, stored-state deltas and public reads. Explicit controlled
completion/conflict actions distinguish injected failures from actual committed
transactions. Operator replay records actual processed/repeated results and
full before/after collections; every HTTP delivery and supporting read keeps its
own captured exchange. No new collector or application behavior is introduced.

## Business validation evidence

[PAY-BDD-10](../bdd-10-business-validation.md) preserves exact authored Orders
numeric tokens and complete repeated rejection/state evidence. Non-JSON numeric
constants such as NaN and Infinity retain their exact invalid JSON text and bytes;
the collector does not place those constants in a JSON evidence envelope.
Standalone typed domain/converter checks retain their ordinary suite identity
and do not claim an HTTP input contract or operation-linked exchange.

## Framework evidence

[PAY-BDD-11](../bdd-11-framework-failures.md) authors exact request bytes and
complete safe problem/protocol/state tables, including repeated rejections.
Explicit fault actions and actual hit witnesses identify unexpected-failure
boundaries; they do not claim natural dependency failures or branch tracing.
Valid JSON exponents outside the finite float range use a `json-number-text`
convenience view with unchanged original bytes, preserving a valid evidence
envelope. Non-JSON numeric constants remain `invalid-json`.

## Coordinated transaction and worker evidence

[PAY-BDD-12](../bdd-12-concurrency-atomicity.md) uses finite test-only gates around
real persistence/adapter calls. An actual X-Bdd-Attempt header and scoped async
identity join concurrent API and outgoing exchanges. Workers use scoped action/
exchange identities without inventing inbound HTTP. The collector restores the
parent scope after exceptions. Session-visible staged writes and independent
outside snapshots distinguish actual MongoDB abort from pre-write injection;
complete winners and real lease errors prove the observed boundaries, not runtime
branch tracing or deployed Azure behavior. Native tables remain separate CSV
attachments beside the immutable JSON observations and physical HTTP pairs.


## Technical lifecycle evidence

[PAY-BDD-13](../bdd-13-technical-scenarios.md) separates completed HTTP responses,
cancelled exchanges and explicit command/startup actions. Native tables use
`<none>` for absent HTTP status/media; cancellation retains the actual exception
and owning action. The shared validator checks all physical pairs, bytes, header
items, indexes and action witnesses before interpreting the outcome kind.

`technical-scenarios.tsv` projects real source functions and framework routes into
`operation-links.json.technicalScenarios`, independently from the seven named API
operations and their 42 declared status pairs. Real owned containers and clients
support lifecycle observations; controlled downstream replies remain identified
as controlled. This does not change service behavior, published HTTP contracts,
production topology or the manual LiveDocs refresh process.
