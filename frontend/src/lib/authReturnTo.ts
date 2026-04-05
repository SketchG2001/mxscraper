/** Build a safe post-login path: never carry OAuth ?code= / ?state= (breaks the next login). */
export function getSafeReturnTo(): string {
  const path = window.location.pathname
  const params = new URLSearchParams(window.location.search)
  for (const key of [
    'code',
    'state',
    'error',
    'error_description',
    'iss',
  ]) {
    params.delete(key)
  }
  const q = params.toString()
  return q ? `${path}?${q}` : path
}
