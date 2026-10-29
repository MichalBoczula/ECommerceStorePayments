Feature: Hosted checkout creation and recovery

  Scenario: PAY21-01 Create checkout from the server order
    A payable order starts without a payment or checkout session. Checkout persists Pending state, its history and one provider session.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a payable order
    And I remember checkout state and provider calls
    When I create checkout for the order
    Then the response matches case "PAY21-01"
      | Field                     | Value            |
      | HTTPStatuses              | 200              |
      | ContentType               | application/json |
      | Code                      | -                |
      | JSON.payment.status       | "pending"        |
      | JSON.payment.amount_minor | 1299             |
      | JSON.payment.currency     | "PLN"            |
      | JSON.checkout_status      | "open"           |
    And the current payment is "Pending" at version 2
    And the database has 1 current payment and 2 history snapshots
    And Stripe has one checkout session
    And the complete checkout response is
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
    And only this checkout is created with this provider request
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

  Scenario: PAY21-02 Read an existing checkout instead of creating another
    A Pending payment already has an open hosted checkout. Repeating checkout reads that session without creating a second one.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And I remember checkout state and provider calls
    When I create checkout for the order
    Then the response matches case "PAY21-02"
      | Field                     | Value            |
      | HTTPStatuses              | 200              |
      | ContentType               | application/json |
      | Code                      | -                |
      | JSON.payment.status       | "pending"        |
      | JSON.payment.amount_minor | 1299             |
      | JSON.payment.currency     | "PLN"            |
      | JSON.checkout_status      | "open"           |
    And the current payment is "Pending" at version 2
    And the database has 1 current payment and 2 history snapshots
    And Stripe has one checkout session
    And the complete checkout response is
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
    And checkout reads only the existing provider session without writes

  Scenario: PAY21-03 Recover a timeout after the provider accepted checkout
    Stripe accepted a checkout but its first response was lost. A retry recovers the same provider session and finishes Pending state.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an ambiguous checkout timeout
    And the earlier checkout failure matches
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
    And the earlier checkout failure leaves
      | Field          | Value    |
      | Effect         | reserved |
      | OrdersReads    | 2        |
      | StripeMethod   | POST     |
      | SessionsAdded  | 1        |
      | CurrentVersion | 1        |
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY21-03"
      | Field                     | Value            |
      | HTTPStatuses              | 200              |
      | ContentType               | application/json |
      | Code                      | -                |
      | JSON.payment.status       | "pending"        |
      | JSON.payment.amount_minor | 1299             |
      | JSON.payment.currency     | "PLN"            |
      | JSON.checkout_status      | "open"           |
    And the current payment is "Pending" at version 2
    And Stripe has one checkout session
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

  Scenario: PAY21-04 Disabled checkout does not prepare a payment
    Hosted checkout is disabled in service settings. The API returns checkout_disabled before preparing payment state or calling Stripe.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And checkout is disabled
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY21-04"
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
    And the database has 0 current payments and 0 history snapshots
    And Stripe was not called
    And checkout failure leaves this complete state
      | Field          | Value     |
      | Effect         | unchanged |
      | OrdersReads    | 0         |
      | StripeMethod   | none      |
      | SessionsAdded  | 0         |
      | CurrentVersion | none      |

  Scenario: PAY21-05 Reject a Paid order before contacting Stripe
    Orders reports an already Paid order during checkout. The API returns order_not_payable before any Stripe request is sent.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And Orders reports status "Paid"
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY21-05"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 409                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | order_not_payable                                         |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Conflict"                                                |
      | JSON.status            | 409                                                       |
      | JSON.detail            | "Order cannot be paid in its current state."              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And Stripe was not called
    And checkout failure leaves this complete state
      | Field          | Value     |
      | Effect         | unchanged |
      | OrdersReads    | 1         |
      | StripeMethod   | none      |
      | SessionsAdded  | 0         |
      | CurrentVersion | none      |

  Scenario: PAY21-06 Report provider rejection safely
    Stripe rejects checkout creation with a controlled provider response. The API returns a safe checkout_provider_error and retains Created state.
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
    Then the response matches case "PAY21-06"
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
    And the current payment is "Created" at version 1
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

  Scenario: PAY21-07 Report an ambiguous provider timeout safely
    Stripe accepts checkout but a transport timeout interrupts its acknowledgement. The API reports checkout_timeout and keeps the prepared payment retryable.
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
    And Stripe responds with "timeout_once"
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY21-07"
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
    And the current payment is "Created" at version 1
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

  Scenario: PAY21-08 Reject a missing order
    The order needed for checkout does not exist. Checkout returns order_not_found without sending a request to Stripe.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And Orders returns "missing"
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY21-08"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 404                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | order_not_found                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Not Found"                                               |
      | JSON.status            | 404                                                       |
      | JSON.detail            | "Order was not found."                                    |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And Stripe was not called
    And checkout failure leaves this complete state
      | Field          | Value     |
      | Effect         | unchanged |
      | OrdersReads    | 1         |
      | StripeMethod   | none      |
      | SessionsAdded  | 0         |
      | CurrentVersion | none      |

  Scenario: PAY21-09 Preserve payment snapshot after the order total changes
    The order total changes after hosted checkout was created. Repeating checkout rejects the change and retains the original Pending payment.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And Orders total has changed
    And I remember checkout recovery state
    When I create checkout for the order
    Then the response matches case "PAY21-09"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 409                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | order_total_changed                                       |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Conflict"                                                |
      | JSON.status            | 409                                                       |
      | JSON.detail            | "Order total has changed."                                |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And the current payment is "Pending" at version 2
    And Stripe has one checkout session
    And checkout failure leaves this complete state
      | Field          | Value     |
      | Effect         | unchanged |
      | OrdersReads    | 1         |
      | StripeMethod   | none      |
      | SessionsAdded  | 0         |
      | CurrentVersion | 2         |
