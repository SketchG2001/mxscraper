import { useQueries } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { resolveContinueWatchingThumb } from '../lib/continueWatchingThumbs'
import {
  formatPlaybackClock,
  listContinueWatching,
  patchWatchProgressPoster,
  watchUrlForProgress,
} from '../lib/watchProgress'
import { CatalogSectionTitle } from './catalog/CatalogSectionTitle'
import styles from './ContinueWatching.module.css'

export function ContinueWatching() {
  const [rev, setRev] = useState(0)

  useEffect(() => {
    const bump = () => setRev((r) => r + 1)
    document.addEventListener('visibilitychange', bump)
    window.addEventListener('focus', bump)
    window.addEventListener('storage', bump)
    return () => {
      document.removeEventListener('visibilitychange', bump)
      window.removeEventListener('focus', bump)
      window.removeEventListener('storage', bump)
    }
  }, [])

  const items = useMemo(() => listContinueWatching(12), [rev])

  const thumbQueries = useQueries({
    queries: items.map((it) => ({
      queryKey: ['continue-thumb', it.key, it.contentId, it.type, it.seasonId],
      queryFn: () => resolveContinueWatchingThumb(it),
      enabled: Boolean(it.contentId) && !it.poster?.trim(),
      staleTime: 86_400_000,
    })),
  })

  const thumbSig = useMemo(
    () => thumbQueries.map((q) => `${q.status}:${q.data ?? ''}`).join('|'),
    [thumbQueries],
  )

  useEffect(() => {
    let bumped = false
    items.forEach((it, i) => {
      const url = thumbQueries[i]?.data
      if (typeof url === 'string' && url.trim() && !it.poster) {
        patchWatchProgressPoster(it.key, url)
        bumped = true
      }
    })
    if (bumped) setRev((r) => r + 1)
  }, [items, thumbSig])

  if (items.length === 0) return null

  return (
    <section className={styles.wrap} aria-labelledby="continue-heading">
      <div className={styles.head}>
        <CatalogSectionTitle
          variant="row"
          title="Continue watching"
          id="continue-heading"
          className={styles.titleWrap}
        />
        <p className={styles.hint}>Saved on this device — pick up where you left off.</p>
      </div>
      <div className={styles.rail}>
        {items.map((it, i) => {
          const thumbUrl =
            it.poster?.trim() ||
            (typeof thumbQueries[i]?.data === 'string'
              ? thumbQueries[i]?.data?.trim()
              : '') ||
            ''
          return (
            <Link
              key={it.key}
              to={watchUrlForProgress(it)}
              state={{
                title: it.title,
                ...(thumbUrl ? { coverImage: thumbUrl } : {}),
              }}
              className={styles.card}
            >
              <div className={styles.thumbWrap}>
                {thumbUrl ? (
                  <img
                    src={thumbUrl}
                    alt=""
                    className={styles.thumb}
                    loading="lazy"
                    decoding="async"
                  />
                ) : (
                  <div className={styles.thumbPh} aria-hidden />
                )}
                <span className={styles.badge}>
                  {it.percent >= 5 ? 'Resume' : 'Play'}
                </span>
                <div
                  className={styles.bar}
                  style={{ width: `${Math.min(100, it.percent)}%` }}
                />
              </div>
              <span className={styles.cardTitle}>{it.title}</span>
              <span className={styles.meta}>
                {formatPlaybackClock(it.position)}
                {it.duration > 0 ? ` / ${formatPlaybackClock(it.duration)}` : ''}
              </span>
            </Link>
          )
        })}
      </div>
    </section>
  )
}
