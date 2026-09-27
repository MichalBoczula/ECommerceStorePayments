# ADR-0007: Archive previous Payment snapshots transactionally

Status: Accepted
Date: 2026-09-27

## Context

The current payment must remain cheap to find by order ID, while prior states need to be available for diagnosis and an audit trail. Storing every version in `payments` would require every active-state lookup to filter versions and expand the collection with every transition. A separate history collection keeps the operational query and its unique order index simple.

## Decision

`payments` holds one current document per payment. `payment_history` stores only the previous state of each successful update, with a flat copy of its business fields, `payment_id`, `version`, `recorded_at`, and a deterministic `_id` composed of payment ID and archived version. A new payment has no history; after the first update, history contains version 0 and the current document has version 1. For a legacy versionless document, the archived snapshot is normalized to version 0.

The repository reads the matching current document, replaces it using the expected-version and order-ID filter, and inserts the previous snapshot in one MongoDB transaction. Missing or stale writes produce typed errors and do not append history. An archive failure aborts the current-state replacement. The repository exposes ordered prior snapshots through `get_history(payment_id)`; the public HTTP contract does not change. Use the history collection's default `_id` index and an index on `payment_id`; the small number of transitions per payment is sorted by version after reading. Startup creates both named indexes.

MongoDB must run as a replica set or sharded cluster for these transactions, including local development. The integration fixture runs a single-node replica set and verifies rollback, conflicts and legacy migration. A provider webhook event ledger remains a separate later design.

## Consequences

Each successful transition writes two documents and keeps the current payment independently indexed. History grows with transitions, while the operational collection stays one document per payment. History records earlier snapshots only; append the current payment when presenting a full timeline. Deployments using standalone MongoDB must switch to a replica set before processing updates. Existing payments do not gain retroactive snapshots until they are updated.

## Alternatives considered

- Put all versions into `payments` and mark one active: multiplies the operational collection and complicates unique order and active-state queries.
- Write history outside the current-state transaction: an interrupted write can leave history and current state inconsistent.
- Store only transition events: would not preserve the complete earlier document and requires reconstruction to inspect a state.
