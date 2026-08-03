"""
app.py — root launcher
======================
Adds src/ to the path, sets the page config once, and routes between the
landing page and the analysis dashboard using session state.

Run with:  streamlit run app.py
"""

import os
import sys

# Make the src/ package importable.
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import streamlit as st

# Must be the first Streamlit command in the whole app.
st.set_page_config(
    page_title="GenAI Financial Earnings Report Analyst",
    page_icon="📊",
    layout="wide",
)

# Initialise navigation state before anything reads it.
if "view" not in st.session_state:
    st.session_state["view"] = "landing"


def main():
    view = st.session_state.get("view", "landing")
    if view == "landing":
        from genai_analyst import landing
        landing.render()
    else:
        from genai_analyst import dashboard
        dashboard.main()


main()
