import streamlit as st
CSS = """
<style>
.stApp { background: #0a0612; color: #fff; }
h1, h2, h3, h4 { color: #fff !important; }
.metric-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    padding: 1rem 1.25rem; border-radius: 14px;
}
.metric-card .lbl { font-size:.72rem; letter-spacing:.2em;
    text-transform:uppercase; color:#f0abfc; }
.metric-card .val { font-size:1.9rem; font-weight:700; color:#fff; margin-top:.25rem; }
.metric-card .sub { font-size:.72rem; color:rgba(255,255,255,.5); margin-top:.15rem; }
.eyebrow { font-family: ui-monospace, monospace; font-size:.72rem;
    color:#e879f9; letter-spacing:.25em; text-transform:uppercase; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

PLOTLY_TEMPLATE = "plotly_dark"
ACCENT = "#e879f9"
ACCENT2 = "#38bdf8"
ACCENT3 = "#f472b6"
