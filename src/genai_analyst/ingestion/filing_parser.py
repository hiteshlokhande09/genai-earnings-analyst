"""
HTML parsing and text cleaning (Sprint 1, Steps 3-4 of the SRS flow).

Converts the raw filing HTML into clean plain text and segments it into the
named sections an analyst cares about (Risk Factors, MD&A, Financial
Statements). Section-aware segmentation improves downstream RAG retrieval
because chunks stay within a coherent topic.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

# Regular expressions that locate the standard 10-K / 10-Q item headings.
_SECTION_PATTERNS = {
    "Risk Factors": re.compile(r"item\s*1a[.\s]+risk\s+factors", re.IGNORECASE),
    "MD&A": re.compile(
        r"item\s*7[.\s]+management.s\s+discussion", re.IGNORECASE
    ),
    "Financial Statements": re.compile(
        r"item\s*8[.\s]+financial\s+statements", re.IGNORECASE
    ),
}


def html_to_text(html: str) -> str:
    """Strip tags, scripts and styles from filing HTML, returning plain text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator=" ")


def clean_text(text: str) -> str:
    """Collapse whitespace and remove obvious boilerplate artefacts."""
    text = re.sub(r"\s+", " ", text)          # collapse runs of whitespace
    text = re.sub(r"\u00a0", " ", text)       # non-breaking spaces
    return text.strip()


def segment_sections(text: str) -> dict[str, str]:
    """Split cleaned text into named sections.

    Returns a mapping of section name to its text. A ``Full Document`` entry is
    always included as a fallback so retrieval never has an empty corpus.
    """
    sections: dict[str, str] = {"Full Document": text}

    # Record the start offset of each detected section heading.
    offsets: list[tuple[int, str]] = []
    for name, pattern in _SECTION_PATTERNS.items():
        match = pattern.search(text)
        if match:
            offsets.append((match.start(), name))

    offsets.sort()
    for position, (start, name) in enumerate(offsets):
        end = offsets[position + 1][0] if position + 1 < len(offsets) else len(text)
        section_text = text[start:end].strip()
        if section_text:
            sections[name] = section_text

    return sections


def parse_filing(html: str) -> dict[str, str]:
    """Full parse entry point: HTML -> cleaned, section-segmented text."""
    text = clean_text(html_to_text(html))
    return segment_sections(text)
