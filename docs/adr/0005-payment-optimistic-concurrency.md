# ADR-0005: Version payment writes with compare-and-replace

Status: Accepted
Date: 2026-09-27

## Context

Replacing MongoDB payment documents solely by `_id` lets a stale writer overwrite a newer status. Two Pay requests may both read an absent payment before either creates it. Documents written before PAY/5 do not contain a `version` field.

## Decision

The aggregate and MongoDB document carry a nonnegative integer version. A created payment starts at 0. `MongoPaymentRepository.update` uses a single `replace_one` matching `_id`, `order_id` and the read version, without upsert. Its replacement has version +1. On success it returns a new aggregate with the advanced version; the caller must keep that returned aggregate for subsequent writes. The input remains at its original version, including when a write fails.

On a failed match, lookup by ID distinguishes a missing record (`PaymentMissingError`) from an existing but stale or mismatched record (`PaymentConflictError`). The unique order ID index and MongoDB `_id` index arbitrate competing creates; `DuplicateKeyError` becomes `PaymentDuplicateError`. If another request has created a payment for the same order, `PaymentService.pay` reads and returns the winner. If no payment exists for that order, the duplicate error propagates and the current API maps it to HTTP 409. The complete Pay response semantics remain in PAY/9.

Versionless documents are interpreted as version 0. The version-0 update filter matches either numeric zero or an absent version, and writes version 1 atomically. A second writer holding the old snapshot then receives a conflict. Documents with other invalid version values fail domain validation; they are not silently migrated.

## Consequences

Concurrent updates cannot overwrite one another silently. Existing versionless documents need no bulk migration for normal reads and writes. Retries after a conflict must reload and reapply the intended domain decision; the repository does not automatically retry a stale replacement. Repository update advances the version for every successful write, including an unchanged snapshot; higher-level no-op policy remains with application use cases.

## Alternatives considered

- Last-write-wins replacement by `_id` loses state changes under concurrent writes.
- Eagerly update all versionless documents at startup, which would add operational risk before the startup and migration policy is finalized.
- Mutate the input aggregate version before or after storage; returning a new versioned snapshot makes failed writes and old references explicitly stale.
