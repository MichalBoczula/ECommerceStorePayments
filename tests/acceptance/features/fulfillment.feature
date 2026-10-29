Feature: Durable fulfillment of verified checkout payments

  Scenario: PAY23-01 Fulfillment reconciles ok
    A verified successful webhook schedules durable fulfillment. The worker marks the order Paid, completes one invoice and safely handles redelivery.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a verified successful checkout with fulfillment mode "ok"
    And I remember complete fulfillment state
    Then the response matches case "PAY23-01"
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
    Then one paid order and one completed invoice are recorded
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
    When the successful webhook is delivered again
    And the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 0     |
    Then fulfillment stays completed without repeating downstream writes
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

  Scenario: PAY23-02 Fulfillment reconciles paid_ack_lost
    Orders commits Paid but loses its completion acknowledgement. The worker reconciles the committed state and completes one invoice without another Paid write.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a verified successful checkout with fulfillment mode "paid_ack_lost"
    And I remember complete fulfillment state
    Then the response matches case "PAY23-02"
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
    Then one paid order and one completed invoice are recorded
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
      | Field             | Value                                                       |
      | Sequence          | order:200 paid:ReadTimeout order:200 invoice:404 create:200 |
      | LogicalPaidWrites | 1                                                           |
      | LogicalInvoices   | 1                                                           |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333"                      |
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
    When the successful webhook is delivered again
    And the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 0     |
    Then fulfillment stays completed without repeating downstream writes
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

  Scenario: PAY23-03 Fulfillment reconciles invoice_ack_lost
    Invoice creation commits but loses its completion acknowledgement. The worker discovers the existing invoice and finishes durable fulfillment safely.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a verified successful checkout with fulfillment mode "invoice_ack_lost"
    And I remember complete fulfillment state
    Then the response matches case "PAY23-03"
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
    Then one paid order and one completed invoice are recorded
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
      | Field             | Value                                                                   |
      | Sequence          | order:200 paid:200 order:200 invoice:404 create:ReadTimeout invoice:200 |
      | LogicalPaidWrites | 1                                                                       |
      | LogicalInvoices   | 1                                                                       |
      | InvoiceVersion    | "33333333-3333-4333-8333-333333333333"                                  |
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
    When the successful webhook is delivered again
    And the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | now   |
      | Processed | 0     |
    Then fulfillment stays completed without repeating downstream writes
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

  Scenario: PAY23-04 PDF failure remains recoverable after the order is paid
    Invoice PDF generation fails after the order is already Paid. Durable retry later completes the invoice without repeating the Paid write.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a verified successful checkout with fulfillment mode "pdf_failure"
    And I remember complete fulfillment state
    Then the response matches case "PAY23-04"
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
    Then the order is paid and invoice fulfillment is scheduled for retry
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
    When the invoice retry becomes due and the durable fulfillment command runs
      | Field     | Value |
      | Limit     | 100   |
      | Clock     | due   |
      | Processed | 1     |
    Then one paid order and one completed invoice are recorded
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
