"""
vector_store.py
===============
ChromaDB Vector Storage (Pipeline Step 6).

Persists chunk embeddings to an on-disk ChromaDB collection and exposes
add / query / reset operations. Each filing gets its own logical collection
keyed by ticker + form + accession so that retrieval is scoped to a single
document and stale data is never mixed across companies.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from genai_analyst.core import config
_CLIENT = None  # persistent client singleton


def get_client():
    """Return a persistent ChromaDB client rooted at CHROMA_DIR."""
    global _CLIENT
    if _CLIENT is None:
        import chromadb

        _CLIENT = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return _CLIENT


def _collection_name(filing: dict) -> str:
    """Deterministic, Chroma-safe collection name for a filing."""
    raw = f"{filing['ticker']}_{filing['form']}_{filing['accession']}"
    return raw.replace("-", "_").replace(".", "_").lower()[:60]


def get_or_create_collection(filing: dict):
    """Return the collection for a filing, creating it if needed."""
    client = get_client()
    return client.get_or_create_collection(
        name=_collection_name(filing),
        metadata={"hnsw:space": "cosine"},
    )


def collection_exists(filing: dict) -> bool:
    """True if a non-empty collection already exists for this filing."""
    try:
        col = get_client().get_collection(_collection_name(filing))
        return col.count() > 0
    except Exception:  # noqa: BLE001 - collection not found
        return False


def add_chunks(
    filing: dict,
    chunks: List[str],
    embeddings: List[List[float]],
    metadatas: Optional[List[Dict]] = None,
) -> int:
    """Add chunk texts + embeddings to the filing's collection."""
    if not chunks:
        return 0
    col = get_or_create_collection(filing)
    ids = [f"{_collection_name(filing)}_{i}" for i in range(len(chunks))]
    if metadatas is None:
        metadatas = [{"chunk_index": i} for i in range(len(chunks))]
    col.add(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)
    return len(chunks)


def query(
    filing: dict, query_embedding: List[float], top_k: int = config.RAG_TOP_K
) -> List[Dict]:
    """Top-K cosine similarity search. Returns list of {document, metadata, distance}."""
    col = get_or_create_collection(filing)
    n = min(top_k, max(col.count(), 1))
    res = col.query(query_embeddings=[query_embedding], n_results=n)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    return [
        {"document": d, "metadata": m, "distance": dist}
        for d, m, dist in zip(docs, metas, dists)
    ]


def reset_collection(filing: dict) -> None:
    """Delete a filing's collection (used for forced re-index)."""
    try:
        get_client().delete_collection(_collection_name(filing))
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    fake = {"ticker": "TEST", "form": "10-K", "accession": "0000-00"}
    add_chunks(fake, ["hello world"], [[0.1] * 384])
    print("Collection count:", get_or_create_collection(fake).count())
