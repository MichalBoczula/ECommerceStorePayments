# PAY-BDD-14 — Request and response contracts

Task 14 keeps all 391 BDD cases, seventeen features, seven named operations and
42/42 declared status pairs. It enriches the generated OpenAPI and checks every
captured exchange, including Given/setup, concurrent, primary and supporting
traffic. It does not change domain rules, request binding, persistence, provider
dependencies, image inputs, workflows or coverage/security/package limits.

## One generated contract

Response models author field descriptions and typed examples, complete nested
examples and explicit serialized member presence. Nullable provider/timestamp/URL
members remain required response members. Payment status values come from the
domain enum; money/currency/provider constraints document existing domain output.
UUID/date-time/URI formats remain visible. Serialized acknowledgements require
`received`, while its existing Python default remains unchanged. Complete safe
problems include the defaulted `type`, aliases, typed arrays and trace format.

FastAPI drops null-valued object members while serializing example metadata.
The OpenAPI wrapper restores examples from the same response models so complete
examples retain their required nulls. Unreferenced automatic 422 validation models
are removed after the existing 422 response removal. No generated schema is
committed or maintained as another source of truth.

Path UUIDs and signature headers have descriptions/examples. Pay and Checkout
continue to advertise no request body. All named responses document actual trace
and content-length headers; 405 responses also document the matched route's Allow
header. Source-derived shape checks reject lost types, required members,
nullability, enum values and formats, and every authored example validates against
the same generated schema.

The webhook request metadata describes the four supported checkout snapshot
types, paid/unpaid completion and the ignored-event envelope. It records test
mode/account/context restrictions, session/money/metadata fields, original signed
bytes, one signature header, size and freshness rules. Extra provider fields stay
allowed. The route still receives `Request` and verifies the original bytes before
parsing; these documentation schemas add no request-binding layer. Cross-field
UUID/state associations, duplicate-key and cryptographic verification remain the
existing verifier's responsibilities. Example signatures are illustrative.

## Actual captured evidence

The shared recorder freezes each request with its exchange identity and attaches
one contract observation to every completed response or transport failure. A
contract mismatch retains the real HTTP response and records `valid: false`;
it never becomes a fabricated transport failure. The Acceptance post-suite gate
recomputes every observation from actual paired bytes, headers and the current
generated OpenAPI. Missing, duplicate, foreign or forged observations fail it.

- Payments responses validate the complete declared schema, actual status/media,
  byte length, fresh trace and declared headers. Problems additionally match the
  wire status, title, request path and trace header. Successful route UUIDs,
  bodyless commands and accepted signed webhook shapes are checked.
  Encoded wire paths remain intact; operation matching and problem instances use
  the decoded ASGI path, including Unicode and encoded path separators.
- Wrong-method exchanges retain their matched operation and actual 405/Allow.
  Unmatched routes retain a global 404 problem. Documentation HTML keeps its real
  media/bytes; served OpenAPI must equal the current generated document.
- External Orders/Invoice/Stripe calls remain explicitly external and are not
  validated against Payments schemas. Transport failures/cancellations retain
  their actual exception and no invented response/status. Worker actions stay
  separate from HTTP exchanges.

This validates recorded contracts and protocol correlations. It does not prove
every internal branch, implement RAG, contact live Stripe or deploy LiveDocs.
Task 15 owns flow/rule identities and joins; Task 16 owns the final frozen audit
and manual LiveDocs refresh handoff.

## Verification

[Implementation CI 41039859462](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/41039859462)
passes all source, suite, security, packaging, real Mongo-backed container smoke,
image scan and final gates. Frozen head: `d98df8925fc1df3522a0668b1ed4c8cd5fb11da4`;
tested merge: `a8b3fb7d970ab5a5186dbbbe1545dba42147224e`;
exact tree: `db3303c02821b034117845ecc80143fb9b9fe398`.

- **1,793 passing suite executions, zero failures/skips:** Domain 134,
  Application 82, Infrastructure 274, ExternalProviders 175 and Acceptance 1,128
  (**391 BDD + 737 ordinary**). There are 1,618 distinct members with the
  unchanged intentional 175-member provider overlap. Seventy-six new ordinary
  contract regressions are added; all previous test sources/BDD features remain.
- Domain/Application/Infrastructure line coverage remains 96.88% / 96.16% /
  91.03%, each with the unchanged 70% floor. Provider/Acceptance coverage is
  96.35% / 98.90%. No dependency, image, workflow, exclusion or limit changes.
- **1,192 local unit tests pass** on the final implementation. Pinned sync,
  format/lint, strict Pyright, architecture, operation links, OpenAPI and wheel
  build/install checks pass. Local Docker is unavailable; actual Mongo/Invoice
  and container evidence comes from CI. API handler bodies remain unchanged;
  flow/policy exports byte-match Task 13. Ordinary warnings stay visible.
- Eight downloaded official artifact digests match GitHub metadata. The complete
  inner archive has **21,263 inventory entries**, **24,279,435 bytes** and SHA-256
  `f0b1f92f9d913ef3d696d4b2cc3bbebcc3da9b71fe029cea89c3ca22a0596517`.
  Every path, size, hash and attachment reference resolves with closed inventory.
  All seventeen features match source and all four exports match the separate
  generated-contract artifact. Source/run/time and all suite JUnit counts match.
- **4,654 actual exchanges** have independently recomputed contract observations:
  2,045 completed Payments responses, 2,608 external-boundary exchanges and one
  Payments cancellation. The total retains 4,638 completed responses and sixteen
  intentional transport failures. Payments request phases are 1,266 Given,
  384 When and 396 Then, including the cancelled request. All applicable complete
  JSON responses pass an additional JSON Schema 2020-12/format/protocol audit.
  Independently recomputed HMACs match the original bytes of all 508 accepted
  webhook deliveries; this is not a new live-provider or freshness claim.
- All 391 previous Allure identities, names, descriptions, outcomes, history/test
  IDs and ordered nested steps survive. Allure **2.46.1** official distribution
  digest is verified. Every rendered case and all **20,851 attachments** match
  raw bytes: 18,301 JSON, 2,533 native CSV tables, thirteen expected-fault logs
  and four Invoice PDFs. All **21,276 generated report resources** pass actual
  local HTTP reads; JSON resources parse. This is report-data/asset verification,
  not a pixel-by-pixel browser or deployed Azure inspection.

Task 14 implementation and its frozen evidence audit are complete. The completion
update changes only Markdown; full CI and fresh evidence comparison are required
before PR handoff. Preserve all JUnit/BDD identities, seventeen features, four
exports, contract classifications and per-case attachment counts in that check.
PR image publication/Blob archival skip as designed. Tasks 15–16, overall PAY/22,
hosted Stripe and the manual LiveDocs/Terraform rollout remain open.
