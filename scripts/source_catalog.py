"""Authored stable names and prose; executable bindings/guards are checked separately.

IDs are semantic names, never source line numbers, list positions or hashes.
Changing a source selector requires review while its logical identity can remain.
"""


def method(identity: str, title: str, effects: str, failures: str) -> dict[str, str]:
    return dict(id="payments.method." + identity, title=title, effects=effects, failures=failures)


METHODS = {
    "health.get_health": method(
        "health-alias",
        "Report compatibility liveness",
        "Returns the healthy process response without a database probe.",
        "A server failure is a safe problem; this is not transaction readiness.",
    ),
    "health.get_liveness": method(
        "liveness",
        "Report process liveness",
        "Returns healthy independently of Mongo availability.",
        "A healthy process does not establish dependency availability.",
    ),
    "health.get_readiness": method(
        "readiness",
        "Probe Mongo readiness",
        "Runs the bounded Mongo ping and returns healthy when it succeeds.",
        "Dependency failures return a safe 503; ping readiness does not certify transactions.",
    ),
    "PaymentService.pay": method(
        "pay",
        "Create, reuse or retry a payment",
        "Reads current state; creates one payment or renews a failed/canceled attempt with history.",
        ("Orders, money and concurrency failures can reject the request; a race may expose the winning payment."),
    ),
    "PaymentService._retry": method(
        "retry",
        "Renew a terminal payment attempt",
        "Checks authoritative money and Created order state before resetting the same payment identity.",
        "Changed totals/statuses reject retry; concurrency may return a newer winner.",
    ),
    "PaymentService._require_created_order": method(
        "created-order",
        "Require a Created order",
        "Rejects an authoritative order that is not Created, ignoring case.",
        "Raises OrderNotPayableError before the caller continues.",
    ),
    "PaymentService.checkout": method(
        "checkout",
        "Create or recover a hosted checkout",
        "Uses server money and a durable attempt to create/reuse one provider session.",
        (
            "Ambiguous provider acknowledgements or persistence may retain a reservation; the "
            "23-hour boundary requires reconciliation."
        ),
    ),
    "PaymentService.get_by_order_id": method(
        "read-payment",
        "Read the current payment by order",
        "Returns the complete current aggregate without writing it.",
        "A missing payment is a safe 404; invalid stored snapshots are rejected.",
    ),
    "WebhookService.receive": method(
        "receive-webhook",
        "Verify, receive and apply a signed event",
        "Verifies original bytes, persists a receipt, then reconciles the normalized event.",
        ("Bad signatures/envelopes are rejected; HTTP acknowledgement is not proof of a transition or fulfillment."),
    ),
    "WebhookService.process_received": method(
        "process-receipt",
        "Reconcile durable normalized webhook work",
        (
            "Reuses verified receipts, atomically updates payment/history/receipt and schedules "
            "fulfillment when appropriate."
        ),
        ("Conflicts retry at most four times; existing receipts and interrupted writes require actual state evidence."),
    ),
    "WebhookService._apply": method(
        "apply-receipt",
        "Decide a receipt state and reason",
        "Matches payment/order/money/attempt/session and applies permitted terminal transitions.",
        ("Ignored/rejected reasons can accompany HTTP 200; these source guards are not runtime branch telemetry."),
    ),
    "FulfillmentService.run_batch": method(
        "fulfillment-batch",
        "Process bounded durable fulfillment work",
        "Claims due leases, reconciles orders/invoices and records fenced progress or recoverable failure.",
        (
            "The batch is bounded to 1-1000; stale leases cannot publish progress and "
            "cancellation can retain an active lease."
        ),
    ),
    "FulfillmentService._process": method(
        "fulfillment-process",
        "Reconcile Paid state and one completed invoice",
        (
            "Validates succeeded payment identity, reads authoritative order state, persists Paid "
            "progress and completed invoice association."
        ),
        (
            "Lost acknowledgements require readback; partial durable progress can remain and must "
            "not be inferred from a status alone."
        ),
    ),
    "FulfillmentService._record_failure": method(
        "fulfillment-failure",
        "Record a fenced retry or terminal failure",
        "Uses bounded backoff until ten attempts, then leaves failed work for manual repair/resume.",
        "A stale worker's failure update is ignored through lease fencing.",
    ),
    "FulfillmentService._validate_order": method(
        "fulfillment-order",
        "Validate fulfillment order ownership and money",
        "Requires matching order/money/client and a Created or Paid authoritative state.",
        "Mismatch, owner change or nonpayable state blocks automatic fulfillment.",
    ),
    "FulfillmentService._validate_invoice": method(
        "fulfillment-invoice",
        "Validate a completed invoice association",
        "Requires the expected order and nonzero invoice/client-version identities.",
        "A mismatched completed invoice blocks fulfillment.",
    ),
    "fulfill_payments.run": method(
        "fulfill-command",
        "Run fulfillment, inspect or resume durable work",
        (
            "Probes/indexes Mongo, optionally inspects/resumes work, replays pending receipts and "
            "processes a bounded batch."
        ),
        (
            "Resources close on failure; replay failures are reported after processing and do not "
            "imply universal rollback."
        ),
    ),
    "fulfill_payments.main": method(
        "fulfill-cli",
        "Parse the fulfillment operator command",
        "Validates CLI limits before allocation and prints the actual selected-mode result.",
        "Invalid limits exit with parser error; inspect/resume differ from normal batch mode.",
    ),
    "replay_webhooks.replay": method(
        "replay-command",
        "Replay persisted verified receipts",
        (
            "Reads the oldest bounded pending receipts and processes their normalized contents "
            "without provider credentials."
        ),
        "The database closes on failure; already verified work is not signed again.",
    ),
    "replay_webhooks.main": method(
        "replay-cli",
        "Parse the replay operator command",
        "Validates a 1-1000 CLI limit and prints the actual processed receipt count.",
        ("Invalid limits exit before settings/client allocation; the library entry has no separate limit guard."),
    ),
    "MongoDatabase.probe": method(
        "mongo-probe",
        "Await a bounded real Mongo ping",
        "Checks driver reachability within the configured probe deadline.",
        ("Timeout/driver failure or cancellation propagates to its caller; ping does not prove transactions."),
    ),
    "MongoDatabase.ensure_indexes": method(
        "mongo-indexes",
        "Ensure the service's Mongo indexes",
        "Creates/checks the current, history and receipt scheduling indexes.",
        "Conflicting options or duplicates can stop startup; cleanup is checked independently.",
    ),
    "MongoDatabase.close": method(
        "mongo-close",
        "Close the allocated Mongo client",
        "Releases the actual driver resource.",
        "This does not undo persisted writes or claim cleanup of another database.",
    ),
    "MongoPaymentRepository.get_by_order_id": method(
        "payment-read-order",
        "Read a payment by order identity",
        "Maps and rehydrates the current stored aggregate.",
        "Missing data returns no payment; invalid snapshots cannot bypass domain invariants.",
    ),
    "MongoPaymentRepository.get_by_id": method(
        "payment-read-id",
        "Read a payment by its identity",
        "Loads and rehydrates current payment state for reconciliation.",
        "Missing/invalid data is handled by the calling use case.",
    ),
    "MongoPaymentRepository.create": method(
        "payment-insert",
        "Insert a current payment",
        "Writes one unique payment for an order.",
        "A duplicate order can lose a create race; this call is not an automatic retry.",
    ),
    "MongoPaymentRepository.update": method(
        "payment-update",
        "Save a versioned payment and immutable history",
        "Uses the actual repository transaction and optimistic concurrency contract.",
        ("Conflicts or failed writes require state/rollback evidence; source metadata alone does not prove rollback."),
    ),
    "MongoWebhookRepository.receive": method(
        "receipt-receive",
        "Durably receive or reload a verified event",
        "Keeps one event identity and detects conflicting payload digests.",
        "A duplicate can reuse a receipt; a collision is rejected without replacing the original.",
    ),
    "MongoWebhookRepository.complete": method(
        "receipt-complete",
        "Atomically complete receipt reconciliation",
        "Stores receipt state/reason with payment/history and fulfillment markers.",
        "Conflicts or interrupted transactions require redelivery and actual atomicity evidence.",
    ),
    "MongoFulfillmentRepository.claim": method(
        "work-claim",
        "Claim the oldest due fulfillment lease",
        "Atomically acquires eligible pending/retry/expired-lease work.",
        "No work returns none; an active nonexpired lease cannot be stolen.",
    ),
    "MongoFulfillmentRepository.fail": method(
        "work-fail",
        "Store failure through the current lease",
        "Records safe error, next attempt and status only for the owning lease.",
        "A stale lease cannot overwrite the winning worker.",
    ),
    "MongoFulfillmentRepository.save_order_paid": method(
        "work-paid",
        "Persist fenced Paid progress",
        "Records authoritative client/paid progress for later recovery.",
        "A lost lease rejects stale progress; a lost acknowledgement may conceal a committed update.",
    ),
    "MongoFulfillmentRepository.complete": method(
        "work-complete",
        "Persist a fenced completed invoice association",
        "Completes work with the actual invoice and immutable client-data version.",
        ("A stale lease cannot overwrite completion; readback/retry can be necessary after acknowledgement loss."),
    ),
    "MongoFulfillmentRepository.resume": method(
        "work-resume",
        "Resume repaired failed work",
        "Resets scheduling/attempt failure fields while retaining durable Paid progress.",
        "Only failed work can be resumed; resume is not evidence that the next attempt succeeds.",
    ),
    "HttpOrderReader.get_by_id": method(
        "orders-read",
        "Read authoritative order money and status",
        "Uses the generated Orders adapter with exact decimal conversion.",
        "Missing, malformed, unavailable or timed-out Orders responses produce distinct safe failures.",
    ),
    "HttpFulfillmentOrders.get": method(
        "fulfillment-orders-read",
        "Read and validate the fulfillment order",
        "Uses the generated client and exact money/identity mapping.",
        "Unauthorized/malformed responses block; transient transport/upstream failures can retry.",
    ),
    "HttpFulfillmentOrders.mark_paid": method(
        "orders-paid",
        "Request the authoritative Paid transition",
        "Issues the actual order-status request through the adapter.",
        "An error can conceal a committed transition; the service reads back before deciding recovery.",
    ),
    "HttpFulfillmentInvoices.get_by_order": method(
        "invoice-read",
        "Look up an already completed invoice",
        "Reads the order's completed invoice association; 404 represents no completed invoice.",
        "Unauthorized/invalid results block and transient lookup failures retry.",
    ),
    "HttpFulfillmentInvoices.create": method(
        "invoice-create",
        "Create or recover an invoice",
        "Uses generated Invoice operations and validates the completed association.",
        ("A PDF failure or lost acknowledgement may require lookup/retry rather than another logical invoice."),
    ),
    "StripeCheckoutProvider.require_available": method(
        "stripe-available",
        "Require configured checkout",
        "Checks the provider configuration before checkout proceeds.",
        "Missing configuration returns checkout_disabled; no live Stripe processing is implied.",
    ),
    "StripeCheckoutProvider.validate_money": method(
        "stripe-money",
        "Require supported hosted-checkout money",
        "Accepts the implemented PLN minor-unit boundaries.",
        "Unsupported currency/amount rejects checkout without changing broader Pay conversion rules.",
    ),
    "StripeCheckoutProvider.get": method(
        "stripe-read",
        "Retrieve the existing provider session",
        "Reuses the persisted session identity.",
        "Provider failure/timeout does not establish a new session or payment outcome.",
    ),
    "StripeCheckoutProvider.create": method(
        "stripe-create",
        "Create/recover the provider session idempotently",
        "Uses server money, metadata and the reserved attempt's idempotency key.",
        "An ambiguous acknowledgement can conceal an accepted provider session.",
    ),
    "StripeWebhookVerifier.verify": method(
        "stripe-verify",
        "Verify original event bytes and envelope",
        "Checks the timestamp/signature before parsing a test-mode own-account snapshot.",
        ("Invalid signature, duplicate keys, unsupported context or malformed supported snapshots are rejected."),
    ),
    "WebhookMapper.to_receipt": method(
        "receipt-map",
        "Rehydrate a persisted normalized receipt",
        "Maps the stored verified event and durable processing fields.",
        "This is not a new signature verification or a browser request-binding path.",
    ),
    "Payment.create": method(
        "aggregate-create",
        "Construct a valid new payment",
        "Creates a nonzero payment identity with validated positive money and initial state.",
        "Pure domain validation rejects invalid construction without persistence.",
    ),
    "Payment.retry": method(
        "aggregate-retry",
        "Reset a failed/canceled attempt",
        "Retains identity, clears provider fields and returns the aggregate to Created.",
        "Only defined terminal states can retry; persistence is a separate caller action.",
    ),
    "Payment.begin_checkout": method(
        "aggregate-attempt",
        "Reserve an identifiable checkout attempt",
        "Records an attempt identity, start time and request version.",
        "Only an eligible Created payment can start an attempt.",
    ),
    "Payment.mark_as_pending": method(
        "aggregate-pending",
        "Associate a pending provider session",
        "Sets the session and permitted Pending state.",
        "Invalid provider identity/state is rejected before the caller saves.",
    ),
    "Payment.confirm_checkout": method(
        "aggregate-confirm",
        "Confirm the matching checkout payment",
        "Preserves attempt/session association and moves to Succeeded.",
        "Conflicting identifiers or invalid transitions are rejected.",
    ),
    "Payment.mark_as_failed": method(
        "aggregate-fail",
        "Record an unsuccessful checkout",
        "Sets the permitted failure state and safe provider failure code.",
        "Success/terminal transition rules still apply; this method does not persist by itself.",
    ),
}

