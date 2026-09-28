Feature: Payment API with real persistence and a controlled Orders boundary

  Scenario: PAY11-01 Create a payment from a payable order
    Given a payable order
    When I pay the order
    Then the response matches case "PAY11-01"
    And the database has 1 current payment and 0 history snapshots
    And the current payment is "Created" at version 0

  Scenario: PAY11-02 Read a payment by order ID
    Given a payment created through the API
    When I get the payment by order ID
    Then the response matches case "PAY11-02"
    And the response refers to the original payment

  Scenario: PAY11-03 Repeat Pay without writing or calling Orders again
    Given a payment created through the API
    When I pay the order
    Then the response matches case "PAY11-03"
    And the response refers to the original payment
    And Orders was not called again
    And the database has 1 current payment and 0 history snapshots

  Scenario: PAY11-04 Missing payment
    Given a payable order
    When I get the payment by order ID
    Then the response matches case "PAY11-04"
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-05 Missing order
    Given Orders returns "missing"
    When I pay the order
    Then the response matches case "PAY11-05"
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-06 Order not payable
    Given Orders reports status "Paid"
    When I pay the order
    Then the response matches case "PAY11-06"
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-07 Invalid Orders response
    Given Orders returns "invalid"
    When I pay the order
    Then the response matches case "PAY11-07"
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-08 Orders timeout
    Given Orders returns "timeout"
    When I pay the order
    Then the response matches case "PAY11-08"
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-09 Orders outage
    Given Orders returns "outage"
    When I pay the order
    Then the response matches case "PAY11-09"
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-10 Retry a failed payment and archive its previous state
    Given a "Failed" payment created through the API
    When I pay the order
    Then the response matches case "PAY11-10"
    And the response refers to the original payment
    And the current payment is "Created" at version 3
    And the history statuses are "Created,Pending,Failed"

  Scenario: PAY11-11 Retry a canceled payment
    Given a "Canceled" payment created through the API
    When I pay the order
    Then the response matches case "PAY11-11"
    And the response refers to the original payment
    And the current payment is "Created" at version 2
    And the history statuses are "Created,Canceled"

  Scenario: PAY11-12 Reject retry when the order total changed
    Given a "Failed" payment created through the API
    And Orders total has changed
    When I pay the order
    Then the response matches case "PAY11-12"
    And the current payment is "Failed" at version 2
    And the history statuses are "Created,Pending"

  Scenario: PAY11-13 Concurrent Pay creates one current payment
    Given a payable order
    When I submit two Pay requests concurrently
    Then the response matches case "PAY11-13"
    And both responses refer to one payment
    And the database has 1 current payment and 0 history snapshots

  Scenario: PAY11-14 Invalid order ID
    Given a payable order
    When I pay with an invalid order ID
    Then the response matches case "PAY11-14"
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-15 Malformed JSON body
    Given a payable order
    When I pay with malformed JSON
    Then the response matches case "PAY11-15"
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-16 Unsupported request media
    Given a payable order
    When I pay with plain text
    Then the response matches case "PAY11-16"
    And the database has 0 current payments and 0 history snapshots

  Scenario: PAY11-17 Unknown route
    Given a payable order
    When I request an unknown route
    Then the response matches case "PAY11-17"

  Scenario: PAY11-18 Wrong method
    Given a payable order
    When I post to a read-only health route
    Then the response matches case "PAY11-18"
    And the Allow header is "GET"
