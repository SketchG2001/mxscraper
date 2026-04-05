import type { StreamOption } from '../types/api'
import { proxiedStreamUrl } from './proxyUrl'

const HLS_ORDER = ['hls_high', 'hls_main', 'hls_base'] as const
const DASH_ORDER = ['dash_high', 'dash_main', 'dash_base'] as const

/** User-facing labels (MX exposes high / main / base, not always literal 1080p). */
export function labelForStreamOption(key: string): string {
  const map: Record<string, string> = {
    hls_high: '1080p',
    hls_main: '720p',
    hls_base: '480p',
    dash_high: '1080p (DASH)',
    dash_main: '720p (DASH)',
    dash_base: '480p (DASH)',
  }
  return map[key] || key.replace(/_/g, ' ')
}

/** Prefer HLS for browser VHS; fall back to DASH. Order: high → main → base. */
export function orderedStreamOptions(options: StreamOption[]): StreamOption[] {
  const hls = options.filter((o) => o.key.startsWith('hls_'))
  const dash = options.filter((o) => o.key.startsWith('dash_'))
  const pick = hls.length > 0 ? hls : dash
  const order = pick.some((o) => o.key.startsWith('hls_')) ? HLS_ORDER : DASH_ORDER
  const rank = (key: string) => {
    const i = (order as readonly string[]).indexOf(key)
    return i === -1 ? 999 : i
  }
  return [...pick].sort((a, b) => rank(a.key) - rank(b.key))
}

export type ProxiedQualitySource = { key: string; label: string; url: string }

export function proxiedUrlsMatch(a: string, b: string): boolean {
  if (a === b) return true
  try {
    return new URL(a).href === new URL(b).href
  } catch {
    return false
  }
}

/**
 * Episodes often expose ``stream_url`` that does not exactly match ``stream_options`` URLs.
 * Without this, the player defaulted to the first option (usually 1080p) and could fail while
 * the API default stream still works.
 */
export function withDefaultQualitySource(
  sources: ProxiedQualitySource[],
  playbackUrl: string,
): ProxiedQualitySource[] {
  if (!playbackUrl.trim() || sources.length < 2) return sources
  if (sources.some((s) => proxiedUrlsMatch(s.url, playbackUrl))) return sources
  return [
    { key: 'stream_default', label: 'Default', url: playbackUrl },
    ...sources,
  ]
}

export function buildProxiedQualitySources(
  options: StreamOption[] | undefined,
  proxyHost: string,
  proxyPort: number,
): ProxiedQualitySource[] {
  if (!options?.length) return []
  return orderedStreamOptions(options)
    .map((o) => {
      const u = (o.url || '').trim()
      if (!u.startsWith('http')) return null
      return {
        key: o.key,
        label: labelForStreamOption(o.key),
        url: proxiedStreamUrl(u, proxyHost, proxyPort),
      }
    })
    .filter((x): x is ProxiedQualitySource => x != null)
}
