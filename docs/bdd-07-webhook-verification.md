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

Implementation verification and the full CI/archive/render audit are recorded
after they pass. Fifty-five new regressions cover raw/header fidelity, per-item
redaction, publication rejection of broken inventories, SDK timestamp behavior,
complete rejected collections and exact accepted receipt/digest assertions.

Application/API/persistence code, dependencies, workflow/image pins, frozen
baseline/matrix rows, security/coverage floors, Blob publication and manual
LiveDocs/Terraform selection remain unchanged. Accepted controls cover the
verification boundary; the complete paid/failed/async/replay/receipt lifecycle
remains Task 8. Fulfillment recovery remains Task 9. Tasks 8–16 and overall PAY/22
stay open. Signed fixtures use a synthetic test secret and establish controlled
SDK/HTTP/MongoDB evidence; real hosted card/BLIK rollout remains separate.
