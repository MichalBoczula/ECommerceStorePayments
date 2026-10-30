# PAY-BDD-10 — Business validation

Task 10 adds **56 HTTP scenarios** and strengthens three original rejection
cases without replacing any of the **215 previous BDD identities**. There are
**271 current BDD cases**. All new cases populate unrelated current, history and
webhook-receipt collections first. Rejections compare every document after both
requests, return complete safe problems with distinct matching trace IDs, and
make no Stripe call or provider-session change.

## Where values enter

Pay and Checkout have an order UUID path argument and no JSON money body. New
native tables author the exact controlled **Orders response**, not fictional
caller-supplied Payment fields. The actual FastAPI routes, precise JSON factory,
generated Kiota client, HTTP adapter, application/domain rules and real MongoDB
repositories execute. Central capture retains empty command bodies, each actual
Orders request/response and all supporting reads and repeats.

`TotalAmountToken` is a literal JSON token. `LineAmountTokens` is a JSON array of
strings containing literal tokens; the fixture writes their exact contents as
JSON numbers rather than converting through a binary float. `CurrencyToken`,
`LineCurrencyToken`, `StatusToken` and `OrderIdToken` similarly preserve exact
typed values. `<absent>` physically omits a field. Invalid NaN/Infinity constants
are recorded as invalid JSON text with exact bytes, never serialized as invalid
numeric literals in the evidence envelope.

| Cases | Executed boundary |
| --- | --- |
| PAY10-01–15 | All twelve accepted Orders currencies; smallest units; exact multi-line sum; trailing zeros; scientific notation; a number beyond binary-float integer precision; the signed BSON int64 upper boundary; case-insensitive Created status |
| PAY10-16–20 | Nonpositive money and fractions below the minor unit for exponents two, zero and three |
| PAY10-21–31, 37–41 | Unknown, lower/padded/non-ASCII/short/long/empty currencies; string/null/boolean totals; missing fields and non-string currencies |
| PAY10-32–36, 42–45 | Nonfinite numeric constants, bounded exponent, inconsistent exact line sum, empty lines, inconsistent product currency, blank status and a response for another order |
| PAY10-46–48 | Paid/Canceled order rejection and the reachable zero-UUID domain rejection through Pay |
| PAY10-49–56 | Invalid Orders money at Checkout; valid EUR/JPY rejected by the provider policy; exact inclusive PLN 200 and 99,999,999 minor-unit boundaries and their immediate rejected neighbors |

Zero/negative/fractional amounts use matching line totals so a contradictory sum
does not mask the conversion rule. Wrong scalar types retain otherwise valid
lines; a bad line sum or product currency changes that individual consistency
condition. Unknown order status is a different application rule from missing or
blank status. Invalid Orders money returns `502/order_invalid_response`;
unsupported checkout money returns `409/checkout_money_unsupported`; an order
that cannot be paid returns `409/order_not_payable`; the zero UUID reaches
`400/validation_failed`. Every problem includes exact type/title/status/detail/
instance/code, empty errors/missingProperties, and a fresh 32-hex trace matched
to the response header.

All seventeen accepted cases assert every Payment or nested Checkout response
field and exact durable effects. Two checkout cases also assert the full encoded
provider request, idempotency identity, card/BLIK methods and complete history.
Later Get/Pay reads preserve the complete populated collections and make no new
dependency calls. Timestamp comparisons explicitly project create-time
microseconds to MongoDB milliseconds; stored reads compare exact UTC values.

## Standalone rules are not HTTP inputs

The new ordinary tests retain their actual suite classification; they are not
operation-linked Gherkin cases or fabricated request/response exchanges.

| Test source | Actual evidence |
| --- | --- |
| `tests/unit/domain/test_business_validation.py` | 37 typed rule cases: Money amount/currency signatures; syntactic currency normalization including ZZZ; invalid provider IDs and checkout versions leave every aggregate slot unchanged; creation/rehydration both reject invalid order IDs |
| `tests/unit/infrastructure/test_currency_units.py` | 24 converter cases: exact values under small ambient Decimal precision, unchanged caller precision, nonfinite/unknown/fractional values and the adjusted-exponent boundary |
| `tests/unit/api/test_business_validation_evidence.py` | 36 evidence/source checks: altered problem fields, missing/extra fields, trace/media/status drift, raw numeric tokens, malformed fixture tables, strict non-JSON constants and corruption of populated collections/dependency/session state |

Domain Money accepts and normalizes any three ASCII letters; Orders conversion
uses its explicit twelve-code allowlist; checkout additionally requires PLN and
its amount limits. Provider IDs, internal versions and payment IDs are not
arbitrary caller-set Pay/Checkout inputs. The pure converter can accept `1e28`
major units even when the result exceeds BSON int64; that ordinary check does
not claim the value can be stored through the public HTTP route.

