import type {
  BannersResponse,
  ContentDetailResponse,
  DownloadJob,
  ExtractBrowserResponse,
  HealthResponse,
  ResolveResponse,
  SearchResponse,
  ShelvesResponse,
  StreamResponse,
} from '../types/api'
import { apiUrl } from './apiBase'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text()
  if (!res.ok) {
    let detail = text
    try {
      const j = JSON.parse(text) as { detail?: string }
      if (j.detail) detail = j.detail
    } catch {
      /* use raw */
    }
    throw new ApiError(res.status, detail || res.statusText)
  }
  return text ? (JSON.parse(text) as T) : ({} as T)
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(apiUrl('/health'))
  return parseJson<HealthResponse>(res)
}

/** Poll existing /health until the loopback FastAPI is up (Android startup). */
export async function waitForHealth(
  timeoutMs = 30000,
  intervalMs = 250,
): Promise<HealthResponse> {
  const deadline = Date.now() + timeoutMs
  let last: unknown
  while (Date.now() < deadline) {
    try {
      const health = await fetchHealth()
      if (health.status === 'ok') return health
      last = new Error(`health status ${health.status}`)
    } catch (err) {
      last = err
    }
    await new Promise((r) => setTimeout(r, intervalMs))
  }
  throw last instanceof Error ? last : new Error('local API not ready')
}

export async function searchMx(q: string): Promise<SearchResponse> {
  const res = await fetch(apiUrl(`/api/search?q=${encodeURIComponent(q)}`))
  return parseJson<SearchResponse>(res)
}

export async function fetchBanners(limit = 12): Promise<BannersResponse> {
  const res = await fetch(apiUrl(`/api/banners?limit=${limit}`))
  return parseJson<BannersResponse>(res)
}

export async function fetchHomeShelves(perShelf = 14): Promise<ShelvesResponse> {
  const res = await fetch(
    apiUrl(`/api/home/shelves?per_shelf=${encodeURIComponent(String(perShelf))}`),
  )
  return parseJson<ShelvesResponse>(res)
}

export async function resolveUrl(url: string): Promise<ResolveResponse> {
  const res = await fetch(apiUrl('/api/resolve'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  return parseJson<ResolveResponse>(res)
}

export async function extractBrowser(url: string): Promise<ExtractBrowserResponse> {
  const res = await fetch(apiUrl('/api/extract-browser'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  return parseJson<ExtractBrowserResponse>(res)
}

export async function fetchContent(
  contentId: string,
  type: string,
  refTitle?: string | null,
): Promise<ContentDetailResponse> {
  const q = new URLSearchParams({ type })
  if (refTitle?.trim()) q.set('ref_title', refTitle.trim())
  const res = await fetch(
    apiUrl(`/api/content/${encodeURIComponent(contentId)}?${q}`),
  )
  return parseJson<ContentDetailResponse>(res)
}

export async function fetchEpisodes(seasonId: string): Promise<{
  episodes: import('../types/api').ContentItem[]
  error?: string | null
}> {
  const res = await fetch(apiUrl(`/api/seasons/${encodeURIComponent(seasonId)}/episodes`))
  return parseJson(res)
}

export async function fetchStream(
  contentId: string,
  contentType: string,
  seasonId?: string | null,
  refTitle?: string | null,
): Promise<StreamResponse> {
  const q = new URLSearchParams({ type: contentType })
  if (seasonId) q.set('season_id', seasonId)
  if (refTitle?.trim()) q.set('ref_title', refTitle.trim())
  const res = await fetch(apiUrl(`/api/stream/${encodeURIComponent(contentId)}?${q}`))
  return parseJson<StreamResponse>(res)
}

export type DownloadCreateBody = {
  content_id: string
  type: string
  season_id?: string | null
  language?: string | null
  quality?: string | null
  ref_title?: string | null
  title?: string | null
}

export async function createDownload(
  body: DownloadCreateBody,
): Promise<DownloadJob> {
  const res = await fetch(apiUrl('/api/downloads'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      content_id: body.content_id,
      type: body.type,
      season_id: body.season_id || undefined,
      language: body.language || undefined,
      quality: body.quality || undefined,
      ref_title: body.ref_title || undefined,
      title: body.title || undefined,
    }),
  })
  return parseJson<DownloadJob>(res)
}

export async function fetchDownload(jobId: string): Promise<DownloadJob> {
  const res = await fetch(apiUrl(`/api/downloads/${encodeURIComponent(jobId)}`))
  return parseJson<DownloadJob>(res)
}

export async function cancelDownload(jobId: string): Promise<DownloadJob> {
  const res = await fetch(
    apiUrl(`/api/downloads/${encodeURIComponent(jobId)}/cancel`),
    { method: 'POST' },
  )
  return parseJson<DownloadJob>(res)
}

export async function fetchDownloadFile(jobId: string): Promise<Blob> {
  const res = await fetch(apiUrl(`/api/downloads/${encodeURIComponent(jobId)}/file`))
  if (!res.ok) {
    const text = await res.text()
    throw new ApiError(res.status, text || res.statusText)
  }
  return res.blob()
}
