"""
Root launcher for the Streamlit dashboard.

Adds the ``src`` directory to the import path and runs the dashboard. This lets
the project use a clean ``src/`` layout while still being launched with the
simple command ``streamlit run app.py``.
"""

import os
import sys

# Make the `src` package importable.
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from genai_analyst.dashboard import main

main()
