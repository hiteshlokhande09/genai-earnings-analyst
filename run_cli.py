"""
Headless command-line runner for the Sprint 1 pipeline.

Usage:
    python run_cli.py AAPL 10-K

Prints the executive summary, tone, risks and guidance to the terminal. Useful
for testing the pipeline without launching the Streamlit dashboard.
"""

import os
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from genai_analyst.core import pipeline


def _progress(message, fraction):
    print(f"[{int(fraction * 100):3d}%] {message}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_cli.py TICKER [FORM_TYPE]")
        sys.exit(1)

    ticker = sys.argv[1].upper()  # normalise ticker to uppercase, e.g. 'aapl' -> 'AAPL'
    form_type = sys.argv[2] if len(sys.argv) > 2 else "10-K"

    result = pipeline.run_analysis(ticker, form_type, progress=_progress)

    print("\n" + "=" * 60)
    if "error" in result:
        print("ERROR:", result["error"])
        sys.exit(1)

    filing = result["filing"]
    print(f"{filing['company']} ({filing['ticker']}) — {filing['form']} "
          f"filed {filing['filing_date']}")
    print("=" * 60)
    print("\nEXECUTIVE SUMMARY\n", result["summary"])
    print("\nTONE\n", result["tone"])
    print("\nRISK FACTORS")
    for risk in result["risks"]:
        print(" -", risk)
    print("\nFORWARD GUIDANCE\n", result["guidance"])


if __name__ == "__main__":
    main()
