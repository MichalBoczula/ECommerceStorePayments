# ADR-0004: Isolated MongoDB integration tests

Status: Accepted
Date: 2026-09-27

## Context

The in-memory collection used by repository unit tests cannot verify BSON UUID and datetime conversions, MongoDB's unique index, or real driver behavior.

## Decision

Run repository integration tests against a MongoDB Testcontainers instance. The container initializes a single-node replica set so payment/history writes can use transactions (see [ADR-0007](0007-payment-history.md)). Share one container per test session and create a unique database per test. Create indexes through `MongoDatabase.ensure_indexes()` and drop each database during fixture teardown. Keep fake collection tests in the unit suite. Run the integration stage in CI and in the local verification script; a Docker daemon is required.

## Consequences

The tests check create, replace, lookup, unique `order_id`, mapper rehydration, BSON UUID values, timezone aware UTC datetimes, and database isolation against MongoDB. BSON stores datetimes at millisecond precision, so comparisons normalize Python microseconds. A developer without Docker can run focused stages, but full verification needs Docker.

## Alternatives considered

Using mocks for all repository tests would not expose actual BSON and index behavior. Starting a fresh container for each test would give isolation with substantially longer execution; unique databases provide isolation within one container.
