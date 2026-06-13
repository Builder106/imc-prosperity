import os

from groq import Groq


def run_groq_chat(
    prompt,
    model,
    api_key=None,
    temperature=0.2,
    timeout_seconds=180,
    max_tokens=None,
):
    """Send a single-turn prompt to the Groq chat API and return the text."""
    api_key = api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file locally or to "
            "Streamlit secrets when deploying."
        )

    client = Groq(api_key=api_key, timeout=timeout_seconds)
    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    # Bound the completion so input + reserved output stays under the model's
    # tokens-per-minute limit (Groq free tier = 12k TPM for llama-3.3-70b).
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    completion = client.chat.completions.create(**kwargs)
    return (completion.choices[0].message.content or "").strip()


class GroqRagChain:
    def __init__(
        self,
        retriever,
        prompt_template,
        model,
        api_key=None,
        temperature=0.2,
        timeout_seconds=180,
        max_context_chars=12000,
        max_completion_tokens=None,
    ):
        self.retriever = retriever
        self.prompt_template = prompt_template
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        # Cap how much retrieved text is stuffed into the prompt so the request
        # stays under the LLM's tokens-per-minute limit. The retriever is RRF-
        # ranked, so truncating keeps the most relevant chunks.
        self.max_context_chars = max_context_chars
        self.max_completion_tokens = max_completion_tokens

    def _retrieve_documents(self, query):
        if self.retriever is None:
            raise RuntimeError(
                "No retriever is available — the vector store failed to build. "
                "Check the app logs for the underlying error."
            )
        # langchain 1.x retrievers expose .invoke(); the legacy
        # get_relevant_documents() was removed. Every langchain retriever
        # (incl. EnsembleRetriever) has .invoke, so call it directly.
        documents = self.retriever.invoke(query)
        return documents or []

    def _build_context(self, documents):
        """Join retrieved chunks into a context string, stopping once the
        char budget is hit. Returns (context, documents_actually_used) so the
        UI shows the sources that informed the answer."""
        pieces, used_docs, used_chars = [], [], 0
        for doc in documents:
            text = doc.page_content or ""
            # +2 for the "\n\n" separator. Always keep at least one chunk.
            if pieces and used_chars + len(text) + 2 > self.max_context_chars:
                break
            pieces.append(text)
            used_docs.append(doc)
            used_chars += len(text) + 2
        return "\n\n".join(pieces), used_docs

    def invoke(self, inputs):
        query = inputs.get("query", "").strip()
        if not query:
            raise ValueError("Query is required")

        source_documents = self._retrieve_documents(query)
        context, used_documents = self._build_context(source_documents)
        prompt = self.prompt_template.format(context=context, question=query)
        result = run_groq_chat(
            prompt=prompt,
            model=self.model,
            api_key=self.api_key,
            temperature=self.temperature,
            timeout_seconds=self.timeout_seconds,
            max_tokens=self.max_completion_tokens,
        )
        return {"result": result, "source_documents": used_documents}
