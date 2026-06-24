"""Unit tests for FinBERT tone aggregation (no model required)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from genai_analyst.nlp import sentiment


def test_aggregate_tone_empty():
    result = sentiment.aggregate_tone([])
    assert result["label"] == "N/A"
    assert result["tone_score"] == 0.5


def test_aggregate_tone_positive():
    results = [
        {"label": "positive", "score": 0.9},
        {"label": "positive", "score": 0.8},
        {"label": "neutral", "score": 0.7},
    ]
    agg = sentiment.aggregate_tone(results)
    assert agg["label"] == "Positive"
    assert agg["tone_score"] > 0.5
    assert agg["positive"] == 2
