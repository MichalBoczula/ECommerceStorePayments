Feature: Durable fulfillment of verified checkout payments

  Scenario: PAY23-01 Fulfillment reconciles ok
    Given a verified successful checkout with fulfillment mode "ok"
    Then the response matches case "PAY23-01"
    When the durable fulfillment command runs
    Then one paid order and one completed invoice are recorded
    When the successful webhook is delivered again
    And the durable fulfillment command runs
    Then fulfillment stays completed without repeating downstream writes

  Scenario: PAY23-02 Fulfillment reconciles paid_ack_lost
    Given a verified successful checkout with fulfillment mode "paid_ack_lost"
    Then the response matches case "PAY23-02"
    When the durable fulfillment command runs
    Then one paid order and one completed invoice are recorded
    When the successful webhook is delivered again
    And the durable fulfillment command runs
    Then fulfillment stays completed without repeating downstream writes

  Scenario: PAY23-03 Fulfillment reconciles invoice_ack_lost
    Given a verified successful checkout with fulfillment mode "invoice_ack_lost"
    Then the response matches case "PAY23-03"
    When the durable fulfillment command runs
    Then one paid order and one completed invoice are recorded
    When the successful webhook is delivered again
    And the durable fulfillment command runs
    Then fulfillment stays completed without repeating downstream writes

  Scenario: PAY23-04 PDF failure remains recoverable after the order is paid
    Given a verified successful checkout with fulfillment mode "pdf_failure"
    Then the response matches case "PAY23-04"
    When the durable fulfillment command runs
    Then the order is paid and invoice fulfillment is scheduled for retry
    When the invoice retry becomes due and the durable fulfillment command runs
    Then one paid order and one completed invoice are recorded
