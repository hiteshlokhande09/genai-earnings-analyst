"""
landing.py
==========
Marketing landing page shown before the analysis tool.

Currency
--------
All customer-facing prices on this page are quoted in Indian Rupees (INR).
"""

from __future__ import annotations

import streamlit as st

from genai_analyst.core import config


# ---- Pricing (INR) --------------------------------------------------------- #
PRICING = {
    "student": {"amount": "₹0", "per": "forever"},
    "analyst": {"amount": "₹2,499", "per": "per month"},
    "desk": {"amount": "₹7,999", "per": "per month"},
}
API_COST_PER_FILING = "₹0"
BUY_LABEL = f"Buy — {PRICING['analyst']['amount']}/mo"


# ---- Palette (dark only) --------------------------------------------------- #
_DARK = {
    "page": "#0A1628", "hero1": "#0A1628", "hero2": "#12233D", "line": "#24374F",
    "paper": "#F5F3EC", "lede": "#C7D2E0", "muted": "#7C8DA4", "gold": "#C9A227",
    "ledger": "#2FBE8F", "alert": "#E8863B", "sec_title": "#F5F3EC",
    "step_body": "#A9B7C9", "card": "#12233D", "card_feat": "#16294A",
    "card_border": "#24374F", "card_text": "#F5F3EC", "li_border": "rgba(255,255,255,.10)",
}


def _css(p: dict, feat_text: str) -> str:
    return f"""
<style>
.stApp {{ background: {p['page']}; }}
header, footer {{visibility:hidden;}}
.block-container{{padding-top:1.2rem; max-width:1100px;}}
.hero{{
  background: linear-gradient(160deg,{p['hero1']} 0%,{p['hero2']} 100%);
  border:1px solid {p['line']}; border-radius:18px;
  padding:52px 48px 42px; color:#F5F3EC;
}}
.eyebrow{{font-family:ui-monospace,monospace; font-size:12px; letter-spacing:.28em;
  text-transform:uppercase; color:{p['gold']}; margin-bottom:16px;}}
.hero h1{{font-family:Georgia,serif; font-size:52px; line-height:1.05; font-weight:600;
  margin:0 0 18px; color:#F5F3EC;}}
.hero h1 em{{color:{p['gold']}; font-style:italic;}}
.hero p.lede{{font-size:18px; line-height:1.55; color:#C7D2E0; max-width:620px; margin:0;}}
.stats{{display:flex; gap:40px; margin-top:32px; border-top:1px solid {p['line']}; padding-top:22px;}}
.stat .num{{font-family:ui-monospace,monospace; font-size:30px; color:#F5F3EC; font-weight:600;}}
.stat .lbl{{font-size:12px; color:#9FB0C4; letter-spacing:.08em; text-transform:uppercase; margin-top:4px;}}
.sec-title{{font-family:Georgia,serif; font-size:30px; color:{p['sec_title']}; margin:0 0 24px; font-weight:600;}}
.step{{border-left:2px solid {p['ledger']}; padding:4px 0 18px 20px; position:relative;}}
.step h4{{font-family:ui-monospace,monospace; font-size:14px; color:{p['sec_title']}; margin:0 0 4px;}}
.step p{{font-size:14px; color:{p['step_body']}; margin:0;}}
.price-card{{border:1px solid {p['card_border']}; border-radius:14px; padding:26px;
  background:{p['card']}; color:{p['card_text']}; height:100%;}}
.price-card.feat{{border:1.5px solid {p['gold']}; background:{p['card_feat']}; color:{feat_text};}}
.price-card h3{{font-family:ui-monospace,monospace; font-size:13px; letter-spacing:.18em;
  text-transform:uppercase; margin:0 0 8px; color:{p['gold']};}}
.price-card .amt{{font-family:Georgia,serif; font-size:40px; font-weight:600; margin:0 0 4px;}}
.price-card .per{{font-size:13px; color:{p['muted']};}}
.price-card ul{{list-style:none; padding:16px 0 0; margin:0;}}
.price-card li{{font-size:14px; padding:7px 0; border-top:1px solid {p['li_border']};}}
.disc{{font-size:12px; color:{p['muted']}; text-align:center; margin-top:40px;
  padding-top:20px; border-top:1px solid {p['line']};}}
</style>
"""