# selector = exact normalized source expression; alias/prose remain stable through
# reordering. An unknown or removed guard fails the source gate.
GUARDS = {
    "PaymentService.checkout": [
        ("provider-missing", "provider is None", "No checkout provider is composed"),
        (
            "money-changed",
            "payment.money != order.money",
            "Current payment money differs from authoritative order money",
        ),
        (
            "state-unavailable",
            "payment.status not in (PaymentStatus.CREATED, PaymentStatus.PENDING)",
            "Payment is neither Created nor Pending",
        ),
        (
            "reserve",
            "payment.status is PaymentStatus.CREATED and payment.checkout_attempt_id is None",
            "A Created payment has no reserved attempt",
        ),
        (
            "missing-attempt",
            "payment.checkout_attempt_id is None or payment.checkout_started_at is None",
            "The attempt identity or start time is missing",
        ),
        ("pending", "payment.status is PaymentStatus.PENDING", "An existing payment is Pending"),
        ("not-created", "payment.status is not PaymentStatus.CREATED", "The remaining payment is not Created"),
        (
            "recovery-age",
            "datetime.now(UTC) - payment.checkout_started_at >= timedelta(hours=23)",
            "The attempt is at least 23 hours old",
        ),
        ("missing-session", "payment.provider_session_id is None", "A Pending payment lacks its provider session"),
        (
            "winner-conflicts",
            (
                "current is None or current.checkout_attempt_id != request.attempt_id or "
                "current.provider_session_id != session.session_id or (current.status is not "
                "PaymentStatus.PENDING)"
            ),
            "Reloaded winner does not identify the same pending attempt and session",
        ),
        (
            "winner-attempt-missing",
            "current is None or current.checkout_attempt_id is None",
            "The reservation winner or its attempt is missing",
        ),
    ],
    "PaymentService.pay": [
        ("existing", "existing_payment is not None", "A current payment already exists"),
        (
            "terminal",
            "existing_payment.status in (PaymentStatus.FAILED, PaymentStatus.CANCELED)",
            "The existing payment is Failed or Canceled",
        ),
        ("winner-missing", "existing_payment is None", "No winner can be reloaded after a duplicate insert"),
    ],
    "PaymentService._retry": [
        ("money-changed", "order.money != payment.money", "Authoritative money changed before retry"),
        (
            "winner-not-newer",
            "current is None or current.version <= payment.version",
            "The reloaded winner is absent or not newer",
        ),
        (
            "winner-terminal",
            "current.status in (PaymentStatus.FAILED, PaymentStatus.CANCELED)",
            "The reloaded winner is still terminal",
        ),
    ],
    "PaymentService._require_created_order": [
        ("not-created", "status.casefold() != 'created'", "Authoritative order status is not Created")
    ],
    "PaymentService.get_by_order_id": [("missing", "payment is None", "No current payment exists for the order")],
    "WebhookService.receive": [],
    "WebhookService.process_received": [
        ("already-decided", "receipt.state is not WebhookState.PENDING", "The durable receipt already has a decision"),
        ("has-checkout", "event.checkout", "The normalized event contains a supported checkout notification"),
    ],
    "WebhookService._apply": [
        ("unsupported", "checkout is None", "The verified event has no supported checkout notification"),
        ("payment-missing", "payment is None", "The referenced current payment is missing"),
        (
            "payment-mismatch",
            "payment.order_id != checkout.order_id or payment.money != checkout.money",
            "Order identity or money does not match the current payment",
        ),
        (
            "stale-attempt",
            "payment.checkout_attempt_id != checkout.attempt_id",
            "The notification targets an older/different checkout attempt",
        ),
        (
            "session-mismatch",
            "payment.provider_session_id not in (None, checkout.session_id)",
            "The recorded session conflicts with the notification",
        ),
        ("success", "event.outcome is CheckoutOutcome.SUCCEEDED", "The normalized outcome is successful payment"),
        ("already-succeeded", "payment.status is PaymentStatus.SUCCEEDED", "The current payment already succeeded"),
        ("waiting", "event.outcome is CheckoutOutcome.WAITING", "Checkout completion is still unpaid"),
        (
            "already-terminal",
            "payment.status in (PaymentStatus.FAILED, PaymentStatus.CANCELED)",
            "The current payment already failed or was canceled",
        ),
        ("created", "payment.status is PaymentStatus.CREATED", "The current payment is still Created"),
        (
            "provider-mismatch",
            "payment.provider_payment_id != checkout.provider_payment_id",
            "The successful provider payment identity conflicts",
        ),
        ("expired", "event.outcome is CheckoutOutcome.EXPIRED", "The normalized checkout outcome is expiry"),
    ],
    "FulfillmentService.run_batch": [
        ("limit", "not 1 <= limit <= 1000", "The batch limit is outside 1-1000"),
        ("no-work", "work is None", "No due work could be claimed"),
    ],
    "FulfillmentService._record_failure": [
        (
            "retryable",
            "retry and work.attempts < self.MAX_ATTEMPTS",
            "The failure is retryable and fewer than ten attempts have been made",
        )
    ],
    "FulfillmentService._validate_order": [
        (
            "mismatch",
            "order.order_id != work.order_id or order.money != work.money or order.client_id.int == 0",
            "Authoritative order identity/money/client is invalid",
        ),
        (
            "owner-changed",
            "work.client_id is not None and work.client_id != order.client_id",
            "A previously recorded owner differs from the authoritative client",
        ),
        (
            "not-payable",
            "order.status not in {'Created', 'Paid'}",
            "The authoritative order is neither Created nor Paid",
        ),
    ],
    "FulfillmentService._validate_invoice": [
        (
            "mismatch",
            (
                "invoice.order_id != work.order_id or invoice.invoice_id.int == 0 or "
                "invoice.client_data_version_id.int == 0"
            ),
            "The completed invoice association or its identities are invalid",
        )
    ],
    "FulfillmentService._process": [
        ("exhausted", "work.attempts > self.MAX_ATTEMPTS", "The claim exceeds ten allowed attempts"),
        (
            "payment-mismatch",
            (
                "payment is None or payment.status is not PaymentStatus.SUCCEEDED or payment.order_id "
                "!= work.order_id or (payment.money != work.money) or (payment.checkout_attempt_id != "
                "work.attempt_id)"
            ),
            "Current succeeded payment identity/money/attempt does not match the work",
        ),
        ("created-order", "order.status == 'Created'", "The authoritative order is still Created"),
        ("invoice-missing", "invoice is None", "No completed invoice was found"),
        ("paid-regressed", "work.order_paid", "Durable Paid progress exists although the order returned to Created"),
        ("paid-unconfirmed", "order.status != 'Paid'", "Readback has not confirmed the Paid transition"),
    ],
    "fulfill_payments.run": [
        ("limit", "not 1 <= limit <= 1000", "The direct batch limit is outside 1-1000"),
        ("resume", "resume is not None", "The operator requested a failed-work resume"),
        ("inspect", "inspect", "The operator requested durable work inspection"),
        ("pending-failed", "receipt_failures", "Some pending receipts could not be reconciled"),
        (
            "resume-rejected",
            "not await repository.resume(resume, datetime.now(UTC))",
            "The selected work is not resumable failed work",
        ),
    ],
    "fulfill_payments.main": [
        ("limit", "not 1 <= args.limit <= 1000", "The CLI limit is outside 1-1000"),
        ("batch-output", "not args.inspect", "The selected mode is not inspection"),
    ],
    "replay_webhooks.replay": [],
    "replay_webhooks.main": [("limit", "not 1 <= args.limit <= 1000", "The replay CLI limit is outside 1-1000")],
    "health.get_health": [],
    "health.get_liveness": [],
    "health.get_readiness": [],
    "PaymentPolicy.require_identifier": [
        ("nonzero-uuid", "not isinstance(value, UUID) or value.int == 0", "The supplied identity is not a nonzero UUID")
    ],
    "PaymentPolicy.require_provider_identifier": [
        (
            "ascii",
            "not isinstance(value, str) or not value or (not value.isascii()) or (not value.isprintable())",
            "The provider identity is not nonempty printable ASCII",
        ),
        (
            "whitespace",
            "any((character.isspace() for character in value))",
            "The provider identity contains whitespace",
        ),
    ],
    "PaymentPolicy.validate_snapshot": [
        (
            "version",
            "isinstance(version, bool) or not isinstance(version, int) or version < 0",
            "The stored version is not a nonnegative integer",
        ),
        (
            "types",
            "not isinstance(money, Money) or not isinstance(status, PaymentStatus)",
            "Stored money/status is not a valid domain type",
        ),
        (
            "created-time",
            "not isinstance(created_at, datetime) or created_at.utcoffset() is None",
            "Creation time is not timezone-aware",
        ),
        (
            "updated-time",
            (
                "updated_at is not None and (not isinstance(updated_at, datetime) or "
                "updated_at.utcoffset() is None or updated_at < created_at)"
            ),
            "The supplied update time is naive, invalid or earlier than creation",
        ),
        (
            "version-without-attempt",
            "checkout_attempt_id is None and checkout_request_version != 1",
            "A nonlegacy request version has no attempt",
        ),
        ("attempt", "checkout_attempt_id is not None", "A checkout attempt identity is present"),
        ("provider-session", "provider_session_id is not None", "A provider session identity is present"),
        ("provider-payment", "provider_payment_id is not None", "A provider payment identity is present"),
        ("failure-code", "failure_code is not None", "A provider failure code is present"),
        ("created-state", "status is PaymentStatus.CREATED", "The stored state is Created"),
        ("state-inconsistent", "not valid", "The complete snapshot violates the selected state invariant"),
        (
            "attempt-time",
            (
                "not isinstance(checkout_started_at, datetime) or checkout_started_at.utcoffset() is "
                "None or (not isinstance(updated_at, datetime)) or (not created_at <= "
                "checkout_started_at <= updated_at)"
            ),
            "Attempt time is invalid or outside creation/update bounds",
        ),
        ("time-without-attempt", "checkout_started_at is not None", "A start time exists without an attempt identity"),
        ("pending-state", "status is PaymentStatus.PENDING", "The stored state is Pending"),
        ("succeeded-state", "status is PaymentStatus.SUCCEEDED", "The stored state is Succeeded"),
        ("failed-state", "status is PaymentStatus.FAILED", "The stored state is Failed"),
    ],
    "PaymentPolicy.require_transition": [
        (
            "allowed-edge",
            "target not in cls._ALLOWED_TRANSITIONS.get(current, frozenset())",
            "The requested state edge is not in the allowed transition map",
        )
    ],
    "PaymentPolicy.require_checkout_start": [
        ("created", "status is not PaymentStatus.CREATED", "The payment is not Created when reserving checkout")
    ],
    "PaymentPolicy.require_checkout_confirmation": [
        (
            "association",
            (
                "attempt_id is None or current_session not in (None, session_id) or current_payment "
                "not in (None, payment_id)"
            ),
            "The confirmation lacks or conflicts with the recorded attempt/session/payment association",
        )
    ],
    "PaymentPolicy.require_checkout_request_version": [
        (
            "positive-version",
            "isinstance(value, bool) or not isinstance(value, int) or value < 1",
            "Checkout request version is not a positive integer",
        )
    ],
    "Money._validate": [
        (
            "amount",
            "isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor <= 0",
            "Money amount is not a positive nonboolean integer",
        ),
        ("currency-type", "not isinstance(currency, str)", "Currency is not text"),
        (
            "currency-format",
            "len(raw_currency) != 3 or not raw_currency.isascii() or (not raw_currency.isalpha())",
            "Trimmed currency does not contain exactly three ASCII letters",
        ),
    ],
}

