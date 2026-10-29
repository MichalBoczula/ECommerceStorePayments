# PAY-BDD-09 — Fulfillment and invoice recovery

Task 9 strengthens four original worker cases and adds **36 scenarios**, retaining
all 179 earlier BDD identities. There are **215 current BDD cases**. Native
Gherkin tables author worker inputs, processed counts, complete receipt presence,
exact HTTP sequences and all ten Payment read fields. Every new scenario first
settles a populated unrelated payment/history/receipt fixture through the worker.

## Durable work and recovery

The real one-shot worker runs with fresh MongoDB clients/event loops and no
Stripe API/signing credentials. The SDK verifier, public Payments API, real
MongoDB transactions, Kiota adapters and worker/repository implementations run.
Each observed worker result compares all 26 potential receipt fields, explicitly
distinguishing absent fields from null. Original verified fields/dates/digests,
Payment/current history and every unrelated document remain unchanged. No worker
run charges Stripe again or archives another Payment version.

Cover authoritative Paid state, existing completed invoice/version references,
order/update/lookup/create failures, exact money/ownership/state mismatches,
malformed metadata, stale/missing payment associations, retries and repair/resume.
Paid progress is saved before invoice work and retained across failures. A
successful or ambiguous Paid response still requires authoritative Paid readback;
a failed/Generating invoice response is not treated as completed. Invoice
creation requests pass the client/order route IDs with an empty body; the
returned `clietDataVersionId` belongs to Invoice and is distinct from the client.

Only the FulfillmentService clock is isolated, with real stored deadlines used
for due retries. Three/eight/ten actual attempts exercise exponential backoff,
the one-hour cap and exhaustion. A run one millisecond before due cannot claim
work. Failed work remains failed until explicit operator resume; resume retains
Paid progress. Controlled repository-boundary faults before/after Paid progress
and completion distinguish interrupted writes from lost acknowledgements after
real commits. Actual competing claims, lease expiry/fencing and transactional
rollback remain Task 12.

## Published Invoice and actual PDF evidence

Four cases additionally run the real published Invoice service, its isolated
replica-set database and Chromium PDF generation. The new test-only image pin is
`mb0101/ecommerce-store-invoice-api@sha256:6e9244804a2645f8aecaff89f60cff03337a94b70ca877195e585c678f2d996a`,
from master `d28dd23c14dee519ac753da6fe2c32289581ca3e`, successfully scanned/published
by [Invoice CI 40908053521](https://github.com/MichalBoczula/ECommerceStoreInvoice/actions/runs/40908053521).
The disposable container uses the explicit `Testing` environment with local PDF
storage. The image's Production Blob-storage requirement remains enforced.
Existing older published-image compatibility tests and production image selections
remain unchanged. The older fulfillment image predates the PDF download route.

Payment checkout setup retains its controlled order/provider boundary. Worker
Orders/invoice calls use the actual published API. Each physical exchange and
adapter-visible outcome has its own capture and explicit mapping. Lost Paid and
invoice acknowledgements occur only after recorded successful remote responses;
no fabricated remote failure is presented as an actual service outcome.

The PDF failure case replaces only the disposable service's `/app/Invoices`
directory with a blocking file. Actual generation returns 500 and leaves a Failed
reservation after Paid. Repair permits a due retry to complete the same invoice
identity. Two client data versions verify latest-version selection. Download
checks media/disposition, PDF signature/EOF/page marker, length and byte-for-byte
equality with the actual stored file, retains exact Base64/SHA HTTP evidence and
attaches the binary PDF. Repeated worker execution preserves completed work.
These cases do not change or deploy the Invoice service.

## Verification and scope

All **853 local unit tests** pass, including 48 new evidence/source regressions.
Ruff/format, strict Pyright, architecture, operation links, 7-operation/216-outcome
export, byte-identical non-link exports, pinned lock/sync, wheel build/install,
Markdown links and git checks pass. A temporary real-Kiota/application probe
verifies all 21 controlled HTTP modes. Ordinary warnings remain visible. Docker
is unavailable locally; CI supplies actual MongoDB/Invoice/container/image proof.

[Implementation CI 40972811871](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/40972811871)
passes all source/contract/wheel/security checks, five suites, documentation and
quality gates, real Mongo-backed container smoke, Trivy and final gate. Frozen
implementation head: `97bee0650b8a4d35548ec43aad178defc02344f6`;
tested merge: `6ad89f0c02e6d979152cc7149647bdad452dfae7`;
exact tree: `6bea1d319a62d2df56f31a6487aad7388ce7697d`.
Its exact parents/tree match the merged Task 8 base and this implementation head.

- **1,278 passing executions, zero failures/skips:** Domain 97, Application 82,
  Infrastructure 250, ExternalProviders 175, Acceptance 674 (**215 BDD + 459
  ordinary**). All Task 8 members survive, adding 36 BDD and 48 ordinary checks.
  There are **1,103 distinct members**, retaining the intentional 175-member
  provider-suite overlap.
- Coverage remains 96.88% / 96.16% / 90.90% for Domain/Application/Infrastructure,
  with separate unchanged 70% floors. Provider/Acceptance report 96.35% / 98.06%.
  Generated-client exclusions, dependency/security gates and workflow pins stay.
- All seven official outer artifact digests and closed inventory/path/size/hash/
  source/export/JUnit checks pass. Frozen inner bundle: **11,090,989 bytes**,
  SHA-256 `7bc2044fba722d227e4937528fa8824b033d0c88d0a74c8e04174e1ddf61ec84`,
  **9,134 manifest entries**: 215 results, thirteen features, four exports and
  **8,902 attachments** (7,458 JSON, 1,437 native CSV tables, four binary PDFs and
  three retained expected-fault logs).
- Allure 2.46.1 renders every case/description/ordered nested step/attachment
  matching raw bytes. Every case/attachment/entry asset passes local HTTP reads.
  Every earlier full name/history/test identity/title path survives. Three
  non-link exports match Task 8; links add only 36 cases/current counts.
- Independent raw HTTP/BSON checks cover **40 worker cases and 61 complete
  state/HTTP/read evidence sets**, **89 worker runs** including 28 real earlier
  retry attempts, exact presence/nullability/counters/deadlines/cap/exhaustion,
  unchanged current/history/unrelated state, four local persistence faults and
  one repair/resume. Physical/adapter joins verify two lost real replies, one
  actual Failed-PDF storage repair and four completed/downloaded/stored PDFs.
  `pdftotext` additionally confirms the matching invoice UUID, fixture client/
  product, PLN subtotal 12.99, tax 2.99 and total 15.98 in every PDF.
- All earlier Task 3–8 audits pass. Captures have **2,518 HTTP pairs** (2,505
  responses and thirteen intentional transport failures), plus **219 explicit
  action start/result pairs**. The three retained logs match the previous
  intentional persistence exceptions and exact API-500 trace IDs, with no fixture
  key/auth leak. There is no new unexpected failure or skipped case.

Task 9 is complete. The documentation-only completion head is checked again in
full CI and with fresh archive/render/PDF audits before PR handoff.

There are no Payments application/API/persistence/dependency/production-image or
workflow changes. Declared operation/status coverage remains 27/42 with fifteen
reviewed gaps. Tasks 10–16 and overall PAY/22 remain open. Hosted Stripe rollout,
automatic successful-main Blob publication and selected manual LiveDocs/Terraform
refresh remain separate and unchanged.
