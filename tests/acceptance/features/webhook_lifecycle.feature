Feature: Complete webhook lifecycle and durable replay

  Scenario: PAY08-01 Confirm asynchronous payment success
    A signed asynchronous success matches the current Pending checkout. All receipt fields and the single complete archived Pending version are checked.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And the lifecycle event is prepared
      | Field         | Value                                    |
      | EventId       | evt_pay08_01                             |
      | EventType     | checkout.session.async_payment_succeeded |
      | AttemptSource | current                                  |
      | PaymentId     | {payment.id}                             |
      | OrderId       | {order.id}                               |
      | AttemptId     | {attempt.id}                             |
      | SessionId     | {session.id}                             |
      | AmountMinor   | 1299                                     |
      | PaymentStatus | paid                                     |
      | SessionStatus | complete                                 |
      | PaymentIntent | "pi_fixture"                             |
      | Encoding      | normal                                   |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-01"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value               |
      | _id                 | {event.id}          |
      | event_type          | {event.type}        |
      | payload_digest      | {request.sha256}    |
      | outcome             | "succeeded"         |
      | payment_id          | {event.payment_id}  |
      | order_id            | {event.order_id}    |
      | attempt_id          | {event.attempt_id}  |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | session_id          | {event.session_id}  |
      | provider_payment_id | "pi_fixture"        |
      | state               | "applied"           |
      | reason              | "payment_succeeded" |
      | received_at         | {request.window}    |
      | completed_at        | {request.window}    |
      | fulfillment_status  | "pending"           |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 1                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-02 Record asynchronous payment failure
    A signed asynchronous failure matches a Pending attempt. It records checkout_failed and completes its receipt without scheduling fulfillment.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And the lifecycle event is prepared
      | Field         | Value                                 |
      | EventId       | evt_pay08_02                          |
      | EventType     | checkout.session.async_payment_failed |
      | AttemptSource | current                               |
      | PaymentId     | {payment.id}                          |
      | OrderId       | {order.id}                            |
      | AttemptId     | {attempt.id}                          |
      | SessionId     | {session.id}                          |
      | AmountMinor   | 1299                                  |
      | PaymentStatus | unpaid                                |
      | SessionStatus | complete                              |
      | PaymentIntent | null                                  |
      | Encoding      | normal                                |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-02"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "failed"           |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | null               |
      | state               | "applied"          |
      | reason              | "payment_failed"   |
      | received_at         | {request.window}   |
      | completed_at        | {request.window}   |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | failed             |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | "checkout_failed"  |
      | NewArchives             | 1                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "failed"            |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | "checkout_failed"   |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-03 Late paid completion wins after expiry
    An earlier expiry failed this same attempt. A later paid completion clears its failure and establishes success with one additional immutable archive.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And the lifecycle event is prepared
      | Field         | Value                    |
      | EventId       | evt_setup_expiry         |
      | EventType     | checkout.session.expired |
      | AttemptSource | current                  |
      | PaymentId     | {payment.id}             |
      | OrderId       | {order.id}               |
      | AttemptId     | {attempt.id}             |
      | SessionId     | {session.id}             |
      | AmountMinor   | 1299                     |
      | PaymentStatus | unpaid                   |
      | SessionStatus | expired                  |
      | PaymentIntent | null                     |
      | Encoding      | normal                   |
    And the lifecycle event was delivered
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_03               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-03"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value               |
      | _id                 | {event.id}          |
      | event_type          | {event.type}        |
      | payload_digest      | {request.sha256}    |
      | outcome             | "succeeded"         |
      | payment_id          | {event.payment_id}  |
      | order_id            | {event.order_id}    |
      | attempt_id          | {event.attempt_id}  |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | session_id          | {event.session_id}  |
      | provider_payment_id | "pi_fixture"        |
      | state               | "applied"           |
      | reason              | "payment_succeeded" |
      | received_at         | {request.window}    |
      | completed_at        | {request.window}    |
      | fulfillment_status  | "pending"           |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 4                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 1                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-04 Late asynchronous success wins after failure
    The current attempt previously failed asynchronously. A later asynchronous success for that same attempt clears the failure.
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
    And a lifecycle payment starts in
      | Field | Value  |
      | State | failed |
    And the lifecycle event is prepared
      | Field         | Value                                    |
      | EventId       | evt_pay08_04                             |
      | EventType     | checkout.session.async_payment_succeeded |
      | AttemptSource | current                                  |
      | PaymentId     | {payment.id}                             |
      | OrderId       | {order.id}                               |
      | AttemptId     | {attempt.id}                             |
      | SessionId     | {session.id}                             |
      | AmountMinor   | 1299                                     |
      | PaymentStatus | paid                                     |
      | SessionStatus | complete                                 |
      | PaymentIntent | "pi_fixture"                             |
      | Encoding      | normal                                   |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-04"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value               |
      | _id                 | {event.id}          |
      | event_type          | {event.type}        |
      | payload_digest      | {request.sha256}    |
      | outcome             | "succeeded"         |
      | payment_id          | {event.payment_id}  |
      | order_id            | {event.order_id}    |
      | attempt_id          | {event.attempt_id}  |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | session_id          | {event.session_id}  |
      | provider_payment_id | "pi_fixture"        |
      | state               | "applied"           |
      | reason              | "payment_succeeded" |
      | received_at         | {request.window}    |
      | completed_at        | {request.window}    |
      | fulfillment_status  | "pending"           |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 4                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 1                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-05 Ignore asynchronous failure after success
    The same attempt already succeeded. A later failure is acknowledged with already_succeeded while every payment and history field is retained.
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
    And a lifecycle payment starts in
      | Field | Value     |
      | State | succeeded |
    And the lifecycle event is prepared
      | Field         | Value                                 |
      | EventId       | evt_pay08_05                          |
      | EventType     | checkout.session.async_payment_failed |
      | AttemptSource | current                               |
      | PaymentId     | {payment.id}                          |
      | OrderId       | {order.id}                            |
      | AttemptId     | {attempt.id}                          |
      | SessionId     | {session.id}                          |
      | AmountMinor   | 1299                                  |
      | PaymentStatus | unpaid                                |
      | SessionStatus | complete                              |
      | PaymentIntent | null                                  |
      | Encoding      | normal                                |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-05"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value               |
      | _id                 | {event.id}          |
      | event_type          | {event.type}        |
      | payload_digest      | {request.sha256}    |
      | outcome             | "failed"            |
      | payment_id          | {event.payment_id}  |
      | order_id            | {event.order_id}    |
      | attempt_id          | {event.attempt_id}  |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | session_id          | {event.session_id}  |
      | provider_payment_id | null                |
      | state               | "ignored"           |
      | reason              | "already_succeeded" |
      | received_at         | {request.window}    |
      | completed_at        | {request.window}    |
      | fulfillment_status  | null                |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-06 Ignore unpaid completion after success
    An unpaid completion arrives after confirmed success. Its normalized waiting outcome cannot downgrade the successful payment.
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
    And a lifecycle payment starts in
      | Field | Value     |
      | State | succeeded |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_06               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | unpaid                     |
      | SessionStatus | complete                   |
      | PaymentIntent | null                       |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-06"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value               |
      | _id                 | {event.id}          |
      | event_type          | {event.type}        |
      | payload_digest      | {request.sha256}    |
      | outcome             | "waiting"           |
      | payment_id          | {event.payment_id}  |
      | order_id            | {event.order_id}    |
      | attempt_id          | {event.attempt_id}  |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | session_id          | {event.session_id}  |
      | provider_payment_id | null                |
      | state               | "ignored"           |
      | reason              | "already_succeeded" |
      | received_at         | {request.window}    |
      | completed_at        | {request.window}    |
      | fulfillment_status  | null                |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-07 Ignore another failure of a failed attempt
    A distinct failure event targets an already Failed attempt. Its completed receipt records already_terminal and preserves the original failure.
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
    And a lifecycle payment starts in
      | Field | Value  |
      | State | failed |
    And the lifecycle event is prepared
      | Field         | Value                                 |
      | EventId       | evt_pay08_07                          |
      | EventType     | checkout.session.async_payment_failed |
      | AttemptSource | current                               |
      | PaymentId     | {payment.id}                          |
      | OrderId       | {order.id}                            |
      | AttemptId     | {attempt.id}                          |
      | SessionId     | {session.id}                          |
      | AmountMinor   | 1299                                  |
      | PaymentStatus | unpaid                                |
      | SessionStatus | complete                              |
      | PaymentIntent | null                                  |
      | Encoding      | normal                                |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-07"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "failed"           |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | null               |
      | state               | "ignored"          |
      | reason              | "already_terminal" |
      | received_at         | {request.window}   |
      | completed_at        | {request.window}   |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | failed             |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | "checkout_failed"  |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "failed"            |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | "checkout_failed"   |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-08 Ignore expiry of a canceled attempt
    A matching expiry targets a Canceled attempt. Its receipt is ignored as already_terminal without altering cancellation or history.
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
    And a lifecycle payment starts in
      | Field | Value    |
      | State | canceled |
    And the lifecycle event is prepared
      | Field         | Value                    |
      | EventId       | evt_pay08_08             |
      | EventType     | checkout.session.expired |
      | AttemptSource | current                  |
      | PaymentId     | {payment.id}             |
      | OrderId       | {order.id}               |
      | AttemptId     | {attempt.id}             |
      | SessionId     | {session.id}             |
      | AmountMinor   | 1299                     |
      | PaymentStatus | unpaid                   |
      | SessionStatus | expired                  |
      | PaymentIntent | null                     |
      | Encoding      | normal                   |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-08"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "expired"          |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | null               |
      | state               | "ignored"          |
      | reason              | "already_terminal" |
      | received_at         | {request.window}   |
      | completed_at        | {request.window}   |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | canceled           |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "canceled"          |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-09 Confirm late success of a canceled attempt
    A signed paid completion still identifies the same canceled attempt. Current policy accepts verified success and archives the complete canceled state.
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
    And a lifecycle payment starts in
      | Field | Value    |
      | State | canceled |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_09               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-09"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value               |
      | _id                 | {event.id}          |
      | event_type          | {event.type}        |
      | payload_digest      | {request.sha256}    |
      | outcome             | "succeeded"         |
      | payment_id          | {event.payment_id}  |
      | order_id            | {event.order_id}    |
      | attempt_id          | {event.attempt_id}  |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | session_id          | {event.session_id}  |
      | provider_payment_id | "pi_fixture"        |
      | state               | "applied"           |
      | reason              | "payment_succeeded" |
      | received_at         | {request.window}    |
      | completed_at        | {request.window}    |
      | fulfillment_status  | "pending"           |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 4                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 1                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-10 Ignore a distinct success for the same provider payment
    A different event identity reports the provider payment already confirmed. It records already_succeeded without another archive or fulfillment marker.
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
    And a lifecycle payment starts in
      | Field | Value     |
      | State | succeeded |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_10               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-10"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value               |
      | _id                 | {event.id}          |
      | event_type          | {event.type}        |
      | payload_digest      | {request.sha256}    |
      | outcome             | "succeeded"         |
      | payment_id          | {event.payment_id}  |
      | order_id            | {event.order_id}    |
      | attempt_id          | {event.attempt_id}  |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | session_id          | {event.session_id}  |
      | provider_payment_id | "pi_fixture"        |
      | state               | "ignored"           |
      | reason              | "already_succeeded" |
      | received_at         | {request.window}    |
      | completed_at        | {request.window}    |
      | fulfillment_status  | null                |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-11 Reject a different provider payment after success
    A distinct paid event reports another provider payment for an already successful attempt. Its receipt is rejected and the original provider reference is retained.
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
    And a lifecycle payment starts in
      | Field | Value     |
      | State | succeeded |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_11               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_other"                 |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-11"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
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
      | provider_payment_id | "pi_other"                  |
      | state               | "rejected"                  |
      | reason              | "provider_payment_mismatch" |
      | received_at         | {request.window}            |
      | completed_at        | {request.window}            |
      | fulfillment_status  | null                        |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-12 Reject a verified event for an absent payment
    Signed metadata and client reference consistently identify a missing payment. A full payment_not_found receipt is retained without changing populated collections.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And the lifecycle event is prepared
      | Field         | Value                                |
      | EventId       | evt_pay08_12                         |
      | EventType     | checkout.session.completed           |
      | AttemptSource | current                              |
      | PaymentId     | 88888888-8888-4888-8888-888888888888 |
      | OrderId       | {order.id}                           |
      | AttemptId     | {attempt.id}                         |
      | SessionId     | {session.id}                         |
      | AmountMinor   | 1299                                 |
      | PaymentStatus | paid                                 |
      | SessionStatus | complete                             |
      | PaymentIntent | "pi_fixture"                         |
      | Encoding      | normal                               |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-12"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value               |
      | _id                 | {event.id}          |
      | event_type          | {event.type}        |
      | payload_digest      | {request.sha256}    |
      | outcome             | "succeeded"         |
      | payment_id          | {event.payment_id}  |
      | order_id            | {event.order_id}    |
      | attempt_id          | {event.attempt_id}  |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | session_id          | {event.session_id}  |
      | provider_payment_id | "pi_fixture"        |
      | state               | "rejected"          |
      | reason              | "payment_not_found" |
      | received_at         | {request.window}    |
      | completed_at        | {request.window}    |
      | fulfillment_status  | null                |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-13 Reject a different order identity
    A valid signed event identifies the existing payment but another order. Processing records payment_mismatch without altering payment or history.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And the lifecycle event is prepared
      | Field         | Value                                |
      | EventId       | evt_pay08_13                         |
      | EventType     | checkout.session.completed           |
      | AttemptSource | current                              |
      | PaymentId     | {payment.id}                         |
      | OrderId       | 88888888-8888-4888-8888-888888888888 |
      | AttemptId     | {attempt.id}                         |
      | SessionId     | {session.id}                         |
      | AmountMinor   | 1299                                 |
      | PaymentStatus | paid                                 |
      | SessionStatus | complete                             |
      | PaymentIntent | "pi_fixture"                         |
      | Encoding      | normal                               |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-13"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "succeeded"        |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | "pi_fixture"       |
      | state               | "rejected"         |
      | reason              | "payment_mismatch" |
      | received_at         | {request.window}   |
      | completed_at        | {request.window}   |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-14 Reject a different checkout session
    A signed event matches money and attempt metadata but names another checkout session. The full rejected receipt records session_mismatch.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_14               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | "cs_test_other"            |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-14"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "succeeded"        |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | "pi_fixture"       |
      | state               | "rejected"         |
      | reason              | "session_mismatch" |
      | received_at         | {request.window}   |
      | completed_at        | {request.window}   |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value               |
      | Status                  | pending             |
      | Version                 | 2                   |
      | SessionId               | {before.session_id} |
      | ProviderPaymentId       | null                |
      | FailureCode             | null                |
      | NewArchives             | 0                   |
      | NewReceipts             | 1                   |
      | ExternalCalls           | 0                   |
      | ControlledInterruptions | 0                   |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-15 Ignore old success after a real checkout retry
    The previous attempt failed and the API opened a new reserved checkout. An authentic event for the old attempt is ignored as stale_attempt, preserving the full new state.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | retried |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_15               |
      | EventType     | checkout.session.completed |
      | AttemptSource | previous                   |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-15"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "succeeded"        |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | "pi_fixture"       |
      | state               | "ignored"          |
      | reason              | "stale_attempt"    |
      | received_at         | {request.window}   |
      | completed_at        | {request.window}   |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value               |
      | Status                  | pending             |
      | Version                 | 6                   |
      | SessionId               | {before.session_id} |
      | ProviderPaymentId       | null                |
      | FailureCode             | null                |
      | NewArchives             | 0                   |
      | NewReceipts             | 1                   |
      | ExternalCalls           | 0                   |
      | ControlledInterruptions | 0                   |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-16 Ignore old expiry after a real checkout retry
    The previous attempt failed and the API opened a new reserved checkout. An authentic event for the old attempt is ignored as stale_attempt, preserving the full new state.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | retried |
    And the lifecycle event is prepared
      | Field         | Value                    |
      | EventId       | evt_pay08_16             |
      | EventType     | checkout.session.expired |
      | AttemptSource | previous                 |
      | PaymentId     | {payment.id}             |
      | OrderId       | {order.id}               |
      | AttemptId     | {attempt.id}             |
      | SessionId     | {session.id}             |
      | AmountMinor   | 1299                     |
      | PaymentStatus | unpaid                   |
      | SessionStatus | expired                  |
      | PaymentIntent | null                     |
      | Encoding      | normal                   |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-16"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "expired"          |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | null               |
      | state               | "ignored"          |
      | reason              | "stale_attempt"    |
      | received_at         | {request.window}   |
      | completed_at        | {request.window}   |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value               |
      | Status                  | pending             |
      | Version                 | 6                   |
      | SessionId               | {before.session_id} |
      | ProviderPaymentId       | null                |
      | FailureCode             | null                |
      | NewArchives             | 0                   |
      | NewReceipts             | 1                   |
      | ExternalCalls           | 0                   |
      | ControlledInterruptions | 0                   |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-17 Ignore old failure after a real checkout retry
    The previous attempt failed and the API opened a new reserved checkout. An authentic event for the old attempt is ignored as stale_attempt, preserving the full new state.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | retried |
    And the lifecycle event is prepared
      | Field         | Value                                 |
      | EventId       | evt_pay08_17                          |
      | EventType     | checkout.session.async_payment_failed |
      | AttemptSource | previous                              |
      | PaymentId     | {payment.id}                          |
      | OrderId       | {order.id}                            |
      | AttemptId     | {attempt.id}                          |
      | SessionId     | {session.id}                          |
      | AmountMinor   | 1299                                  |
      | PaymentStatus | unpaid                                |
      | SessionStatus | complete                              |
      | PaymentIntent | null                                  |
      | Encoding      | normal                                |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-17"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "failed"           |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | null               |
      | state               | "ignored"          |
      | reason              | "stale_attempt"    |
      | received_at         | {request.window}   |
      | completed_at        | {request.window}   |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value               |
      | Status                  | pending             |
      | Version                 | 6                   |
      | SessionId               | {before.session_id} |
      | ProviderPaymentId       | null                |
      | FailureCode             | null                |
      | NewArchives             | 0                   |
      | NewReceipts             | 1                   |
      | ExternalCalls           | 0                   |
      | ControlledInterruptions | 0                   |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-18 Ignore notification for a legacy attemptless payment
    A historical Pending document physically lacks attempt fields. A verified former notification is ignored as stale_attempt while preserving the absent fields.
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
    And a lifecycle payment starts in
      | Field | Value          |
      | State | legacy_pending |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_18               |
      | EventType     | checkout.session.completed |
      | AttemptSource | previous                   |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-18"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "succeeded"        |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | "pi_fixture"       |
      | state               | "ignored"          |
      | reason              | "stale_attempt"    |
      | received_at         | {request.window}   |
      | completed_at        | {request.window}   |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-19 Confirm success before the session was persisted
    Only the Created reservation is stored when verified success arrives. One transaction records its session and provider payment, archives that reservation and completes durable work.
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
    And a lifecycle payment starts in
      | Field | Value    |
      | State | reserved |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_19               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-19"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value               |
      | _id                 | {event.id}          |
      | event_type          | {event.type}        |
      | payload_digest      | {request.sha256}    |
      | outcome             | "succeeded"         |
      | payment_id          | {event.payment_id}  |
      | order_id            | {event.order_id}    |
      | attempt_id          | {event.attempt_id}  |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | session_id          | {event.session_id}  |
      | provider_payment_id | "pi_fixture"        |
      | state               | "applied"           |
      | reason              | "payment_succeeded" |
      | received_at         | {request.window}    |
      | completed_at        | {request.window}    |
      | fulfillment_status  | "pending"           |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 1                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-20 Fail a reserved checkout before its session was persisted
    An asynchronous failure arrives while only the Created reservation is stored. Pending and Failed domain changes persist as one version with one full reservation archive.
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
    And a lifecycle payment starts in
      | Field | Value    |
      | State | reserved |
    And the lifecycle event is prepared
      | Field         | Value                                 |
      | EventId       | evt_pay08_20                          |
      | EventType     | checkout.session.async_payment_failed |
      | AttemptSource | current                               |
      | PaymentId     | {payment.id}                          |
      | OrderId       | {order.id}                            |
      | AttemptId     | {attempt.id}                          |
      | SessionId     | {session.id}                          |
      | AmountMinor   | 1299                                  |
      | PaymentStatus | unpaid                                |
      | SessionStatus | complete                              |
      | PaymentIntent | null                                  |
      | Encoding      | normal                                |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-20"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "failed"           |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | null               |
      | state               | "applied"          |
      | reason              | "payment_failed"   |
      | received_at         | {request.window}   |
      | completed_at        | {request.window}   |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | failed             |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | "checkout_failed"  |
      | NewArchives             | 1                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "failed"            |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | "checkout_failed"   |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-21 Expire a reserved checkout before its session was persisted
    A signed expiry targets the current Created reservation. It stores the session and checkout_expired failure in one version without scheduling fulfillment.
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
    And a lifecycle payment starts in
      | Field | Value    |
      | State | reserved |
    And the lifecycle event is prepared
      | Field         | Value                    |
      | EventId       | evt_pay08_21             |
      | EventType     | checkout.session.expired |
      | AttemptSource | current                  |
      | PaymentId     | {payment.id}             |
      | OrderId       | {order.id}               |
      | AttemptId     | {attempt.id}             |
      | SessionId     | {session.id}             |
      | AmountMinor   | 1299                     |
      | PaymentStatus | unpaid                   |
      | SessionStatus | expired                  |
      | PaymentIntent | null                     |
      | Encoding      | normal                   |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-21"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "expired"          |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | null               |
      | state               | "applied"          |
      | reason              | "payment_failed"   |
      | received_at         | {request.window}   |
      | completed_at        | {request.window}   |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | failed             |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | "checkout_expired" |
      | NewArchives             | 1                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "failed"            |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | "checkout_expired"  |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-22 Reject different signed bytes for an applied event
    An earlier verified delivery owns this event identity. Different newly signed bytes return webhook_collision and preserve the complete original receipt and all populated collections.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_22               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And the lifecycle event was delivered
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_22               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | trailing_space             |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-22"
      | Field                  | Value                                          |
      | HTTPStatuses           | 400                                            |
      | ContentType            | application/problem+json                       |
      | Code                   | webhook_collision                              |
      | JSON.type              | "about:blank"                                  |
      | JSON.title             | "Bad Request"                                  |
      | JSON.status            | 400                                            |
      | JSON.detail            | "Webhook identity conflicts with its receipt." |
      | JSON.instance          | "/payments/webhooks/stripe"                    |
      | JSON.errors            | []                                             |
      | JSON.missingProperties | []                                             |
    And the complete lifecycle receipt is
      | Field               | Value                   |
      | _id                 | {event.id}              |
      | event_type          | {event.type}            |
      | payload_digest      | {before.payload_digest} |
      | outcome             | "succeeded"             |
      | payment_id          | {event.payment_id}      |
      | order_id            | {event.order_id}        |
      | attempt_id          | {event.attempt_id}      |
      | amount_minor        | 1299                    |
      | currency            | "PLN"                   |
      | session_id          | {event.session_id}      |
      | provider_payment_id | "pi_fixture"            |
      | state               | "applied"               |
      | reason              | "payment_succeeded"     |
      | received_at         | {before.received_at}    |
      | completed_at        | {before.completed_at}   |
      | fulfillment_status  | "pending"               |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 0                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-23 Reject another payload for an applied event identity
    An earlier verified delivery owns this event identity. Different newly signed bytes return webhook_collision and preserve the complete original receipt and all populated collections.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_23               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And the lifecycle event was delivered
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_23               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_other"                 |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-23"
      | Field                  | Value                                          |
      | HTTPStatuses           | 400                                            |
      | ContentType            | application/problem+json                       |
      | Code                   | webhook_collision                              |
      | JSON.type              | "about:blank"                                  |
      | JSON.title             | "Bad Request"                                  |
      | JSON.status            | 400                                            |
      | JSON.detail            | "Webhook identity conflicts with its receipt." |
      | JSON.instance          | "/payments/webhooks/stripe"                    |
      | JSON.errors            | []                                             |
      | JSON.missingProperties | []                                             |
    And the complete lifecycle receipt is
      | Field               | Value                   |
      | _id                 | {event.id}              |
      | event_type          | {event.type}            |
      | payload_digest      | {before.payload_digest} |
      | outcome             | "succeeded"             |
      | payment_id          | {event.payment_id}      |
      | order_id            | {event.order_id}        |
      | attempt_id          | {event.attempt_id}      |
      | amount_minor        | 1299                    |
      | currency            | "PLN"                   |
      | session_id          | {event.session_id}      |
      | provider_payment_id | "pi_fixture"            |
      | state               | "applied"               |
      | reason              | "payment_succeeded"     |
      | received_at         | {before.received_at}    |
      | completed_at        | {before.completed_at}   |
      | fulfillment_status  | "pending"               |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 0                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-24 Reject a collision without replacing pending work
    An earlier verified delivery owns this event identity. Different newly signed bytes return webhook_collision and preserve the complete original receipt and all populated collections.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_24               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And lifecycle completion is interrupted
      | Field    | Value             |
      | Point    | before_completion |
      | Failures | 1                 |
    And the lifecycle event was delivered
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_24               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | trailing_space             |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-24"
      | Field                  | Value                                          |
      | HTTPStatuses           | 400                                            |
      | ContentType            | application/problem+json                       |
      | Code                   | webhook_collision                              |
      | JSON.type              | "about:blank"                                  |
      | JSON.title             | "Bad Request"                                  |
      | JSON.status            | 400                                            |
      | JSON.detail            | "Webhook identity conflicts with its receipt." |
      | JSON.instance          | "/payments/webhooks/stripe"                    |
      | JSON.errors            | []                                             |
      | JSON.missingProperties | []                                             |
    And the complete lifecycle receipt is
      | Field               | Value                   |
      | _id                 | {event.id}              |
      | event_type          | {event.type}            |
      | payload_digest      | {before.payload_digest} |
      | outcome             | "succeeded"             |
      | payment_id          | {event.payment_id}      |
      | order_id            | {event.order_id}        |
      | attempt_id          | {event.attempt_id}      |
      | amount_minor        | 1299                    |
      | currency            | "PLN"                   |
      | session_id          | {event.session_id}      |
      | provider_payment_id | "pi_fixture"            |
      | state               | "pending"               |
      | reason              | null                    |
      | received_at         | {before.received_at}    |
      | completed_at        | null                    |
      | fulfillment_status  | null                    |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 0                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 1                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-25 Reject a collision with an ignored receipt
    An earlier verified delivery owns this event identity. Different newly signed bytes return webhook_collision and preserve the complete original receipt and all populated collections.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_25               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | unpaid                     |
      | SessionStatus | complete                   |
      | PaymentIntent | null                       |
      | Encoding      | normal                     |
    And the lifecycle event was delivered
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_25               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | unpaid                     |
      | SessionStatus | complete                   |
      | PaymentIntent | null                       |
      | Encoding      | trailing_space             |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-25"
      | Field                  | Value                                          |
      | HTTPStatuses           | 400                                            |
      | ContentType            | application/problem+json                       |
      | Code                   | webhook_collision                              |
      | JSON.type              | "about:blank"                                  |
      | JSON.title             | "Bad Request"                                  |
      | JSON.status            | 400                                            |
      | JSON.detail            | "Webhook identity conflicts with its receipt." |
      | JSON.instance          | "/payments/webhooks/stripe"                    |
      | JSON.errors            | []                                             |
      | JSON.missingProperties | []                                             |
    And the complete lifecycle receipt is
      | Field               | Value                   |
      | _id                 | {event.id}              |
      | event_type          | {event.type}            |
      | payload_digest      | {before.payload_digest} |
      | outcome             | "waiting"               |
      | payment_id          | {event.payment_id}      |
      | order_id            | {event.order_id}        |
      | attempt_id          | {event.attempt_id}      |
      | amount_minor        | 1299                    |
      | currency            | "PLN"                   |
      | session_id          | {event.session_id}      |
      | provider_payment_id | null                    |
      | state               | "ignored"               |
      | reason              | "awaiting_payment"      |
      | received_at         | {before.received_at}    |
      | completed_at        | {before.completed_at}   |
      | fulfillment_status  | null                    |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 0                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-26 Redeliver an ignored event without rewriting its receipt
    The identical waiting event was already ignored. Redelivery preserves both receipt timestamps and every payment, history and unrelated receipt field.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_26               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | unpaid                     |
      | SessionStatus | complete                   |
      | PaymentIntent | null                       |
      | Encoding      | normal                     |
    And the lifecycle event was delivered
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_26               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | unpaid                     |
      | SessionStatus | complete                   |
      | PaymentIntent | null                       |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-26"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value                 |
      | _id                 | {event.id}            |
      | event_type          | {event.type}          |
      | payload_digest      | {request.sha256}      |
      | outcome             | "waiting"             |
      | payment_id          | {event.payment_id}    |
      | order_id            | {event.order_id}      |
      | attempt_id          | {event.attempt_id}    |
      | amount_minor        | 1299                  |
      | currency            | "PLN"                 |
      | session_id          | {event.session_id}    |
      | provider_payment_id | null                  |
      | state               | "ignored"             |
      | reason              | "awaiting_payment"    |
      | received_at         | {before.received_at}  |
      | completed_at        | {before.completed_at} |
      | fulfillment_status  | null                  |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 0                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-27 Redeliver a rejected event without rewriting its receipt
    The identical mismatched-order event was already rejected. Redelivery acknowledges the stored rejection without another receipt or state change.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And the lifecycle event is prepared
      | Field         | Value                                |
      | EventId       | evt_pay08_27                         |
      | EventType     | checkout.session.completed           |
      | AttemptSource | current                              |
      | PaymentId     | {payment.id}                         |
      | OrderId       | 88888888-8888-4888-8888-888888888888 |
      | AttemptId     | {attempt.id}                         |
      | SessionId     | {session.id}                         |
      | AmountMinor   | 1299                                 |
      | PaymentStatus | paid                                 |
      | SessionStatus | complete                             |
      | PaymentIntent | "pi_fixture"                         |
      | Encoding      | normal                               |
    And the lifecycle event was delivered
    And the lifecycle event is prepared
      | Field         | Value                                |
      | EventId       | evt_pay08_27                         |
      | EventType     | checkout.session.completed           |
      | AttemptSource | current                              |
      | PaymentId     | {payment.id}                         |
      | OrderId       | 88888888-8888-4888-8888-888888888888 |
      | AttemptId     | {attempt.id}                         |
      | SessionId     | {session.id}                         |
      | AmountMinor   | 1299                                 |
      | PaymentStatus | paid                                 |
      | SessionStatus | complete                             |
      | PaymentIntent | "pi_fixture"                         |
      | Encoding      | normal                               |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-27"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value                 |
      | _id                 | {event.id}            |
      | event_type          | {event.type}          |
      | payload_digest      | {request.sha256}      |
      | outcome             | "succeeded"           |
      | payment_id          | {event.payment_id}    |
      | order_id            | {event.order_id}      |
      | attempt_id          | {event.attempt_id}    |
      | amount_minor        | 1299                  |
      | currency            | "PLN"                 |
      | session_id          | {event.session_id}    |
      | provider_payment_id | "pi_fixture"          |
      | state               | "rejected"            |
      | reason              | "payment_mismatch"    |
      | received_at         | {before.received_at}  |
      | completed_at        | {before.completed_at} |
      | fulfillment_status  | null                  |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 0                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 0                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-28 A fresh application resumes a pending receipt
    Completion is interrupted after durable receipt insertion. A new application instance redelivers the same signed bytes and commits exactly one payment transition.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And lifecycle completion is interrupted
      | Field    | Value             |
      | Point    | before_completion |
      | Failures | 1                 |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_28               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-28"
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
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "succeeded"        |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | "pi_fixture"       |
      | state               | "pending"          |
      | reason              | null               |
      | received_at         | {request.window}   |
      | completed_at        | null               |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 1                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And durable webhook recovery runs with
      | Field          | Value      |
      | Mode           | fresh_http |
      | FirstResult    | 200        |
      | RepeatedResult | 200        |
    And the complete lifecycle receipt is
      | Field               | Value                |
      | _id                 | {event.id}           |
      | event_type          | {event.type}         |
      | payload_digest      | {request.sha256}     |
      | outcome             | "succeeded"          |
      | payment_id          | {event.payment_id}   |
      | order_id            | {event.order_id}     |
      | attempt_id          | {event.attempt_id}   |
      | amount_minor        | 1299                 |
      | currency            | "PLN"                |
      | session_id          | {event.session_id}   |
      | provider_payment_id | "pi_fixture"         |
      | state               | "applied"            |
      | reason              | "payment_succeeded"  |
      | received_at         | {before.received_at} |
      | completed_at        | {request.window}     |
      | fulfillment_status  | "pending"            |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 1                  |
      | NewReceipts             | 0                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 1                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-29 An operator resumes success without provider credentials
    A signed HTTP delivery durably receives normalized work but cannot complete it. A fresh operator replay without Stripe credentials completes that receipt; another replay processes zero and preserves every field.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And lifecycle completion is interrupted
      | Field    | Value             |
      | Point    | before_completion |
      | Failures | 1                 |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_29               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-29"
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
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "succeeded"        |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | "pi_fixture"       |
      | state               | "pending"          |
      | reason              | null               |
      | received_at         | {request.window}   |
      | completed_at        | null               |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 1                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And durable webhook recovery runs with
      | Field          | Value    |
      | Mode           | operator |
      | FirstResult    | 1        |
      | RepeatedResult | 0        |
    And the complete lifecycle receipt is
      | Field               | Value                |
      | _id                 | {event.id}           |
      | event_type          | {event.type}         |
      | payload_digest      | {request.sha256}     |
      | outcome             | "succeeded"          |
      | payment_id          | {event.payment_id}   |
      | order_id            | {event.order_id}     |
      | attempt_id          | {event.attempt_id}   |
      | amount_minor        | 1299                 |
      | currency            | "PLN"                |
      | session_id          | {event.session_id}   |
      | provider_payment_id | "pi_fixture"         |
      | state               | "applied"            |
      | reason              | "payment_succeeded"  |
      | received_at         | {before.received_at} |
      | completed_at        | {request.window}     |
      | fulfillment_status  | "pending"            |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 1                  |
      | NewReceipts             | 0                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 1                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-30 An operator completes an unsupported pending event
    A signed HTTP delivery durably receives normalized work but cannot complete it. A fresh operator replay without Stripe credentials completes that receipt; another replay processes zero and preserves every field.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And lifecycle completion is interrupted
      | Field    | Value             |
      | Point    | before_completion |
      | Failures | 1                 |
    And the lifecycle event is prepared
      | Field         | Value                         |
      | EventId       | evt_pay08_30                  |
      | EventType     | payment_intent.payment_failed |
      | AttemptSource | current                       |
      | PaymentId     | {payment.id}                  |
      | OrderId       | {order.id}                    |
      | AttemptId     | {attempt.id}                  |
      | SessionId     | {session.id}                  |
      | AmountMinor   | 1299                          |
      | PaymentStatus | paid                          |
      | SessionStatus | complete                      |
      | PaymentIntent | "pi_fixture"                  |
      | Encoding      | normal                        |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-30"
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
    And the complete lifecycle receipt is
      | Field               | Value            |
      | _id                 | {event.id}       |
      | event_type          | {event.type}     |
      | payload_digest      | {request.sha256} |
      | outcome             | "unknown"        |
      | payment_id          | null             |
      | order_id            | null             |
      | attempt_id          | null             |
      | amount_minor        | null             |
      | currency            | null             |
      | session_id          | null             |
      | provider_payment_id | null             |
      | state               | "pending"        |
      | reason              | null             |
      | received_at         | {request.window} |
      | completed_at        | null             |
      | fulfillment_status  | null             |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 1                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And durable webhook recovery runs with
      | Field          | Value    |
      | Mode           | operator |
      | FirstResult    | 1        |
      | RepeatedResult | 0        |
    And the complete lifecycle receipt is
      | Field               | Value                |
      | _id                 | {event.id}           |
      | event_type          | {event.type}         |
      | payload_digest      | {request.sha256}     |
      | outcome             | "unknown"            |
      | payment_id          | null                 |
      | order_id            | null                 |
      | attempt_id          | null                 |
      | amount_minor        | null                 |
      | currency            | null                 |
      | session_id          | null                 |
      | provider_payment_id | null                 |
      | state               | "ignored"            |
      | reason              | "unsupported_event"  |
      | received_at         | {before.received_at} |
      | completed_at        | {request.window}     |
      | fulfillment_status  | null                 |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 0                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 1                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-31 An operator completes a mismatched pending event
    A signed HTTP delivery durably receives normalized work but cannot complete it. A fresh operator replay without Stripe credentials completes that receipt; another replay processes zero and preserves every field.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And lifecycle completion is interrupted
      | Field    | Value             |
      | Point    | before_completion |
      | Failures | 1                 |
    And the lifecycle event is prepared
      | Field         | Value                                |
      | EventId       | evt_pay08_31                         |
      | EventType     | checkout.session.completed           |
      | AttemptSource | current                              |
      | PaymentId     | {payment.id}                         |
      | OrderId       | 88888888-8888-4888-8888-888888888888 |
      | AttemptId     | {attempt.id}                         |
      | SessionId     | {session.id}                         |
      | AmountMinor   | 1299                                 |
      | PaymentStatus | paid                                 |
      | SessionStatus | complete                             |
      | PaymentIntent | "pi_fixture"                         |
      | Encoding      | normal                               |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-31"
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
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "succeeded"        |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | "pi_fixture"       |
      | state               | "pending"          |
      | reason              | null               |
      | received_at         | {request.window}   |
      | completed_at        | null               |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 1                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And durable webhook recovery runs with
      | Field          | Value    |
      | Mode           | operator |
      | FirstResult    | 1        |
      | RepeatedResult | 0        |
    And the complete lifecycle receipt is
      | Field               | Value                |
      | _id                 | {event.id}           |
      | event_type          | {event.type}         |
      | payload_digest      | {request.sha256}     |
      | outcome             | "succeeded"          |
      | payment_id          | {event.payment_id}   |
      | order_id            | {event.order_id}     |
      | attempt_id          | {event.attempt_id}   |
      | amount_minor        | 1299                 |
      | currency            | "PLN"                |
      | session_id          | {event.session_id}   |
      | provider_payment_id | "pi_fixture"         |
      | state               | "rejected"           |
      | reason              | "payment_mismatch"   |
      | received_at         | {before.received_at} |
      | completed_at        | {request.window}     |
      | fulfillment_status  | null                 |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 0                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 1                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-32 An operator ignores pending work from an old attempt
    A signed HTTP delivery durably receives normalized work but cannot complete it. A fresh operator replay without Stripe credentials completes that receipt; another replay processes zero and preserves every field.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | retried |
    And lifecycle completion is interrupted
      | Field    | Value             |
      | Point    | before_completion |
      | Failures | 1                 |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_32               |
      | EventType     | checkout.session.completed |
      | AttemptSource | previous                   |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-32"
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
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "succeeded"        |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | "pi_fixture"       |
      | state               | "pending"          |
      | reason              | null               |
      | received_at         | {request.window}   |
      | completed_at        | null               |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value               |
      | Status                  | pending             |
      | Version                 | 6                   |
      | SessionId               | {before.session_id} |
      | ProviderPaymentId       | null                |
      | FailureCode             | null                |
      | NewArchives             | 0                   |
      | NewReceipts             | 1                   |
      | ExternalCalls           | 0                   |
      | ControlledInterruptions | 1                   |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
    And durable webhook recovery runs with
      | Field          | Value    |
      | Mode           | operator |
      | FirstResult    | 1        |
      | RepeatedResult | 0        |
    And the complete lifecycle receipt is
      | Field               | Value                |
      | _id                 | {event.id}           |
      | event_type          | {event.type}         |
      | payload_digest      | {request.sha256}     |
      | outcome             | "succeeded"          |
      | payment_id          | {event.payment_id}   |
      | order_id            | {event.order_id}     |
      | attempt_id          | {event.attempt_id}   |
      | amount_minor        | 1299                 |
      | currency            | "PLN"                |
      | session_id          | {event.session_id}   |
      | provider_payment_id | "pi_fixture"         |
      | state               | "ignored"            |
      | reason              | "stale_attempt"      |
      | received_at         | {before.received_at} |
      | completed_at        | {request.window}     |
      | fulfillment_status  | null                 |
    And webhook processing changes exactly this state
      | Field                   | Value               |
      | Status                  | pending             |
      | Version                 | 6                   |
      | SessionId               | {before.session_id} |
      | ProviderPaymentId       | null                |
      | FailureCode             | null                |
      | NewArchives             | 0                   |
      | NewReceipts             | 0                   |
      | ExternalCalls           | 0                   |
      | ControlledInterruptions | 1                   |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |

  Scenario: PAY08-33 Redelivery recovers an acknowledgement lost after commit
    The real receipt/payment/history transaction commits before a controlled completion acknowledgement is lost. A fresh application acknowledges the stored result without a second transition.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And lifecycle completion is interrupted
      | Field    | Value            |
      | Point    | after_completion |
      | Failures | 1                |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_33               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-33"
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
    And the complete lifecycle receipt is
      | Field               | Value               |
      | _id                 | {event.id}          |
      | event_type          | {event.type}        |
      | payload_digest      | {request.sha256}    |
      | outcome             | "succeeded"         |
      | payment_id          | {event.payment_id}  |
      | order_id            | {event.order_id}    |
      | attempt_id          | {event.attempt_id}  |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | session_id          | {event.session_id}  |
      | provider_payment_id | "pi_fixture"        |
      | state               | "applied"           |
      | reason              | "payment_succeeded" |
      | received_at         | {request.window}    |
      | completed_at        | {request.window}    |
      | fulfillment_status  | "pending"           |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 1                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 1                  |
    And the complete payment read after webhook is
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
    And durable webhook recovery runs with
      | Field          | Value      |
      | Mode           | fresh_http |
      | FirstResult    | 200        |
      | RepeatedResult | 200        |
    And the complete lifecycle receipt is
      | Field               | Value                 |
      | _id                 | {event.id}            |
      | event_type          | {event.type}          |
      | payload_digest      | {request.sha256}      |
      | outcome             | "succeeded"           |
      | payment_id          | {event.payment_id}    |
      | order_id            | {event.order_id}      |
      | attempt_id          | {event.attempt_id}    |
      | amount_minor        | 1299                  |
      | currency            | "PLN"                 |
      | session_id          | {event.session_id}    |
      | provider_payment_id | "pi_fixture"          |
      | state               | "applied"             |
      | reason              | "payment_succeeded"   |
      | received_at         | {before.received_at}  |
      | completed_at        | {before.completed_at} |
      | fulfillment_status  | "pending"             |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 0                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 1                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-34 Reload once after a controlled stale version
    One completion attempt reports a controlled payment conflict before any transaction. The service reloads the same receipt and commits once with no partial state.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And lifecycle completion is interrupted
      | Field    | Value    |
      | Point    | conflict |
      | Failures | 1        |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_34               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-34"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the complete lifecycle receipt is
      | Field               | Value               |
      | _id                 | {event.id}          |
      | event_type          | {event.type}        |
      | payload_digest      | {request.sha256}    |
      | outcome             | "succeeded"         |
      | payment_id          | {event.payment_id}  |
      | order_id            | {event.order_id}    |
      | attempt_id          | {event.attempt_id}  |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | session_id          | {event.session_id}  |
      | provider_payment_id | "pi_fixture"        |
      | state               | "applied"           |
      | reason              | "payment_succeeded" |
      | received_at         | {request.window}    |
      | completed_at        | {request.window}    |
      | fulfillment_status  | "pending"           |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | succeeded          |
      | Version                 | 3                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | "pi_fixture"       |
      | FailureCode             | null               |
      | NewArchives             | 1                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 1                  |
    And the complete payment read after webhook is
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

  Scenario: PAY08-35 Leave durable work after exhausting conflict retries
    All four completion attempts report controlled stale versions before a transaction. The safe retry response leaves the complete receipt pending and all payment/history fields unchanged.
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
    And a lifecycle payment starts in
      | Field | Value   |
      | State | pending |
    And lifecycle completion is interrupted
      | Field    | Value    |
      | Point    | conflict |
      | Failures | 4        |
    And the lifecycle event is prepared
      | Field         | Value                      |
      | EventId       | evt_pay08_35               |
      | EventType     | checkout.session.completed |
      | AttemptSource | current                    |
      | PaymentId     | {payment.id}               |
      | OrderId       | {order.id}                 |
      | AttemptId     | {attempt.id}               |
      | SessionId     | {session.id}               |
      | AmountMinor   | 1299                       |
      | PaymentStatus | paid                       |
      | SessionStatus | complete                   |
      | PaymentIntent | "pi_fixture"               |
      | Encoding      | normal                     |
    And I remember complete webhook lifecycle state
    When I deliver the lifecycle event
    Then the response matches case "PAY08-35"
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
    And the complete lifecycle receipt is
      | Field               | Value              |
      | _id                 | {event.id}         |
      | event_type          | {event.type}       |
      | payload_digest      | {request.sha256}   |
      | outcome             | "succeeded"        |
      | payment_id          | {event.payment_id} |
      | order_id            | {event.order_id}   |
      | attempt_id          | {event.attempt_id} |
      | amount_minor        | 1299               |
      | currency            | "PLN"              |
      | session_id          | {event.session_id} |
      | provider_payment_id | "pi_fixture"       |
      | state               | "pending"          |
      | reason              | null               |
      | received_at         | {request.window}   |
      | completed_at        | null               |
      | fulfillment_status  | null               |
    And webhook processing changes exactly this state
      | Field                   | Value              |
      | Status                  | pending            |
      | Version                 | 2                  |
      | SessionId               | {event.session_id} |
      | ProviderPaymentId       | null               |
      | FailureCode             | null               |
      | NewArchives             | 0                  |
      | NewReceipts             | 1                  |
      | ExternalCalls           | 0                  |
      | ControlledInterruptions | 4                  |
    And the complete payment read after webhook is
      | Field               | Value               |
      | id                  | {stored.id}         |
      | order_id            | {order.id}          |
      | amount_minor        | 1299                |
      | currency            | "PLN"               |
      | status              | "pending"           |
      | provider_session_id | {stored.session_id} |
      | provider_payment_id | null                |
      | failure_code        | null                |
      | created_at          | {stored.created_at} |
      | updated_at          | {stored.updated_at} |
