# IMC Prosperity workbench

TradeTell has three jobs: inspect a recorded market, replay a built-in strategy, and ask a question with inspectable sources. The market desk opens first. A product price trace, backed by the tracked Round 2 fixture, is the page's main visual. Controls change the trace and the order-book snapshot together, so the drawing helps someone investigate actual data.

## What stays

- Streamlit, the dark navy and emerald identity, the candlestick logo, chat history, and source disclosure remain.
- The RAG implementation and its in-memory index stay as they are. It starts when someone asks a question, so the other tools remain available without a model warm-up.
- The existing strategy replay supplies fill and position logic. The UI calls it on small, tracked samples from Round 1 and Round 2 day 0.

## How the page works

- The sidebar names three destinations: Market desk, Replay lab, and Ask TradeTell. Each view has one clear task and its own controls.
- Market desk uses `src/algorithms/round_2/test_data/CSV/prices_round_2.csv`. Choose a product and time window to inspect its mid price. Pick a timestamp to see the recorded bid and ask levels and recent public trades. Label this as a historical Round 2 fixture; it is not a live feed.
- Replay lab runs the built-in Round 1 or Round 2 Trader against the first 800 ticks of day 0 from a matching, tracked sample. Choose how resting orders match public trades, then run the replay. Show P&L, drawdown, fills, product results, and the simulator's limits. Do not compare these results to the separate Market desk fixture.
- Ask TradeTell keeps the four starting questions in the main reading path. Answers stay narrow and show source title, corpus, filename, and raw retrieved context.

## Visual choices

- The market trace is the signature element. Give it most of the horizontal space. Keep the controls and order book close enough that changing a timestamp feels connected to the plot.
- Use a compact 36–40 px page title, 19–22 px view headings, 16 px reading text, and 13–14 px provenance. Let the chart and answer text carry the hierarchy.
- Keep the dark palette from `.streamlit/config.toml` and `assets/banner-dark.svg`. Use emerald for the trace and primary action. Use muted gray for source and sample labels. Avoid borders around every block and decorative status marks.
- On narrow screens, stack controls, chart, and snapshot in that order. Use native Streamlit inputs, visible keyboard focus, and no decorative animation.

## References and review

The live app, `assets/banner-dark.svg`, and `assets/diagrams/rag-flow.png` define the starting identity and the sourced-answer flow. An Awwwards search for data interfaces did not yield a suitable interaction reference, so no external page structure was adopted. Review the rendered market, replay, and research views at desktop and mobile widths; verify controls, answer sources, and the sample labels before calling the redesign finished.
