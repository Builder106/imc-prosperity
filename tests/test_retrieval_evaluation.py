import pytest
from langchain_core.documents import Document
from src.rag.retrieval_evaluation import RetrievalQuestion, score_retrieval


class FixedRetriever:
    def __init__(self, sources: list[str]):
        self.documents = [
            Document(page_content="chunk", metadata={"source": source}) for source in sources
        ]

    def invoke(self, input: str) -> list[Document]:
        return self.documents


def test_scoring_counts_each_exact_source_once_and_keeps_chunk_ranks():
    questions: list[RetrievalQuestion] = [
        {"id": "rules", "query": "rules", "relevant_sources": ["rules.md", "rules.md", "faq.md"]},
        {"id": "limits", "query": "limits", "relevant_sources": ["limits.md"]},
    ]
    retriever = FixedRetriever(
        ["rules.md.bak", "/wiki/RULES.md", "/wiki/rules.md", "faq.md", "limits.md"]
    )

    result = score_retrieval(retriever, questions, k=4)

    assert result["source_recall_at_k"] == 0.6667
    assert result["mean_reciprocal_rank"] == 0.25
    assert result["results"][0]["found_sources"] == ["faq.md", "rules.md"]
    assert result["results"][0]["first_relevant_rank"] == 2
    assert result["results"][1]["first_relevant_rank"] is None


@pytest.mark.parametrize("k", [0, -1])
def test_scoring_rejects_invalid_k(k):
    with pytest.raises(ValueError, match="k must be greater than zero"):
        score_retrieval(FixedRetriever([]), [], k)


def test_scoring_rejects_empty_benchmarks_and_missing_labels():
    with pytest.raises(ValueError, match="at least one question"):
        score_retrieval(FixedRetriever([]), [], 5)
    with pytest.raises(ValueError, match="no relevant sources"):
        score_retrieval(
            FixedRetriever([]), [{"id": "empty", "query": "?", "relevant_sources": []}], 5
        )
