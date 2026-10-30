# PAY-BDD-11 — Framework failures

Task 11 adds **71 scenarios** and strengthens five original framework cases,
retaining every previous BDD identity and outcome. There are **342 BDD cases**:
339 matched route cases and three deliberately unmatched routes. All **42/42
declared operation/status pairs** have scenario intent, including wrong methods
on all seven operations. The fifteen reviewed gaps are closed; the reviewed-gap
file retains its header so future unreviewed declarations still fail the guard.

## Requests and complete safe problems

Native tables author method, path/query, literal or generated body bytes,
media type, incoming trace and signing mode. Central capture retains the actual
prepared request and response, including setup and repeated requests. Hex input
preserves invalid UTF-8; repeat/padding input specifies exact byte boundaries
without committing unreadable payloads to feature files.

Every rejection starts with two populated payments, five complete history
snapshots and an existing signed webhook receipt. The main payment is Pending
at version two; an unrelated order is Succeeded. Both requests compare every
field of all three real MongoDB collections and all provider sessions, with no
new Orders or Stripe HTTP call. Native tables verify all nine problem fields:
type/title/status/detail/instance/code, generated traceId, errors and
missingProperties. Traces are distinct, match response headers and do not echo
the caller's valid-looking trace. Problem instance excludes private query values.
Allow is exact for 405 and absent on other problems; Content-Length matches the
actual response bytes.

| Cases | Actual request/response boundary |
| --- | --- |
| PAY11-23–28, strengthened PAY11-18 | Wrong methods on all seven operations, exact 405/Allow and populated-state preservation |
| PAY11-29–35 | Explicit unexpected RuntimeError boundaries on every operation, producing complete safe 500 problems |
| PAY11-36–41, strengthened PAY11-14 | Invalid UUID route values for Pay, Checkout and payment reads, including private query omission |
| PAY11-42–81, strengthened PAY11-15/16 | Pay/Checkout malformed/null/object/array/string/number/boolean bodies; invalid UTF-8; trailing/truncated JSON; missing/wrong/vendor/mixed-case media; Unicode and large exponents; exact 64 KiB and next-byte rejection |
| PAY11-82–88 | Signed empty/null/array/malformed/invalid-UTF-8 webhook bytes and missing/vendor media; exact HMAC checks preserve body-error isolation |
| PAY11-89/90, strengthened PAY11-17 | Unknown routes, extra segments and safe query-free problem instances |
| PAY11-91–93 | Accepted missing Pay body, empty Checkout before media validation, and ignored uncontracted Get body; complete responses and exact stored effects |

Malformed JSON at exactly 65,536 bytes reaches parsing and returns invalid_json;
65,537 bytes returns invalid_request before parsing. A valid padded JSON string
at 65,536 bytes still returns invalid_request because these commands take no
body contract. Missing body is valid for Pay; an empty Checkout body is valid
even with text/plain. Get has no body contract and ignores a supplied null body.
These accepted boundaries are not falsely described as missing-body failures.
Webhook payload rejection remains webhook_invalid after the actual SDK signature
boundary; it is distinct from command invalid_json/invalid_request handling.

## Explicit unexpected-failure evidence

These scenarios demonstrate the framework's safe fallback, not a claimed
natural database or provider outage. An explicit configuration action records
the installed point and RuntimeError class. Both actual requests must reach the
recorded point, and both complete collection snapshots must remain unchanged.

- Compatibility/liveness faults occur after the real HealthResponse constructor.
- Readiness faults occur after the actual MongoDB probe completes successfully.
- Payment faults occur at API delegation to pay/checkout/get_by_order_id, before
  the application operation performs work.
- Webhook failure occurs after the real SDK signature and event normalization,
  before receipt creation. A valid signed unknown event isolates this boundary.

Expected captured logs retain the two server trace IDs and controlled fixture
exception. Public problems contain no exception message or traceback. This
package does not claim runtime branch tracing, real network outages or actual
transaction rollback; Task 12 owns deterministic concurrency/atomicity.

## Evidence and guard changes

The collector marks syntactically valid JSON numbers beyond the finite Python
float range as **json-number-text**, preserving their original text/bytes while
keeping the JSON evidence envelope encodable. Non-JSON NaN/Infinity constants
remain invalid-json. Request parsing in the application is unchanged.

The 55 new evidence/source regressions challenge missing/ambiguous fixture
inputs, exact body sizes/encoding, JSON overflow classification, Allow/content
length/trace drift, method/path/query/body/media/header/signature drift and
corruption of populated current/history/receipt/session/call state. Source
checks require full tables and explicit boundaries for all seven 500 cases.
Existing gap guard tests retain their identities and now use a temporary
synthetic 418 declaration to prove reviewed-gap closure after the real inventory
has become empty. A covered original response cannot be removed from the frozen
contract either.

## Verification and scope

Locally, all **1,005 unit tests pass**. Pinned dependency sync, Ruff/format,
strict Pyright, architecture, operation links, the seven-operation/341-outcome
export and wheel build/install pass. OpenAPI, flows and validation policies
are byte-identical to Task 10. A temporary real-FastAPI/Kiota/Stripe-SDK probe
passes all 71 new HTTP modes and seven explicit failure boundaries using a
memory repository; it is not real MongoDB proof. CI results, archive identities
and the rendered report audit are recorded after verification. Docker is unavailable locally; actual database,
published Invoice/PDF, container and image evidence must come from full CI.

There are no application/API/schema/dependency/image/workflow changes or weakened
gates. The 50,000-file LiveDocs tooling remains pinned. Tasks 11–16 and overall
PAY/22 remain open until their respective verification completes. Automatic
successful-main Blob publication and selected manual LiveDocs/Terraform refresh
remain unchanged.
