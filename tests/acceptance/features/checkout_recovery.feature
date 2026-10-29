Feature: Checkout failures and durable recovery

  Scenario: PAY06-01 Preserve one reservation across repeated provider rejections
    Stripe rejects the same reserved request repeatedly. Every safe problem preserves the complete reservation and history; a fresh application instance later replays exactly that request successfully.
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
    And Stripe responds with "rejection"
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-01"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 502                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_provider_error                                   |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Gateway"                                             |
      | JSON.status            | 502                                                       |
      | JSON.detail            | "Checkout provider request could not complete."           |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And checkout failure leaves this complete state
      | Field          | Value    |
      | Effect         | reserved |
      | OrdersReads    | 2        |
      | StripeMethod   | POST     |
      | SessionsAdded  | 0        |
      | CurrentVersion | 1        |
    And the failed provider request is
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
    And repeated provider rejection preserves the reserved attempt
      | Field   | Value |
      | Repeats | 2     |
    And a fresh application instance recovers checkout with
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}                  |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovery provider request is
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

  Scenario: PAY06-02 Recover a timeout before the provider accepts checkout
    A transport timeout occurs before Stripe accepts any session. The complete reservation remains durable, and a fresh application instance creates one session using the same request and key.
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
    And Stripe responds with "timeout_before"
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-02"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 504                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_timeout                                          |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Gateway Timeout"                                         |
      | JSON.status            | 504                                                       |
      | JSON.detail            | "Checkout provider timed out."                            |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And checkout failure leaves this complete state
      | Field          | Value    |
      | Effect         | reserved |
      | OrdersReads    | 2        |
      | StripeMethod   | POST     |
      | SessionsAdded  | 0        |
      | CurrentVersion | 1        |
    And the failed provider request is
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
    And a fresh application instance recovers checkout with
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}                  |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovery provider request is
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

  Scenario: PAY06-03 Recover interruption before the Pending save
    Stripe accepts the session but the next repository update is interrupted before commit. The API returns a complete safe server problem; a fresh application instance replays the same durable attempt and stores Pending.
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
    And checkout persistence is interrupted at "pending_before"
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-03"
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
    And checkout failure leaves this complete state
      | Field          | Value    |
      | Effect         | reserved |
      | OrdersReads    | 2        |
      | StripeMethod   | POST     |
      | SessionsAdded  | 1        |
      | CurrentVersion | 1        |
    And the failed provider request is
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
    And a fresh application instance recovers checkout with
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}                  |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovery provider request is
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

  Scenario: PAY06-04 Recover a lost acknowledgment after the Pending commit
    The real Pending transaction and history commit before an injected acknowledgment loss. The API returns a safe server problem; a fresh application instance retrieves that session without another write or create.
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
    And checkout persistence is interrupted at "pending_after"
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-04"
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
    And checkout failure leaves this complete state
      | Field          | Value   |
      | Effect         | pending |
      | OrdersReads    | 2       |
      | StripeMethod   | POST    |
      | SessionsAdded  | 1       |
      | CurrentVersion | 2       |
    And the failed provider request is
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
    And a fresh application instance recovers checkout with
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}                  |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovery provider request is
      | Field          | Value                              |
      | Method         | GET                                |
      | Path           | /v1/checkout/sessions/{session.id} |
      | StripeVersion  | 2026-08-26.dahlia                  |
      | IdempotencyKey | absent                             |
      | Body           | empty                              |

  Scenario: PAY06-05 Recover interruption before the reservation save
    The initial payment insert succeeds but attempt reservation is interrupted before persistence or Stripe. A fresh application instance reserves safely and completes checkout, preserving every unrelated document.
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
    And checkout persistence is interrupted at "reservation_before"
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-05"
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
    And checkout failure leaves this complete state
      | Field          | Value   |
      | Effect         | created |
      | OrdersReads    | 2       |
      | StripeMethod   | none    |
      | SessionsAdded  | 0       |
      | CurrentVersion | 0       |
    And a fresh application instance recovers checkout with
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}                  |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovery provider request is
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

  Scenario: PAY06-06 Recover a legacy card-only reserved request
    A historical Created reservation physically omits the request-version field. Rehydration defaults to version one, and recovery sends the original card-only form without adding BLIK or changing the attempt.
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
    And a reserved checkout fixture contains
      | Field          | Value                    |
      | RequestVersion | 1                        |
      | AgeSeconds     | 0                        |
      | OmittedFields  | checkout_request_version |
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-06"
      | Field                | Value            |
      | HTTPStatuses         | 200              |
      | ContentType          | application/json |
      | Code                 | -                |
      | JSON.payment.status  | "pending"        |
      | JSON.checkout_status | "open"           |
    And the complete recovered checkout response is
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}                  |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovery provider request is
      | Field                                              | Value                                         |
      | Method                                             | POST                                          |
      | Path                                               | /v1/checkout/sessions                         |
      | StripeVersion                                      | 2026-08-26.dahlia                             |
      | ContentType                                        | application/x-www-form-urlencoded             |
      | IdempotencyKey                                     | checkout:{payment.id}:{attempt.id}            |
      | form.mode                                          | payment                                       |
      | form.payment_method_types[0]                       | card                                          |
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

  Scenario: PAY06-07 Recover an existing version-two reservation
    A durable version-two attempt has not yet received a provider session. Checkout creates one card-and-BLIK session and one exact prior-state archive without reserving another attempt.
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
    And a reserved checkout fixture contains
      | Field          | Value |
      | RequestVersion | 2     |
      | AgeSeconds     | 0     |
      | OmittedFields  | -     |
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-07"
      | Field                | Value            |
      | HTTPStatuses         | 200              |
      | ContentType          | application/json |
      | Code                 | -                |
      | JSON.payment.status  | "pending"        |
      | JSON.checkout_status | "open"           |
    And the complete recovered checkout response is
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}                  |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovery provider request is
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

  Scenario: PAY06-08 Require reconciliation at exactly twenty-three hours
    The application clock observes an unresolved Created attempt exactly twenty-three hours old. Checkout returns reconciliation-required without calling Stripe or altering any stored or provider state.
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
    And a reserved checkout fixture contains
      | Field          | Value |
      | RequestVersion | 2     |
      | AgeSeconds     | 82800 |
      | OmittedFields  | -     |
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-08"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 409                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_recovery_required                                |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Conflict"                                                |
      | JSON.status            | 409                                                       |
      | JSON.detail            | "Checkout requires reconciliation."                       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And checkout failure leaves this complete state
      | Field          | Value     |
      | Effect         | unchanged |
      | OrdersReads    | 1         |
      | StripeMethod   | none      |
      | SessionsAdded  | 0         |
      | CurrentVersion | 1         |

  Scenario: PAY06-09 Recover one millisecond before the attempt age limit
    An unresolved Created reservation is one millisecond younger than twenty-three hours under the application comparison clock. Checkout replays that attempt successfully and preserves its original identity and timestamp.
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
    And a reserved checkout fixture contains
      | Field          | Value     |
      | RequestVersion | 2         |
      | AgeSeconds     | 82799.999 |
      | OmittedFields  | -         |
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-09"
      | Field                | Value            |
      | HTTPStatuses         | 200              |
      | ContentType          | application/json |
      | Code                 | -                |
      | JSON.payment.status  | "pending"        |
      | JSON.checkout_status | "open"           |
    And the complete recovered checkout response is
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}                  |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovery provider request is
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

  Scenario: PAY06-10 Require reconciliation one millisecond beyond the age limit
    An unresolved reservation is one millisecond older than twenty-three hours. Checkout rejects it without a Stripe request, new attempt, archive, version, timestamp or change to unrelated records.
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
    And a reserved checkout fixture contains
      | Field          | Value     |
      | RequestVersion | 2         |
      | AgeSeconds     | 82800.001 |
      | OmittedFields  | -         |
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-10"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 409                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_recovery_required                                |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Conflict"                                                |
      | JSON.status            | 409                                                       |
      | JSON.detail            | "Checkout requires reconciliation."                       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And checkout failure leaves this complete state
      | Field          | Value     |
      | Effect         | unchanged |
      | OrdersReads    | 1         |
      | StripeMethod   | none      |
      | SessionsAdded  | 0         |
      | CurrentVersion | 1         |

  Scenario: PAY06-11 Require reconciliation for legacy Pending without an attempt
    A valid historical Pending document physically lacks checkout identity fields. Checkout preserves the entire historical document and populated collections and never creates or retrieves a provider session.
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
    And a legacy Pending checkout has no attempt identity
      | Field             | Value                                                            |
      | OmittedFields     | checkout_attempt_id,checkout_started_at,checkout_request_version |
      | ProviderSessionId | cs_test_historical                                               |
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-11"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 409                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_recovery_required                                |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Conflict"                                                |
      | JSON.status            | 409                                                       |
      | JSON.detail            | "Checkout requires reconciliation."                       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And checkout failure leaves this complete state
      | Field          | Value     |
      | Effect         | unchanged |
      | OrdersReads    | 1         |
      | StripeMethod   | none      |
      | SessionsAdded  | 0         |
      | CurrentVersion | 0         |

  Scenario: PAY06-12 Reject an unsupported positive reserved request version
    A domain-valid historical reservation records positive request version three. The provider adapter rejects this unsupported request format before sending HTTP, preserving the complete reservation and every unrelated record.
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
    And a reserved checkout fixture contains
      | Field          | Value |
      | RequestVersion | 3     |
      | AgeSeconds     | 0     |
      | OmittedFields  | -     |
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-12"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 502                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_provider_error                                   |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Gateway"                                             |
      | JSON.status            | 502                                                       |
      | JSON.detail            | "Checkout provider request could not complete."           |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And checkout failure leaves this complete state
      | Field          | Value     |
      | Effect         | unchanged |
      | OrdersReads    | 1         |
      | StripeMethod   | none      |
      | SessionsAdded  | 0         |
      | CurrentVersion | 1         |

  Scenario: PAY06-13 Preserve Pending checkout after a provider rejection
    An existing Pending checkout cannot be retrieved from Stripe. The API returns the exact safe failure and preserves all payment/history/receipt fields and provider sessions; a fresh application instance later reads that same session.
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
    And a checkout created through the API
    And Stripe responds with "rejection"
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-13"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 502                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_provider_error                                   |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Gateway"                                             |
      | JSON.status            | 502                                                       |
      | JSON.detail            | "Checkout provider request could not complete."           |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And checkout failure leaves this complete state
      | Field          | Value     |
      | Effect         | unchanged |
      | OrdersReads    | 1         |
      | StripeMethod   | GET       |
      | SessionsAdded  | 0         |
      | CurrentVersion | 2         |
    And a fresh application instance recovers checkout with
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}                  |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovery provider request is
      | Field          | Value                              |
      | Method         | GET                                |
      | Path           | /v1/checkout/sessions/{session.id} |
      | StripeVersion  | 2026-08-26.dahlia                  |
      | IdempotencyKey | absent                             |
      | Body           | empty                              |

  Scenario: PAY06-14 Preserve Pending checkout after a provider read timeout
    An existing Pending checkout cannot be retrieved from Stripe. The API returns the exact safe failure and preserves all payment/history/receipt fields and provider sessions; a fresh application instance later reads that same session.
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
    And a checkout created through the API
    And Stripe responds with "timeout_before"
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-14"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 504                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_timeout                                          |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Gateway Timeout"                                         |
      | JSON.status            | 504                                                       |
      | JSON.detail            | "Checkout provider timed out."                            |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And checkout failure leaves this complete state
      | Field          | Value     |
      | Effect         | unchanged |
      | OrdersReads    | 1         |
      | StripeMethod   | GET       |
      | SessionsAdded  | 0         |
      | CurrentVersion | 2         |
    And a fresh application instance recovers checkout with
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}                  |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovery provider request is
      | Field          | Value                              |
      | Method         | GET                                |
      | Path           | /v1/checkout/sessions/{session.id} |
      | StripeVersion  | 2026-08-26.dahlia                  |
      | IdempotencyKey | absent                             |
      | Body           | empty                              |

  Scenario: PAY06-15 Recover a provider response with mismatched money
    Stripe accepts one checkout but returns a mismatched amount in its response. Mapping rejects it safely and preserves Created reservation state; a fresh application instance replays the same form and recovers the accepted session.
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
    And Stripe responds with "invalid_money"
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-15"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 502                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_provider_error                                   |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Gateway"                                             |
      | JSON.status            | 502                                                       |
      | JSON.detail            | "Checkout provider request could not complete."           |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And checkout failure leaves this complete state
      | Field          | Value    |
      | Effect         | reserved |
      | OrdersReads    | 2        |
      | StripeMethod   | POST     |
      | SessionsAdded  | 1        |
      | CurrentVersion | 1        |
    And the failed provider request is
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
    And a fresh application instance recovers checkout with
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}                  |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovery provider request is
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

  Scenario: PAY06-16 Recover a provider connection failure before acceptance
    A connection failure prevents Stripe from accepting checkout. The API keeps the complete durable reservation and safe problem; a fresh application instance sends the identical form and idempotency key successfully.
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
    And Stripe responds with "connection"
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-16"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 502                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_provider_error                                   |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Gateway"                                             |
      | JSON.status            | 502                                                       |
      | JSON.detail            | "Checkout provider request could not complete."           |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And checkout failure leaves this complete state
      | Field          | Value    |
      | Effect         | reserved |
      | OrdersReads    | 2        |
      | StripeMethod   | POST     |
      | SessionsAdded  | 0        |
      | CurrentVersion | 1        |
    And the failed provider request is
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
    And a fresh application instance recovers checkout with
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 1299                                   |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}                  |
      | payment.provider_payment_id | null                                   |
      | payment.failure_code        | null                                   |
      | payment.created_at          | {stored.created_at}                    |
      | payment.updated_at          | {stored.updated_at}                    |
      | checkout_url                | {provider.url}                         |
      | checkout_status             | "open"                                 |
      | expires_at                  | {provider.expires_at}                  |
    And the recovery provider request is
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

  Scenario: PAY06-17 Preserve an existing payment when checkout is disabled
    Checkout is disabled after an existing Created payment and unrelated populated collections exist. Availability rejection performs no Orders or Stripe call and preserves every stored field.
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
    And a payment created through the API
    And checkout is disabled
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-17"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 503                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_disabled                                         |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Service Unavailable"                                     |
      | JSON.status            | 503                                                       |
      | JSON.detail            | "Checkout is not configured."                             |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And checkout failure leaves this complete state
      | Field          | Value     |
      | Effect         | unchanged |
      | OrdersReads    | 0         |
      | StripeMethod   | none      |
      | SessionsAdded  | 0         |
      | CurrentVersion | 0         |

  Scenario: PAY06-18 Reject checkout for a Succeeded payment without changes
    A complete Succeeded payment already has provider identifiers and immutable history. Checkout rechecks Orders, returns checkout-unavailable, and preserves all current/history/receipt fields without contacting Stripe.
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
    And a stored payment is prepared in state "succeeded"
      | Field               | Value               |
      | provider_session_id | "cs_test_succeeded" |
      | provider_payment_id | "pi_succeeded"      |
      | failure_code        | null                |
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY06-18"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 409                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_unavailable                                      |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Conflict"                                                |
      | JSON.status            | 409                                                       |
      | JSON.detail            | "Payment cannot start checkout in this state."            |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And checkout failure leaves this complete state
      | Field          | Value     |
      | Effect         | unchanged |
      | OrdersReads    | 1         |
      | StripeMethod   | none      |
      | SessionsAdded  | 0         |
      | CurrentVersion | 3         |
