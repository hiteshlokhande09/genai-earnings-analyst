"""
RAG indexing orchestration (Sprint 1, Steps 4-6 combined).

Ties together chunking, embedding and vector storage for a single filing.
Indexing is skipped when the filing's collection already exists, which makes
repeat analyses fast and avoids redundant embedding work.
"""

from __future__ import annotations

from typing import Dict

from genai_analyst.rag import chunker, embedder, vector_store


def index_filing(filing: dict, sections: Dict[str, str]) -> int:
    """Chunk, embed and store a filing's sections.

    Returns the number of chunks indexed. If the filing is already indexed,
    returns the existing chunk count without re-embedding.
    """
    if vector_store.collection_exists(filing):
        return -1  # sentinel: already indexed (cache hit)

    chunks = chunker.chunk_sections(sections)
    if not chunks:
        return 0

    vectors = embedder.embed_texts([chunk["text"] for chunk in chunks])
    return vector_store.add_chunks(filing, chunks, vectors)
