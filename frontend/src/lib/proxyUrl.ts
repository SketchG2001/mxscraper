import { isAndroidNative } from './apiBase'

/**
 * Prefix CDN HLS URL so it loads through the CORS proxy.
 *
 * Web HTTPS: nginx /hls/ (no mixed content).
 * Web HTTP: direct http://<host>:<proxyPort>/.
 * Android APK: no nginx. Proxy is the in-process server on 127.0.0.1
 * (IPv4 only). Capacitor origin is https://localhost — /hls/ would 404.
 */
export function proxiedStreamUrl(
  originalUrl: string,
  proxyHost: string,
  proxyPort: number,
): string {
  if (isAndroidNative()) {
    return `http://127.0.0.1:${proxyPort}/${originalUrl}`
  }

  const isSecure =
    typeof window !== 'undefined' && window.location.protocol === 'https:'

  if (isSecure) {
    return `${window.location.origin}/hls/${originalUrl}`
  }

  const host = proxyHost.replace(/\/$/, '')
  return `http://${host}:${proxyPort}/${originalUrl}`
}
