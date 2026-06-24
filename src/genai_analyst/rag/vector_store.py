"""
Vector storage (Sprint 1, Step 6 of the SRS flow).

Wraps a persistent ChromaDB client. Each filing is stored in its own collection
keyed by ``ticker_form_accession`` so that re-analysing the same filing reuses
the existing index instead of re-embedding (a simple, effective cache).
"""

from __future__ import annotations

from typing import List, Optional

from genai_analyst.core import config

_CLIENT = None  # lazy-loaded persistent ChromaDB client


def _get_client():
    """Create and cache the persistent ChromaDB client on first use."""
    global _CLIENT
    if _CLIENT is None:
        import chromadb

        _CLIENT = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return _CLIENT


def _collection_name(filing: dict) -> str:
    """Build a filesystem-safe collection name for a filing."""
    accession = filing.get("accession", "na").replace("-", "")
    return f"{filing['ticker']}_{filing['form']}_{accession}".replace("-", "_")


def collection_exists(filing: dict) -> bool:
    """Return True if this filing already has a populated collection."""
    name = _collection_name(filing)
    try:
        collection = _get_client().get_collection(name)
        return collection.count() > 0
    except Exception:
        return False


def add_chunks(filing: dict, chunks: List[dict], vectors: List[List[float]]) -> int:
    """Store chunk texts + vectors for a filing. Returns the chunk count."""
    if not chunks:
        return 0

    name = _collection_name(filing)
    client = _get_client()
    collection = client.get_or_create_collection(name)

    ids = [f"{name}_{chunk['chunk_id']}" for chunk in chunks]
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [{"section": chunk["section"]} for chunk in chunks]

    collection.add(
        ids=ids, embeddings=vectors, documents=documents, metadatas=metadatas
    )
    return len(chunks)


def query(filing: dict, query_vector: List[float], top_k: Optional[int] = None) -> List[dict]:
    """Return the top-k most similar chunks for a query vector.

    Each result is ``{"text": str, "section": str, "distance": float}``.
    """
    top_k = top_k or config.RAG_TOP_K
    name = _collection_name(filing)

    try:
        collection = _get_client().get_collection(name)
    except Exception:
        return []

    response = collection.query(query_embeddings=[query_vector], n_results=top_k)
    documents = response.get("documents", [[]])[0]
    metadatas = response.get("metadatas", [[]])[0]
    distances = response.get("distances", [[]])[0]

    results: List[dict] = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        results.append(
            {
                "text": text,
                "section": (metadata or {}).get("section", ""),
                "distance": distance,
            }
        )
    return results
