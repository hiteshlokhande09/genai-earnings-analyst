"""
landing.py
==========
Marketing landing page shown before the analysis tool.

Includes a visible System / Light / Dark theme selector. The choice is stored
in st.session_state["landing_theme"]:
  * "Dark"   -> dark navy palette (default, the brand look)
  * "Light"  -> light paper palette
  * "System" -> follows the browser's prefers-color-scheme

"Try it now" and "Buy" switch the app into the analysis dashboard.

Currency
--------
All customer-facing prices on this page are quoted in Indian Rupees (INR).
Prices are defined once in ``PRICING`` below so they can be changed in a single
place. Note these are product price points, not converted SEC filing figures —
financial data inside the dashboard continues to be shown in the currency
reported in the filing's XBRL data.
"""

from __future__ import annotations

import streamlit as st

from genai_analyst.core import config


# ---- Pricing (INR) --------------------------------------------------------- #
# Amounts are pre-formatted with the rupee sign and Indian digit grouping.
PRICING = {
    "student": {"amount": "₹0", "per": "forever"},
    "analyst": {"amount": "₹2,499", "per": "per month"},
    "desk": {"amount": "₹7,999", "per": "per month"},
}
# Shown on the hero stat strip and the "Buy" button.
API_COST_PER_FILING = "₹0"
BUY_LABEL = f"Buy — {PRICING['analyst']['amount']}/mo"


# ---- Palettes -------------------------------------------------------------- #
_DARK = {
    "page": "#0A1628", "hero1": "#0A1628", "hero2": "#12233D", "line": "#24374F",
    "paper": "#F5F3EC", "lede": "#C7D2E0", "muted": "#7C8DA4", "gold": "#C9A227",
    "ledger": "#2FBE8F", "alert": "#E8863B", "sec_title": "#F5F3EC",
    "step_body": "#A9B7C9", "card": "#12233D", "card_feat": "#16294A",
    "card_border": "#24374F", "card_text": "#F5F3EC", "li_border": "rgba(255,255,255,.10)",
}
_LIGHT = {
    "page": "#F5F3EC", "hero1": "#0A1628", "hero2": "#12233D", "line": "#D8D2C4",
    "paper": "#F5F3EC", "lede": "#C7D2E0", "muted": "#6B7A8F", "gold": "#B08D1E",
    "ledger": "#0E7C5A", "alert": "#C2410C", "sec_title": "#0A1628",
    "step_body": "#45566B", "card": "#FFFFFF", "card_feat": "#0A1628",
    "card_border": "#E2DDD0", "card_text": "#0A1628", "li_border": "rgba(0,0,0,.06)",
}


def _css(p: dict, feat_text: str) -> str:
    return f"""
<style>
.stApp {{ background: {p['page']}; }}
header, footer {{visibility:hidden;}}
.block-container{{padding-top:1.2rem; max-width:1100px;}}

.hero{{
  background:
    radial-gradient(1200px 400px at 80% -10%, rgba(201,162,39,0.10), transparent),
    linear-gradient(160deg,{p['hero1']} 0%,{p['hero2']} 100%);
  border:1px solid {p['line']}; border-radius:18px;
  padding:52px 48px 42px; color:#F5F3EC; overflow:hidden;
}}
.tape{{font-family:ui-monospace,Menlo,monospace; font-size:12px; letter-spacing:.14em;
  color:{p['ledger']}; border-bottom:1px dashed {p['line']};
  padding-bottom:14px; margin-bottom:26px; white-space:nowrap; overflow:hidden;}}
.eyebrow{{font-family:ui-monospace,monospace; font-size:12px; letter-spacing:.28em;
  text-transform:uppercase; color:{p['gold']}; margin-bottom:16px;}}
.hero h1{{font-family:Georgia,serif; font-size:52px; line-height:1.05; font-weight:600;
  margin:0 0 18px; letter-spacing:-.015em; color:#F5F3EC;}}
.hero h1 em{{color:{p['gold']}; font-style:italic;}}
.hero p.lede{{font-size:18px; line-height:1.55; color:#C7D2E0; max-width:620px; margin:0;}}
.stats{{display:flex; gap:40px; margin-top:32px; border-top:1px solid {p['line']}; padding-top:22px;}}
.stat .num{{font-family:ui-monospace,monospace; font-size:30px; color:#F5F3EC; font-weight:600;}}
.stat .lbl{{font-size:12px; color:#9FB0C4; letter-spacing:.08em; text-transform:uppercase; margin-top:4px;}}

.sec-eyebrow{{font-family:ui-monospace,monospace; font-size:12px; letter-spacing:.24em;
  text-transform:uppercase; color:{p['alert']}; margin:48px 0 8px;}}
.sec-title{{font-family:Georgia,serif; font-size:30px; color:{p['sec_title']}; margin:0 0 24px; font-weight:600;}}

.step{{border-left:2px solid {p['ledger']}; padding:4px 0 18px 20px; position:relative;}}
.step::before{{content:""; position:absolute; left:-6px; top:6px; width:10px; height:10px;
  border-radius:50%; background:{p['ledger']};}}
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

/* System mode: follow the browser's dark preference for the page background */
</style>
"""


