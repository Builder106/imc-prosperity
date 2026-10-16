"""Deterministic Streamlit smoke test using the in-process RAG fixture."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_workbench_market_and_replay(monkeypatch):
    monkeypatch.setenv("TRADETELL_TEST_MODE", "1")

    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=60)
    app.run()

    assert not app.exception
    assert any("Explore the market archive" in heading.value for heading in app.subheader)
    assert "PICNIC_BASKET1" in app.selectbox[0].options

    app.radio[0].set_value("Replay lab").run()
    assert not app.exception
    assert any("Replay a built-in Trader" in heading.value for heading in app.subheader)
    app.button[0].click().run()
    assert not app.exception
    assert any(metric.label == "Sample P&L" for metric in app.metric)


def test_app_answers_with_fixture(monkeypatch):
    monkeypatch.setenv("TRADETELL_TEST_MODE", "1")

    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=60)
    app.run()
    app.radio[0].set_value("Ask TradeTell").run()

    assert not app.exception
    assert any("Start with a question" in markdown.value for markdown in app.markdown)
    app.chat_input[0].set_value("What is the Round 1 position limit?").run()

    assert not app.exception
    assert any("Fixture answer" in markdown.value for markdown in app.markdown)
    assert any("Sources (1)" in expander.label for expander in app.expander)
