Feature: Preserve localized card observations without monetary data
  Scenario: Read normalized rules and the real set name
    Given a collected French Pokemon card with rules and illustrator
    When I open its catalog detail
    Then I read its localized set name, HP, attack cost and illustrator
    And the original source payload is still available
    And monetary values are excluded but gameplay costs remain

  Scenario: Navigate a block containing localized extensions
    Given a collected French Pokemon card with rules and illustrator
    When I browse the Base block
    Then I find the card through its extension and localized block
