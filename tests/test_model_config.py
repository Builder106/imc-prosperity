import importlib
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _reload_module():
    import src.rag.model_config as model_config

    return importlib.reload(model_config)


def test_defaults_use_claude_and_local_embeddings(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("CLAUDE_CLI_COMMAND", raising=False)
    monkeypatch.delenv("CLAUDE_CLI_TIMEOUT_SECONDS", raising=False)

    module = _reload_module()

    assert module.get_llm_model_name().startswith("claude")
    assert module.get_embedding_model_name() == "sentence-transformers/all-MiniLM-L6-v2"
    assert module.get_claude_cli_command() == "claude"
    assert module.get_claude_cli_timeout_seconds() == 180


def test_env_overrides_model_selection(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "claude-3-5-haiku-latest")
    monkeypatch.setenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
    monkeypatch.setenv("CLAUDE_CLI_COMMAND", "/opt/homebrew/bin/claude")
    monkeypatch.setenv("CLAUDE_CLI_TIMEOUT_SECONDS", "240")

    module = _reload_module()

    assert module.get_llm_model_name() == "claude-3-5-haiku-latest"
    assert module.get_embedding_model_name() == "sentence-transformers/all-mpnet-base-v2"
    assert module.get_claude_cli_command() == "/opt/homebrew/bin/claude"
    assert module.get_claude_cli_timeout_seconds() == 240
