Feature: Warmup

  # Throwaway scenarios that absorb Playwright's 0-byte-first-video bug in
  # single-worker slowMo runs. Their videos are discarded — never use them
  # as a demo source. Two is the floor; one is sometimes not enough.

  Scenario: Warmup A
    Given I open the trading assistant
    Then I see the "IMC Prosperity Trading Assistant" title

  Scenario: Warmup B
    Given I open the trading assistant
    Then I see the "IMC Prosperity Trading Assistant" title
