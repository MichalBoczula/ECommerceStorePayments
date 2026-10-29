Feature: Liveness and readiness through the public API

  Scenario: PAY11-22 Compatibility health alias
    The compatibility health alias is requested through the public API. It returns the same healthy process response as liveness.
    Given the health request uses
      | Field | Value   |
      | Path  | /health |
    When I request the health probe
    Then the response matches case "PAY11-22"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
      | JSON.status  | "healthy"        |

  Scenario: PAY11-19 Healthy liveness
    The process liveness route is requested through the public API. It returns healthy independently of payment creation.
    Given the health request uses
      | Field | Value        |
      | Path  | /health/live |
    When I request the health probe
    Then the response matches case "PAY11-19"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
      | JSON.status  | "healthy"        |

  Scenario: PAY11-20 Healthy readiness probes real MongoDB
    Readiness runs with a reachable real MongoDB database. The public readiness response reports that the service is healthy.
    Given the health request uses
      | Field | Value         |
      | Path  | /health/ready |
    When I request the health probe
    Then the response matches case "PAY11-20"
      | Field        | Value            |
      | HTTPStatuses | 200              |
      | ContentType  | application/json |
      | Code         | -                |
      | JSON.status  | "healthy"        |

  Scenario: PAY11-21 Failed readiness keeps liveness healthy
    The MongoDB readiness probe throws a controlled dependency failure. Readiness returns a safe problem while a supporting liveness request succeeds.
    Given the health request uses
      | Field | Value         |
      | Path  | /health/ready |
    And the MongoDB readiness probe fails
    When I request the health probe
    Then the response matches case "PAY11-21"
      | Field        | Value                    |
      | HTTPStatuses | 503                      |
      | ContentType  | application/problem+json |
      | Code         | service_unavailable      |
    And the error hides the database failure
    And liveness is still healthy
