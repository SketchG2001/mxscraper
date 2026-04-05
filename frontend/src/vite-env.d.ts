/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_AUTH0_DOMAIN: string
  readonly VITE_AUTH0_CLIENT_ID: string
  readonly VITE_AUTH0_AUDIENCE: string
  readonly VITE_AUTH0_USE_REFRESH_TOKENS: string
  readonly VITE_AUTH0_AUDIENCE_ON_LOGIN: string
  /** Space-separated API permissions if your Auth0 API uses RBAC scopes */
  readonly VITE_AUTH0_API_SCOPE: string
  readonly VITE_PROXY_HOST: string
  /** Google AdSense publisher id, e.g. ca-pub-1234567890123456 */
  readonly VITE_ADSENSE_CLIENT: string
  /** Optional display ad slot (numeric string from AdSense UI) */
  readonly VITE_ADSENSE_SLOT_TOP: string
  readonly VITE_ADSENSE_SLOT_BOTTOM: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
