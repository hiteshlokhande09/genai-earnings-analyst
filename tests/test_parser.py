"""Unit tests for the HTML filing parser (no network required)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from genai_analyst.ingestion import filing_parser


def test_html_to_text_strips_tags():
    """HTML tags are removed; script content is excluded."""
    html = "<html><body><p>Hello</p><script>bad()</script></body></html>"
    text = filing_parser.html_to_text(html)
    assert "Hello" in text
    assert "bad" not in text


def test_html_to_text_returns_string():
    """html_to_text always returns a string."""
    result = filing_parser.html_to_text("<p>Test</p>")
    assert isinstance(result, str)


def test_parse_filing_returns_dict():
    """parse_filing returns a dict with at least one section."""
    sections = filing_parser.parse_filing(
        "<p>Item 1A. Risk Factors The company faces significant risks.</p>"
    )
    assert isinstance(sections, dict)
    assert len(sections) >= 1


def test_parse_filing_has_full_key():
    """parse_filing always includes a 'full' fallback key."""
    sections = filing_parser.parse_filing("<p>Some filing content here.</p>")
    assert "full" in sections


def test_clean_text_removes_whitespace():
    """clean_text collapses multiple spaces and newlines."""
    dirty = "Revenue   grew\n\n\nstrongly   this   quarter."
    result = filing_parser.clean_text(dirty)
    assert "  " not in result


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in tests:
        try:
            fn(); print(f"PASS  {fn.__name__}"); passed += 1
        except Exception as e:
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")