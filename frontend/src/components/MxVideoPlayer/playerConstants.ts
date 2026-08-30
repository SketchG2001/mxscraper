export const SEEK_SECONDS = 10
export const PLAYBACK_RATES = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2] as const
export const CONTROL_HIDE_MS = 3000
export const DOUBLE_TAP_MS = 280
export const AUTO_NEXT_SECONDS = 5
export const PREFS_KEY = 'mxscraper.playerPrefs.v1'

export type CcSize = 'sm' | 'md' | 'lg'

export type PlayerPrefs = {
  rate?: number
  ccSize?: CcSize
  ccBg?: number
}

export function asTime(v: unknown): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : NaN
}

export function loadPlayerPrefs(): PlayerPrefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (!raw) return {}
    const p = JSON.parse(raw) as PlayerPrefs
    return p && typeof p === 'object' ? p : {}
  } catch {
    return {}
  }
}

export function savePlayerPrefs(patch: PlayerPrefs): void {
  try {
    const next = { ...loadPlayerPrefs(), ...patch }
    localStorage.setItem(PREFS_KEY, JSON.stringify(next))
  } catch {
    /* quota / private mode */
  }
}

export function ccSizePx(size: CcSize | undefined): string {
  if (size === 'sm') return '14px'
  if (size === 'lg') return '22px'
  return '17px'
}

/**
 * HTML5 `video.volume` is not Android system volume. A vertical-swipe overlay
 * would feel broken (stream gain vs media keys). Native volume buttons stay.
 */
export const VOLUME_GESTURE = false as const
