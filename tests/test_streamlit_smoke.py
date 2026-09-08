"""Deterministic Streamlit smoke test using the in-process RAG fixture."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_answers_with_fixture(monkeypatch):
    monkeypatch.setenv("TRADETELL_TEST_MODE", "1")

    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=60)
    app.run()

    assert not app.exception
    app.chat_input[0].set_value("What is the Round 1 position limit?").run()

    assert not app.exception
    assert any("Fixture answer" in markdown.value for markdown in app.markdown)
    assert any("1 source document" in expander.label for expander in app.expander)
