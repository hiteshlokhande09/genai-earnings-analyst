"""Unit tests for the HTML filing parser (no network required)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from genai_analyst.ingestion import filing_parser


def test_html_to_text_strips_tags():
    html = "<html><body><p>Hello</p><script>ignore()</script></body></html>"
    text = filing_parser.html_to_text(html)
    assert "Hello" in text
    assert "ignore" not in text


def test_clean_text_collapses_whitespace():
    assert filing_parser.clean_text("a   b\n\n c") == "a b c"


def test_segment_sections_always_has_fallback():
    sections = filing_parser.parse_filing("<p>Some filing text here.</p>")
    assert "Full Document" in sections


def test_segment_sections_detects_risk_factors():
    html = (
        "<p>Intro text. Item 1A. Risk Factors The company faces many risks "
        "including market risk and competition.</p>"
    )
    sections = filing_parser.parse_filing(html)
    assert "Risk Factors" in sections
