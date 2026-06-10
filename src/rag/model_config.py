import os


def get_llm_model_name():
    return os.getenv("LLM_MODEL", "claude-3-7-sonnet-latest")


def get_llm_temperature():
    return float(os.getenv("LLM_TEMPERATURE", "0.2"))


def get_embedding_model_name():
    return os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def get_claude_cli_command():
    return os.getenv("CLAUDE_CLI_COMMAND", "claude")


def get_claude_cli_timeout_seconds():
    return int(os.getenv("CLAUDE_CLI_TIMEOUT_SECONDS", "180"))
