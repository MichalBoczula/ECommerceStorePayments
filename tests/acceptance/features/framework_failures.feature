Feature: Complete framework failures with populated state

  Scenario: PAY11-23 Reject POST at the compatibility health alias
    The actual POST request to /health uses none input. Both deliveries return the complete safe 405/method_not_allowed problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /health                          |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-23"
      | Field                  | Value                                   |
      | HTTPStatuses           | 405                                     |
      | ContentType            | application/problem+json                |
      | Code                   | method_not_allowed                      |
      | JSON.type              | "about:blank"                           |
      | JSON.title             | "Method Not Allowed"                    |
      | JSON.status            | 405                                     |
      | JSON.detail            | "Method is not allowed for this route." |
      | JSON.instance          | "/health"                               |
      | JSON.errors            | []                                      |
      | JSON.missingProperties | []                                      |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | GET       |
      | FaultHits        | 0         |

  Scenario: PAY11-24 Reject POST at readiness
    The actual POST request to /health/ready uses none input. Both deliveries return the complete safe 405/method_not_allowed problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /health/ready                    |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-24"
      | Field                  | Value                                   |
      | HTTPStatuses           | 405                                     |
      | ContentType            | application/problem+json                |
      | Code                   | method_not_allowed                      |
      | JSON.type              | "about:blank"                           |
      | JSON.title             | "Method Not Allowed"                    |
      | JSON.status            | 405                                     |
      | JSON.detail            | "Method is not allowed for this route." |
      | JSON.instance          | "/health/ready"                         |
      | JSON.errors            | []                                      |
      | JSON.missingProperties | []                                      |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | GET       |
      | FaultHits        | 0         |

  Scenario: PAY11-25 Reject GET at Pay
    The actual GET request to /payments/{order_id}/pay uses none input. Both deliveries return the complete safe 405/method_not_allowed problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | GET                              |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-25"
      | Field                  | Value                                                |
      | HTTPStatuses           | 405                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | method_not_allowed                                   |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Method Not Allowed"                                 |
      | JSON.status            | 405                                                  |
      | JSON.detail            | "Method is not allowed for this route."              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | POST      |
      | FaultHits        | 0         |

  Scenario: PAY11-26 Reject GET at Checkout
    The actual GET request to /payments/{order_id}/checkout uses none input. Both deliveries return the complete safe 405/method_not_allowed problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | GET                              |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-26"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 405                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | method_not_allowed                                        |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Method Not Allowed"                                      |
      | JSON.status            | 405                                                       |
      | JSON.detail            | "Method is not allowed for this route."                   |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | POST      |
      | FaultHits        | 0         |

  Scenario: PAY11-27 Reject POST at payment reads
    The actual POST request to /payments/order/{order_id} uses none input. Both deliveries return the complete safe 405/method_not_allowed problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/order/{order_id}       |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-27"
      | Field                  | Value                                                  |
      | HTTPStatuses           | 405                                                    |
      | ContentType            | application/problem+json                               |
      | Code                   | method_not_allowed                                     |
      | JSON.type              | "about:blank"                                          |
      | JSON.title             | "Method Not Allowed"                                   |
      | JSON.status            | 405                                                    |
      | JSON.detail            | "Method is not allowed for this route."                |
      | JSON.instance          | "/payments/order/11111111-1111-4111-8111-111111111111" |
      | JSON.errors            | []                                                     |
      | JSON.missingProperties | []                                                     |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | GET       |
      | FaultHits        | 0         |

  Scenario: PAY11-28 Reject GET at the Stripe webhook
    The actual GET request to /payments/webhooks/stripe uses none input. Both deliveries return the complete safe 405/method_not_allowed problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | GET                              |
      | Path        | /payments/webhooks/stripe        |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-28"
      | Field                  | Value                                   |
      | HTTPStatuses           | 405                                     |
      | ContentType            | application/problem+json                |
      | Code                   | method_not_allowed                      |
      | JSON.type              | "about:blank"                           |
      | JSON.title             | "Method Not Allowed"                    |
      | JSON.status            | 405                                     |
      | JSON.detail            | "Method is not allowed for this route." |
      | JSON.instance          | "/payments/webhooks/stripe"             |
      | JSON.errors            | []                                      |
      | JSON.missingProperties | []                                      |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | POST      |
      | FaultHits        | 0         |

  Scenario: PAY11-29 Hide an unexpected compatibility health failure
    The actual GET request to /health uses none input. Both deliveries return the complete safe 500/internal_error problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request. The report records an explicit HealthResponse RuntimeError boundary rather than presenting an injected fault as a natural outage.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | GET                              |
      | Path        | /health                          |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    And this framework failure is installed
      | Field     | Value          |
      | Point     | HealthResponse |
      | Exception | RuntimeError   |
    When I submit the prepared framework request
    Then the response matches case "PAY11-29"
      | Field                  | Value                           |
      | HTTPStatuses           | 500                             |
      | ContentType            | application/problem+json        |
      | Code                   | internal_error                  |
      | JSON.type              | "about:blank"                   |
      | JSON.title             | "Internal Server Error"         |
      | JSON.status            | 500                             |
      | JSON.detail            | "An unexpected error occurred." |
      | JSON.instance          | "/health"                       |
      | JSON.errors            | []                              |
      | JSON.missingProperties | []                              |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 2         |

  Scenario: PAY11-30 Hide an unexpected liveness failure
    The actual GET request to /health/live uses none input. Both deliveries return the complete safe 500/internal_error problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request. The report records an explicit HealthResponse RuntimeError boundary rather than presenting an injected fault as a natural outage.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | GET                              |
      | Path        | /health/live                     |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    And this framework failure is installed
      | Field     | Value          |
      | Point     | HealthResponse |
      | Exception | RuntimeError   |
    When I submit the prepared framework request
    Then the response matches case "PAY11-30"
      | Field                  | Value                           |
      | HTTPStatuses           | 500                             |
      | ContentType            | application/problem+json        |
      | Code                   | internal_error                  |
      | JSON.type              | "about:blank"                   |
      | JSON.title             | "Internal Server Error"         |
      | JSON.status            | 500                             |
      | JSON.detail            | "An unexpected error occurred." |
      | JSON.instance          | "/health/live"                  |
      | JSON.errors            | []                              |
      | JSON.missingProperties | []                              |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 2         |

  Scenario: PAY11-31 Hide an unexpected failure after a real readiness probe
    The actual GET request to /health/ready uses none input. Both deliveries return the complete safe 500/internal_error problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request. The report records an explicit MongoDatabase.probe RuntimeError boundary rather than presenting an injected fault as a natural outage.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | GET                              |
      | Path        | /health/ready                    |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    And this framework failure is installed
      | Field     | Value               |
      | Point     | MongoDatabase.probe |
      | Exception | RuntimeError        |
    When I submit the prepared framework request
    Then the response matches case "PAY11-31"
      | Field                  | Value                           |
      | HTTPStatuses           | 500                             |
      | ContentType            | application/problem+json        |
      | Code                   | internal_error                  |
      | JSON.type              | "about:blank"                   |
      | JSON.title             | "Internal Server Error"         |
      | JSON.status            | 500                             |
      | JSON.detail            | "An unexpected error occurred." |
      | JSON.instance          | "/health/ready"                 |
      | JSON.errors            | []                              |
      | JSON.missingProperties | []                              |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 2         |

  Scenario: PAY11-32 Hide an unexpected Pay delegation failure
    The actual POST request to /payments/{order_id}/pay uses none input. Both deliveries return the complete safe 500/internal_error problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request. The report records an explicit PaymentService.pay RuntimeError boundary rather than presenting an injected fault as a natural outage.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    And this framework failure is installed
      | Field     | Value              |
      | Point     | PaymentService.pay |
      | Exception | RuntimeError       |
    When I submit the prepared framework request
    Then the response matches case "PAY11-32"
      | Field                  | Value                                                |
      | HTTPStatuses           | 500                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | internal_error                                       |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Internal Server Error"                              |
      | JSON.status            | 500                                                  |
      | JSON.detail            | "An unexpected error occurred."                      |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 2         |

  Scenario: PAY11-33 Hide an unexpected Checkout delegation failure
    The actual POST request to /payments/{order_id}/checkout uses none input. Both deliveries return the complete safe 500/internal_error problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request. The report records an explicit PaymentService.checkout RuntimeError boundary rather than presenting an injected fault as a natural outage.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    And this framework failure is installed
      | Field     | Value                   |
      | Point     | PaymentService.checkout |
      | Exception | RuntimeError            |
    When I submit the prepared framework request
    Then the response matches case "PAY11-33"
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
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 2         |

  Scenario: PAY11-34 Hide an unexpected payment-read delegation failure
    The actual GET request to /payments/order/{order_id} uses none input. Both deliveries return the complete safe 500/internal_error problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request. The report records an explicit PaymentService.get_by_order_id RuntimeError boundary rather than presenting an injected fault as a natural outage.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | GET                              |
      | Path        | /payments/order/{order_id}       |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    And this framework failure is installed
      | Field     | Value                          |
      | Point     | PaymentService.get_by_order_id |
      | Exception | RuntimeError                   |
    When I submit the prepared framework request
    Then the response matches case "PAY11-34"
      | Field                  | Value                                                  |
      | HTTPStatuses           | 500                                                    |
      | ContentType            | application/problem+json                               |
      | Code                   | internal_error                                         |
      | JSON.type              | "about:blank"                                          |
      | JSON.title             | "Internal Server Error"                                |
      | JSON.status            | 500                                                    |
      | JSON.detail            | "An unexpected error occurred."                        |
      | JSON.instance          | "/payments/order/11111111-1111-4111-8111-111111111111" |
      | JSON.errors            | []                                                     |
      | JSON.missingProperties | []                                                     |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 2         |

  Scenario: PAY11-35 Hide an unexpected failure after real webhook verification
    The actual POST request to /payments/webhooks/stripe uses text input. Both deliveries return the complete safe 500/internal_error problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request. The report records an explicit StripeWebhookVerifier.verify RuntimeError boundary rather than presenting an injected fault as a natural outage.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                                                                                                          |
      | Method      | POST                                                                                                           |
      | Path        | /payments/webhooks/stripe                                                                                      |
      | BodyKind    | text                                                                                                           |
      | BodyValue   | {"id":"evt_framework_fault","object":"event","type":"framework.unknown","livemode":false,"data":{"object":{}}} |
      | ContentType | application/json                                                                                               |
      | TraceHeader | 11111111111111111111111111111111                                                                               |
      | Signature   | valid                                                                                                          |
    And I remember populated framework state
    And this framework failure is installed
      | Field     | Value                        |
      | Point     | StripeWebhookVerifier.verify |
      | Exception | RuntimeError                 |
    When I submit the prepared framework request
    Then the response matches case "PAY11-35"
      | Field                  | Value                           |
      | HTTPStatuses           | 500                             |
      | ContentType            | application/problem+json        |
      | Code                   | internal_error                  |
      | JSON.type              | "about:blank"                   |
      | JSON.title             | "Internal Server Error"         |
      | JSON.status            | 500                             |
      | JSON.detail            | "An unexpected error occurred." |
      | JSON.instance          | "/payments/webhooks/stripe"     |
      | JSON.errors            | []                              |
      | JSON.missingProperties | []                              |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 2         |

  Scenario: PAY11-36 Reject a non-UUID route value at Pay
    The actual POST request to /payments/invalid-uuid/pay uses none input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/invalid-uuid/pay       |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-36"
      | Field                  | Value                        |
      | HTTPStatuses           | 400                          |
      | ContentType            | application/problem+json     |
      | Code                   | invalid_request              |
      | JSON.type              | "about:blank"                |
      | JSON.title             | "Bad Request"                |
      | JSON.status            | 400                          |
      | JSON.detail            | "Request validation failed." |
      | JSON.instance          | "/payments/invalid-uuid/pay" |
      | JSON.errors            | []                           |
      | JSON.missingProperties | []                           |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-37 Reject an invalid hex UUID and private query at Pay
    The actual POST request to /payments/11111111-1111-4111-8111-11111111111g/pay?private=query-marker uses none input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                                                                   |
      | Method      | POST                                                                    |
      | Path        | /payments/11111111-1111-4111-8111-11111111111g/pay?private=query-marker |
      | BodyKind    | none                                                                    |
      | BodyValue   | <empty>                                                                 |
      | ContentType | <absent>                                                                |
      | TraceHeader | 11111111111111111111111111111111                                        |
      | Signature   | absent                                                                  |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-37"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_request                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "Request validation failed."                         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-11111111111g/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-38 Reject a non-UUID route value at Checkout
    The actual POST request to /payments/invalid-uuid/checkout uses none input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/invalid-uuid/checkout  |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-38"
      | Field                  | Value                             |
      | HTTPStatuses           | 400                               |
      | ContentType            | application/problem+json          |
      | Code                   | invalid_request                   |
      | JSON.type              | "about:blank"                     |
      | JSON.title             | "Bad Request"                     |
      | JSON.status            | 400                               |
      | JSON.detail            | "Request validation failed."      |
      | JSON.instance          | "/payments/invalid-uuid/checkout" |
      | JSON.errors            | []                                |
      | JSON.missingProperties | []                                |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-39 Reject an invalid hex UUID and private query at Checkout
    The actual POST request to /payments/11111111-1111-4111-8111-11111111111g/checkout?private=query-marker uses none input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                                                                        |
      | Method      | POST                                                                         |
      | Path        | /payments/11111111-1111-4111-8111-11111111111g/checkout?private=query-marker |
      | BodyKind    | none                                                                         |
      | BodyValue   | <empty>                                                                      |
      | ContentType | <absent>                                                                     |
      | TraceHeader | 11111111111111111111111111111111                                             |
      | Signature   | absent                                                                       |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-39"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_request                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "Request validation failed."                              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-11111111111g/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-40 Reject a non-UUID route value at payment reads
    The actual GET request to /payments/order/invalid-uuid uses none input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | GET                              |
      | Path        | /payments/order/invalid-uuid     |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-40"
      | Field                  | Value                          |
      | HTTPStatuses           | 400                            |
      | ContentType            | application/problem+json       |
      | Code                   | invalid_request                |
      | JSON.type              | "about:blank"                  |
      | JSON.title             | "Bad Request"                  |
      | JSON.status            | 400                            |
      | JSON.detail            | "Request validation failed."   |
      | JSON.instance          | "/payments/order/invalid-uuid" |
      | JSON.errors            | []                             |
      | JSON.missingProperties | []                             |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-41 Reject an invalid hex UUID and private query at payment reads
    The actual GET request to /payments/order/11111111-1111-4111-8111-11111111111g?private=query-marker uses none input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                                                                     |
      | Method      | GET                                                                       |
      | Path        | /payments/order/11111111-1111-4111-8111-11111111111g?private=query-marker |
      | BodyKind    | none                                                                      |
      | BodyValue   | <empty>                                                                   |
      | ContentType | <absent>                                                                  |
      | TraceHeader | 11111111111111111111111111111111                                          |
      | Signature   | absent                                                                    |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-41"
      | Field                  | Value                                                  |
      | HTTPStatuses           | 400                                                    |
      | ContentType            | application/problem+json                               |
      | Code                   | invalid_request                                        |
      | JSON.type              | "about:blank"                                          |
      | JSON.title             | "Bad Request"                                          |
      | JSON.status            | 400                                                    |
      | JSON.detail            | "Request validation failed."                           |
      | JSON.instance          | "/payments/order/11111111-1111-4111-8111-11111111111g" |
      | JSON.errors            | []                                                     |
      | JSON.missingProperties | []                                                     |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-42 Reject malformed JSON at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 400/invalid_json problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | {"private":                      |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-42"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_json                                         |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "The request body is not valid JSON."                |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-43 Reject JSON null at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | null                             |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-43"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_request                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "Request validation failed."                         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-44 Reject an object body at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | {}                               |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-44"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_request                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "Request validation failed."                         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-45 Reject an array body at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | []                               |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-45"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_request                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "Request validation failed."                         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-46 Reject a string body at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | "fixture"                        |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-46"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_request                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "Request validation failed."                         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-47 Reject a numeric body at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | 1                                |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-47"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_request                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "Request validation failed."                         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-48 Reject a boolean body at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | true                             |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-48"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_request                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "Request validation failed."                         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-49 Reject invalid UTF-8 JSON bytes at Pay
    The actual POST request to /payments/{order_id}/pay uses hex input. Both deliveries return the complete safe 400/invalid_json problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | hex                              |
      | BodyValue   | ff                               |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-49"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_json                                         |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "The request body is not valid JSON."                |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-50 Reject a truncated JSON literal at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 400/invalid_json problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | tru                              |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-50"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_json                                         |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "The request body is not valid JSON."                |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-51 Reject trailing JSON garbage at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 400/invalid_json problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | {} trailing                      |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-51"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_json                                         |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "The request body is not valid JSON."                |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-52 Reject a plain-text body at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 415/unsupported_media_type problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | fixture                          |
      | ContentType | text/plain                       |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-52"
      | Field                  | Value                                                |
      | HTTPStatuses           | 415                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | unsupported_media_type                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Unsupported Media Type"                             |
      | JSON.status            | 415                                                  |
      | JSON.detail            | "The request content type is not supported."         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-53 Reject a body without content type at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 415/unsupported_media_type problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | {}                               |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-53"
      | Field                  | Value                                                |
      | HTTPStatuses           | 415                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | unsupported_media_type                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Unsupported Media Type"                             |
      | JSON.status            | 415                                                  |
      | JSON.detail            | "The request content type is not supported."         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-54 Reject an XML body at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 415/unsupported_media_type problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | <fixture/>                       |
      | ContentType | application/xml                  |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-54"
      | Field                  | Value                                                |
      | HTTPStatuses           | 415                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | unsupported_media_type                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Unsupported Media Type"                             |
      | JSON.status            | 415                                                  |
      | JSON.detail            | "The request content type is not supported."         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-55 Reject a vendor JSON body at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | {}                               |
      | ContentType | application/vnd.fixture+json     |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-55"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_request                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "Request validation failed."                         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-56 Reject mixed-case JSON with charset at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | {}                               |
      | ContentType | Application/JSON; charset=utf-8  |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-56"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_request                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "Request validation failed."                         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-57 Reject a valid JSON exponent beyond float range at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | 1e999                            |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-57"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_request                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "Request validation failed."                         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-58 Reject a Unicode string body at Pay
    The actual POST request to /payments/{order_id}/pay uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | text                             |
      | BodyValue   | "żółć"                           |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-58"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_request                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "Request validation failed."                         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-59 Reject malformed JSON at exactly 64 KiB at Pay
    The actual POST request to /payments/{order_id}/pay uses repeat input. Both deliveries return the complete safe 400/invalid_json problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | repeat                           |
      | BodyValue   | {"Token": "{", "Count": 65536}   |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-59"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_json                                         |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "The request body is not valid JSON."                |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-60 Reject one byte beyond 64 KiB before parsing at Pay
    The actual POST request to /payments/{order_id}/pay uses repeat input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | repeat                           |
      | BodyValue   | {"Token": "{", "Count": 65537}   |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-60"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_request                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "Request validation failed."                         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-61 Reject a valid JSON string at exactly 64 KiB at Pay
    The actual POST request to /payments/{order_id}/pay uses json-padding input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | json-padding                     |
      | BodyValue   | 65536                            |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-61"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | invalid_request                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "Request validation failed."                         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-62 Reject malformed JSON at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 400/invalid_json problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | {"private":                      |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-62"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_json                                              |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "The request body is not valid JSON."                     |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-63 Reject JSON null at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | null                             |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-63"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_request                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "Request validation failed."                              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-64 Reject an object body at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | {}                               |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-64"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_request                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "Request validation failed."                              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-65 Reject an array body at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | []                               |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-65"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_request                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "Request validation failed."                              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-66 Reject a string body at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | "fixture"                        |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-66"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_request                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "Request validation failed."                              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-67 Reject a numeric body at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | 1                                |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-67"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_request                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "Request validation failed."                              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-68 Reject a boolean body at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | true                             |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-68"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_request                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "Request validation failed."                              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-69 Reject invalid UTF-8 JSON bytes at Checkout
    The actual POST request to /payments/{order_id}/checkout uses hex input. Both deliveries return the complete safe 400/invalid_json problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | hex                              |
      | BodyValue   | ff                               |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-69"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_json                                              |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "The request body is not valid JSON."                     |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-70 Reject a truncated JSON literal at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 400/invalid_json problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | tru                              |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-70"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_json                                              |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "The request body is not valid JSON."                     |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-71 Reject trailing JSON garbage at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 400/invalid_json problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | {} trailing                      |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-71"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_json                                              |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "The request body is not valid JSON."                     |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-72 Reject a plain-text body at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 415/unsupported_media_type problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | fixture                          |
      | ContentType | text/plain                       |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-72"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 415                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | unsupported_media_type                                    |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Unsupported Media Type"                                  |
      | JSON.status            | 415                                                       |
      | JSON.detail            | "The request content type is not supported."              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-73 Reject a body without content type at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 415/unsupported_media_type problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | {}                               |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-73"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 415                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | unsupported_media_type                                    |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Unsupported Media Type"                                  |
      | JSON.status            | 415                                                       |
      | JSON.detail            | "The request content type is not supported."              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-74 Reject an XML body at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 415/unsupported_media_type problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | <fixture/>                       |
      | ContentType | application/xml                  |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-74"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 415                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | unsupported_media_type                                    |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Unsupported Media Type"                                  |
      | JSON.status            | 415                                                       |
      | JSON.detail            | "The request content type is not supported."              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-75 Reject a vendor JSON body at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | {}                               |
      | ContentType | application/vnd.fixture+json     |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-75"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_request                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "Request validation failed."                              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-76 Reject mixed-case JSON with charset at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | {}                               |
      | ContentType | Application/JSON; charset=utf-8  |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-76"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_request                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "Request validation failed."                              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-77 Reject a valid JSON exponent beyond float range at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | 1e999                            |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-77"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_request                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "Request validation failed."                              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-78 Reject a Unicode string body at Checkout
    The actual POST request to /payments/{order_id}/checkout uses text input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | text                             |
      | BodyValue   | "żółć"                           |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-78"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_request                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "Request validation failed."                              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-79 Reject malformed JSON at exactly 64 KiB at Checkout
    The actual POST request to /payments/{order_id}/checkout uses repeat input. Both deliveries return the complete safe 400/invalid_json problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | repeat                           |
      | BodyValue   | {"Token": "{", "Count": 65536}   |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-79"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_json                                              |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "The request body is not valid JSON."                     |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-80 Reject one byte beyond 64 KiB before parsing at Checkout
    The actual POST request to /payments/{order_id}/checkout uses repeat input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | repeat                           |
      | BodyValue   | {"Token": "{", "Count": 65537}   |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-80"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_request                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "Request validation failed."                              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-81 Reject a valid JSON string at exactly 64 KiB at Checkout
    The actual POST request to /payments/{order_id}/checkout uses json-padding input. Both deliveries return the complete safe 400/invalid_request problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | json-padding                     |
      | BodyValue   | 65536                            |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-81"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 400                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | invalid_request                                           |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Request"                                             |
      | JSON.status            | 400                                                       |
      | JSON.detail            | "Request validation failed."                              |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-82 Reject an empty signed webhook body
    The actual POST request to /payments/webhooks/stripe uses empty input. Both deliveries return the complete safe 400/webhook_invalid problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/webhooks/stripe        |
      | BodyKind    | empty                            |
      | BodyValue   | <empty>                          |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | valid                            |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-82"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-83 Reject a signed null webhook body
    The actual POST request to /payments/webhooks/stripe uses text input. Both deliveries return the complete safe 400/webhook_invalid problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/webhooks/stripe        |
      | BodyKind    | text                             |
      | BodyValue   | null                             |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | valid                            |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-83"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-84 Reject a signed array webhook body
    The actual POST request to /payments/webhooks/stripe uses text input. Both deliveries return the complete safe 400/webhook_invalid problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/webhooks/stripe        |
      | BodyKind    | text                             |
      | BodyValue   | []                               |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | valid                            |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-84"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-85 Reject malformed signed webhook JSON
    The actual POST request to /payments/webhooks/stripe uses text input. Both deliveries return the complete safe 400/webhook_invalid problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/webhooks/stripe        |
      | BodyKind    | text                             |
      | BodyValue   | {"fixture":                      |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | valid                            |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-85"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-86 Reject signed invalid UTF-8 webhook bytes
    The actual POST request to /payments/webhooks/stripe uses hex input. Both deliveries return the complete safe 400/webhook_invalid problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/webhooks/stripe        |
      | BodyKind    | hex                              |
      | BodyValue   | ff                               |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | valid                            |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-86"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-87 Reject a webhook without content type
    The actual POST request to /payments/webhooks/stripe uses text input. Both deliveries return the complete safe 415/unsupported_media_type problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                                                                                                          |
      | Method      | POST                                                                                                           |
      | Path        | /payments/webhooks/stripe                                                                                      |
      | BodyKind    | text                                                                                                           |
      | BodyValue   | {"id":"evt_framework_fault","object":"event","type":"framework.unknown","livemode":false,"data":{"object":{}}} |
      | ContentType | <absent>                                                                                                       |
      | TraceHeader | 11111111111111111111111111111111                                                                               |
      | Signature   | valid                                                                                                          |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-87"
      | Field                  | Value                                        |
      | HTTPStatuses           | 415                                          |
      | ContentType            | application/problem+json                     |
      | Code                   | unsupported_media_type                       |
      | JSON.type              | "about:blank"                                |
      | JSON.title             | "Unsupported Media Type"                     |
      | JSON.status            | 415                                          |
      | JSON.detail            | "The request content type is not supported." |
      | JSON.instance          | "/payments/webhooks/stripe"                  |
      | JSON.errors            | []                                           |
      | JSON.missingProperties | []                                           |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-88 Reject a vendor JSON webhook media type
    The actual POST request to /payments/webhooks/stripe uses text input. Both deliveries return the complete safe 415/unsupported_media_type problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                                                                                                          |
      | Method      | POST                                                                                                           |
      | Path        | /payments/webhooks/stripe                                                                                      |
      | BodyKind    | text                                                                                                           |
      | BodyValue   | {"id":"evt_framework_fault","object":"event","type":"framework.unknown","livemode":false,"data":{"object":{}}} |
      | ContentType | application/vnd.fixture+json                                                                                   |
      | TraceHeader | 11111111111111111111111111111111                                                                               |
      | Signature   | valid                                                                                                          |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-88"
      | Field                  | Value                                        |
      | HTTPStatuses           | 415                                          |
      | ContentType            | application/problem+json                     |
      | Code                   | unsupported_media_type                       |
      | JSON.type              | "about:blank"                                |
      | JSON.title             | "Unsupported Media Type"                     |
      | JSON.status            | 415                                          |
      | JSON.detail            | "The request content type is not supported." |
      | JSON.instance          | "/payments/webhooks/stripe"                  |
      | JSON.errors            | []                                           |
      | JSON.missingProperties | []                                           |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-89 Hide the private query on an unknown route
    The actual GET request to /framework-missing?private=query-marker uses none input. Both deliveries return the complete safe 404/route_not_found problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                                   |
      | Method      | GET                                     |
      | Path        | /framework-missing?private=query-marker |
      | BodyKind    | none                                    |
      | BodyValue   | <empty>                                 |
      | ContentType | <absent>                                |
      | TraceHeader | 11111111111111111111111111111111        |
      | Signature   | absent                                  |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-89"
      | Field                  | Value                    |
      | HTTPStatuses           | 404                      |
      | ContentType            | application/problem+json |
      | Code                   | route_not_found          |
      | JSON.type              | "about:blank"            |
      | JSON.title             | "Not Found"              |
      | JSON.status            | 404                      |
      | JSON.detail            | "Route was not found."   |
      | JSON.instance          | "/framework-missing"     |
      | JSON.errors            | []                       |
      | JSON.missingProperties | []                       |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-90 Reject an extra segment after a Pay route
    The actual POST request to /payments/{order_id}/pay/extra uses none input. Both deliveries return the complete safe 404/route_not_found problem, preserve two populated payments and all history/receipts, and send no Orders or Stripe request.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay/extra   |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-90"
      | Field                  | Value                                                      |
      | HTTPStatuses           | 404                                                        |
      | ContentType            | application/problem+json                                   |
      | Code                   | route_not_found                                            |
      | JSON.type              | "about:blank"                                              |
      | JSON.title             | "Not Found"                                                |
      | JSON.status            | 404                                                        |
      | JSON.detail            | "Route was not found."                                     |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay/extra" |
      | JSON.errors            | []                                                         |
      | JSON.missingProperties | []                                                         |
    And framework rejection keeps this populated state and protocol
      | Field            | Value     |
      | Payments         | 2         |
      | History          | 5         |
      | Receipts         | 1         |
      | TargetStatus     | pending   |
      | OrdersCalls      | 0         |
      | StripeCalls      | 0         |
      | ProviderSessions | unchanged |
      | Repeat           | true      |
      | Allow            | <absent>  |
      | FaultHits        | 0         |

  Scenario: PAY11-91 Accept Pay without a request body
    The actual POST request to /payments/{order_id}/pay uses none input. Its accepted body boundary returns every public field with exact stored effects, while unrelated populated state survives.
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
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/pay         |
      | BodyKind    | none                             |
      | BodyValue   | <empty>                          |
      | ContentType | <absent>                         |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-91"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And the complete payment response is
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
    And only the requested payment is inserted
    And the accepted framework input has these effects
      | Field        | Value   |
      | BodyBytes    | 0       |
      | OrdersCalls  | 1       |
      | StripeCalls  | 0       |
      | ResultStatus | created |
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 1299  |
      | Currency    | PLN   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY11-92 Accept empty Checkout before media validation
    The actual POST request to /payments/{order_id}/checkout uses empty input. Its accepted body boundary returns every public field with exact stored effects, while unrelated populated state survives.
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
    And the framework request contains
      | Field       | Value                            |
      | Method      | POST                             |
      | Path        | /payments/{order_id}/checkout    |
      | BodyKind    | empty                            |
      | BodyValue   | <empty>                          |
      | ContentType | text/plain                       |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    And I remember checkout state and provider calls
    When I submit the prepared framework request
    Then the response matches case "PAY11-92"
      | Field                     | Value            |
      | HTTPStatuses              | 200              |
      | ContentType               | application/json |
      | Code                      | -                |
      | JSON.payment.status       | "pending"        |
      | JSON.payment.amount_minor | 1299             |
      | JSON.payment.currency     | "PLN"            |
    And the complete checkout response is
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
    And the accepted framework input has these effects
      | Field        | Value   |
      | BodyBytes    | 0       |
      | OrdersCalls  | 2       |
      | StripeCalls  | 1       |
      | ResultStatus | pending |
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 1299  |
      | Currency    | PLN   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY11-93 Read a payment while ignoring an uncontracted null body
    The actual GET request to /payments/order/{order_id} uses text input. Its accepted body boundary returns every public field with exact stored effects, while unrelated populated state survives.
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
    And a stored payment is prepared in state "pending"
      | Field               | Value                |
      | provider_session_id | "cs_framework_guard" |
      | provider_payment_id | null                 |
      | failure_code        | null                 |
    And the framework request contains
      | Field       | Value                            |
      | Method      | GET                              |
      | Path        | /payments/order/{order_id}       |
      | BodyKind    | text                             |
      | BodyValue   | null                             |
      | ContentType | application/json                 |
      | TraceHeader | 11111111111111111111111111111111 |
      | Signature   | absent                           |
    And I remember populated framework state
    When I submit the prepared framework request
    Then the response matches case "PAY11-93"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "pending"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "pending"                              |
      | provider_session_id | "cs_framework_guard"                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And every payment collection and external call count is unchanged
    And the accepted framework input has these effects
      | Field        | Value   |
      | BodyBytes    | 4       |
      | OrdersCalls  | 0       |
      | StripeCalls  | 0       |
      | ResultStatus | pending |
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 1299  |
      | Currency    | PLN   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |
