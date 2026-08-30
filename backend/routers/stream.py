"""Stream endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from dependencies import get_api
from models import LanguageDetail, StreamOption, StreamResponse
from services.mx_api import (
    MXPlayerAPI,
    parse_item,
    parse_stream_options,
    prefer_main_if_default_is_high,
    stream_url,
)

router = APIRouter(prefix="/api", tags=["stream"])

QUALITY_LABELS: dict[str, str] = {
    "hls_high": "HLS High",
    "hls_main": "HLS Main",
    "hls_base": "HLS Base",
    "dash_high": "DASH High",
    "dash_main": "DASH Main",
    "dash_base": "DASH Base",
}


def _response_from_detail(detail: dict) -> StreamResponse:
    raw_stream = detail.get("stream")
    url = stream_url(raw_stream)
    parsed = parse_item(detail)
    if not url and parsed:
        url = parsed.get("stream_url") or ""
    if not url:
        raise HTTPException(status_code=404, detail="No stream available for this content.")

    options_map = parse_stream_options(raw_stream)
    options = [
        StreamOption(key=k, label=QUALITY_LABELS.get(k, k), url=v)
        for k, v in options_map.items()
    ]
    drm = parsed["drm"] if parsed else False
    languages = [
        LanguageDetail(**ld) for ld in (parsed.get("languages_details") or [])
    ] if parsed else []
    return StreamResponse(stream_url=url, options=options, languages=languages, drm=drm)


def _maybe_enrich_episode_stream(api: MXPlayerAPI, content_id: str, parsed: dict) -> dict:
    """Merge stream_options from episode collection when the season list is missing rungs."""
    base = parsed.get("stream_options") or {}
    if not isinstance(base, dict):
        base = {}
    rich = api.episode_collection_stream_options(content_id)
    if not isinstance(rich, dict) or not rich:
        return parsed
    merged = {**rich, **base}
    if len(merged) > len(base):
        return {**parsed, "stream_options": merged}
    return parsed


def _response_from_parsed_episode(parsed: dict) -> StreamResponse:
    url = (parsed.get("stream_url") or "").strip()
    if not url:
        raise HTTPException(status_code=404, detail="No stream available for this content.")
    options_map = parsed.get("stream_options") or {}
    if isinstance(options_map, dict):
        url = prefer_main_if_default_is_high(url, options_map)
    options = [
        StreamOption(key=k, label=QUALITY_LABELS.get(k, k), url=v)
        for k, v in options_map.items()
        if isinstance(v, str) and v
    ]
    languages = [
        LanguageDetail(id=str(ld["id"]), name=str(ld["name"]))
        for ld in (parsed.get("languages_details") or [])
        if isinstance(ld, dict) and ld.get("id") is not None and ld.get("name")
    ]
    return StreamResponse(
        stream_url=url,
        options=options,
        languages=languages,
        drm=bool(parsed.get("drm")),
    )


def resolve_stream_response(
    api: MXPlayerAPI,
    content_id: str,
    type: str = "tvshow",
    season_id: str | None = None,
    ref_title: str | None = None,
    title: str | None = None,
) -> StreamResponse:
    """Same resolution as GET /api/stream — used by playback and downloads."""
    ref_q = (ref_title or title or "").strip() or None
    t = (type or "").lower()
    if t == "episode" and season_id:
        episodes, err = api.get_episodes(season_id)
        if err and not episodes:
            raise HTTPException(status_code=502, detail=err)
        for ep in episodes:
            if ep.get("id") == content_id:
                return _response_from_parsed_episode(
                    _maybe_enrich_episode_stream(api, content_id, ep),
                )
        raise HTTPException(
            status_code=404,
            detail="Episode not found in this season — open the show and play again.",
        )

    if t == "episode" and not season_id:
        detail_ep = api.get_episode_collection_detail(content_id)
        if detail_ep:
            parsed = parse_item(detail_ep)
            if parsed and (parsed.get("stream_url") or "").strip():
                parsed = _maybe_enrich_episode_stream(api, content_id, parsed)
                return _response_from_parsed_episode(parsed)

    detail, error = api.get_collection(content_id, type)
    if detail:
        return _response_from_detail(detail)

    if ref_q:
        hit = api.find_parsed_item_by_id(content_id, ref_q)
        if hit:
            if isinstance(hit, dict) and (hit.get("type") or "").lower() == "episode":
                hit = _maybe_enrich_episode_stream(api, content_id, hit)
            return _response_from_parsed_episode(hit)

    if error:
        raise HTTPException(status_code=502, detail=error)
    if t == "episode":
        raise HTTPException(
            status_code=400,
            detail="TV episodes need season_id — open the episode from the show page (season list).",
        )
    raise HTTPException(status_code=404, detail="Content not found.")


@router.get("/stream/{content_id}", response_model=StreamResponse)
async def get_stream(
    content_id: str,
    type: str = Query(
        "tvshow",
        description="MX content type: tvshow, movie, episode, music_video, video, …",
    ),
    season_id: str | None = Query(
        None,
        description="Required for episodes: parent season id (from tvshow episodes tab).",
    ),
    ref_title: str | None = Query(
        None,
        min_length=2,
        max_length=220,
        description="Title from browse — used when MX detail/collection fails for this id.",
    ),
    title: str | None = Query(
        None,
        min_length=2,
        max_length=220,
        description="Alias for ref_title (some clients send ``title``).",
    ),
    api: MXPlayerAPI = Depends(get_api),
):
    """Returns stream URL and quality options."""
    return resolve_stream_response(
        api,
        content_id,
        type=type,
        season_id=season_id,
        ref_title=ref_title,
        title=title,
    )