def _go_to_app():
    st.session_state["view"] = "app"


def render():
    """Render the landing page (dark theme only)."""
    # Apply dark palette
    st.markdown(_css(_DARK, feat_text="#F5F3EC"), unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="hero">
          <div class="eyebrow">SEC Filing Intelligence</div>
          <h1>Read a 200-page filing<br>in <em>ninety seconds</em>.</h1>
          <p class="lede">
            Enter a ticker. We pull the company's latest 10-K or 10-Q straight
            from SEC EDGAR, retrieve the passages that matter with RAG, and hand
            you an executive summary, risk factors, management tone, KPIs and a
            Bull/Bear signal.
          </p>
          <div class="stats">
            <div class="stat"><div class="num">17</div><div class="lbl">Pipeline stages</div></div>
            <div class="stat"><div class="num">{API_COST_PER_FILING}</div><div class="lbl">API cost / filing</div></div>
            <div class="stat"><div class="num">&lt;90s</div><div class="lbl">Per analysis</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        st.button("Try it now  →", type="primary", use_container_width=True,
                  on_click=_go_to_app, key="cta_try")
    with c2:
        st.button(BUY_LABEL, use_container_width=True,
                  on_click=_go_to_app, key="cta_buy")

    st.markdown('<div class="sec-title">From ticker to thesis, in one pass.</div>',
                unsafe_allow_html=True)
    for title, body in [
        ("01 · Ingest", "Fetch the latest 10-K / 10-Q from SEC EDGAR and parse the filing HTML into clean, named sections."),
        ("02 · Retrieve (RAG)", "Chunk, embed with Sentence Transformers, store in ChromaDB, and retrieve the Top-K passages relevant to each question."),
        ("03 · Analyse", "FinBERT scores management tone; Meta Llama 3 writes the summary, extracts risk factors and reads forward guidance."),
        ("04 · Decide", "A Bull/Bear signal combines KPIs, tone and guidance — with charts and a downloadable PDF report."),
    ]:
        st.markdown(f'<div class="step"><h4>{title}</h4><p>{body}</p></div>',
                    unsafe_allow_html=True)

    st.markdown('<div class="sec-title">Start free. Upgrade when you scale.</div>',
                unsafe_allow_html=True)
    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown(f"""<div class="price-card"><h3>Student</h3>
            <div class="amt">{PRICING['student']['amount']}</div>
            <div class="per">{PRICING['student']['per']}</div>
            <ul><li>5 filings / day</li><li>Summary · risks · guidance</li>
            <li>FinBERT tone analysis</li><li>Local SQLite history</li></ul></div>""",
            unsafe_allow_html=True)
    with p2:
        st.markdown(f"""<div class="price-card feat"><h3>Analyst</h3>
            <div class="amt">{PRICING['analyst']['amount']}</div>
            <div class="per">{PRICING['analyst']['per']}</div>
            <ul><li>Unlimited filings</li><li>Bull/Bear signal + charts</li>
            <li>PDF investor reports</li><li>KPI comparison</li></ul></div>""",
            unsafe_allow_html=True)
    with p3:
        st.markdown(f"""<div class="price-card"><h3>Desk</h3>
            <div class="amt">{PRICING['desk']['amount']}</div>
            <div class="per">{PRICING['desk']['per']}</div>
            <ul><li>Everything in Analyst</li><li>Team workspace</li>
            <li>API access</li><li>Priority support</li></ul></div>""",
            unsafe_allow_html=True)

    st.write("")
    b1, _, _ = st.columns([1, 1, 3])
    with b1:
        st.button("Start free  →", type="primary", use_container_width=True,
                  on_click=_go_to_app, key="cta_bottom")

    st.markdown(f'<div class="disc">{config.DISCLAIMER}</div>', unsafe_allow_html=True)
