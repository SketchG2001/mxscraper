"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import content, extract, search, stream
from services.proxy import start_proxy


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_proxy(settings.proxy_port)
    yield


app = FastAPI(
    title="MX Player Scraper API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(content.router)
app.include_router(stream.router)
app.include_router(extract.router)


@app.get("/health")
async def health():
    return {"status": "ok", "proxy_port": settings.proxy_port}
