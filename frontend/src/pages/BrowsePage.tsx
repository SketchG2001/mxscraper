import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { FeedbackState } from '../components/FeedbackState'
import { fetchContent, fetchEpisodes } from '../lib/api'
import { episodeProgressUi } from '../lib/watchProgress'
import type { ContentItem } from '../types/api'
import { usePageMeta } from '../hooks/usePageMeta'
import styles from './BrowsePage.module.css'

function sortEpisodes(list: ContentItem[]): ContentItem[] {
  return [...list].sort((a, b) => {
    const sa = Number(a.sequence)
    const sb = Number(b.sequence)
    if (Number.isFinite(sa) && Number.isFinite(sb) && sa !== sb) return sa - sb
    return 0
  })
}

export function BrowsePage() {
  const { contentId } = useParams<{ contentId: string }>()
  const [searchParams] = useSearchParams()
  const type = searchParams.get('type') || 'tvshow'
  const refTitle = searchParams.get('ref_title')?.trim() || undefined
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

  const item = detailQuery.data?.item
  const isShow = type === 'tvshow' && seasons.length > 0
  const sortedEpisodes = useMemo(
    () => sortEpisodes(episodesQuery.data?.episodes ?? []),
    [episodesQuery.data?.episodes],
  )
  const firstEpisode = sortedEpisodes[0] ?? null

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
        <div className={styles.skeletonPoster} />
        <div className={styles.skeletonLine} />
        <div className={styles.skeletonLineShort} />
        <div className={styles.skeletonLine} />
      </div>
    )
  }

  if (detailQuery.isError || !item) {
    return (
      <FeedbackState
        title="Something went wrong"
        message="We couldn't load this title."
        onRetry={() => void detailQuery.refetch()}
      />
    )
  }

  const movieWatchQs = new URLSearchParams({
    type,
    ...(refTitle ? { ref_title: refTitle } : {}),
  })
  const metaBits = [
    item.rating != null &&
    String(item.rating).trim() &&
    String(item.rating) !== '0'
      ? `★ ${item.rating}`
      : null,
    item.year,
    item.publisher,
    ...(item.languages?.length ? [item.languages.slice(0, 3).join(', ')] : []),
  ].filter(Boolean)

  const episodeWatchQs = (ep: ContentItem) => {
    const watchQs = new URLSearchParams({
      type: 'episode',
      seasonId: effectiveSeasonId!,
    })
    if (ep.title?.trim()) watchQs.set('ref_title', ep.title.trim())
    return watchQs
  }

  const seriesState = {
    title: firstEpisode?.title,
    ...(firstEpisode?.image ? { coverImage: firstEpisode.image } : {}),
    seriesContentId: contentId,
    seriesTitle: item.title,
    seriesType: type,
    ...(item.rating != null ? { rating: String(item.rating) } : {}),
  }

  return (
    <article className={styles.page}>
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
        <div className={styles.heroBody}>
          <h1 className={styles.title}>{item.title}</h1>
          {metaBits.length > 0 ? (
            <p className={styles.meta}>{metaBits.join('   ')}</p>
          ) : null}
          <div className={styles.actions}>
            {!isShow ? (
              <Link
                to={`/watch/${encodeURIComponent(contentId)}?${movieWatchQs}`}
                state={{
                  title: item.title,
                  ...(item.image ? { coverImage: item.image } : {}),
                  ...(item.rating != null ? { rating: String(item.rating) } : {}),
                }}
                className={styles.play}
              >
                Play
              </Link>
            ) : firstEpisode && effectiveSeasonId ? (
              <Link
                to={`/watch/${encodeURIComponent(firstEpisode.id)}?${episodeWatchQs(firstEpisode)}`}
                state={seriesState}
                className={styles.play}
              >
                Play
              </Link>
            ) : episodesQuery.isLoading ? (
              <span className={styles.playDisabled}>Play</span>
            ) : null}
          </div>
          {item.description && (
            <p className={styles.desc}>{item.description.slice(0, 600)}</p>
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
          </div>

          {episodesQuery.isLoading && (
            <div className={styles.epSkel} aria-busy="true" aria-label="Loading episodes">
              <div className={styles.skeletonLine} />
              <div className={styles.skeletonLine} />
              <div className={styles.skeletonLineShort} />
            </div>
          )}
          {episodesQuery.isError && (
            <FeedbackState
              title="Couldn’t load episodes"
              onRetry={() => void episodesQuery.refetch()}
            />
          )}
          {!episodesQuery.isLoading &&
            !episodesQuery.isError &&
            sortedEpisodes.length === 0 && (
              <FeedbackState
                title="No episodes"
                message="This season doesn’t have any episodes yet."
              />
            )}
          <ul className={styles.epList}>
            {sortedEpisodes.map((ep: ContentItem) => {
              const prog =
                effectiveSeasonId != null
                  ? episodeProgressUi(ep.id, effectiveSeasonId)
                  : null
              const desc = ep.description?.trim()
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
                    <Link
                      to={`/watch/${encodeURIComponent(ep.id)}?${episodeWatchQs(ep)}`}
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
