Feature: Original signed webhook verification boundaries

  Scenario: PAY07-01 Reject an empty physical signature header
    The body remains a valid paid checkout snapshot but its sole signature header is empty. Verification returns the complete safe problem and preserves every populated document.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | empty                      |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-01"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value       |
      | SignatureHeaders       | 1           |
      | MatchingV1Signatures   | 0           |
      | BodyBytes              | natural     |
      | SignedBytesEqual       | true        |
      | TimestampOffsetSeconds | unparseable |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-02 Reject a signature from another endpoint secret
    A valid checkout body is signed with another synthetic endpoint secret. The exact delivered bytes are retained, while verification rejects the signature without changing payment, history or receipts.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | wrong_secret               |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-02"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 0       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-03 Reject a noninteger signature timestamp
    The signature header contains a noninteger timestamp while the checkout body remains unchanged. The API rejects the malformed header safely and preserves every current and archived document.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | malformed_timestamp        |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-03"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value       |
      | SignatureHeaders       | 1           |
      | MatchingV1Signatures   | 0           |
      | BodyBytes              | natural     |
      | SignedBytesEqual       | true        |
      | TimestampOffsetSeconds | unparseable |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-04 Reject a signature without a version-one digest
    A correctly computed digest appears under the unsupported v0 scheme. The webhook requires a v1 signature and preserves all populated collections when rejecting this delivery.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | no_v1                      |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-04"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 0       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-05 Reject an incorrect version-one digest
    A well-formed current timestamp accompanies an incorrect hexadecimal v1 digest. The public problem is exact and safe, and no receipt or payment change is allowed.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | bad_v1                     |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-05"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 0       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-06 Reject a correctly signed timestamp older than the tolerance
    The exact paid checkout bytes carry a mathematically valid signature timestamped 301 seconds before the fixed SDK comparison clock. Verification rejects its age and preserves all stored state.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | -301                       |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-06"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | -301    |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-07 Accept the inclusive three-hundred-second timestamp boundary
    A valid unrelated event is signed exactly 300 seconds before the SDK comparison clock. The real verifier accepts it and stores one exact ignored receipt whose digest covers the original bytes.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                         |
      | EventType              | payment_intent.payment_failed |
      | PayloadVariant         | normal                        |
      | MutationPath           | -                             |
      | MutationValue          | -                             |
      | SignatureMode          | correct                       |
      | TimestampOffsetSeconds | -300                          |
      | ContentType            | application/json              |
      | BodyBytes              | natural                       |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-07"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | -300    |
    And the accepted verification stores this exact ignored receipt
      | Field               | Value                           |
      | _id                 | {event.id}                      |
      | event_type          | "payment_intent.payment_failed" |
      | payload_digest      | {request.sha256}                |
      | outcome             | "unknown"                       |
      | payment_id          | null                            |
      | order_id            | null                            |
      | attempt_id          | null                            |
      | amount_minor        | null                            |
      | currency            | null                            |
      | session_id          | null                            |
      | provider_payment_id | null                            |
      | state               | "ignored"                       |
      | reason              | "unsupported_event"             |
      | received_at         | {request.window}                |
      | completed_at        | {request.window}                |
      | fulfillment_status  | null                            |

  Scenario: PAY07-08 Accept one valid rotated digest within a single header
    One physical header contains an invalid v1 digest followed by the valid v1 digest. Signature rotation succeeds through the real SDK while an unrelated event leaves all payment and history fields unchanged.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                         |
      | EventType              | payment_intent.payment_failed |
      | PayloadVariant         | normal                        |
      | MutationPath           | -                             |
      | MutationValue          | -                             |
      | SignatureMode          | multiple_v1                   |
      | TimestampOffsetSeconds | 0                             |
      | ContentType            | application/json              |
      | BodyBytes              | natural                       |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-08"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And the accepted verification stores this exact ignored receipt
      | Field               | Value                           |
      | _id                 | {event.id}                      |
      | event_type          | "payment_intent.payment_failed" |
      | payload_digest      | {request.sha256}                |
      | outcome             | "unknown"                       |
      | payment_id          | null                            |
      | order_id            | null                            |
      | attempt_id          | null                            |
      | amount_minor        | null                            |
      | currency            | null                            |
      | session_id          | null                            |
      | provider_payment_id | null                            |
      | state               | "ignored"                       |
      | reason              | "unsupported_event"             |
      | received_at         | {request.window}                |
      | completed_at        | {request.window}                |
      | fulfillment_status  | null                            |

  Scenario: PAY07-09 Reject two physical signature headers even when both are valid
    Two separate physical Stripe-Signature headers each authenticate the unchanged checkout body. The route rejects header multiplicity and the evidence retains both header values without coalescing their identities.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | duplicate_headers          |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-09"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 2       |
      | MatchingV1Signatures   | 2       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-10 Record the SDK acceptance of a future signed timestamp
    The current SDK rejects old timestamps but accepts a correctly signed future timestamp. This scenario records that policy explicitly with a one-hour future signature and an exact ignored receipt.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                         |
      | EventType              | payment_intent.payment_failed |
      | PayloadVariant         | normal                        |
      | MutationPath           | -                             |
      | MutationValue          | -                             |
      | SignatureMode          | correct                       |
      | TimestampOffsetSeconds | 3600                          |
      | ContentType            | application/json              |
      | BodyBytes              | natural                       |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-10"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 3600    |
    And the accepted verification stores this exact ignored receipt
      | Field               | Value                           |
      | _id                 | {event.id}                      |
      | event_type          | "payment_intent.payment_failed" |
      | payload_digest      | {request.sha256}                |
      | outcome             | "unknown"                       |
      | payment_id          | null                            |
      | order_id            | null                            |
      | attempt_id          | null                            |
      | amount_minor        | null                            |
      | currency            | null                            |
      | session_id          | null                            |
      | provider_payment_id | null                            |
      | state               | "ignored"                       |
      | reason              | "unsupported_event"             |
      | received_at         | {request.window}                |
      | completed_at        | {request.window}                |
      | fulfillment_status  | null                            |

  Scenario: PAY07-11 Reject semantically equal JSON reencoded after signing
    The signed compact JSON is reencoded with indentation before delivery. Its parsed object remains identical but its bytes change, so signature verification rejects it without any durable state change.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | reencoded                  |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-11"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 0       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | false   |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-12 Reject correctly signed malformed JSON
    A current valid signature covers malformed JSON bytes. Authentication cannot make the payload valid; the API returns the complete safe problem without echoing fixture diagnostics or mutating populated collections.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | malformed_json             |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-12"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-13 Reject duplicate top-level JSON keys
    The raw signed JSON repeats its event id key with the same value. Verification rejects duplicate keys even though a permissive parser would return an otherwise valid checkout event.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | duplicate_event_id         |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-13"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-14 Reject duplicate nested metadata keys
    The signed checkout metadata repeats payment_id with the same value. Raw bytes retain the duplicate nested key, and verification rejects the payload without changing the existing payment or receipt collection.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | duplicate_metadata         |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-14"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-15 Reject signed invalid UTF-8 bytes
    A mathematically valid signature covers a checkout body ending in an invalid UTF-8 byte. The byte evidence is lossless and verification rejects decoding before any receipt or payment change.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | invalid_utf8               |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-15"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-16 Reject a signed JSON array root
    The valid checkout event is wrapped in a JSON array and signed over those exact bytes. Verification requires an event object and preserves every populated current, history and receipt document.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | array                      |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-16"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-17 Reject a signed JSON null root
    A current signature authenticates the literal JSON null. The webhook requires an event object and returns an exact safe problem without creating a receipt or changing any populated document.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | null                       |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-17"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-18 Reject a signed empty body
    The signature authenticates an empty byte sequence with application/json media. The API returns webhook_invalid and preserves every populated collection and external call count.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | empty                      |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | 0                          |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-18"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value |
      | SignatureHeaders       | 1     |
      | MatchingV1Signatures   | 1     |
      | BodyBytes              | 0     |
      | SignedBytesEqual       | true  |
      | TimestampOffsetSeconds | 0     |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-19 Reject a live-mode event envelope
    The signed envelope declares live mode while every checkout field remains valid. Test-mode verification rejects that isolated envelope value without any durable change.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | livemode                   |
      | MutationValue          | true                       |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-19"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-20 Reject an event from a connected account
    The signed envelope adds a connected-account identity to an otherwise valid checkout. The endpoint is bound to its own account and rejects the event while retaining every populated document.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | account                    |
      | MutationValue          | "acct_other"               |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-20"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-21 Reject an organization-context event
    An otherwise valid signed checkout envelope adds organization context. Verification rejects this endpoint-scope mismatch and leaves all payment, history and receipt fields unchanged.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | context                    |
      | MutationValue          | "organization_other"       |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-21"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-22 Reject an incorrect envelope object kind
    The signed envelope changes only its object discriminator from event to another object type. Verification rejects the wrong envelope kind before recording any receipt.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | object                     |
      | MutationValue          | "payment_intent"           |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-22"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-23 Reject an event identifier with only its prefix
    The signed envelope event id contains only evt_ with no identifier suffix. Verification rejects that isolated malformed identifier and preserves the complete populated state.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | id                         |
      | MutationValue          | "evt_"                     |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-23"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-24 Reject a live-mode checkout session
    The envelope remains a valid test event while only its checkout session declares live mode. Verification rejects the inconsistent session and retains every existing current and archived field.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | data.object.livemode       |
      | MutationValue          | true                       |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-24"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-25 Reject a boolean checkout amount
    The signed session replaces the integer minor-unit amount with JSON true. Verification rejects the boolean type without treating it as a Python integer or changing populated collections.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | data.object.amount_total   |
      | MutationValue          | true                       |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-25"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-26 Reject a floating-point checkout amount
    The signed session uses JSON 1299.0 instead of an integer minor-unit token. Verification rejects the amount type while preserving the entire payment, history and receipt state.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | data.object.amount_total   |
      | MutationValue          | 1299.0                     |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-26"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-27 Reject missing checkout metadata
    The signed session physically omits metadata while its other fields remain valid. Verification returns the complete safe problem without creating any receipt or changing the Pending payment.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | data.object.metadata       |
      | MutationValue          | {omit}                     |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-27"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-28 Reject malformed attempt metadata UUID
    The signed session changes only the attempt metadata to an invalid UUID string. Verification rejects that contract value before storage and preserves all populated documents.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                           |
      | EventType              | checkout.session.completed      |
      | PayloadVariant         | normal                          |
      | MutationPath           | data.object.metadata.attempt_id |
      | MutationValue          | "invalid"                       |
      | SignatureMode          | correct                         |
      | TimestampOffsetSeconds | 0                               |
      | ContentType            | application/json                |
      | BodyBytes              | natural                         |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-28"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-29 Reject a zero attempt metadata UUID
    The signed session replaces its attempt identity with the zero UUID. Verification rejects that isolated identifier and preserves the real reserved attempt, payment, history and unrelated receipts.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                                  |
      | EventType              | checkout.session.completed             |
      | PayloadVariant         | normal                                 |
      | MutationPath           | data.object.metadata.attempt_id        |
      | MutationValue          | "00000000-0000-0000-0000-000000000000" |
      | SignatureMode          | correct                                |
      | TimestampOffsetSeconds | 0                                      |
      | ContentType            | application/json                       |
      | BodyBytes              | natural                                |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-29"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-30 Reject a client reference that differs from payment metadata
    The signed client reference names another valid UUID while payment metadata retains the real payment id. Verification rejects this internal contract inconsistency without recording a receipt.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                                  |
      | EventType              | checkout.session.completed             |
      | PayloadVariant         | normal                                 |
      | MutationPath           | data.object.client_reference_id        |
      | MutationValue          | "99999999-9999-4999-8999-999999999999" |
      | SignatureMode          | correct                                |
      | TimestampOffsetSeconds | 0                                      |
      | ContentType            | application/json                       |
      | BodyBytes              | natural                                |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-30"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-31 Reject a live session identifier in a test event
    The signed checkout session id uses a live-mode prefix while the envelope and session remain test-mode. Verification rejects the inconsistent identifier and preserves every stored field.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | data.object.id             |
      | MutationValue          | "cs_live_other"            |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-31"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-32 Reject a paid completion without a payment intent
    The signed paid completion physically sets its payment_intent to null. Verification rejects the missing paid-provider identity without confirming the payment or changing any existing receipt.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | data.object.payment_intent |
      | MutationValue          | null                       |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-32"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-33 Reject a non-PLN webhook session
    The signed session changes only its currency to eur while retaining the original amount and metadata. The current hosted-checkout verifier rejects the unsupported currency without altering durable state.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | data.object.currency       |
      | MutationValue          | "eur"                      |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-33"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-34 Reject subscription mode in a checkout notification
    The signed session changes only its mode from payment to subscription. Verification rejects the unsupported checkout contract and preserves every populated current, history and receipt document.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | data.object.mode           |
      | MutationValue          | "subscription"             |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-34"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-35 Reject an open session reported as completed
    The signed event type remains checkout.session.completed but its session status is open. Verification rejects the inconsistent completion contract and leaves every stored field unchanged.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | data.object.status         |
      | MutationValue          | "open"                     |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-35"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-36 Reject an unsupported completion payment status
    The signed complete session reports no_payment_required instead of paid or unpaid. Verification rejects that isolated status value and preserves the Pending payment and all populated collections.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | data.object.payment_status |
      | MutationValue          | "no_payment_required"      |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-36"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-37 Reject a missing webhook media type
    The correctly signed body arrives without a Content-Type header. The route returns the exact unsupported-media problem before verification and preserves all populated durable state.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | absent                     |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-37"
      | Field                  | Value                                        |
      | HTTPStatuses           | 415                                          |
      | ContentType            | application/problem+json                     |
      | Code                   | unsupported_media_type                       |
      | JSON.type              | "about:blank"                                |
      | JSON.title             | "Unsupported Media Type"                     |
      | JSON.status            | 415                                          |
      | JSON.detail            | "The request content type is not supported." |
      | JSON.instance          | "/payments/webhooks/stripe"                  |
      | JSON.errors            | []                                           |
      | JSON.missingProperties | []                                           |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-38 Reject a JSON suffix media type for this endpoint
    The correctly signed checkout bytes arrive as application/problem+json. This webhook endpoint requires application/json, so the media rejection preserves every populated document and external call count.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | -                          |
      | MutationValue          | -                          |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/problem+json   |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-38"
      | Field                  | Value                                        |
      | HTTPStatuses           | 415                                          |
      | ContentType            | application/problem+json                     |
      | Code                   | unsupported_media_type                       |
      | JSON.type              | "about:blank"                                |
      | JSON.title             | "Unsupported Media Type"                     |
      | JSON.status            | 415                                          |
      | JSON.detail            | "The request content type is not supported." |
      | JSON.instance          | "/payments/webhooks/stripe"                  |
      | JSON.errors            | []                                           |
      | JSON.missingProperties | []                                           |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-39 Accept application-json media with case and charset
    The original signed bytes arrive with Application/JSON and a UTF-8 charset parameter. Media normalization accepts the request and the stored ignored receipt retains the exact received-byte digest.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                           |
      | EventType              | payment_intent.payment_failed   |
      | PayloadVariant         | normal                          |
      | MutationPath           | -                               |
      | MutationValue          | -                               |
      | SignatureMode          | correct                         |
      | TimestampOffsetSeconds | 0                               |
      | ContentType            | Application/JSON; charset=utf-8 |
      | BodyBytes              | natural                         |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-39"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And the accepted verification stores this exact ignored receipt
      | Field               | Value                           |
      | _id                 | {event.id}                      |
      | event_type          | "payment_intent.payment_failed" |
      | payload_digest      | {request.sha256}                |
      | outcome             | "unknown"                       |
      | payment_id          | null                            |
      | order_id            | null                            |
      | attempt_id          | null                            |
      | amount_minor        | null                            |
      | currency            | null                            |
      | session_id          | null                            |
      | provider_payment_id | null                            |
      | state               | "ignored"                       |
      | reason              | "unsupported_event"             |
      | received_at         | {request.window}                |
      | completed_at        | {request.window}                |
      | fulfillment_status  | null                            |

  Scenario: PAY07-40 Accept exactly one mebibyte of signed JSON bytes
    A valid unrelated event is padded with signed trailing JSON whitespace to exactly 1048576 bytes. The inclusive request-size boundary succeeds and the ignored receipt hashes every received byte.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                         |
      | EventType              | payment_intent.payment_failed |
      | PayloadVariant         | normal                        |
      | MutationPath           | -                             |
      | MutationValue          | -                             |
      | SignatureMode          | correct                       |
      | TimestampOffsetSeconds | 0                             |
      | ContentType            | application/json              |
      | BodyBytes              | 1048576                       |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-40"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | 1048576 |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And the accepted verification stores this exact ignored receipt
      | Field               | Value                           |
      | _id                 | {event.id}                      |
      | event_type          | "payment_intent.payment_failed" |
      | payload_digest      | {request.sha256}                |
      | outcome             | "unknown"                       |
      | payment_id          | null                            |
      | order_id            | null                            |
      | attempt_id          | null                            |
      | amount_minor        | null                            |
      | currency            | null                            |
      | session_id          | null                            |
      | provider_payment_id | null                            |
      | state               | "ignored"                       |
      | reason              | "unsupported_event"             |
      | received_at         | {request.window}                |
      | completed_at        | {request.window}                |
      | fulfillment_status  | null                            |

  Scenario: PAY07-41 Accept original multibyte UTF-8 event bytes
    A signed unrelated event includes Polish characters and an emoji as original UTF-8 bytes. The real SDK accepts the signature and the stored digest preserves those exact multibyte bytes.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                         |
      | EventType              | payment_intent.payment_failed |
      | PayloadVariant         | unicode                       |
      | MutationPath           | -                             |
      | MutationValue          | -                             |
      | SignatureMode          | correct                       |
      | TimestampOffsetSeconds | 0                             |
      | ContentType            | application/json              |
      | BodyBytes              | natural                       |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-41"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And the accepted verification stores this exact ignored receipt
      | Field               | Value                           |
      | _id                 | {event.id}                      |
      | event_type          | "payment_intent.payment_failed" |
      | payload_digest      | {request.sha256}                |
      | outcome             | "unknown"                       |
      | payment_id          | null                            |
      | order_id            | null                            |
      | attempt_id          | null                            |
      | amount_minor        | null                            |
      | currency            | null                            |
      | session_id          | null                            |
      | provider_payment_id | null                            |
      | state               | "ignored"                       |
      | reason              | "unsupported_event"             |
      | received_at         | {request.window}                |
      | completed_at        | {request.window}                |
      | fulfillment_status  | null                            |

  Scenario: PAY07-42 Accept the maximum event identifier length
    A correctly signed unrelated event has an event identifier exactly 255 characters long. Verification accepts the boundary and stores one complete ignored receipt under that exact identifier.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                                                                                                                                                                                                                                                             |
      | EventType              | payment_intent.payment_failed                                                                                                                                                                                                                                     |
      | PayloadVariant         | normal                                                                                                                                                                                                                                                            |
      | MutationPath           | id                                                                                                                                                                                                                                                                |
      | MutationValue          | "evt_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" |
      | SignatureMode          | correct                                                                                                                                                                                                                                                           |
      | TimestampOffsetSeconds | 0                                                                                                                                                                                                                                                                 |
      | ContentType            | application/json                                                                                                                                                                                                                                                  |
      | BodyBytes              | natural                                                                                                                                                                                                                                                           |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-42"
      | Field         | Value            |
      | HTTPStatuses  | 200              |
      | ContentType   | application/json |
      | Code          | -                |
      | JSON.received | true             |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And the accepted verification stores this exact ignored receipt
      | Field               | Value                           |
      | _id                 | {event.id}                      |
      | event_type          | "payment_intent.payment_failed" |
      | payload_digest      | {request.sha256}                |
      | outcome             | "unknown"                       |
      | payment_id          | null                            |
      | order_id            | null                            |
      | attempt_id          | null                            |
      | amount_minor        | null                            |
      | currency            | null                            |
      | session_id          | null                            |
      | provider_payment_id | null                            |
      | state               | "ignored"                       |
      | reason              | "unsupported_event"             |
      | received_at         | {request.window}                |
      | completed_at        | {request.window}                |
      | fulfillment_status  | null                            |

  Scenario: PAY07-43 Reject an event identifier one character too long
    The correctly signed event identifier is 256 characters long, one beyond the verifier limit. The API rejects that isolated boundary without creating a receipt or changing populated state.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                                                                                                                                                                                                                                                              |
      | EventType              | checkout.session.completed                                                                                                                                                                                                                                         |
      | PayloadVariant         | normal                                                                                                                                                                                                                                                             |
      | MutationPath           | id                                                                                                                                                                                                                                                                 |
      | MutationValue          | "evt_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" |
      | SignatureMode          | correct                                                                                                                                                                                                                                                            |
      | TimestampOffsetSeconds | 0                                                                                                                                                                                                                                                                  |
      | ContentType            | application/json                                                                                                                                                                                                                                                   |
      | BodyBytes              | natural                                                                                                                                                                                                                                                            |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-43"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-44 Reject a webhook amount below the supported minimum
    The signed checkout amount is 199 minor units while all other fields remain valid. Verification rejects the below-minimum value without changing any payment, history or receipt document.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | data.object.amount_total   |
      | MutationValue          | 199                        |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-44"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |

  Scenario: PAY07-45 Reject a webhook amount above the supported maximum
    The signed checkout amount is 100000000 minor units, one beyond the supported maximum. Verification returns the complete safe problem and preserves the entire populated state.
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
    And a checkout created through the API
    And the webhook verification request is prepared
      | Field                  | Value                      |
      | EventType              | checkout.session.completed |
      | PayloadVariant         | normal                     |
      | MutationPath           | data.object.amount_total   |
      | MutationValue          | 100000000                  |
      | SignatureMode          | correct                    |
      | TimestampOffsetSeconds | 0                          |
      | ContentType            | application/json           |
      | BodyBytes              | natural                    |
    And I remember webhook verification state
    When I deliver the prepared verification webhook
    Then the response matches case "PAY07-45"
      | Field                  | Value                                      |
      | HTTPStatuses           | 400                                        |
      | ContentType            | application/problem+json                   |
      | Code                   | webhook_invalid                            |
      | JSON.type              | "about:blank"                              |
      | JSON.title             | "Bad Request"                              |
      | JSON.status            | 400                                        |
      | JSON.detail            | "Webhook signature or payload is invalid." |
      | JSON.instance          | "/payments/webhooks/stripe"                |
      | JSON.errors            | []                                         |
      | JSON.missingProperties | []                                         |
    And the webhook delivery matches this verification evidence
      | Field                  | Value   |
      | SignatureHeaders       | 1       |
      | MatchingV1Signatures   | 1       |
      | BodyBytes              | natural |
      | SignedBytesEqual       | true    |
      | TimestampOffsetSeconds | 0       |
    And verification rejection preserves this complete state
      | Field            | Value   |
      | CurrentStatus    | pending |
      | CurrentVersion   | 2       |
      | NewReceipts      | 0       |
      | NewExternalCalls | 0       |
