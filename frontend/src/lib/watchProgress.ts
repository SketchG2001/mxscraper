/**
 * Local resume positions (same idea as MX Player “continue watching”).
 * All I/O is defensive — never throws to the caller.
 */

export const WATCH_PROGRESS_STORAGE_KEY = 'mxscraper.watchProgress.v1'
export const MAX_STORED_TITLES = 80
/** Ignore resume if earlier than this (seconds). */
export const MIN_RESUME_SECONDS = 12
/** Treat as finished if within this many seconds of the end. */
export const END_MARGIN_SECONDS = 45

export type WatchProgressRecord = {
  v: 1
  position: number
  duration: number
  title: string
  updatedAt: number
  /** Optional poster for Continue watching rail */
  poster?: string
}

function djb2(str: string): number {
  let h = 5381
  for (let i = 0; i < str.length; i++) {
    h = (h * 33) ^ str.charCodeAt(i)
  }
  return h >>> 0
}

/** Stable key for localStorage; same title always maps to the same slot. */
export function makeWatchKey(params: {
  contentId?: string | null
  type: string
  seasonId?: string | null
  directUrl?: string | null
}): string {
  const t = (params.type || 'movie').toLowerCase()
  const sid = params.seasonId?.trim() || ''
  if (params.contentId?.trim()) {
    return `c:${params.contentId.trim()}:${t}:${sid}`
  }
  const u = params.directUrl?.trim()
  if (u) return `d:${djb2(u).toString(36)}`
  return 'x:unknown'
}

function readStore(): Record<string, WatchProgressRecord> {
  try {
    const raw = localStorage.getItem(WATCH_PROGRESS_STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
    return parsed as Record<string, WatchProgressRecord>
  } catch {
    return {}
  }
}

function writeStore(store: Record<string, WatchProgressRecord>): void {
  try {
    const entries = Object.entries(store).sort(
      (a, b) => (b[1].updatedAt ?? 0) - (a[1].updatedAt ?? 0),
    )
    const pruned = Object.fromEntries(entries.slice(0, MAX_STORED_TITLES))
    localStorage.setItem(WATCH_PROGRESS_STORAGE_KEY, JSON.stringify(pruned))
  } catch {
    /* quota, private mode, disabled storage */
  }
}

export function loadWatchProgress(key: string): WatchProgressRecord | null {
  if (!key || key === 'x:unknown') return null
  try {
    const row = readStore()[key]
    if (!row || row.v !== 1) return null
    if (typeof row.position !== 'number' || typeof row.duration !== 'number') return null
    if (!Number.isFinite(row.position) || !Number.isFinite(row.duration)) return null
    return row
  } catch {
    return null
  }
}

export function shouldOfferResume(
  record: WatchProgressRecord,
  durationSeconds: number,
): boolean {
  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) return false
  const pos = record.position
  if (!Number.isFinite(pos) || pos < MIN_RESUME_SECONDS) return false
  const endCut = Math.max(0, durationSeconds - END_MARGIN_SECONDS)
  if (pos >= endCut) return false
  return true
}

/** Clamp saved position to a safe seek target for the current asset duration. */
export function clampResumePosition(
  position: number,
  durationSeconds: number,
): number {
  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) return 0
  const margin = Math.min(END_MARGIN_SECONDS, durationSeconds * 0.05)
  const max = Math.max(0, durationSeconds - margin)
  return Math.max(0, Math.min(position, max))
}

export function saveWatchProgress(
  key: string,
  payload: Omit<WatchProgressRecord, 'v' | 'updatedAt'> & {
    title: string
    /** New poster URL; omit or empty to keep previous ``poster`` when updating position. */
    poster?: string | null
  },
): void {
  if (!key || key === 'x:unknown') return
  try {
    const store = readStore()
    const prev = store[key]
    const nextPoster =
      typeof payload.poster === 'string' && payload.poster.trim()
        ? payload.poster.trim().slice(0, 800)
        : prev?.poster
    store[key] = {
      v: 1,
      position: Math.max(0, payload.position),
      duration: Math.max(0, payload.duration),
      title: payload.title.slice(0, 300),
      updatedAt: Date.now(),
      ...(nextPoster ? { poster: nextPoster } : {}),
    }
    writeStore(store)
  } catch {
    /* ignore */
  }
}

