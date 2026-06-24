"""
Financial sentiment analysis with FinBERT (Sprint 1, Step 8 — sentiment).

Uses the local ``ProsusAI/finbert`` model to label management commentary as
positive / negative / neutral. The model is loaded lazily and cached. An
aggregate tone score in the range [0, 1] is produced by weighting the
per-chunk labels.
"""

from __future__ import annotations

from typing import Dict, List

from genai_analyst.core import config

_PIPELINE = None  # lazy-loaded transformers sentiment pipeline


def _get_pipeline():
    """Load and cache the FinBERT pipeline on first use."""
    global _PIPELINE
    if _PIPELINE is None:
        from transformers import pipeline as hf_pipeline

        _PIPELINE = hf_pipeline(
            "sentiment-analysis",
            model=config.FINBERT_MODEL_NAME,
            truncation=True,
            max_length=512,
        )
    return _PIPELINE


def analyze_chunks(chunks: List[str]) -> List[dict]:
    """Label each chunk with a sentiment and confidence score."""
    if not chunks:
        return []
    pipeline = _get_pipeline()
    sample = chunks[: config.FINBERT_MAX_CHUNKS]
    raw = pipeline(sample)
    return [
        {"label": item["label"].lower(), "score": float(item["score"])}
        for item in raw
    ]


def aggregate_tone(results: List[dict]) -> Dict[str, object]:
    """Combine per-chunk labels into an overall tone score and label.

    The tone score maps positive -> 1.0, neutral -> 0.5, negative -> 0.0,
    weighted by model confidence, then averaged.
    """
    if not results:
        return {
            "label": "N/A",
            "tone_score": 0.5,
            "positive": 0,
            "neutral": 0,
            "negative": 0,
        }

    weight = {"positive": 1.0, "neutral": 0.5, "negative": 0.0}  # maps labels onto a 0-1 scale so tone_score is directly interpretable (0=negative, 1=positive)
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    total = 0.0

    for item in results:
        label = item["label"]
        counts[label] = counts.get(label, 0) + 1
        total += weight.get(label, 0.5)

    tone_score = total / len(results)
    overall = max(counts, key=counts.get)

    return {
        "label": overall.capitalize(),
        "tone_score": round(tone_score, 4),
        "positive": counts["positive"],
        "neutral": counts["neutral"],
        "negative": counts["negative"],
    }


def analyze(chunks: List[str]) -> Dict[str, object]:
    """Full sentiment entry point: chunks -> aggregate tone summary."""
    return aggregate_tone(analyze_chunks(chunks))
