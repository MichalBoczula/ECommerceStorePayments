# PAY-BDD-01 — Baseline and coverage guard

## Frozen inventory

The baseline is the audited main source
`ab868c98940741ef6422dfafcab71134f3e4b8e3`, successful
[CI 40219243830](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/40219243830).
The source bundle has SHA-256
`bd1b5998877dd95b6a2c0e8cad56faadf64910b15855eccde32e31bb3c38bc1c`,
105,830 bytes and sixty verified manifest entries. Its feature sources and all
five JUnit inventories were independently downloaded and checked before freezing.

| Baseline | Cases |
| --- | ---: |
| Feature files / scenario declarations / expanded BDD cases | 5 / 51 / 51 |
| Ordinary Acceptance cases, outside Allure BDD | 89 |
| Acceptance suite total | 140 |
| Domain / Application / Infrastructure / ExternalProviders | 97 / 82 / 250 / 175 |

`bdd-baseline.json` freezes each original feature/rendered scenario identity,
behavioral Example values and complete cause/status/code/requirement matrix row.
It also freezes original operation method/path/status declarations and actual
executed JUnit member identities for all five suites. New cases, metadata and
Gherkin tables are additive; changing/removing an original identity, example or
outcome requires an explicit reviewed migration, not baseline regeneration to
make a removed test pass. There is no automatic regeneration command in CI.

Two external-provider parameter names previously embedded a random UUID. They
now have explicit pytest IDs `wrong-order` and `wrong-client-reference`, retaining
the same values, assertions and case counts. The two reviewed naming migrations
are recorded in the frozen baseline. Other member identities remain unchanged.
External-provider tests intentionally run both independently and within the full
Infrastructure scope; summed suite executions are not a distinct-test count.

## Source and operation coverage

The existing link/OpenAPI stages invoke the guard. Source parsing uses the same
locked pytest-bdd/Gherkin parser as execution, expands Examples, includes Rule and
Background steps, checks one matching result ID per expanded case, and rejects
duplicate IDs/titles, empty Examples and disabled source tags. It does not use a
regular expression to guess scenario boundaries inside tables or DocStrings.

The current projection has **seven operations, 51 cases and 42 declared
operation/status pairs**. **26** pairs have guaranteed matrix/scenario intent;
exactly **sixteen** reviewed gaps are in `acceptance-gaps.tsv`, assigned to
PAY-BDD-11. New uncovered pairs, duplicate/invalid gaps, unknown follow-up tasks
and stale resolved gaps fail. A scenario cannot claim an undeclared status, and
removing an original declaration cannot hide its gap. Existing operation, service,
policy, route, requirement and generated-schema checks stay active.

| Operation | Missing status cases |
| --- | --- |
| get_health | 405, 500 |
| get_liveness | 500 |
| get_readiness | 405, 500 |
| createOrderCheckout | 400, 405, 415, 500 |
| payOrder | 405, 500 |
| getPaymentByOrderId | 400, 405, 500 |
| receiveStripeWebhook | 405, 500 |

The 26 covered pairs include one explicitly counted wrong-method 405 against the
known liveness path. This is framework evidence, not execution of its GET handler.
The unmatched-route 404 is separate and cannot close any named-operation gap.
Status multiplicity in original concurrent matrix rows remains frozen.

Coverage is declared scenario intent, not attached exchange evidence or proof of
all internal branches and every failure cause. The frozen matrix retains each
existing cause and signature. Additional distinct causes under already covered
statuses belong to the functional packages, and execution/evidence joins belong
to PAY-BDD-02/15. No missing HTTP case is fabricated from a standalone rule test.

## Executed suite and generated-file guard

`run_suite.py` passes the frozen inventory to the existing JUnit verifier. Each
required suite must execute every original member successfully; replacing one
with a different test at the same total fails. Skipped cases fail, and JUnit
case elements must agree with success counters. Missing identities, duplicates
or hidden failure/skip elements cannot satisfy the baseline. Additional tests
are allowed and the runner still preserves pytest's nonzero exit status.

Acceptance also compares every current expanded source case with the real Allure
result inventory: exactly one passed result with the matching identity/title is
required. An added matrix/source case whose feature is never bound to pytest
cannot inflate coverage. Missing, duplicate, renamed and unsuccessful results fail.

The link stage rejects tracked verification/build output, virtual environments
and bytecode and requires committed dependency inputs. Feature sources remain
authoritative. The intentionally committed generated Kiota client is allowed and
continues to be checked by its existing regeneration/hash stage. No generated
OpenAPI, Allure results, HTML reports or verification output is committed.

Python 3.14.7, uv 0.12.18, the Invoice OpenAPI/client/image inputs and Docker/action
version pins remain unchanged. Locked installation and the
existing separate 70% Domain/Application/Infrastructure line floors, dependency
audit, secret scan, image scan and publication gates remain in force.

