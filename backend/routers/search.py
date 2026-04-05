"""Search endpoints — public, no auth required."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from content_public import strip_stream_fields
from dependencies import get_api
from models import (
    BannerItem,
    BannersResponse,
    ContentItem,
    ResolveRequest,
    ResolveResponse,
    SearchResponse,
    Season,
    Shelf,
    ShelvesResponse,
)
from services.mx_api import MXPlayerAPI, extract_seasons, parse_item

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    api: MXPlayerAPI = Depends(get_api),
):
    items, error = api.search(q)
    if error:
        raise HTTPException(status_code=502, detail=error)
    return SearchResponse(
        items=[ContentItem(**strip_stream_fields(i)) for i in items],
    )


@router.get("/banners", response_model=BannersResponse)
async def get_banners(
    limit: int = Query(12, ge=4, le=24),
    api: MXPlayerAPI = Depends(get_api),
):
    """MX Player poster rails — aggregated search (same host as /api/search)."""
    raw, err = api.fetch_home_banners(limit=limit)
    items = [BannerItem(**row) for row in raw]
    return BannersResponse(items=items, error=err if not items else None)


@router.get("/home/shelves", response_model=ShelvesResponse)
async def get_home_shelves(
    per_shelf: int = Query(14, ge=4, le=24),
    api: MXPlayerAPI = Depends(get_api),
):
    """Category-style horizontal rails — one MX search per shelf (curated queries)."""
    raw, err = api.fetch_home_shelves(per_shelf=per_shelf)
    shelves = [Shelf(**row) for row in raw]
    return ShelvesResponse(shelves=shelves, error=err if not shelves else None)


@router.post("/resolve", response_model=ResolveResponse)
async def resolve_url(
    body: ResolveRequest,
    api: MXPlayerAPI = Depends(get_api),
):
    """Resolve an MX Player URL to structured content."""
    resolved = api.resolve_url(body.url)
    if not resolved:
        raise HTTPException(status_code=404, detail="Could not resolve URL.")

    item = None
    seasons: list[Season] = []
    episodes: list[ContentItem] = []

    parsed = resolved.get("parsed")
    if parsed:
        item = ContentItem(**strip_stream_fields(parsed))

    detail = resolved.get("detail")
    if detail:
        seasons = [Season(**s) for s in extract_seasons(detail)]

    raw_eps = resolved.get("episodes") or []
    episodes = [ContentItem(**strip_stream_fields(e)) for e in raw_eps]

    return ResolveResponse(
        type=resolved.get("type", ""),
        item=item,
        seasons=seasons,
        episodes=episodes,
    )
