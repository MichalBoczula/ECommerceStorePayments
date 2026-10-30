# PAY-BDD-15 — Flows, rules and RAG links

Task 15 gives source flows, policies, rejection sites and outcome families stable
semantic identities and readable meanings, then joins them to the existing BDD
HTTP and worker evidence. The [description contract](source-description-contract.md)
defines identity, source checking, evidence references and claim limits.

The source catalogue covers nine flows (seven HTTP operations and fulfillment/
replay), eight domain policies, 49 rejection rules, 68 outcome families, eleven
receipt reasons, 59 methods and 164 canonical source sites. All 391 expanded BDD
cases have checked source bindings: 319 primary HTTP cases, 51 worker/repository
action cases and 21 separately classified technical cases. Their existing case
identities, descriptions, steps and tables remain authoritative.

The authored registry is checked against actual predicates, call sites, command
wiring and receipt state/reason returns. Steps have flow-qualified IDs, canonical
source-site references, natural conditions/effects/failures and retained native
expressions. HTTP and command roots expose only reachable policies and rules.
Public errors, source guards and recorded receipt reasons remain separate.

Each case gets one grouped attachment referencing every actual HTTP and action
pair, including setup, supporting, concurrent, controlled and failed traffic.
Worker action wrappers explicitly name their source context. A setup webhook
acknowledgement cannot satisfy a missing worker `When`. Receipt facts reference
actual snapshot JSON pointers and preserve phase; matching event IDs do not claim
causality. No source branch/rule execution or implemented RAG is inferred.

No production code, endpoint/schema, domain or persistence rule, dependency,
image, workflow, exclusion, coverage/security or package limit changes. All 391
BDD cases, seventeen features, original 51 BDD/89 ordinary cases and 42/42 declared
status pairs remain protected. Task 16, hosted Stripe and the manual LiveDocs/
Terraform rollout remain separate.

## Verification in progress

The compatibility pass accepts all 391 Task 14 frozen results, 4,654 HTTP pairs,
366 action pairs and 3,244 recorded receipt snapshot facts. Historical action
source annotations were added only to the temporary compatibility input based on
reviewed existing wrappers; they are not fresh execution evidence. The PR CI must
produce the explicit source tags and grouped attachments itself.

Completion requires local source/unit gates, full applicable CI, verification of
all official artifact digests and archive inventory, every raw/rendered case and
attachment, source joins and preservation against Task 14. The backlog stays open
until that frozen evidence audit passes.
