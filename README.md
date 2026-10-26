<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/banner-light.svg">
    <img alt="TradeTell IMC Prosperity workbench banner" src="assets/banner-dark.svg" width="100%">
  </picture>
</p>

[![CI](https://github.com/Builder106/imc-prosperity/actions/workflows/ci.yml/badge.svg)](https://github.com/Builder106/imc-prosperity/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](#license)
[![Live demo](https://img.shields.io/badge/demo-live-success.svg)](https://tradetell.streamlit.app)
[![Built with Streamlit](https://img.shields.io/badge/built%20with-Streamlit-FF4B4B.svg)](https://streamlit.io)

> **A workbench for the IMC Prosperity 4 market.** Read four recorded days tick by tick, replay a built-in Trader through any of them, and ask the competition wiki with sources.

## What is TradeTell?

TradeTell is a study tool for IMC Prosperity 4, IMC's online algorithmic trading challenge. It draws the recorded Prosperity 4 market on Intara as one section. Both goods opened at 10,000 XIRECs: Ash-Coated Osmium stayed there, and Intarian Pepper Root climbed about 1,000 a day to 14,000. Move the probe along the section to open the order book at any tick. Switch on the Trader layer to replay a built-in Round 1 or Round 2 Trader through a full day and see its fills and P&L on the same ticks. Open the field notes to ask the competition wiki, market data and code examples, with the passages behind each answer.

The ground and Trader layers work without an API key. The assistant needs a Groq API key and builds its search index when you first ask a question.

**Live app:** [tradetell.streamlit.app](https://tradetell.streamlit.app)

## Technical overview

The section is a Streamlit v2 component: HTML, CSS and JavaScript mounted in the page DOM. It draws four full days (40,000 ticks per good) on a canvas. The browser fetches the gzipped day files from Streamlit's static folder and decompresses them itself, and Python replays the Traders from the same files. The field notes search the local wiki, market, and code corpora to:

- Answer questions about IMC Prosperity rules, mechanics, and market concepts
- Draft Trader classes for review and testing
- Show the retrieved material behind each answer

## Features

- **Ground**: four recorded days as one price section; zoom into a day to split the goods onto their own scales and read three levels of book, the spread and public trades at any tick
- **Your Trader**: replay the built-in Round 1 or Round 2 Trader through a full recorded day with one of three public-trade matching rules; fills, position, P&L, drawdown and rejections sit on the same ticks
- **Field notes**: conversational research with chat history, retrieved source passages, and example questions
- **Index**: every day and layer as plain links and tables, with per-day open, close and range
- **Multi-source search**: Searches across three in-process knowledge stores (rules wiki, historical trading data, and code examples)
- **Groq inference**: Uses `llama-3.3-70b-versatile` by default when answering questions
- **Trading log analyzer**: A separate command summarizes competition logs

## How it works

Everything except the call to Groq runs inside the Streamlit process.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/diagrams/rag-flow-dark.png">
  <img src="assets/diagrams/rag-flow.png" alt="Inside the Streamlit process, the app asks GroqRagChain, which queries a combined retriever that searches local vector stores for the wiki, trading data, and code. The chain sends one prompt to the Groq API outside the process and returns the answer to the app." width="720">
</picture>

Streamlit passes the question to GroqRagChain. Its combined retriever searches the local wiki, trading, and code stores and fuses the three rankings. The chain trims that context to fit Groq's token limit and sends one prompt, and Streamlit shows the answer with its source documents. [Editable HTML source](assets/diagrams/rag-flow.html).

The vector stores are built in memory when the first question is asked. Streamlit
caches the assembled retriever, but the first question still processes and embeds
the corpus.

## Project structure

- **`app.py`**: Streamlit entry point; reads the layer and probe from the URL and mounts the section
- **`src/ui/`**: the section component (`ground/`), its Python wrapper, and data and URL helpers
- **`static/intara/`**: the four recorded days, gzipped, served to the browser and read by the replay
- **`src/`**: source code
  - **`rag/`**: RAG system
    - **`build_rag_system.py`**: document processing, vector stores, retriever, chain
    - **`groq_llm.py`**: `GroqRagChain` (Groq-backed, swappable backend)
    - **`model_config.py`**: env-driven model/embedding configuration
    - **`process_raw_trading_data.py`**: trading-data processing
  - **`algorithms/`**: round-by-round trading algorithms
  - **`utils/`**: Notion scraper and trading-log tools
- **`data/`**: `prosperity_wiki/` (Markdown) and `trading_data/`
- **`tests/`**: pytest suite (offline; network mocked)

## Getting started

### Prerequisites

- Python 3.11+
- Installed dependencies (`uv sync --group dev`)
- A Groq API key for Ask TradeTell ([console.groq.com/keys](https://console.groq.com/keys))

### Installation

```bash
git clone https://github.com/Builder106/imc-prosperity.git
cd imc-prosperity
uv sync --group dev
```

To use Ask TradeTell, create a `.env` in the project root with your Groq API key:

```bash
GROQ_API_KEY=your_groq_api_key_here
```

Optional overrides (defaults shown):

```bash
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.2
GROQ_TIMEOUT_SECONDS=180
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

When deploying on Streamlit Community Cloud, add the same keys under
**Manage app → Settings → Secrets** instead of a `.env` file.

### Running

```bash
streamlit run app.py
```

## Usage

1. On **Ground**, drag the probe or use the arrow keys (Shift for ten ticks, Page Up and Page Down for a hundred). Pick a day under the section to zoom in. The URL keeps the day and tick, so a link opens the same place.
2. Choose **Your Trader** in the legend, then a Trader, a day and a matching rule. The replay reruns on each change. Read the fill rules under the results before interpreting its P&L.
3. Choose **Field notes** to ask about rules or strategies. Expand **Sources** under an answer to read the retrieved passages.

### Working with trading logs

```bash
python src/utils/summarize_trading_logs.py
```

Follow the prompts to input a log file path and receive a detailed summary.

### Evaluating strategies

Replay a built-in strategy on a local historical archive:

```bash
uv run python -m src.evaluation.strategy_replay --round 1 --match-trades worse
```

Use `--round 2` or pass `--day -1` to select one day. The report includes
daily P&L, drawdown, fills, inventory, and rejected orders. Queue priority,
conversions, and Round 2 market-access bidding are not modeled. See the
[evaluation plan](docs/specs/rag-eval-and-decoupling-plan.md) for the fill rules.
Rows with no quotes carry forward the last valid mid price for inventory
valuation. The Streamlit app replays the full days in `static/intara/`; the CLI
reads the local competition archive when it is available.

Measure retrieval against the app's local corpus and embedding model:

```bash
uv run python -m src.rag.retrieval_evaluation --k 5
```

This reports source recall at k and mean reciprocal rank without calling the
Groq API. The first run may download the configured Hugging Face model.
Add `--compare-corpora` to score the wiki, trading, and code stores separately
from the combined retriever.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, test commands, and project
guardrails. Run the suite with:

```bash
pytest
```

The deterministic unit coverage gate is:

```bash
uv run pytest --cov-report=term-missing
```

## Acknowledgments

- IMC Prosperity for the trading competition
- LangChain for the RAG framework
- Groq for fast LLM inference
- Streamlit for the web interface

## License

Released under the [MIT License](LICENSE).
