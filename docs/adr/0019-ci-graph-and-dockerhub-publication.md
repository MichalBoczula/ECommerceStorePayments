# ADR-0019: Named CI suites and gated Docker Hub publication

Status: Accepted
Date: 2026-09-28

## Context

PAY/18 gates dependencies, secrets, tests and the smoke-tested image. The five test suites appear as a matrix of identically named jobs, which makes their roles harder to read in the GitHub Actions graph. The image is not yet available to other portfolio services through Docker Hub.

## Decision

- Run Domain, Application, Infrastructure, ExternalProviders and Acceptance as five named jobs after the source quality job. Keep their existing `scripts/ci.sh suite` commands, isolated runners, coverage thresholds, reports and artifact names.
- A `quality-gate` job requires source quality, all five suites, locked dependency audit, secret scan and PR-only Dependency Review. A skipped Dependency Review is accepted only for a `main` push. If any required result fails or is skipped unexpectedly, do not build or publish.
- The container job runs only after the quality gate succeeds. It builds the Compose image, smoke tests it, and scans that same local image with the PAY/18 Trivy policy. `final-gate` requires the quality gate and the entire container job, including publication on push.
- Only on a push to `main`, log in with repository secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`, tag the scanned local image as `mb0101/ecommerce-store-payments-api:<full GITHUB_SHA>` and `:latest`, and push both. Verify both local tags have the scanned image ID, capture the digest reported by each push, and fail if either is missing or differs. Record the image ID, tags and digest in the job summary. Pull requests never access Docker Hub credentials or publish.
- Pin the Docker login action to its release commit, as with the other CI actions. No registry credentials enter the build context or runtime image.

## Consequences

The graph shows individual suite results and the source/security gate before the container job. A `main` push publishes only after all checks and the image scan have succeeded. The final job fails if the registry login or either push fails. A PR can verify the whole pipeline except the push because secrets and publication are restricted to `main`; the first merged push verifies registry access and tag digest equality. No API, persistence schema or dependency changes.

## Alternatives considered

Keeping the suite matrix would preserve less workflow text but not show distinct suite roles in the job graph. A separate publishing runner would rebuild or transfer the scanned image, weakening the direct identity check or adding an image artifact. Publishing during the first build before the suites would allow an unverified commit to replace `latest`.
