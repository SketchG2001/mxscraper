"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import cors_allow_credentials, cors_allow_origins, settings
from routers import content, download, extract, search, stream
from services.ffmpeg import ffmpeg_status
from services.proxy import start_proxy


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_proxy(settings.proxy_port, host=settings.proxy_bind_host)
    yield


app = FastAPI(
    title="MX Player Scraper API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins(),
    allow_credentials=cors_allow_credentials(),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(content.router)
app.include_router(stream.router)
app.include_router(download.router)
app.include_router(extract.router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "proxy_port": settings.proxy_port,
        "ffmpeg": ffmpeg_status(),
    }
