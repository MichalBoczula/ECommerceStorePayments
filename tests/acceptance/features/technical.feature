Feature: Technical operations with actual lifecycle and command evidence

  Scenario: PAY13-01 Serve complete Swagger UI HTML
    Swagger UI returns the complete framework-generated HTML twice with the real OpenAPI and OAuth redirect references. Populated collections and provider sessions remain unchanged.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value    |
      | Mode   | docs     |
      | Target | /swagger |
      | Value  | source   |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-01"
      | Field         | Value                    |
      | Outcome       | response                 |
      | HTTPStatuses  | 200                      |
      | ContentType   | text/html; charset=utf-8 |
      | Code          | -                        |
      | ExceptionType | <none>                   |
      | Result        | rendered                 |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-02 Serve complete ReDoc HTML
    ReDoc returns complete source-generated HTML twice with the OpenAPI reference. This verifies served HTML and protocol headers without claiming a browser loaded remote assets.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value  |
      | Mode   | docs   |
      | Target | /redoc |
      | Value  | source |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-02"
      | Field         | Value                    |
      | Outcome       | response                 |
      | HTTPStatuses  | 200                      |
      | ContentType   | text/html; charset=utf-8 |
      | Code          | -                        |
      | ExceptionType | <none>                   |
      | Result        | rendered                 |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-03 Serve the actual OAuth redirect document
    The framework OAuth redirect route returns the exact source-generated HTML twice. Existing payments, history and receipts remain unchanged.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value                 |
      | Mode   | docs                  |
      | Target | /docs/oauth2-redirect |
      | Value  | source                |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-03"
      | Field         | Value                    |
      | Outcome       | response                 |
      | HTTPStatuses  | 200                      |
      | ContentType   | text/html; charset=utf-8 |
      | Code          | -                        |
      | ExceptionType | <none>                   |
      | Result        | rendered                 |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-04 Export documentation without a Mongo connection
    A cold application serves repeated OpenAPI and documentation responses without entering lifespan or allocating Mongo. The complete schema matches the actual four-file export; this does not claim failed startup serves traffic.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value         |
      | Mode   | offline-docs  |
      | Target | /openapi.json |
      | Value  | no-lifespan   |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-04"
      | Field         | Value            |
      | Outcome       | response         |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | ExceptionType | <none>           |
      | Result        | rendered         |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-05 Recover readiness after an owned Mongo outage
    Only a scenario-owned replica is stopped. Readiness reports a complete safe problem while liveness, documentation and an independent database remain available. Restarting the same container restores readiness and all stored fields.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value                 |
      | Mode   | outage                |
      | Target | /health/ready         |
      | Value  | restart-owned-replica |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-05"
      | Field                  | Value                           |
      | Outcome                | response                        |
      | HTTPStatuses           | 503                             |
      | ContentType            | application/problem+json        |
      | Code                   | service_unavailable             |
      | ExceptionType          | <none>                          |
      | Result                 | observed                        |
      | JSON.type              | "about:blank"                   |
      | JSON.title             | "Service Unavailable"           |
      | JSON.status            | 503                             |
      | JSON.detail            | "Payment service is not ready." |
      | JSON.instance          | "/health/ready"                 |
      | JSON.errors            | []                              |
      | JSON.missingProperties | []                              |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-06 Expose ping-only readiness on standalone Mongo
    A real standalone Mongo passes ping-based readiness. A supporting checkout fails safely because transactions are unavailable, preserves two populated Created payments and makes no Stripe request. Readiness does not certify transaction capability.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value           |
      | Mode   | standalone      |
      | Target | /health/ready   |
      | Value  | no-transactions |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-06"
      | Field         | Value            |
      | Outcome       | response         |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | ExceptionType | <none>           |
      | Result        | observed         |
      | JSON.status   | "healthy"        |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-07 Cancel an in-flight real readiness ping
    The HTTP task is cancelled after entering the real Mongo driver await against a stopped scenario-owned replica. Evidence retains CancelledError with no completed HTTP response. Restart restores healthy probes and exact data, and actual clients close.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value            |
      | Mode   | cancel-readiness |
      | Target | /health/ready    |
      | Value  | driver-await     |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-07"
      | Field         | Value          |
      | Outcome       | cancelled      |
      | HTTPStatuses  | <none>         |
      | ContentType   | <none>         |
      | Code          | -              |
      | ExceptionType | CancelledError |
      | Result        | cancelled      |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-08 Cancel fulfillment during the Orders read
    Cancellation interrupts an actual fulfillment command while the controlled Orders reply is held. The real claimed lease remains intact without a failure marker. At lease expiry a fresh command reclaims and completes exactly one logical Paid update and invoice.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value         |
      | Mode   | cancel-worker |
      | Target | fulfill       |
      | Value  | order         |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 6 |
      | Receipts | 2 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-08"
      | Field         | Value          |
      | Outcome       | cancelled      |
      | HTTPStatuses  | <none>         |
      | ContentType   | <none>         |
      | Code          | -              |
      | ExceptionType | CancelledError |
      | Result        | cancelled      |
    And technical work has this complete receipt
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 2                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-09 Cancel fulfillment after Paid mutation before acknowledgement
    The controlled upstream applies Paid before its response is delivered and the actual worker is cancelled. Recovery at the lease boundary reads the Paid state, avoids a second mutation and creates one invoice; the real receipt records two attempts and complete cleanup.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value         |
      | Mode   | cancel-worker |
      | Target | fulfill       |
      | Value  | paid          |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 6 |
      | Receipts | 2 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-09"
      | Field         | Value          |
      | Outcome       | cancelled      |
      | HTTPStatuses  | <none>         |
      | ContentType   | <none>         |
      | Code          | -              |
      | ExceptionType | CancelledError |
      | Result        | cancelled      |
    And technical work has this complete receipt
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 2                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-10 Isolate two hosts sharing business identities
    Two real hosts use different databases with the same order and client IDs but different complete money and stored fields. Full reads prove isolation. Closing and dropping only the peer database preserves the primary database and its readiness.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value           |
      | Mode   | isolation       |
      | Target | databases       |
      | Value  | same-identities |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-10"
      | Field         | Value    |
      | Outcome       | action   |
      | HTTPStatuses  | <none>   |
      | ContentType   | <none>   |
      | Code          | -        |
      | ExceptionType | <none>   |
      | Result        | isolated |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-11 Reject a conflicting unique index before serving
    A populated candidate database has a genuinely conflicting named index. Actual application startup fails before yielding and closes its real resources. Removing only the wrong index allows a new host to build exact indexes and read every original field.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value          |
      | Mode   | startup        |
      | Target | indexes        |
      | Value  | index-conflict |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-11"
      | Field         | Value            |
      | Outcome       | action           |
      | HTTPStatuses  | <none>           |
      | ContentType   | <none>           |
      | Code          | -                |
      | ExceptionType | OperationFailure |
      | Result        | rejected         |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-12 Reject duplicate order documents during startup
    An explicitly injected duplicate order prevents the real unique index from building. Startup never serves traffic and preserves every populated field. Removing only that duplicate restores startup, exact named indexes and full reads.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value           |
      | Mode   | startup         |
      | Target | indexes         |
      | Value  | duplicate-order |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-12"
      | Field         | Value            |
      | Outcome       | action           |
      | HTTPStatuses  | <none>           |
      | ContentType   | <none>           |
      | Code          | -                |
      | ExceptionType | DuplicateKeyError |
      | Result        | rejected         |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-13 Bound failed startup and close allocated resources
    Startup points at an unreachable local port with bounded driver and probe timeouts. The actual timeout prevents host yield, closes real Mongo, Orders and Stripe resources and leaves the independent populated service unchanged.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value       |
      | Mode   | startup     |
      | Target | mongo       |
      | Value  | unreachable |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-13"
      | Field         | Value                                    |
      | Outcome       | action                                   |
      | HTTPStatuses  | <none>                                   |
      | ContentType   | <none>                                   |
      | Code          | -                                        |
      | ExceptionType | TimeoutError,ServerSelectionTimeoutError |
      | Result        | rejected                                 |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-14 Reject fulfill command limit 0
    The actual fulfill CLI rejects limit 0 with exit code 2 before settings or client allocation. The actual fulfillment run entry also rejects the value before allocation. All populated collection fields and provider sessions remain unchanged.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value   |
      | Mode   | limits  |
      | Target | fulfill |
      | Value  | 0       |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-14"
      | Field         | Value      |
      | Outcome       | action     |
      | HTTPStatuses  | <none>     |
      | ContentType   | <none>     |
      | Code          | -          |
      | ExceptionType | ValueError |
      | Result        | rejected   |
    And the technical command has these exact effects
      | Field             | Value     |
      | CLIExitCode       | 2         |
      | ClientAllocations | 0         |
      | Collections       | unchanged |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-15 Reject fulfill command limit 1001
    The actual fulfill CLI rejects limit 1001 with exit code 2 before settings or client allocation. The actual fulfillment run entry also rejects the value before allocation. All populated collection fields and provider sessions remain unchanged.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value   |
      | Mode   | limits  |
      | Target | fulfill |
      | Value  | 1001    |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-15"
      | Field         | Value      |
      | Outcome       | action     |
      | HTTPStatuses  | <none>     |
      | ContentType   | <none>     |
      | Code          | -          |
      | ExceptionType | ValueError |
      | Result        | rejected   |
    And the technical command has these exact effects
      | Field             | Value     |
      | CLIExitCode       | 2         |
      | ClientAllocations | 0         |
      | Collections       | unchanged |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-16 Reject replay command limit 0
    The actual replay CLI rejects limit 0 with exit code 2 before settings or client allocation. This checks the replay CLI boundary. All populated collection fields and provider sessions remain unchanged.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value  |
      | Mode   | limits |
      | Target | replay |
      | Value  | 0      |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-16"
      | Field         | Value      |
      | Outcome       | action     |
      | HTTPStatuses  | <none>     |
      | ContentType   | <none>     |
      | Code          | -          |
      | ExceptionType | SystemExit |
      | Result        | rejected   |
    And the technical command has these exact effects
      | Field             | Value     |
      | CLIExitCode       | 2         |
      | ClientAllocations | 0         |
      | Collections       | unchanged |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-17 Reject replay command limit 1001
    The actual replay CLI rejects limit 1001 with exit code 2 before settings or client allocation. This checks the replay CLI boundary. All populated collection fields and provider sessions remain unchanged.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value  |
      | Mode   | limits |
      | Target | replay |
      | Value  | 1001   |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 2 |
      | History  | 5 |
      | Receipts | 1 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-17"
      | Field         | Value      |
      | Outcome       | action     |
      | HTTPStatuses  | <none>     |
      | ContentType   | <none>     |
      | Code          | -          |
      | ExceptionType | SystemExit |
      | Result        | rejected   |
    And the technical command has these exact effects
      | Field             | Value     |
      | CLIExitCode       | 2         |
      | ClientAllocations | 0         |
      | Collections       | unchanged |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-18 Accept fulfill command limit 1 with a populated batch
    The actual fulfill CLI receives two eligible records with an explicit oldest-event fixture. Limit 1 processes exactly one and preserves the other in full. A fresh command drains remaining work, a repeat reports zero, and complete durable fields, stdout and actual resource closure are retained.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value   |
      | Mode   | batch   |
      | Target | fulfill |
      | Value  | 1       |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 3 |
      | History  | 9 |
      | Receipts | 3 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-18"
      | Field         | Value     |
      | Outcome       | action    |
      | HTTPStatuses  | <none>    |
      | ContentType   | <none>    |
      | Code          | -         |
      | ExceptionType | <none>    |
      | Result        | processed |
    And technical work has this complete receipt
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 1                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the technical command has these exact effects
      | Field              | Value  |
      | PrimaryLimit       | 1      |
      | PrimaryProcessed   | 1      |
      | RemainingProcessed | 1      |
      | RepeatedProcessed  | 0      |
      | Clients            | closed |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-19 Accept fulfill command limit 1000 with a populated batch
    The actual fulfill CLI receives two eligible records with an explicit oldest-event fixture. Limit 1000 processes exactly both. A fresh command drains remaining work, a repeat reports zero, and complete durable fields, stdout and actual resource closure are retained.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value   |
      | Mode   | batch   |
      | Target | fulfill |
      | Value  | 1000    |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 3 |
      | History  | 9 |
      | Receipts | 3 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-19"
      | Field         | Value     |
      | Outcome       | action    |
      | HTTPStatuses  | <none>    |
      | ContentType   | <none>    |
      | Code          | -         |
      | ExceptionType | <none>    |
      | Result        | processed |
    And technical work has this complete receipt
      | Field                              | Value             |
      | _id                                | {before}          |
      | event_type                         | {before}          |
      | payload_digest                     | {before}          |
      | outcome                            | {before}          |
      | payment_id                         | {before}          |
      | order_id                           | {before}          |
      | attempt_id                         | {before}          |
      | amount_minor                       | {before}          |
      | currency                           | {before}          |
      | session_id                         | {before}          |
      | provider_payment_id                | {before}          |
      | state                              | {before}          |
      | reason                             | {before}          |
      | received_at                        | {before}          |
      | completed_at                       | {before}          |
      | fulfillment_status                 | "completed"       |
      | fulfillment_attempts               | 1                 |
      | fulfillment_lease_id               | null              |
      | fulfillment_lease_until            | null              |
      | fulfillment_next_attempt           | null              |
      | fulfillment_error                  | null              |
      | fulfillment_order_paid             | true              |
      | fulfillment_client_id              | {client.id}       |
      | fulfillment_invoice_id             | {invoice.id}      |
      | fulfillment_client_data_version_id | {invoice.version} |
      | fulfillment_completed_at           | {clock}           |
    And the technical command has these exact effects
      | Field              | Value  |
      | PrimaryLimit       | 1000   |
      | PrimaryProcessed   | 2      |
      | RemainingProcessed | 0      |
      | RepeatedProcessed  | 0      |
      | Clients            | closed |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-20 Accept replay command limit 1 with a populated batch
    The actual replay CLI receives two eligible records with an explicit oldest-event fixture. Limit 1 processes exactly one and preserves the other in full. A fresh command drains remaining work, a repeat reports zero, and complete durable fields, stdout and actual resource closure are retained.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value  |
      | Mode   | batch  |
      | Target | replay |
      | Value  | 1      |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 3 |
      | History  | 7 |
      | Receipts | 3 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-20"
      | Field         | Value     |
      | Outcome       | action    |
      | HTTPStatuses  | <none>    |
      | ContentType   | <none>    |
      | Code          | -         |
      | ExceptionType | <none>    |
      | Result        | processed |
    And technical work has this complete receipt
      | Field                              | Value               |
      | _id                                | {before}            |
      | event_type                         | {before}            |
      | payload_digest                     | {before}            |
      | outcome                            | {before}            |
      | payment_id                         | {before}            |
      | order_id                           | {before}            |
      | attempt_id                         | {before}            |
      | amount_minor                       | {before}            |
      | currency                           | {before}            |
      | session_id                         | {before}            |
      | provider_payment_id                | {before}            |
      | state                              | "applied"           |
      | reason                             | "payment_succeeded" |
      | received_at                        | {before}            |
      | completed_at                       | {operation.window}  |
      | fulfillment_status                 | "pending"           |
      | fulfillment_attempts               | <absent>            |
      | fulfillment_lease_id               | <absent>            |
      | fulfillment_lease_until            | <absent>            |
      | fulfillment_next_attempt           | <absent>            |
      | fulfillment_error                  | <absent>            |
      | fulfillment_order_paid             | <absent>            |
      | fulfillment_client_id              | <absent>            |
      | fulfillment_invoice_id             | <absent>            |
      | fulfillment_client_data_version_id | <absent>            |
      | fulfillment_completed_at           | <absent>            |
    And the technical command has these exact effects
      | Field              | Value  |
      | PrimaryLimit       | 1      |
      | PrimaryProcessed   | 1      |
      | RemainingProcessed | 1      |
      | RepeatedProcessed  | 0      |
      | Clients            | closed |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |

  Scenario: PAY13-21 Accept replay command limit 1000 with a populated batch
    The actual replay CLI receives two eligible records with an explicit oldest-event fixture. Limit 1000 processes exactly both. A fresh command drains remaining work, a repeat reports zero, and complete durable fields, stdout and actual resource closure are retained.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And the technical operation uses
      | Field  | Value  |
      | Mode   | batch  |
      | Target | replay |
      | Value  | 1000   |
    And populated technical collections contain
      | Field    | Value |
      | Payments | 3 |
      | History  | 7 |
      | Receipts | 3 |
    When I execute the technical operation
    Then the technical outcome matches case "PAY13-21"
      | Field         | Value     |
      | Outcome       | action    |
      | HTTPStatuses  | <none>    |
      | ContentType   | <none>    |
      | Code          | -         |
      | ExceptionType | <none>    |
      | Result        | processed |
    And technical work has this complete receipt
      | Field                              | Value               |
      | _id                                | {before}            |
      | event_type                         | {before}            |
      | payload_digest                     | {before}            |
      | outcome                            | {before}            |
      | payment_id                         | {before}            |
      | order_id                           | {before}            |
      | attempt_id                         | {before}            |
      | amount_minor                       | {before}            |
      | currency                           | {before}            |
      | session_id                         | {before}            |
      | provider_payment_id                | {before}            |
      | state                              | "applied"           |
      | reason                             | "payment_succeeded" |
      | received_at                        | {before}            |
      | completed_at                       | {operation.window}  |
      | fulfillment_status                 | "pending"           |
      | fulfillment_attempts               | <absent>            |
      | fulfillment_lease_id               | <absent>            |
      | fulfillment_lease_until            | <absent>            |
      | fulfillment_next_attempt           | <absent>            |
      | fulfillment_error                  | <absent>            |
      | fulfillment_order_paid             | <absent>            |
      | fulfillment_client_id              | <absent>            |
      | fulfillment_invoice_id             | <absent>            |
      | fulfillment_client_data_version_id | <absent>            |
      | fulfillment_completed_at           | <absent>            |
    And the technical command has these exact effects
      | Field              | Value  |
      | PrimaryLimit       | 1000   |
      | PrimaryProcessed   | 2      |
      | RemainingProcessed | 0      |
      | RepeatedProcessed  | 0      |
      | Clients            | closed |
    And technical supporting reads preserve final state
      | Field       | Value     |
      | Collections | unchanged |
      | OrdersCalls | 0         |
      | StripeCalls | 0         |
