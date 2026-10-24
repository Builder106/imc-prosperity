"""Deterministic Streamlit smoke test using the in-process RAG fixture."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / "app.py"


def test_every_layer_renders(monkeypatch):
    monkeypatch.setenv("TRADETELL_TEST_MODE", "1")
    for layer in ("ground", "trader", "index"):
        app = AppTest.from_file(APP, default_timeout=60)
        app.query_params["layer"] = layer
        app.run()
        assert not app.exception, layer
    assert any("Recorded days" in element.proto.body for element in app.get("html"))


def test_field_notes_answer_with_fixture(monkeypatch):
    monkeypatch.setenv("TRADETELL_TEST_MODE", "1")

    app = AppTest.from_file(APP, default_timeout=60)
    app.query_params["layer"] = "notes"
    app.run()

    assert not app.exception
    assert any("Pepper Root" in button.label for button in app.button)
    app.chat_input[0].set_value("What is the Round 1 position limit?").run()

    assert not app.exception
    assert any("Fixture answer" in markdown.value for markdown in app.markdown)
    assert any("Sources (1)" in expander.label for expander in app.expander)
