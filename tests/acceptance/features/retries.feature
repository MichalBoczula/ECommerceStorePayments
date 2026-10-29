Feature: Complete retry state and immutable payment history

  Scenario: PAY04-01 Retry Failed with complete provider reset and archive
    A Failed payment has provider and durable checkout metadata beside an unrelated order. Retry returns the same payment at the next version and archives every previous field unchanged.
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
      | Field               | Value            |
      | provider_session_id | "cs_task4_retry" |
      | provider_payment_id | null             |
      | failure_code        | "retry_declined" |
    And I remember the payment and every collection
    When I pay the order
    Then the response matches case "PAY04-01"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
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
      | Field                  | Value                          |
      | PreviousVersion        | 3                              |
      | CurrentVersion         | 4                              |
      | HistoryVersions        | 0,1,2,3                        |
      | HistoryStatuses        | created,created,pending,failed |
      | CheckoutRequestVersion | 1                              |
    And repeating Pay preserves the completed retry

  Scenario: PAY04-02 Retry Canceled with complete provider reset and archive
    A Canceled payment retains its former checkout session and attempt. Retry clears attempt metadata, appends exactly one full archive and preserves unrelated collections.
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
      | Field               | Value            |
      | provider_session_id | "cs_task4_retry" |
      | provider_payment_id | null             |
      | failure_code        | null             |
    And I remember the payment and every collection
    When I pay the order
    Then the response matches case "PAY04-02"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
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
      | Field                  | Value                            |
      | PreviousVersion        | 3                                |
      | CurrentVersion         | 4                                |
      | HistoryVersions        | 0,1,2,3                          |
      | HistoryStatuses        | created,created,pending,canceled |
      | CheckoutRequestVersion | 1                                |
    And repeating Pay preserves the completed retry

  Scenario: PAY04-03 Retry multiple attempts without mutating older history
    The same payment fails again after its first successful retry. Each later transition archives its actual previous state while all older snapshots and recorded timestamps remain unchanged.
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
      | Field               | Value            |
      | provider_session_id | "cs_task4_retry" |
      | provider_payment_id | null             |
      | failure_code        | "retry_declined" |
    And I remember the payment and every collection
    When I pay the order
    Then the response matches case "PAY04-03"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
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
      | Field                  | Value                          |
      | PreviousVersion        | 3                              |
      | CurrentVersion         | 4                              |
      | HistoryVersions        | 0,1,2,3                        |
      | HistoryStatuses        | created,created,pending,failed |
      | CheckoutRequestVersion | 1                              |
    And a later failed attempt is retried without changing older snapshots
      | Field           | Value                                                         |
      | SessionId       | cs_retry_second                                               |
      | FailureCode     | second_decline                                                |
      | FinalVersion    | 8                                                             |
      | HistoryStatuses | created,created,pending,failed,created,created,pending,failed |

  Scenario: PAY04-04 Retry a historical Failed document as version one
    A genuine historical Failed document physically omits version and checkout members. Retry preserves its identity and money and creates a normalized version-zero archive.
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
    And a historical payment in state "failed" has no version or checkout fields
      | Field             | Value                                                                    |
      | OmittedFields     | version,checkout_attempt_id,checkout_started_at,checkout_request_version |
      | ProviderSessionId | "cs_legacy_retry"                                                        |
      | FailureCode       | "legacy_declined"                                                        |
    And I remember the payment and every collection
    When I pay the order
    Then the response matches case "PAY04-04"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
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
      | Field                  | Value  |
      | PreviousVersion        | 0      |
      | CurrentVersion         | 1      |
      | HistoryVersions        | 0      |
      | HistoryStatuses        | failed |
      | CheckoutRequestVersion | 1      |
    And repeating Pay preserves the completed retry

  Scenario: PAY04-05 Retry a historical Canceled document as version one
    A historical Canceled document has no version or checkout members. Retry advances the existing identity to version one while preserving the exact older business fields.
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
    And a historical payment in state "canceled" has no version or checkout fields
      | Field             | Value                                                                    |
      | OmittedFields     | version,checkout_attempt_id,checkout_started_at,checkout_request_version |
      | ProviderSessionId | "cs_legacy_retry"                                                        |
      | FailureCode       | null                                                                     |
    And I remember the payment and every collection
    When I pay the order
    Then the response matches case "PAY04-05"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
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
      | Field                  | Value    |
      | PreviousVersion        | 0        |
      | CurrentVersion         | 1        |
      | HistoryVersions        | 0        |
      | HistoryStatuses        | canceled |
      | CheckoutRequestVersion | 1        |
    And repeating Pay preserves the completed retry

  Scenario: PAY04-06 Repeat historical Created without migrating storage
    A historical Created document is missing optional bookkeeping fields. Repeated Pay returns its complete existing snapshot without fetching Orders, writing or silently migrating the document.
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
    And a historical payment in state "created" has no version or checkout fields
      | Field             | Value                                                                    |
      | OmittedFields     | version,checkout_attempt_id,checkout_started_at,checkout_request_version |
      | ProviderSessionId | null                                                                     |
      | FailureCode       | null                                                                     |
    And I remember the payment and every collection
    And Orders returns "outage"
    When I pay the order
    Then the response matches case "PAY04-06"
      | Field             | Value            |
      | HTTPStatuses      | 200              |
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
    And every payment collection and external call count is unchanged

  Scenario: PAY04-07 Reject Failed retry after currency changes
    Orders reports another currency for the same numeric amount. Failed retry returns the complete total-changed problem and leaves every populated collection unchanged.
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
      | Field               | Value            |
      | provider_session_id | "cs_task4_retry" |
      | provider_payment_id | null             |
      | failure_code        | "retry_declined" |
    And I remember the payment and every collection
    And Orders currency changes to "USD"
    When I pay the order
    Then the response matches case "PAY04-07"
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
    And the rejected retry preserves every document

  Scenario: PAY04-08 Reject Canceled retry after amount changes
    A Canceled payment is retried after Orders changes its total. The complete conflict problem is returned without changing the payment, any history or receipts.
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
      | Field               | Value            |
      | provider_session_id | "cs_task4_retry" |
      | provider_payment_id | null             |
      | failure_code        | null             |
    And I remember the payment and every collection
    And Orders total has changed
    When I pay the order
    Then the response matches case "PAY04-08"
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
    And the rejected retry preserves every document

  Scenario: PAY04-09 Reject Failed retry for a Paid order
    Orders reports Paid after the payment failed. Retry returns order_not_payable and preserves the complete Failed snapshot and all unrelated stored data.
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
      | Field               | Value            |
      | provider_session_id | "cs_task4_retry" |
      | provider_payment_id | null             |
      | failure_code        | "retry_declined" |
    And I remember the payment and every collection
    And Orders reports status "Paid"
    When I pay the order
    Then the response matches case "PAY04-09"
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
    And the rejected retry preserves every document

  Scenario: PAY04-10 Reject Canceled retry for a Canceled order
    Orders reports a Canceled order that cannot start another payment attempt. Retry returns the full safe conflict problem and retains every populated document.
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
      | Field               | Value            |
      | provider_session_id | "cs_task4_retry" |
      | provider_payment_id | null             |
      | failure_code        | null             |
    And I remember the payment and every collection
    And Orders reports status "Canceled"
    When I pay the order
    Then the response matches case "PAY04-10"
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
    And the rejected retry preserves every document

  Scenario: PAY04-11 Retain Failed payment when its order is missing
    Orders cannot find the order during Failed retry. The complete not-found problem is returned while existing payment, history and receipt data remains unchanged.
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
      | Field               | Value            |
      | provider_session_id | "cs_task4_retry" |
      | provider_payment_id | null             |
      | failure_code        | "retry_declined" |
    And I remember the payment and every collection
    And Orders returns "missing"
    When I pay the order
    Then the response matches case "PAY04-11"
      | Field                  | Value                                                |
      | HTTPStatuses           | 404                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_not_found                                      |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Not Found"                                          |
      | JSON.status            | 404                                                  |
      | JSON.detail            | "Order was not found."                               |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And the rejected retry preserves every document

  Scenario: PAY04-12 Retain Failed payment after an invalid Orders payload
    Orders returns an invalid payload while a Failed payment already exists. Retry returns a safe invalid-response problem without replacing or archiving any document.
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
      | Field               | Value            |
      | provider_session_id | "cs_task4_retry" |
      | provider_payment_id | null             |
      | failure_code        | "retry_declined" |
    And I remember the payment and every collection
    And Orders returns "invalid"
    When I pay the order
    Then the response matches case "PAY04-12"
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
    And the rejected retry preserves every document

  Scenario: PAY04-13 Retain Failed payment when Orders times out
    A controlled Orders request times out during retry of a Failed payment. The safe timeout response preserves all current, history and receipt fields.
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
      | Field               | Value            |
      | provider_session_id | "cs_task4_retry" |
      | provider_payment_id | null             |
      | failure_code        | "retry_declined" |
    And I remember the payment and every collection
    And Orders returns "timeout"
    When I pay the order
    Then the response matches case "PAY04-13"
      | Field                  | Value                                                |
      | HTTPStatuses           | 504                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_timeout                                        |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Gateway Timeout"                                    |
      | JSON.status            | 504                                                  |
      | JSON.detail            | "Orders service timed out."                          |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And the rejected retry preserves every document

  Scenario: PAY04-14 Retain Failed payment during an Orders outage
    Orders cannot be reached while retrying an existing Failed payment. The complete unavailable problem is returned without changing any populated collection.
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
      | Field               | Value            |
      | provider_session_id | "cs_task4_retry" |
      | provider_payment_id | null             |
      | failure_code        | "retry_declined" |
    And I remember the payment and every collection
    And Orders returns "outage"
    When I pay the order
    Then the response matches case "PAY04-14"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_unavailable                                    |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service is unavailable."                     |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And the rejected retry preserves every document
