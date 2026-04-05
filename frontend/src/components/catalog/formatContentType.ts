/** MX-style row label under posters (e.g. ``TV SHOW``). */
export function formatContentType(type: string): string {
  return (type || '')
    .replace(/_/g, ' ')
    .trim()
    .toUpperCase() || 'TITLE'
}
