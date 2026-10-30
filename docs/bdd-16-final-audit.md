# PAY-BDD-16 — Final BDD audit

The sixteen Payments BDD packages are implemented and verified. This audit freezes
successful main [CI 41053783581](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/41053783581)
after Task 15, source `bebd01803175b442453c31403ddd2f58f1790cc8`, exact tree
`c9770402a539d2b0e505e2ac2a3be63ca0a13bb8`. It includes the real MongoDB/Invoice
suites, dependency/security gates, container smoke, image scan, service image
publication, final gate and successful documentation archival. PR-only Dependency
Review is correctly skipped on this main push.

The [manual LiveDocs refresh handoff](payments-livedocs-refresh.md) identifies
this exact archived package. Source publication and a prepared handoff complete
this BDD audit; selected LiveDocs image publication and Terraform deployment
remain **PAY/21**. Hosted Stripe and RAG ingestion/retrieval remain separate.

## Retention and suite evidence

The original main source is `ab868c98940741ef6422dfafcab71134f3e4b8e3`,
[CI 40219243830](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/40219243830).
Its independently downloaded official bundle matches the frozen **105,830 bytes**,
SHA-256 `bd1b5998877dd95b6a2c0e8cad56faadf64910b15855eccde32e31bb3c38bc1c`
and all sixty inventory entries. All **51 original Allure titles, full names,
history/test IDs, title paths and passing outcomes** remain in the current report.
The enriched descriptions, steps and tables are the intentional later packages.

`bdd-baseline.json` is byte-identical to the Task 1 implementation, SHA-256
`be5f74b88a63bc5df00f80d5912c17997ddfcf779481fccf98f6ba5c7a49fcde`.
Every frozen member of every suite remains, including the original **89 ordinary
Acceptance checks**. The two original provider parameter-ID migrations remain
explicitly recorded in that baseline; no new identity migration is introduced.

| Suite | Original members | Current passed | Line coverage | Gate |
| --- | ---: | ---: | ---: | --- |
| Domain | 97 | 134 | 96.88% | 70% |
| Application | 82 | 82 | 96.16% | 70% |
| Infrastructure | 250 | 274 | 91.03% | 70% |
| ExternalProviders | 175 | 175 | 96.35% | Report only |
| Acceptance | 140 | 1,172 | 98.90% | Report only |

All **1,837 executions pass with zero failures/skips**, representing **1,662
distinct members**. The exact 175-member duplicate set is the intentional provider
suite overlap with Infrastructure, with no other duplicate identities. All 569
original distinct members remain. Acceptance is **391 BDD + 781 ordinary**;
relative to the original it adds 340 BDD and 692 ordinary checks. The thresholds,
exclusions, pinned dependency inputs and security/package policies are unchanged.
Warnings remain visible.

## Source and evidence inventory

All seventeen feature files byte-match the audited checkout. Every expanded case
has a stable source/result ID, readable description, executed input/expected
Gherkin tables and immutable scenario identity. The existing source, BDD-result,
raw-evidence, captured-contract and source-link gates all pass. All 2,533 native
CSV tables also match expanded authored Gherkin values and multiplicities per case.
Named coverage is
**42/42 declared operation/status pairs**, with zero reviewed gaps; routing,
technical actions and cancellations stay separate.

| Feature | BDD cases | Native tables | HTTP exchanges | Paired actions |
| --- | ---: | ---: | ---: | ---: |
| `business_validation.feature` | 56 | 299 | 508 | 0 |
| `checkout.feature` | 9 | 41 | 63 | 2 |
| `checkout_recovery.feature` | 18 | 108 | 199 | 20 |
| `checkout_success.feature` | 7 | 41 | 110 | 2 |
| `concurrency_atomicity.feature` | 28 | 199 | 413 | 30 |
| `framework_failures.feature` | 71 | 438 | 711 | 76 |
| `fulfillment.feature` | 4 | 40 | 56 | 8 |
| `fulfillment_invoice.feature` | 4 | 60 | 127 | 19 |
| `fulfillment_recovery.feature` | 32 | 319 | 678 | 122 |
| `health.feature` | 4 | 16 | 45 | 0 |
| `payment_reads.feature` | 9 | 41 | 76 | 6 |
| `payments.feature` | 18 | 71 | 114 | 8 |
| `retries.feature` | 14 | 68 | 143 | 15 |
| `technical.feature` | 21 | 119 | 394 | 36 |
| `webhook_lifecycle.feature` | 35 | 320 | 422 | 22 |
| `webhook_verification.feature` | 45 | 270 | 495 | 0 |
| `webhooks.feature` | 16 | 83 | 100 | 0 |
| **Total** | **391** | **2,533** | **4,654** | **366** |

