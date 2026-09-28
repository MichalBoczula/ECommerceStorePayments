# Architecture Decision Records

Records describe decisions implemented in Payments. Keep proposed work in [the technical backlog](../../TECHNICAL_TODO.md). A later ADR can supersede a decision without deleting the original context.

Use repository-local sequential numbers. Each record has a title, `Status` and `Date`, then `Context`, `Decision`, `Consequences`, and `Alternatives considered` in that order. Update this index when adding a record.

| ADR | Status | Decision |
| --- | --- | --- |
| [0001](0001-payment-layers-and-mongodb-mapping.md) | Accepted | Separate Payment domain state from MongoDB documents and HTTP transport. |
| [0002](0002-pinned-python-and-basic-ci.md) | Accepted | Pin local/CI tools and run the same baseline quality stages. |
| [0003](0003-payment-invariants-and-rehydration.md) | Accepted | Validate payment snapshots and make transitions and domain errors explicit. |
| [0004](0004-isolated-mongodb-integration-tests.md) | Accepted | Run real MongoDB repository tests in isolated per-test databases. |
| [0005](0005-payment-optimistic-concurrency.md) | Accepted | Version payment writes and migrate versionless documents on their first update. |
| [0006](0006-startup-and-health.md) | Accepted | Probe MongoDB at startup and separate liveness from database readiness. |
| [0007](0007-payment-history.md) | Accepted | Archive previous payment snapshots in a shadow collection in the same transaction as current-state updates. |
| [0008](0008-orders-http-adapter.md) | Accepted | Validate the Orders response and convert amounts with explicit currency minor units at the HTTP boundary. |
| [0009](0009-pay-get-semantics.md) | Accepted | Return 201 for new payments, 200 for existing/retried payments, and retry failed/canceled attempts on the same aggregate. |
| [0010](0010-safe-public-errors.md) | Accepted | Map API failures to safe problem+json responses with stable codes and trace IDs. |
| [0011](0011-acceptance-isolation.md) | Accepted | Exercise the public API against isolated real MongoDB with a controlled Orders HTTP boundary. |
| [0012](0012-generated-operation-links.md) | Accepted | Generate operation-to-flow, policy and acceptance links from executable sources. |
| [0013](0013-generated-openapi-contract.md) | Accepted | Export and validate OpenAPI against acceptance outcomes and observed HTTP bodies. |
| [0014](0014-python-architecture-gate.md) | Accepted | Enforce Python layer imports and MongoDB persistence boundaries with source checks. |
