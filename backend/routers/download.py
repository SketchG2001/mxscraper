"""Download jobs. Content is resolved, not a raw URL."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from dependencies import get_api
from models import DownloadCreateRequest, DownloadJobResponse
from routers.stream import resolve_stream_response
from services.download import (
    DownloadJob,
    DownloadRejected,
    downloads_root,
    get_manager,
)
from services.mx_api import MXPlayerAPI

router = APIRouter(prefix="/api", tags=["downloads"])

DRM_DETAIL = "This content is protected and cannot be downloaded."


def _to_response(job: DownloadJob) -> DownloadJobResponse:
    return DownloadJobResponse(
        job_id=job.job_id,
        content_id=job.content_id,
        title=job.title,
        status=job.status,
        progress=job.progress,
        bytes_downloaded=job.bytes_downloaded,
        total_bytes=job.total_bytes,
        speed=job.speed,
        eta=job.eta,
        filename=job.filename,
        file_available=job.file_available,
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


def _pick_url(stream_url: str, options: list, quality: str | None) -> str:
    if not quality:
        return stream_url
    for opt in options:
        if opt.key == quality and opt.url:
            return opt.url
    raise HTTPException(status_code=400, detail="Requested quality is not available.")


@router.post("/downloads", response_model=DownloadJobResponse)
async def create_download(
    body: DownloadCreateRequest,
    api: MXPlayerAPI = Depends(get_api),
):
    stream = resolve_stream_response(
        api,
        body.content_id,
        type=body.type,
        season_id=body.season_id,
        ref_title=body.ref_title,
        title=body.title,
    )
    if stream.drm:
        raise HTTPException(status_code=403, detail=DRM_DETAIL)

    url = _pick_url(stream.stream_url, stream.options, body.quality)
    if not url:
        raise HTTPException(status_code=404, detail="No stream available for this content.")

    if body.language:
        known = {lang.id for lang in stream.languages}
        if known and body.language not in known:
            raise HTTPException(status_code=400, detail="Requested language is not available.")

    title = (body.title or "").strip() or body.content_id
    try:
        job = get_manager().create(
            content_id=body.content_id,
            title=title,
            stream_url=url,
            language=body.language,
        )
    except DownloadRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _to_response(job)


@router.get("/downloads/{job_id}", response_model=DownloadJobResponse)
async def get_download(job_id: str):
    job = get_manager().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found.")
    return _to_response(job)


@router.post("/downloads/{job_id}/cancel", response_model=DownloadJobResponse)
async def cancel_download(job_id: str):
    try:
        job = get_manager().cancel(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Download job not found.")
    return _to_response(job)


@router.get("/downloads/{job_id}/file")
async def download_file(job_id: str):
    job = get_manager().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found.")
    if not job.file_available or not job.output_path:
        raise HTTPException(status_code=409, detail="File is not ready.")
    path = Path(job.output_path).resolve()
    root = downloads_root().resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="File is no longer available.") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File is no longer available.")
    return FileResponse(
        path,
        filename=job.filename or path.name,
        media_type="video/mp4",
    )