POLICIES = {
    "PaymentPolicy.require_identifier": ("identifier", "Validate nonzero aggregate/attempt identities"),
    "PaymentPolicy.require_provider_identifier": ("provider-identifier", "Validate printable provider identities"),
    "PaymentPolicy.validate_snapshot": ("snapshot", "Validate complete constructed/rehydrated payment state"),
    "PaymentPolicy.require_transition": ("transition", "Validate the requested payment state edge"),
    "PaymentPolicy.require_checkout_start": ("checkout-start", "Validate checkout reservation eligibility"),
    "PaymentPolicy.require_checkout_confirmation": (
        "checkout-confirmation",
        "Validate immutable checkout confirmation associations",
    ),
    "PaymentPolicy.require_checkout_request_version": (
        "checkout-version",
        "Validate the persisted checkout request version",
    ),
    "Money._validate": ("money", "Validate positive minor units and normalized currency"),
}

FLOW_IDS = {
    "get_health": "health-alias",
    "get_liveness": "liveness",
    "get_readiness": "readiness",
    "createOrderCheckout": "checkout",
    "payOrder": "pay",
    "getPaymentByOrderId": "read-payment",
    "receiveStripeWebhook": "webhook",
    "fulfill": "fulfill",
    "replay": "replay",
}

CATCHES = {
    "PaymentConflictError": (
        "optimistic-conflict",
        "The protected repository operation reports an optimistic conflict",
    ),
    "PaymentDuplicateError": ("duplicate-payment", "A competing insertion already created this order's payment"),
    "FulfillmentLeaseLostError": ("lease-lost", "The worker no longer owns the current lease"),
    "FulfillmentBlockedError": ("fulfillment-blocked", "Authoritative validation blocks automatic fulfillment"),
    "FulfillmentRetryError": ("fulfillment-retry", "The downstream result requires recoverable reconciliation"),
    "TimeoutError": ("deadline", "The protected operation exceeds its deadline"),
    "Exception": ("unexpected", "An unexpected protected-operation failure requires safe recovery"),
    "(PyMongoError, TimeoutError)": ("mongo-probe", "The real Mongo probe fails or exceeds its deadline"),
}

