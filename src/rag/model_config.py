import os


def get_llm_model_name():
    return os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")


def get_llm_temperature():
    return float(os.getenv("LLM_TEMPERATURE", "0.2"))


def get_embedding_model_name():
    return os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def get_groq_api_key():
    return os.getenv("GROQ_API_KEY", "")


def get_groq_timeout_seconds():
    return int(os.getenv("GROQ_TIMEOUT_SECONDS", "180"))


def get_max_completion_tokens():
    # Bounds the model's output so input + reserved output stays under the
    # tokens-per-minute limit.
    return int(os.getenv("LLM_MAX_TOKENS", "4096"))


def get_max_context_chars():
    # Caps retrieved-context size fed into the prompt. ~12k chars ~= ~3k tokens,
    # leaving room for the template + question + completion under Groq's free
    # tier (12k TPM for llama-3.3-70b). Raise it on a higher tier.
    return int(os.getenv("RAG_MAX_CONTEXT_CHARS", "12000"))
