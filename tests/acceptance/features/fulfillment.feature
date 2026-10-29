Feature: Durable fulfillment of verified checkout payments

  Scenario: PAY23-01 Fulfillment reconciles ok
    A verified successful webhook schedules durable fulfillment. The worker marks the order Paid, completes one invoice and safely handles redelivery.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a verified successful checkout with fulfillment mode "ok"
    Then the response matches case "PAY23-01"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
    Then one paid order and one completed invoice are recorded
    When the successful webhook is delivered again
    And the durable fulfillment command runs
    Then fulfillment stays completed without repeating downstream writes

  Scenario: PAY23-02 Fulfillment reconciles paid_ack_lost
    Orders commits Paid but loses its completion acknowledgement. The worker reconciles the committed state and completes one invoice without another Paid write.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a verified successful checkout with fulfillment mode "paid_ack_lost"
    Then the response matches case "PAY23-02"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
    Then one paid order and one completed invoice are recorded
    When the successful webhook is delivered again
    And the durable fulfillment command runs
    Then fulfillment stays completed without repeating downstream writes

  Scenario: PAY23-03 Fulfillment reconciles invoice_ack_lost
    Invoice creation commits but loses its completion acknowledgement. The worker discovers the existing invoice and finishes durable fulfillment safely.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a verified successful checkout with fulfillment mode "invoice_ack_lost"
    Then the response matches case "PAY23-03"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
    Then one paid order and one completed invoice are recorded
    When the successful webhook is delivered again
    And the durable fulfillment command runs
    Then fulfillment stays completed without repeating downstream writes

  Scenario: PAY23-04 PDF failure remains recoverable after the order is paid
    Invoice PDF generation fails after the order is already Paid. Durable retry later completes the invoice without repeating the Paid write.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And a verified successful checkout with fulfillment mode "pdf_failure"
    Then the response matches case "PAY23-04"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    When the durable fulfillment command runs
    Then the order is paid and invoice fulfillment is scheduled for retry
    When the invoice retry becomes due and the durable fulfillment command runs
    Then one paid order and one completed invoice are recorded
