import { getApiBase } from './apiBase'

const LOOPBACK = new Set(['localhost', '127.0.0.1', '[::1]'])

function isLoopbackHost(hostname: string): boolean {
  return LOOPBACK.has(hostname)
}

/**
 * Hostname for the HLS CORS proxy. When the page is opened on `localhost` but the API
 * URL uses `127.0.0.1` (or Vite same-origin + empty base), using mismatched loopback
 * names breaks some browsers (requests stuck, “Provisional headers”).
 */
export function getProxyHost(): string {
  const override = import.meta.env.VITE_PROXY_HOST
  if (override) return override

  const pageHost =
    typeof window !== 'undefined' ? window.location.hostname : ''
  const base = getApiBase()

  if (base) {
    try {
      const apiHost = new URL(base).hostname
      if (pageHost && isLoopbackHost(pageHost) && isLoopbackHost(apiHost)) {
        return pageHost
      }
      return apiHost
    } catch {
      /* fall through */
    }
  }

  if (pageHost) return pageHost
  return '127.0.0.1'
}
