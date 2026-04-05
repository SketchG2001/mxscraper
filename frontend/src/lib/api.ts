import type {
  BannersResponse,
  ContentDetailResponse,
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
  accessToken: string,
  seasonId?: string | null,
  refTitle?: string | null,
): Promise<StreamResponse> {
  const q = new URLSearchParams({ type: contentType })
  if (seasonId) q.set('season_id', seasonId)
  if (refTitle?.trim()) q.set('ref_title', refTitle.trim())
  const res = await fetch(
    apiUrl(`/api/stream/${encodeURIComponent(contentId)}?${q}`),
    { headers: { Authorization: `Bearer ${accessToken}` } },
  )
  return parseJson<StreamResponse>(res)
}
