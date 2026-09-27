# ADR-0001: Separate Payment domain state from MongoDB and HTTP

- Status: Accepted
- Date: 2026-09-27

## Context

Payments needs to store payment state by order ID while exposing HTTP operations. A domain object tied to BSON, an HTTP request model, or an external Orders client would make state transitions depend on transport and persistence choices.

## Decision

Keep the Payment aggregate and Money value object in Domain. The aggregate creates new state through `Payment.create` and reconstructs persisted state through `Payment.rehydrate`. Domain declares a PaymentRepository contract. Application uses that contract and the OrderReader port to coordinate Pay and Get by order ID.

Infrastructure implements the repository using a MongoDB PaymentDocument and explicit PaymentMapper. The mapper converts documents into domain state through `rehydrate`. The HTTP Orders reader is an Infrastructure adapter. FastAPI routes and response models are in API; `api/app.py` assembles the service and concrete adapters. The MongoDB collection has a unique `order_id` index.

## Consequences

Domain rules can be tested without MongoDB or FastAPI. Changes to the stored document or Orders transport remain localized to adapters and mapping, with integration tests needed to prove actual database behavior.

Later decisions added optimistic version matching in [ADR-0005](0005-payment-optimistic-concurrency.md) and transactionally persisted history in [ADR-0007](0007-payment-history.md). The Stripe webhook ledger remains a separate later decision.

## Alternatives considered

- Persist the aggregate directly as a BSON document: couples domain structure to MongoDB schema and driver behavior.
- Let FastAPI routes call the MongoDB collection directly: spreads application decisions across HTTP handlers.
