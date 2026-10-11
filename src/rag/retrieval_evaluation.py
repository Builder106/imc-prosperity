from __future__ import annotations

import argparse
import contextlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, TypedDict

from langchain_core.documents import Document

from .build_rag_system import (
    DISCORD_DATA_DIR,
    create_combined_retriever,
    create_vector_stores,
    process_discord_data,
    process_notion_wiki_data,
    process_trading_data,
)
from .model_config import get_embedding_model_name

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_PATH = PROJECT_ROOT / "data" / "evaluations" / "retrieval_benchmark.json"


class RetrieverProtocol(Protocol):
    def invoke(self, input: str) -> list[Document]: ...


class RetrievalQuestion(TypedDict):
    id: str
    query: str
    relevant_sources: list[str]


class QuestionResult(TypedDict):
    id: str
    query: str
    found_sources: list[str]
    retrieved_sources: list[str]
    first_relevant_rank: int | None


class RetrievalScore(TypedDict):
    k: int
    question_count: int
    source_recall_at_k: float
    mean_reciprocal_rank: float
    results: list[QuestionResult]


def score_retrieval(
    retriever: RetrieverProtocol, questions: Sequence[RetrievalQuestion], k: int
) -> RetrievalScore:
    if k <= 0:
        raise ValueError("k must be greater than zero")
    if not questions:
        raise ValueError("The retrieval benchmark must contain at least one question")

    results: list[QuestionResult] = []
    found_total = 0
    relevant_total = 0
    reciprocal_ranks = []
    for question in questions:
        query_id = question["id"]
        query = question["query"]
        expected_sources = {Path(source).name.casefold() for source in question["relevant_sources"]}
        if not expected_sources:
            raise ValueError(f"Question {query_id} has no relevant sources")

        documents = retriever.invoke(query)[:k]
        found_ranks: dict[str, int] = {}
        retrieved_sources = []
        for rank, document in enumerate(documents, start=1):
            source = Path(str(document.metadata.get("source", ""))).name.casefold()
            retrieved_sources.append(source)
            if source in expected_sources:
                found_ranks.setdefault(source, rank)

        found_sources = sorted(found_ranks)
        found_total += len(found_sources)
        relevant_total += len(expected_sources)
        first_rank = min(found_ranks.values(), default=None)
        reciprocal_ranks.append(1 / first_rank if first_rank is not None else 0.0)
        results.append(
            {
                "id": query_id,
                "query": query,
                "found_sources": found_sources,
                "retrieved_sources": retrieved_sources,
                "first_relevant_rank": first_rank,
            }
        )

    return {
        "k": k,
        "question_count": len(questions),
        "source_recall_at_k": round(found_total / relevant_total, 4),
        "mean_reciprocal_rank": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4),
        "results": results,
    }


def build_application_retrievers(k: int, compare_corpora: bool) -> dict[str, RetrieverProtocol]:
    with contextlib.redirect_stdout(sys.stderr):
        notion_documents = process_notion_wiki_data()
        if DISCORD_DATA_DIR.is_dir():
            notion_documents.extend(process_discord_data(DISCORD_DATA_DIR))
        trading_documents = process_trading_data()
        stores = create_vector_stores(notion_documents, trading_documents)
        retriever = create_combined_retriever(*stores)
    if retriever is None:
        raise RuntimeError("The application corpus did not produce a retriever")
    retrievers: dict[str, RetrieverProtocol] = {"combined": retriever}
    if compare_corpora:
        for name, store in zip(("wiki", "trading", "code"), stores, strict=True):
            if store is not None:
                retrievers[name] = store.as_retriever(search_kwargs={"k": k})
    return retrievers


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the application's local retriever.")
    parser.add_argument("--k", type=int, default=5, help="Number of retrieved chunks to score.")
    parser.add_argument(
        "--compare-corpora",
        action="store_true",
        help="Also score each available corpus separately.",
    )
    args = parser.parse_args()
    if args.k <= 0:
        parser.error("--k must be greater than zero")
    questions: list[RetrievalQuestion] = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    retrievers = build_application_retrievers(args.k, args.compare_corpora)
    result: dict[str, object] = {
        "benchmark": BENCHMARK_PATH.name,
        "embedding_model": get_embedding_model_name(),
        **score_retrieval(retrievers["combined"], questions, args.k),
    }
    if args.compare_corpora:
        result["corpus_results"] = {
            name: score_retrieval(retriever, questions, args.k)
            for name, retriever in retrievers.items()
            if name != "combined"
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
