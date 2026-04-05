/** Prefix CDN HLS URL so it loads through the backend CORS proxy. */
export function proxiedStreamUrl(
  originalUrl: string,
  proxyHost: string,
  proxyPort: number,
): string {
  const host = proxyHost.replace(/\/$/, '')
  return `http://${host}:${proxyPort}/${originalUrl}`
}
