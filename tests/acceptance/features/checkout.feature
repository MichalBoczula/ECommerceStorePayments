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

  Scenario: PAY21-02 Read an existing checkout instead of creating another
    A Pending payment already has an open hosted checkout. Repeating checkout reads that session without creating a second one.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
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

  Scenario: PAY21-03 Recover a timeout after the provider accepted checkout
    Stripe accepted a checkout but its first response was lost. A retry recovers the same provider session and finishes Pending state.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an ambiguous checkout timeout
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

  Scenario: PAY21-04 Disabled checkout does not prepare a payment
    Hosted checkout is disabled in service settings. The API returns checkout_disabled before preparing payment state or calling Stripe.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And checkout is disabled
    When I create checkout for the order
    Then the response matches case "PAY21-04"
      | Field        | Value                    |
      | HTTPStatuses | 503                      |
      | ContentType  | application/problem+json |
      | Code         | checkout_disabled        |
    And the database has 0 current payments and 0 history snapshots
    And Stripe was not called

  Scenario: PAY21-05 Reject a Paid order before contacting Stripe
    Orders reports an already Paid order during checkout. The API returns order_not_payable before any Stripe request is sent.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And Orders reports status "Paid"
    When I create checkout for the order
    Then the response matches case "PAY21-05"
      | Field        | Value                    |
      | HTTPStatuses | 409                      |
      | ContentType  | application/problem+json |
      | Code         | order_not_payable        |
    And Stripe was not called

  Scenario: PAY21-06 Report provider rejection safely
    Stripe rejects checkout creation with a controlled provider response. The API returns a safe checkout_provider_error and retains Created state.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And Stripe responds with "rejection"
    When I create checkout for the order
    Then the response matches case "PAY21-06"
      | Field        | Value                    |
      | HTTPStatuses | 502                      |
      | ContentType  | application/problem+json |
      | Code         | checkout_provider_error  |
    And the current payment is "Created" at version 1

  Scenario: PAY21-07 Report an ambiguous provider timeout safely
    Stripe accepts checkout but a transport timeout interrupts its acknowledgement. The API reports checkout_timeout and keeps the prepared payment retryable.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And Stripe responds with "timeout_once"
    When I create checkout for the order
    Then the response matches case "PAY21-07"
      | Field        | Value                    |
      | HTTPStatuses | 504                      |
      | ContentType  | application/problem+json |
      | Code         | checkout_timeout         |
    And the current payment is "Created" at version 1

  Scenario: PAY21-08 Reject a missing order
    The order needed for checkout does not exist. Checkout returns order_not_found without sending a request to Stripe.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And Orders returns "missing"
    When I create checkout for the order
    Then the response matches case "PAY21-08"
      | Field        | Value                    |
      | HTTPStatuses | 404                      |
      | ContentType  | application/problem+json |
      | Code         | order_not_found          |
    And Stripe was not called

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
    When I create checkout for the order
    Then the response matches case "PAY21-09"
      | Field        | Value                    |
      | HTTPStatuses | 409                      |
      | ContentType  | application/problem+json |
      | Code         | order_total_changed      |
    And the current payment is "Pending" at version 2
    And Stripe has one checkout session
