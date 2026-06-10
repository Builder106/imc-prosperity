import os

from groq import Groq


def run_groq_chat(
    prompt,
    model,
    api_key=None,
    temperature=0.2,
    timeout_seconds=180,
):
    """Send a single-turn prompt to the Groq chat API and return the text."""
    api_key = api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file locally or to "
            "Streamlit secrets when deploying."
        )

    client = Groq(api_key=api_key, timeout=timeout_seconds)
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
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
    ):
        self.retriever = retriever
        self.prompt_template = prompt_template
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

    def _retrieve_documents(self, query):
        if self.retriever is None:
            raise RuntimeError(
                "No retriever is available — the vector store failed to build. "
                "Check the app logs for the underlying error."
            )
        if hasattr(self.retriever, "invoke"):
            documents = self.retriever.invoke(query)
        else:
            documents = self.retriever.get_relevant_documents(query)
        return documents or []

    def invoke(self, inputs):
        query = inputs.get("query", "").strip()
        if not query:
            raise ValueError("Query is required")

        source_documents = self._retrieve_documents(query)
        context = "\n\n".join(doc.page_content for doc in source_documents)
        prompt = self.prompt_template.format(context=context, question=query)
        result = run_groq_chat(
            prompt=prompt,
            model=self.model,
            api_key=self.api_key,
            temperature=self.temperature,
            timeout_seconds=self.timeout_seconds,
        )
        return {"result": result, "source_documents": source_documents}
