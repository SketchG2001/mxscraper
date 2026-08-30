/// <reference types="@capacitor/app" />
import type { CapacitorConfig } from '@capacitor/cli'

/**
 * Bundled SPA only. Do not set server.url here — the APK must load local dist/.
 * Web API host: VITE_API_BASE_URL (empty = same-origin / Vite proxy).
 * Android API host: frontend/src/lib/androidLocalApi.json (http://127.0.0.1:8787).
 */
const config: CapacitorConfig = {
  appId: 'com.mxscraper.app',
  appName: 'MX Scraper',
  webDir: 'dist',
  android: {
    backgroundColor: '#050505',
    // WebView origin is https://localhost; API + HLS proxy are http://127.0.0.1.
    // Network security already limits cleartext to loopback.
    allowMixedContent: true,
  },
  plugins: {
    App: {
      // Back is handled in MainActivity → window.__mxConsumeBack (see Layout).
      disableBackButtonHandler: true,
    },
    SystemBars: {
      insetsHandling: 'css',
      style: 'DARK',
    },
  },
}

export default config
