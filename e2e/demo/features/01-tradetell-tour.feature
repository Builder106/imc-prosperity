Feature: TradeTell tour

  # One continuous narrative: a competitor opens the assistant, asks a
  # grounded question through the chat input, watches the RAG answer arrive,
  # and inspects the retrieved source documents.

  Scenario: A competitor asks the assistant about position limits
    Given I open the trading assistant
    Then I see the "IMC Prosperity Trading Assistant" title
    And I see example prompts in the sidebar
    When I ask "What are the position limits for each product?"
    Then the assistant answers with sources
    When I open the retrieved sources
    Then I see the retrieved source documents
