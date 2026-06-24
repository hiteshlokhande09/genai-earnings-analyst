"""Unit tests for the RAG chunker (no network / no model required)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from genai_analyst.rag import chunker


def test_chunk_sections_produces_chunks():
    sections = {"MD&A": "word " * 2000}  # long enough to split
    chunks = chunker.chunk_sections(sections)
    assert len(chunks) >= 1
    assert all("text" in c and "section" in c for c in chunks)


def test_chunk_sections_skips_full_document_when_named_exist():
    sections = {"Full Document": "x " * 100, "Risk Factors": "risk " * 100}
    chunks = chunker.chunk_sections(sections)
    assert all(c["section"] == "Risk Factors" for c in chunks)


def test_empty_sections_return_empty():
    assert chunker.chunk_sections({}) == []
