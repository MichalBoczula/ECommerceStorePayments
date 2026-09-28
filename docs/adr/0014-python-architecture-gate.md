# ADR-0014: Check Python import and persistence boundaries

Status: Accepted

Date: 2026-09-28

## Context

Payments has Domain, Application, Infrastructure and API directories with explicit ownership, but ordinary lint and type checks do not prevent an import from reversing a dependency or leaking a MongoDB document into the public contract. The API composition root builds concrete adapters. Readiness is a technical exception: it probes MongoDB directly and handles `PyMongoError`.

## Decision

`scripts/check_architecture.py` parses every Python source file under the package with the standard-library AST. It resolves absolute and relative imports, plus literal `__import__` and `importlib.import_module` calls. It checks these source-level rules:

- Domain imports only Domain; Application imports Application or Domain; Infrastructure imports Infrastructure, Application or Domain; API imports API, Application or Domain.
- Domain and Application do not import FastAPI, Starlette, Pydantic, HTTPX or MongoDB drivers. MongoDB driver imports belong in `infrastructure/persistence/mongodb`.
- Only `api/app.py` may import Infrastructure to compose adapters. `api/routes/health.py` may import the specific `MongoDatabase` probe type and `PyMongoError` for readiness; other routes cannot import Infrastructure or MongoDB drivers. MongoDB document modules never leave Infrastructure.
- Wildcard imports fail because they hide dependencies. A missing layer or invalid Python source also fails.

The shared `architecture` stage runs before other source checks in CI and `scripts/verify.sh`. Unit tests scan the current source and inject forbidden imports into temporary source trees, including a subprocess run proving that the CI command exits nonzero. The rules and exceptions are versioned with the service and use no added runtime or development dependency.

## Consequences

New Python imports violating a boundary fail with a file and line number. The static checker does not evaluate arbitrary runtime module names constructed dynamically, and it does not replace tests of state mapping or behavior. A future readiness abstraction can remove the technical exception without changing the other layer rules. If new adapters need MongoDB access, they belong in the persistence package rather than widening the exception.

## Alternatives considered

A text search would mistake strings or comments for imports and miss relative imports. An import-time check would execute application code and require external dependencies. Adding a general dependency graph package would bring extra tool configuration for a small, explicit Python layout.
