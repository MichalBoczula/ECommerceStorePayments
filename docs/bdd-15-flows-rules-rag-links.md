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

## Verification

[Implementation CI 41049724083](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/41049724083)
passes every applicable source, suite, dependency/security, packaging, real Mongo/
Invoice, container smoke, image scan and final gate. Frozen head:
`811e45e51bfb8cf35702dbbca571cc2646f6efaa`; tested merge:
`2b7e22825abb1d0894e7340d6df9cfd805583a8e`; exact tree:
`34a381d5d16186e833c06ea3a5617c3bc320a191`.

- **1,837 passing suite executions, zero failures/skips:** Domain 134,
  Application 82, Infrastructure 274, ExternalProviders 175 and Acceptance 1,172
  (**391 BDD + 781 ordinary**). All previous JUnit identities remain; the increase
  is 44 source/evidence regressions. There are 1,662 distinct members with the
  unchanged intentional 175-member provider overlap.
- **1,236 local unit tests pass.** Pinned sync, format/lint, strict Pyright,
  architecture, operation links, OpenAPI and wheel build/install checks pass.
  Source features, matrices, production code, dependencies, image/workflow inputs,
  exclusions and all quality/security/package limits remain unchanged. Wire
  OpenAPI equals Task 14. Local Docker is unavailable; native proof comes from CI.
- Domain/Application/Infrastructure line coverage remains **96.88% / 96.16% /
  91.03%**, each with the unchanged 70% floor. Provider/Acceptance coverage remains
  96.35% / 98.90%. Ordinary warnings stay visible.
- All **nine downloaded official artifact digests** match GitHub metadata. The
  frozen inner archive has **21,654 closed inventory entries**, **26,033,027 bytes**
  and SHA-256
  `7490ab22c0cedb64c247ff94428a128922f61c2cf7b051f186ed52536809eea9`.
  Every path, size, hash and attachment resolves. All seventeen features match
  source and all four exports match the separate generated-contract artifact.
  Every one of the 21,633 Allure result/attachment files byte-matches the separate
  raw Acceptance artifact. Source/run/time and all suite counts match.
- Every source/evidence group independently recomputes: **391 cases, 4,654 actual
  exchanges, 366 paired actions and 3,244 recorded receipt facts**. A separate
  reference audit checks all physical attachment/JSON-pointer targets, identities,
  phases, ownership, declared source references and empty executed-step/rule lists.
  All **68 declared outcome families** and **eleven receipt reason meanings** have
  actual linked observations; this does not claim execution of the 49 source rules.
- Primary witnesses retain **342 HTTP, 87 action, 49 setup HTTP and two supporting
  HTTP references**. Setup/supporting responses cannot replace required worker or
  repository When actions. Actual Payments request phases remain 1,266 Given,
  384 When and 396 Then, including one cancellation with no invented status.
- All **4,654 captured contract observations** recompute. There are 2,045 completed
  Payments responses, 2,608 external exchanges and one Payments cancellation;
  overall, 4,638 responses and sixteen intentional transport failures remain.
  Applicable complete responses pass an additional JSON Schema/format/protocol
  audit. HMACs independently match the original bytes of all **508 accepted
  webhook deliveries**, without claiming fresh timestamps or live Stripe execution.
- All previous **391 Allure identities, descriptions, outcomes, history/test IDs,
  ordered nested steps and attachment-name/type counts** survive, with exactly
  one additional source-link JSON attachment per case. Pinned official Allure
  **2.46.1** renders all **21,242 attachments** with exact raw bytes: 18,692 JSON,
  2,533 native CSV tables, thirteen expected-fault logs and four Invoice PDFs.
  All **21,667 report resources** pass actual local HTTP reads; JSON parses.
  This is report-data/asset verification, not pixel-by-pixel browser or deployed
  Azure inspection.

The historical compatibility pass also accepted all Task 14 results. Temporary
historical action annotations were compatibility input only; the frozen fresh CI
above captures its own explicit tags and groups.

Task 15 implementation and its frozen evidence audit are complete. The completion
update changes three Markdown files only; full CI and a fresh raw/rendered evidence
comparison are required before PR handoff. Preserve all suite/BDD identities,
per-case attachment/link counts and four exports in that check. PR image/Blob
publication skips remain intentional. Task 16, overall PAY/22, hosted Stripe and
the manual LiveDocs/Terraform rollout remain open.
