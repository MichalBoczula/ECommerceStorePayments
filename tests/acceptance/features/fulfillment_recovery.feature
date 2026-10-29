Feature: Complete durable fulfillment and invoice recovery

  Scenario: PAY09-01 Use authoritative Paid state without another Paid write
    The verified payment already has an authoritative Paid order. The worker reads it and creates the completed invoice without issuing another Paid request.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value        |
      | Mode           | already_paid |
      | PriorRetries   | 0            |
      | ReceiptFixture | none         |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-01"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 1                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                  |
      | Sequence          | order:200 invoice:404 create:200       |
      | LogicalPaidWrites | 0                                      |
      | LogicalInvoices   | 1                                      |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333" |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-02 Preserve the version of an existing completed invoice
    An authoritative Paid order already owns a completed invoice using an older data version. Lookup completes work without writes and preserves that exact version reference.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value            |
      | Mode           | existing_invoice |
      | PriorRetries   | 0                |
      | ReceiptFixture | none             |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-02"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 1                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                  |
      | Sequence          | order:200 invoice:200                  |
      | LogicalPaidWrites | 0                                      |
      | LogicalInvoices   | 0                                      |
      | InvoiceVersion    | "44444444-4444-4444-8444-444444444444" |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-03 Recover an unavailable order read when its retry becomes due
    An upstream order failure leaves safe retry state without Paid progress. A later fresh worker recovers at the persisted deadline and completes one logical order and invoice.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value     |
      | Mode           | order_500 |
      | PriorRetries   | 0         |
      | ReceiptFixture | none      |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-03"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value               |
      | _id                                | {before}            |
      | event_type                         | {before}            |
      | payload_digest                     | {before}            |
      | outcome                            | {before}            |
      | payment_id                         | {before}            |
      | order_id                           | {before}            |
      | attempt_id                         | {before}            |
      | amount_minor                       | {before}            |
      | currency                           | {before}            |
      | session_id                         | {before}            |
      | provider_payment_id                | {before}            |
      | state                              | {before}            |
      | reason                             | {before}            |
      | received_at                        | {before}            |
      | completed_at                       | {before}            |
      | fulfillment_status                 | "retry"             |
      | fulfillment_attempts               | 1                   |
      | fulfillment_lease_id               | null                |
      | fulfillment_lease_until            | null                |
      | fulfillment_next_attempt           | {clock+60s}         |
      | fulfillment_error                  | "order_unavailable" |
      | fulfillment_order_paid             | <absent>            |
      | fulfillment_client_id              | <absent>            |
      | fulfillment_invoice_id             | <absent>            |
      | fulfillment_client_data_version_id | <absent>            |
      | fulfillment_completed_at           | <absent>            |
    And the worker performs exactly these HTTP operations
      | Field             | Value     |
      | Sequence          | order:500 |
      | LogicalPaidWrites | 0         |
      | LogicalInvoices   | 0         |
      | InvoiceVersion    | null      |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And the controlled downstream state changes to
      | Field       | Value     |
      | Mode        | ok        |
      | OrderStatus | unchanged |
      | ClientId    | unchanged |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 2                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                               |
      | Sequence          | order:200 paid:200 order:200 invoice:404 create:200 |
      | LogicalPaidWrites | 1                                                   |
      | LogicalInvoices   | 1                                                   |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333"              |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-04 Keep a rejected Paid write retryable until Paid is confirmed
    A rejected Paid request leaves the authoritative order Created. Its error response cannot prove commitment; invoice work does not begin.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value     |
      | Mode           | patch_409 |
      | PriorRetries   | 0         |
      | ReceiptFixture | none      |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-04"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                      |
      | _id                                | {before}                   |
      | event_type                         | {before}                   |
      | payload_digest                     | {before}                   |
      | outcome                            | {before}                   |
      | payment_id                         | {before}                   |
      | order_id                           | {before}                   |
      | attempt_id                         | {before}                   |
      | amount_minor                       | {before}                   |
      | currency                           | {before}                   |
      | session_id                         | {before}                   |
      | provider_payment_id                | {before}                   |
      | state                              | {before}                   |
      | reason                             | {before}                   |
      | received_at                        | {before}                   |
      | completed_at                       | {before}                   |
      | fulfillment_status                 | "retry"                    |
      | fulfillment_attempts               | 1                          |
      | fulfillment_lease_id               | null                       |
      | fulfillment_lease_until            | null                       |
      | fulfillment_next_attempt           | {clock+60s}                |
      | fulfillment_error                  | "order_update_unavailable" |
      | fulfillment_order_paid             | <absent>                   |
      | fulfillment_client_id              | <absent>                   |
      | fulfillment_invoice_id             | <absent>                   |
      | fulfillment_client_data_version_id | <absent>                   |
      | fulfillment_completed_at           | <absent>                   |
    And the worker performs exactly these HTTP operations
      | Field             | Value                        |
      | Sequence          | order:200 paid:409 order:200 |
      | LogicalPaidWrites | 0                            |
      | LogicalInvoices   | 0                            |
      | InvoiceVersion    | null                         |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-05 Reject a successful Paid response without authoritative Paid state
    A nominally successful Paid response leaves the order Created. Readback prevents invoice generation and schedules order_not_confirmed.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value             |
      | Mode           | patch_unconfirmed |
      | PriorRetries   | 0                 |
      | ReceiptFixture | none              |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-05"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                 |
      | _id                                | {before}              |
      | event_type                         | {before}              |
      | payload_digest                     | {before}              |
      | outcome                            | {before}              |
      | payment_id                         | {before}              |
      | order_id                           | {before}              |
      | attempt_id                         | {before}              |
      | amount_minor                       | {before}              |
      | currency                           | {before}              |
      | session_id                         | {before}              |
      | provider_payment_id                | {before}              |
      | state                              | {before}              |
      | reason                             | {before}              |
      | received_at                        | {before}              |
      | completed_at                       | {before}              |
      | fulfillment_status                 | "retry"               |
      | fulfillment_attempts               | 1                     |
      | fulfillment_lease_id               | null                  |
      | fulfillment_lease_until            | null                  |
      | fulfillment_next_attempt           | {clock+60s}           |
      | fulfillment_error                  | "order_not_confirmed" |
      | fulfillment_order_paid             | <absent>              |
      | fulfillment_client_id              | <absent>              |
      | fulfillment_invoice_id             | <absent>              |
      | fulfillment_client_data_version_id | <absent>              |
      | fulfillment_completed_at           | <absent>              |
    And the worker performs exactly these HTTP operations
      | Field             | Value                        |
      | Sequence          | order:200 paid:200 order:200 |
      | LogicalPaidWrites | 0                            |
      | LogicalInvoices   | 0                            |
      | InvoiceVersion    | null                         |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-06 Reconcile a Paid commit followed by a conflict acknowledgement
    Orders committed Paid before returning a conflict. The worker trusts the authoritative readback and completes one logical invoice without another Paid write.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value              |
      | Mode           | paid_409_committed |
      | PriorRetries   | 0                  |
      | ReceiptFixture | none               |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-06"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 1                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                               |
      | Sequence          | order:200 paid:409 order:200 invoice:404 create:200 |
      | LogicalPaidWrites | 1                                                   |
      | LogicalInvoices   | 1                                                   |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333"              |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-07 Recover an invoice reservation conflict after Paid progress
    A completed-only lookup misses an active invoice reservation and creation conflicts. Paid progress survives until a later available invoice creation can complete.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value       |
      | Mode           | invoice_409 |
      | PriorRetries   | 0           |
      | ReceiptFixture | none        |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-07"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                        |
      | _id                                | {before}                     |
      | event_type                         | {before}                     |
      | payload_digest                     | {before}                     |
      | outcome                            | {before}                     |
      | payment_id                         | {before}                     |
      | order_id                           | {before}                     |
      | attempt_id                         | {before}                     |
      | amount_minor                       | {before}                     |
      | currency                           | {before}                     |
      | session_id                         | {before}                     |
      | provider_payment_id                | {before}                     |
      | state                              | {before}                     |
      | reason                             | {before}                     |
      | received_at                        | {before}                     |
      | completed_at                       | {before}                     |
      | fulfillment_status                 | "retry"                      |
      | fulfillment_attempts               | 1                            |
      | fulfillment_lease_id               | null                         |
      | fulfillment_lease_until            | null                         |
      | fulfillment_next_attempt           | {clock+60s}                  |
      | fulfillment_error                  | "invoice_create_unavailable" |
      | fulfillment_order_paid             | true                         |
      | fulfillment_client_id              | {client.id}                  |
      | fulfillment_invoice_id             | <absent>                     |
      | fulfillment_client_data_version_id | <absent>                     |
      | fulfillment_completed_at           | <absent>                     |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                                           |
      | Sequence          | order:200 paid:200 order:200 invoice:404 create:409 invoice:404 |
      | LogicalPaidWrites | 1                                                               |
      | LogicalInvoices   | 0                                                               |
      | InvoiceVersion    | null                                                            |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And the controlled downstream state changes to
      | Field       | Value     |
      | Mode        | ok        |
      | OrderStatus | unchanged |
      | ClientId    | unchanged |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 2                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                  |
      | Sequence          | order:200 invoice:404 create:200       |
      | LogicalPaidWrites | 1                                      |
      | LogicalInvoices   | 1                                      |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333" |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-08 Recover after missing client data is repaired upstream
    Invoice creation reports unavailable client data after the order became Paid. Repair and a due retry complete the invoice without another Paid write.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value       |
      | Mode           | invoice_404 |
      | PriorRetries   | 0           |
      | ReceiptFixture | none        |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-08"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                        |
      | _id                                | {before}                     |
      | event_type                         | {before}                     |
      | payload_digest                     | {before}                     |
      | outcome                            | {before}                     |
      | payment_id                         | {before}                     |
      | order_id                           | {before}                     |
      | attempt_id                         | {before}                     |
      | amount_minor                       | {before}                     |
      | currency                           | {before}                     |
      | session_id                         | {before}                     |
      | provider_payment_id                | {before}                     |
      | state                              | {before}                     |
      | reason                             | {before}                     |
      | received_at                        | {before}                     |
      | completed_at                       | {before}                     |
      | fulfillment_status                 | "retry"                      |
      | fulfillment_attempts               | 1                            |
      | fulfillment_lease_id               | null                         |
      | fulfillment_lease_until            | null                         |
      | fulfillment_next_attempt           | {clock+60s}                  |
      | fulfillment_error                  | "invoice_create_unavailable" |
      | fulfillment_order_paid             | true                         |
      | fulfillment_client_id              | {client.id}                  |
      | fulfillment_invoice_id             | <absent>                     |
      | fulfillment_client_data_version_id | <absent>                     |
      | fulfillment_completed_at           | <absent>                     |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                                           |
      | Sequence          | order:200 paid:200 order:200 invoice:404 create:404 invoice:404 |
      | LogicalPaidWrites | 1                                                               |
      | LogicalInvoices   | 0                                                               |
      | InvoiceVersion    | null                                                            |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And the controlled downstream state changes to
      | Field       | Value     |
      | Mode        | ok        |
      | OrderStatus | unchanged |
      | ClientId    | unchanged |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 2                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                  |
      | Sequence          | order:200 invoice:404 create:200       |
      | LogicalPaidWrites | 1                                      |
      | LogicalInvoices   | 1                                      |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333" |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-09 Recover an unavailable invoice lookup without repeating Paid
    The order is already Paid when invoice lookup fails. The durable record retains Paid ownership and retries lookup before attempting creation.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value      |
      | Mode           | lookup_500 |
      | PriorRetries   | 0          |
      | ReceiptFixture | none       |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-09"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                        |
      | _id                                | {before}                     |
      | event_type                         | {before}                     |
      | payload_digest                     | {before}                     |
      | outcome                            | {before}                     |
      | payment_id                         | {before}                     |
      | order_id                           | {before}                     |
      | attempt_id                         | {before}                     |
      | amount_minor                       | {before}                     |
      | currency                           | {before}                     |
      | session_id                         | {before}                     |
      | provider_payment_id                | {before}                     |
      | state                              | {before}                     |
      | reason                             | {before}                     |
      | received_at                        | {before}                     |
      | completed_at                       | {before}                     |
      | fulfillment_status                 | "retry"                      |
      | fulfillment_attempts               | 1                            |
      | fulfillment_lease_id               | null                         |
      | fulfillment_lease_until            | null                         |
      | fulfillment_next_attempt           | {clock+60s}                  |
      | fulfillment_error                  | "invoice_lookup_unavailable" |
      | fulfillment_order_paid             | true                         |
      | fulfillment_client_id              | {client.id}                  |
      | fulfillment_invoice_id             | <absent>                     |
      | fulfillment_client_data_version_id | <absent>                     |
      | fulfillment_completed_at           | <absent>                     |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                    |
      | Sequence          | order:200 paid:200 order:200 invoice:500 |
      | LogicalPaidWrites | 1                                        |
      | LogicalInvoices   | 0                                        |
      | InvoiceVersion    | null                                     |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And the controlled downstream state changes to
      | Field       | Value     |
      | Mode        | ok        |
      | OrderStatus | unchanged |
      | ClientId    | unchanged |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 2                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                  |
      | Sequence          | order:200 invoice:404 create:200       |
      | LogicalPaidWrites | 1                                      |
      | LogicalInvoices   | 1                                      |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333" |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-10 Block unauthorized invoice lookup with safe durable state
    Invoice lookup is forbidden after Paid progress was saved. The worker records a safe permanent reason and preserves the successful payment.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value      |
      | Mode           | lookup_403 |
      | PriorRetries   | 0          |
      | ReceiptFixture | none       |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-10"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                         |
      | _id                                | {before}                      |
      | event_type                         | {before}                      |
      | payload_digest                     | {before}                      |
      | outcome                            | {before}                      |
      | payment_id                         | {before}                      |
      | order_id                           | {before}                      |
      | attempt_id                         | {before}                      |
      | amount_minor                       | {before}                      |
      | currency                           | {before}                      |
      | session_id                         | {before}                      |
      | provider_payment_id                | {before}                      |
      | state                              | {before}                      |
      | reason                             | {before}                      |
      | received_at                        | {before}                      |
      | completed_at                       | {before}                      |
      | fulfillment_status                 | "failed"                      |
      | fulfillment_attempts               | 1                             |
      | fulfillment_lease_id               | null                          |
      | fulfillment_lease_until            | null                          |
      | fulfillment_next_attempt           | null                          |
      | fulfillment_error                  | "invoice_lookup_unauthorized" |
      | fulfillment_order_paid             | true                          |
      | fulfillment_client_id              | {client.id}                   |
      | fulfillment_invoice_id             | <absent>                      |
      | fulfillment_client_data_version_id | <absent>                      |
      | fulfillment_completed_at           | <absent>                      |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                    |
      | Sequence          | order:200 paid:200 order:200 invoice:403 |
      | LogicalPaidWrites | 1                                        |
      | LogicalInvoices   | 0                                        |
      | InvoiceVersion    | null                                     |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-11 Block unauthorized invoice creation after completed-only reconciliation
    Invoice creation is forbidden and its readback remains missing. The safe permanent failure retains Paid progress and creates no invoice.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value      |
      | Mode           | create_403 |
      | PriorRetries   | 0          |
      | ReceiptFixture | none       |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-11"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                         |
      | _id                                | {before}                      |
      | event_type                         | {before}                      |
      | payload_digest                     | {before}                      |
      | outcome                            | {before}                      |
      | payment_id                         | {before}                      |
      | order_id                           | {before}                      |
      | attempt_id                         | {before}                      |
      | amount_minor                       | {before}                      |
      | currency                           | {before}                      |
      | session_id                         | {before}                      |
      | provider_payment_id                | {before}                      |
      | state                              | {before}                      |
      | reason                             | {before}                      |
      | received_at                        | {before}                      |
      | completed_at                       | {before}                      |
      | fulfillment_status                 | "failed"                      |
      | fulfillment_attempts               | 1                             |
      | fulfillment_lease_id               | null                          |
      | fulfillment_lease_until            | null                          |
      | fulfillment_next_attempt           | null                          |
      | fulfillment_error                  | "invoice_create_unauthorized" |
      | fulfillment_order_paid             | true                          |
      | fulfillment_client_id              | {client.id}                   |
      | fulfillment_invoice_id             | <absent>                      |
      | fulfillment_client_data_version_id | <absent>                      |
      | fulfillment_completed_at           | <absent>                      |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                                           |
      | Sequence          | order:200 paid:200 order:200 invoice:404 create:403 invoice:404 |
      | LogicalPaidWrites | 1                                                               |
      | LogicalInvoices   | 0                                                               |
      | InvoiceVersion    | null                                                            |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-12 Block an unauthorized order read before downstream writes
    The order read requires unavailable authorization. The worker records order_unauthorized without claiming Paid progress or contacting invoices.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value     |
      | Mode           | order_401 |
      | PriorRetries   | 0         |
      | ReceiptFixture | none      |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-12"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                |
      | _id                                | {before}             |
      | event_type                         | {before}             |
      | payload_digest                     | {before}             |
      | outcome                            | {before}             |
      | payment_id                         | {before}             |
      | order_id                           | {before}             |
      | attempt_id                         | {before}             |
      | amount_minor                       | {before}             |
      | currency                           | {before}             |
      | session_id                         | {before}             |
      | provider_payment_id                | {before}             |
      | state                              | {before}             |
      | reason                             | {before}             |
      | received_at                        | {before}             |
      | completed_at                       | {before}             |
      | fulfillment_status                 | "failed"             |
      | fulfillment_attempts               | 1                    |
      | fulfillment_lease_id               | null                 |
      | fulfillment_lease_until            | null                 |
      | fulfillment_next_attempt           | null                 |
      | fulfillment_error                  | "order_unauthorized" |
      | fulfillment_order_paid             | <absent>             |
      | fulfillment_client_id              | <absent>             |
      | fulfillment_invoice_id             | <absent>             |
      | fulfillment_client_data_version_id | <absent>             |
      | fulfillment_completed_at           | <absent>             |
    And the worker performs exactly these HTTP operations
      | Field             | Value     |
      | Sequence          | order:401 |
      | LogicalPaidWrites | 0         |
      | LogicalInvoices   | 0         |
      | InvoiceVersion    | null      |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-13 Block an authoritative order with different exact money
    The upstream order total differs from the paid amount by one minor unit. Full receipt and Payment evidence prove no Paid or invoice write occurred.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value        |
      | Mode           | wrong_amount |
      | PriorRetries   | 0            |
      | ReceiptFixture | none         |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-13"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value            |
      | _id                                | {before}         |
      | event_type                         | {before}         |
      | payload_digest                     | {before}         |
      | outcome                            | {before}         |
      | payment_id                         | {before}         |
      | order_id                           | {before}         |
      | attempt_id                         | {before}         |
      | amount_minor                       | {before}         |
      | currency                           | {before}         |
      | session_id                         | {before}         |
      | provider_payment_id                | {before}         |
      | state                              | {before}         |
      | reason                             | {before}         |
      | received_at                        | {before}         |
      | completed_at                       | {before}         |
      | fulfillment_status                 | "failed"         |
      | fulfillment_attempts               | 1                |
      | fulfillment_lease_id               | null             |
      | fulfillment_lease_until            | null             |
      | fulfillment_next_attempt           | null             |
      | fulfillment_error                  | "order_mismatch" |
      | fulfillment_order_paid             | <absent>         |
      | fulfillment_client_id              | <absent>         |
      | fulfillment_invoice_id             | <absent>         |
      | fulfillment_client_data_version_id | <absent>         |
      | fulfillment_completed_at           | <absent>         |
    And the worker performs exactly these HTTP operations
      | Field             | Value     |
      | Sequence          | order:200 |
      | LogicalPaidWrites | 0         |
      | LogicalInvoices   | 0         |
      | InvoiceVersion    | null      |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-14 Block a canceled authoritative order without undoing payment
    A successful payment now targets an authoritative Cancelled order. The worker requires operator repair and does not refund or mutate the payment.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value     |
      | Mode           | cancelled |
      | PriorRetries   | 0         |
      | ReceiptFixture | none      |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-14"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value               |
      | _id                                | {before}            |
      | event_type                         | {before}            |
      | payload_digest                     | {before}            |
      | outcome                            | {before}            |
      | payment_id                         | {before}            |
      | order_id                           | {before}            |
      | attempt_id                         | {before}            |
      | amount_minor                       | {before}            |
      | currency                           | {before}            |
      | session_id                         | {before}            |
      | provider_payment_id                | {before}            |
      | state                              | {before}            |
      | reason                             | {before}            |
      | received_at                        | {before}            |
      | completed_at                       | {before}            |
      | fulfillment_status                 | "failed"            |
      | fulfillment_attempts               | 1                   |
      | fulfillment_lease_id               | null                |
      | fulfillment_lease_until            | null                |
      | fulfillment_next_attempt           | null                |
      | fulfillment_error                  | "order_not_payable" |
      | fulfillment_order_paid             | <absent>            |
      | fulfillment_client_id              | <absent>            |
      | fulfillment_invoice_id             | <absent>            |
      | fulfillment_client_data_version_id | <absent>            |
      | fulfillment_completed_at           | <absent>            |
    And the worker performs exactly these HTTP operations
      | Field             | Value     |
      | Sequence          | order:200 |
      | LogicalPaidWrites | 0         |
      | LogicalInvoices   | 0         |
      | InvoiceVersion    | null      |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-15 Reject completed invoice metadata for another order
    A completed invoice lookup returns invalid ownership or version metadata. The real adapter blocks completion, keeps safe state and issues no invoice create.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value              |
      | Mode           | lookup_wrong_order |
      | PriorRetries   | 0                  |
      | ReceiptFixture | none               |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-15"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                      |
      | _id                                | {before}                   |
      | event_type                         | {before}                   |
      | payload_digest                     | {before}                   |
      | outcome                            | {before}                   |
      | payment_id                         | {before}                   |
      | order_id                           | {before}                   |
      | attempt_id                         | {before}                   |
      | amount_minor                       | {before}                   |
      | currency                           | {before}                   |
      | session_id                         | {before}                   |
      | provider_payment_id                | {before}                   |
      | state                              | {before}                   |
      | reason                             | {before}                   |
      | received_at                        | {before}                   |
      | completed_at                       | {before}                   |
      | fulfillment_status                 | "failed"                   |
      | fulfillment_attempts               | 1                          |
      | fulfillment_lease_id               | null                       |
      | fulfillment_lease_until            | null                       |
      | fulfillment_next_attempt           | null                       |
      | fulfillment_error                  | "invoice_invalid_response" |
      | fulfillment_order_paid             | true                       |
      | fulfillment_client_id              | {client.id}                |
      | fulfillment_invoice_id             | <absent>                   |
      | fulfillment_client_data_version_id | <absent>                   |
      | fulfillment_completed_at           | <absent>                   |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                  |
      | Sequence          | order:200 invoice:200                  |
      | LogicalPaidWrites | 0                                      |
      | LogicalInvoices   | 0                                      |
      | InvoiceVersion    | "44444444-4444-4444-8444-444444444444" |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-16 Reject a zero client data version in completed metadata
    A completed invoice lookup returns invalid ownership or version metadata. The real adapter blocks completion, keeps safe state and issues no invoice create.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value               |
      | Mode           | lookup_zero_version |
      | PriorRetries   | 0                   |
      | ReceiptFixture | none                |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-16"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                      |
      | _id                                | {before}                   |
      | event_type                         | {before}                   |
      | payload_digest                     | {before}                   |
      | outcome                            | {before}                   |
      | payment_id                         | {before}                   |
      | order_id                           | {before}                   |
      | attempt_id                         | {before}                   |
      | amount_minor                       | {before}                   |
      | currency                           | {before}                   |
      | session_id                         | {before}                   |
      | provider_payment_id                | {before}                   |
      | state                              | {before}                   |
      | reason                             | {before}                   |
      | received_at                        | {before}                   |
      | completed_at                       | {before}                   |
      | fulfillment_status                 | "failed"                   |
      | fulfillment_attempts               | 1                          |
      | fulfillment_lease_id               | null                       |
      | fulfillment_lease_until            | null                       |
      | fulfillment_next_attempt           | null                       |
      | fulfillment_error                  | "invoice_invalid_response" |
      | fulfillment_order_paid             | true                       |
      | fulfillment_client_id              | {client.id}                |
      | fulfillment_invoice_id             | <absent>                   |
      | fulfillment_client_data_version_id | <absent>                   |
      | fulfillment_completed_at           | <absent>                   |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                  |
      | Sequence          | order:200 invoice:200                  |
      | LogicalPaidWrites | 0                                      |
      | LogicalInvoices   | 0                                      |
      | InvoiceVersion    | "44444444-4444-4444-8444-444444444444" |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-17 Block historical work referring to a missing payment
    An explicitly prepared historical ledger association differs from the persisted successful payment. The worker rejects it before any downstream request and preserves all payment/history records.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value           |
      | Mode           | ok              |
      | PriorRetries   | 0               |
      | ReceiptFixture | missing_payment |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-17"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value              |
      | _id                                | {before}           |
      | event_type                         | {before}           |
      | payload_digest                     | {before}           |
      | outcome                            | {before}           |
      | payment_id                         | {before}           |
      | order_id                           | {before}           |
      | attempt_id                         | {before}           |
      | amount_minor                       | {before}           |
      | currency                           | {before}           |
      | session_id                         | {before}           |
      | provider_payment_id                | {before}           |
      | state                              | {before}           |
      | reason                             | {before}           |
      | received_at                        | {before}           |
      | completed_at                       | {before}           |
      | fulfillment_status                 | "failed"           |
      | fulfillment_attempts               | 1                  |
      | fulfillment_lease_id               | null               |
      | fulfillment_lease_until            | null               |
      | fulfillment_next_attempt           | null               |
      | fulfillment_error                  | "payment_mismatch" |
      | fulfillment_order_paid             | <absent>           |
      | fulfillment_client_id              | <absent>           |
      | fulfillment_invoice_id             | <absent>           |
      | fulfillment_client_data_version_id | <absent>           |
      | fulfillment_completed_at           | <absent>           |
    And the worker performs exactly these HTTP operations
      | Field             | Value  |
      | Sequence          | <none> |
      | LogicalPaidWrites | 0      |
      | LogicalInvoices   | 0      |
      | InvoiceVersion    | null   |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-18 Block historical work referring to another attempt
    An explicitly prepared historical ledger association differs from the persisted successful payment. The worker rejects it before any downstream request and preserves all payment/history records.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value         |
      | Mode           | ok            |
      | PriorRetries   | 0             |
      | ReceiptFixture | stale_attempt |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-18"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value              |
      | _id                                | {before}           |
      | event_type                         | {before}           |
      | payload_digest                     | {before}           |
      | outcome                            | {before}           |
      | payment_id                         | {before}           |
      | order_id                           | {before}           |
      | attempt_id                         | {before}           |
      | amount_minor                       | {before}           |
      | currency                           | {before}           |
      | session_id                         | {before}           |
      | provider_payment_id                | {before}           |
      | state                              | {before}           |
      | reason                             | {before}           |
      | received_at                        | {before}           |
      | completed_at                       | {before}           |
      | fulfillment_status                 | "failed"           |
      | fulfillment_attempts               | 1                  |
      | fulfillment_lease_id               | null               |
      | fulfillment_lease_until            | null               |
      | fulfillment_next_attempt           | null               |
      | fulfillment_error                  | "payment_mismatch" |
      | fulfillment_order_paid             | <absent>           |
      | fulfillment_client_id              | <absent>           |
      | fulfillment_invoice_id             | <absent>           |
      | fulfillment_client_data_version_id | <absent>           |
      | fulfillment_completed_at           | <absent>           |
    And the worker performs exactly these HTTP operations
      | Field             | Value  |
      | Sequence          | <none> |
      | LogicalPaidWrites | 0      |
      | LogicalInvoices   | 0      |
      | InvoiceVersion    | null   |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-19 Block ownership changes after Paid progress
    An invoice failure first saves authoritative Paid progress. A later changed owner or regressed order cannot overwrite that saved association during retry.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value       |
      | Mode           | pdf_failure |
      | PriorRetries   | 0           |
      | ReceiptFixture | none        |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-19"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                        |
      | _id                                | {before}                     |
      | event_type                         | {before}                     |
      | payload_digest                     | {before}                     |
      | outcome                            | {before}                     |
      | payment_id                         | {before}                     |
      | order_id                           | {before}                     |
      | attempt_id                         | {before}                     |
      | amount_minor                       | {before}                     |
      | currency                           | {before}                     |
      | session_id                         | {before}                     |
      | provider_payment_id                | {before}                     |
      | state                              | {before}                     |
      | reason                             | {before}                     |
      | received_at                        | {before}                     |
      | completed_at                       | {before}                     |
      | fulfillment_status                 | "retry"                      |
      | fulfillment_attempts               | 1                            |
      | fulfillment_lease_id               | null                         |
      | fulfillment_lease_until            | null                         |
      | fulfillment_next_attempt           | {clock+60s}                  |
      | fulfillment_error                  | "invoice_create_unavailable" |
      | fulfillment_order_paid             | true                         |
      | fulfillment_client_id              | {client.id}                  |
      | fulfillment_invoice_id             | <absent>                     |
      | fulfillment_client_data_version_id | <absent>                     |
      | fulfillment_completed_at           | <absent>                     |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                                           |
      | Sequence          | order:200 paid:200 order:200 invoice:404 create:500 invoice:404 |
      | LogicalPaidWrites | 1                                                               |
      | LogicalInvoices   | 0                                                               |
      | InvoiceVersion    | null                                                            |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And the controlled downstream state changes to
      | Field       | Value                                |
      | Mode        | ok                                   |
      | OrderStatus | unchanged                            |
      | ClientId    | 88888888-8888-4888-8888-888888888888 |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                 |
      | _id                                | {before}              |
      | event_type                         | {before}              |
      | payload_digest                     | {before}              |
      | outcome                            | {before}              |
      | payment_id                         | {before}              |
      | order_id                           | {before}              |
      | attempt_id                         | {before}              |
      | amount_minor                       | {before}              |
      | currency                           | {before}              |
      | session_id                         | {before}              |
      | provider_payment_id                | {before}              |
      | state                              | {before}              |
      | reason                             | {before}              |
      | received_at                        | {before}              |
      | completed_at                       | {before}              |
      | fulfillment_status                 | "failed"              |
      | fulfillment_attempts               | 2                     |
      | fulfillment_lease_id               | null                  |
      | fulfillment_lease_until            | null                  |
      | fulfillment_next_attempt           | null                  |
      | fulfillment_error                  | "order_owner_changed" |
      | fulfillment_order_paid             | true                  |
      | fulfillment_client_id              | {client.id}           |
      | fulfillment_invoice_id             | <absent>              |
      | fulfillment_client_data_version_id | <absent>              |
      | fulfillment_completed_at           | <absent>              |
    And the worker performs exactly these HTTP operations
      | Field             | Value     |
      | Sequence          | order:200 |
      | LogicalPaidWrites | 1         |
      | LogicalInvoices   | 0         |
      | InvoiceVersion    | null      |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-20 Block regressed Created state after Paid progress
    An invoice failure first saves authoritative Paid progress. A later changed owner or regressed order cannot overwrite that saved association during retry.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value       |
      | Mode           | pdf_failure |
      | PriorRetries   | 0           |
      | ReceiptFixture | none        |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-20"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                        |
      | _id                                | {before}                     |
      | event_type                         | {before}                     |
      | payload_digest                     | {before}                     |
      | outcome                            | {before}                     |
      | payment_id                         | {before}                     |
      | order_id                           | {before}                     |
      | attempt_id                         | {before}                     |
      | amount_minor                       | {before}                     |
      | currency                           | {before}                     |
      | session_id                         | {before}                     |
      | provider_payment_id                | {before}                     |
      | state                              | {before}                     |
      | reason                             | {before}                     |
      | received_at                        | {before}                     |
      | completed_at                       | {before}                     |
      | fulfillment_status                 | "retry"                      |
      | fulfillment_attempts               | 1                            |
      | fulfillment_lease_id               | null                         |
      | fulfillment_lease_until            | null                         |
      | fulfillment_next_attempt           | {clock+60s}                  |
      | fulfillment_error                  | "invoice_create_unavailable" |
      | fulfillment_order_paid             | true                         |
      | fulfillment_client_id              | {client.id}                  |
      | fulfillment_invoice_id             | <absent>                     |
      | fulfillment_client_data_version_id | <absent>                     |
      | fulfillment_completed_at           | <absent>                     |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                                           |
      | Sequence          | order:200 paid:200 order:200 invoice:404 create:500 invoice:404 |
      | LogicalPaidWrites | 1                                                               |
      | LogicalInvoices   | 0                                                               |
      | InvoiceVersion    | null                                                            |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And the controlled downstream state changes to
      | Field       | Value     |
      | Mode        | ok        |
      | OrderStatus | Created   |
      | ClientId    | unchanged |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                   |
      | _id                                | {before}                |
      | event_type                         | {before}                |
      | payload_digest                     | {before}                |
      | outcome                            | {before}                |
      | payment_id                         | {before}                |
      | order_id                           | {before}                |
      | attempt_id                         | {before}                |
      | amount_minor                       | {before}                |
      | currency                           | {before}                |
      | session_id                         | {before}                |
      | provider_payment_id                | {before}                |
      | state                              | {before}                |
      | reason                             | {before}                |
      | received_at                        | {before}                |
      | completed_at                       | {before}                |
      | fulfillment_status                 | "failed"                |
      | fulfillment_attempts               | 2                       |
      | fulfillment_lease_id               | null                    |
      | fulfillment_lease_until            | null                    |
      | fulfillment_next_attempt           | null                    |
      | fulfillment_error                  | "order_state_regressed" |
      | fulfillment_order_paid             | true                    |
      | fulfillment_client_id              | {client.id}             |
      | fulfillment_invoice_id             | <absent>                |
      | fulfillment_client_data_version_id | <absent>                |
      | fulfillment_completed_at           | <absent>                |
    And the worker performs exactly these HTTP operations
      | Field             | Value     |
      | Sequence          | order:200 |
      | LogicalPaidWrites | 1         |
      | LogicalInvoices   | 0         |
      | InvoiceVersion    | null      |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-21 Do not claim invoice retry one millisecond before its deadline
    A PDF-boundary failure leaves persisted Paid retry state. Running one millisecond before its due time processes zero and preserves every field and upstream record.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value       |
      | Mode           | pdf_failure |
      | PriorRetries   | 0           |
      | ReceiptFixture | none        |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-21"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                        |
      | _id                                | {before}                     |
      | event_type                         | {before}                     |
      | payload_digest                     | {before}                     |
      | outcome                            | {before}                     |
      | payment_id                         | {before}                     |
      | order_id                           | {before}                     |
      | attempt_id                         | {before}                     |
      | amount_minor                       | {before}                     |
      | currency                           | {before}                     |
      | session_id                         | {before}                     |
      | provider_payment_id                | {before}                     |
      | state                              | {before}                     |
      | reason                             | {before}                     |
      | received_at                        | {before}                     |
      | completed_at                       | {before}                     |
      | fulfillment_status                 | "retry"                      |
      | fulfillment_attempts               | 1                            |
      | fulfillment_lease_id               | null                         |
      | fulfillment_lease_until            | null                         |
      | fulfillment_next_attempt           | {clock+60s}                  |
      | fulfillment_error                  | "invoice_create_unavailable" |
      | fulfillment_order_paid             | true                         |
      | fulfillment_client_id              | {client.id}                  |
      | fulfillment_invoice_id             | <absent>                     |
      | fulfillment_client_data_version_id | <absent>                     |
      | fulfillment_completed_at           | <absent>                     |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                                           |
      | Sequence          | order:200 paid:200 order:200 invoice:404 create:500 invoice:404 |
      | LogicalPaidWrites | 1                                                               |
      | LogicalInvoices   | 0                                                               |
      | InvoiceVersion    | null                                                            |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    When the durable fulfillment command runs
      | Field     | Value      |
      | Limit     | 100        |
      | Clock     | before_due |
      | Processed | 0          |
    And the complete durable fulfillment record is
      | Field                              | Value                        |
      | _id                                | {before}                     |
      | event_type                         | {before}                     |
      | payload_digest                     | {before}                     |
      | outcome                            | {before}                     |
      | payment_id                         | {before}                     |
      | order_id                           | {before}                     |
      | attempt_id                         | {before}                     |
      | amount_minor                       | {before}                     |
      | currency                           | {before}                     |
      | session_id                         | {before}                     |
      | provider_payment_id                | {before}                     |
      | state                              | {before}                     |
      | reason                             | {before}                     |
      | received_at                        | {before}                     |
      | completed_at                       | {before}                     |
      | fulfillment_status                 | "retry"                      |
      | fulfillment_attempts               | 1                            |
      | fulfillment_lease_id               | null                         |
      | fulfillment_lease_until            | null                         |
      | fulfillment_next_attempt           | {before}                     |
      | fulfillment_error                  | "invoice_create_unavailable" |
      | fulfillment_order_paid             | true                         |
      | fulfillment_client_id              | {client.id}                  |
      | fulfillment_invoice_id             | <absent>                     |
      | fulfillment_client_data_version_id | <absent>                     |
      | fulfillment_completed_at           | <absent>                     |
    And the worker performs exactly these HTTP operations
      | Field             | Value  |
      | Sequence          | <none> |
      | LogicalPaidWrites | 1      |
      | LogicalInvoices   | 0      |
      | InvoiceVersion    | null   |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-22 Persist the third retry exponential delay
    Earlier retry attempts execute through the real worker with isolated application time. The next due attempt increments the durable count and records its exact bounded deadline.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value     |
      | Mode           | order_500 |
      | PriorRetries   | 2         |
      | ReceiptFixture | none      |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-22"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value               |
      | _id                                | {before}            |
      | event_type                         | {before}            |
      | payload_digest                     | {before}            |
      | outcome                            | {before}            |
      | payment_id                         | {before}            |
      | order_id                           | {before}            |
      | attempt_id                         | {before}            |
      | amount_minor                       | {before}            |
      | currency                           | {before}            |
      | session_id                         | {before}            |
      | provider_payment_id                | {before}            |
      | state                              | {before}            |
      | reason                             | {before}            |
      | received_at                        | {before}            |
      | completed_at                       | {before}            |
      | fulfillment_status                 | "retry"             |
      | fulfillment_attempts               | 3                   |
      | fulfillment_lease_id               | null                |
      | fulfillment_lease_until            | null                |
      | fulfillment_next_attempt           | {clock+240s}        |
      | fulfillment_error                  | "order_unavailable" |
      | fulfillment_order_paid             | <absent>            |
      | fulfillment_client_id              | <absent>            |
      | fulfillment_invoice_id             | <absent>            |
      | fulfillment_client_data_version_id | <absent>            |
      | fulfillment_completed_at           | <absent>            |
    And the worker performs exactly these HTTP operations
      | Field             | Value     |
      | Sequence          | order:500 |
      | LogicalPaidWrites | 0         |
      | LogicalInvoices   | 0         |
      | InvoiceVersion    | null      |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-23 Cap the eighth retry delay at one hour
    Earlier retry attempts execute through the real worker with isolated application time. The next due attempt increments the durable count and records its exact bounded deadline.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value     |
      | Mode           | order_500 |
      | PriorRetries   | 7         |
      | ReceiptFixture | none      |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-23"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value               |
      | _id                                | {before}            |
      | event_type                         | {before}            |
      | payload_digest                     | {before}            |
      | outcome                            | {before}            |
      | payment_id                         | {before}            |
      | order_id                           | {before}            |
      | attempt_id                         | {before}            |
      | amount_minor                       | {before}            |
      | currency                           | {before}            |
      | session_id                         | {before}            |
      | provider_payment_id                | {before}            |
      | state                              | {before}            |
      | reason                             | {before}            |
      | received_at                        | {before}            |
      | completed_at                       | {before}            |
      | fulfillment_status                 | "retry"             |
      | fulfillment_attempts               | 8                   |
      | fulfillment_lease_id               | null                |
      | fulfillment_lease_until            | null                |
      | fulfillment_next_attempt           | {clock+3600s}       |
      | fulfillment_error                  | "order_unavailable" |
      | fulfillment_order_paid             | <absent>            |
      | fulfillment_client_id              | <absent>            |
      | fulfillment_invoice_id             | <absent>            |
      | fulfillment_client_data_version_id | <absent>            |
      | fulfillment_completed_at           | <absent>            |
    And the worker performs exactly these HTTP operations
      | Field             | Value     |
      | Sequence          | order:500 |
      | LogicalPaidWrites | 0         |
      | LogicalInvoices   | 0         |
      | InvoiceVersion    | null      |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-24 Exhaust the tenth real retry into failed work
    Nine earlier unavailable-order attempts ran and persisted deadlines. The tenth attempt records Failed with no future deadline and preserves every successful Payment field.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value     |
      | Mode           | order_500 |
      | PriorRetries   | 9         |
      | ReceiptFixture | none      |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-24"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value               |
      | _id                                | {before}            |
      | event_type                         | {before}            |
      | payload_digest                     | {before}            |
      | outcome                            | {before}            |
      | payment_id                         | {before}            |
      | order_id                           | {before}            |
      | attempt_id                         | {before}            |
      | amount_minor                       | {before}            |
      | currency                           | {before}            |
      | session_id                         | {before}            |
      | provider_payment_id                | {before}            |
      | state                              | {before}            |
      | reason                             | {before}            |
      | received_at                        | {before}            |
      | completed_at                       | {before}            |
      | fulfillment_status                 | "failed"            |
      | fulfillment_attempts               | 10                  |
      | fulfillment_lease_id               | null                |
      | fulfillment_lease_until            | null                |
      | fulfillment_next_attempt           | null                |
      | fulfillment_error                  | "order_unavailable" |
      | fulfillment_order_paid             | <absent>            |
      | fulfillment_client_id              | <absent>            |
      | fulfillment_invoice_id             | <absent>            |
      | fulfillment_client_data_version_id | <absent>            |
      | fulfillment_completed_at           | <absent>            |
    And the worker performs exactly these HTTP operations
      | Field             | Value     |
      | Sequence          | order:500 |
      | LogicalPaidWrites | 0         |
      | LogicalInvoices   | 0         |
      | InvoiceVersion    | null      |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-25 Reject an over-limit historical attempt before downstream calls
    A historical pending marker already records ten attempts. Its next claim records retry_exhausted without issuing any downstream request.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value        |
      | Mode           | ok           |
      | PriorRetries   | 0            |
      | ReceiptFixture | attempts_ten |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-25"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "failed"          |
      | fulfillment_attempts               | 11                |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | "retry_exhausted" |
      | fulfillment_order_paid             | <absent>          |
      | fulfillment_client_id              | <absent>          |
      | fulfillment_invoice_id             | <absent>          |
      | fulfillment_client_data_version_id | <absent>          |
      | fulfillment_completed_at           | <absent>          |
    And the worker performs exactly these HTTP operations
      | Field             | Value  |
      | Sequence          | <none> |
      | LogicalPaidWrites | 0      |
      | LogicalInvoices   | 0      |
      | InvoiceVersion    | null   |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-26 Recover a local paid before persistence interruption
    A controlled repository-boundary interruption happens before or after actual durable progress. A due retry in a fresh worker reconciles existing upstream state without another logical Paid or invoice.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value |
      | Mode           | ok    |
      | PriorRetries   | 0     |
      | ReceiptFixture | none  |
    And I remember complete fulfillment state
    And local fulfillment persistence is interrupted
      | Field | Value       |
      | Point | paid_before |
    Then the response matches case "PAY09-26"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                     |
      | _id                                | {before}                  |
      | event_type                         | {before}                  |
      | payload_digest                     | {before}                  |
      | outcome                            | {before}                  |
      | payment_id                         | {before}                  |
      | order_id                           | {before}                  |
      | attempt_id                         | {before}                  |
      | amount_minor                       | {before}                  |
      | currency                           | {before}                  |
      | session_id                         | {before}                  |
      | provider_payment_id                | {before}                  |
      | state                              | {before}                  |
      | reason                             | {before}                  |
      | received_at                        | {before}                  |
      | completed_at                       | {before}                  |
      | fulfillment_status                 | "retry"                   |
      | fulfillment_attempts               | 1                         |
      | fulfillment_lease_id               | null                      |
      | fulfillment_lease_until            | null                      |
      | fulfillment_next_attempt           | {clock+60s}               |
      | fulfillment_error                  | "fulfillment_unavailable" |
      | fulfillment_order_paid             | <absent>                  |
      | fulfillment_client_id              | <absent>                  |
      | fulfillment_invoice_id             | <absent>                  |
      | fulfillment_client_data_version_id | <absent>                  |
      | fulfillment_completed_at           | <absent>                  |
    And the worker performs exactly these HTTP operations
      | Field             | Value                        |
      | Sequence          | order:200 paid:200 order:200 |
      | LogicalPaidWrites | 1                            |
      | LogicalInvoices   | 0                            |
      | InvoiceVersion    | null                         |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And the controlled downstream state changes to
      | Field       | Value     |
      | Mode        | ok        |
      | OrderStatus | unchanged |
      | ClientId    | unchanged |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 2                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                  |
      | Sequence          | order:200 invoice:404 create:200       |
      | LogicalPaidWrites | 1                                      |
      | LogicalInvoices   | 1                                      |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333" |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-27 Recover a local paid after persistence interruption
    A controlled repository-boundary interruption happens before or after actual durable progress. A due retry in a fresh worker reconciles existing upstream state without another logical Paid or invoice.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value |
      | Mode           | ok    |
      | PriorRetries   | 0     |
      | ReceiptFixture | none  |
    And I remember complete fulfillment state
    And local fulfillment persistence is interrupted
      | Field | Value      |
      | Point | paid_after |
    Then the response matches case "PAY09-27"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                     |
      | _id                                | {before}                  |
      | event_type                         | {before}                  |
      | payload_digest                     | {before}                  |
      | outcome                            | {before}                  |
      | payment_id                         | {before}                  |
      | order_id                           | {before}                  |
      | attempt_id                         | {before}                  |
      | amount_minor                       | {before}                  |
      | currency                           | {before}                  |
      | session_id                         | {before}                  |
      | provider_payment_id                | {before}                  |
      | state                              | {before}                  |
      | reason                             | {before}                  |
      | received_at                        | {before}                  |
      | completed_at                       | {before}                  |
      | fulfillment_status                 | "retry"                   |
      | fulfillment_attempts               | 1                         |
      | fulfillment_lease_id               | null                      |
      | fulfillment_lease_until            | null                      |
      | fulfillment_next_attempt           | {clock+60s}               |
      | fulfillment_error                  | "fulfillment_unavailable" |
      | fulfillment_order_paid             | true                      |
      | fulfillment_client_id              | {client.id}               |
      | fulfillment_invoice_id             | <absent>                  |
      | fulfillment_client_data_version_id | <absent>                  |
      | fulfillment_completed_at           | <absent>                  |
    And the worker performs exactly these HTTP operations
      | Field             | Value                        |
      | Sequence          | order:200 paid:200 order:200 |
      | LogicalPaidWrites | 1                            |
      | LogicalInvoices   | 0                            |
      | InvoiceVersion    | null                         |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And the controlled downstream state changes to
      | Field       | Value     |
      | Mode        | ok        |
      | OrderStatus | unchanged |
      | ClientId    | unchanged |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 2                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                  |
      | Sequence          | order:200 invoice:404 create:200       |
      | LogicalPaidWrites | 1                                      |
      | LogicalInvoices   | 1                                      |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333" |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-28 Recover a local complete before persistence interruption
    A controlled repository-boundary interruption happens before or after actual durable progress. A due retry in a fresh worker reconciles existing upstream state without another logical Paid or invoice.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value |
      | Mode           | ok    |
      | PriorRetries   | 0     |
      | ReceiptFixture | none  |
    And I remember complete fulfillment state
    And local fulfillment persistence is interrupted
      | Field | Value           |
      | Point | complete_before |
    Then the response matches case "PAY09-28"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                     |
      | _id                                | {before}                  |
      | event_type                         | {before}                  |
      | payload_digest                     | {before}                  |
      | outcome                            | {before}                  |
      | payment_id                         | {before}                  |
      | order_id                           | {before}                  |
      | attempt_id                         | {before}                  |
      | amount_minor                       | {before}                  |
      | currency                           | {before}                  |
      | session_id                         | {before}                  |
      | provider_payment_id                | {before}                  |
      | state                              | {before}                  |
      | reason                             | {before}                  |
      | received_at                        | {before}                  |
      | completed_at                       | {before}                  |
      | fulfillment_status                 | "retry"                   |
      | fulfillment_attempts               | 1                         |
      | fulfillment_lease_id               | null                      |
      | fulfillment_lease_until            | null                      |
      | fulfillment_next_attempt           | {clock+60s}               |
      | fulfillment_error                  | "fulfillment_unavailable" |
      | fulfillment_order_paid             | true                      |
      | fulfillment_client_id              | {client.id}               |
      | fulfillment_invoice_id             | <absent>                  |
      | fulfillment_client_data_version_id | <absent>                  |
      | fulfillment_completed_at           | <absent>                  |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                               |
      | Sequence          | order:200 paid:200 order:200 invoice:404 create:200 |
      | LogicalPaidWrites | 1                                                   |
      | LogicalInvoices   | 1                                                   |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333"              |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And the controlled downstream state changes to
      | Field       | Value     |
      | Mode        | ok        |
      | OrderStatus | unchanged |
      | ClientId    | unchanged |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 2                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                  |
      | Sequence          | order:200 invoice:200                  |
      | LogicalPaidWrites | 1                                      |
      | LogicalInvoices   | 1                                      |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333" |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-29 Keep committed completion after a lost local acknowledgement
    The real local completion write commits before its acknowledgement is lost. Failure fencing preserves Completed state, and another worker processes zero without downstream writes.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value |
      | Mode           | ok    |
      | PriorRetries   | 0     |
      | ReceiptFixture | none  |
    And I remember complete fulfillment state
    And local fulfillment persistence is interrupted
      | Field | Value          |
      | Point | complete_after |
    Then the response matches case "PAY09-29"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 1                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                               |
      | Sequence          | order:200 paid:200 order:200 invoice:404 create:200 |
      | LogicalPaidWrites | 1                                                   |
      | LogicalInvoices   | 1                                                   |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333"              |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 0     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 1                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {before}          |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                  |
      | Sequence          | <none>                                 |
      | LogicalPaidWrites | 1                                      |
      | LogicalInvoices   | 1                                      |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333" |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-30 Resume repaired failed work while preserving Paid progress
    Forbidden invoice creation leaves Failed work with Paid progress. The explicit operator resume resets attempt scheduling and later completes one invoice without another Paid write.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value      |
      | Mode           | create_403 |
      | PriorRetries   | 0          |
      | ReceiptFixture | none       |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-30"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value                         |
      | _id                                | {before}                      |
      | event_type                         | {before}                      |
      | payload_digest                     | {before}                      |
      | outcome                            | {before}                      |
      | payment_id                         | {before}                      |
      | order_id                           | {before}                      |
      | attempt_id                         | {before}                      |
      | amount_minor                       | {before}                      |
      | currency                           | {before}                      |
      | session_id                         | {before}                      |
      | provider_payment_id                | {before}                      |
      | state                              | {before}                      |
      | reason                             | {before}                      |
      | received_at                        | {before}                      |
      | completed_at                       | {before}                      |
      | fulfillment_status                 | "failed"                      |
      | fulfillment_attempts               | 1                             |
      | fulfillment_lease_id               | null                          |
      | fulfillment_lease_until            | null                          |
      | fulfillment_next_attempt           | null                          |
      | fulfillment_error                  | "invoice_create_unauthorized" |
      | fulfillment_order_paid             | true                          |
      | fulfillment_client_id              | {client.id}                   |
      | fulfillment_invoice_id             | <absent>                      |
      | fulfillment_client_data_version_id | <absent>                      |
      | fulfillment_completed_at           | <absent>                      |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                                           |
      | Sequence          | order:200 paid:200 order:200 invoice:404 create:403 invoice:404 |
      | LogicalPaidWrites | 1                                                               |
      | LogicalInvoices   | 0                                                               |
      | InvoiceVersion    | null                                                            |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And the controlled downstream state changes to
      | Field       | Value     |
      | Mode        | ok        |
      | OrderStatus | unchanged |
      | ClientId    | unchanged |
    And the operator resumes repaired fulfillment with
      | Field                | Value |
      | Result               | 1     |
      | PreservePaidProgress | true  |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 1                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                  |
      | Sequence          | order:200 invoice:404 create:200       |
      | LogicalPaidWrites | 1                                      |
      | LogicalInvoices   | 1                                      |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333" |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-31 Leave exhausted work untouched without explicit resume
    Ten real failures exhausted the work before the primary batch. A later worker processes zero and cannot silently reopen the failed record.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value     |
      | Mode           | order_500 |
      | PriorRetries   | 10        |
      | ReceiptFixture | none      |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-31"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 0     |
    And the complete durable fulfillment record is
      | Field                              | Value               |
      | _id                                | {before}            |
      | event_type                         | {before}            |
      | payload_digest                     | {before}            |
      | outcome                            | {before}            |
      | payment_id                         | {before}            |
      | order_id                           | {before}            |
      | attempt_id                         | {before}            |
      | amount_minor                       | {before}            |
      | currency                           | {before}            |
      | session_id                         | {before}            |
      | provider_payment_id                | {before}            |
      | state                              | {before}            |
      | reason                             | {before}            |
      | received_at                        | {before}            |
      | completed_at                       | {before}            |
      | fulfillment_status                 | "failed"            |
      | fulfillment_attempts               | 10                  |
      | fulfillment_lease_id               | null                |
      | fulfillment_lease_until            | null                |
      | fulfillment_next_attempt           | null                |
      | fulfillment_error                  | "order_unavailable" |
      | fulfillment_order_paid             | <absent>            |
      | fulfillment_client_id              | <absent>            |
      | fulfillment_invoice_id             | <absent>            |
      | fulfillment_client_data_version_id | <absent>            |
      | fulfillment_completed_at           | <absent>            |
    And the worker performs exactly these HTTP operations
      | Field             | Value  |
      | Sequence          | <none> |
      | LogicalPaidWrites | 0      |
      | LogicalInvoices   | 0      |
      | InvoiceVersion    | null   |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY09-32 Reconcile malformed create acknowledgement against a completed lookup
    Invoice creation commits canonical metadata but its immediate response omits storage. A completed-only lookup validates the committed invoice and finishes once.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And unrelated fulfillment has completed through the worker
    And verified fulfillment work is prepared
      | Field          | Value          |
      | Mode           | create_invalid |
      | PriorRetries   | 0              |
      | ReceiptFixture | none           |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-32"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 1     |
    And the complete durable fulfillment record is
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 1                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the worker performs exactly these HTTP operations
      | Field             | Value                                                           |
      | Sequence          | order:200 paid:200 order:200 invoice:404 create:200 invoice:200 |
      | LogicalPaidWrites | 1                                                               |
      | LogicalInvoices   | 1                                                               |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333"                          |
    And the complete payment read after fulfillment is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "succeeded"         |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | "pi_fixture"        |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