RECEIPTS = {
    "unsupported_event": (
        "ignored",
        "The verified event has no supported checkout notification",
        "Retain an ignored receipt without a payment transition",
    ),
    "payment_not_found": (
        "rejected",
        "The referenced current payment is missing",
        "Retain a rejected receipt without inventing a payment",
    ),
    "payment_mismatch": (
        "rejected",
        "Order identity or money differs",
        "Retain a rejected receipt and the existing payment",
    ),
    "stale_attempt": ("ignored", "Notification targets a different attempt", "Retain the newer payment attempt"),
    "session_mismatch": (
        "rejected",
        "Notification conflicts with the recorded session",
        "Preserve the recorded session association",
    ),
    "provider_payment_mismatch": (
        "rejected",
        "A succeeded payment has a different provider payment",
        "Preserve the successful association",
    ),
    "already_succeeded": (
        "ignored",
        "Current payment has already succeeded",
        "A stale failure/expiry or replay cannot undo success",
    ),
    "payment_succeeded": (
        "applied",
        "Matching checkout success is accepted",
        "Apply success with atomic receipt/history/fulfillment markers",
    ),
    "awaiting_payment": ("ignored", "Checkout completion is unpaid", "Wait for a later async payment outcome"),
    "already_terminal": (
        "ignored",
        "Current payment is already Failed or Canceled",
        "Preserve the terminal payment for this notification",
    ),
    "payment_failed": (
        "applied",
        "Matching failure or expiry is accepted",
        "Apply a failed payment with the appropriate provider failure code",
    ),
}

