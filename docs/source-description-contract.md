# Payments source and evidence description contract

The four generated source files keep their existing names. `openapi.json` remains
the public wire contract; `operation-links.json` owns the semantic catalogue;
`flows.json` projects all seven HTTP and two command flows; and
`validation-policies.json` projects policies, rejection rules and receipt reasons.
They are generated together from the same source revision and are not committed.

## Identities and meanings

`scripts/source_catalog.py` authors readable method effects, failure limits,
condition meanings and semantic aliases. `scripts/source_knowledge.py` checks
those aliases against executable AST predicates, supported call sites, concrete
adapter composition and receipt return values. Unknown calls, changed predicates,
ambiguous sites, missing prose and duplicate identities fail generation. New
indirection requires a reviewed resolver change.

IDs use the `payments.` namespace: `method`, `site`, `flow`, `step`, `policy`,
`rule`, `outcome`, `command` and `receipt`. They use semantic aliases rather than
line numbers, array positions or hashes. Step IDs include their flow and call
path so shared methods retain distinct flow contexts. Sites have canonical method
owners and call targets; steps and rejection rules reference real sites. Policies
include only dependencies reachable through the supported source graph. References,
ownership, unique IDs and HTTP status families are checked before export.

Every flow/step/policy/rule has readable conditions, effects and failure limits.
Native expressions remain beside those descriptions for review. The projection
lists possible call/return/raise sites, including alternative branches, in source
evaluation order; it evaluates nested arguments before the enclosing call. It is
not a control-flow graph or an observed runtime trace. A later site may require an
earlier guard to fall through even when it has no enclosing `if` expression.
Repository/HTTP/provider boundaries remain calls, rather than expanded fictional
internal traces. Fulfillment and replay roots include their actual production
composition and explicit CLI limits/guards.

`outcomes` describe declared HTTP, routing, technical, transport and command
families. A public problem code is an observed signature, not proof of a particular
domain rejection rule. `receiptReasons` describe exact durable state/reason pairs;
HTTP 200 alone does not imply an applied event or completed fulfillment. Worker
errors remain recorded durable fields, distinct from public codes and source
predicates. An action can include several invocations or cancellation and recovery;
it does not imply a single CLI exit.

## Actual scenario joins

Each BDD case gets one `Scenario source links` JSON attachment. Its immutable
scenario identity and explicit references join the exported source catalogue to
all recorded request/outcome and action-start/result-or-failure attachment names.
Exchange/action IDs, phase, step, role, concurrent attempt, controlled-boundary
flag and actual action ownership remain intact. Canonical flow references also
list their declared steps, policies and rules. `executedStepIds` and
`executedRuleIds` stay empty.

The linker rechecks physical HTTP bytes, media, status, headers and response
schemas with the captured-contract validator. It resolves decoded ASGI paths
while retaining encoded request evidence. Wrong methods keep nominal route
context; unmatched routes keep the global routing family. Documentation routes,
external peers and transport failures retain their actual classification.
Cancellation has no response or status.

Source scenario bindings are derived from expanded Gherkin `When` steps and the
existing matrices. Worker/repository scenarios require an explicitly tagged
actual `When` action. Their selected setup webhook or supporting read stays
`setup-http` or `supporting-http`; it cannot substitute for that action. Ordinary
HTTP cases require their selected actual `When` exchange(s), exact authored
status/signature/JSON and the correct operation. Concurrent outcomes keep every
selected exchange. Technical cases retain their separately validated actual
HTTP/cancellation/action witnesses.

Receipt facts reference the observation attachment plus a JSON pointer into the
canonical recorded BSON snapshot. Authored expected tables and substitution
tokens are excluded. Each fact preserves its phase and exact recorded state,
reason and fulfillment fields. Same-event HTTP IDs are a correlation only;
existing, setup or unrelated snapshots do not establish request causality.

The collector retains serialized records across flushes and appends one grouped
observation. Link failures retain original evidence and record `valid: false`.
The Acceptance post-suite gate independently recomputes all groups and rejects
missing/duplicate/foreign attachments, unsupported source IDs, false associations,
missing primary witnesses and forged declared/executed references. It requires
all expanded cases, alongside the unchanged BDD, raw-evidence and contract gates.

These references prepare documentation for retrieval tooling. No ingestion,
retrieval, ranking, evaluation service or runtime branch instrumentation is added.
