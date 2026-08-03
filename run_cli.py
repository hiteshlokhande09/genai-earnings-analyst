"""
run_cli.py
==========
Headless command-line runner — useful for testing the pipeline without
launching the Streamlit UI, and for the review demo.

Usage:
    python run_cli.py AAPL 10-K
    python run_cli.py MSFT 10-Q --force
"""
import argparse
from genai_analyst.core import pipeline
def main():
    ap = argparse.ArgumentParser(description="Run the earnings analysis pipeline.")
    ap.add_argument("ticker", help="Stock ticker symbol, e.g. AAPL")
    ap.add_argument("form", nargs="?", default="10-K", choices=["10-K", "10-Q"])
    ap.add_argument("--force", action="store_true", help="Ignore cache, re-analyse")
    args = ap.parse_args()

    result = pipeline.run_analysis(args.ticker, args.form, force=args.force)
    if "error" in result:
        print("ERROR:", result["error"])
        return
    print("\n========== RESULT ==========")
    print("Company :", result["filing"]["company"])
    print("Form    :", result["filing"]["form"], result["filing"]["filing_date"])
    print("Chunks  :", result.get("n_chunks"))
    print("Tone    :", result["tone"]["label"], result["tone"]["tone_score"])
    print("Signal  :", result["signal"]["classification"], result["signal"]["score"])
    print("PDF     :", result["pdf_path"])
    print("Summary :", result["summary"][:300])


if __name__ == "__main__":
    main()
