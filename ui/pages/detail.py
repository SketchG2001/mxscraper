from __future__ import annotations

import streamlit as st

from api import MXPlayerAPI, extract_seasons, stream_url as parse_stream_url
from downloader import start_download
from ui.player import render_player
from utils import format_duration, go_home


# ── Quality label helpers ─────────────────────────────────

_QUALITY_LABELS = {
    "hls_high": "HLS High",
    "hls_main": "HLS Medium",
    "hls_base": "HLS Low",
    "dash_high": "DASH High",
    "dash_main": "DASH Medium",
    "dash_base": "DASH Low",
}


def _quality_choices(stream_options: dict) -> list[tuple[str, str]]:
    """Return [(label, url), ...] from stream options, best first."""
    choices = []
    for key in ("hls_high", "hls_main", "hls_base", "dash_high", "dash_main", "dash_base"):
        url = stream_options.get(key)
        if url:
            choices.append((_QUALITY_LABELS[key], url))
    return choices


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Main render
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def render(api: MXPlayerAPI):
    content = st.session_state.selected_content
    if not content:
        return

    if st.button("← Back to results"):
        st.session_state.playing_episode_id = None
        go_home()
        st.rerun()

    _render_hero(content)
    st.divider()

    if content["type"] == "tvshow":
        _render_tvshow(api, content)
    elif content["type"] in ("movie", "video", "episode", "music_video", ""):
        _render_single_video(api, content)
    else:
        st.info(f"Content type **{content['type']}** — try using the Direct URL tab.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Hero section (shared between tvshow and movie)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _render_hero(content: dict):
    hero_cols = st.columns([1, 2], gap="large")
    with hero_cols[0]:
        if content.get("image"):
            st.image(content["image"], use_container_width=True)
    with hero_cols[1]:
        st.markdown(
            f'<div class="detail-title">{content["title"]}</div>',
            unsafe_allow_html=True,
        )

        meta_parts = []
        if content.get("year"):
            meta_parts.append(f"📅 {content['year']}")
        if content.get("genres"):
            meta_parts.append(f"🎭 {', '.join(content['genres'][:3])}")
        if content.get("languages"):
            meta_parts.append(f"🗣️ {', '.join(content['languages'])}")
        if content.get("publisher"):
            meta_parts.append(f"🏢 {content['publisher']}")
        dur = format_duration(content.get("duration", 0))
        if dur:
            meta_parts.append(f"⏱️ {dur}")
        if meta_parts:
            st.markdown(
                f'<div class="detail-meta">{" &nbsp;|&nbsp; ".join(meta_parts)}</div>',
                unsafe_allow_html=True,
            )

        if content.get("description"):
            desc = content["description"]
            if len(desc) > 300:
                with st.expander("Show full description"):
                    st.write(desc)
            else:
                st.markdown(
                    f'<div class="detail-desc">{desc}</div>',
                    unsafe_allow_html=True,
                )

        if content.get("contributors"):
            cast = ", ".join(c["name"] for c in content["contributors"][:6])
            st.caption(f"🎭 Cast: {cast}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TV Show — seasons + clickable episodes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _render_tvshow(api: MXPlayerAPI, content: dict):
    if not st.session_state.seasons:
        with st.spinner("Loading seasons..."):
            if st.session_state.show_detail:
                st.session_state.seasons = extract_seasons(st.session_state.show_detail)
            else:
                detail, err = api.get_collection(content["id"], "tvshow")
                if detail:
                    st.session_state.show_detail = detail
                    st.session_state.seasons = extract_seasons(detail)
                elif err:
                    st.error(err)

    seasons = st.session_state.seasons
    if not seasons:
        st.warning("Could not load season information for this show.")
        return

    season_labels = [
        f"{s['title']}  ({s['episodesCount']} ep{'s' if s['episodesCount'] != 1 else ''})"
        for s in seasons
    ]
    sel = st.selectbox(
        "Select Season",
        range(len(season_labels)),
        format_func=lambda i: season_labels[i],
        key="season_picker",
    )

    current_season_id = seasons[sel]["id"]
    if current_season_id != st.session_state.episodes_season_id:
        st.session_state.sel_season_idx = sel
        st.session_state.episodes_season_id = current_season_id
        st.session_state.playing_episode_id = None
        with st.spinner("Loading episodes..."):
            eps, err = api.get_episodes(current_season_id)
            st.session_state.episodes = eps
            if err and not eps:
                st.error(err)

    episodes = st.session_state.episodes
    if not episodes:
        st.info("No episodes found for this season.")
        return

    st.markdown(f"### Episodes ({len(episodes)})")

    for i, ep in enumerate(episodes):
        _render_episode_card(ep, i, content["title"], sel, episodes)


def _build_playlist(
    all_episodes: list[dict], current_idx: int, show_title: str, season_idx: int,
) -> dict:
    """Build a playlist dict for the player with correct index mapping."""
    entries = []
    mapped_idx = 0
    for i, e in enumerate(all_episodes):
        if not e.get("stream_url") or e.get("drm"):
            continue
        seq = e.get("sequence") or i + 1
        langs = e.get("languages") or []
        entries.append({
            "title": f"{show_title} - S{season_idx + 1}E{seq} - {e['title']}",
            "url": e["stream_url"],
            "seq": seq,
            "langs": langs,
        })
        if i == current_idx:
            mapped_idx = len(entries) - 1
    return {"current": mapped_idx, "episodes": entries}


def _render_episode_card(
    ep: dict, idx: int, show_title: str, season_idx: int,
    all_episodes: list[dict] | None = None,
):
    """Render a single clickable episode card with play/download options."""
    seq = ep.get("sequence") or idx + 1
    dur = format_duration(ep.get("duration", 0))
    dur_label = f"  •  {dur}" if dur else ""
    ep_id = ep.get("id", str(idx))
    has_stream = bool(ep.get("stream_url")) and not ep.get("drm")

    label = f"Ep {seq} — {ep['title']}{dur_label}"
    if ep.get("drm"):
        label += "  🔒"

    with st.expander(label, expanded=(st.session_state.playing_episode_id == ep_id)):
        # top row: thumbnail + description
        info_cols = st.columns([1, 3])
        with info_cols[0]:
            if ep.get("image"):
                st.image(ep["image"], use_container_width=True)
        with info_cols[1]:
            if ep.get("description"):
                st.markdown(ep["description"][:400])
            langs = ep.get("languages") or []
            if langs:
                st.caption(f"🗣️ Available: {', '.join(langs)}")

        if ep.get("drm"):
            st.warning("This episode is DRM-protected and cannot be played or downloaded directly.")
            return

        if not has_stream:
            st.info("No stream URL available for this episode.")
            return

        # action row: quality + language selectors, play / download buttons
        stream_options = ep.get("stream_options") or {}
        qualities = _quality_choices(stream_options)
        lang_details = ep.get("languages_details") or []

        sel_cols = st.columns([2, 2, 1, 1])

        with sel_cols[0]:
            if len(qualities) > 1:
                q_labels = [q[0] for q in qualities]
                q_idx = st.selectbox(
                    "Quality", range(len(q_labels)),
                    format_func=lambda j: q_labels[j],
                    key=f"q_{ep_id}_{idx}",
                    label_visibility="collapsed",
                )
                chosen_url = qualities[q_idx][1]
            else:
                chosen_url = ep["stream_url"]
                st.caption("Quality: Best available")

        with sel_cols[1]:
            chosen_lang = None
            if len(lang_details) > 1:
                lang_names = [ld["name"] for ld in lang_details]
                lang_idx = st.selectbox(
                    "Audio", range(len(lang_names)),
                    format_func=lambda j: lang_names[j],
                    key=f"lang_{ep_id}_{idx}",
                    label_visibility="collapsed",
                )
                chosen_lang = lang_details[lang_idx]["id"]
            elif lang_details:
                st.caption(f"Audio: {lang_details[0]['name']}")
                chosen_lang = lang_details[0]["id"]
            else:
                st.caption("Audio: Default")

        with sel_cols[2]:
            if st.button("▶️ Play", key=f"play_{ep_id}_{idx}", use_container_width=True):
                st.session_state.playing_episode_id = ep_id
                st.rerun()

        with sel_cols[3]:
            if st.button("⬇️ Download", key=f"dl_{ep_id}_{idx}", use_container_width=True):
                ep_label = (
                    f"{show_title} - S{season_idx + 1}"
                    f"E{seq} - {ep['title']}"
                )
                start_download(
                    ep["stream_url"], ep_label,
                    audio_lang=chosen_lang,
                    quality=chosen_url,
                )
                st.rerun()

        # inline player (visible only when this episode is playing)
        if st.session_state.playing_episode_id == ep_id:
            st.divider()
            playlist = (
                _build_playlist(all_episodes, idx, show_title, season_idx)
                if all_episodes else None
            )
            render_player(chosen_url, ep["title"], playlist=playlist)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Movie / single video
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _render_single_video(api: MXPlayerAPI, content: dict):
    stream = content.get("stream_url", "")
    stream_options = content.get("stream_options") or {}

    if not stream:
        detail, err = api.get_collection(content["id"], content["type"] or "movie")
        if detail:
            stream = parse_stream_url(detail.get("stream"))
        elif err:
            st.warning(err)

    if not stream:
        st.info("No direct stream found via API. Try using the **Direct URL** tab with browser extraction.")
        return

    if content.get("drm"):
        st.warning("This content is DRM-protected and cannot be played or downloaded directly.")
        return

    # controls row
    qualities = _quality_choices(stream_options)
    lang_details = content.get("languages_details") or []

    ctrl_cols = st.columns([2, 2, 1, 1])

    with ctrl_cols[0]:
        if len(qualities) > 1:
            q_labels = [q[0] for q in qualities]
            q_idx = st.selectbox(
                "Quality", range(len(q_labels)),
                format_func=lambda j: q_labels[j],
                key="movie_quality",
                label_visibility="collapsed",
            )
            chosen_url = qualities[q_idx][1]
        else:
            chosen_url = stream
            st.caption("Quality: Best available")

    with ctrl_cols[1]:
        chosen_lang = None
        if len(lang_details) > 1:
            lang_names = [ld["name"] for ld in lang_details]
            lang_idx = st.selectbox(
                "Audio", range(len(lang_names)),
                format_func=lambda j: lang_names[j],
                key="movie_lang",
                label_visibility="collapsed",
            )
            chosen_lang = lang_details[lang_idx]["id"]
        elif lang_details:
            st.caption(f"Audio: {lang_details[0]['name']}")
            chosen_lang = lang_details[0]["id"]
        else:
            st.caption("Audio: Default")

    with ctrl_cols[2]:
        play_btn = st.button("▶️ Play", key="movie_play", type="primary", use_container_width=True)

    with ctrl_cols[3]:
        if st.button("⬇️ Download", key="movie_dl", use_container_width=True):
            start_download(
                stream, content["title"],
                audio_lang=chosen_lang,
                quality=chosen_url,
            )
            st.rerun()

    # player
    if play_btn or st.session_state.playing_episode_id == "movie":
        st.session_state.playing_episode_id = "movie"
        st.divider()
        render_player(chosen_url, content["title"])
