"""
retriever.py
================
Retrieval-Augmented Generation - Retrieval Layer (Pipeline Step 7).

Given a natural-language query (e.g. "What are the main risk factors?"),
embeds the query and performs a Top-K cosine similarity search over a
filing's ChromaDB collection, returning the most relevant chunks.

Only these retrieved chunks are later passed to Llama 3, which:
    * minimises token usage / API cost (SRS constraint), and
    * reduces hallucination by grounding the LLM in source text.
"""

from __future__ import annotations

from typing import List

from genai_analyst.core import config
from genai_analyst.rag import vector_store
from genai_analyst.rag.embedder import embed_query


def retrieve(filing: dict, query_text: str, top_k: int = config.RAG_TOP_K) -> List[dict]:
    """Return the Top-K most relevant chunks for a query against a filing."""
    q_vec = embed_query(query_text)
    return vector_store.query(filing, q_vec, top_k=top_k)


def retrieve_context(filing: dict, query_text: str, top_k: int = config.RAG_TOP_K) -> str:
    """Retrieve Top-K chunks and concatenate them into one context block."""
    hits = retrieve(filing, query_text, top_k=top_k)
    return "\n\n---\n\n".join(h["document"] for h in hits)


# Canonical analyst queries used by the pipeline to pull targeted context.
QUERY_TEMPLATES = {
    "executive_summary": "Overall business performance, revenue, profitability, "
    "and key results this period.",
    "risk_factors": "What are the most significant risk factors and uncertainties "
    "facing the company?",
    "guidance": "Forward-looking guidance, outlook, expectations, and future "
    "projections from management.",
    "tone": "Management's discussion of results, confidence, challenges, and outlook.",
}


def retrieve_all_contexts(filing: dict, top_k: int = config.RAG_TOP_K) -> dict:
    """Retrieve context blocks for every canonical analyst query."""
    return {
        key: retrieve_context(filing, q, top_k=top_k)
        for key, q in QUERY_TEMPLATES.items()
    }


if __name__ == "__main__":
    print("Available query templates:", list(QUERY_TEMPLATES.keys()))
