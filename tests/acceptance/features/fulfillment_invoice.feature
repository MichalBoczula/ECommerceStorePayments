Feature: Published Invoice fulfillment and real PDF recovery

  Scenario: PAY09-33 Complete a published Invoice and download its real PDF
    A signed payment schedules work against the pinned published Invoice image. The actual API marks Paid, selects the latest client data version and streams the exact stored generated PDF.
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
    And the published Invoice service is prepared
      | Field          | Value                                                                   |
      | Mode           | ok                                                                      |
      | ImageDigest    | sha256:6e9244804a2645f8aecaff89f60cff03337a94b70ca877195e585c678f2d996a |
      | TimeoutSeconds | 30                                                                      |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-33"
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
    And the completed published invoice PDF is
      | Field              | Value                                |
      | ContentType        | application/pdf                      |
      | ContentDisposition | attachment; invoice-{invoice.id}.pdf |
      | Magic              | %PDF-                                |
      | EOF                | %%EOF                                |
      | MinimumBytes       | 1000                                 |
      | StoredBytesMatch   | true                                 |
      | CompletedInvoices  | 1                                    |
      | DataVersion        | 33333333-3333-4333-8333-333333333333 |
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

  Scenario: PAY09-34 Recover a lost real Paid acknowledgement
    The published Orders API commits Paid before a controlled transport loses its response. Authoritative readback completes one real invoice and its downloadable PDF.
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
    And the published Invoice service is prepared
      | Field          | Value                                                                   |
      | Mode           | paid_ack_lost                                                           |
      | ImageDigest    | sha256:6e9244804a2645f8aecaff89f60cff03337a94b70ca877195e585c678f2d996a |
      | TimeoutSeconds | 30                                                                      |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-34"
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
    And the completed published invoice PDF is
      | Field              | Value                                |
      | ContentType        | application/pdf                      |
      | ContentDisposition | attachment; invoice-{invoice.id}.pdf |
      | Magic              | %PDF-                                |
      | EOF                | %%EOF                                |
      | MinimumBytes       | 1000                                 |
      | StoredBytesMatch   | true                                 |
      | CompletedInvoices  | 1                                    |
      | DataVersion        | 33333333-3333-4333-8333-333333333333 |
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

  Scenario: PAY09-35 Recover a lost real invoice creation acknowledgement
    The published Invoice API commits its generated PDF and metadata before a controlled transport loses the response. Completed-only lookup recovers the same invoice and exact stored bytes.
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
    And the published Invoice service is prepared
      | Field          | Value                                                                   |
      | Mode           | invoice_ack_lost                                                        |
      | ImageDigest    | sha256:6e9244804a2645f8aecaff89f60cff03337a94b70ca877195e585c678f2d996a |
      | TimeoutSeconds | 30                                                                      |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-35"
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
    And the completed published invoice PDF is
      | Field              | Value                                |
      | ContentType        | application/pdf                      |
      | ContentDisposition | attachment; invoice-{invoice.id}.pdf |
      | Magic              | %PDF-                                |
      | EOF                | %%EOF                                |
      | MinimumBytes       | 1000                                 |
      | StoredBytesMatch   | true                                 |
      | CompletedInvoices  | 1                                    |
      | DataVersion        | 33333333-3333-4333-8333-333333333333 |
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

  Scenario: PAY09-36 Recover a real PDF storage failure after Paid
    A file blocks the disposable published service PDF directory. Real generation fails and releases its reservation; repair and a due worker retry reuse the invoice identity and produce the downloadable PDF.
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
    And the published Invoice service is prepared
      | Field          | Value                                                                   |
      | Mode           | pdf_storage_failure                                                     |
      | ImageDigest    | sha256:6e9244804a2645f8aecaff89f60cff03337a94b70ca877195e585c678f2d996a |
      | TimeoutSeconds | 30                                                                      |
    And I remember complete fulfillment state
    Then the response matches case "PAY09-36"
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
    And the published PDF storage path is repaired
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
    And the completed published invoice PDF is
      | Field              | Value                                |
      | ContentType        | application/pdf                      |
      | ContentDisposition | attachment; invoice-{invoice.id}.pdf |
      | Magic              | %PDF-                                |
      | EOF                | %%EOF                                |
      | MinimumBytes       | 1000                                 |
      | StoredBytesMatch   | true                                 |
      | CompletedInvoices  | 1                                    |
      | DataVersion        | 33333333-3333-4333-8333-333333333333 |
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
      | fulfillment_attempts               | 2                 |
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
