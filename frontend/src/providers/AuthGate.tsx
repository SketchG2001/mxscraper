import { Auth0Provider, useAuth0 } from '@auth0/auth0-react'
import { useEffect, type ReactNode } from 'react'
import { BrowserRouter, useNavigate } from 'react-router-dom'
import {
  AppAuthProvider,
  type AppAuthValue,
} from '../contexts/AppAuthContext'
import { getSafeReturnTo } from '../lib/authReturnTo'

/** Auth0 expects host only (no https://). */
function normalizeAuth0Domain(raw: string | undefined): string {
  if (!raw) return ''
  let d = raw.trim()
  if (d.startsWith('https://')) d = d.slice(8)
  if (d.startsWith('http://')) d = d.slice(7)
  return d.replace(/\/$/, '')
}

/** Only after Auth0 authorizes this SPA for your custom API; otherwise /oauth/token fails at login. */
const audienceOnLogin =
  import.meta.env.VITE_AUTH0_AUDIENCE_ON_LOGIN === 'true'

const apiScope = import.meta.env.VITE_AUTH0_API_SCOPE?.trim() || undefined

const disabledAuth: AppAuthValue = {
  authConfigured: false,
  isAuthenticated: false,
  isLoading: false,
  user: undefined,
  login: () => {
    console.warn(
      'Configure VITE_AUTH0_DOMAIN and VITE_AUTH0_CLIENT_ID for login.',
    )
  },
  signup: () => {},
  logout: () => {},
  getAccessToken: async () => null,
  authError: undefined,
}

/** Opt-in: set VITE_AUTH0_USE_REFRESH_TOKENS=true after enabling Refresh Token Rotation in Auth0. */
const useRefreshTokens =
  import.meta.env.VITE_AUTH0_USE_REFRESH_TOKENS === 'true'

const loginScope = useRefreshTokens
  ? 'openid profile email offline_access'
  : 'openid profile email'

function Auth0Bridge({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const {
    isAuthenticated,
    isLoading,
    user,
    error,
    loginWithRedirect,
    logout,
    getAccessTokenSilently,
  } = useAuth0()
  const audience = import.meta.env.VITE_AUTH0_AUDIENCE?.trim() || undefined

  useEffect(() => {
    if (!error) return
    const u = new URL(window.location.href)
    if (
      !u.searchParams.has('code') &&
      !u.searchParams.has('error')
    ) {
      return
    }
    for (const key of [
      'code',
      'state',
      'error',
      'error_description',
      'iss',
    ]) {
      u.searchParams.delete(key)
    }
    const q = u.searchParams.toString()
    const next = u.pathname + (q ? `?${q}` : '')
    navigate(next, { replace: true })
  }, [error, navigate])

  const value: AppAuthValue = {
    authConfigured: true,
    isAuthenticated,
    isLoading,
    user: user ?? undefined,
    authError: error,
    login: () =>
      void loginWithRedirect({
        appState: {
          returnTo: getSafeReturnTo(),
        },
      }),
    signup: () =>
      void loginWithRedirect({
        authorizationParams: { screen_hint: 'signup' },
        appState: {
          returnTo: getSafeReturnTo(),
        },
      }),
    logout: () =>
      void logout({ logoutParams: { returnTo: window.location.origin } }),
    getAccessToken: async () => {
      try {
        if (!audience) {
          return await getAccessTokenSilently({
            authorizationParams: { scope: loginScope },
          })
        }
        const authorizationParams = {
          audience,
          ...(apiScope ? { scope: apiScope } : {}),
        }
        try {
          return await getAccessTokenSilently({ authorizationParams })
        } catch {
          return await getAccessTokenSilently({
            authorizationParams,
            cacheMode: 'off',
          })
        }
      } catch (e) {
        console.warn('getAccessTokenSilently failed', e)
        return null
      }
    },
  }

  return <AppAuthProvider value={value}>{children}</AppAuthProvider>
}

/** Must render under BrowserRouter so onRedirectCallback can use navigate(). */
function Auth0ProviderWithNav({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const domain = normalizeAuth0Domain(import.meta.env.VITE_AUTH0_DOMAIN)
  const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID?.trim() || ''
  const audience = import.meta.env.VITE_AUTH0_AUDIENCE?.trim() || undefined

  if (!domain || !clientId) {
    return (
      <AppAuthProvider value={disabledAuth}>{children}</AppAuthProvider>
    )
  }

  return (
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      useRefreshTokens={useRefreshTokens}
      cacheLocation="localstorage"
      authorizationParams={{
        redirect_uri: `${window.location.origin}`,
        ...(audienceOnLogin && audience ? { audience } : {}),
        scope: loginScope,
      }}
      onRedirectCallback={(appState) => {
        const target = appState?.returnTo ?? '/'
        navigate(target, { replace: true })
      }}
    >
      <Auth0Bridge>{children}</Auth0Bridge>
    </Auth0Provider>
  )
}

export function AuthGate({ children }: { children: ReactNode }) {
  return (
    <BrowserRouter>
      <Auth0ProviderWithNav>{children}</Auth0ProviderWithNav>
    </BrowserRouter>
  )
}