## Verification and scope

All **950 local unit tests** pass, including 97 new cases (37 domain, 24
infrastructure and 36 evidence/source checks). Ruff/format, strict Pyright,
architecture, source links, the 7-operation/272-outcome export, pinned lock/sync,
wheel build/install, Markdown links and git checks pass. OpenAPI, flows and
validation policies are byte-identical to Task 9; operation links add only 56
cases and current counts. A temporary actual-FastAPI/Kiota/application/provider
probe verifies all 56 authored outcomes using a memory repository. It does not
substitute for real MongoDB evidence. Ordinary warnings remain visible.

[Implementation CI 40978654005](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/40978654005)
passes source/contract/wheel/security checks, all five suites, documentation and
quality gates, the real Mongo-backed container smoke, Trivy and final gate.
Frozen head: `e0865482219afb5186f911ab5d0e198c01b42782`;
tested merge: `d56ec76bcebaab10625d7c4a9273f384284ca26d`;
exact tree: `629ca4cfbca7dff1f723ece22a2924dbfdf295dc`.
Merge parents/tree exactly match the merged Task 9 base and this source head.

- **1,431 passing executions, zero failures/skips:** Domain 134, Application 82,
  Infrastructure 274, ExternalProviders 175, Acceptance 766 (**271 BDD + 495
  ordinary**). All Task 9 members survive, adding 56 BDD and 97 ordinary checks.
  There are **1,256 distinct members**, retaining the intentional 175-member
  provider-suite overlap.
- Domain/Application/Infrastructure coverage is 96.88% / 96.16% / 91.03%,
  with separate unchanged 70% floors. Provider/Acceptance report 96.35% / 98.06%.
  Generated-client exclusions and dependency/security gates remain enforced.
- All seven official outer artifact digests and closed inventory/path/size/hash/
  source/export/JUnit checks pass. Frozen inner bundle: **13,259,318 bytes**,
  SHA-256 `0b33e35ec7dd1d613b4601d3bc2f05ef7db1e97d19f4b91ec4df418266c4d9df`,
  **11,049 manifest entries** and **10,760 attachments**
  (9,011 JSON, 1,742 native CSV tables, four retained
  actual Invoice PDFs and three retained expected-fault logs).
- Allure 2.46.1 renders every case, authored description, ordered nested step and
  attachment matching raw bytes. Every case/attachment/entry asset passes local
  HTTP reads. All previous full names/history/test IDs/title paths survive.
- Independent raw HTTP/BSON joins verify **56 exact Orders contracts**, **42
  repeated full safe rejections** (39 new and three originals), **15 exact Pay
  insertions**, **two full checkout/provider/archive boundaries**, **17 no-op
  read/repeat sets**, twelve currencies, exact typed/nonfinite/precision/status/
  UUID inputs and complete populated-state/session preservation.
- Earlier Task 3–9 audits all pass, including four actual Invoice PDF/stored-byte
  checks and text extraction for invoice IDs, client/product and PLN amounts.
  Three retained expected-fault logs match exact exceptions and API trace IDs
  without fixture-key/auth leaks. Captures have **3,047 HTTP pairs**
  (3,034 responses and thirteen intentional transport failures), plus
  **219 explicit action start/result pairs**.

Task 10 is complete. The documentation-only completion head receives full CI and
fresh archive/render/PDF audits and a frozen/final comparison before PR handoff.

There are no Payments application/API/persistence/package-dependency or image
changes. The required [LiveDocs capacity dependency](https://github.com/MichalBoczula/ECommerceStore.LiveDocs/pull/13)
raises the shared bounded inventory ceiling from 10,000 to 50,000 source files
plus one manifest, retaining compressed/unpacked byte limits and all integrity
checks. The first CI passed all 1,431 tests, but its complete 11,049-file inventory
exceeded the former ceiling. Payments pins reusable workflow and tooling commit
`93ce670ba4bcd56ed4c0ca0ec75bf82ffaef7098`; merge the LiveDocs dependency first
and include it in build/import tooling before selecting the larger archive.
No cases or attachments are removed to fit the old ceiling. Quality/security
thresholds remain unchanged. Coverage intent remains 27/42 status pairs with
fifteen reviewed gaps.
Task 11 owns remaining framework failures, and Task 12 owns deterministic
concurrency/rollback. Tasks 11–16 and overall PAY/22 remain open until their
respective verification completes. Automatic successful-main Blob publication
and selected manual LiveDocs/Terraform refresh remain unchanged.
