# IMC Prosperity roadmap

TradeTell helps competitors study the rules, inspect historical data, and build
trading strategies. The next release adds a repeatable way to measure both
retrieval quality and strategy outcomes.

## v1.1: Strategy evaluation loop

- Replay the built-in Round 1 and Round 2 strategies against the bundled
  historical order books and public trades.
- Report P&L, drawdown, fills, traded volume, and order-limit rejections for
  each day.
- Measure source recall at k and mean reciprocal rank using the same local
  retriever and corpus as the app.
- Keep the replay assumptions visible. The historical data does not include
  queue priority, conversions, or Round 2 market-access bidding. The retrieval
  benchmark does not call the LLM.

## v1.2: Strategy comparison

- Compare candidate strategies on held-out days and rounds.
- Show the retrieved sources and replay results beside each strategy answer.
- Add a Streamlit comparison view if the command-line results prove useful.

## Out of Scope

- Real-money exchange execution
- Unseeded or non-repeatable simulation results

---
For the implementation plan, see [`docs/specs/`](docs/specs/).
