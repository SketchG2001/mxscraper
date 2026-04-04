"""Inject global CSS into the Streamlit app."""

import streamlit as st

_CSS = """
<style>
.app-header {
    background: linear-gradient(135deg, #0d253f 0%, #01b4e4 100%);
    padding: 2rem 2.5rem; border-radius: 12px; margin-bottom: 1.5rem; color: white;
}
.app-header h1 { margin: 0; font-size: 2rem; font-weight: 700; }
.app-header p  { margin: 0.3rem 0 0; opacity: 0.85; font-size: 1rem; }
.badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
}
.badge-show  { background: #01b4e4; color: white; }
.badge-movie { background: #e91e63; color: white; }
.badge-video { background: #ff9800; color: white; }
.card-title {
    font-weight: 600; font-size: 0.95rem; margin: 0.5rem 0 0.2rem;
    line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2;
    -webkit-box-orient: vertical; overflow: hidden;
}
.card-meta { font-size: 0.78rem; opacity: 0.7; margin-bottom: 0.5rem; }
.ep-num {
    font-weight: 700; font-size: 1rem; color: #01b4e4;
    min-width: 2.5rem; text-align: center;
}
.detail-title { font-size: 1.6rem; font-weight: 700; margin-bottom: 0.5rem; }
.detail-desc  { opacity: 0.8; line-height: 1.6; font-size: 0.92rem; }
.detail-meta  { font-size: 0.85rem; opacity: 0.65; margin-top: 0.5rem; }
.app-footer {
    text-align: center; padding: 1.5rem; opacity: 0.5;
    font-size: 0.85rem; margin-top: 2rem;
}
.dl-controls { margin-top: 0.5rem; }
.stButton > button { border-radius: 8px; }
div[data-testid="stImage"] img { border-radius: 8px; }
/* episode card inside expander */
.ep-card-header {
    display: flex; align-items: center; gap: 0.5rem;
}
.ep-card-header .ep-num {
    min-width: 2rem; font-weight: 700; color: #01b4e4;
}
.ep-card-actions {
    display: flex; gap: 0.5rem; align-items: center;
    flex-wrap: wrap; margin-top: 0.5rem;
}
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)
