Feature: Verified checkout notifications and durable receipt

  Scenario: PAY22-01 Confirm a matching checkout and persist durable work
    A signed paid event matches an existing checkout. The webhook confirms payment and records durable work without contacting downstream services.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "paid"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-01"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the current payment is "Succeeded" at version 3
    And webhook work is persisted for fulfillment
    And webhook processing did not contact external services

  Scenario: PAY22-02 Redeliver the same event without another transition
    The same signed paid event was already applied once. Redelivery acknowledges it without another payment transition or history snapshot.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "paid"
    And the checkout webhook was delivered
    When I deliver the checkout webhook
    Then the response matches case "PAY22-02"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the current payment is "Succeeded" at version 3
    And the database has 1 current payment and 3 history snapshots

  Scenario: PAY22-03 Reject a missing signature
    A checkout event is delivered without its signature header. Verification returns webhook_invalid and records no durable receipt.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "paid"
    And webhook delivery is "missing"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-03"
      | Field        | Value                    |
      | HTTPStatuses | 400                      |
      | ContentType  | application/problem+json |
      | Code         | webhook_invalid          |
    And the current payment is "Pending" at version 2
    And no webhook receipt exists

  Scenario: PAY22-04 Reject tampered original bytes
    The original signed checkout bytes are changed before delivery. Signature verification rejects the request and creates no receipt.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "paid"
    And webhook delivery is "tampered"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-04"
      | Field        | Value                    |
      | HTTPStatuses | 400                      |
      | ContentType  | application/problem+json |
      | Code         | webhook_invalid          |
    And no webhook receipt exists

  Scenario: PAY22-05 Ignore a signed unrelated event
    A valid signature covers an event type unrelated to checkout. The API acknowledges the event while the payment remains Pending.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "unknown"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-05"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the current payment is "Pending" at version 2

  Scenario: PAY22-06 Record mismatched money without confirming payment
    A signed checkout event carries an amount different from payment money. Processing rejects its receipt without confirming the Pending payment.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "mismatched"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-06"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the current payment is "Pending" at version 2
    And the webhook receipt is "rejected"

  Scenario: PAY22-07 Expire payment without canceling the order
    A signed expiry event targets an existing checkout session. Payment becomes Failed without contacting Orders or canceling the order.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "expired"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-07"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the current payment is "Failed" at version 3
    And webhook processing did not contact external services

  Scenario: PAY22-08 Earlier expiry cannot downgrade success
    A successful checkout later receives an earlier expiry event. The acknowledgement succeeds while payment remains Succeeded at its current version.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "paid"
    And the checkout webhook was delivered
    And a signed checkout event "expired"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-08"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the current payment is "Succeeded" at version 3

  Scenario: PAY22-09 Concurrent duplicate delivery commits once
    Two identical signed webhook deliveries arrive concurrently. Both are acknowledged while payment and history record only one successful transition.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "paid"
    When I deliver two checkout webhooks concurrently
    Then the response matches case "PAY22-09"
      | Field         | Value            |
      | HTTPStatuses  | 200,200          |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the current payment is "Succeeded" at version 3
    And the database has 1 current payment and 3 history snapshots

  Scenario: PAY22-10 Interrupted processing remains retryable
    Receipt completion fails once after accepting a signed checkout event. The API returns webhook_retry and leaves a pending durable receipt.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "paid"
    And webhook processing fails once after receipt
    When I deliver the checkout webhook
    Then the response matches case "PAY22-10"
      | Field        | Value                    |
      | HTTPStatuses | 503                      |
      | ContentType  | application/problem+json |
      | Code         | webhook_retry            |
    And the current payment is "Pending" at version 2
    And the webhook receipt is "pending"

  Scenario: PAY22-11 Redelivery finishes an interrupted receipt
    A previous webhook attempt left a pending receipt after interruption. Redelivery finishes the payment transition and schedules durable fulfillment.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "paid"
    And webhook processing fails once after receipt
    And the checkout webhook was delivered
    When I deliver the checkout webhook
    Then the response matches case "PAY22-11"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the current payment is "Succeeded" at version 3
    And webhook work is persisted for fulfillment

  Scenario: PAY22-12 Unconfigured webhook verification is unavailable
    Webhook verification has no configured signing secret. The API returns webhook_disabled without recording a receipt for the request.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "paid"
    And webhook delivery is "disabled"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-12"
      | Field        | Value                    |
      | HTTPStatuses | 503                      |
      | ContentType  | application/problem+json |
      | Code         | webhook_disabled         |
    And no webhook receipt exists

  Scenario: PAY22-13 Reject unsupported webhook media
    A signed checkout body arrives with plain-text media type. The API rejects its media before applying webhook processing.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "paid"
    And webhook delivery is "media"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-13"
      | Field        | Value                    |
      | HTTPStatuses | 415                      |
      | ContentType  | application/problem+json |
      | Code         | unsupported_media_type   |

  Scenario: PAY22-14 Reject oversized webhook before receipt
    A webhook body exceeds the one-megabyte request limit. The API returns webhook_too_large before recording a durable receipt.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "paid"
    And webhook delivery is "large"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-14"
      | Field        | Value                    |
      | HTTPStatuses | 413                      |
      | ContentType  | application/problem+json |
      | Code         | webhook_too_large        |
    And no webhook receipt exists

  Scenario: PAY22-15 Unpaid completion cannot establish success
    A signed completion event still reports an unpaid checkout. The API acknowledges it without establishing payment success.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a checkout created through the API
    And a signed checkout event "unpaid"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-15"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the current payment is "Pending" at version 2

  Scenario: PAY22-16 New checkout enables both card and BLIK
    A payable order starts a new hosted checkout. The actual Stripe SDK request enables both card and BLIK payment methods.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a payable order
    And I remember checkout state and provider calls
    When I create checkout for the order
    Then the response matches case "PAY22-16"
      | Field                     | Value            |
      | HTTPStatuses              | 200              |
      | ContentType               | application/json |
      | Code                      | -                |
      | JSON.payment.status       | "pending"        |
      | JSON.payment.amount_minor | 1299             |
      | JSON.payment.currency     | "PLN"            |
      | JSON.checkout_status      | "open"           |
    And checkout requests both card and BLIK
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