The four generated exports exactly match the separate generated-contract artifact
and the Task 15 proof. They contain seven HTTP operations, nine HTTP/command flows,
eight policies, 49 rejection rules, 68 outcome families, eleven receipt reasons,
59 methods and 164 canonical source sites. All declared source references resolve;
all 68 outcome families and eleven receipt reason meanings have actual linked
observations. This does not claim execution of the 49 source rejection rules.

All **4,654 physical request/outcome pairs** recompute successfully: 4,638
completed responses and sixteen intentional transport failures. There are 2,045
completed Payments responses, 2,608 external exchanges and one Payments
cancellation. Payments request phases retain 1,266 Given, 384 When and 396 Then.
Complete applicable responses also pass independent JSON Schema/format/protocol
checks; original bytes, physical headers, status, media, trace and length agree.
All **508 accepted webhook HMACs** independently match their captured original
bytes; this is not a current timestamp-freshness or real-account Stripe claim.

Every source-link group independently recomputes from its physical records.
A separate reference audit checks all 391 groups, 366 paired actions and **3,244
recorded receipt facts**, including actual attachment names/JSON pointers, phases,
ownership, concurrent attempts and controlled-boundary flags. Its **87 primary
action**, **49 setup HTTP** and **two supporting HTTP** witnesses stay distinct.
Declared steps/policies/rules remain source context; executed step/rule lists are
empty. Existing snapshots and same-event correlations do not establish causality.

All Task 15 identities, descriptions, outcomes, history/test IDs, ordered nested
steps and per-case attachment-name/type counts survive unchanged. Pinned official
Allure **2.46.1** distribution SHA-256
`37428164f310c8d137cfdd2c3a25d049b233261ddab13e1bd4dfd7627b5cbf8d`
is verified. All 391 rendered cases and **21,242 rendered attachments** match
raw bytes: **18,692 JSON, 2,533 CSV, thirteen expected-fault logs and four Invoice
PDFs**. Every one of **21,667 generated report resources** passes an actual local
HTTP read; JSON resources parse. This is exhaustive report-data/asset verification,
not pixel-by-pixel browser inspection or a deployed ACA check.

## Archive and publication

All **ten official Actions artifact digests** match GitHub metadata, including
all five suite reports, OpenAPI, generated contract, raw Allure results, source
bundle and publication receipt. The raw artifact byte-matches every one of the
21,633 bundled Allure result/attachment files.

| Frozen bundle field | Verified value |
| --- | --- |
| Generated at | `2026-10-30T12:27:08Z` |
| Compressed bytes | **26,035,978** |
| Unpacked bytes, including manifest | **121,876,542** |
| Inventoried files, excluding manifest | **21,654** |
| SHA-256 | `deaafa169451d60066f888b3f0130ec314c010961cb848d7604275f2294e1b82` |

Inventory is closed: every file/path, size, CRC, SHA-256 and attachment reference
resolves, with no duplicates, traversal or symlink entries. The unchanged limits
remain 100 MiB compressed, 500 MiB unpacked and 50,000 inventoried files. The
publication receipt's source/run/time/size/digest and immutable Blob path match
the independently verified archive exactly.

Main publishes the smoke-tested/scanned service image as the source SHA and
`latest`, both with digest
`sha256:4d768cdc7e1f9e1e92c15cbb2ec7a9ba075521f894b0f233ade1abde7b8371ca`.
Its subsequent archive job succeeds using content-validated, create-only uploads
and byte comparison on retries. This is the Payments service image; LiveDocs
selects the source reference and publishes its own image in the manual handoff.
An independent private-Blob download belongs to the LiveDocs prefetch gate; this
audit does not claim use of an unconfigured local SAS session.

## Completion and remaining work

Local pinned sync, operation links and OpenAPI export pass and reproduce the
merged Task 15 sources. Native CI supplies MongoDB, published Invoice/PDF,
container and scanner proof; local Docker is unavailable. This package changes
only audit/handoff documentation and backlog status, with no test, feature, API,
domain, persistence, dependency, workflow, image or limit change. Existing 1,236
local unit results for the same production/test sources are recorded in Task 15;
there is no additional local unit rerun for these Markdown changes.

The completion PR must pass fresh full CI and a complete raw/rendered artifact
comparison before review. Its exact final-head proof is recorded on the PR;
this page retains the frozen published-main evidence above. All sixteen BDD
packages and **PAY/22** are complete. **PAY/21**, hosted Stripe, the selected
LiveDocs image/ACA rollout and actual RAG retrieval remain open.
