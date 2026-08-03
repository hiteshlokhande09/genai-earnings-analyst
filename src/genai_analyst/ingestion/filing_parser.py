"""
parser.py
=========
HTML Parsing, Text Extraction & Cleaning (Pipeline Steps 3-4).

Responsibilities:
    * Strip HTML to clean, readable plain text using BeautifulSoup4.
    * Remove boilerplate (scripts, styles, tables of XBRL tags, page numbers).
    * Identify and segment the key narrative sections of a 10-Q / 10-K:
        - MD&A (Management's Discussion & Analysis)
        - Risk Factors
        - Financial Statements (narrative notes)

spaCy is used opportunistically for sentence-aware cleaning when installed,
but the module degrades gracefully to regex-only cleaning if it is absent.
"""

from __future__ import annotations

import re
from typing import Dict

from bs4 import BeautifulSoup

from genai_analyst.core import config
# Optional spaCy: improves sentence segmentation but is not required.
try:
    import spacy

    try:
        _NLP = spacy.load("en_core_web_sm", disable=["ner", "tagger", "lemmatizer"])
    except OSError:
        _NLP = None  # model not downloaded
except ImportError:
    spacy = None  # type: ignore
    _NLP = None


# --------------------------------------------------------------------------- #
# Raw HTML -> clean text
# --------------------------------------------------------------------------- #
def html_to_text(html: str) -> str:
    """Convert filing HTML into clean plain text."""
    soup = BeautifulSoup(html, "html.parser")

    # Drop non-content elements.
    for tag in soup(["script", "style", "head", "meta", "link", "title"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    return clean_text(text)


def clean_text(text: str) -> str:
    """Normalise whitespace, strip page artefacts and non-breaking chars."""
    text = text.replace("\xa0", " ").replace("\u200b", "")
    # Collapse runs of whitespace.
    text = re.sub(r"[ \t]+", " ", text)
    # Remove standalone page-number lines.
    text = re.sub(r"\n\s*\d+\s*\n", "\n", text)
    # Collapse 3+ newlines into a paragraph break.
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]  # drop empty lines
    return "\n".join(lines).strip()


# --------------------------------------------------------------------------- #
# Section segmentation
# --------------------------------------------------------------------------- #
# Heading patterns commonly used in SEC filings. Order matters: we scan the
# document and slice between matched headings.
_SECTION_PATTERNS = {
    "Risk Factors": re.compile(r"item\s*1a\.?\s*risk factors", re.IGNORECASE),
    "MD&A": re.compile(
        r"item\s*[27]\.?\s*management.?s discussion and analysis", re.IGNORECASE
    ),
    "Financial Statements": re.compile(
        r"item\s*[18]\.?\s*financial statements", re.IGNORECASE
    ),
}


def segment_sections(text: str) -> Dict[str, str]:
    """Split cleaned filing text into the target narrative sections.

    Returns a dict mapping section name -> section text. Sections that cannot
    be located fall back to an empty string (graceful degradation).
    """
    matches = []
    for name, pattern in _SECTION_PATTERNS.items():
        for m in pattern.finditer(text):
            matches.append((m.start(), name))
    matches.sort()

    sections: Dict[str, str] = {name: "" for name in config.TARGET_SECTIONS}
    if not matches:
        # No headings found -> treat whole document as one MD&A blob.
        sections["MD&A"] = text
        return sections

    for idx, (start, name) in enumerate(matches):
        end = matches[idx + 1][0] if idx + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()
        # Keep the longest match per section (skips the TOC reference).
        if len(chunk) > len(sections.get(name, "")):
            sections[name] = chunk

    # If nothing meaningful captured, keep full text as fallback context.
    if all(len(v) < 200 for v in sections.values()):
        sections["MD&A"] = text
    return sections


def parse_filing(html: str) -> Dict[str, str]:
    """High-level entry point: HTML -> {section_name: section_text, 'full': ...}."""
    text = html_to_text(html)
    sections = segment_sections(text)
    sections["full"] = text
    return sections


if __name__ == "__main__":
    sample = "<html><body><h1>Item 1A. Risk Factors</h1><p>We face risks.</p>" \
             "<h1>Item 7. Management's Discussion and Analysis</h1>" \
             "<p>Revenue grew.</p></body></html>"
    parsed = parse_filing(sample)
    for k, v in parsed.items():
        print(f"--- {k} ({len(v)} chars) ---\n{v[:120]}\n")
