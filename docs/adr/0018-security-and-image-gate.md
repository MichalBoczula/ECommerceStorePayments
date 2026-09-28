# ADR-0018: Dependency, secret and image security gate

Status: Accepted
Date: 2026-09-28

## Context

PAY/17 builds and smoke tests a non-root image, but the build alone cannot detect known vulnerabilities in locked dependencies or the resulting OS and library packages. A pull request also needs checks for newly introduced vulnerable dependencies and committed credentials. Image publication is deferred to PAY/19.

## Decision

- Audit all packages in the committed `uv.lock`, including the dev group, using the pinned uv CLI's `uv audit --locked`. Any known vulnerability or audit error fails. Upgrade the test-only pytest package from 8.4.2 to 9.1.1 to resolve the reported tmpdir advisory rather than excluding the dev group.
- On pull requests, Dependency Review rejects newly introduced dependencies with HIGH or CRITICAL advisories. This job is intentionally skipped on main pushes; the final gate checks the expected result for each event. The full lockfile audit runs on both events.
- GitHub Dependency Graph must be enabled in the repository settings for Dependency Review to run. An unavailable graph fails the PR gate rather than being treated as a passing review.
- Gitleaks v3 scans Git history on both events. Any detected secret or scanner failure blocks the gate; automated PR comments and finding artifacts are disabled. The repository is owned by a personal GitHub account, so this action does not require an organization license.
- Scan the same locally built image that passed the Compose smoke test with Trivy. OS and library vulnerabilities rated HIGH or CRITICAL with an available fix fail; `ignore-unfixed` excludes findings without a fix. Scanner errors also fail. No image is published in this task.
- Remove unused vulnerable `msgpack` and `setuptools` packages inherited from the Python base image. Neither is in the runtime lockfile; keeping them would add avoidable scan findings.
- Require quality, five test suites, lockfile audit, secret scan, conditional PR review and the smoke-tested image scan in `final-gate`. Actions are pinned to commit SHA. The local `scripts/verify.sh` runs the lockfile audit and the container smoke; the Trivy check runs in CI where Docker is available.

## Consequences

The gate checks the runtime and development lockfile plus the actual image. Unfixed OS/library issues remain visible in Trivy output but do not block; the next base image or package update can change the result as vulnerability databases change. Dependency Review checks changes in PRs, while the full lock audit checks existing dependencies on every run. No public API, persistence schema or application-layer dependency changes.

## Alternatives considered

Auditing only runtime dependencies would miss vulnerable test tools. Ignoring the pytest advisory would retain a fixable known issue. Scanning a separately built image could differ from the image exercised by Compose. Publishing before scanning would bypass the security decision for the published artifact.
