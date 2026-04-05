import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { BannerItem } from '../types/api'
import styles from './MxPlayerBanners.module.css'

type Props = {
  items: BannerItem[]
  /** Shown when MX returned no posters (optional). */
  fetchError?: string | null
  children?: React.ReactNode
}

function truncateDesc(s: string, max: number): string {
  const t = s.trim()
  if (!t) return ''
  if (t.length <= max) return t
  const cut = t.slice(0, max)
  const lastSpace = cut.lastIndexOf(' ')
  return (lastSpace > 40 ? cut.slice(0, lastSpace) : cut) + '…'
}

function metaLineMx(b: BannerItem): string {
  const langs = b.languages?.length ? b.languages.join(', ') : ''
  const gens = b.genres?.length ? b.genres.slice(0, 6).join(', ') : ''
  if (langs && gens) return `${langs} | ${gens}`
  return langs || gens || ''
}

function primarySpotlightBadge(type: string): string {
  const t = (type || '').toLowerCase()
  if (t === 'tvshow' || t === 'show' || t === 'episode') return 'New series'
  if (t === 'movie' || t === 'movies' || t === 'film') return 'New movie'
  return 'Featured'
}

function formatRatingLabel(rating: string | null | undefined): string {
  const s = (rating || '').trim()
  if (!s) return ''
  if (/^u\/?a/i.test(s) || /^\d/.test(s) || s.length <= 12) return s
  return s
}

