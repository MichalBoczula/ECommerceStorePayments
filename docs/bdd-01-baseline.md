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
