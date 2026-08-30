import type { NavigateFunction } from 'react-router-dom'

export function canGoBackInApp(): boolean {
  const st = window.history.state as { idx?: number } | null
  if (typeof st?.idx === 'number') return st.idx > 0
  return window.history.length > 1
}

/** React Router history first; Home only if this entry is the stack root. */
export function navigateBack(navigate: NavigateFunction): void {
  if (canGoBackInApp()) {
    navigate(-1)
    return
  }
  if (window.location.pathname !== '/') {
    navigate('/', { replace: true })
  }
}
