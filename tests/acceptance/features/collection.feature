Feature: Request a collection from the administration
  Scenario: Queue a complete extension instead of a number of cards
    Given an administrator viewing the local catalog
    When I request the complete TCGdex extension swsh12.5 in French and English
    Then the queued collection preserves the extension without a card limit

  Scenario: Repair images throughout the existing catalog
    Given an administrator viewing the local catalog
    When I request a repair of missing images
    Then an image repair appears in the persistent history

  Scenario: Queue a small collection
    Given an administrator viewing the local catalog
    When I request a TCGdex collection in French with a limit of two
    Then a queued collection appears in the persistent history

  Scenario: Queue a collection in all TCGdex languages
    Given an administrator viewing the local catalog
    Then all eighteen TCGdex languages are available
    When I request a TCGdex collection in all eighteen languages
    Then the queued collection preserves all eighteen language codes
