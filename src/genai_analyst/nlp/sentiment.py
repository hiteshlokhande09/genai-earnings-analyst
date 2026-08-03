"""
sentiment.py
================
Financial Sentiment / Management Tone Analysis (Pipeline Step 8).

Uses FinBERT (ProsusAI/finbert) running fully LOCALLY via HuggingFace
transformers + PyTorch. No API cost. First run downloads ~440 MB and
caches it; subsequent runs are instant.

Produces a per-chunk Positive/Negative/Neutral label with a confidence
score, then aggregates into an overall management tone score in [0, 1]
where 1.0 = maximally positive.
"""

from __future__ import annotations

from typing import Dict, List

from genai_analyst.core import config
_PIPELINE = None  # transformers pipeline singleton


def get_pipeline():
    """Load (once) the FinBERT text-classification pipeline."""
    global _PIPELINE
    if _PIPELINE is None:
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            pipeline,
        )

        print(f"[sentiment] Loading FinBERT '{config.FINBERT_MODEL_NAME}'...")
        tokenizer = AutoTokenizer.from_pretrained(config.FINBERT_MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(
            config.FINBERT_MODEL_NAME
        )
        _PIPELINE = pipeline(
            "text-classification",
            model=model,
            tokenizer=tokenizer,
            truncation=True,
            max_length=512,
        )
    return _PIPELINE


def analyze_chunks(chunks: List[str]) -> List[Dict]:
    """Classify each chunk. Returns list of {label, score, text_preview}."""
    if not chunks:
        return []
    clf = get_pipeline()
    results = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            out = clf(chunk[:2000])[0]  # guard against very long inputs
            results.append(
                {
                    "label": out["label"].capitalize(),
                    "score": round(float(out["score"]), 4),
                    "text_preview": chunk[:120],
                }
            )
        except Exception as exc:  # noqa: BLE001 - never crash on a bad chunk
            print(f"[sentiment] skipped a chunk: {exc}")
    return results


def aggregate_tone(chunk_results: List[Dict]) -> Dict:
    """Aggregate per-chunk sentiment into an overall tone summary.

    Returns:
        {tone_score: float in [0,1], label: str, positive: int,
         negative: int, neutral: int, total: int}
    """
    pos = neg = neu = 0
    weighted = 0.0
    for r in chunk_results:
        label = r["label"].lower()
        conf = r["score"]
        if label == "positive":
            pos += 1
            weighted += conf
        elif label == "negative":
            neg += 1
            weighted -= conf
        else:
            neu += 1
    total = max(pos + neg + neu, 1)
    # Map weighted polarity from [-1, 1] to a [0, 1] tone score.
    raw = weighted / total
    tone_score = round((raw + 1) / 2, 4)

    if tone_score >= 0.6:
        label = "Positive"
    elif tone_score <= 0.4:
        label = "Negative"
    else:
        label = "Neutral"

    return {
        "tone_score": tone_score,
        "label": label,
        "positive": pos,
        "negative": neg,
        "neutral": neu,
        "total": total,
    }


def analyze(chunks: List[str]) -> Dict:
    """Convenience wrapper: per-chunk classification + aggregate."""
    per_chunk = analyze_chunks(chunks)
    summary = aggregate_tone(per_chunk)
    summary["chunks"] = per_chunk
    return summary


if __name__ == "__main__":
    demo = ["Revenue grew strongly and margins expanded.",
            "We face significant competitive and regulatory risks."]
    print(aggregate_tone(analyze_chunks(demo)))
