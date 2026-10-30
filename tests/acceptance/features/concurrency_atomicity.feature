Feature: Deterministic concurrency and real atomicity

  Scenario: PAY12-01 Keep the complete pending winner after a stale repository write
    Both commands load version zero and mutate their own aggregate before either real transaction runs. The selected write commits; the stale command throws the actual PaymentConflictError and cannot alter the complete winner or its archive.
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
    And the coordinated target starts "created"
    And the real write schedule is
      | Field  | Value              |
      | Mode   | repository-pending |
      | Winner | first              |
    When two stale repository commands follow the schedule
    Then the response matches case "PAY12-01"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
    And the coordinated payment responses are
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "pending"                              |
      | provider_session_id | "cs_coordinated"                       |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And the coordinated database effects are
      | Field         | Value   |
      | Status        | pending |
      | Version       | 1       |
      | NewArchives   | 1       |
      | NewReceipts   | 0       |
      | OrdersCalls   | 0       |
      | StripeCalls   | 0       |
      | Conflicts     | 1       |
      | SessionsAdded | 0       |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-02 Keep the complete canceled winner after a stale repository write
    Both commands load version zero and mutate their own aggregate before either real transaction runs. The selected write commits; the stale command throws the actual PaymentConflictError and cannot alter the complete winner or its archive.
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
    And the coordinated target starts "created"
    And the real write schedule is
      | Field  | Value               |
      | Mode   | repository-canceled |
      | Winner | second              |
    When two stale repository commands follow the schedule
    Then the response matches case "PAY12-02"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
    And the coordinated payment responses are
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "canceled"                             |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And the coordinated database effects are
      | Field         | Value    |
      | Status        | canceled |
      | Version       | 1        |
      | NewArchives   | 1        |
      | NewReceipts   | 0        |
      | OrdersCalls   | 0        |
      | StripeCalls   | 0        |
      | Conflicts     | 1        |
      | SessionsAdded | 0        |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-03 Let the first Pay insertion win after both reads were empty
    Both first Pay requests reach the real create boundary with distinct candidate payment IDs. The selected insert commits, the other hits the actual unique order index, and both complete responses identify the exact surviving payment.
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
    And the coordinated target starts "absent"
    And the real write schedule is
      | Field  | Value      |
      | Mode   | pay-create |
      | Winner | first      |
    When two real Pay requests follow the schedule
    Then the response matches case "PAY12-03"
      | Field        | Value            |
      | HTTPStatuses | 200,201          |
      | ContentType  | application/json |
      | Code         | -                |
    And the coordinated payment responses are
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And the coordinated database effects are
      | Field         | Value   |
      | Status        | created |
      | Version       | 0       |
      | NewArchives   | 0       |
      | NewReceipts   | 0       |
      | OrdersCalls   | 2       |
      | StripeCalls   | 0       |
      | Conflicts     | 1       |
      | SessionsAdded | 0       |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-04 Let the second Pay insertion win after both reads were empty
    Both first Pay requests reach the real create boundary with distinct candidate payment IDs. The selected insert commits, the other hits the actual unique order index, and both complete responses identify the exact surviving payment.
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
    And the coordinated target starts "absent"
    And the real write schedule is
      | Field  | Value      |
      | Mode   | pay-create |
      | Winner | second     |
    When two real Pay requests follow the schedule
    Then the response matches case "PAY12-04"
      | Field        | Value            |
      | HTTPStatuses | 200,201          |
      | ContentType  | application/json |
      | Code         | -                |
    And the coordinated payment responses are
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And the coordinated database effects are
      | Field         | Value   |
      | Status        | created |
      | Version       | 0       |
      | NewArchives   | 0       |
      | NewReceipts   | 0       |
      | OrdersCalls   | 2       |
      | StripeCalls   | 0       |
      | Conflicts     | 1       |
      | SessionsAdded | 0       |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-05 Retry one failed version once under competing Pay requests
    Both requests load the same terminal version and validate the unchanged order before either update. One reset and one exact archive commit; the stale real write conflicts and the API returns the full winner with provider and attempt fields cleared.
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
    And the coordinated target starts "failed"
    And the real write schedule is
      | Field  | Value     |
      | Mode   | pay-retry |
      | Winner | first     |
    When two real Pay requests follow the schedule
    Then the response matches case "PAY12-05"
      | Field        | Value            |
      | HTTPStatuses | 200,200          |
      | ContentType  | application/json |
      | Code         | -                |
    And the coordinated payment responses are
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And the coordinated database effects are
      | Field         | Value   |
      | Status        | created |
      | Version       | 4       |
      | NewArchives   | 1       |
      | NewReceipts   | 0       |
      | OrdersCalls   | 2       |
      | StripeCalls   | 0       |
      | Conflicts     | 1       |
      | SessionsAdded | 0       |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-06 Retry one canceled version once under competing Pay requests
    Both requests load the same terminal version and validate the unchanged order before either update. One reset and one exact archive commit; the stale real write conflicts and the API returns the full winner with provider and attempt fields cleared.
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
    And the coordinated target starts "canceled"
    And the real write schedule is
      | Field  | Value     |
      | Mode   | pay-retry |
      | Winner | second    |
    When two real Pay requests follow the schedule
    Then the response matches case "PAY12-06"
      | Field        | Value            |
      | HTTPStatuses | 200,200          |
      | ContentType  | application/json |
      | Code         | -                |
    And the coordinated payment responses are
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And the coordinated database effects are
      | Field         | Value   |
      | Status        | created |
      | Version       | 4       |
      | NewArchives   | 1       |
      | NewReceipts   | 0       |
      | OrdersCalls   | 2       |
      | StripeCalls   | 0       |
      | Conflicts     | 1       |
      | SessionsAdded | 0       |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-07 Keep the first Checkout reservation and one provider session
    Both requests propose distinct attempts at version zero. The chosen real reservation commits; the stale reservation reloads it. Both real SDK creates use the same full encoded form and key, and a second stale write cannot replace the complete Pending winner or add an extra archive.
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
    And the coordinated target starts "created"
    And the real write schedule is
      | Field  | Value    |
      | Mode   | checkout |
      | Winner | first    |
    When two real Checkout requests follow the schedule
    Then the response matches case "PAY12-07"
      | Field                     | Value            |
      | HTTPStatuses              | 200,200          |
      | ContentType               | application/json |
      | Code                      | -                |
      | JSON.payment.status       | "pending"        |
      | JSON.payment.amount_minor | 1299             |
      | JSON.payment.currency     | "PLN"            |
    And the coordinated checkout responses are
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}           |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the coordinated provider requests are
      | Field                                              | Value                                         |
      | Method                                             | POST                                          |
      | Path                                               | /v1/checkout/sessions                         |
      | StripeVersion                                      | 2026-08-26.dahlia                             |
      | ContentType                                        | application/x-www-form-urlencoded             |
      | IdempotencyKey                                     | checkout:{payment.id}:{attempt.id}            |
      | form.mode                                          | payment                                       |
      | form.payment_method_types[0]                       | card                                          |
      | form.payment_method_types[1]                       | blik                                          |
      | form.client_reference_id                           | {payment.id}                                  |
      | form.metadata[payment_id]                          | {payment.id}                                  |
      | form.metadata[order_id]                            | {order.id}                                    |
      | form.metadata[attempt_id]                          | {attempt.id}                                  |
      | form.payment_intent_data[metadata][payment_id]     | {payment.id}                                  |
      | form.payment_intent_data[metadata][order_id]       | {order.id}                                    |
      | form.payment_intent_data[metadata][attempt_id]     | {attempt.id}                                  |
      | form.success_url                                   | http://localhost:4200/orders?checkout=success |
      | form.cancel_url                                    | http://localhost:4200/orders?checkout=cancel  |
      | form.line_items[0][quantity]                       | 1                                             |
      | form.line_items[0][price_data][currency]           | pln                                           |
      | form.line_items[0][price_data][unit_amount]        | 1299                                          |
      | form.line_items[0][price_data][product_data][name] | Order {order.id}                              |
    And the coordinated database effects are
      | Field         | Value   |
      | Status        | pending |
      | Version       | 2       |
      | NewArchives   | 2       |
      | NewReceipts   | 0       |
      | OrdersCalls   | 2       |
      | StripeCalls   | 2       |
      | Conflicts     | 2       |
      | SessionsAdded | 1       |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-08 Keep the second Checkout reservation and one provider session
    Both requests propose distinct attempts at version zero. The chosen real reservation commits; the stale reservation reloads it. Both real SDK creates use the same full encoded form and key, and a second stale write cannot replace the complete Pending winner or add an extra archive.
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
    And the coordinated target starts "created"
    And the real write schedule is
      | Field  | Value    |
      | Mode   | checkout |
      | Winner | second   |
    When two real Checkout requests follow the schedule
    Then the response matches case "PAY12-08"
      | Field                     | Value            |
      | HTTPStatuses              | 200,200          |
      | ContentType               | application/json |
      | Code                      | -                |
      | JSON.payment.status       | "pending"        |
      | JSON.payment.amount_minor | 1299             |
      | JSON.payment.currency     | "PLN"            |
    And the coordinated checkout responses are
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}           |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the coordinated provider requests are
      | Field                                              | Value                                         |
      | Method                                             | POST                                          |
      | Path                                               | /v1/checkout/sessions                         |
      | StripeVersion                                      | 2026-08-26.dahlia                             |
      | ContentType                                        | application/x-www-form-urlencoded             |
      | IdempotencyKey                                     | checkout:{payment.id}:{attempt.id}            |
      | form.mode                                          | payment                                       |
      | form.payment_method_types[0]                       | card                                          |
      | form.payment_method_types[1]                       | blik                                          |
      | form.client_reference_id                           | {payment.id}                                  |
      | form.metadata[payment_id]                          | {payment.id}                                  |
      | form.metadata[order_id]                            | {order.id}                                    |
      | form.metadata[attempt_id]                          | {attempt.id}                                  |
      | form.payment_intent_data[metadata][payment_id]     | {payment.id}                                  |
      | form.payment_intent_data[metadata][order_id]       | {order.id}                                    |
      | form.payment_intent_data[metadata][attempt_id]     | {attempt.id}                                  |
      | form.success_url                                   | http://localhost:4200/orders?checkout=success |
      | form.cancel_url                                    | http://localhost:4200/orders?checkout=cancel  |
      | form.line_items[0][quantity]                       | 1                                             |
      | form.line_items[0][price_data][currency]           | pln                                           |
      | form.line_items[0][price_data][unit_amount]        | 1299                                          |
      | form.line_items[0][price_data][product_data][name] | Order {order.id}                              |
    And the coordinated database effects are
      | Field         | Value   |
      | Status        | pending |
      | Version       | 2       |
      | NewArchives   | 2       |
      | NewReceipts   | 0       |
      | OrdersCalls   | 2       |
      | StripeCalls   | 2       |
      | Conflicts     | 2       |
      | SessionsAdded | 1       |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-09 Coordinate same deliveries with first first
    Both signed requests load the same Pending version and reach completion before either transaction starts. The selected commit is fully captured; duplicate or stale real completion follows the existing receipt/retry policy. Success remains authoritative, exact archives/receipts survive and repeated deliveries preserve every field.
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
    And the coordinated target starts "pending"
    And the real write schedule is
      | Field  | Value        |
      | Mode   | webhook-same |
      | Winner | first        |
    When two signed webhook requests follow the schedule
    Then the response matches case "PAY12-09"
      | Field        | Value            |
      | HTTPStatuses | 200,200          |
      | ContentType  | application/json |
      | Code         | -                |
    And the first coordinated receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "succeeded"                 |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "applied"                   |
      | reason              | "payment_succeeded"         |
      | received_at         | {request.window}            |
      | completed_at        | {request.window}            |
      | fulfillment_status  | "pending"                   |
    And the second coordinated receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "succeeded"                 |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "applied"                   |
      | reason              | "payment_succeeded"         |
      | received_at         | {request.window}            |
      | completed_at        | {request.window}            |
      | fulfillment_status  | "pending"                   |
    And the coordinated database effects are
      | Field         | Value     |
      | Status        | succeeded |
      | Version       | 3         |
      | NewArchives   | 1         |
      | NewReceipts   | 1         |
      | OrdersCalls   | 0         |
      | StripeCalls   | 0         |
      | Conflicts     | 0         |
      | SessionsAdded | 0         |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-10 Coordinate same deliveries with second first
    Both signed requests load the same Pending version and reach completion before either transaction starts. The selected commit is fully captured; duplicate or stale real completion follows the existing receipt/retry policy. Success remains authoritative, exact archives/receipts survive and repeated deliveries preserve every field.
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
    And the coordinated target starts "pending"
    And the real write schedule is
      | Field  | Value        |
      | Mode   | webhook-same |
      | Winner | second       |
    When two signed webhook requests follow the schedule
    Then the response matches case "PAY12-10"
      | Field        | Value            |
      | HTTPStatuses | 200,200          |
      | ContentType  | application/json |
      | Code         | -                |
    And the first coordinated receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "succeeded"                 |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "applied"                   |
      | reason              | "payment_succeeded"         |
      | received_at         | {request.window}            |
      | completed_at        | {request.window}            |
      | fulfillment_status  | "pending"                   |
    And the second coordinated receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "succeeded"                 |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "applied"                   |
      | reason              | "payment_succeeded"         |
      | received_at         | {request.window}            |
      | completed_at        | {request.window}            |
      | fulfillment_status  | "pending"                   |
    And the coordinated database effects are
      | Field         | Value     |
      | Status        | succeeded |
      | Version       | 3         |
      | NewArchives   | 1         |
      | NewReceipts   | 1         |
      | OrdersCalls   | 0         |
      | StripeCalls   | 0         |
      | Conflicts     | 0         |
      | SessionsAdded | 0         |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-11 Coordinate distinct deliveries with first first
    Both signed requests load the same Pending version and reach completion before either transaction starts. The selected commit is fully captured; duplicate or stale real completion follows the existing receipt/retry policy. Success remains authoritative, exact archives/receipts survive and repeated deliveries preserve every field.
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
    And the coordinated target starts "pending"
    And the real write schedule is
      | Field  | Value            |
      | Mode   | webhook-distinct |
      | Winner | first            |
    When two signed webhook requests follow the schedule
    Then the response matches case "PAY12-11"
      | Field        | Value            |
      | HTTPStatuses | 200,200          |
      | ContentType  | application/json |
      | Code         | -                |
    And the first coordinated receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "succeeded"                 |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "applied"                   |
      | reason              | "payment_succeeded"         |
      | received_at         | {request.window}            |
      | completed_at        | {request.window}            |
      | fulfillment_status  | "pending"                   |
    And the second coordinated receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "succeeded"                 |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "ignored"                   |
      | reason              | "already_succeeded"         |
      | received_at         | {request.window}            |
      | completed_at        | {request.window}            |
      | fulfillment_status  | null                        |
    And the coordinated database effects are
      | Field         | Value     |
      | Status        | succeeded |
      | Version       | 3         |
      | NewArchives   | 1         |
      | NewReceipts   | 2         |
      | OrdersCalls   | 0         |
      | StripeCalls   | 0         |
      | Conflicts     | 1         |
      | SessionsAdded | 0         |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-12 Coordinate distinct deliveries with second first
    Both signed requests load the same Pending version and reach completion before either transaction starts. The selected commit is fully captured; duplicate or stale real completion follows the existing receipt/retry policy. Success remains authoritative, exact archives/receipts survive and repeated deliveries preserve every field.
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
    And the coordinated target starts "pending"
    And the real write schedule is
      | Field  | Value            |
      | Mode   | webhook-distinct |
      | Winner | second           |
    When two signed webhook requests follow the schedule
    Then the response matches case "PAY12-12"
      | Field        | Value            |
      | HTTPStatuses | 200,200          |
      | ContentType  | application/json |
      | Code         | -                |
    And the first coordinated receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "succeeded"                 |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "ignored"                   |
      | reason              | "already_succeeded"         |
      | received_at         | {request.window}            |
      | completed_at        | {request.window}            |
      | fulfillment_status  | null                        |
    And the second coordinated receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "succeeded"                 |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "applied"                   |
      | reason              | "payment_succeeded"         |
      | received_at         | {request.window}            |
      | completed_at        | {request.window}            |
      | fulfillment_status  | "pending"                   |
    And the coordinated database effects are
      | Field         | Value     |
      | Status        | succeeded |
      | Version       | 3         |
      | NewArchives   | 1         |
      | NewReceipts   | 2         |
      | OrdersCalls   | 0         |
      | StripeCalls   | 0         |
      | Conflicts     | 1         |
      | SessionsAdded | 0         |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-13 Coordinate success-first deliveries with first first
    Both signed requests load the same Pending version and reach completion before either transaction starts. The selected commit is fully captured; duplicate or stale real completion follows the existing receipt/retry policy. Success remains authoritative, exact archives/receipts survive and repeated deliveries preserve every field.
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
    And the coordinated target starts "pending"
    And the real write schedule is
      | Field  | Value                 |
      | Mode   | webhook-success-first |
      | Winner | first                 |
    When two signed webhook requests follow the schedule
    Then the response matches case "PAY12-13"
      | Field        | Value            |
      | HTTPStatuses | 200,200          |
      | ContentType  | application/json |
      | Code         | -                |
    And the first coordinated receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "succeeded"                 |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "applied"                   |
      | reason              | "payment_succeeded"         |
      | received_at         | {request.window}            |
      | completed_at        | {request.window}            |
      | fulfillment_status  | "pending"                   |
    And the second coordinated receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "expired"                   |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "ignored"                   |
      | reason              | "already_succeeded"         |
      | received_at         | {request.window}            |
      | completed_at        | {request.window}            |
      | fulfillment_status  | null                        |
    And the coordinated database effects are
      | Field         | Value     |
      | Status        | succeeded |
      | Version       | 3         |
      | NewArchives   | 1         |
      | NewReceipts   | 2         |
      | OrdersCalls   | 0         |
      | StripeCalls   | 0         |
      | Conflicts     | 1         |
      | SessionsAdded | 0         |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-14 Coordinate expiry-first deliveries with second first
    Both signed requests load the same Pending version and reach completion before either transaction starts. The selected commit is fully captured; duplicate or stale real completion follows the existing receipt/retry policy. Success remains authoritative, exact archives/receipts survive and repeated deliveries preserve every field.
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
    And the coordinated target starts "pending"
    And the real write schedule is
      | Field  | Value                |
      | Mode   | webhook-expiry-first |
      | Winner | second               |
    When two signed webhook requests follow the schedule
    Then the response matches case "PAY12-14"
      | Field        | Value            |
      | HTTPStatuses | 200,200          |
      | ContentType  | application/json |
      | Code         | -                |
    And the first coordinated receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "succeeded"                 |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "applied"                   |
      | reason              | "payment_succeeded"         |
      | received_at         | {request.window}            |
      | completed_at        | {request.window}            |
      | fulfillment_status  | "pending"                   |
    And the second coordinated receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "expired"                   |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "applied"                   |
      | reason              | "payment_failed"            |
      | received_at         | {request.window}            |
      | completed_at        | {request.window}            |
      | fulfillment_status  | null                        |
    And the coordinated database effects are
      | Field         | Value     |
      | Status        | succeeded |
      | Version       | 4         |
      | NewArchives   | 2         |
      | NewReceipts   | 2         |
      | OrdersCalls   | 0         |
      | StripeCalls   | 0         |
      | Conflicts     | 1         |
      | SessionsAdded | 0         |
    And supporting reads and repeats preserve the coordinated result

  Scenario: PAY12-15 Abort checkout after the real payments.replace_one write
    The scoped decorator awaits the actual MongoDB write inside its real session, records all session-visible collections and proves outside readers still see the complete populated baseline. An explicit post-write OperationFailure aborts the transaction; a fresh real HTTP retry succeeds without leaking a staged attempt, archive or fulfillment marker.
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
    And the coordinated target starts "created"
    And the post-write rollback boundary is
      | Field      | Value                |
      | Command    | checkout             |
      | AfterWrite | payments.replace_one |
      | Exception  | OperationFailure     |
    When the public request reaches the real post-write fault
    Then the response matches case "PAY12-15"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 500                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | internal_error                                            |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Internal Server Error"                                   |
      | JSON.status            | 500                                                       |
      | JSON.detail            | "An unexpected error occurred."                           |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And the real abort preserves this populated state
      | Field                    | Value     |
      | WritesReached            | 1         |
      | TransactionActiveAtFault | true      |
      | SessionEnded             | true      |
      | Collections              | unchanged |
      | OrdersCalls              | 1         |
      | StripeCalls              | 0         |
      | ProviderSessions         | unchanged |
    When the fault is removed and the public request is retried
    Then the recovered checkout response is
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}           |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovered checkout provider request is
      | Field                                              | Value                                         |
      | Method                                             | POST                                          |
      | Path                                               | /v1/checkout/sessions                         |
      | StripeVersion                                      | 2026-08-26.dahlia                             |
      | ContentType                                        | application/x-www-form-urlencoded             |
      | IdempotencyKey                                     | checkout:{payment.id}:{attempt.id}            |
      | form.mode                                          | payment                                       |
      | form.payment_method_types[0]                       | card                                          |
      | form.payment_method_types[1]                       | blik                                          |
      | form.client_reference_id                           | {payment.id}                                  |
      | form.metadata[payment_id]                          | {payment.id}                                  |
      | form.metadata[order_id]                            | {order.id}                                    |
      | form.metadata[attempt_id]                          | {attempt.id}                                  |
      | form.payment_intent_data[metadata][payment_id]     | {payment.id}                                  |
      | form.payment_intent_data[metadata][order_id]       | {order.id}                                    |
      | form.payment_intent_data[metadata][attempt_id]     | {attempt.id}                                  |
      | form.success_url                                   | http://localhost:4200/orders?checkout=success |
      | form.cancel_url                                    | http://localhost:4200/orders?checkout=cancel  |
      | form.line_items[0][quantity]                       | 1                                             |
      | form.line_items[0][price_data][currency]           | pln                                           |
      | form.line_items[0][price_data][unit_amount]        | 1299                                          |
      | form.line_items[0][price_data][product_data][name] | Order {order.id}                              |
    And supporting requests preserve the post-abort recovery

  Scenario: PAY12-16 Abort checkout after the real payment_history.insert_one write
    The scoped decorator awaits the actual MongoDB write inside its real session, records all session-visible collections and proves outside readers still see the complete populated baseline. An explicit post-write OperationFailure aborts the transaction; a fresh real HTTP retry succeeds without leaking a staged attempt, archive or fulfillment marker.
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
    And the coordinated target starts "created"
    And the post-write rollback boundary is
      | Field      | Value                      |
      | Command    | checkout                   |
      | AfterWrite | payment_history.insert_one |
      | Exception  | OperationFailure           |
    When the public request reaches the real post-write fault
    Then the response matches case "PAY12-16"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 500                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | internal_error                                            |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Internal Server Error"                                   |
      | JSON.status            | 500                                                       |
      | JSON.detail            | "An unexpected error occurred."                           |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And the real abort preserves this populated state
      | Field                    | Value     |
      | WritesReached            | 2         |
      | TransactionActiveAtFault | true      |
      | SessionEnded             | true      |
      | Collections              | unchanged |
      | OrdersCalls              | 1         |
      | StripeCalls              | 0         |
      | ProviderSessions         | unchanged |
    When the fault is removed and the public request is retried
    Then the recovered checkout response is
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}           |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovered checkout provider request is
      | Field                                              | Value                                         |
      | Method                                             | POST                                          |
      | Path                                               | /v1/checkout/sessions                         |
      | StripeVersion                                      | 2026-08-26.dahlia                             |
      | ContentType                                        | application/x-www-form-urlencoded             |
      | IdempotencyKey                                     | checkout:{payment.id}:{attempt.id}            |
      | form.mode                                          | payment                                       |
      | form.payment_method_types[0]                       | card                                          |
      | form.payment_method_types[1]                       | blik                                          |
      | form.client_reference_id                           | {payment.id}                                  |
      | form.metadata[payment_id]                          | {payment.id}                                  |
      | form.metadata[order_id]                            | {order.id}                                    |
      | form.metadata[attempt_id]                          | {attempt.id}                                  |
      | form.payment_intent_data[metadata][payment_id]     | {payment.id}                                  |
      | form.payment_intent_data[metadata][order_id]       | {order.id}                                    |
      | form.payment_intent_data[metadata][attempt_id]     | {attempt.id}                                  |
      | form.success_url                                   | http://localhost:4200/orders?checkout=success |
      | form.cancel_url                                    | http://localhost:4200/orders?checkout=cancel  |
      | form.line_items[0][quantity]                       | 1                                             |
      | form.line_items[0][price_data][currency]           | pln                                           |
      | form.line_items[0][price_data][unit_amount]        | 1299                                          |
      | form.line_items[0][price_data][product_data][name] | Order {order.id}                              |
    And supporting requests preserve the post-abort recovery

  Scenario: PAY12-17 Abort webhook after the real payments.replace_one write
    The scoped decorator awaits the actual MongoDB write inside its real session, records all session-visible collections and proves outside readers still see the complete populated baseline. An explicit post-write OperationFailure aborts the transaction; a fresh real HTTP retry succeeds without leaking a staged attempt, archive or fulfillment marker.
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
    And the coordinated target starts "pending"
    And the post-write rollback boundary is
      | Field      | Value                |
      | Command    | webhook              |
      | AfterWrite | payments.replace_one |
      | Exception  | OperationFailure     |
    When the public request reaches the real post-write fault
    Then the response matches case "PAY12-17"
      | Field                  | Value                                 |
      | HTTPStatuses           | 503                                   |
      | ContentType            | application/problem+json              |
      | Code                   | webhook_retry                         |
      | JSON.type              | "about:blank"                         |
      | JSON.title             | "Service Unavailable"                 |
      | JSON.status            | 503                                   |
      | JSON.detail            | "Webhook processing must be retried." |
      | JSON.instance          | "/payments/webhooks/stripe"           |
      | JSON.errors            | []                                    |
      | JSON.missingProperties | []                                    |
    And the real abort preserves this populated state
      | Field                    | Value     |
      | WritesReached            | 1         |
      | TransactionActiveAtFault | true      |
      | SessionEnded             | true      |
      | Collections              | unchanged |
      | OrdersCalls              | 0         |
      | StripeCalls              | 0         |
      | ProviderSessions         | unchanged |
    When the fault is removed and the public request is retried
    Then the recovered webhook receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "succeeded"                 |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "applied"                   |
      | reason              | "payment_succeeded"         |
      | received_at         | {before.received_at}        |
      | completed_at        | {request.window}            |
      | fulfillment_status  | "pending"                   |
    And the complete payment after webhook rollback recovery is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | {stored.session_id}                    |
      | provider_payment_id | "pi_fixture"                           |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And supporting requests preserve the post-abort recovery

  Scenario: PAY12-18 Abort webhook after the real payment_history.insert_one write
    The scoped decorator awaits the actual MongoDB write inside its real session, records all session-visible collections and proves outside readers still see the complete populated baseline. An explicit post-write OperationFailure aborts the transaction; a fresh real HTTP retry succeeds without leaking a staged attempt, archive or fulfillment marker.
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
    And the coordinated target starts "pending"
    And the post-write rollback boundary is
      | Field      | Value                      |
      | Command    | webhook                    |
      | AfterWrite | payment_history.insert_one |
      | Exception  | OperationFailure           |
    When the public request reaches the real post-write fault
    Then the response matches case "PAY12-18"
      | Field                  | Value                                 |
      | HTTPStatuses           | 503                                   |
      | ContentType            | application/problem+json              |
      | Code                   | webhook_retry                         |
      | JSON.type              | "about:blank"                         |
      | JSON.title             | "Service Unavailable"                 |
      | JSON.status            | 503                                   |
      | JSON.detail            | "Webhook processing must be retried." |
      | JSON.instance          | "/payments/webhooks/stripe"           |
      | JSON.errors            | []                                    |
      | JSON.missingProperties | []                                    |
    And the real abort preserves this populated state
      | Field                    | Value     |
      | WritesReached            | 2         |
      | TransactionActiveAtFault | true      |
      | SessionEnded             | true      |
      | Collections              | unchanged |
      | OrdersCalls              | 0         |
      | StripeCalls              | 0         |
      | ProviderSessions         | unchanged |
    When the fault is removed and the public request is retried
    Then the recovered webhook receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "succeeded"                 |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "applied"                   |
      | reason              | "payment_succeeded"         |
      | received_at         | {before.received_at}        |
      | completed_at        | {request.window}            |
      | fulfillment_status  | "pending"                   |
    And the complete payment after webhook rollback recovery is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | {stored.session_id}                    |
      | provider_payment_id | "pi_fixture"                           |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And supporting requests preserve the post-abort recovery

  Scenario: PAY12-19 Abort webhook after the real stripe_webhooks.replace_one write
    The scoped decorator awaits the actual MongoDB write inside its real session, records all session-visible collections and proves outside readers still see the complete populated baseline. An explicit post-write OperationFailure aborts the transaction; a fresh real HTTP retry succeeds without leaking a staged attempt, archive or fulfillment marker.
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
    And the coordinated target starts "pending"
    And the post-write rollback boundary is
      | Field      | Value                       |
      | Command    | webhook                     |
      | AfterWrite | stripe_webhooks.replace_one |
      | Exception  | OperationFailure            |
    When the public request reaches the real post-write fault
    Then the response matches case "PAY12-19"
      | Field                  | Value                                 |
      | HTTPStatuses           | 503                                   |
      | ContentType            | application/problem+json              |
      | Code                   | webhook_retry                         |
      | JSON.type              | "about:blank"                         |
      | JSON.title             | "Service Unavailable"                 |
      | JSON.status            | 503                                   |
      | JSON.detail            | "Webhook processing must be retried." |
      | JSON.instance          | "/payments/webhooks/stripe"           |
      | JSON.errors            | []                                    |
      | JSON.missingProperties | []                                    |
    And the real abort preserves this populated state
      | Field                    | Value     |
      | WritesReached            | 3         |
      | TransactionActiveAtFault | true      |
      | SessionEnded             | true      |
      | Collections              | unchanged |
      | OrdersCalls              | 0         |
      | StripeCalls              | 0         |
      | ProviderSessions         | unchanged |
    When the fault is removed and the public request is retried
    Then the recovered webhook receipt is
      | Field               | Value                       |
      | _id                 | {event.id}                  |
      | event_type          | {event.type}                |
      | payload_digest      | {request.sha256}            |
      | outcome             | "succeeded"                 |
      | payment_id          | {event.payment_id}          |
      | order_id            | {event.order_id}            |
      | attempt_id          | {event.attempt_id}          |
      | amount_minor        | 1299                        |
      | currency            | "PLN"                       |
      | session_id          | {event.session_id}          |
      | provider_payment_id | {event.provider_payment_id} |
      | state               | "applied"                   |
      | reason              | "payment_succeeded"         |
      | received_at         | {before.received_at}        |
      | completed_at        | {request.window}            |
      | fulfillment_status  | "pending"                   |
    And the complete payment after webhook rollback recovery is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | {stored.session_id}                    |
      | provider_payment_id | "pi_fixture"                           |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And supporting requests preserve the post-abort recovery

  Scenario: PAY12-20 Check claims at 0 milliseconds with worker-1
    Eight actual worker commands reach the real atomic claim boundary. The selected worker holds its actual lease while all seven competitors observe no available work, then completes through the real HTTP adapters with one logical Paid write and invoice.
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
    And the worker coordination schedule is
      | Field               | Value    |
      | Mode                | claims   |
      | Winner              | worker-1 |
      | Participants        | 8        |
      | AdvanceMilliseconds | 0        |
    Then the response matches case "PAY12-20"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
    When real claim and worker commands follow the schedule
    Then the complete coordinated worker receipt is
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
    And the coordinated worker effects are
      | Field             | Value     |
      | Claims            | 1         |
      | Processed         | 1         |
      | StaleRejections   | 0         |
      | LogicalPaidWrites | 1         |
      | LogicalInvoices   | 1         |
      | StripeCalls       | 0         |
      | FinalStatus       | completed |
    And the complete payment after worker coordination is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | {stored.session_id}                    |
      | provider_payment_id | "pi_fixture"                           |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |

  Scenario: PAY12-21 Check claims at 0 milliseconds with worker-8
    Eight actual worker commands reach the real atomic claim boundary. The selected worker holds its actual lease while all seven competitors observe no available work, then completes through the real HTTP adapters with one logical Paid write and invoice.
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
    And the worker coordination schedule is
      | Field               | Value    |
      | Mode                | claims   |
      | Winner              | worker-8 |
      | Participants        | 8        |
      | AdvanceMilliseconds | 0        |
    Then the response matches case "PAY12-21"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
    When real claim and worker commands follow the schedule
    Then the complete coordinated worker receipt is
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
    And the coordinated worker effects are
      | Field             | Value     |
      | Claims            | 1         |
      | Processed         | 1         |
      | StaleRejections   | 0         |
      | LogicalPaidWrites | 1         |
      | LogicalInvoices   | 1         |
      | StripeCalls       | 0         |
      | FinalStatus       | completed |
    And the complete payment after worker coordination is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | {stored.session_id}                    |
      | provider_payment_id | "pi_fixture"                           |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |

  Scenario: PAY12-22 Check lease-boundary at 299999 milliseconds with worker-1
    Explicit repository actions use an exact millisecond clock around the real 300-second lease boundary. Every field of the active owner is checked; stale save, complete and failure commands cannot overwrite a replacement or an expired unreclaimed lease. These actions are not presented as HTTP requests or worker batches.
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
    And the worker coordination schedule is
      | Field               | Value          |
      | Mode                | lease-boundary |
      | Winner              | worker-1       |
      | Participants        | 2              |
      | AdvanceMilliseconds | 299999         |
    Then the response matches case "PAY12-22"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
    When real claim and worker commands follow the schedule
    Then the complete coordinated worker receipt is
      | Field                              | Value         |
      | _id                                | {before}      |
      | event_type                         | {before}      |
      | payload_digest                     | {before}      |
      | outcome                            | {before}      |
      | payment_id                         | {before}      |
      | order_id                           | {before}      |
      | attempt_id                         | {before}      |
      | amount_minor                       | {before}      |
      | currency                           | {before}      |
      | session_id                         | {before}      |
      | provider_payment_id                | {before}      |
      | state                              | {before}      |
      | reason                             | {before}      |
      | received_at                        | {before}      |
      | completed_at                       | {before}      |
      | fulfillment_status                 | "processing"  |
      | fulfillment_attempts               | 1             |
      | fulfillment_lease_id               | {lease.id}    |
      | fulfillment_lease_until            | {lease.until} |
      | fulfillment_next_attempt           | <absent>      |
      | fulfillment_error                  | <absent>      |
      | fulfillment_order_paid             | <absent>      |
      | fulfillment_client_id              | <absent>      |
      | fulfillment_invoice_id             | <absent>      |
      | fulfillment_client_data_version_id | <absent>      |
      | fulfillment_completed_at           | <absent>      |
    And the coordinated worker effects are
      | Field             | Value      |
      | Claims            | 1          |
      | Processed         | 0          |
      | StaleRejections   | 0          |
      | LogicalPaidWrites | 0          |
      | LogicalInvoices   | 0          |
      | StripeCalls       | 0          |
      | FinalStatus       | processing |
    And the complete payment after worker coordination is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | {stored.session_id}                    |
      | provider_payment_id | "pi_fixture"                           |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |

  Scenario: PAY12-23 Check lease-boundary at 300000 milliseconds with worker-2
    Explicit repository actions use an exact millisecond clock around the real 300-second lease boundary. Every field of the active owner is checked; stale save, complete and failure commands cannot overwrite a replacement or an expired unreclaimed lease. These actions are not presented as HTTP requests or worker batches.
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
    And the worker coordination schedule is
      | Field               | Value          |
      | Mode                | lease-boundary |
      | Winner              | worker-2       |
      | Participants        | 2              |
      | AdvanceMilliseconds | 300000         |
    Then the response matches case "PAY12-23"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
    When real claim and worker commands follow the schedule
    Then the complete coordinated worker receipt is
      | Field                              | Value         |
      | _id                                | {before}      |
      | event_type                         | {before}      |
      | payload_digest                     | {before}      |
      | outcome                            | {before}      |
      | payment_id                         | {before}      |
      | order_id                           | {before}      |
      | attempt_id                         | {before}      |
      | amount_minor                       | {before}      |
      | currency                           | {before}      |
      | session_id                         | {before}      |
      | provider_payment_id                | {before}      |
      | state                              | {before}      |
      | reason                             | {before}      |
      | received_at                        | {before}      |
      | completed_at                       | {before}      |
      | fulfillment_status                 | "processing"  |
      | fulfillment_attempts               | 2             |
      | fulfillment_lease_id               | {lease.id}    |
      | fulfillment_lease_until            | {lease.until} |
      | fulfillment_next_attempt           | <absent>      |
      | fulfillment_error                  | <absent>      |
      | fulfillment_order_paid             | <absent>      |
      | fulfillment_client_id              | <absent>      |
      | fulfillment_invoice_id             | <absent>      |
      | fulfillment_client_data_version_id | <absent>      |
      | fulfillment_completed_at           | <absent>      |
    And the coordinated worker effects are
      | Field             | Value      |
      | Claims            | 2          |
      | Processed         | 0          |
      | StaleRejections   | 3          |
      | LogicalPaidWrites | 0          |
      | LogicalInvoices   | 0          |
      | StripeCalls       | 0          |
      | FinalStatus       | processing |
    And the complete payment after worker coordination is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | {stored.session_id}                    |
      | provider_payment_id | "pi_fixture"                           |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |

  Scenario: PAY12-24 Check lease-boundary at 300001 milliseconds with worker-2
    Explicit repository actions use an exact millisecond clock around the real 300-second lease boundary. Every field of the active owner is checked; stale save, complete and failure commands cannot overwrite a replacement or an expired unreclaimed lease. These actions are not presented as HTTP requests or worker batches.
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
    And the worker coordination schedule is
      | Field               | Value          |
      | Mode                | lease-boundary |
      | Winner              | worker-2       |
      | Participants        | 2              |
      | AdvanceMilliseconds | 300001         |
    Then the response matches case "PAY12-24"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
    When real claim and worker commands follow the schedule
    Then the complete coordinated worker receipt is
      | Field                              | Value         |
      | _id                                | {before}      |
      | event_type                         | {before}      |
      | payload_digest                     | {before}      |
      | outcome                            | {before}      |
      | payment_id                         | {before}      |
      | order_id                           | {before}      |
      | attempt_id                         | {before}      |
      | amount_minor                       | {before}      |
      | currency                           | {before}      |
      | session_id                         | {before}      |
      | provider_payment_id                | {before}      |
      | state                              | {before}      |
      | reason                             | {before}      |
      | received_at                        | {before}      |
      | completed_at                       | {before}      |
      | fulfillment_status                 | "processing"  |
      | fulfillment_attempts               | 2             |
      | fulfillment_lease_id               | {lease.id}    |
      | fulfillment_lease_until            | {lease.until} |
      | fulfillment_next_attempt           | <absent>      |
      | fulfillment_error                  | <absent>      |
      | fulfillment_order_paid             | <absent>      |
      | fulfillment_client_id              | <absent>      |
      | fulfillment_invoice_id             | <absent>      |
      | fulfillment_client_data_version_id | <absent>      |
      | fulfillment_completed_at           | <absent>      |
    And the coordinated worker effects are
      | Field             | Value      |
      | Claims            | 2          |
      | Processed         | 0          |
      | StaleRejections   | 3          |
      | LogicalPaidWrites | 0          |
      | LogicalInvoices   | 0          |
      | StripeCalls       | 0          |
      | FinalStatus       | processing |
    And the complete payment after worker coordination is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | {stored.session_id}                    |
      | provider_payment_id | "pi_fixture"                           |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |

  Scenario: PAY12-25 Check stale-save_order_paid at 300000 milliseconds with worker-2
    The old worker pauses immediately before its real save_order_paid command after any earlier downstream effects. At the exact lease boundary a new actual worker reclaims and completes. The resumed old command uses its originally captured clock and lease, throws the real fencing error and preserves the complete winner and downstream state.
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
    And the worker coordination schedule is
      | Field               | Value                 |
      | Mode                | stale-save_order_paid |
      | Winner              | worker-2              |
      | Participants        | 2                     |
      | AdvanceMilliseconds | 300000                |
    Then the response matches case "PAY12-25"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
    When real claim and worker commands follow the schedule
    Then the complete coordinated worker receipt is
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
    And the coordinated worker effects are
      | Field             | Value     |
      | Claims            | 2         |
      | Processed         | 2         |
      | StaleRejections   | 1         |
      | LogicalPaidWrites | 1         |
      | LogicalInvoices   | 1         |
      | StripeCalls       | 0         |
      | FinalStatus       | completed |
    And the complete payment after worker coordination is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | {stored.session_id}                    |
      | provider_payment_id | "pi_fixture"                           |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |

  Scenario: PAY12-26 Check stale-complete at 300000 milliseconds with worker-2
    The old worker pauses immediately before its real complete command after any earlier downstream effects. At the exact lease boundary a new actual worker reclaims and completes. The resumed old command uses its originally captured clock and lease, throws the real fencing error and preserves the complete winner and downstream state.
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
    And the worker coordination schedule is
      | Field               | Value          |
      | Mode                | stale-complete |
      | Winner              | worker-2       |
      | Participants        | 2              |
      | AdvanceMilliseconds | 300000         |
    Then the response matches case "PAY12-26"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
    When real claim and worker commands follow the schedule
    Then the complete coordinated worker receipt is
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
    And the coordinated worker effects are
      | Field             | Value     |
      | Claims            | 2         |
      | Processed         | 2         |
      | StaleRejections   | 1         |
      | LogicalPaidWrites | 1         |
      | LogicalInvoices   | 1         |
      | StripeCalls       | 0         |
      | FinalStatus       | completed |
    And the complete payment after worker coordination is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | {stored.session_id}                    |
      | provider_payment_id | "pi_fixture"                           |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |

  Scenario: PAY12-27 Check stale-fail at 300000 milliseconds with worker-2
    The old worker pauses immediately before its real fail command after any earlier downstream effects. At the exact lease boundary a new actual worker reclaims and completes. The resumed old command uses its originally captured clock and lease, throws the real fencing error and preserves the complete winner and downstream state.
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
    And the worker coordination schedule is
      | Field               | Value      |
      | Mode                | stale-fail |
      | Winner              | worker-2   |
      | Participants        | 2          |
      | AdvanceMilliseconds | 300000     |
    Then the response matches case "PAY12-27"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
    When real claim and worker commands follow the schedule
    Then the complete coordinated worker receipt is
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
    And the coordinated worker effects are
      | Field             | Value     |
      | Claims            | 2         |
      | Processed         | 2         |
      | StaleRejections   | 1         |
      | LogicalPaidWrites | 1         |
      | LogicalInvoices   | 1         |
      | StripeCalls       | 0         |
      | FinalStatus       | completed |
    And the complete payment after worker coordination is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | {stored.session_id}                    |
      | provider_payment_id | "pi_fixture"                           |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |

  Scenario: PAY12-28 Check lease-expiry at 300000 milliseconds with worker-1
    Explicit repository actions use an exact millisecond clock around the real 300-second lease boundary. Every field of the active owner is checked; stale save, complete and failure commands cannot overwrite a replacement or an expired unreclaimed lease. These actions are not presented as HTTP requests or worker batches.
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
    And the worker coordination schedule is
      | Field               | Value        |
      | Mode                | lease-expiry |
      | Winner              | worker-1     |
      | Participants        | 1            |
      | AdvanceMilliseconds | 300000       |
    Then the response matches case "PAY12-28"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
    When real claim and worker commands follow the schedule
    Then the complete coordinated worker receipt is
      | Field                              | Value         |
      | _id                                | {before}      |
      | event_type                         | {before}      |
      | payload_digest                     | {before}      |
      | outcome                            | {before}      |
      | payment_id                         | {before}      |
      | order_id                           | {before}      |
      | attempt_id                         | {before}      |
      | amount_minor                       | {before}      |
      | currency                           | {before}      |
      | session_id                         | {before}      |
      | provider_payment_id                | {before}      |
      | state                              | {before}      |
      | reason                             | {before}      |
      | received_at                        | {before}      |
      | completed_at                       | {before}      |
      | fulfillment_status                 | "processing"  |
      | fulfillment_attempts               | 1             |
      | fulfillment_lease_id               | {lease.id}    |
      | fulfillment_lease_until            | {lease.until} |
      | fulfillment_next_attempt           | <absent>      |
      | fulfillment_error                  | <absent>      |
      | fulfillment_order_paid             | <absent>      |
      | fulfillment_client_id              | <absent>      |
      | fulfillment_invoice_id             | <absent>      |
      | fulfillment_client_data_version_id | <absent>      |
      | fulfillment_completed_at           | <absent>      |
    And the coordinated worker effects are
      | Field             | Value      |
      | Claims            | 1          |
      | Processed         | 0          |
      | StaleRejections   | 3          |
      | LogicalPaidWrites | 0          |
      | LogicalInvoices   | 0          |
      | StripeCalls       | 0          |
      | FinalStatus       | processing |
    And the complete payment after worker coordination is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | {stored.session_id}                    |
      | provider_payment_id | "pi_fixture"                           |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
