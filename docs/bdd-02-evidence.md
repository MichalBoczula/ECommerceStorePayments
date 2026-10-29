# Shared BDD structure and evidence — PAY-BDD-02

Task 2 preserves all original 51 scenario IDs, titles and outcomes. Each scenario
has an authored description, an executable input table and an expected HTTP table.
The order tables configure the controlled Orders fixture's identifiers and money;
health tables select the actual requested path. Expected tables check status,
media type, public code and the listed typed JSON values. Existing persistence,
history, provider and contract assertions still execute. Tasks 3–14 deepen those
assertions and add missing cases; these tables do not claim complete body/state
coverage today.

## Identity and report structure

The pattern follows Products, Users and Orders/Invoices: a scenario-local collector,
immutable captures, Allure JSON attachments, native Gherkin tables and explicit
scenario identity. Payments uses its existing leading `PAYxx-xx` title ID as the
canonical source identity. It does not need a second Gherkin tag containing the
same ID. The result has exactly one `service=payments`, `scenarioId` and
`instanceId` label, plus a **Scenario identity** JSON attachment. Existing Allure
names, full names, history/test identities and original JUnit names remain stable.

`instanceId` is SHA-256 of UTF-8 canonical JSON containing `scenarioId` and sorted
Examples parameters, with sorted keys, compact separators and no ASCII escaping.
An execution's random payment IDs, database names and timing do not enter that
identity. Every JSON attachment carries the same identity. Scenario descriptions
come from Gherkin, and pytest-bdd attaches the actual input/expected tables as CSV
inside their rendered steps.

## Actual HTTP and action evidence

`tests/acceptance/evidence.py` is shared test infrastructure. `EvidenceClient`
builds and sends each real TestClient request once and reads its response without
replacing it. Controlled Orders/Invoice HTTP and Stripe SDK transports use the same
collector. Every request gets a scenario-local sequence and `exchangeId`; the
matching response or failure preserves the metadata captured at request start.

**HTTP NNN request/response/failure** attachments include the actual method, path,
query, headers, phase, step, target service, boundary role, optional concurrent
attempt and owning worker action. Request/response content includes media type,
parsed JSON where applicable, raw text, exact Base64 bytes, length and SHA-256.
Empty, malformed JSON, text and binary bodies retain their distinctions. Bodies
are not truncated, including the oversized webhook. Authorization/API keys and
cookies are redacted in headers. Synthetic webhook signatures are retained;
transport/action exception messages are omitted and their exception types remain.

All API requests use the collector, including Given setup, the asserted response,
both concurrent requests, webhook redelivery and Then supporting health calls.
**Expected response** explicitly lists the actual exchange IDs whose responses
were asserted; it does not infer the primary response from the last attachment.
Fulfillment's original acknowledgement assertion truthfully refers to its Given
exchange. Concurrent calls have distinct attempt IDs independent of completion
order. **Scenario evidence index** enumerates every captured HTTP exchange.

Repository terminal-state preparation, durable worker invocations and making a
retry due have **Action NNN start/result/failure** records. Worker outputs record
actual fulfillment status, order status, invoice identity and downstream write
counters. Worker HTTP calls refer to the action that caused them. The Orders,
Invoice and Stripe boundaries are marked `controlledBoundary=true`: these are
actual adapter/SDK requests against controlled transports, not live account or
external-service execution claims. API and MongoDB behavior remain real in CI.

Records are serialized when observed and queued under a lock. Worker threads never
call Allure. Hooks flush on the scenario thread after successful/failed steps and
at scenario completion, so an assertion failure retains already observed work.
The next response cannot overwrite earlier evidence. Each fixture owns its
collector and retains the existing database/client cleanup.

## Publication guard and verification

The existing `links` stage checks descriptions and input/expected source tables,
including agreement with the frozen status/code matrix. The normal Acceptance
runner retains the Task 1 baseline guard and also validates all actual attachments:
identity/labels, descriptions, safe attachment paths, rendered tables, executed
table values, exact content digests, request/outcome pairs, action pairs, complete
exchange index and real asserted response witnesses. Missing evidence fails CI
before the existing LiveDocs packaging/upload stages. Exports, package workflow,
Blob publication and manual selected LiveDocs refresh are unchanged.

Regression tests cover immutable snapshots, exact body formats, concurrent pairing,
main-thread publication, safe API/Stripe failures, failed/canceled actions, source
regressions and corrupt/missing/foreign attachments. A subprocess runs the actual
pytest-bdd/Allure hooks over the four health sources with the HTTP unit database
adapter. It checks native CSV/JSON output, the supporting liveness request and
retained evidence after an intentional assertion failure. The child results are
isolated from published acceptance results. Real MongoDB scenarios and full image
verification run in CI because Docker is unavailable in the editing environment.

Implementation verification is in progress; the backlog checkbox stays open until
full CI and an independent archive/render audit pass. Tasks 3–16 and overall
PAY/22 remain open. Sixteen declared status gaps remain assigned to Task 11.
