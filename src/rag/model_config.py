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
