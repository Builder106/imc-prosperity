import html
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from src.ui.ground import component_value, intara_section
from src.ui.workbench import (
    DAYS,
    MATCHES,
    OSMIUM,
    PEPPER,
    TRADERS,
    DaySummary,
    Overview,
    Place,
    ReplayPayload,
    day_summary,
    overview,
    parse_params,
    place_params,
    replay_payload,
)

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
FAVICON = PROJECT_ROOT / "assets" / "logo.png"
TITLES = {
    "ground": "TradeTell | Study IMC Prosperity 4",
    "trader": "TradeTell | Replay a Trader",
    "notes": "TradeTell | Field notes",
    "index": "TradeTell | Index",
}
EXAMPLE_PROMPTS = (
    "What does the wiki say about Intarian Pepper Root and Ash-Coated Osmium?",
    "What are the position limits in Round 1?",
    "How does the Market Access Fee bid work in Round 2?",
    "Write a market-making Trader class for ASH_COATED_OSMIUM.",
)

params = parse_params(st.query_params.to_dict())
layer = params["layer"]

st.set_page_config(
    page_title=TITLES[layer],
    page_icon=str(FAVICON) if FAVICON.exists() else "📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.html(f"<style>{(PROJECT_ROOT / 'src/ui/app.css').read_text(encoding='utf-8')}</style>")
# The section mounts after its script loads; reserving its height keeps the notes and index from
# jumping down under it. Measured at 1440 and 390 px wide.
RESERVED_HEIGHT = {"notes": (530, 446), "index": (504, 421)}
if layer in RESERVED_HEIGHT:
    desktop, phone = RESERVED_HEIGHT[layer]
    st.html(
        f"<style>.st-key-intara {{ min-height: {desktop}px; }}"
        f"@media (max-width: 900px) {{ .st-key-intara {{ min-height: {phone}px; }} }}</style>"
    )


@st.cache_data(show_spinner=False, max_entries=24)
def replay(trader_round: int, day: int, match: str) -> ReplayPayload:
    return replay_payload(trader_round, day, match)


@st.cache_data(show_spinner=False)
def record_overview() -> Overview:
    return overview()


@st.cache_data(show_spinner=False)
def cached_day_summary(day: int) -> DaySummary:
    return day_summary(day)


@st.cache_data(show_spinner=False)
def summaries() -> list[DaySummary]:
    return [cached_day_summary(day) for day in DAYS]


# The section reports state through these callbacks, which run before the script reruns.
def on_place() -> None:
    place = component_value("place")
    if isinstance(place, dict):
        merged: Place = {
            "zoom": place.get("zoom"),
            "day": int(place.get("day", params["place"]["day"])),
            "t": int(place.get("t", params["place"]["t"])),
        }
        for name in ("zoom", "day", "t"):
            st.query_params.pop(name, None)
        st.query_params.update(place_params(merged))


def on_replay() -> None:
    settings = component_value("replay")
    if isinstance(settings, dict):
        st.query_params.update(
            {
                "trader": str(settings.get("trader")),
                "rday": str(settings.get("day")),
                "match": str(settings.get("match")),
            }
        )


def on_nav() -> None:
    target = component_value("nav")
    if isinstance(target, str):
        st.query_params["layer"] = target


# RAG system (built once, cached for the session)
@st.cache_resource(show_spinner="Loading the knowledge base and building the search index…")
def initialize_rag_system():
    if os.environ.get("TRADETELL_TEST_MODE") == "1":
        return _fake_rag_chain()
    # Imported here so the section paints without waiting for the embedding stack to load.
    from src.rag.build_rag_system import (
        create_combined_retriever,
        create_rag_chain,
        create_vector_stores,
        process_discord_data,
        process_notion_wiki_data,
        process_trading_data,
    )

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
    """Render retrieved passages as specimen labels inside a collapsed expander."""
    if not source_documents:
        return
    with st.expander(f"Sources ({len(source_documents)})"):
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
            st.html(
                f'<p class="specimen"><b>{i}. {html.escape(str(title))}</b>'
                f"<span>{corpus}, {html.escape(source)}</span></p>"
            )
            st.code(doc.page_content, language="text")


def bridge_secrets() -> None:
    # On Streamlit Cloud, secrets aren't automatically in os.environ; bridge the config keys
    # across so the os.getenv-based model config picks them up. Locally this no-ops.
    if os.environ.get("TRADETELL_TEST_MODE") == "1":
        return
    try:
        # HF_TOKEN authenticates the sentence-transformers model download.
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


def render_notes() -> None:
    bridge_secrets()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    with st.container(key="notes"):
        pending = st.session_state.pop("pending_prompt", None)
        if not st.session_state.messages and not pending:
            st.html('<p class="notes-start">Start with a question</p>')
            for i, example in enumerate(EXAMPLE_PROMPTS):
                if st.button(example, key=f"example_{i}", width="stretch"):
                    st.session_state.pending_prompt = example
                    st.rerun()

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message["role"] == "assistant":
                    render_sources(message.get("sources", []))

        prompt = st.chat_input("Ask about a good, a rule, or a Trader class") or pending
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Retrieving passages and writing an answer…"):
                    try:
                        result = initialize_rag_system().invoke({"query": prompt})
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

        if st.session_state.messages and st.button("Clear the notes", key="clear"):
            st.session_state.messages = []
            st.rerun()


def _day_label(day: int) -> str:
    return f"Day \N{MINUS SIGN}{-day}" if day < 0 else f"Day {day}"


def _n(value: float) -> str:
    return f"{value:,.1f}".removesuffix(".0")


def render_index() -> None:
    rows = []
    for summary in summaries():
        day = summary["day"]
        pepper, osmium = summary["goods"][PEPPER], summary["goods"][OSMIUM]
        rows.append(
            f"<tr><th scope='row'><a href='?layer=ground&zoom={day}&day={day}&t=500000'>"
            f"{_day_label(day)}</a></th><td>{summary['source']}</td>"
            f"<td class='pepper'>{_n(pepper['open'])} to {_n(pepper['close'])}</td>"
            f"<td class='osmium'>{_n(osmium['low'])} to {_n(osmium['high'])}</td>"
            f"<td>{pepper['trades'] + osmium['trades']:,}</td>"
            f"<td><a href='?layer=trader&rday={day}'>Replay {_day_label(day).lower()}</a></td></tr>"
        )
    with st.container(key="index"):
        st.html(
            f"""
            <div class="ix">
              <h2>Recorded days</h2>
              <table>
                <thead><tr><th scope="col">Day</th><th scope="col">Data capsule</th>
                <th scope="col">Pepper root, open to close</th><th scope="col">Osmium, low to high</th>
                <th scope="col">Public trades</th><th scope="col">Trader</th></tr></thead>
                <tbody>{"".join(rows)}</tbody>
              </table>
              <p class="muted">Prices are mid prices in XIRECs. Each day has 10,000 ticks, one every 100 timestamps.</p>
              <h2>Layers</h2>
              <ul>
                <li><a href="?layer=ground">Ground</a>: the four days as one section, with the order book at any tick.</li>
                <li><a href="?layer=trader">Your Trader</a>: replay the built-in Round {TRADERS[0]} or Round {TRADERS[-1]} Trader through any day.</li>
                <li><a href="?layer=notes">Field notes</a>: ask the competition wiki, the market archive and the code examples.</li>
              </ul>
              <h2>About the data</h2>
              <p>The record comes from the Prosperity 4 data capsules: days {_day_label(-2)[4:]}, {_day_label(-1)[4:]} and 0 from Round 1, and day 1 from Round 2. Each tick holds up to three bid and three ask levels per good, plus the public trades at that tick.</p>
              <p>The replay fills marketable orders against the displayed book and resting orders from public trades, using one of {len(MATCHES)} rules. It does not model queue priority, conversions or the Round 2 market access bid, so its results are a study aid and not a forecast of competition scores.</p>
            </div>
            """
        )


# The section is the interface on every layer; only the content under it changes.
data: dict[str, object] = {
    "layer": layer,
    "static": "app/static/intara/",
    "overview": record_overview(),
    "place": params["place"],
    "replay_settings": params["replay"],
    "options": {"traders": list(TRADERS), "matches": list(MATCHES)},
}
zoom_day = params["place"]["zoom"]
if layer == "ground" and zoom_day is not None:
    data["zoom_summary"] = cached_day_summary(zoom_day)
if layer == "trader":
    settings = params["replay"]
    try:
        data["replay"] = replay(settings["trader"], settings["day"], settings["match"])
    except Exception as exc:  # noqa: BLE001
        st.error("The replay could not finish.")
        st.exception(exc)

intara_section(data, on_place=on_place, on_replay=on_replay, on_nav=on_nav)

if layer == "notes":
    render_notes()
elif layer == "index":
    render_index()

# Streamlit hides <footer> elements, so the band is a div with the contentinfo role.
st.html(
    """
    <div class="tt-foot" role="contentinfo">
      <div class="tt-foot__in">
        <span class="tt-foot__mark">TradeTell</span>
        <nav class="tt-foot__links" aria-label="More">
          <a href="https://github.com/Builder106/imc-prosperity">Source on GitHub</a>
          <a href="https://prosperity.imc.com/">IMC Prosperity</a>
          <a href="?layer=index">Index</a>
        </nav>
        <p class="tt-foot__note">A study tool built on the Prosperity 4 data capsules. Not made by or affiliated with IMC.</p>
      </div>
    </div>
    """
)
