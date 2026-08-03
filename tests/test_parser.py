"""Unit tests for the HTML filing parser (no network required)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from genai_analyst.ingestion import filing_parser


def test_html_to_text_strips_tags():
    html = "<html><body><p>Hello</p><script>bad()</script></body></html>"
    text = parser.html_to_text(html) if hasattr(parser, "html_to_text") else ""
    assert "Hello" in text
    assert "bad" not in text


def test_parse_filing_returns_sections():
    sections = parser.parse_filing("<p>Item 1A. Risk Factors The company faces risks.</p>")
    assert isinstance(sections, dict)
    assert len(sections) >= 1
