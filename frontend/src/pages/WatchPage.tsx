import { useQuery } from '@tanstack/react-query'
import { useCallback, useMemo } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { DownloadPanel } from '../components/DownloadPanel'
import { FeedbackState } from '../components/FeedbackState'
import { MxVideoPlayer } from '../components/MxVideoPlayer/MxVideoPlayer'
import {
  WatchBelowFold,
  formatDurationSeconds,
} from '../components/WatchBelowFold/WatchBelowFold'
import { usePageMeta } from '../hooks/usePageMeta'
import {
  ApiError,
  fetchContent,
  fetchEpisodes,
  fetchHealth,
  fetchStream,
} from '../lib/api'
import { navigateBack } from '../lib/navBack'
import { getProxyHost } from '../lib/proxyHost'
import { proxiedStreamUrl } from '../lib/proxyUrl'
import {
  buildProxiedQualitySources,
  withDefaultQualitySource,
} from '../lib/streamQuality'
import { makeWatchKey } from '../lib/watchProgress'
import type { ContentItem } from '../types/api'
import styles from './WatchPage.module.css'

type LocationState = {
  streamUrl?: string
  title?: string
  coverImage?: string
  rating?: string
  /** When opened from a series browse page — keeps “view series” + rail handoff. */
  seriesContentId?: string
  seriesTitle?: string
  seriesType?: string
}

