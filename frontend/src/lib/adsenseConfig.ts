/** Google AdSense — optional; enable with env vars (see .env.example). */

function trimEnv(v: string | undefined): string {
  return (v ?? '').trim()
}

/** e.g. ca-pub-1234567890123456 */
export function adsenseClientId(): string {
  return trimEnv(import.meta.env.VITE_ADSENSE_CLIENT)
}

export function adsenseSlotTop(): string {
  return trimEnv(import.meta.env.VITE_ADSENSE_SLOT_TOP)
}

export function adsenseSlotBottom(): string {
  return trimEnv(import.meta.env.VITE_ADSENSE_SLOT_BOTTOM)
}

export function isAdsenseConfigured(): boolean {
  return /^ca-pub-\d+$/i.test(adsenseClientId())
}

export function isWatchOrPlayerPath(pathname: string): boolean {
  return pathname.startsWith('/watch/') || pathname === '/player'
}
