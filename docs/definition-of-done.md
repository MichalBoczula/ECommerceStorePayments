# Definition of done

This is a review standard for a change, not a claim that every existing endpoint already meets it. Apply relevant items and explain a deferred or inapplicable check in the PR.

- Link a PAY/xx or STRIPE/xx backlog item. Explain the problem, resulting behavior, scope, and any new dependency or architectural choice.
- Preserve the API / Application / Domain / Infrastructure boundaries. Review BSON document mapping and schema/index evolution for persistence changes.
- Test pure rules at Domain level, application decisions with suitable port substitutes, real MongoDB behavior with Testcontainers where storage semantics matter, and public HTTP outcomes in acceptance tests as those suites are built.
- For API changes, review request validation, public error/status/media type, generated OpenAPI, and success plus distinct failure causes. For writes, verify durable state, duplicate/concurrent requests, and absence of partial writes where applicable.
- Run `bash scripts/verify.sh` for the current lock/install, format, lint, typing, tests, wheel build and install check, or the relevant `scripts/ci.sh` stages for focused work. Record actual commands and results; report checks unavailable because a dependency or gate has not yet been implemented.
- Run subsequent quality gates once their backlog items exist. Do not lower agreed coverage thresholds, skip failing tests, hide a tool failure, or turn ordinary warnings into an unagreed global failure policy.
- Update README, source documentation, ADR, and backlog when behavior or a decision changes. An ADR marked Accepted must describe an implemented decision. Follow-up tasks remain open until their criteria are verified.

See [the backlog](../TECHNICAL_TODO.md) for the current gaps; this checklist does not silently close them.