export function MxPlayerBanners({ items, fetchError, children }: Props) {
  const navigate = useNavigate()
  const [active, setActive] = useState(0)
  const [muteDecor, setMuteDecor] = useState(true)
  const n = items.length

  useEffect(() => {
    setActive(0)
  }, [items])

  useEffect(() => {
    if (n <= 1) return
    const id = window.setInterval(() => {
      setActive((i) => (i + 1) % n)
    }, 8500)
    return () => window.clearInterval(id)
  }, [n])

  const go = useCallback(
    (b: BannerItem) => {
      const t = b.type || 'tvshow'
      const q = new URLSearchParams({ type: t })
      if (b.title?.trim()) q.set('ref_title', b.title.trim())
      void navigate(`/browse/${encodeURIComponent(b.id)}?${q}`)
    },
    [navigate],
  )

  const prevSlide = useCallback(() => {
    if (n <= 1) return
    setActive((i) => (i - 1 + n) % n)
  }, [n])

  const nextSlide = useCallback(() => {
    if (n <= 1) return
    setActive((i) => (i + 1) % n)
  }, [n])

  const safeIndex = n > 0 ? Math.min(active, n - 1) : 0
  const current = n > 0 ? items[safeIndex] : null

  const slideBg = (b: BannerItem) =>
    (b.backdrop || b.image || '').trim() || undefined

  const ratingLabel = current
    ? formatRatingLabel(current.rating ?? undefined)
    : ''

  return (
    <section
      className={`${styles.wrap} ${n > 0 ? styles.wrapWithBg : ''}`}
      aria-label="Featured from MX Player"
    >
      {n > 0 && (
        <div className={styles.backdrop} aria-hidden>
          {items.map((b, i) => (
            <div
              key={b.id}
              className={styles.slide}
              data-active={i === safeIndex}
              style={
                slideBg(b)
                  ? { backgroundImage: `url(${slideBg(b)})` }
                  : undefined
              }
            />
          ))}
          <div className={styles.scrim} />
        </div>
      )}
      <div className={styles.content}>
        <div className={styles.heroStack}>
          {current && (
            <div className={styles.heroPanel}>
              <div className={styles.badgeRow}>
                {ratingLabel ? (
                  <span className={styles.ratingPill}>{ratingLabel}</span>
                ) : null}
                <span className={styles.badgeBlue}>
                  {primarySpotlightBadge(current.type)}
                </span>
                <span className={styles.badgeMuted}>
                  {(current.type || 'content').replace(/_/g, ' ')}
                </span>
              </div>
              <h2 className={styles.heroTitle}>{current.title}</h2>
              {metaLineMx(current) ? (
                <p className={styles.heroMeta}>{metaLineMx(current)}</p>
              ) : null}
              {current.description?.trim() ? (
                <p className={styles.heroDesc}>
                  {truncateDesc(current.description, 260)}
                </p>
              ) : null}
              <div className={styles.heroActions}>
                <button
                  type="button"
                  className={styles.btnPlay}
                  onClick={() => go(current)}
                >
                  <span className={styles.playIcon} aria-hidden>
                    ▶
                  </span>
                  Play
                </button>
                <button
                  type="button"
                  className={styles.btnSecondary}
                  onClick={() => go(current)}
                >
                  More info
                </button>
                <button
                  type="button"
                  className={styles.btnMyList}
                  onClick={() => {
                    try {
                      const k = 'mxscraper_mylist_ids'
                      const raw = localStorage.getItem(k)
                      const ids: string[] = raw ? JSON.parse(raw) : []
                      if (!ids.includes(current.id)) {
                        ids.unshift(current.id)
                        localStorage.setItem(k, JSON.stringify(ids.slice(0, 120)))
                      }
                    } catch {
                      /* ignore quota / private mode */
                    }
                  }}
                  title="Save to this device (local list)"
                >
                  <span className={styles.myListPlus} aria-hidden>
                    +
                  </span>
                  Add to my list
                </button>
              </div>
            </div>
          )}
          {children}
          {fetchError && n === 0 && (
            <p className={styles.bannerError} role="status">
              Spotlight titles unavailable ({fetchError}). Search in the header still works.
            </p>
          )}
        </div>

        {n > 1 ? (
          <div className={styles.heroBottom}>
            <div className={styles.dots} role="tablist" aria-label="Featured slides">
              {items.map((b, i) => (
                <button
                  key={b.id}
                  type="button"
                  role="tab"
                  aria-selected={i === safeIndex}
                  aria-label={`Show ${b.title}`}
                  className={styles.dot}
                  data-active={i === safeIndex}
                  onClick={() => setActive(i)}
                />
              ))}
            </div>
            <div className={styles.bannerControls}>
              <button
                type="button"
                className={styles.ctrlBtn}
                aria-label="Previous spotlight"
                onClick={prevSlide}
              >
                ‹
              </button>
              <button
                type="button"
                className={styles.ctrlBtn}
                aria-label="Next spotlight"
                onClick={nextSlide}
              >
                ›
              </button>
              <button
                type="button"
                className={styles.ctrlBtn}
                aria-label={muteDecor ? 'Mute (UI only)' : 'Unmute (UI only)'}
                aria-pressed={muteDecor}
                onClick={() => setMuteDecor((m) => !m)}
              >
                {muteDecor ? (
                  <svg
                    className={styles.muteGlyph}
                    viewBox="0 0 24 24"
                    width="20"
                    height="20"
                    fill="currentColor"
                    aria-hidden
                  >
                    <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.73 4.73L19.73 21 21 19.73 4.27 3zM12 4L9.91 6.09 12 8.18V4z" />
                  </svg>
                ) : (
                  <svg
                    className={styles.muteGlyph}
                    viewBox="0 0 24 24"
                    width="20"
                    height="20"
                    fill="currentColor"
                    aria-hidden
                  >
                    <path d="M3 10v4h4l5 5V5L7 10H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        ) : null}
      </div>

      {n > 0 && (
        <div className={styles.railWrap}>
          <p className={styles.railLabel}>Trending &amp; featured</p>
          <ul className={styles.rail} aria-label="Pick a highlighted title">
            {items.map((b, i) => (
              <li key={b.id}>
                <button
                  type="button"
                  className={styles.railItem}
                  data-active={i === safeIndex}
                  onClick={() => setActive(i)}
                  title={b.title}
                >
                  <img src={b.image} alt="" loading="lazy" decoding="async" />
                  <span className={styles.railTitle}>{b.title}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