The first full [PR run 40920673215](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/40920673215)
identified two current dependency advisories and a MongoDB startup failure before
any integration work on the Ubuntu 24.04 runner. The required audit remains active:
only PyMongo 4.18.2 → 4.18.3 and dnspython 2.8.0 → 2.9.0 are updated in `uv.lock`,
using the published fixes for
[GHSA-98qm-wvgf-w4cf](https://github.com/advisories/GHSA-98qm-wvgf-w4cf) and
[GHSA-45c3-73f7-pv4m](https://github.com/advisories/GHSA-45c3-73f7-pv4m).
The local locked audit then reports no known vulnerabilities/adverse statuses.

The three MongoDB suite jobs and Mongo-backed container smoke use Ubuntu 22.04,
as already validated by Users and Orders/Invoices. Other jobs retain Ubuntu 24.04.
The shared CI entry point records the actual Docker kernel, pulls the same
`mongo:8.0` image and checks mongosh before starting tests. This addresses the
observed runner/startup incompatibility without skipping tests, substituting a
fake database or changing application storage behavior. Actual CI must verify it;
the earlier empty container error does not establish a more specific root cause.

The repaired [run 40922412829](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/40922412829)
passed all five suites, source/security checks, packaging and actual container
smoke. Trivy then reported fixable HIGH findings in the existing Debian `libssl3`
and `openssl` packages (CVE-2026-84782). The runtime's existing targeted apt upgrade
also upgrades these two installed packages; the Python base tag and scanner's
severity/fix policy stay unchanged. A later full successful image scan is required.

## Verification and scope

Focused regressions mutate original source/matrix pairs, titles and Examples,
unreviewed/stale/duplicate gaps, wrong-method outcomes, runtime identities and
JUnit counters, and tracked generated output. They also prove additive cases and
tables can pass without rewriting the baseline. All original business services,
API schemas, five feature files and persistence behavior are unchanged.

Full actual CI and fresh artifact/JUnit/source-report audits are required before
the PR is ready for review. Runtime verification uses CI for Docker/MongoDB and
the real Invoice/PDF image checks. Local pinned installation, source checks and
focused unit verification are available; Docker is unavailable locally.

This package does not add tables, JSON/HTTP attachments, descriptions or exchange
IDs to the existing 51 Allure cases. Those known gaps remain PAY-BDD-02, followed
by complete domain/state/contract packages. Selected LiveDocs refresh and Azure
deployment remain manual; no production rollout is claimed.

## Verified implementation evidence

Implementation head `d86f23ef16f868bc21e3f50ca8dd616bfa1779ea` passes full
[CI 40923486875](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/40923486875).
The tested merge `595398c68f300b1c1b62793887f2ad3914e30cae` has the audited main
and that head as parents and matches implementation tree
`4a1c781ff8ce81806c72727341da5bd7de36cb4b` exactly. Quality, audited locked
dependencies, PR Dependency Review, secret scan, all five suites, package/quality
gates, real Mongo-backed container smoke, unchanged Trivy policy and final gate
pass. PR publication and Blob archival are correctly skipped.

| Suite | Passed; zero failures/skips | Line coverage |
| --- | ---: | ---: |
| Domain | 97 | 96.88% |
| Application | 82 | 96.16% |
| Infrastructure | 250 | 90.90% |
| External providers | 175 | 96.35% |
| Acceptance | 175 | 98.06% |

Acceptance is **51 original BDD cases + 124 ordinary cases**. All original 89
ordinary cases survive; exactly 35 guard regressions are added. All 569 distinct
original members remain, with only the two documented parameter-ID migrations.
Current suites execute 779 cases, representing 604 distinct members because the
same 175 external-provider cases run twice intentionally. Coverage floors remain
separate and unchanged; no handwritten Infrastructure code is excluded.

Independent downloads match every official Actions artifact digest. The inner
ZIP is **106,136 bytes**, SHA-256
`96e19f25f0a3880f07dbe08fd66873047489fc2cdb083cc5aaf3f043d92ce025`;
all sixty manifest paths, lengths and hashes match, with closed inventory and
safe paths. Source/run provenance matches the tested merge/run above. Every
feature byte matches reviewed and original source. OpenAPI, flow and policy
exports remain byte-identical to the original main archive; all original
operation-link fields remain identical, with only coverage added.

Pinned Allure **2.46.1** independently renders all 51 cases. Every original title,
full name, history/test identity, title path, feature label, ordered/nested step
and outcome survives. Each generated case and report entry asset resolves through
local HTTP. There are still no JSON/HTTP/table attachments, exactly as reported
in the audit; this is not falsely claimed as completed PAY-BDD-02 work.

Locally, pinned installation and lock checks, all 518 unit cases, the official
Domain/ExternalProviders runners, full collection retention, format, Ruff, strict
Pyright, architecture, exact CI link/OpenAPI commands, wheel build/install and
Markdown/git checks pass. The locked audit reports no known vulnerabilities or
adverse statuses. Actual MongoDB/Invoice/PDF/container/image evidence comes from
CI; Docker is unavailable locally. Mongo-backed CI records kernel
`6.8.0-1070-azure` on the compatible runner.

This completion record freezes the verified implementation. The final
documentation-only head must independently pass full CI and fresh artifact
checks before review; its exact verification is recorded on the PR. PAY/22 and
PAY-BDD-02–16 stay open. No deployment, selected LiveDocs refresh, real-account
Stripe verification or runtime branch telemetry is claimed.
