from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore


class LocalVectorStore(VectorStore):
    """Small in-process vector store for the application's local corpus."""

    def __init__(
        self, documents: Sequence[Document], vectors: Sequence[Sequence[float]], embedding: Any
    ):
        self._documents = list(documents)
        self._vectors = np.asarray(vectors, dtype=np.float32)
        self._embedding = embedding

        if self._vectors.ndim != 2 or len(self._documents) != len(self._vectors):
            raise ValueError(
                "Documents and embedding vectors must have matching two-dimensional shapes"
            )

    @property
    def embeddings(self) -> Any:
        return self._embedding

    @classmethod
    def from_documents(
        cls,
        documents: Iterable[Document],
        embedding: Any,
        **_: Any,
    ) -> "LocalVectorStore":
        materialized_documents = list(documents)
        if not materialized_documents:
            raise ValueError("At least one document is required")

        vectors = embedding.embed_documents(
            [document.page_content for document in materialized_documents]
        )
        return cls(materialized_documents, vectors, embedding)

    @classmethod
    def from_texts(
        cls,
        texts: Iterable[str],
        embedding: Any,
        metadatas: Sequence[dict[str, Any]] | None = None,
        **_: Any,
    ) -> "LocalVectorStore":
        materialized_texts = list(texts)
        materialized_metadatas = list(metadatas or [{} for _ in materialized_texts])
        if len(materialized_texts) != len(materialized_metadatas):
            raise ValueError("Texts and metadata must have matching lengths")

        documents = [
            Document(page_content=text, metadata=metadata)
            for text, metadata in zip(materialized_texts, materialized_metadatas, strict=True)
        ]
        return cls.from_documents(documents, embedding)

    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> list[Document]:
        del kwargs
        return [document for document, _ in self.similarity_search_with_score(query, k=k)]

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        **kwargs: Any,
    ) -> list[tuple[Document, float]]:
        del kwargs
        if k <= 0 or not self._documents:
            return []

        query_vector = np.asarray(self._embedding.embed_query(query), dtype=np.float32)
        if query_vector.ndim != 1 or query_vector.shape[0] != self._vectors.shape[1]:
            raise ValueError("Query and document embeddings must have matching dimensions")

        document_norms = np.linalg.norm(self._vectors, axis=1)
        query_norm = np.linalg.norm(query_vector)
        if query_norm == 0:
            scores = np.zeros(len(self._documents), dtype=np.float32)
        else:
            denominators = document_norms * query_norm
            scores = np.divide(
                self._vectors @ query_vector,
                denominators,
                out=np.zeros_like(document_norms),
                where=denominators != 0,
            )

        ranked_indexes = np.argsort(-scores, kind="stable")[:k]
        return [(self._documents[index], float(1 - scores[index])) for index in ranked_indexes]
