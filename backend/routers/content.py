"""Content detail endpoints — public, no auth required."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from content_public import strip_stream_fields
from dependencies import get_api
from models import (
    ContentDetailResponse,
    ContentItem,
    EpisodesResponse,
    Season,
    SeasonsResponse,
)
from services.mx_api import MXPlayerAPI, extract_seasons, parse_item

router = APIRouter(prefix="/api", tags=["content"])


@router.get("/content/{content_id}", response_model=ContentDetailResponse)
async def get_content(
    content_id: str,
    type: str = Query("tvshow", description="Content type: tvshow, movie, etc."),
    ref_title: str | None = Query(
        None,
        min_length=2,
        max_length=220,
        description="Title from search/shelves — used when MX detail/collection fails for this id.",
    ),
    title: str | None = Query(
        None,
        min_length=2,
        max_length=220,
        description="Alias for ref_title (some clients send ``title``).",
    ),
    api: MXPlayerAPI = Depends(get_api),
):
    ref_q = (ref_title or title or "").strip() or None
    t = (type or "tvshow").lower()
    if t == "episode":
        detail_ep = api.get_episode_collection_detail(content_id)
        if detail_ep:
            parsed = parse_item(detail_ep)
            if parsed:
                item = ContentItem(**strip_stream_fields(parsed))
                seasons = [Season(**s) for s in extract_seasons(detail_ep)]
                return ContentDetailResponse(item=item, seasons=seasons)

    detail, error = api.get_collection(content_id, type)
    if detail:
        parsed = parse_item(detail)
        item = ContentItem(**strip_stream_fields(parsed)) if parsed else None
        seasons = [Season(**s) for s in extract_seasons(detail)]
        return ContentDetailResponse(item=item, seasons=seasons)

    if ref_q:
        hit = api.find_parsed_item_by_id(content_id, ref_q)
        if hit:
            row = parse_item(hit) or hit
            item = ContentItem(**strip_stream_fields(row))
            return ContentDetailResponse(item=item, seasons=[])

    if error:
        raise HTTPException(status_code=502, detail=error)
    raise HTTPException(status_code=404, detail="Content not found.")


@router.get("/content/{content_id}/seasons", response_model=SeasonsResponse)
async def get_seasons(
    content_id: str,
    api: MXPlayerAPI = Depends(get_api),
):
    detail, error = api.get_collection(content_id, "tvshow")
    if error:
        raise HTTPException(status_code=502, detail=error)
    if not detail:
        raise HTTPException(status_code=404, detail="Show not found.")

    seasons = [Season(**s) for s in extract_seasons(detail)]
    return SeasonsResponse(seasons=seasons)


@router.get("/seasons/{season_id}/episodes", response_model=EpisodesResponse)
async def get_episodes(
    season_id: str,
    api: MXPlayerAPI = Depends(get_api),
):
    episodes, error = api.get_episodes(season_id)
    if error and not episodes:
        raise HTTPException(status_code=502, detail=error)

    items = [ContentItem(**strip_stream_fields(e)) for e in episodes]
    return EpisodesResponse(episodes=items, error=error)
