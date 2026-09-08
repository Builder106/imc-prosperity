# Security notes

## Dependency security boundary

The application does not install or import ChromaDB. The three local retrieval
stores use the in-process implementation in `src/rag/local_vector_store.py`,
which performs cosine similarity over embedding vectors for the current
session. This removes the four previously open ChromaDB advisories from the
dependency graph instead of suppressing them.

The CI dependency audit has no Chroma-specific exceptions. Do not reintroduce
ChromaDB or a networked vector database without reviewing authentication,
tenant isolation, collection access, and code-execution behavior.
