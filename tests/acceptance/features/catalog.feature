Feature: Browse the collected catalog
  Scenario: Find a localized card and its image
    Given a catalog containing a French card and an English card
    When I search for French cards named Dracaufeu
    Then I see only the French card with its local image
