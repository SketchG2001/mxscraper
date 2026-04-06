/**
 * Prefix CDN HLS URL so it loads through the CORS proxy.
 *
 * On HTTPS pages direct http://<host>:8513 is blocked (mixed content),
 * so we route through nginx's /hls/ path which proxies to the same backend.
 * On HTTP (local dev) we hit the proxy port directly.
 */
export function proxiedStreamUrl(
  originalUrl: string,
  proxyHost: string,
  proxyPort: number,
): string {
  const isSecure =
    typeof window !== 'undefined' && window.location.protocol === 'https:'

  if (isSecure) {
    return `${window.location.origin}/hls/${originalUrl}`
  }

  const host = proxyHost.replace(/\/$/, '')
  return `http://${host}:${proxyPort}/${originalUrl}`
}
