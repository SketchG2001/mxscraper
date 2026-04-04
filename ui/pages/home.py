"""Home page — search tab + direct URL tab."""

from __future__ import annotations

import streamlit as st

from api import MXPlayerAPI, extract_seasons
from downloader import selenium_extract_and_resolve


def render(api: MXPlayerAPI):
    tab_search, tab_url = st.tabs(["🔍  Search", "🔗  Direct URL"])

    with tab_search:
        _render_search(api)

    with tab_url:
        _render_direct_url(api)


# ── Search Tab ─────────────────────────────────────────────


def _render_search(api: MXPlayerAPI):
    with st.form("search_form"):
        c_in, c_btn = st.columns([5, 1])
        with c_in:
            query = st.text_input(
                "Search",
                placeholder="Search movies, shows, web series...",
                label_visibility="collapsed",
            )
        with c_btn:
            go = st.form_submit_button("Search", use_container_width=True, type="primary")

    if go and query:
        with st.spinner("Searching MX Player..."):
            results, err = api.search(query)
            st.session_state.search_results = results
            if err:
                st.error(err)

    results = st.session_state.search_results
    if results:
        st.caption(f"Found {len(results)} result{'s' if len(results) != 1 else ''}")
        _render_result_grid(results)
    elif go and query:
        st.info("No results found. Try a different search term.")


def _render_result_grid(results: list[dict]):
    n_cols = 4
    for row_start in range(0, len(results), n_cols):
        cols = st.columns(n_cols, gap="medium")
        for idx, col in enumerate(cols):
            ri = row_start + idx
            if ri >= len(results):
                break
            item = results[ri]
            with col:
                if item.get("image"):
                    st.image(item["image"], use_container_width=True)

                ctype = item.get("type", "")
                badge_cls = {
                    "tvshow": "badge-show",
                    "movie": "badge-movie",
                }.get(ctype, "badge-video")
                badge_text = {
                    "tvshow": "TV Show",
                    "movie": "Movie",
                }.get(ctype, ctype.title() or "Video")

                st.markdown(
                    f'<span class="badge {badge_cls}">{badge_text}</span>'
                    f'<div class="card-title">{item["title"]}</div>',
                    unsafe_allow_html=True,
                )

                meta = []
                if item.get("year"):
                    meta.append(item["year"])
                if item.get("genres"):
                    meta.append(", ".join(item["genres"][:2]))
                if item.get("languages"):
                    meta.append(", ".join(item["languages"][:1]))
                if meta:
                    st.markdown(
                        f'<div class="card-meta">{" · ".join(meta)}</div>',
                        unsafe_allow_html=True,
                    )

                if st.button(
                    "View Details →",
                    key=f"view_{item['id']}_{ri}",
                    use_container_width=True,
                ):
                    st.session_state.selected_content = item
                    st.session_state.page = "detail"
                    st.session_state.seasons = []
                    st.session_state.episodes = []
                    st.session_state.sel_season_idx = 0
                    st.session_state.show_detail = None
                    st.session_state.episodes_season_id = None
                    st.rerun()


# ── Direct URL Tab ─────────────────────────────────────────


def _render_direct_url(api: MXPlayerAPI):
    st.markdown("Paste an MX Player URL to load content info or download directly.")
    url_input = st.text_input(
        "MX Player URL",
        placeholder="https://www.mxplayer.in/show/...",
        label_visibility="collapsed",
    )
    col_api, col_sel = st.columns(2)
    with col_api:
        btn_api = st.button("🔍  Load via API", use_container_width=True)
    with col_sel:
        btn_sel = st.button("🌐  Extract via Browser", use_container_width=True)

    if not url_input or not (btn_api or btn_sel):
        return

    if "mxplayer.in" not in url_input:
        st.error("Please enter a valid MX Player URL (https://www.mxplayer.in/...)")
        return

    if btn_api:
        _load_via_api(api, url_input)
    else:
        selenium_extract_and_resolve(url_input, api)


def _load_via_api(api: MXPlayerAPI, url: str):
    with st.spinner("Resolving URL..."):
        resolved = api.resolve_url(url)

    if resolved and resolved.get("parsed"):
        st.session_state.selected_content = resolved["parsed"]
        st.session_state.show_detail = resolved.get("detail")
        if resolved.get("detail"):
            st.session_state.seasons = extract_seasons(resolved["detail"])
        if resolved.get("episodes"):
            st.session_state.episodes = resolved["episodes"]
        st.session_state.page = "detail"
        st.rerun()
    elif resolved and resolved.get("episodes"):
        st.session_state.episodes = resolved["episodes"]
        first_ep = resolved["episodes"][0]
        st.session_state.selected_content = {
            "id": "", "title": first_ep.get("title", "Episodes"),
            "type": "tvshow", "description": "",
            "image": first_ep.get("image", ""),
            "genres": [], "languages": [], "year": "",
            "publisher": "", "contributors": [],
            "stream_url": "", "drm": False,
            "duration": 0, "sequence": "", "rating": "",
            "shareUrl": "", "firstVideo": None, "container": {},
        }
        st.session_state.page = "detail"
        st.rerun()
    else:
        st.warning(
            "Could not resolve this URL via API. "
            "Try **Extract via Browser** instead."
        )
