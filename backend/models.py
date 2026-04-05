"""Pydantic schemas for API request / response payloads."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Shared sub-models ────────────────────────────────────


class LanguageDetail(BaseModel):
    id: str
    name: str


class Contributor(BaseModel):
    name: str
    role: str = ""


# ── Content item (search results, episodes, movies) ──────


class ContentItem(BaseModel):
    id: str
    title: str
    type: str = ""
    description: str = ""
    image: str = ""
    duration: int | float = 0
    sequence: str | int = ""
    year: str = ""
    rating: str | int = ""
    languages: list[str] = Field(default_factory=list)
    languages_details: list[LanguageDetail] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    publisher: str = ""
    contributors: list[Contributor] = Field(default_factory=list)
    shareUrl: str = ""
    drm: bool = False


# ── Responses ────────────────────────────────────────────


class SearchResponse(BaseModel):
    items: list[ContentItem]
    error: str | None = None


class BannerItem(BaseModel):
    """Home rail item; ``backdrop`` is MX desktop hero art when available."""

    id: str
    title: str
    type: str = ""
    image: str = ""
    backdrop: str = ""
    description: str = ""
    genres: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    rating: str | None = None


class BannersResponse(BaseModel):
    items: list[BannerItem]
    error: str | None = None


class ShelfItem(BaseModel):
    """Lightweight card for homepage category rails."""

    id: str
    title: str
    type: str = ""
    image: str = ""


class Shelf(BaseModel):
    id: str
    title: str
    items: list[ShelfItem]


class ShelvesResponse(BaseModel):
    shelves: list[Shelf]
    error: str | None = None


class Season(BaseModel):
    id: str
    title: str = "Season"
    episodesCount: int = 0


class SeasonsResponse(BaseModel):
    seasons: list[Season]
    error: str | None = None


class EpisodesResponse(BaseModel):
    episodes: list[ContentItem]
    error: str | None = None


class StreamOption(BaseModel):
    key: str
    label: str
    url: str


class StreamResponse(BaseModel):
    stream_url: str
    options: list[StreamOption] = Field(default_factory=list)
    languages: list[LanguageDetail] = Field(default_factory=list)
    drm: bool = False
    error: str | None = None


class ContentDetailResponse(BaseModel):
    item: ContentItem | None = None
    seasons: list[Season] = Field(default_factory=list)
    error: str | None = None


class ResolveRequest(BaseModel):
    url: str


class ResolveResponse(BaseModel):
    type: str = ""
    item: ContentItem | None = None
    seasons: list[Season] = Field(default_factory=list)
    episodes: list[ContentItem] = Field(default_factory=list)
    error: str | None = None


class ExtractBrowserRequest(BaseModel):
    url: str


class ExtractBrowserResponse(BaseModel):
    type: str = ""
    item: ContentItem | None = None
    seasons: list[Season] = Field(default_factory=list)
    episodes: list[ContentItem] = Field(default_factory=list)
    direct_stream_url: str | None = None
