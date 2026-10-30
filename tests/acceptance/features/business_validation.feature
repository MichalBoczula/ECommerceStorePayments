Feature: Isolated business validation and exact Orders money

  Scenario: PAY10-01 Accept the smallest PLN unit
    Orders returns total token 0.01, currency "PLN" and status "Created", with line tokens ["0.01"]. The bodyless pay request preserves exactly 1 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 0.01                                 |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 0.01                                   |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["0.01"]                               |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-01"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1                |
      | JSON.currency     | "PLN"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1                                      |
      | currency            | "PLN"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 1     |
      | Currency    | PLN   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-02 Convert EUR without binary float drift
    Orders returns total token 0.29, currency "EUR" and status "Created", with line tokens ["0.29"]. The bodyless pay request preserves exactly 29 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 0.29                                 |
      | TotalCurrency | EUR                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 0.29                                   |
      | CurrencyToken     | "EUR"                                  |
      | LineAmountTokens  | ["0.29"]                               |
      | LineCurrencyToken | "EUR"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-02"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 29               |
      | JSON.currency     | "EUR"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 29                                     |
      | currency            | "EUR"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 29    |
      | Currency    | EUR   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-03 Sum decimal USD lines exactly
    Orders returns total token 0.30, currency "USD" and status "Created", with line tokens ["0.10", "0.20"]. The bodyless pay request preserves exactly 30 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 0.30                                 |
      | TotalCurrency | USD                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 0.30                                   |
      | CurrencyToken     | "USD"                                  |
      | LineAmountTokens  | ["0.10", "0.20"]                       |
      | LineCurrencyToken | "USD"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-03"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 30               |
      | JSON.currency     | "USD"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 30                                     |
      | currency            | "USD"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 30    |
      | Currency    | USD   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-04 Accept trailing zeros for GBP
    Orders returns total token 1.2300, currency "GBP" and status "Created", with line tokens ["1.2300"]. The bodyless pay request preserves exactly 123 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 1.2300                               |
      | TotalCurrency | GBP                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 1.2300                                 |
      | CurrencyToken     | "GBP"                                  |
      | LineAmountTokens  | ["1.2300"]                             |
      | LineCurrencyToken | "GBP"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-04"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 123              |
      | JSON.currency     | "GBP"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 123                                    |
      | currency            | "GBP"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 123   |
      | Currency    | GBP   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-05 Convert a scientific CHF token exactly
    Orders returns total token 1.23e1, currency "CHF" and status "Created", with line tokens ["1.23e1"]. The bodyless pay request preserves exactly 1230 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 1.23e1                               |
      | TotalCurrency | CHF                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 1.23e1                                 |
      | CurrencyToken     | "CHF"                                  |
      | LineAmountTokens  | ["1.23e1"]                             |
      | LineCurrencyToken | "CHF"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-05"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1230             |
      | JSON.currency     | "CHF"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1230                                   |
      | currency            | "CHF"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 1230  |
      | Currency    | CHF   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-06 Accept the smallest JPY unit
    Orders returns total token 1, currency "JPY" and status "Created", with line tokens ["1"]. The bodyless pay request preserves exactly 1 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 1                                    |
      | TotalCurrency | JPY                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 1                                      |
      | CurrencyToken     | "JPY"                                  |
      | LineAmountTokens  | ["1"]                                  |
      | LineCurrencyToken | "JPY"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-06"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1                |
      | JSON.currency     | "JPY"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1                                      |
      | currency            | "JPY"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 1     |
      | Currency    | JPY   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-07 Keep zero-decimal KRW money exact
    Orders returns total token 500, currency "KRW" and status "Created", with line tokens ["500"]. The bodyless pay request preserves exactly 500 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 500                                  |
      | TotalCurrency | KRW                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 500                                    |
      | CurrencyToken     | "KRW"                                  |
      | LineAmountTokens  | ["500"]                                |
      | LineCurrencyToken | "KRW"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-07"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 500              |
      | JSON.currency     | "KRW"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 500                                    |
      | currency            | "KRW"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 500   |
      | Currency    | KRW   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-08 Accept the smallest BHD unit
    Orders returns total token 0.001, currency "BHD" and status "Created", with line tokens ["0.001"]. The bodyless pay request preserves exactly 1 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 0.001                                |
      | TotalCurrency | BHD                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 0.001                                  |
      | CurrencyToken     | "BHD"                                  |
      | LineAmountTokens  | ["0.001"]                              |
      | LineCurrencyToken | "BHD"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-08"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1                |
      | JSON.currency     | "BHD"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1                                      |
      | currency            | "BHD"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 1     |
      | Currency    | BHD   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-09 Convert JOD at three decimals
    Orders returns total token 1.234, currency "JOD" and status "Created", with line tokens ["1.234"]. The bodyless pay request preserves exactly 1234 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 1.234                                |
      | TotalCurrency | JOD                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 1.234                                  |
      | CurrencyToken     | "JOD"                                  |
      | LineAmountTokens  | ["1.234"]                              |
      | LineCurrencyToken | "JOD"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-09"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1234             |
      | JSON.currency     | "JOD"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1234                                   |
      | currency            | "JOD"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 1234  |
      | Currency    | JOD   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-10 Convert KWD at three decimals
    Orders returns total token 1.234, currency "KWD" and status "Created", with line tokens ["1.234"]. The bodyless pay request preserves exactly 1234 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 1.234                                |
      | TotalCurrency | KWD                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 1.234                                  |
      | CurrencyToken     | "KWD"                                  |
      | LineAmountTokens  | ["1.234"]                              |
      | LineCurrencyToken | "KWD"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-10"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1234             |
      | JSON.currency     | "KWD"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1234                                   |
      | currency            | "KWD"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 1234  |
      | Currency    | KWD   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-11 Convert OMR at three decimals
    Orders returns total token 1.234, currency "OMR" and status "Created", with line tokens ["1.234"]. The bodyless pay request preserves exactly 1234 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 1.234                                |
      | TotalCurrency | OMR                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 1.234                                  |
      | CurrencyToken     | "OMR"                                  |
      | LineAmountTokens  | ["1.234"]                              |
      | LineCurrencyToken | "OMR"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-11"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1234             |
      | JSON.currency     | "OMR"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1234                                   |
      | currency            | "OMR"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 1234  |
      | Currency    | OMR   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-12 Convert TND at three decimals
    Orders returns total token 1.234, currency "TND" and status "Created", with line tokens ["1.234"]. The bodyless pay request preserves exactly 1234 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 1.234                                |
      | TotalCurrency | TND                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 1.234                                  |
      | CurrencyToken     | "TND"                                  |
      | LineAmountTokens  | ["1.234"]                              |
      | LineCurrencyToken | "TND"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-12"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1234             |
      | JSON.currency     | "TND"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1234                                   |
      | currency            | "TND"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 1234  |
      | Currency    | TND   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-13 Store the exact BSON signed-int64 upper boundary
    Orders returns total token 92233720368547758.07, currency "PLN" and status "Created", with line tokens ["92233720368547758.07"]. The bodyless pay request preserves exactly 9223372036854775807 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 92233720368547758.07                 |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 92233720368547758.07                   |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["92233720368547758.07"]               |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-13"
      | Field             | Value               |
      | HTTPStatuses      | 201                 |
      | ContentType       | application/json    |
      | Code              | -                   |
      | JSON.status       | "created"           |
      | JSON.amount_minor | 9223372036854775807 |
      | JSON.currency     | "PLN"               |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 9223372036854775807                    |
      | currency            | "PLN"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value               |
      | AmountMinor | 9223372036854775807 |
      | Currency    | PLN                 |
      | OrdersReads | 0                   |
      | StripeCalls | 0                   |

  Scenario: PAY10-14 Preserve a USD integer beyond binary-float precision
    Orders returns total token 90071992547409.91, currency "USD" and status "Created", with line tokens ["90071992547409.91"]. The bodyless pay request preserves exactly 9007199254740991 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 90071992547409.91                    |
      | TotalCurrency | USD                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 90071992547409.91                      |
      | CurrencyToken     | "USD"                                  |
      | LineAmountTokens  | ["90071992547409.91"]                  |
      | LineCurrencyToken | "USD"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-14"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 9007199254740991 |
      | JSON.currency     | "USD"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 9007199254740991                       |
      | currency            | "USD"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value            |
      | AmountMinor | 9007199254740991 |
      | Currency    | USD              |
      | OrdersReads | 0                |
      | StripeCalls | 0                |

  Scenario: PAY10-15 Accept a case-insensitive Created order status
    Orders returns total token 12.99, currency "PLN" and status "cReAtEd", with line tokens ["12.99"]. The bodyless pay request preserves exactly 1299 minor units and every response field, then repeats without changing populated state or calling dependencies.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "cReAtEd"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-15"
      | Field             | Value            |
      | HTTPStatuses      | 201              |
      | ContentType       | application/json |
      | Code              | -                |
      | JSON.status       | "created"        |
      | JSON.amount_minor | 1299             |
      | JSON.currency     | "PLN"            |
    And the complete payment response is
      | Field               | Value                                  |
      | id                  | {stored.id}                            |
      | order_id            | "11111111-1111-4111-8111-111111111111" |
      | amount_minor        | 1299                                   |
      | currency            | "PLN"                                  |
      | status              | "created"                              |
      | provider_session_id | null                                   |
      | provider_payment_id | null                                   |
      | failure_code        | null                                   |
      | created_at          | {stored.created_at}                    |
      | updated_at          | null                                   |
    And only the requested payment is inserted
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 1299  |
      | Currency    | PLN   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-16 Reject a zero order total
    Orders returns total token 0, currency "PLN" and status "Created", with line tokens ["0"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 0                                      |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["0"]                                  |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-16"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-17 Reject a negative order total
    Orders returns total token -0.01, currency "PLN" and status "Created", with line tokens ["-0.01"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | -0.01                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["-0.01"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-17"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-18 Reject a fractional PLN minor unit
    Orders returns total token 0.001, currency "PLN" and status "Created", with line tokens ["0.001"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 0.001                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["0.001"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-18"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-19 Reject a fractional JPY unit
    Orders returns total token 0.1, currency "JPY" and status "Created", with line tokens ["0.1"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 0.1                                    |
      | CurrencyToken     | "JPY"                                  |
      | LineAmountTokens  | ["0.1"]                                |
      | LineCurrencyToken | "JPY"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-19"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-20 Reject a fourth decimal for KWD
    Orders returns total token 0.0001, currency "KWD" and status "Created", with line tokens ["0.0001"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 0.0001                                 |
      | CurrencyToken     | "KWD"                                  |
      | LineAmountTokens  | ["0.0001"]                             |
      | LineCurrencyToken | "KWD"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-20"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-21 Reject an unknown Orders currency
    Orders returns total token 12.99, currency "ZZZ" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "ZZZ"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "ZZZ"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-21"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-22 Reject lowercase Orders currency
    Orders returns total token 12.99, currency "pln" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "pln"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "pln"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-22"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-23 Reject padded Orders currency
    Orders returns total token 12.99, currency " PLN " and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | " PLN "                                |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | " PLN "                                |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-23"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-24 Reject non-ASCII Orders currency
    Orders returns total token 12.99, currency "PŁN" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "PŁN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PŁN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-24"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-25 Reject a short Orders currency
    Orders returns total token 12.99, currency "PL" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "PL"                                   |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PL"                                   |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-25"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-26 Reject a long Orders currency
    Orders returns total token 12.99, currency "PLNN" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "PLNN"                                 |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLNN"                                 |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-26"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-27 Reject an empty Orders currency
    Orders returns total token 12.99, currency "" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | ""                                     |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | ""                                     |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-27"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-28 Reject a string Orders total
    Orders returns total token "12.99", currency "PLN" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | "12.99"                                |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-28"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-29 Reject a null Orders total
    Orders returns total token null, currency "PLN" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | null                                   |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-29"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-30 Reject a true Orders total
    Orders returns total token true, currency "PLN" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | true                                   |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-30"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-31 Reject a false Orders total
    Orders returns total token false, currency "PLN" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | false                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-31"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-32 Reject a nonfinite NaN token
    Orders returns total token NaN, currency "PLN" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | NaN                                    |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-32"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-33 Reject a nonfinite Infinity token
    Orders returns total token Infinity, currency "PLN" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | Infinity                               |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-33"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-34 Reject an amount beyond the conversion exponent bound
    Orders returns total token 1e29, currency "PLN" and status "Created", with line tokens ["1e29"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 1e29                                   |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["1e29"]                               |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-34"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-35 Reject a mismatch in the exact line sum
    Orders returns total token 12.99, currency "PLN" and status "Created", with line tokens ["12.98"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.98"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-35"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-36 Reject an empty collection of order lines
    Orders returns total token 12.99, currency "PLN" and status "Created", with line tokens []. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | []                                     |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-36"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-37 Reject an absent Orders total
    Orders returns total token <absent>, currency "PLN" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | <absent>                               |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-37"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-38 Reject a numeric Orders currency
    Orders returns total token 12.99, currency 123 and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | 123                                    |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-38"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-39 Reject a null Orders currency
    Orders returns total token 12.99, currency null and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | null                                   |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-39"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-40 Reject a boolean Orders currency
    Orders returns total token 12.99, currency true and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | true                                   |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-40"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-41 Reject an absent Orders currency
    Orders returns total token 12.99, currency <absent> and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | <absent>                               |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-41"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-42 Reject an inconsistent product currency
    Orders returns total token 12.99, currency "PLN" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "USD"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-42"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-43 Reject an empty order status
    Orders returns total token 12.99, currency "PLN" and status "", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | ""                                     |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-43"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-44 Reject a whitespace-only order status
    Orders returns total token 12.99, currency "PLN" and status "   ", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "   "                                  |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-44"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-45 Reject a response for a different order
    Orders returns total token 12.99, currency "PLN" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "88888888-8888-4888-8888-888888888888" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-45"
      | Field                  | Value                                                |
      | HTTPStatuses           | 502                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_invalid_response                               |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Gateway"                                        |
      | JSON.status            | 502                                                  |
      | JSON.detail            | "Orders service returned an invalid response."       |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-46 Reject a Paid order without creating payment
    Orders returns total token 12.99, currency "PLN" and status "Paid", with line tokens ["12.99"]. The bodyless pay request returns 409/order_not_payable twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Paid"                                 |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-46"
      | Field                  | Value                                                |
      | HTTPStatuses           | 409                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_not_payable                                    |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Conflict"                                           |
      | JSON.status            | 409                                                  |
      | JSON.detail            | "Order cannot be paid in its current state."         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-47 Reject a Canceled order without creating payment
    Orders returns total token 12.99, currency "PLN" and status "Canceled", with line tokens ["12.99"]. The bodyless pay request returns 409/order_not_payable twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Canceled"                             |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-47"
      | Field                  | Value                                                |
      | HTTPStatuses           | 409                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | order_not_payable                                    |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Conflict"                                           |
      | JSON.status            | 409                                                  |
      | JSON.detail            | "Order cannot be paid in its current state."         |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-48 Reject a zero UUID through the real Pay route
    Orders returns total token 12.99, currency "PLN" and status "Created", with line tokens ["12.99"]. The bodyless pay request returns 400/validation_failed twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 00000000-0000-0000-0000-000000000000 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 12.99                                |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "00000000-0000-0000-0000-000000000000" |
    And I remember complete business validation state
    When I pay the order
    Then the response matches case "PAY10-48"
      | Field                  | Value                                                |
      | HTTPStatuses           | 400                                                  |
      | ContentType            | application/problem+json                             |
      | Code                   | validation_failed                                    |
      | JSON.type              | "about:blank"                                        |
      | JSON.title             | "Bad Request"                                        |
      | JSON.status            | 400                                                  |
      | JSON.detail            | "One or more validation errors occurred."            |
      | JSON.instance          | "/payments/00000000-0000-0000-0000-000000000000/pay" |
      | JSON.errors            | []                                                   |
      | JSON.missingProperties | []                                                   |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-49 Reject zero at checkout before preparing payment
    Orders returns total token 0, currency "PLN" and status "Created", with line tokens ["0"]. The bodyless checkout request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 0                                      |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["0"]                                  |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I create checkout for the order
    Then the response matches case "PAY10-49"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 502                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | order_invalid_response                                    |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Gateway"                                             |
      | JSON.status            | 502                                                       |
      | JSON.detail            | "Orders service returned an invalid response."            |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-50 Reject a fractional minor unit at checkout
    Orders returns total token 1.999, currency "PLN" and status "Created", with line tokens ["1.999"]. The bodyless checkout request returns 502/order_invalid_response twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 1.999                                  |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["1.999"]                              |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I create checkout for the order
    Then the response matches case "PAY10-50"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 502                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | order_invalid_response                                    |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Bad Gateway"                                             |
      | JSON.status            | 502                                                       |
      | JSON.detail            | "Orders service returned an invalid response."            |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-51 Reject valid EUR only at the checkout provider policy
    Orders returns total token 12.99, currency "EUR" and status "Created", with line tokens ["12.99"]. The bodyless checkout request returns 409/checkout_money_unsupported twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 12.99                                  |
      | CurrencyToken     | "EUR"                                  |
      | LineAmountTokens  | ["12.99"]                              |
      | LineCurrencyToken | "EUR"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I create checkout for the order
    Then the response matches case "PAY10-51"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 409                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_money_unsupported                                |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Conflict"                                                |
      | JSON.status            | 409                                                       |
      | JSON.detail            | "Checkout amount or currency is not supported."           |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-52 Reject valid JPY only at the checkout provider policy
    Orders returns total token 500, currency "JPY" and status "Created", with line tokens ["500"]. The bodyless checkout request returns 409/checkout_money_unsupported twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 500                                    |
      | CurrencyToken     | "JPY"                                  |
      | LineAmountTokens  | ["500"]                                |
      | LineCurrencyToken | "JPY"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I create checkout for the order
    Then the response matches case "PAY10-52"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 409                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_money_unsupported                                |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Conflict"                                                |
      | JSON.status            | 409                                                       |
      | JSON.detail            | "Checkout amount or currency is not supported."           |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-53 Reject one PLN minor unit below the checkout minimum
    Orders returns total token 1.99, currency "PLN" and status "Created", with line tokens ["1.99"]. The bodyless checkout request returns 409/checkout_money_unsupported twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 1.99                                   |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["1.99"]                               |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I create checkout for the order
    Then the response matches case "PAY10-53"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 409                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_money_unsupported                                |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Conflict"                                                |
      | JSON.status            | 409                                                       |
      | JSON.detail            | "Checkout amount or currency is not supported."           |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |

  Scenario: PAY10-54 Accept the inclusive PLN checkout minimum
    Orders returns total token 2.00, currency "PLN" and status "Created", with line tokens ["2.00"]. The bodyless checkout request preserves exactly 200 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 2.00                                 |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 2.00                                   |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["2.00"]                               |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    And I remember checkout state and provider calls
    When I create checkout for the order
    Then the response matches case "PAY10-54"
      | Field                     | Value            |
      | HTTPStatuses              | 200              |
      | ContentType               | application/json |
      | Code                      | -                |
      | JSON.payment.status       | "pending"        |
      | JSON.payment.amount_minor | 200              |
      | JSON.payment.currency     | "PLN"            |
    And the complete checkout response is
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 200                                    |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}           |
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
      | form.line_items[0][price_data][unit_amount]        | 200                                           |
      | form.line_items[0][price_data][product_data][name] | Order {order.id}                              |
    And the accepted business boundary remains stable
      | Field       | Value |
      | AmountMinor | 200   |
      | Currency    | PLN   |
      | OrdersReads | 0     |
      | StripeCalls | 0     |

  Scenario: PAY10-55 Accept the inclusive PLN checkout maximum
    Orders returns total token 999999.99, currency "PLN" and status "Created", with line tokens ["999999.99"]. The bodyless checkout request preserves exactly 99999999 minor units and every response field, then repeats without changing populated state or calling dependencies.
    Given the order fixture contains
      | Field         | Value                                |
      | OrderId       | 11111111-1111-4111-8111-111111111111 |
      | ClientId      | 22222222-2222-4222-8222-222222222222 |
      | TotalAmount   | 999999.99                            |
      | TotalCurrency | PLN                                  |
    And an unrelated succeeded payment fills all collections
      | Field         | Value                                |
      | OrderId       | 66666666-6666-4666-8666-666666666666 |
      | ClientId      | 77777777-7777-4777-8777-777777777777 |
      | TotalAmount   | 31.73                                |
      | TotalCurrency | PLN                                  |
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 999999.99                              |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["999999.99"]                          |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    And I remember checkout state and provider calls
    When I create checkout for the order
    Then the response matches case "PAY10-55"
      | Field                     | Value            |
      | HTTPStatuses              | 200              |
      | ContentType               | application/json |
      | Code                      | -                |
      | JSON.payment.status       | "pending"        |
      | JSON.payment.amount_minor | 99999999         |
      | JSON.payment.currency     | "PLN"            |
    And the complete checkout response is
      | Field                       | Value                                  |
      | payment.id                  | {stored.id}                            |
      | payment.order_id            | "11111111-1111-4111-8111-111111111111" |
      | payment.amount_minor        | 99999999                               |
      | payment.currency            | "PLN"                                  |
      | payment.status              | "pending"                              |
      | payment.provider_session_id | {stored.provider_session_id}           |
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
      | form.line_items[0][price_data][unit_amount]        | 99999999                                      |
      | form.line_items[0][price_data][product_data][name] | Order {order.id}                              |
    And the accepted business boundary remains stable
      | Field       | Value    |
      | AmountMinor | 99999999 |
      | Currency    | PLN      |
      | OrdersReads | 0        |
      | StripeCalls | 0        |

  Scenario: PAY10-56 Reject one PLN minor unit above the checkout maximum
    Orders returns total token 1000000.00, currency "PLN" and status "Created", with line tokens ["1000000.00"]. The bodyless checkout request returns 409/checkout_money_unsupported twice with complete safe problems, no Stripe work and no changes to populated current, history or receipt collections.
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
    And Orders exposes this business contract
      | Field             | Value                                  |
      | TotalAmountToken  | 1000000.00                             |
      | CurrencyToken     | "PLN"                                  |
      | LineAmountTokens  | ["1000000.00"]                         |
      | LineCurrencyToken | "PLN"                                  |
      | StatusToken       | "Created"                              |
      | OrderIdToken      | "11111111-1111-4111-8111-111111111111" |
    And I remember complete business validation state
    When I create checkout for the order
    Then the response matches case "PAY10-56"
      | Field                  | Value                                                     |
      | HTTPStatuses           | 409                                                       |
      | ContentType            | application/problem+json                                  |
      | Code                   | checkout_money_unsupported                                |
      | JSON.type              | "about:blank"                                             |
      | JSON.title             | "Conflict"                                                |
      | JSON.status            | 409                                                       |
      | JSON.detail            | "Checkout amount or currency is not supported."           |
      | JSON.instance          | "/payments/11111111-1111-4111-8111-111111111111/checkout" |
      | JSON.errors            | []                                                        |
      | JSON.missingProperties | []                                                        |
    And business rejection preserves populated state on both requests
      | Field         | Value     |
      | OrdersReads   | 1         |
      | StripeCalls   | 0         |
      | TargetPayment | absent    |
      | Collections   | unchanged |
      | Repeat        | true      |
