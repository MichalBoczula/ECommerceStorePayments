Feature: Payment API with real persistence and a controlled Orders boundary

  Scenario: PAY11-01 Create a payment from a payable order
    A Created order supplies the payment amount and currency. Pay creates one current payment without a history snapshot.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a payable order
    And I remember the payment and every collection
    When I pay the order
    Then the response matches case "PAY11-01"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And the database has 1 current payment and 0 history snapshots
    And the current payment is "Created" at version 0
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

  Scenario: PAY11-02 Read a payment by order ID
    A payment already exists for the requested order. Reading by order ID returns the original payment identity.
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
    And I remember the payment and every collection
    And Orders returns "outage"
    When I get the payment by order ID
    Then the response matches case "PAY11-02"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And the response refers to the original payment
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
    And every payment collection and external call count is unchanged

  Scenario: PAY11-03 Repeat Pay without writing or calling Orders again
    Pay is repeated for an existing nonterminal payment. It returns the same identity without another Orders call or database write.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a payment created through the API
    And I remember the payment and every collection
    And Orders returns "outage"
    When I pay the order
    Then the response matches case "PAY11-03"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And the response refers to the original payment
    And Orders was not called again
    And the database has 1 current payment and 0 history snapshots
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
    And every payment collection and external call count is unchanged

  Scenario: PAY11-04 Missing payment
    The requested order has no stored payment. The API returns payment_not_found and both payment collections stay empty.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a payable order
    And I remember the payment and every collection
    And Orders returns "outage"
    When I get the payment by order ID
    Then the response matches case "PAY11-04"
      | Field                  | Value                                                  |
      | HTTPStatuses           | 404                                                    |
      | ContentType            | application/problem+json                               |
      | Code                   | payment_not_found                                      |
      | JSON.type              | "about:blank"                                          |
      | JSON.title             | "Not Found"                                            |
      | JSON.status            | 404                                                    |
      | JSON.detail            | "Payment was not found."                               |
      | JSON.instance          | "/payments/order/11111111-1111-4111-8111-111111111111" |
      | JSON.errors            | []                                                     |
      | JSON.missingProperties | []                                                     |
    And the database has 0 current payments and 0 history snapshots
    And every payment collection and external call count is unchanged

  Scenario: PAY11-05 Missing order
    Orders returns a missing-order response to Pay. The API returns order_not_found without creating a payment or history.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And Orders returns "missing"
    When I pay the order
    Then the response matches case "PAY11-05"
      | Field        | Value                    |
      | HTTPStatuses | 404                      |
      | ContentType  | application/problem+json |
      | Code         | order_not_found          |
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-06 Order not payable
    Orders reports a Paid order that cannot be paid again. Pay rejects it with order_not_payable and creates no payment.
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
    And Orders reports status "Paid"
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY11-06"
      | Field                  | Value                                                |
      | HTTPStatuses           | 409                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_not_payable                                    |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Conflict"                                           |
      | JSON.status            | 409                                                  |
      | JSON.detail            | "Order cannot be paid in its current state."         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |


  Scenario: PAY11-07 Invalid Orders response
    Orders returns an invalid total in its JSON response. Pay exposes a safe order_invalid_response problem and stores nothing.
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
    And Orders returns "invalid"
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY11-07"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |


  Scenario: PAY11-08 Orders timeout
    The Orders HTTP request times out before returning an order. Pay returns order_timeout without creating durable payment state.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And Orders returns "timeout"
    When I pay the order
    Then the response matches case "PAY11-08"
      | Field        | Value                    |
      | HTTPStatuses | 504                      |
      | ContentType  | application/problem+json |
      | Code         | order_timeout            |
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-09 Orders outage
    The controlled Orders transport cannot connect to the service. Pay returns order_unavailable without exposing private connection details.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And Orders returns "outage"
    When I pay the order
    Then the response matches case "PAY11-09"
      | Field        | Value                    |
      | HTTPStatuses | 502                      |
      | ContentType  | application/problem+json |
      | Code         | order_unavailable        |
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-10 Retry a failed payment and archive its previous state
    A failed payment is retried for the same unchanged order. Its identity survives and the previous states remain in history.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a "Failed" payment created through the API
    And I remember the payment and every collection
    When I pay the order
    Then the response matches case "PAY11-10"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And the response refers to the original payment
    And the current payment is "Created" at version 3
    And the history statuses are "Created,Pending,Failed"
    And the complete retry response is
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
    And the retry changes only this version and archive
      | Field                  | Value                  |
      | PreviousVersion        | 2                      |
      | CurrentVersion         | 3                      |
      | HistoryVersions        | 0,1,2                  |
      | HistoryStatuses        | created,pending,failed |
      | CheckoutRequestVersion | 1                      |
    And repeating Pay preserves the completed retry

  Scenario: PAY11-11 Retry a canceled payment
    A canceled payment is retried for the same unchanged order. It returns to Created while preserving the canceled snapshot.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a "Canceled" payment created through the API
    And I remember the payment and every collection
    When I pay the order
    Then the response matches case "PAY11-11"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And the response refers to the original payment
    And the current payment is "Created" at version 2
    And the history statuses are "Created,Canceled"
    And the complete retry response is
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
    And the retry changes only this version and archive
      | Field                  | Value            |
      | PreviousVersion        | 1                |
      | CurrentVersion         | 2                |
      | HistoryVersions        | 0,1              |
      | HistoryStatuses        | created,canceled |
      | CheckoutRequestVersion | 1                |
    And repeating Pay preserves the completed retry

  Scenario: PAY11-12 Reject retry when the order total changed
    Orders changes its total after the payment has failed. Retry returns order_total_changed and retains the failed payment version.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a "Failed" payment created through the API
    And Orders total has changed
    And I remember the payment and every collection
    When I pay the order
    Then the response matches case "PAY11-12"
      | Field                  | Value                                                |
      | HTTPStatuses           | 409                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_total_changed                                  |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Conflict"                                           |
      | JSON.status            | 409                                                  |
      | JSON.detail            | "Order total has changed."                           |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And the current payment is "Failed" at version 2
    And the history statuses are "Created,Pending"
    And the rejected retry preserves every document

  Scenario: PAY11-13 Concurrent Pay creates one current payment
    Two first Pay requests target one order concurrently. Both responses refer to one payment and only one current document exists.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a payable order
    When I submit two Pay requests concurrently
    Then the response matches case "PAY11-13"
      | Field             | Value            |
      | HTTPStatuses      | 200,201          |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And both responses refer to one payment
    And the database has 1 current payment and 0 history snapshots

  Scenario: PAY11-14 Invalid order ID
    Pay receives a path segment that is not a UUID. Request validation returns invalid_request without creating payment state.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a payable order
    When I pay with an invalid order ID
    Then the response matches case "PAY11-14"
      | Field        | Value                    |
      | HTTPStatuses | 400                      |
      | ContentType  | application/problem+json |
      | Code         | invalid_request          |
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-15 Malformed JSON body
    Pay receives an incomplete JSON object with JSON media type. Parsing returns invalid_json before any payment is stored.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a payable order
    When I pay with malformed JSON
    Then the response matches case "PAY11-15"
      | Field        | Value                    |
      | HTTPStatuses | 400                      |
      | ContentType  | application/problem+json |
      | Code         | invalid_json             |
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-16 Unsupported request media
    Pay receives a plain-text body instead of JSON. The API returns unsupported_media_type and leaves payment storage empty.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a payable order
    When I pay with plain text
    Then the response matches case "PAY11-16"
      | Field        | Value                    |
      | HTTPStatuses | 415                      |
      | ContentType  | application/problem+json |
      | Code         | unsupported_media_type   |
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-17 Unknown route
    A request targets a path without a registered route. The API returns a safe route_not_found problem for that path.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a payable order
    When I request an unknown route
    Then the response matches case "PAY11-17"
      | Field        | Value                    |
      | HTTPStatuses | 404                      |
      | ContentType  | application/problem+json |
      | Code         | route_not_found          |

  Scenario: PAY11-18 Wrong method
    POST targets the read-only liveness endpoint. The API returns method_not_allowed and advertises GET in the Allow header.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a payable order
    When I post to a read-only health route
    Then the response matches case "PAY11-18"
      | Field        | Value                    |
      | HTTPStatuses | 405                      |
      | ContentType  | application/problem+json |
      | Code         | method_not_allowed       |
    And the Allow header is "GET"