export function WatchPage() {
  const { contentId } = useParams<{ contentId: string }>()
  const [searchParams] = useSearchParams()
  const type = searchParams.get('type') || 'movie'
  const seasonId = searchParams.get('seasonId')
  const refTitle = searchParams.get('ref_title')?.trim() || undefined
  const location = useLocation()
  const state = location.state as LocationState | undefined
  const directUrl = location.pathname === '/player' ? state?.streamUrl : undefined
  const title = state?.title ?? 'Watch'
  const coverImage = state?.coverImage?.trim() || undefined
  const navigate = useNavigate()

  const watchKey = useMemo(
    () =>
      makeWatchKey({
        contentId: contentId ?? null,
        type,
        seasonId: seasonId ?? null,
        directUrl: directUrl ?? null,
      }),
    [contentId, type, seasonId, directUrl],
  )

  usePageMeta(
    title === 'Watch' ? 'Watch' : `Watch ${title}`,
    `Playback: ${title}.`,
  )

  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    staleTime: 120_000,
  })

  const episodesQuery = useQuery({
    queryKey: ['episodes', seasonId],
    queryFn: () => fetchEpisodes(seasonId!),
    enabled: Boolean(seasonId) && type === 'episode' && !directUrl,
    staleTime: 60_000,
  })

  const sortedEpisodesForRef = useMemo(() => {
    const list = [...(episodesQuery.data?.episodes ?? [])]
    list.sort((a, b) => {
      const sa = Number(a.sequence)
      const sb = Number(b.sequence)
      if (Number.isFinite(sa) && Number.isFinite(sb) && sa !== sb) return sa - sb
      return 0
    })
    return list
  }, [episodesQuery.data?.episodes])

  /** Same ref_title for content + stream: URL, then season list title, then navigation state. */
  const refTitleForApi = useMemo(() => {
    const fromUrl = refTitle?.trim()
    if (fromUrl) return fromUrl
    if (type === 'episode' && contentId) {
      const ep = sortedEpisodesForRef.find((e) => e.id === contentId)
      if (ep?.title?.trim()) return ep.title.trim()
    }
    const t0 = title.trim()
    if (type === 'episode' && t0 && t0 !== 'Watch') return t0
    return undefined
  }, [refTitle, type, contentId, sortedEpisodesForRef, title])

  const detailQuery = useQuery({
    queryKey: ['content', contentId, type, refTitleForApi],
    queryFn: () => fetchContent(contentId!, type, refTitleForApi),
    enabled: Boolean(contentId) && !directUrl,
    staleTime: 60_000,
  })

  /** Season-scoped episodes ignore ref_title on the server; omitting it avoids a refetch when the list fills in. */
  const streamQueryKey = useMemo(
    () =>
      type === 'episode' && seasonId
        ? (['stream', contentId, type, seasonId] as const)
        : (['stream', contentId, type, seasonId, refTitleForApi] as const),
    [contentId, type, seasonId, refTitleForApi],
  )

  const streamQuery = useQuery({
    queryKey: streamQueryKey,
    queryFn: () => fetchStream(contentId!, type, seasonId, refTitleForApi),
    enabled: Boolean(contentId) && !directUrl,
  })

  const rawStreamUrl = directUrl ?? streamQuery.data?.stream_url ?? ''
  const proxyHost = getProxyHost()
  const proxyPort = healthQuery.data?.proxy_port ?? 8513

  const playbackUrl = useMemo(() => {
    if (!rawStreamUrl) return ''
    if (!rawStreamUrl.startsWith('http')) return ''
    return proxiedStreamUrl(rawStreamUrl, proxyHost, proxyPort)
  }, [rawStreamUrl, proxyHost, proxyPort])

  const qualitySources = useMemo(() => {
    if (directUrl || !playbackUrl) return []
    const built = buildProxiedQualitySources(
      streamQuery.data?.options,
      proxyHost,
      proxyPort,
    )
    const merged = withDefaultQualitySource(built, playbackUrl)
    if (merged.length >= 1) return merged
    if (streamQuery.data?.stream_url) {
      return [{ key: 'stream_only', label: 'Auto', url: playbackUrl }]
    }
    return []
  }, [
    directUrl,
    playbackUrl,
    streamQuery.data?.options,
    streamQuery.data?.stream_url,
    proxyHost,
    proxyPort,
  ])

  const sortedEpisodes = sortedEpisodesForRef

  const episodeNav = useMemo(() => {
    if (type !== 'episode' || !seasonId || !contentId) return null
    const idx = sortedEpisodes.findIndex((e) => e.id === contentId)
    if (idx < 0) return null
    const prevEp = idx > 0 ? sortedEpisodes[idx - 1] : null
    const nextEp = idx < sortedEpisodes.length - 1 ? sortedEpisodes[idx + 1] : null
    if (!prevEp && !nextEp) return null
    const qs = (ep: ContentItem) => {
      const q = new URLSearchParams({ type: 'episode', seasonId })
      if (ep.title?.trim()) q.set('ref_title', ep.title.trim())
      return q
    }
    return { prevEp, nextEp, qs }
  }, [type, seasonId, contentId, sortedEpisodes])

  const episodeMetaLine = useMemo(() => {
    if (type !== 'episode' || !contentId) return undefined
    const idx = sortedEpisodes.findIndex((e) => e.id === contentId)
    if (idx < 0) return undefined
    const ep = sortedEpisodes[idx]
    const seq = ep?.sequence
    const n = Number(seq)
    if (Number.isFinite(n) && n > 0) return `Episode ${n}`
    return `Episode ${idx + 1}`
  }, [type, contentId, sortedEpisodes])

  const episodeNavState = useCallback(
    (ep: ContentItem): LocationState => ({
      title: ep.title,
      ...(ep.image ? { coverImage: ep.image } : {}),
      ...(state?.seriesContentId?.trim()
        ? {
            seriesContentId: state.seriesContentId.trim(),
            seriesTitle: state.seriesTitle,
            seriesType: state.seriesType,
          }
        : {}),
    }),
    [state?.seriesContentId, state?.seriesTitle, state?.seriesType],
  )

  const goPrevEpisode = useCallback(() => {
    if (!episodeNav?.prevEp) return
    const ep = episodeNav.prevEp
    navigate(
      {
        pathname: `/watch/${encodeURIComponent(ep.id)}`,
        search: `?${episodeNav.qs(ep)}`,
      },
      { replace: true, state: episodeNavState(ep) },
    )
  }, [episodeNav, episodeNavState, navigate])

  const goNextEpisode = useCallback(() => {
    if (!episodeNav?.nextEp) return
    const ep = episodeNav.nextEp
    navigate(
      {
        pathname: `/watch/${encodeURIComponent(ep.id)}`,
        search: `?${episodeNav.qs(ep)}`,
      },
      { replace: true, state: episodeNavState(ep) },
    )
  }, [episodeNav, episodeNavState, navigate])

  const currentEpisode = useMemo(
    () => (contentId ? sortedEpisodes.find((e) => e.id === contentId) : undefined),
    [contentId, sortedEpisodes],
  )

  const detailItem = detailQuery.data?.item
  const detailErrSoft =
    detailQuery.error instanceof ApiError && detailQuery.error.status === 404
  const detailErrorForUi =
    detailQuery.isError && !detailErrSoft ? String(detailQuery.error) : null

  const metaParts = useMemo(() => {
    const parts: string[] = []
    const src = detailItem ?? currentEpisode
    if (!src) return parts
    if (src.year) parts.push(String(src.year))
    const d = formatDurationSeconds(src.duration)
    if (d) parts.push(d)
    if (src.rating != null && String(src.rating).trim()) {
      parts.push(String(src.rating))
    }
    if (src.publisher?.trim()) parts.push(src.publisher.trim())
    return parts
  }, [detailItem, currentEpisode])

  const displayTitle =
    (detailItem?.title ?? currentEpisode?.title ?? title).trim() || 'Watch'
  const synopsis =
    detailItem?.description?.trim() ||
    currentEpisode?.description?.trim() ||
    null

  const seriesBrowse = useMemo(() => {
    if (!state?.seriesContentId?.trim()) return null
    const id = state.seriesContentId.trim()
    const t = (state.seriesType || 'tvshow').trim() || 'tvshow'
    return {
      href: `/browse/${encodeURIComponent(id)}?${new URLSearchParams({ type: t })}`,
      label: state.seriesTitle?.trim()
        ? `Series · ${state.seriesTitle.trim()}`
        : 'View series page',
    }
  }, [state?.seriesContentId, state?.seriesTitle, state?.seriesType])

  const movieBrowse = useMemo(() => {
    if (!contentId || directUrl || type !== 'movie') return null
    const q = new URLSearchParams({ type: 'movie' })
    if (refTitle?.trim()) q.set('ref_title', refTitle.trim())
    return {
      href: `/browse/${encodeURIComponent(contentId)}?${q}`,
      label: 'Details & synopsis',
    }
  }, [contentId, directUrl, type, refTitle])

  const seriesLinkState = useMemo(() => {
    if (!state?.seriesContentId?.trim()) return null
    return {
      seriesContentId: state.seriesContentId.trim(),
      seriesTitle: state.seriesTitle,
      seriesType: state.seriesType,
    }
  }, [state?.seriesContentId, state?.seriesTitle, state?.seriesType])

  const waitingApi =
    !directUrl && streamQuery.isLoading && Boolean(contentId)
  const apiError =
    !directUrl && streamQuery.isError ? String(streamQuery.error) : null

  const onPlayerBack = useCallback(() => {
    navigateBack(navigate)
  }, [navigate])

  return (
    <div className={styles.page}>
      {!playbackUrl ? (
        <div className={styles.chrome}>
          <button
            type="button"
            className={styles.back}
            onClick={onPlayerBack}
            aria-label="Back"
          >
            ← Back
          </button>
          <div className={styles.titleBlock}>
            <h1 className={styles.title}>{title}</h1>
          </div>
        </div>
      ) : null}

      {waitingApi && (
        <div className={styles.loadingRow} role="status" aria-live="polite">
          <span className={styles.loadingPulse} aria-hidden />
          <span className={styles.skelBar} />
        </div>
      )}
      {apiError && (
        <FeedbackState
          title="Something went wrong"
          message="We couldn't start playback."
          onRetry={() => void streamQuery.refetch()}
        />
      )}

      {playbackUrl ? (
        <>
          <div className={styles.watchCinema}>
            <MxVideoPlayer
              key={watchKey}
              playbackUrl={playbackUrl}
              watchKey={watchKey}
              title={title}
              coverImage={coverImage}
              qualitySources={
                qualitySources.length >= 1 ? qualitySources : undefined
              }
              variant="cinema"
              onBack={onPlayerBack}
              onPrevEpisode={episodeNav?.prevEp ? goPrevEpisode : undefined}
              onNextEpisode={episodeNav?.nextEp ? goNextEpisode : undefined}
            />
          </div>
          {contentId && !directUrl ? (
            <div className={styles.below}>
              <DownloadPanel
                contentId={contentId}
                contentType={type}
                seasonId={seasonId}
                title={title}
                refTitle={refTitleForApi}
                stream={streamQuery.data}
                ffmpeg={healthQuery.data?.ffmpeg}
              />
            </div>
          ) : null}
          {contentId ? (
            <WatchBelowFold
              displayTitle={displayTitle}
              episodeMetaLine={episodeMetaLine}
              description={synopsis}
              metaParts={metaParts}
              audioLanguages={streamQuery.data?.languages}
              sortedEpisodes={sortedEpisodes}
              currentContentId={contentId}
              seasonId={seasonId ?? null}
              episodesLoading={episodesQuery.isLoading}
              episodesError={
                episodesQuery.isError ? String(episodesQuery.error) : null
              }
              detailLoading={detailQuery.isLoading}
              detailError={detailErrorForUi}
              contentType={type}
              seriesBrowse={seriesBrowse}
              movieBrowse={movieBrowse}
              seriesState={seriesLinkState}
            />
          ) : null}
        </>
      ) : !waitingApi && !apiError ? (
        <FeedbackState
          title={!directUrl && !contentId ? 'No stream' : 'Unavailable'}
          message={
            !directUrl && !contentId
              ? 'Open a title from search or the catalog.'
              : 'This title doesn’t have a playable stream.'
          }
        />
      ) : null}

      {!directUrl && streamQuery.data?.drm && (
        <p className={styles.drmNote}>This asset may be DRM protected.</p>
      )}
    </div>
  )
}
