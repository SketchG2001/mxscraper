import uuid
import streamlit as st
from dotenv import load_dotenv

from api import MXPlayerAPI
from config import SESSION_DEFAULTS
from proxy import start_proxy
from ui.styles import inject_css
from ui.components import render_download_bar, render_download_complete, render_download_error, render_header, render_footer
from ui.pages import detail, home

load_dotenv()

# ── Page config (must be first Streamlit call) ────────────

st.set_page_config(page_title="MX Player Scraper", page_icon="🎬", layout="wide")

# ── Start CORS proxy (once per process) ──────────────────

start_proxy()

# ── Session state init ────────────────────────────────────

for _k, _v in SESSION_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v
if st.session_state.userid is None:
    st.session_state.userid = str(uuid.uuid4())

# ── Global CSS ────────────────────────────────────────────

inject_css()

# ── Header ────────────────────────────────────────────────

render_header()

# ── API client ────────────────────────────────────────────

api = MXPlayerAPI(st.session_state.userid)

# ── Download overlays (visible on every page) ─────────────

render_download_bar()
render_download_complete()
render_download_error()

# ── Page routing ──────────────────────────────────────────

if st.session_state.page == "detail" and st.session_state.selected_content:
    detail.render(api)
elif st.session_state.page == "home":
    home.render(api)

# ── Footer ────────────────────────────────────────────────

render_footer()
