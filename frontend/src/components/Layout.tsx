import { useCallback, useEffect, useRef, useState, type MouseEvent, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AdSenseLoader } from './adsense/AdSenseLoader'
import { SiteAdBottom, SiteAdTop } from './adsense/SiteAdPlacements'
import { AppFooter } from './AppFooter'
import { HeaderSearchPanel } from './HeaderSearchPanel'
import { useCompactUi } from '../hooks/useCompactUi'
import { navigateBack } from '../lib/navBack'
import { exitPlayerFullscreen } from './MxVideoPlayer/playerFullscreen'
import styles from './Layout.module.css'

const DOC_TITLES: Record<string, string> = {
  '/terms': 'Terms of Use',
  '/privacy': 'Privacy',
  '/content-policy': 'Content Policy',
  '/help': 'Help',
  '/about': 'About',
}

function isWatchPath(pathname: string) {
  return pathname.startsWith('/watch') || pathname === '/player'
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

function IconSearch() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" aria-hidden>
      <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="2" />
      <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function IconBack() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" aria-hidden>
      <path
        d="M15 5l-7 7 7 7"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function IconHome({ active }: { active: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" aria-hidden>
      <path
        d="M4 10.5L12 4l8 6.5V20a1 1 0 01-1 1h-5.5v-6h-3v6H5a1 1 0 01-1-1v-9.5z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
        fill={active ? 'currentColor' : 'none'}
      />
    </svg>
  )
}

export function Layout({
  children,
  localApiFailed = null,
  localApiWaiting = false,
}: {
  children: ReactNode
  localApiFailed?: string | null
  localApiWaiting?: boolean
}) {
  const location = useLocation()
  const navigate = useNavigate()
  const compact = useCompactUi()
  const { pathname } = location
  const [searchOpen, setSearchOpen] = useState(false)
  const searchOpenRef = useRef(false)
  const mainRef = useRef<HTMLElement>(null)
  const pathnameRef = useRef(pathname)
  pathnameRef.current = pathname
  const navigateRef = useRef(navigate)
  navigateRef.current = navigate

  const setSearch = useCallback((open: boolean) => {
    searchOpenRef.current = open
    setSearchOpen(open)
  }, [])

  const watch = isWatchPath(pathname)
  const browse = pathname.startsWith('/browse')
  const docTitle = DOC_TITLES[pathname]
  const home = pathname === '/'
  const searchFullscreen = searchOpen && compact
  // Portrait Watch keeps the global app shell (brand + Search). Fullscreen hides it via CSS.
  const showTop = !searchFullscreen && (!watch || compact)
  const showBottom =
    compact && !watch && !searchFullscreen && (home || browse)
  const bleed = home || watch
  const topTitle = browse ? 'Details' : docTitle
  const showSearch = home || watch || (!browse && !docTitle)

  useEffect(() => {
    setSearch(false)
  }, [pathname, setSearch])

  useEffect(() => {
    if (!searchOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSearch(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [searchOpen])

  const goHome = useCallback(
    (e: MouseEvent) => {
      if (pathname === '/') {
        e.preventDefault()
        setSearch(false)
        mainRef.current?.scrollTo({ top: 0 })
        window.scrollTo({ top: 0 })
      }
    },
    [pathname],
  )

  useEffect(() => {
    window.__mxConsumeBack = () => {
      if (searchOpenRef.current || document.getElementById('header-search-panel')) {
        setSearch(false)
        return 'search'
      }
      const ev = new CustomEvent('mx-android-back', { cancelable: true })
      window.dispatchEvent(ev)
      if (ev.defaultPrevented) return 'handled'
      if (document.fullscreenElement) {
        void document.exitFullscreen()
        return 'fs'
      }
      const fullWindow = document.querySelector(
        '[data-fullwindow="true"]',
      ) as HTMLElement | null
      if (fullWindow) {
        void exitPlayerFullscreen(fullWindow)
        return 'fs'
      }
      const expanded = document.querySelector(
        '.vjs-menu-button[aria-expanded="true"]',
      ) as HTMLElement | null
      if (expanded) {
        expanded.click()
        return 'menu'
      }
      if (pathnameRef.current !== '/') {
        navigateBack(navigateRef.current)
        return 'hist'
      }
      return 'min'
    }
    return () => {
      delete window.__mxConsumeBack
    }
  }, [setSearch])

  const rootClass = [
    styles.root,
    compact ? styles.rootCompact : '',
    watch ? styles.rootPlayer : '',
  ]
    .filter(Boolean)
    .join(' ')

  const mainClass = [styles.main, bleed ? styles.mainBleed : '']
    .filter(Boolean)
    .join(' ')

  return (
    <div className={rootClass}>
      <AdSenseLoader />
      <a href="#main-content" className={styles.skip}>
        Skip to content
      </a>
      {showTop ? (
        <div className={styles.headerBar} data-app-header>
          <header className={styles.header}>
            <div className={styles.headerLeft}>
              {browse || docTitle ? (
                <button
                  type="button"
                  className={styles.iconBtn}
                  aria-label="Back"
                  onClick={() => navigateBack(navigate)}
                >
                  <IconBack />
                </button>
              ) : (
                <Link to="/" className={styles.brand} onClick={goHome}>
                  <BrandMark />
                  MX Scraper
                </Link>
              )}
              {topTitle ? (
                <h1 className={styles.pageTitle}>{topTitle}</h1>
              ) : null}
            </div>
            {showSearch ? (
              <button
                type="button"
                className={
                  compact
                    ? styles.iconBtn
                    : searchOpen
                      ? styles.navSearchActive
                      : styles.navSearch
                }
                aria-label="Search"
                aria-expanded={searchOpen}
                aria-controls="header-search-panel"
                onClick={() => setSearch(!searchOpen)}
              >
                {compact ? <IconSearch /> : 'Search'}
              </button>
            ) : null}
          </header>
          {searchOpen && !compact ? (
            <HeaderSearchPanel onClose={() => setSearch(false)} />
          ) : null}
        </div>
      ) : null}
      {searchFullscreen ? (
        <HeaderSearchPanel
          fullscreen
          onClose={() => setSearch(false)}
        />
      ) : null}
      {localApiWaiting && (
        <p className={styles.banner} role="status">
          Starting local API…
        </p>
      )}
      {localApiFailed && (
        <p className={styles.errorBanner} role="alert">
          {localApiFailed}
        </p>
      )}
      <main
        id="main-content"
        ref={mainRef}
        className={mainClass}
        tabIndex={-1}
      >
        <SiteAdTop />
        {children}
        <SiteAdBottom />
      </main>
      {showBottom ? (
        <nav className={styles.bottomNav} aria-label="Primary" data-app-bottom-nav>
          <Link
            to="/"
            className={styles.bottomItem}
            aria-current={home && !searchOpen ? 'page' : undefined}
            onClick={goHome}
          >
            <IconHome active={home && !searchOpen} />
            Home
          </Link>
          <button
            type="button"
            className={styles.bottomItem}
            aria-current={searchOpen ? 'true' : undefined}
            aria-label="Search"
            onClick={() => setSearch(true)}
          >
            <IconSearch />
            Search
          </button>
        </nav>
      ) : null}
      {!compact && !watch ? <AppFooter /> : null}
    </div>
  )
}
