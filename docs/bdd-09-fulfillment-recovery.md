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

The implementation adds **48 evidence/source regressions**. Full local/CI,
archive and rendered-report results are recorded after execution below.

There are no Payments application/API/persistence/dependency/production-image or
workflow changes. Declared operation/status coverage remains 27/42 with fifteen
reviewed gaps. Tasks 10–16 and overall PAY/22 remain open. Hosted Stripe rollout,
automatic successful-main Blob publication and selected manual LiveDocs/Terraform
refresh remain separate and unchanged.
