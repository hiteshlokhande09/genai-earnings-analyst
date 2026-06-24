"""
Semantic chunking (Sprint 1, Step 4 of the SRS flow).

Wraps LangChain's ``RecursiveCharacterTextSplitter`` to break each filing
section into overlapping, retrieval-sized chunks. Overlap preserves context
across chunk boundaries so that retrieval does not lose information that spans a
split point.
"""

from __future__ import annotations

from typing import Dict, List

from genai_analyst.core import config


def _get_splitter():
    """Construct the recursive text splitter (imported lazily for fast startup)."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def chunk_sections(sections: Dict[str, str]) -> List[dict]:
    """Split each named section into chunks.

    Parameters
    ----------
    sections:
        Mapping of section name to text (from the parser).

    Returns
    -------
    A list of ``{"text": str, "section": str, "chunk_id": int}`` dictionaries.
    The ``Full Document`` fallback section is skipped when named sections exist,
    to avoid duplicating content in the vector store.
    """
    splitter = _get_splitter()
    named = {k: v for k, v in sections.items() if k != "Full Document"}
    source = named if named else sections

    chunks: List[dict] = []
    chunk_id = 0
    for section_name, section_text in source.items():
        for piece in splitter.split_text(section_text):
            piece = piece.strip()
            if piece:
                chunks.append(
                    {"text": piece, "section": section_name, "chunk_id": chunk_id}
                )
                chunk_id += 1
    return chunks
