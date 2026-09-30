Feature: Hosted checkout creation and recovery

  Scenario: PAY21-01 Create checkout from the server order
    Given a payable order
    When I create checkout for the order
    Then the response matches case "PAY21-01"
    And the current payment is "Pending" at version 2
    And the database has 1 current payment and 2 history snapshots
    And Stripe has one checkout session

  Scenario: PAY21-02 Read an existing checkout instead of creating another
    Given a checkout created through the API
    When I create checkout for the order
    Then the response matches case "PAY21-02"
    And the current payment is "Pending" at version 2
    And the database has 1 current payment and 2 history snapshots
    And Stripe has one checkout session

  Scenario: PAY21-03 Recover a timeout after the provider accepted checkout
    Given an ambiguous checkout timeout
    When I create checkout for the order
    Then the response matches case "PAY21-03"
    And the current payment is "Pending" at version 2
    And Stripe has one checkout session

  Scenario: PAY21-04 Disabled checkout does not prepare a payment
    Given checkout is disabled
    When I create checkout for the order
    Then the response matches case "PAY21-04"
    And the database has 0 current payments and 0 history snapshots
    And Stripe was not called

  Scenario: PAY21-05 Reject a Paid order before contacting Stripe
    Given Orders reports status "Paid"
    When I create checkout for the order
    Then the response matches case "PAY21-05"
    And Stripe was not called

  Scenario: PAY21-06 Report provider rejection safely
    Given Stripe responds with "rejection"
    When I create checkout for the order
    Then the response matches case "PAY21-06"
    And the current payment is "Created" at version 1

  Scenario: PAY21-07 Report an ambiguous provider timeout safely
    Given Stripe responds with "timeout_once"
    When I create checkout for the order
    Then the response matches case "PAY21-07"
    And the current payment is "Created" at version 1

  Scenario: PAY21-08 Reject a missing order
    Given Orders returns "missing"
    When I create checkout for the order
    Then the response matches case "PAY21-08"
    And Stripe was not called

  Scenario: PAY21-09 Preserve payment snapshot after the order total changes
    Given a checkout created through the API
    And Orders total has changed
    When I create checkout for the order
    Then the response matches case "PAY21-09"
    And the current payment is "Pending" at version 2
    And Stripe has one checkout session
