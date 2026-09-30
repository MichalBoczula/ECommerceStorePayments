Feature: Verified checkout notifications and durable receipt

  Scenario: PAY22-01 Confirm a matching checkout and persist durable work
    Given a checkout created through the API
    And a signed checkout event "paid"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-01"
    And the current payment is "Succeeded" at version 3
    And webhook work is persisted for fulfillment
    And webhook processing did not contact external services

  Scenario: PAY22-02 Redeliver the same event without another transition
    Given a checkout created through the API
    And a signed checkout event "paid"
    And the checkout webhook was delivered
    When I deliver the checkout webhook
    Then the response matches case "PAY22-02"
    And the current payment is "Succeeded" at version 3
    And the database has 1 current payment and 3 history snapshots

  Scenario: PAY22-03 Reject a missing signature
    Given a checkout created through the API
    And a signed checkout event "paid"
    And webhook delivery is "missing"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-03"
    And the current payment is "Pending" at version 2
    And no webhook receipt exists

  Scenario: PAY22-04 Reject tampered original bytes
    Given a checkout created through the API
    And a signed checkout event "paid"
    And webhook delivery is "tampered"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-04"
    And no webhook receipt exists

  Scenario: PAY22-05 Ignore a signed unrelated event
    Given a checkout created through the API
    And a signed checkout event "unknown"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-05"
    And the current payment is "Pending" at version 2

  Scenario: PAY22-06 Record mismatched money without confirming payment
    Given a checkout created through the API
    And a signed checkout event "mismatched"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-06"
    And the current payment is "Pending" at version 2
    And the webhook receipt is "rejected"

  Scenario: PAY22-07 Expire payment without canceling the order
    Given a checkout created through the API
    And a signed checkout event "expired"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-07"
    And the current payment is "Failed" at version 3
    And webhook processing did not contact external services

  Scenario: PAY22-08 Earlier expiry cannot downgrade success
    Given a checkout created through the API
    And a signed checkout event "paid"
    And the checkout webhook was delivered
    And a signed checkout event "expired"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-08"
    And the current payment is "Succeeded" at version 3

  Scenario: PAY22-09 Concurrent duplicate delivery commits once
    Given a checkout created through the API
    And a signed checkout event "paid"
    When I deliver two checkout webhooks concurrently
    Then the response matches case "PAY22-09"
    And the current payment is "Succeeded" at version 3
    And the database has 1 current payment and 3 history snapshots

  Scenario: PAY22-10 Interrupted processing remains retryable
    Given a checkout created through the API
    And a signed checkout event "paid"
    And webhook processing fails once after receipt
    When I deliver the checkout webhook
    Then the response matches case "PAY22-10"
    And the current payment is "Pending" at version 2
    And the webhook receipt is "pending"

  Scenario: PAY22-11 Redelivery finishes an interrupted receipt
    Given a checkout created through the API
    And a signed checkout event "paid"
    And webhook processing fails once after receipt
    And the checkout webhook was delivered
    When I deliver the checkout webhook
    Then the response matches case "PAY22-11"
    And the current payment is "Succeeded" at version 3
    And webhook work is persisted for fulfillment

  Scenario: PAY22-12 Unconfigured webhook verification is unavailable
    Given a checkout created through the API
    And a signed checkout event "paid"
    And webhook delivery is "disabled"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-12"
    And no webhook receipt exists

  Scenario: PAY22-13 Reject unsupported webhook media
    Given a checkout created through the API
    And a signed checkout event "paid"
    And webhook delivery is "media"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-13"

  Scenario: PAY22-14 Reject oversized webhook before receipt
    Given a checkout created through the API
    And a signed checkout event "paid"
    And webhook delivery is "large"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-14"
    And no webhook receipt exists

  Scenario: PAY22-15 Unpaid completion cannot establish success
    Given a checkout created through the API
    And a signed checkout event "unpaid"
    When I deliver the checkout webhook
    Then the response matches case "PAY22-15"
    And the current payment is "Pending" at version 2

  Scenario: PAY22-16 New checkout enables both card and BLIK
    Given a payable order
    When I create checkout for the order
    Then the response matches case "PAY22-16"
    And checkout requests both card and BLIK
