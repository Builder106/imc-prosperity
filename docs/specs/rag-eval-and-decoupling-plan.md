# TradeTell evaluation plan

The next release measures whether TradeTell retrieves useful sources and
whether its built-in strategies perform on recorded market data. The app keeps
its current Streamlit interface and in-memory vector store while those checks
take shape.

## Strategy replay

Run the built-in Round 1 or Round 2 trader against the matching historical CSVs
under `data/competition_rounds/`:

```bash
uv run python -m src.evaluation.strategy_replay --round 1 --match-trades worse
uv run python -m src.evaluation.strategy_replay --round 2 --day 0
```

The replay reports daily P&L, maximum drawdown, fills, traded volume, maximum
inventory, and order-limit rejections. Each day starts with a fresh trader and
empty inventory. The strategy receives the current order book and the previous
tick's trades; current public trades are used for fills and become visible on
the next tick.

The default `worse` mode fills a resting order only when a public trade passes
its quote. `all` also fills at the quoted price, and `none` ignores public
trades. Orders that cross the visible book fill at the displayed price. The
CSV data does not record queue priority, so the replay cannot model it. It also
skips conversions and the Round 2 market-access bid.

This is a deterministic comparison tool for the strategies and data bundled in
the repo. It is not a full competition simulator.

## Retrieval benchmark

Run the ten-question benchmark against the same corpus, embeddings, vector
stores, and ensemble retriever used by the app:

```bash
uv run python -m src.rag.retrieval_evaluation --k 5
```

The command reports source recall at k and mean reciprocal rank. It does not
call Groq or score generated answers. It uses the configured Hugging Face
embedding model and builds the index in memory, so the first run may need to
download the model. The benchmark stays outside CI because it requires the
embedding model and builds the full corpus at startup.

## Follow-up work

Before adding a Streamlit comparison view, use the replay to compare strategies
on held-out days and rounds. Add tests for the replay's CSV parsing, fill rules,
and position-limit checks before making its results a CI gate. Consider
persistent indexing or a separate API only if measured startup or deployment
needs justify the added machinery.
