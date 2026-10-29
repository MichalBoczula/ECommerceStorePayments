Feature: Complete Pay and payment reads with isolated stored state

  Scenario: PAY03-01 Create exact large money without changing an unrelated order
    A large USD number reaches Pay as an exact decimal token. Its complete new payment is stored while every unrelated current, history and receipt document is preserved.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 90071992547409.91                    |
      | TotalCurrency | USD                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And I remember the payment and every collection
    When I pay the order
    Then the response matches case "PAY03-01"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 9007199254740991 |
      | JSON.currency     | "USD"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 9007199254740991                       |
      | currency            | "USD"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted

  Scenario: PAY03-02 Read Pending provider and timestamp fields
    A Pending snapshot has a provider session and update time. Reading its order returns every stored public field without calling dependencies or changing populated collections.
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
      | Field               | Value           |
      | provider_session_id | "cs_task3_read" |
      | provider_payment_id | null            |
      | failure_code        | null            |
    And I remember the payment and every collection
    And Orders returns "outage"
    When I get the payment by order ID
    Then the response matches case "PAY03-02"
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
      | provider_session_id | "cs_task3_read"                        |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And every payment collection and external call count is unchanged
    And the current payment is "Pending" at version 2

  Scenario: PAY03-03 Read Succeeded provider identifiers
    A Succeeded snapshot retains both provider identifiers and its timestamps. Reading one order returns its complete payment while unrelated records remain unchanged.
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
      | Field               | Value           |
      | provider_session_id | "cs_task3_read" |
      | provider_payment_id | "pi_task3_read" |
      | failure_code        | null            |
    And I remember the payment and every collection
    And Orders returns "outage"
    When I get the payment by order ID
    Then the response matches case "PAY03-03"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "succeeded"      |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | "cs_task3_read"                        |
      | provider_payment_id | "pi_task3_read"                        |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And every payment collection and external call count is unchanged
    And the current payment is "Succeeded" at version 3

  Scenario: PAY03-04 Read Failed snapshot without retrying
    A Failed snapshot contains a provider session and failure code. Reading it preserves that failure and every populated collection without starting another attempt.
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
    And a stored payment is prepared in state "failed"
      | Field               | Value             |
      | provider_session_id | "cs_task3_read"   |
      | provider_payment_id | null              |
      | failure_code        | "issuer_declined" |
    And I remember the payment and every collection
    And Orders returns "outage"
    When I get the payment by order ID
    Then the response matches case "PAY03-04"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "failed"         |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "failed"                               |
      | provider_session_id | "cs_task3_read"                        |
      | provider_payment_id | null                                   |
      | failure_code        | "issuer_declined"                      |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And every payment collection and external call count is unchanged
    And the current payment is "Failed" at version 3

  Scenario: PAY03-05 Read Canceled snapshot without retrying
    A Canceled snapshot retains its provider session and update time. Reading it returns the complete saved response without retrying or changing another order.
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
    And a stored payment is prepared in state "canceled"
      | Field               | Value           |
      | provider_session_id | "cs_task3_read" |
      | provider_payment_id | null            |
      | failure_code        | null            |
    And I remember the payment and every collection
    And Orders returns "outage"
    When I get the payment by order ID
    Then the response matches case "PAY03-05"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "canceled"       |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "canceled"                             |
      | provider_session_id | "cs_task3_read"                        |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And every payment collection and external call count is unchanged
    And the current payment is "Canceled" at version 3

  Scenario: PAY03-06 Repeat Pay on Pending without any effects
    An existing Pending payment is returned even while Orders is unavailable. Pay preserves the exact remembered response and every current, history and receipt document.
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
      | Field               | Value           |
      | provider_session_id | "cs_task3_read" |
      | provider_payment_id | null            |
      | failure_code        | null            |
    And I remember the payment and every collection
    And Orders returns "outage"
    When I pay the order
    Then the response matches case "PAY03-06"
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
      | provider_session_id | "cs_task3_read"                        |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And every payment collection and external call count is unchanged
    And the current payment is "Pending" at version 2

  Scenario: PAY03-07 Repeat Pay on Succeeded without any effects
    An existing Succeeded payment already has provider confirmation identifiers. Repeating Pay returns its exact snapshot without contacting Orders or modifying populated storage.
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
      | Field               | Value           |
      | provider_session_id | "cs_task3_read" |
      | provider_payment_id | "pi_task3_read" |
      | failure_code        | null            |
    And I remember the payment and every collection
    And Orders returns "outage"
    When I pay the order
    Then the response matches case "PAY03-07"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "succeeded"      |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "succeeded"                            |
      | provider_session_id | "cs_task3_read"                        |
      | provider_payment_id | "pi_task3_read"                        |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | {stored.updated_at}                    |
    And every payment collection and external call count is unchanged
    And the current payment is "Succeeded" at version 3

  Scenario: PAY03-08 Missing payment stays missing beside an unrelated order
    Only an unrelated succeeded order has payment data. Reading the missing order returns its complete not-found problem without leaking the other payment or changing any collection.
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
    And I remember the payment and every collection
    And Orders returns "outage"
    When I get the payment by order ID
    Then the response matches case "PAY03-08"
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
    And every payment collection and external call count is unchanged

  Scenario: PAY03-09 Repeat Pay on Created beside an unrelated order
    A Created payment exists beside a succeeded payment for another order. Repeating Pay preserves its complete response and every populated collection while Orders is unavailable.
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
    When I pay the order
    Then the response matches case "PAY03-09"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And the response refers to the original payment
    And Orders was not called again
    And the database has 2 current payments and 3 history snapshots
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