def _system_css() -> str:
    # When "System" is chosen, use a media query so the page background follows
    # the OS/browser preference. Cards/hero stay branded; only the page flips.
    return """
<style>
@media (prefers-color-scheme: light) { .stApp { background: #F5F3EC; }
  .sec-title, .step h4 { color: #0A1628 !important; } .step p { color:#45566B !important; } }
@media (prefers-color-scheme: dark)  { .stApp { background: #0A1628; }
  .sec-title, .step h4 { color: #F5F3EC !important; } .step p { color:#A9B7C9 !important; } }
</style>
"""


def _go_to_app():
    st.session_state["view"] = "app"


def render():
    """Render the landing page with a System/Light/Dark selector."""
    if "landing_theme" not in st.session_state:
        st.session_state["landing_theme"] = "Dark"

    # ---- Theme selector (top-right) ----
    _, sel_col = st.columns([3, 1])
    with sel_col:
        choice = st.radio(
            "Theme", ["System", "Light", "Dark"],
            index=["System", "Light", "Dark"].index(st.session_state["landing_theme"]),
            horizontal=True, label_visibility="collapsed", key="landing_theme_radio",
        )
        st.session_state["landing_theme"] = choice

    # Apply the selected palette
    if choice == "Light":
        st.markdown(_css(_LIGHT, feat_text="#F5F3EC"), unsafe_allow_html=True)
    elif choice == "Dark":
        st.markdown(_css(_DARK, feat_text="#F5F3EC"), unsafe_allow_html=True)
    else:  # System — base on dark palette, then let media query flip the page
        st.markdown(_css(_DARK, feat_text="#F5F3EC"), unsafe_allow_html=True)
        st.markdown(_system_css(), unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="hero">
          <div class="tape">
            &#9650; AAPL 10-K BULLISH 0.74 &nbsp;•&nbsp;
            &#9660; NFLX 10-Q BEARISH 0.38 &nbsp;•&nbsp;
            &#9650; MSFT 10-K BULLISH 0.81 &nbsp;•&nbsp;
            &#9679; JPM 10-K NEUTRAL 0.55 &nbsp;•&nbsp;
            &#9650; KO 10-K BULLISH 0.69
          </div>
          <div class="eyebrow">SEC Filing Intelligence</div>
          <h1>Read a 200-page filing<br>in <em>ninety seconds</em>.</h1>
          <p class="lede">
            Enter a ticker. We pull the company's latest 10-K or 10-Q straight
            from SEC EDGAR, retrieve the passages that matter with RAG, and hand
            you an executive summary, risk factors, management tone, KPIs and a
            Bull/Bear signal — every figure traceable to the filing.
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
                  on_click=_go_to_app, key="cta_buy",
                  help="Starts your analysis session")

    st.markdown('<div class="sec-eyebrow">How it works</div>', unsafe_allow_html=True)
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

    st.markdown('<div class="sec-eyebrow">Pricing</div>', unsafe_allow_html=True)
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