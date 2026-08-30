import type { ReactNode } from 'react'
import { BrowserRouter } from 'react-router-dom'

/** Router wrapper. Named AuthGate for the existing App/main imports. */
export function AuthGate({ children }: { children: ReactNode }) {
  return <BrowserRouter>{children}</BrowserRouter>
}
