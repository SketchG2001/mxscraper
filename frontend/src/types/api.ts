export type ContentItem = {
  id: string
  title: string
  type: string
  description?: string
  image?: string
  duration?: number
  sequence?: string | number
  year?: string
  rating?: string | number
  languages?: string[]
  languages_details?: { id: string; name: string }[]
  genres?: string[]
  publisher?: string
  drm?: boolean
}

export type Season = { id: string; title: string; episodesCount: number }

export type SearchResponse = { items: ContentItem[]; error?: string | null }

export type BannerItem = {
  id: string
  title: string
  type: string
  image: string
  /** Wide hero from MX ``banner_and_static_bg_desktop`` when available */
  backdrop: string
  description: string
  genres?: string[]
  languages?: string[]
  /** Content rating when MX provides it (e.g. U/A 16+) */
  rating?: string | null
}

export type BannersResponse = { items: BannerItem[]; error?: string | null }

export type ShelfItem = {
  id: string
  title: string
  type: string
  image: string
}

export type Shelf = { id: string; title: string; items: ShelfItem[] }

export type ShelvesResponse = { shelves: Shelf[]; error?: string | null }

export type ResolveResponse = {
  type: string
  item: ContentItem | null
  seasons: Season[]
  episodes: ContentItem[]
}

export type ContentDetailResponse = {
  item: ContentItem | null
  seasons: Season[]
}

export type StreamOption = { key: string; label: string; url: string }

export type StreamResponse = {
  stream_url: string
  options: StreamOption[]
  languages: { id: string; name: string }[]
  drm: boolean
}

export type HealthResponse = { status: string; proxy_port: number }

export type ExtractBrowserResponse = {
  type: string
  item: ContentItem | null
  seasons: Season[]
  episodes: ContentItem[]
  direct_stream_url: string | null
}
