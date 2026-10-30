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

Implementation validation is in progress. The Task 14 backlog remains open until
full applicable CI and the raw/rendered evidence checks pass. Local Docker is
unavailable; native Mongo/Invoice/container verification must come from CI.