/** Attach a poster URL to an existing row (e.g. after lazy thumbnail resolve). */
export function patchWatchProgressPoster(key: string, poster: string): void {
  if (!key || key === 'x:unknown') return
  const u = poster.trim().slice(0, 800)
  if (!u) return
  try {
    const store = readStore()
    const row = store[key]
    if (!row || row.v !== 1 || row.poster) return
    store[key] = { ...row, poster: u, updatedAt: Date.now() }
    writeStore(store)
  } catch {
    /* ignore */
  }
}

export function clearWatchProgress(key: string): void {
  if (!key || key === 'x:unknown') return
  try {
    const store = readStore()
    delete store[key]
    writeStore(store)
  } catch {
    /* ignore */
  }
}

/** Parse keys produced by ``makeWatchKey`` (``c:contentId:type:seasonId``). */
export function parseContentWatchKey(key: string): {
  contentId: string
  type: string
  seasonId: string
} | null {
  const m = /^c:([^:]+):([^:]+):(.*)$/.exec(key)
  if (!m) return null
  return { contentId: m[1], type: m[2] || 'movie', seasonId: m[3] ?? '' }
}

export type ContinueWatchingItem = {
  key: string
  contentId: string
  type: string
  seasonId: string
  title: string
  position: number
  duration: number
  updatedAt: number
  percent: number
  poster?: string
}

/** In-progress titles for the home “Continue watching” rail (newest first). */
export function listContinueWatching(limit = 14): ContinueWatchingItem[] {
  let store: Record<string, WatchProgressRecord>
  try {
    store = readStore()
  } catch {
    return []
  }
  const out: ContinueWatchingItem[] = []
  for (const [key, row] of Object.entries(store)) {
    if (!row || row.v !== 1) continue
    const meta = parseContentWatchKey(key)
    if (!meta) continue
    if (typeof row.position !== 'number' || typeof row.duration !== 'number') continue
    if (row.position < 8) continue
    if (row.duration > 0 && row.position >= row.duration - END_MARGIN_SECONDS) continue
    const pct =
      row.duration > 0
        ? Math.min(100, Math.round((row.position / row.duration) * 1000) / 10)
        : 0
    out.push({
      key,
      ...meta,
      title: row.title,
      position: row.position,
      duration: row.duration,
      updatedAt: row.updatedAt,
      percent: pct,
      poster: row.poster,
    })
  }
  out.sort((a, b) => b.updatedAt - a.updatedAt)
  return out.slice(0, Math.max(1, limit))
}

export function watchUrlForProgress(item: {
  contentId: string
  type: string
  seasonId: string
  title: string
}): string {
  const q = new URLSearchParams({ type: item.type || 'movie' })
  if (item.seasonId) q.set('seasonId', item.seasonId)
  if (item.title.trim()) q.set('ref_title', item.title.trim())
  return `/watch/${encodeURIComponent(item.contentId)}?${q}`
}

export function episodeProgressUi(
  episodeId: string,
  seasonId: string,
): {
  percent: number
  atLabel: string
  showBar: boolean
  isAlmostDone: boolean
} | null {
  const key = makeWatchKey({
    contentId: episodeId,
    type: 'episode',
    seasonId,
  })
  const row = loadWatchProgress(key)
  if (!row || row.duration <= 0) return null
  const almost = row.position >= row.duration - END_MARGIN_SECONDS
  const started = row.position >= 8
  const percent = Math.min(100, (row.position / row.duration) * 100)
  return {
    percent,
    atLabel: formatPlaybackClock(row.position),
    showBar: started && !almost,
    isAlmostDone: almost,
  }
}

export function formatPlaybackClock(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  }
  return `${m}:${String(sec).padStart(2, '0')}`
}
