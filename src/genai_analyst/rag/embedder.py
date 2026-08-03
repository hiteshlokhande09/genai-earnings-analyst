"""
embedder.py
======================
Sentence Transformer Embedding Generation (Pipeline Step 5).

Wraps the `all-MiniLM-L6-v2` Sentence Transformers model to convert text
chunks into 384-dimensional dense vectors. The model is downloaded once on
first use and cached locally thereafter (no per-call cost, runs offline).

A module-level singleton avoids reloading the model on every call.
"""

from __future__ import annotations

from typing import List, Optional

from genai_analyst.core import config
_MODEL = None  # lazily-loaded singleton


def get_model():
    """Load (once) and return the Sentence Transformers embedding model."""
    global _MODEL
    if _MODEL is None:
        # Imported lazily so the rest of the app can be imported without the
        # heavy ML dependency present at import time.
        from sentence_transformers import SentenceTransformer

        print(f"[embedder] Loading model '{config.EMBEDDING_MODEL_NAME}'...")
        _MODEL = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    return _MODEL


def embed_texts(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Embed a list of texts -> list of float vectors."""
    if not texts:
        return []
    model = get_model()
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,  # cosine similarity ready
    )
    return [v.tolist() for v in vectors]


def embed_query(query: str) -> List[float]:
    """Embed a single query string -> one float vector."""
    return embed_texts([query])[0]


def embedding_dimension() -> Optional[int]:
    """Return the embedding vector dimension (384 for all-MiniLM-L6-v2)."""
    try:
        return get_model().get_sentence_embedding_dimension()
    except Exception:  # noqa: BLE001
        return None


if __name__ == "__main__":
    vecs = embed_texts(["Revenue increased.", "Risks remain elevated."])
    print(f"Generated {len(vecs)} vectors of dim {len(vecs[0])}.")
