# Architecture Decision Records

Records describe decisions implemented in Payments. Keep proposed work in [the technical backlog](../../TECHNICAL_TODO.md). A later ADR can supersede a decision without deleting the original context.

Use repository-local sequential numbers. Each record has a title, `Status` and `Date`, then `Context`, `Decision`, `Consequences`, and `Alternatives considered` in that order. Update this index when adding a record.

| ADR | Status | Decision |
| --- | --- | --- |
| [0001](0001-payment-layers-and-mongodb-mapping.md) | Accepted | Separate Payment domain state from MongoDB documents and HTTP transport. |
| [0002](0002-pinned-python-and-basic-ci.md) | Accepted | Pin local/CI tools and run the same baseline quality stages. |
