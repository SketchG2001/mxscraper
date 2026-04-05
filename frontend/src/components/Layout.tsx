import { OAuthError } from '@auth0/auth0-react'
import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAppAuth } from '../hooks/useAppAuth'
import { AdSenseLoader } from './adsense/AdSenseLoader'
import { SiteAdBottom, SiteAdTop } from './adsense/SiteAdPlacements'
import { AppFooter } from './AppFooter'
import { HeaderSearchPanel } from './HeaderSearchPanel'
import styles from './Layout.module.css'

function formatAuthErrorMessage(e: Error): string {
  if (e instanceof OAuthError) {
    const parts = [e.error, e.error_description].filter(Boolean)
    if (parts.length) return parts.join(': ')
  }
  return e.message
}

function BrandMark() {
  return (
    <span className={styles.brandMark} aria-hidden>
      <svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M8 5v14l11-7L8 5z" />
      </svg>
    </span>
  )
}

export function Layout({ children }: { children: React.ReactNode }) {
  const auth = useAppAuth()
  const location = useLocation()
  const [searchOpen, setSearchOpen] = useState(false)

  useEffect(() => {
    setSearchOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!searchOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSearchOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [searchOpen])

  return (
    <div className={styles.root}>
      <AdSenseLoader />
      <a href="#main-content" className={styles.skip}>
        Skip to content
      </a>
      <div className={styles.headerBar}>
        <header className={styles.header}>
          <div className={styles.headerLeft}>
            <Link to="/" className={styles.brand}>
              <BrandMark />
              MX Scraper
            </Link>
            <button
              type="button"
              className={searchOpen ? styles.navSearchActive : styles.navSearch}
              aria-expanded={searchOpen}
              aria-controls="header-search-panel"
              onClick={() => setSearchOpen((o) => !o)}
            >
              Search
            </button>
          </div>
          <nav className={styles.nav}>
            {auth.isLoading ? (
              <span className={styles.muted}>…</span>
            ) : auth.isAuthenticated ? (
              <>
                <span className={styles.user}>
                  {auth.user?.name ?? auth.user?.email ?? 'Signed in'}
                </span>
                <button type="button" className={styles.btn} onClick={auth.logout}>
                  Log out
                </button>
              </>
            ) : (
              <>
                <button type="button" className={styles.btn} onClick={auth.signup}>
                  Sign up
                </button>
                <button type="button" className={styles.btnPrimary} onClick={auth.login}>
                  Log in
                </button>
              </>
            )}
          </nav>
        </header>
        {searchOpen && <HeaderSearchPanel onClose={() => setSearchOpen(false)} />}
      </div>
      {auth.authError && (
        <p className={styles.errorBanner} role="alert">
          <strong>Sign-in failed:</strong>{' '}
          {formatAuthErrorMessage(auth.authError)}.{' '}
          {formatAuthErrorMessage(auth.authError).includes(
            'not authorized to access resource',
          ) ? (
            <>
              In Auth0: open <strong>Applications → APIs</strong>, click your API
              (Identifier must match <code>VITE_AUTH0_AUDIENCE</code>), then allow this
              SPA — e.g. <strong>Applications →</strong> your SPA <strong>→ APIs</strong>{' '}
              tab → set <strong>MX Scraper API</strong> to <strong>Authorized</strong>{' '}
              for <strong>User</strong> access (not only Machine-to-Machine). After
              that, you can set <code>VITE_AUTH0_AUDIENCE_ON_LOGIN=true</code> for a
              simpler token flow.
            </>
          ) : (
            <>
              Check <code>/oauth/token</code> in the Network tab. Callback / Logout /
              Web Origins must include <code>http://localhost:5173</code>. Do not set{' '}
              <code>VITE_AUTH0_AUDIENCE_ON_LOGIN=true</code> until the SPA is
              authorized for your API in Auth0.
            </>
          )}
        </p>
      )}
      {!auth.authConfigured && (
        <p className={styles.banner}>
          Auth0 is not configured — search works; add{' '}
          <code>VITE_AUTH0_*</code> in <code>.env.local</code> for playback.
        </p>
      )}
      <main id="main-content" className={styles.main} tabIndex={-1}>
        <SiteAdTop />
        {children}
        <SiteAdBottom />
      </main>
      <AppFooter />
    </div>
  )
}
