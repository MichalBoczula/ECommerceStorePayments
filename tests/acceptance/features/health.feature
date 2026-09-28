Feature: Liveness and readiness through the public API

  Scenario: PAY11-19 Healthy liveness
    When I get "/health/live"
    Then the response matches case "PAY11-19"

  Scenario: PAY11-20 Healthy readiness probes real MongoDB
    When I get "/health/ready"
    Then the response matches case "PAY11-20"

  Scenario: PAY11-21 Failed readiness keeps liveness healthy
    Given the MongoDB readiness probe fails
    When I get "/health/ready"
    Then the response matches case "PAY11-21"
    And the error hides the database failure
    And liveness is still healthy
