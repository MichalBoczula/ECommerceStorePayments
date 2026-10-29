# Original signed webhook verification — PAY-BDD-07

Task 7 strengthens six original webhook cases and adds forty-five
`PAY07-01`–`PAY07-45` scenarios. All 99 earlier BDD identities and original matrix
rows remain. The current source has 144 BDD cases across ten features. Declared
operation/status coverage remains 27/42 with fifteen reviewed gaps for Task 11.

| Boundary | Observed checks |
| --- | --- |
| Original authentication bytes | Independent HMAC over the actual delivered bytes, actual physical signature headers, Base64/SHA-256/length, explicit signed/delivered equality and captured HTTP witness. |
| Signature form | Missing/empty headers, another secret, malformed timestamp, absent v1, incorrect digest, multiple v1 digests within one header and two distinct physical headers. |
| Timestamp | A signed timestamp exactly 300 seconds old succeeds; 301 seconds old rejects. The pinned SDK accepts a signed timestamp one hour in the future; the scenario records this current behavior explicitly. |
| JSON and UTF-8 | Post-signing JSON reencoding, malformed JSON, duplicate top-level/nested keys, invalid UTF-8, array/null/empty roots and valid multibyte Polish/emoji bytes. |
| Envelope | Live mode, connected account, organization context, wrong object kind and empty/255/256-character event identifiers. |
| Checkout snapshot | Live session, bool/float/out-of-range amounts, missing metadata, malformed/zero attempt UUID, inconsistent client reference, live session ID, missing paid intent, currency, mode and completion statuses. |
| Media and body size | Missing/plain-text/JSON-suffix media reject; case/charset normalization succeeds. Exactly 1,048,576 signed bytes succeed; 1,048,577 signed bytes reject. |
| Rejection state | Complete safe problems and identical current/history/receipt documents; no downstream call or provider-session change. Every new scenario starts with populated unrelated state and a Pending target checkout. |
| Accepted boundary controls | Exact one-field acknowledgement and complete ignored receipt, original-byte digest, bounded UTC times and unchanged payment/history/unrelated receipts. The original paid control also verifies its received-byte digest. |

## Wire capture and executable tables

Each new request has authored event/payload/mutation/signature/time/media/size
inputs. Mutations carry explicit JSON types or a physical omission marker. Every
case has a native expected HTTP table and native signature-count/HMAC-count/byte-
length/equality/timestamp expectations. Rejected cases have explicit state
expectations; accepted boundary controls list every normalized receipt field.

The shared collector now includes an ordered `headerItems` list alongside its
header mapping. Public API capture takes those items from the actual prepared
request and actual response, retaining repeated physical header fields. Each
sensitive header item remains redacted. The publication guard requires a valid,
redacted inventory matching the mapping; dropped/coalesced/corrupt items fail.
Request/outcome identity and index checks remain intact. This additive JSON
attachment evidence preserves the Allure/bundle publication contract.

Two physical Stripe-Signature headers are rejected even when both mathematically
match. One physical header with two v1 digests is accepted when one matches. The
independent HMAC count describes cryptographic matching of bytes, not successful
UTF-8/JSON parsing, timestamp acceptance, endpoint availability or route policy.
Reencoded JSON can have an identical parsed value and still fail authentication.
Duplicate JSON keys and invalid text stay visible in raw byte evidence even when
an attachment's convenient parsed view cannot represent them.

Only the SDK module's timestamp comparison sees the fixed test clock. The real
Stripe signature implementation runs; process/domain/HTTP clocks remain real.
The SDK checks old timestamp age and accepts future signatures. These tests do
not claim a symmetric clock-skew policy or change that existing behavior.

At the size limit, valid JSON is padded with signed trailing whitespace. The
accepted receipt's digest covers all original bytes, including padding and UTF-8.
The oversized original case also uses a valid JSON body and matching signature,
so the size failure is isolated. Tests here exercise received-byte size limits;
stream cancellation and other technical scenarios remain separate packages.

## Verification and remaining work

All **754 local unit tests** pass, including 55 new assertion/source regressions.
Pinned lock/sync, formatting/Ruff/strict Pyright, architecture, exact links/OpenAPI
export, wheel build/install, changed Markdown links and git checks pass. Ordinary
warnings remain visible. Docker is unavailable locally; CI supplies real database,
Invoice, container and image evidence.

[Implementation CI 40959711148](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/40959711148)
passes all source/contract/wheel/security checks, all five suites, documentation
packaging, quality gate, real Mongo-backed container smoke, Trivy and final gate.
Frozen implementation head: `46b333835bda4341c257334c01b6040a01593dbd`;
tested merge: `7470773752808486bbf9dcef029f3168b8e06965`;
exact tree: `d254a5e036672c05ee584b4e58fd8c985f311722`.
Exact parents/tree were checked against Task 6's merged base and this head.

- **1,108 passing suite executions, zero failures/skips:** Domain 97, Application
  82, Infrastructure 250, ExternalProviders 175, Acceptance 504. There are **933
  distinct members**, retaining the intentional 175-member provider-suite overlap.
  Acceptance is **144 BDD + 360 ordinary**. Every Task 6 member survives, with
  forty-five BDD and 55 ordinary regressions added.
- Coverage remains 96.88% / 96.16% / 90.90% for Domain/Application/Infrastructure
  and 96.35% / 98.06% for ExternalProviders/Acceptance. The separate 70% floors,
  generated client exclusions and security gates remain unchanged.
- All seven official outer artifact digests match. The frozen inner bundle is
  **5,339,476 bytes**, SHA-256
  `d6c991911ab72a9d124bd8df0365a424cb38f8a887cc694a57bf940ae55d2eee`, with **4,595 verified
  manifest entries**: 144 results, 10 features, 4 exports and **4,437 attachments**
  (3,755 JSON, 679 native CSV tables and 3 retained expected-fault logs).
- Pinned Allure 2.46.1 renders every case, authored description, ordered/nested
  step and attachment matching raw bytes. All case/attachment/entry assets pass
  local HTTP reads. Every prior name/full name/history/test identity/title path
  survives. OpenAPI/flows/validation-policy bytes match Task 6; operation-links
  adds only forty-five scenarios and current counts, preserving the fifteen gaps.
- Independent raw HTTP/HMAC/BSON checks verify every header inventory/redaction,
  **51 signed-wire witnesses, 43 complete unchanged safe rejections, seven complete
  accepted-boundary receipts and the paid received-byte digest**. Exact timestamp,
  physical-header/rotation, typed mutation, JSON/UTF-8, media, 1 MiB and identifier
  boundaries pass. Earlier Pay/read/retry/history/checkout/recovery audits also pass.
- Captures contain **1,274 HTTP request/outcome pairs**: 1,263 responses and 11
  intentional transport failures, plus **57 explicit action start/result pairs**.
  Every BDD case passed. The three captured logs belong to earlier expected
  persistence-fault scenarios; no new unexpected failure or skipped case is hidden.

Task 7 is complete. A final documentation-only completion head is checked again
in full CI and with fresh archive/render audits before PR handoff.

Application/API/persistence code, dependencies, workflow/image pins, frozen
baseline/matrix rows, security/coverage floors, Blob publication and manual
LiveDocs/Terraform selection remain unchanged. Accepted controls cover the
verification boundary; the complete paid/failed/async/replay/receipt lifecycle
remains Task 8. Fulfillment recovery remains Task 9. Tasks 8–16 and overall PAY/22
stay open. Signed fixtures use a synthetic test secret and establish controlled
SDK/HTTP/MongoDB evidence; real hosted card/BLIK rollout remains separate.
