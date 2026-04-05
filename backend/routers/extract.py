"""Browser-based stream discovery — public (same role as Streamlit \"Extract via Browser\")."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from starlette.concurrency import run_in_threadpool

from content_public import strip_stream_fields
from dependencies import get_api
from models import (
    ContentItem,
    ExtractBrowserRequest,
    ExtractBrowserResponse,
    Season,
)
from services.browser_extract import extract_and_resolve
from services.mx_api import MXPlayerAPI

router = APIRouter(prefix="/api", tags=["extract"])


@router.post("/extract-browser", response_model=ExtractBrowserResponse)
async def extract_browser(
    body: ExtractBrowserRequest,
    api: MXPlayerAPI = Depends(get_api),
):
    """Headless Chrome finds HLS/DASH on the page, then resolves related MX metadata."""
    result = await run_in_threadpool(
        extract_and_resolve,
        body.url,
        api.userid,
    )
    if result.get("error"):
        raise HTTPException(status_code=502, detail=result["error"])

    item = None
    if result.get("parsed"):
        item = ContentItem(**strip_stream_fields(result["parsed"]))

    seasons = [Season(**s) for s in result.get("seasons") or []]
    episodes = [
        ContentItem(**strip_stream_fields(e)) for e in result.get("episodes") or []
    ]

    return ExtractBrowserResponse(
        type=result.get("type", ""),
        item=item,
        seasons=seasons,
        episodes=episodes,
        direct_stream_url=result.get("direct_stream_url"),
    )
