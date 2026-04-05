/* eslint-disable react-refresh/only-export-components -- context + provider pair */
import { createContext } from 'react'
import type { ReactNode } from 'react'

export type AppAuthValue = {
  authConfigured: boolean
  isAuthenticated: boolean
  isLoading: boolean
  user: { name?: string; email?: string } | undefined
  login: () => void
  signup: () => void
  logout: () => void
  getAccessToken: () => Promise<string | null>
  /** Set when redirect login or token exchange fails (see banner in Layout). */
  authError: Error | undefined
}

const noop: AppAuthValue = {
  authConfigured: false,
  isAuthenticated: false,
  isLoading: false,
  user: undefined,
  login: () => {
    console.warn('Auth0: set VITE_AUTH0_DOMAIN and VITE_AUTH0_CLIENT_ID in .env.local')
  },
  signup: () => {},
  logout: () => {},
  getAccessToken: async () => null,
  authError: undefined,
}

export const AppAuthContext = createContext<AppAuthValue>(noop)

export function AppAuthProvider({
  value,
  children,
}: {
  value: AppAuthValue
  children: ReactNode
}) {
  return (
    <AppAuthContext.Provider value={value}>{children}</AppAuthContext.Provider>
  )
}
