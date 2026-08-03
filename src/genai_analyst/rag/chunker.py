"""
chunker.py
==========
Semantic Chunking of filing text (Pipeline Step 4).

Splits the cleaned filing sections into ~500-word overlapping chunks using
LangChain's RecursiveCharacterTextSplitter, tagging each chunk with the source
section it came from. The resulting chunks are consumed by ``indexer.py``,
which embeds and stores them in ChromaDB.
"""

from __future__ import annotations

from typing import Dict, List

from genai_analyst.core import config


def _get_splitter():
    """Return a LangChain RecursiveCharacterTextSplitter (~500-word chunks)."""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain.text_splitter import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def chunk_sections(sections: Dict[str, str]) -> List[dict]:
    """Split each target section into chunks, tagging the source section.

    Returns a list of {text, section} dicts (the 'full' key is skipped to
    avoid duplicating content already covered by the named sections).
    """
    splitter = _get_splitter()
    chunks: List[dict] = []
    named = [s for s in sections if s != "full"]
    used_named_content = any(len(sections.get(s, "")) > 200 for s in named)

    source_items = (
        [(s, sections[s]) for s in named]
        if used_named_content
        else [("full", sections.get("full", ""))]
    )

    for section_name, text in source_items:
        if not text or len(text) < 50:
            continue
        for piece in splitter.split_text(text):
            piece = piece.strip()
            if piece:
                chunks.append({"text": piece, "section": section_name})
    return chunks


if __name__ == "__main__":
    demo_sections = {
        "MD&A": "Revenue grew strongly. " * 200,
        "Risk Factors": "We face competitive risks. " * 200,
        "full": "",
    }
    print("Chunks produced:", len(chunk_sections(demo_sections)))
