# ADR-0002: Pin Python and uv and share baseline CI stages

- Status: Accepted
- Date: 2026-09-27

## Context

The repository has a committed uv.lock and quality tools, but no CI workflow or shared local verification. Unchecked dependency resolution, differing Python patches and tool versions could produce different results for a developer and a clean runner.

## Decision

Use `.python-version` for an exact Python 3.14 patch, with `requires-python` retaining the supported 3.14 minor line. Enforce one uv version through `[tool.uv].required-version` and the matching GitHub Actions setup input. Pin the Hatchling build backend version. Dependency changes require updating and committing `uv.lock`; routine verification checks the lock and installs with `uv sync --locked --all-groups`.

`scripts/ci.sh` exposes sync, format, lint, types, test and build stages; `scripts/verify.sh` runs them locally in that order. The GitHub Actions PR/push workflow calls the same stages on a clean Ubuntu runner. The build stage creates a wheel and checks its installation and a domain import in an isolated temporary environment outside the source tree. Regular warnings stay visible.

## Consequences

Changes to dependency metadata without a matching lockfile fail at sync. Each tool or Python upgrade changes an explicit pin and needs local and CI verification. A wheel that builds but is missing its package fails the isolated import check.

This baseline runs the existing unit tests and their coverage report without a minimum threshold. Separate suite coverage gates, MongoDB Testcontainers integration, security scans and Docker image checks are later PAY/4, PAY/15–PAY/17 work. A successful baseline workflow does not imply those checks were executed.

## Alternatives considered

- Install the latest uv and Python patch in every run: permits tool and interpreter changes without a repository change.
- Depend on GitHub Actions shell commands alone: lets local and CI verification drift.

## Later evolution

This ADR describes the initial baseline. [ADR-0015](0015-suite-reporting-and-coverage.md) introduced the five suite coverage policies, [ADR-0018](0018-security-and-image-gate.md) added security checks and [ADR-0019](0019-ci-graph-and-dockerhub-publication.md) now gates Docker Hub publication. The current stages are listed in the README and `scripts/verify.sh`.
