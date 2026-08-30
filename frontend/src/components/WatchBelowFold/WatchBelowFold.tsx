import { Link } from 'react-router-dom'
import { episodeProgressUi } from '../../lib/watchProgress'
import type { ContentItem } from '../../types/api'
import styles from './WatchBelowFold.module.css'

export type WatchSeriesLinkState = {
  seriesContentId: string
  seriesTitle?: string
  seriesType?: string
}

type Props = {
  displayTitle: string
  episodeMetaLine?: string
  description?: string | null
  metaParts: string[]
  audioLanguages?: { id: string; name: string }[]
  sortedEpisodes: ContentItem[]
  currentContentId: string
  seasonId: string | null
  episodesLoading: boolean
  episodesError: string | null
  detailLoading: boolean
  detailError: string | null
  contentType: string
  seriesBrowse: { href: string; label: string } | null
  movieBrowse: { href: string; label: string } | null
  seriesState: WatchSeriesLinkState | null
}

export function formatDurationSeconds(sec?: number): string | null {
  if (typeof sec !== 'number' || !Number.isFinite(sec) || sec <= 0) return null
  const m = Math.floor(sec / 60)
  if (m < 60) return `${m} min`
  const h = Math.floor(m / 60)
  const rm = m % 60
  return rm ? `${h}h ${rm}m` : `${h}h`
}

export function WatchBelowFold({
  displayTitle,
  episodeMetaLine,
  description,
  metaParts,
  audioLanguages,
  sortedEpisodes,
  currentContentId,
  seasonId,
  episodesLoading,
  episodesError,
  detailLoading,
  detailError,
  contentType,
  seriesBrowse,
  movieBrowse,
  seriesState,
}: Props) {
  const meta = metaParts.filter(Boolean)
  const langs =
    audioLanguages?.map((l) => l.name?.trim()).filter(Boolean) ?? []
  const desc = description?.replace(/\s+/g, ' ').trim() || null
  const showEpisodeRail =
    contentType === 'episode' && Boolean(seasonId) && sortedEpisodes.length > 0

  const linkStateForEpisode = (ep: ContentItem) => ({
    title: ep.title,
    ...(ep.image ? { coverImage: ep.image } : {}),
    ...(seriesState
      ? {
          seriesContentId: seriesState.seriesContentId,
          seriesTitle: seriesState.seriesTitle,
          seriesType: seriesState.seriesType,
        }
      : {}),
  })

  return (
    <section className={styles.root} aria-label="About this title">
      <div className={styles.topRow}>
        <div className={styles.headingBlock}>
          {detailLoading && !displayTitle ? (
            <div className={styles.skelTitle} aria-hidden />
          ) : (
            <h2 className={styles.title}>{displayTitle}</h2>
          )}
          {episodeMetaLine ? (
            <p className={styles.episodeLine}>{episodeMetaLine}</p>
          ) : null}
          {meta.length > 0 ? (
            <p className={styles.meta}>{meta.join(' · ')}</p>
          ) : detailLoading ? (
            <div className={styles.skelMeta} aria-hidden />
          ) : null}
        </div>
        <div className={styles.actions}>
          {seriesBrowse ? (
            <Link to={seriesBrowse.href} className={styles.linkBtn}>
              {seriesBrowse.label}
            </Link>
          ) : null}
          {movieBrowse ? (
            <Link to={movieBrowse.href} className={styles.linkBtn}>
              {movieBrowse.label}
            </Link>
          ) : null}
          <Link to="/" className={styles.linkBtnGhost}>
            Home
          </Link>
        </div>
      </div>

      {detailError ? (
        <p className={styles.warn} role="status">
          Could not load full details: {detailError}
        </p>
      ) : null}

      {langs.length > 0 ? (
        <div className={styles.langRow}>
          <span className={styles.langLabel}>Audio</span>
          <ul className={styles.langList}>
            {langs.map((name) => (
              <li key={name} className={styles.langChip}>
                {name}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {desc ? (
        <p className={styles.description}>{desc}</p>
      ) : detailLoading ? (
        <div className={styles.skelDesc} aria-hidden />
      ) : null}

      {showEpisodeRail ? (
        <div className={styles.railSection}>
          <div className={styles.railHead}>
            <h3 className={styles.railTitle}>Episodes in this season</h3>
            {episodesLoading ? (
              <span className={styles.railHint}>Loading…</span>
            ) : (
              <span className={styles.railHint}>{sortedEpisodes.length} total</span>
            )}
          </div>
          {episodesError ? (
            <p className={styles.warn} role="status">
              {episodesError}
            </p>
          ) : null}
          <ul className={styles.rail} role="list">
            {sortedEpisodes.map((ep) => {
              const isCurrent = ep.id === currentContentId
              const prog =
                seasonId != null ? episodeProgressUi(ep.id, seasonId) : null
              const watchQs = new URLSearchParams({
                type: 'episode',
                seasonId: seasonId!,
              })
              if (ep.title?.trim()) watchQs.set('ref_title', ep.title.trim())
              const seq = Number(ep.sequence)
              const epNum = Number.isFinite(seq) && seq > 0 ? seq : null

              return (
                <li key={ep.id} className={styles.railItem}>
                  <Link
                    replace
                    to={`/watch/${encodeURIComponent(ep.id)}?${watchQs}`}
                    state={linkStateForEpisode(ep)}
                    className={`${styles.railCard} ${isCurrent ? styles.railCardCurrent : ''}`}
                    aria-current={isCurrent ? 'location' : undefined}
                  >
                    <div className={styles.thumbWrap}>
                      {ep.image ? (
                        <>
                          <img
                            src={ep.image}
                            alt=""
                            className={styles.thumb}
                            loading="lazy"
                            decoding="async"
                          />
                          {prog?.showBar ? (
                            <div
                              className={styles.thumbProgress}
                              style={{ width: `${prog.percent}%` }}
                            />
                          ) : null}
                        </>
                      ) : (
                        <div className={styles.thumbPh} aria-hidden>
                          <span>▶</span>
                        </div>
                      )}
                      {isCurrent ? (
                        <span className={styles.nowBadge}>Now playing</span>
                      ) : null}
                    </div>
                    <span className={styles.cardTitle}>
                      {epNum != null ? `E${epNum} · ` : ''}
                      {ep.title?.trim() || 'Episode'}
                    </span>
                    {prog?.showBar ? (
                      <span className={styles.cardProg}>Resume {prog.atLabel}</span>
                    ) : null}
                    {prog?.isAlmostDone ? (
                      <span className={styles.cardDone}>Almost done</span>
                    ) : null}
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      ) : null}
    </section>
  )
}
