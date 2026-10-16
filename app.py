import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from src.evaluation.strategy_replay import load_trader, run_day
from src.rag.build_rag_system import (
    create_combined_retriever,
    create_rag_chain,
    create_vector_stores,
    process_discord_data,
    process_notion_wiki_data,
    process_trading_data,
)

load_dotenv()

# Page configuration
# Custom browser-tab favicon: the candlestick logo (assets/logo.png). Resolved
# relative to this file so it works regardless of the working directory the app
# is launched from (Streamlit Cloud runs from the repo root). Streamlit's
# page_icon expects a raster path/emoji — it doesn't render SVG favicons — so we
# point at the PNG, not logo.svg. Falls back to the chart emoji if the file is
# missing.
_FAVICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")
st.set_page_config(
    page_title="TradeTell | IMC Prosperity Workbench",
    page_icon=_FAVICON if os.path.exists(_FAVICON) else "📈",
    layout="wide",
    initial_sidebar_state="auto",
)

# Styling
st.markdown(
    """
    <style>
      .block-container { max-width: 1120px; padding-top: 3rem; padding-bottom: 6rem; }
      section[data-testid="stSidebar"] { background: #122025; }
      section[data-testid="stSidebar"] .block-container { padding-top: 2rem; }
      .app-title { color: #ECF4F0; font-size: clamp(2rem, 3vw, 2.5rem); line-height: 1.12;
        font-weight: 750; letter-spacing: -0.045em; margin: 0 0 0.75rem; }
      .app-subtitle { color: #B1C3BF; font-size: 1.05rem; line-height: 1.5;
        max-width: 680px; margin: 0 0 2.5rem; }
      .stButton > button { width: 100%; min-height: 44px; text-align: left;
        justify-content: flex-start; white-space: normal; line-height: 1.4;
        color: #ECF4F0; background: transparent; border: 0; padding: 0.5rem 0.25rem; }
      .stButton > button:hover { color: #8FE9BD; background: transparent; border-color: transparent; }
      .stButton > button:focus-visible { outline: 3px solid #8FE9BD; outline-offset: 2px; }
      .stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {
        background: #65D6A3; color: #091216; border-radius: 10px; padding: 0.65rem 1rem;
      }
      .stButton > button[kind="primary"]:hover,
      .stButton > button[data-testid="stBaseButton-primary"]:hover {
        background: #8FE9BD; color: #091216;
      }
      [data-testid="stChatMessage"] { background: #122025; border-radius: 14px; padding: 1rem; }
      @media (max-width: 768px) {
        .block-container { padding-top: 1.5rem; }
        .app-subtitle { margin-bottom: 1.75rem; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

PROJECT_ROOT = Path(__file__).resolve().parent
MARKET_PRICES = PROJECT_ROOT / "src/algorithms/round_2/test_data/CSV/prices_round_2.csv"
MARKET_TRADES = PROJECT_ROOT / "src/algorithms/round_2/test_data/CSV/trades_round_2.csv"
REPLAY_SAMPLES = PROJECT_ROOT / "data/samples"

EXAMPLE_PROMPTS = [
    ("Rules", "What products and position limits are introduced in Round 1?"),
    ("Code", "Write a market-making Trader class for RAINFOREST_RESIN."),
    ("Strategy", "Explain a basket-arbitrage strategy for the PICNIC_BASKET products."),
    ("Risk", "How should I manage risk against position limits in my algorithm?"),
]


@st.cache_data
def load_market_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the tracked Round 2 market fixture for exploration."""
    return pd.read_csv(MARKET_PRICES, sep=";"), pd.read_csv(MARKET_TRADES, sep=";")


@st.cache_data(show_spinner=False)
def replay_sample(round_num: int, match_trades: str) -> dict[str, object]:
    """Replay a built-in strategy on the matching 800-tick day sample."""
    sample_dir = REPLAY_SAMPLES / f"replay_round_{round_num}"
    trader, limits = load_trader(round_num)
    return run_day(
        round_num,
        sample_dir / f"prices_round_{round_num}_day_0.csv",
        sample_dir / f"trades_round_{round_num}_day_0.csv",
        trader,
        limits,
        match_trades,
    )


# RAG system (built once, cached for the session)
@st.cache_resource(show_spinner="Loading knowledge base and building the RAG system…")
def initialize_rag_system():
    if os.environ.get("TRADETELL_TEST_MODE") == "1":
        return _fake_rag_chain()
    notion_documents = process_notion_wiki_data()
    notion_documents.extend(process_discord_data())
    trading_documents = process_trading_data()
    notion_vectorstore, trading_vectorstore, code_vectorstore = create_vector_stores(
        notion_documents, trading_documents
    )
    retriever = create_combined_retriever(notion_vectorstore, trading_vectorstore, code_vectorstore)
    return create_rag_chain(retriever)


class _FakeRagChain:
    def invoke(self, inputs):
        query = inputs["query"]
        return {
            "result": f"Fixture answer for: {query}",
            "source_documents": [
                type(
                    "FixtureDocument",
                    (),
                    {
                        "metadata": {"source": "fixture/round-1.md"},
                        "page_content": "Fixture source content for deterministic smoke tests.",
                    },
                )()
            ],
        }


def _fake_rag_chain():
    return _FakeRagChain()


def render_sources(source_documents):
    """Render retrieved context inside a collapsed expander."""
    if not source_documents:
        return
    label = f"Sources ({len(source_documents)})"
    with st.expander(label):
        for i, doc in enumerate(source_documents, start=1):
            metadata = doc.metadata
            source = os.path.basename(str(metadata.get("source", "Unknown")))
            title = metadata.get("title") or source
            if metadata.get("content_type") == "code_block":
                corpus = "Code example"
            elif metadata.get("type") == "trading_data":
                corpus = "Market archive"
            elif metadata.get("type") == "notion_wiki":
                corpus = "Competition wiki"
            else:
                corpus = "Source"
            st.markdown(f"**{i}. {title}**")
            st.caption(f"{corpus} | {source}")
            st.code(doc.page_content, language="text")


# Sidebar
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.image(_FAVICON, width=46)
    st.markdown("## TradeTell")
    st.caption("IMC Prosperity market research")
    workspace = st.radio("Workspace", ("Market desk", "Replay lab", "Ask TradeTell"))
    st.divider()
    st.caption("Recorded competition data and sourced research. No live market feed.")
    if st.session_state.messages and st.button("Clear conversation", key="clear"):
        st.session_state.messages = []
        st.rerun()


# The three tools share the same page shell but load their data only when used.
def render_market_desk() -> None:
    st.subheader("Explore the market archive")
    st.caption("Round 2, day 1. Tracked historical fixture.")
    prices, trades = load_market_data()
    products = sorted(prices["product"].unique())
    product_column, window_column = st.columns([1, 2], gap="large")
    with product_column:
        product = st.selectbox("Product", products, index=products.index("PICNIC_BASKET1"))
    product_prices = prices.loc[prices["product"] == product].sort_values("timestamp")
    start = int(product_prices["timestamp"].min())
    end = int(product_prices["timestamp"].max())
    with window_column:
        window = st.slider("Time window", start, end, (start, end), step=100)
    visible = product_prices.loc[product_prices["timestamp"].between(*window)]
    chart_sample = visible.iloc[:: max(1, len(visible) // 250)]
    chart = (
        alt.Chart(chart_sample)
        .mark_line(color="#65D6A3", strokeWidth=2)
        .encode(
            x=alt.X("timestamp:Q", title="Timestamp"),
            y=alt.Y("mid_price:Q", title="Mid price (seashells)", scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("timestamp:Q", title="Timestamp", format=","),
                alt.Tooltip("mid_price:Q", title="Mid price", format=",.1f"),
            ],
        )
        .properties(height=310)
    )
    st.altair_chart(chart, width="stretch")
    st.caption("Mid price in seashells. Recorded data, not a live price.")

    timestamp = st.slider(
        "Inspect timestamp",
        int(visible["timestamp"].min()),
        int(visible["timestamp"].max()),
        int(visible["timestamp"].iloc[len(visible) // 2]),
        step=100,
    )
    snapshot = product_prices.loc[product_prices["timestamp"] == timestamp].iloc[0]
    spread = snapshot["ask_price_1"] - snapshot["bid_price_1"]
    product_trades = trades.loc[(trades["symbol"] == product) & (trades["timestamp"] <= timestamp)]
    mid_metric, spread_metric, trades_metric = st.columns(3)
    mid_metric.metric("Mid price", f"{snapshot['mid_price']:,.1f}")
    spread_metric.metric("Best spread", f"{spread:,.0f}" if pd.notna(spread) else "No quote")
    trades_metric.metric("Public trades to here", f"{len(product_trades):,}")

    book_column, tape_column = st.columns([1, 1], gap="large")
    with book_column:
        st.markdown(f"### Order book at {timestamp:,}")
        book = pd.DataFrame(
            [
                {
                    "Level": level,
                    "Bid price": snapshot[f"bid_price_{level}"],
                    "Bid size": snapshot[f"bid_volume_{level}"],
                    "Ask price": snapshot[f"ask_price_{level}"],
                    "Ask size": snapshot[f"ask_volume_{level}"],
                }
                for level in range(1, 4)
            ]
        )
        st.dataframe(book, hide_index=True, width="stretch")
    with tape_column:
        st.markdown("### Recent public trades")
        if product_trades.empty:
            st.info("No public trades for this product before this timestamp.")
        else:
            st.dataframe(
                product_trades[["timestamp", "price", "quantity"]].tail(8).iloc[::-1],
                hide_index=True,
                width="stretch",
            )
    st.caption("The market fixture is separate from the replay samples below.")


def render_replay_lab() -> None:
    st.subheader("Replay a built-in Trader")
    st.caption("First 800 ticks of day 0 from a matching Round 1 or Round 2 sample")
    round_num = st.selectbox("Strategy", (1, 2), format_func=lambda value: f"Round {value} Trader")
    mode = st.selectbox(
        "Public trade matching",
        ("worse", "all", "none"),
        format_func=lambda value: {
            "worse": "Only prices beyond my quote",
            "all": "Include trades at my quote",
            "none": "Displayed book only",
        }[value],
    )
    if st.button("Run sample replay", type="primary"):
        try:
            with st.spinner("Replaying recorded market ticks…"):
                result = replay_sample(round_num, mode)
            st.session_state.replay_result = (round_num, mode, result)
        except Exception as exc:  # noqa: BLE001
            st.error("The sample replay could not finish.")
            st.exception(exc)

    record = st.session_state.get("replay_result")
    if record and record[0] == round_num and record[1] == mode:
        result = record[2]
        pnl_metric, drawdown_metric, fills_metric = st.columns(3)
        pnl_metric.metric("Sample P&L", f"{result['total_pnl']:,.2f} seashells")
        drawdown_metric.metric("Max drawdown", f"{result['max_drawdown']:,.2f} seashells")
        fills_metric.metric("Fills", f"{result['fills']:,}")
        st.markdown("### P&L by product")
        product_pnl = pd.DataFrame(
            [
                {"Product": product, "P&L (seashells)": pnl}
                for product, pnl in result["product_pnl"].items()
            ]
        )
        st.dataframe(product_pnl, hide_index=True, width="stretch")
        st.caption(
            f"Submitted {result['submitted_orders']:,} orders, with "
            f"{result['position_limit_rejections']:,} position-limit rejections "
            f"and {result['traded_volume']:,} units traded."
        )
    with st.expander("How this replay fills orders"):
        st.markdown(
            "Marketable orders fill against the displayed book. Resting orders use "
            "the selected public-trade rule. The sample covers only the first 800 "
            "ticks of day 0. A row with no quotes carries forward the last valid "
            "mid price for inventory valuation. Queue priority, conversions, and "
            "Round 2 market-access bidding are not modeled."
        )


def render_research() -> None:
    st.subheader("Ask TradeTell")
    st.caption("Questions about rules, strategies, and Trader code with retrieved context")
    # On Streamlit Cloud, secrets aren't automatically in os.environ; bridge the
    # config keys across so the os.getenv-based model config picks them up. Locally
    # this no-ops (no secrets file) and .env is used instead.
    if os.environ.get("TRADETELL_TEST_MODE") != "1":
        try:
            # HF_TOKEN is read by huggingface-hub when sentence-transformers pulls the
            # embedding model; bridging it authenticates the download (higher rate limit,
            # no "unauthenticated requests to the HF Hub" warning).
            for key in (
                "GROQ_API_KEY",
                "LLM_MODEL",
                "LLM_TEMPERATURE",
                "GROQ_TIMEOUT_SECONDS",
                "EMBEDDING_MODEL",
                "HF_TOKEN",
            ):
                if key in st.secrets:
                    os.environ.setdefault(key, str(st.secrets[key]))
        except (ImportError, FileNotFoundError):
            # st.secrets may not be available in all contexts
            pass

    pending = st.session_state.pop("pending_prompt", None)
    prompt = st.chat_input("Ask about a product, strategy, or Trader class…")
    if pending:
        prompt = pending

    if not st.session_state.messages and not prompt:
        st.markdown("### Start with a question")
        for category, example in EXAMPLE_PROMPTS:
            category_column, prompt_column = st.columns([1, 5], vertical_alignment="center")
            category_column.caption(category)
            if prompt_column.button(example, key=f"ex_{category}"):
                st.session_state.pending_prompt = example
                st.rerun()
            st.divider()

    # Replay the conversation so far.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_sources(message.get("sources", []))

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Retrieving context and generating an answer…"):
                try:
                    rag_chain = initialize_rag_system()
                    result = rag_chain.invoke({"query": prompt})
                    answer = result["result"]
                    sources = result.get("source_documents", [])
                except Exception as exc:  # noqa: BLE001
                    answer = "The assistant could not answer. Please try again."
                    sources = []
                    st.exception(exc)
            st.markdown(answer)
            render_sources(sources)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "sources": sources}
        )


# Main panel
st.markdown('<h1 class="app-title">IMC Prosperity Workbench</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="app-subtitle">Inspect recorded markets, test a built-in strategy, '
    "and trace answers back to their sources.</p>",
    unsafe_allow_html=True,
)

if workspace == "Market desk":
    render_market_desk()
elif workspace == "Replay lab":
    render_replay_lab()
else:
    render_research()
