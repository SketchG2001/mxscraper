import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { fetchBanners, fetchContent, fetchEpisodes } from '../lib/api'
import { episodeProgressUi } from '../lib/watchProgress'
import type { ContentItem } from '../types/api'
import { useAppAuth } from '../hooks/useAppAuth'
import { usePageMeta } from '../hooks/usePageMeta'
import styles from './BrowsePage.module.css'

export function BrowsePage() {
  const { contentId } = useParams<{ contentId: string }>()
  const [searchParams] = useSearchParams()
  const type = searchParams.get('type') || 'tvshow'
  const refTitle = searchParams.get('ref_title')?.trim() || undefined
  const auth = useAppAuth()

  const [seasonId, setSeasonId] = useState<string | null>(null)

  const detailQuery = useQuery({
    queryKey: ['content', contentId, type, refTitle],
    queryFn: () => fetchContent(contentId!, type, refTitle),
    enabled: Boolean(contentId),
  })

  const seasons = detailQuery.data?.seasons ?? []
  const effectiveSeasonId = seasonId ?? seasons[0]?.id ?? null

  const episodesQuery = useQuery({
    queryKey: ['episodes', effectiveSeasonId],
    queryFn: () => fetchEpisodes(effectiveSeasonId!),
    enabled: Boolean(effectiveSeasonId) && type === 'tvshow',
  })

  const bannersQuery = useQuery({
    queryKey: ['banners'],
    queryFn: () => fetchBanners(8),
    staleTime: 30 * 60 * 1000,
  })

  const item = detailQuery.data?.item

  const isShow = type === 'tvshow' && seasons.length > 0

  const metaTitle = useMemo(() => {
    if (!contentId) return 'Browse'
    if (detailQuery.isError || (!detailQuery.isLoading && !item)) return 'Not found'
    if (item?.title) return item.title
    return 'Loading…'
  }, [contentId, detailQuery.isError, detailQuery.isLoading, item])

  const metaDesc = useMemo(
    () =>
      item?.description?.replace(/\s+/g, ' ').trim().slice(0, 160) ?? undefined,
    [item?.description],
  )

  usePageMeta(metaTitle, metaDesc)

  if (!contentId) {
    return <p className={styles.muted}>Missing content id.</p>
  }

  if (detailQuery.isLoading) {
    return (
      <div className={styles.loadingPage} aria-busy="true" aria-label="Loading content">
        <div className={styles.skeletonHero} />
        <div className={styles.skeletonLine} />
        <div className={styles.skeletonLineShort} />
      </div>
    )
  }

  if (detailQuery.isError || !item) {
    return (
      <p className={styles.error}>
        {detailQuery.error instanceof Error
          ? detailQuery.error.message
          : 'Not found.'}
      </p>
    )
  }

  return (
    <article className={styles.page}>
      <Link to="/" className={styles.back}>
        ← Home
      </Link>

      {bannersQuery.data?.items && bannersQuery.data.items.length > 0 && (
        <div className={styles.mxStrip} aria-label="More from MX Player">
          <span className={styles.mxStripLabel}>More from MX Player</span>
          <div className={styles.mxStripScroll}>
            {bannersQuery.data.items.map((b) => (
              <Link
                key={b.id}
                to={`/browse/${encodeURIComponent(b.id)}?type=${encodeURIComponent(b.type || 'tvshow')}`}
                className={styles.mxStripCard}
              >
                <img src={b.image} alt="" loading="lazy" decoding="async" />
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className={styles.hero}>
        {item.image && (
          <img
            src={item.image}
            alt=""
            className={styles.poster}
            loading="eager"
            decoding="async"
          />
        )}
        <div>
          <h1 className={styles.title}>{item.title}</h1>
          <p className={styles.meta}>
            {[item.year, item.type, item.publisher].filter(Boolean).join(' · ')}
          </p>
          {item.description && (
            <p className={styles.desc}>{item.description.slice(0, 600)}</p>
          )}
          {!isShow && (
            <div className={styles.actions}>
              {!auth.authConfigured ? (
                <span className={styles.muted}>Configure Auth0 in .env.local to play</span>
              ) : auth.isAuthenticated ? (
                <Link
                  to={`/watch/${encodeURIComponent(contentId!)}?${new URLSearchParams({
                    type,
                    ...(refTitle ? { ref_title: refTitle } : {}),
                  })}`}
                  state={{
                    title: item.title,
                    ...(item.image ? { coverImage: item.image } : {}),
                    ...(item.rating != null ? { rating: String(item.rating) } : {}),
                  }}
                  className={styles.play}
                >
                  Play
                </Link>
              ) : (
                <button type="button" className={styles.play} onClick={auth.login}>
                  Log in to play
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {isShow && (
        <section className={styles.episodes} aria-label="Episodes">
          <div className={styles.seasonRow}>
            <label htmlFor="season">Season</label>
            <select
              id="season"
              className={styles.select}
              value={effectiveSeasonId ?? ''}
              onChange={(e) => setSeasonId(e.target.value)}
            >
              {seasons.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title} ({s.episodesCount})
                </option>
              ))}
            </select>
            {episodesQuery.data?.episodes && (
              <span className={styles.epCount}>
                {episodesQuery.data.episodes.length} episode
                {episodesQuery.data.episodes.length === 1 ? '' : 's'} loaded
              </span>
            )}
          </div>

          {episodesQuery.isLoading && <p className={styles.muted}>Loading episodes…</p>}
          {episodesQuery.isError && (
            <p className={styles.error}>{String(episodesQuery.error)}</p>
          )}
          <ul className={styles.epList}>
            {(episodesQuery.data?.episodes ?? []).map((ep: ContentItem) => {
              const prog =
                effectiveSeasonId != null
                  ? episodeProgressUi(ep.id, effectiveSeasonId)
                  : null
              const desc = ep.description?.trim()
              const watchQs = new URLSearchParams({
                type: 'episode',
                seasonId: effectiveSeasonId!,
              })
              if (ep.title?.trim()) watchQs.set('ref_title', ep.title.trim())
              return (
                <li key={ep.id} className={styles.epItem}>
                  <div className={styles.epThumbWrap}>
                    {ep.image ? (
                      <>
                        <img
                          src={ep.image}
                          alt=""
                          className={styles.epThumb}
                          loading="lazy"
                          decoding="async"
                        />
                        {prog?.showBar ? (
                          <div
                            className={styles.epThumbProgress}
                            style={{ width: `${prog.percent}%` }}
                          />
                        ) : null}
                      </>
                    ) : (
                      <div className={styles.epThumbPh} aria-hidden>
                        <span className={styles.epThumbPhIcon}>▶</span>
                      </div>
                    )}
                  </div>
                  <div className={styles.epBody}>
                    <strong className={styles.epTitle}>{ep.title}</strong>
                    {prog?.showBar ? (
                      <p className={styles.epProgMeta}>
                        <span className={styles.epProgDot} />
                        Resume at {prog.atLabel}
                      </p>
                    ) : null}
                    {prog?.isAlmostDone ? (
                      <p className={styles.epProgDone}>Watched · almost done</p>
                    ) : null}
                    {desc ? (
                      <p className={styles.epDesc}>
                        {desc.length > 220 ? `${desc.slice(0, 220)}…` : desc}
                      </p>
                    ) : null}
                  </div>
                  <div className={styles.epActions}>
                    {!auth.authConfigured ? (
                      <span className={styles.muted}>Auth0</span>
                    ) : auth.isAuthenticated ? (
                      <Link
                        to={`/watch/${encodeURIComponent(ep.id)}?${watchQs}`}
                        state={{
                          title: ep.title,
                          ...(ep.image ? { coverImage: ep.image } : {}),
                          seriesContentId: contentId,
                          seriesTitle: item.title,
                          seriesType: type,
                          ...(item.rating != null
                            ? { rating: String(item.rating) }
                            : {}),
                        }}
                        className={styles.playSm}
                      >
                        {prog?.showBar ? 'Resume' : 'Play'}
                      </Link>
                    ) : (
                      <button
                        type="button"
                        className={styles.playSm}
                        onClick={auth.login}
                      >
                        Log in
                      </button>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </section>
      )}
    </article>
  )
}
