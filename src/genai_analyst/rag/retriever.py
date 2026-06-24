"""
Retrieval-Augmented Generation retriever (Sprint 1, Step 7 of the SRS flow).

Embeds a natural-language query and runs a Top-K cosine-similarity search over
the filing's ChromaDB collection. Task-specific query templates target the
sections most relevant to each downstream analysis (summary, risks, guidance),
which improves retrieval precision over a single generic query.
"""

from __future__ import annotations

from typing import Dict, List

from genai_analyst.core import config
from genai_analyst.rag import embedder, vector_store

# One tuned query per downstream analytical task.
QUERY_TEMPLATES: Dict[str, str] = {
    "executive_summary": (
        "Overall financial performance, revenue, net income and business "
        "highlights for the period."
    ),
    "risk_factors": (
        "Key risk factors, uncertainties and threats facing the company."
    ),
    "guidance": (
        "Forward-looking guidance, outlook and management expectations for "
        "future performance."
    ),
}


def retrieve(filing: dict, query_text: str, top_k: int | None = None) -> List[dict]:
    """Retrieve the Top-K most relevant chunks for a free-text query."""
    query_vector = embedder.embed_query(query_text)
    if not query_vector:
        return []
    return vector_store.query(filing, query_vector, top_k=top_k)


def retrieve_context(filing: dict, task: str) -> str:
    """Retrieve and concatenate context for a named task.

    ``task`` must be one of the keys in ``QUERY_TEMPLATES``.
    """
    query_text = QUERY_TEMPLATES.get(task, task)
    chunks = retrieve(filing, query_text, top_k=config.RAG_TOP_K)
    return "\n\n".join(chunk["text"] for chunk in chunks)


def retrieve_all_contexts(filing: dict) -> Dict[str, str]:
    """Retrieve context blocks for every analytical task at once."""
    return {task: retrieve_context(filing, task) for task in QUERY_TEMPLATES}
