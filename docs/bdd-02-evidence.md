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

## Verified implementation

[CI run 40929738816](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/40929738816)
passes all source, contract, wheel, security, suite, package, container smoke/image
scan and final gates. Frozen implementation head:
`da5ab8ae7bdbdc7a985fc0164ee3569f58d470b5`; tested merge:
`dfbce2e797d3777d280ee8b200fcb538a6e327d5`; exact tree:
`0cfcaa99266c5f52688ba49758bbd451d8e84847`. Parents and tree were checked against
Task 1's merged base and the PR head.

- **814 passing suite executions, zero failures/skips:** Domain 97, Application 82,
  Infrastructure 250, ExternalProviders 175, Acceptance 210. There are 639 distinct
  members; the intentional 175-member external-provider overlap remains.
  Acceptance contains the same 51 BDD plus 159 ordinary tests, retaining every
  Task 1 member and adding 35 shared-evidence regressions. Local unit tests: 553.
- Domain/Application/Infrastructure line coverage remains 96.88% / 96.16% /
  90.90%, with the existing separate 70% floors. ExternalProviders/Acceptance
  report 96.35% / 98.06%. Application code, dependencies, baseline and matrix,
  workflow pins and scan rules remain unchanged. All four generated exports are
  byte-identical to Task 1.
- All seven downloaded outer artifacts match GitHub's SHA-256 digests. The frozen
  inner bundle is **841,285 bytes**, SHA-256
  `c01cd6073f3e69aa5f30742f66c4e65a8875089f0db53f45789fbf0d09a44558`, with
  **816 verified manifest entries**: 51 results, 5 feature sources, 4 exports and
  **756 attachments** (654 JSON, 102 native Gherkin CSV tables).
- An independent closed-inventory/path/size/hash/source/JUnit/raw-result audit and
  pinned Allure 2.46.1 render pass. Every original name/full name/history/test
  identity/title path and outcome is retained. Every rendered case, description,
  ordered step and attachment matches its raw result; all case/attachment/entry
  assets pass local HTTP reads. Every case has both executable tables and JSON
  identity, input, expected-response and exchange-index evidence.
- Actual captures contain **213 request/outcome pairs**: 207 responses and 6
  transport failures, plus 12 explicit action start/result pairs. Setup, both
  concurrent attempts, supporting liveness, lost acknowledgements and worker-owned
  downstream calls are verified. Complete oversized-webhook bytes and all body
  digests survive raw packaging and rendering. Private authorization headers and
  exception messages are absent from their designated evidence fields.
- Pinned lock/sync, formatting/Ruff/strict Pyright, architecture, exact source and
  OpenAPI commands, and wheel build/install pass locally. Docker is unavailable
  locally; full real MongoDB/Invoice/container evidence comes from CI.

Task 2 is complete. Tasks 3–16 and overall PAY/22 remain open. Sixteen declared
status gaps remain assigned to Task 11. A final documentation-only completion
commit is checked again in full CI and with fresh artifacts before PR handoff.
Selected LiveDocs refresh remains manual after the main archive is published.