HTTP_FAILURES = {
    400: (
        "Request input, signature or supported snapshot is invalid",
        "Return a complete safe problem",
        "The actual public code/case identifies the cause; it does not expose every domain rule",
    ),
    404: (
        "An authoritative order/payment or route is missing",
        "Return a complete safe not-found problem",
        "Known operations and unmatched routing remain separate; absence is not a rollback proof",
    ),
    405: (
        "The method is unsupported on a known path",
        "Return a safe problem with the actual Allow header",
        "The linked handler flow is nominal context, not evidence that its body ran",
    ),
    409: (
        "State, totals, optimistic version or checkout reconciliation conflicts",
        "Return the actual conflict code while preserving the evidenced winner/progress",
        "A conflict does not identify an executed internal guard by itself",
    ),
    413: (
        "Webhook bytes exceed the 1 MiB input boundary",
        "Reject the oversized delivery with a safe problem",
        "The original bytes remain evidence; no receipt mutation is inferred from metadata",
    ),
    415: (
        "A nonempty command body or webhook has unsupported media",
        "Return the safe unsupported-media problem",
        "Bodyless empty commands and signed webhook media rules are distinct",
    ),
    500: (
        "An unexpected serving failure reaches the safe error boundary",
        "Return internal_error with a fresh trace and safe details",
        "Existing durable progress may remain; only actual state/transaction evidence establishes rollback",
    ),
    502: (
        "An upstream order/provider response is unavailable or invalid",
        "Return the actual safe upstream failure code",
        "A checkout reservation or provider acceptance may already exist",
    ),
    503: (
        "Readiness/configuration/receipt processing is unavailable",
        "Return the actual safe unavailable/retry code",
        "A durable receipt can remain pending and require redelivery",
    ),
    504: (
        "The upstream order/provider deadline expires",
        "Return the actual safe timeout code",
        "A timeout does not prove a downstream operation was not accepted",
    ),
}
