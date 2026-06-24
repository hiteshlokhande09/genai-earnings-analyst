"""
Embedding generation (Sprint 1, Step 5 of the SRS flow).

Wraps the Sentence Transformers ``all-MiniLM-L6-v2`` model to convert text into
384-dimensional dense vectors. The model is loaded lazily and cached as a
module-level singleton so it is only initialised once per process.
"""

from __future__ import annotations

from typing import List, Optional

from genai_analyst.core import config

_MODEL = None  # lazy-loaded SentenceTransformer singleton — avoids reloading the model on every call


def _get_model():
    """Load and cache the embedding model on first use."""
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    return _MODEL


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts, returning one vector per input text."""
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return [vector.tolist() for vector in vectors]


def embed_query(text: str) -> List[float]:
    """Embed a single query string into one vector."""
    result = embed_texts([text])
    return result[0] if result else []
