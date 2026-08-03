"""
indexer.py
==========
Embedding Generation + ChromaDB Indexing (Pipeline Steps 5-6).

Takes the chunks produced by ``chunker.py``, generates Sentence Transformer
embeddings for each (via ``embedder.py``), and persists the chunks + vectors
into ChromaDB (via ``vector_store.py``).

Running ``index_filing()`` makes a filing queryable by ``retriever.py``.
Indexing is cached: an already-indexed filing is skipped unless ``force`` is
set, in which case its collection is reset and rebuilt.
"""

from __future__ import annotations

from typing import Dict

from genai_analyst.rag import chunker
from genai_analyst.rag import embedder
from genai_analyst.rag import vector_store


def index_filing(filing: dict, sections: Dict[str, str], force: bool = False) -> int:
    """Chunk -> embed -> store a filing in ChromaDB. Returns chunk count.

    If the filing is already indexed and force is False, indexing is skipped
    (caching) and the existing chunk count is returned.
    """
    if not force and vector_store.collection_exists(filing):
        col = vector_store.get_or_create_collection(filing)
        return col.count()

    if force:
        vector_store.reset_collection(filing)

    chunk_dicts = chunker.chunk_sections(sections)
    if not chunk_dicts:
        return 0

    texts = [c["text"] for c in chunk_dicts]
    metadatas = [{"section": c["section"], "chunk_index": i}
                 for i, c in enumerate(chunk_dicts)]

    embeddings = embedder.embed_texts(texts)
    return vector_store.add_chunks(filing, texts, embeddings, metadatas)


if __name__ == "__main__":
    demo_sections = {
        "MD&A": "Revenue grew strongly. " * 200,
        "Risk Factors": "We face competitive risks. " * 200,
        "full": "",
    }
    demo_filing = {"ticker": "TEST", "form": "10-K", "accession": "0000-demo"}
    print("Note: requires ChromaDB + embedder; run via the full pipeline.")
