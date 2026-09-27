# ADR-0003: Validate payment state on creation and rehydration

- Status: Accepted
- Date: 2026-09-27

## Context

Payment changes state in response to provider operations and will eventually process duplicate and out-of-order messages. The original aggregate rejected some transitions with general `ValueError`, but accepted arbitrary state combinations when rebuilding from a MongoDB document. Domain validation must also work without an API or database dependency.

## Decision

`PaymentPolicy` is executed by the aggregate constructor, including the `rehydrate` path, and by each state-changing method. Payment/order IDs must be nonzero UUIDs. Timestamps must be timezone-aware, and an update cannot precede creation. Provider identifiers and failure codes, when present, must be nonempty printable ASCII without whitespace.

State snapshots follow these rules:

| Status | Required provider data | Other state |
| --- | --- | --- |
| Created | None | Initially no update time; retried Created has a positive version and update time. No failure code. |
| Pending | Session ID | Update time; no payment ID or failure code. |
| Succeeded | Session and payment IDs | Update time; no failure code. |
| Failed | Session ID; failure code optional | Update time; no payment ID. |
| Canceled | Session ID optional | Update time; no payment ID or failure code. |

New transitions are Created → Pending/Canceled and Pending → Succeeded/Failed/Canceled. ADR-0009 adds Failed/Canceled → Created through `retry`, clearing prior provider data. An exact repeat of Pending with the same session ID, Succeeded with the same payment ID, Failed with the same failure code, Canceled, or a retried Created state is a no-op that does not change `updated_at`. A different repeated identifier or an invalid operation raises `PaymentTransitionError`. Invalid values or snapshots raise `PaymentValidationError` or `MoneyValidationError`. These derive from `PaymentDomainError`, expose stable `PaymentErrorCode` values, and retain `ValueError` compatibility. Mapping these errors to an HTTP problem response belongs to PAY/10.

Money requires a positive integer of minor units and a three-letter ASCII currency code, normalized to uppercase. This checks the code's shape, not membership in an ISO registry or provider support. Decimal conversion and currency-specific exponents belong to the Orders adapter work in PAY/8.

## Consequences

The MongoDB mapper still uses `rehydrate`, so an inconsistent stored document fails explicitly instead of producing an invalid aggregate. Existing documents must match these state rules when read; data migration is a separate task if real persisted data violates them. Provider retries with identical data do not advance timestamps, while conflicting retries remain visible as domain errors.

## Alternatives considered

- Trust persisted documents during rehydration: allows invalid states to bypass the aggregate.
- Automatically accept a different ID for an already completed transition: obscures conflicting provider events.
- Add a static catalogue of every ISO or Stripe currency here: couples the base Money invariant to a changing provider-specific list and does not address minor-unit conversion.
