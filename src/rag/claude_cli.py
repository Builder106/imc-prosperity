import subprocess


def run_claude_cli(prompt, cli_command="claude", timeout_seconds=180):
    completed = subprocess.run(
        [cli_command, "-p", prompt],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        error_text = completed.stderr.strip() or completed.stdout.strip() or "Claude CLI failed"
        raise RuntimeError(error_text)
    return completed.stdout.strip()


class ClaudeCliRagChain:
    def __init__(self, retriever, prompt_template, cli_command="claude", timeout_seconds=180):
        self.retriever = retriever
        self.prompt_template = prompt_template
        self.cli_command = cli_command
        self.timeout_seconds = timeout_seconds

    def _retrieve_documents(self, query):
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
        result = run_claude_cli(
            prompt=prompt,
            cli_command=self.cli_command,
            timeout_seconds=self.timeout_seconds,
        )
        return {"result": result, "source_documents": source_documents}
