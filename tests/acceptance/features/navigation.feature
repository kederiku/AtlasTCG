Feature: Browse one card across its collected languages
  Scenario: Find an extension by its Spanish name while browsing French cards
    Given an extension and a card collected in French and Spanish
    When I find Spanish extension names with French cards
    Then I see one French card with links to both collected languages

  Scenario: Display a Spanish printing in a French interface
    Given an extension and a card collected in French and Spanish
    When I browse the Spanish cards with a French interface
    Then the representative card is Spanish and its other language remains available
