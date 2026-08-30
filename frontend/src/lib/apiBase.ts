import { Capacitor } from '@capacitor/core'
import androidLocalApi from './androidLocalApi.json'

export function isAndroidNative(): boolean {
  return Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android'
}

/**
 * API origin.
 * - VITE_API_BASE_URL if set (web production / explicit override)
 * - Android native: http://127.0.0.1:<port> from androidLocalApi.json
 * - otherwise empty → same-origin (Vite dev proxy)
 */
export function getApiBase(): string {
  const env = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
  if (env) return env
  if (isAndroidNative()) {
    return `http://${androidLocalApi.host}:${androidLocalApi.port}`
  }
  return ''
}

export function apiUrl(path: string): string {
  const base = getApiBase()
  const p = path.startsWith('/') ? path : `/${path}`
  return base ? `${base}${p}` : p
}
