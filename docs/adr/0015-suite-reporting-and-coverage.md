# ADR-0015: Report separate test suites and gate line coverage

Status: Accepted

Date: 2026-09-28

## Context

The baseline ran one unit suite, one integration suite and one acceptance suite with a combined, nonblocking coverage report. This obscured which layer or boundary lost tests. The current Users reference has separate 70% line coverage gates for Domain, Application and Infrastructure. Payments already exceeds these levels in unit-only measurements, including all configuration and persistence code; Orders client tests belong to the external boundary as well.

## Decision

Run five named suites via `bash scripts/ci.sh suite <name>` and the same `scripts/run_suite.py` entry point locally and in CI:

| Suite | Tests | Coverage scope | Minimum |
| --- | --- | --- | --- |
| Domain | Domain unit | `domain` | 70% lines |
| Application | Application unit and real MongoDB application integration | `application` | 70% lines |
| Infrastructure | Infrastructure unit, Orders client unit and real MongoDB repository integration | entire `infrastructure` package | 70% lines |
| ExternalProviders | Orders HTTP adapter unit | `infrastructure/clients` | report only |
| Acceptance | API unit, architecture/report gate unit, real MongoDB API integration and HTTP BDD | `api` | report only |

The Orders client tests run twice intentionally: the Infrastructure gate measures the entire package without exclusions, while ExternalProviders retains its own boundary report. Provider session and webhook work remains in the later STRIPE backlog.

Each suite clears its old result directory and writes `junit.xml`, Cobertura `coverage.xml`, HTML coverage and `summary.md` under `artifacts/verification/<suite>/`. A verifier reads both reports, requires tests and covered source lines, checks the exact coverage scope and enforces the three thresholds from raw covered/valid line counts. It fails on a missing report, failed test, empty run, wrong source or low coverage; the runner also preserves pytest's nonzero exit status. Ordinary warnings remain visible. Unit tests inject missing/failed reports and a subprocess failure to prove the gate behavior.

CI runs source/build checks first, then five independent suite jobs with `fail-fast: false`. Each uploads its own reports even if the suite fails; a final job requires all source/build and suite results to succeed. `scripts/verify.sh` runs the same stages sequentially. Docker is needed for Application, Infrastructure and Acceptance.

## Consequences

Reviewers can inspect suite-specific failures and reports. New Infrastructure code, including adapters, contributes to its 70% denominator. Tests added under new directories must be assigned to a suite; a unit test guards that every existing test file is assigned. The Acceptance and ExternalProviders percentages are reported without new thresholds while provider capabilities evolve. Matrix jobs use separate runners and may start more than one MongoDB container across jobs.

## Alternatives considered

Retaining a global total would let well-tested Domain code hide a weak Infrastructure area. Excluding configuration and MongoDB setup from the Infrastructure denominator would understate the real package. Applying a branch-inclusive total percentage instead of line coverage would differ from the Users reference and the stated 70% line target.
