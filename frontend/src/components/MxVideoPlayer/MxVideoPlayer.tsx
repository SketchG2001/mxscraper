import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import videojs from 'video.js'
import 'video.js/dist/video-js.css'
import { useCompactUi } from '../../hooks/useCompactUi'
import { proxiedUrlsMatch, type ProxiedQualitySource } from '../../lib/streamQuality'
import {
  clearWatchProgress,
  clampResumePosition,
  formatPlaybackClock,
  loadWatchProgress,
  saveWatchProgress,
  shouldOfferResume,
} from '../../lib/watchProgress'
import {
  addMxQualityMenuButton,
  applyVhsQualityLevel,
  registerMxQualityMenu,
  syncMxQualityButtonVisibility,
} from './mxQualityMenu'
import {
  applyMxPlayerReady,
  syncMxEpisodeButtons,
  type PlayerWithControlBar,
} from './mxPlayerReady'
import { PlayerChrome, type ChromePlayer } from './playerChrome'
import { PLAYBACK_RATES, SEEK_SECONDS, asTime } from './playerConstants'
import styles from './MxVideoPlayer.module.css'

registerMxQualityMenu()

const SAVE_INTERVAL_MS = 4000
const MAX_AUTO_RETRIES = 2

type VideoPlayer = ReturnType<typeof videojs>

/** videojs-contrib-quality-levels (bundled) — not on public Player typings. */
type QualityLevelList = {
  length: number
  on: (ev: string, fn: () => void) => void
  [index: number]: { enabled: boolean }
}

type PlayerWithQualityLevels = VideoPlayer & {
  qualityLevels?: () => QualityLevelList
}

function clearMediaError(p: VideoPlayer) {
  try {
    ;(p as unknown as { error: (v: null) => void }).error(null)
  } catch {
    /* */
  }
}

function streamMimeType(url: string): string {
  if (/\.mpd(\?|$)/i.test(url)) return 'application/dash+xml'
  return 'application/x-mpegURL'
}

/** Master HLS/DASH — VHS can expose per-rendition quality levels. */
function isAdaptiveStreamUrl(url: string): boolean {
  return /\.m3u8(\?|$)/i.test(url) || /\.mpd(\?|$)/i.test(url)
}

type Props = {
  playbackUrl: string
  watchKey: string
  title: string
  /** Poster for Continue watching / browse cards (MX CDN URL). */
  coverImage?: string | null
  /** Multiple HLS/DASH levels from the API (proxied URLs). Hidden when fewer than 2. */
  qualitySources?: ProxiedQualitySource[]
  /** Edge-to-edge OTT-style layout with in-player chrome. */
  variant?: 'default' | 'cinema'
  /** Top-left back control (cinema). */
  onBack?: () => void
  onPrevEpisode?: () => void
  onNextEpisode?: () => void
}

export function MxVideoPlayer({
  playbackUrl,
  watchKey,
  title,
  coverImage,
  qualitySources,
  variant = 'default',
  onBack,
  onPrevEpisode,
  onNextEpisode,
}: Props) {
  const videoHostRef = useRef<HTMLDivElement>(null)
  const shellRef = useRef<HTMLDivElement>(null)
  const playerRef = useRef<VideoPlayer | null>(null)
  const lastSaveAt = useRef(0)
  const resumeHandled = useRef(false)
  const seekAfterLoadRef = useRef<number | null>(null)
  const titleRef = useRef(title)
  titleRef.current = title
  const coverRef = useRef((coverImage || '').trim())
  coverRef.current = (coverImage || '').trim()

  const prevEpRef = useRef(onPrevEpisode)
  const nextEpRef = useRef(onNextEpisode)
  prevEpRef.current = onPrevEpisode
  nextEpRef.current = onNextEpisode

  const cinema = variant === 'cinema'
  const compact = useCompactUi()

  const [resumeSeconds, setResumeSeconds] = useState<number | null>(null)
  const [playerBroken, setPlayerBroken] = useState<string | null>(null)
  const [streamError, setStreamError] = useState<string | null>(null)
  const [chromePlayer, setChromePlayer] = useState<ChromePlayer | null>(null)
  const retryCountRef = useRef(0)
  const disposedRef = useRef(false)
  const wantPlayOnShowRef = useRef(false)
  const activeUrlRef = useRef('')

  const sourceSig =
    qualitySources?.map((s) => `${s.key}:${s.url}`).join('|') ?? ''
  const multiQuality = Boolean(qualitySources && qualitySources.length > 1)
  const showQualityControl = Boolean(qualitySources && qualitySources.length >= 1)

  const defaultQualityIndex = useMemo(() => {
    if (!qualitySources?.length) return 0
    const i = qualitySources.findIndex((s) => proxiedUrlsMatch(s.url, playbackUrl))
    return i >= 0 ? i : 0
  }, [watchKey, playbackUrl, sourceSig, qualitySources])

  const [qualityIndex, setQualityIndex] = useState(defaultQualityIndex)
  useEffect(() => {
    setQualityIndex(defaultQualityIndex)
  }, [defaultQualityIndex])

  const qualityIndexRef = useRef(qualityIndex)
  const qualitySourcesRef = useRef(qualitySources ?? [])
  const setQualityIndexRef = useRef(setQualityIndex)
  qualityIndexRef.current = qualityIndex
  qualitySourcesRef.current = qualitySources ?? []
  setQualityIndexRef.current = setQualityIndex

  const activePlaybackUrl =
    multiQuality && qualitySources
      ? (qualitySources[qualityIndex]?.url ?? playbackUrl)
      : playbackUrl
  activeUrlRef.current = activePlaybackUrl

  const useVhsForQuality =
    !multiQuality &&
    Boolean(qualitySources?.length === 1) &&
    isAdaptiveStreamUrl(activePlaybackUrl)

  const flushProgress = useCallback(() => {
    const p = playerRef.current
    if (!p || !watchKey || watchKey === 'x:unknown') return
    try {
      const dur = asTime(p.duration())
      const ct = asTime(p.currentTime())
      if (!Number.isFinite(ct) || ct < 0) return
      const duration = Number.isFinite(dur) && dur > 0 ? dur : 0
      if (duration > 0 && ct >= duration - 5) {
        clearWatchProgress(watchKey)
        return
      }
      saveWatchProgress(watchKey, {
        position: ct,
        duration: duration > 0 ? duration : ct,
        title: titleRef.current || 'Watch',
        poster: coverRef.current || undefined,
      })
    } catch {
      /* player may be disposing */
    }
  }, [watchKey])

  const disposePlayer = useCallback(() => {
    const p = playerRef.current
    playerRef.current = null
    if (!p) return
    try {
      flushProgress()
    } catch {
      /* ignore */
    }
    try {
      p.dispose()
    } catch {
      /* DOM may already be gone */
    }
  }, [flushProgress])

  useEffect(() => {
    if (cinema) return
    const p = playerRef.current
    if (!p) return
    syncMxEpisodeButtons(p as unknown as PlayerWithControlBar, {
      hasPrev: Boolean(onPrevEpisode),
      hasNext: Boolean(onNextEpisode),
    })
  }, [cinema, onPrevEpisode, onNextEpisode])

  useEffect(() => {
    resumeHandled.current = false
    setResumeSeconds(null)
    setPlayerBroken(null)
    setStreamError(null)
    setChromePlayer(null)
    lastSaveAt.current = 0
    retryCountRef.current = 0
    disposedRef.current = false
    wantPlayOnShowRef.current = false

    const host = videoHostRef.current
    if (!host || !activePlaybackUrl) return

    const el = document.createElement('video')
    el.className = `video-js vjs-big-play-centered vjs-matrix-theme${cinema ? ' vjs-mx-cinema' : ''}`
    el.setAttribute('playsinline', '')
    el.setAttribute('crossorigin', 'anonymous')
    host.innerHTML = ''
    host.appendChild(el)

    let player: VideoPlayer
    try {
      player = videojs(el, {
        controls: !cinema,
        bigPlayButton: !cinema,
        fluid: true,
        responsive: true,
        preload: 'metadata',
        playbackRates: cinema ? [...PLAYBACK_RATES] : [0.5, 0.75, 1, 1.25, 1.5, 2],
        ...(cinema
          ? {
              userActions: { hotkeys: false, doubleClick: false },
            }
          : {
              controlBar: {
                skipButtons: {
                  backward: SEEK_SECONDS,
                  forward: SEEK_SECONDS,
                },
                remainingTimeDisplay: false,
              },
            }),
        html5: {
          vhs: { overrideNative: true },
          nativeAudioTracks: false,
          nativeVideoTracks: false,
        },
        ...(showQualityControl && qualitySources
          ? {
              mxQuality: {
                getState: () => ({
                  sources: qualitySourcesRef.current,
                  currentIndex: qualityIndexRef.current,
                }),
                useVhsLevels: useVhsForQuality,
                onPickUrl: (i: number) => {
                  if (i === qualityIndexRef.current) return
                  try {
                    const cur = asTime(playerRef.current?.currentTime?.())
                    if (Number.isFinite(cur) && cur > 0.25) {
                      seekAfterLoadRef.current = cur
                    }
                  } catch {
                    /* */
                  }
                  setQualityIndexRef.current(i)
                },
                onPickVhs: (levelIndex: number) => {
                  const p = playerRef.current as PlayerWithQualityLevels | null
                  applyVhsQualityLevel(p?.qualityLevels?.(), levelIndex)
                },
              },
            }
          : {}),
      })
    } catch (e) {
      setPlayerBroken(e instanceof Error ? e.message : 'Player failed to start.')
      return
    }

    playerRef.current = player

    try {
      const pq = player as PlayerWithQualityLevels
      if (showQualityControl && useVhsForQuality && typeof pq.qualityLevels === 'function') {
        pq.qualityLevels()
      }
    } catch {
      /* VHS quality list may be unavailable until tech loads */
    }

    try {
      player.src({
        src: activePlaybackUrl,
        type: streamMimeType(activePlaybackUrl),
      })
    } catch (e) {
      setPlayerBroken(e instanceof Error ? e.message : 'Could not set stream.')
      try {
        player.dispose()
      } catch {
        /* */
      }
      playerRef.current = null
      return
    }

    const onLoaded = () => {
      const preserve = seekAfterLoadRef.current
      if (preserve != null && Number.isFinite(preserve)) {
        seekAfterLoadRef.current = null
        resumeHandled.current = true
        setResumeSeconds(null)
        const dur = asTime(player.duration())
        const t =
          Number.isFinite(dur) && dur > 0
            ? clampResumePosition(preserve, dur)
            : preserve
        try {
          player.currentTime?.(t)
        } catch {
          /* */
        }
        return
      }
      if (resumeHandled.current) return
      const saved = loadWatchProgress(watchKey)
      const dur = asTime(player.duration())
      if (
        saved &&
        Number.isFinite(dur) &&
        dur > 0 &&
        shouldOfferResume(saved, dur)
      ) {
        resumeHandled.current = true
        setResumeSeconds(clampResumePosition(saved.position, dur))
        try {
          player.pause?.()
          player.currentTime?.(0)
        } catch {
          /* */
        }
        return
      }
      resumeHandled.current = true
      setResumeSeconds(null)
    }

    const onTimeUpdate = () => {
      const now = Date.now()
      if (now - lastSaveAt.current < SAVE_INTERVAL_MS) return
      lastSaveAt.current = now
      flushProgress()
    }

    const onEnded = () => {
      clearWatchProgress(watchKey)
    }

    let retryTimer: ReturnType<typeof setTimeout> | undefined

    const reloadSrc = () => {
      player.src({
        src: activePlaybackUrl,
        type: streamMimeType(activePlaybackUrl),
      })
    }

    const onPlaying = () => {
      retryCountRef.current = 0
      setStreamError(null)
    }

    const onPauseSave = () => {
      flushProgress()
    }

    const onError = () => {
      if (disposedRef.current) return
      let code = 0
      let msg = 'Playback failed.'
      try {
        const err = player.error() as { code?: number; message?: string } | null
        code = typeof err?.code === 'number' ? err.code : 0
        if (err?.message) msg = err.message
      } catch {
        /* */
      }
      if (code === 1) return
      if (retryCountRef.current < MAX_AUTO_RETRIES) {
        retryCountRef.current += 1
        retryTimer = window.setTimeout(() => {
          if (disposedRef.current) return
          try {
            clearMediaError(player)
            reloadSrc()
          } catch {
            setStreamError(msg)
          }
        }, 800 * retryCountRef.current)
        return
      }
      setStreamError(msg)
    }

    player.on('loadedmetadata', onLoaded)
    player.on('timeupdate', onTimeUpdate)
    player.on('ended', onEnded)
    player.on('error', onError)
    player.on('playing', onPlaying)
    player.on('pause', onPauseSave)

    player.ready(() => {
      if (!cinema) {
        applyMxPlayerReady(player as unknown as PlayerWithControlBar, {
          onPrevEpisode: () => {
            prevEpRef.current?.()
          },
          onNextEpisode: () => {
            nextEpRef.current?.()
          },
        })
        syncMxEpisodeButtons(player as unknown as PlayerWithControlBar, {
          hasPrev: Boolean(prevEpRef.current),
          hasNext: Boolean(nextEpRef.current),
        })
        addMxQualityMenuButton(player)
      }

      if (showQualityControl && useVhsForQuality) {
        const bumpQualityUi = () => {
          if (!cinema) syncMxQualityButtonVisibility(player)
          try {
            const bar = player.getChild('controlBar')
            const mb = bar?.getChild?.('MxQualityMenuButton') as
              | { update?: () => void }
              | undefined
            mb?.update?.()
          } catch {
            /* */
          }
        }
        try {
          const ql = (player as PlayerWithQualityLevels).qualityLevels?.()
          if (ql) {
            ql.on('addqualitylevel', bumpQualityUi)
            ql.on('change', bumpQualityUi)
          }
        } catch {
          /* */
        }
        player.on('loadedmetadata', bumpQualityUi)
        bumpQualityUi()
      }

      if (cinema && !disposedRef.current) {
        setChromePlayer(player as unknown as ChromePlayer)
      }
    })

    const onVis = () => {
      if (document.visibilityState === 'hidden') {
        flushProgress()
        try {
          if (player.paused?.() === false) {
            wantPlayOnShowRef.current = true
            player.pause?.()
          } else {
            wantPlayOnShowRef.current = false
          }
        } catch {
          wantPlayOnShowRef.current = false
        }
        return
      }
      if (disposedRef.current) return
      try {
        const err = player.error() as { code?: number } | null
        if (err && err.code !== 1) {
          if (retryCountRef.current < MAX_AUTO_RETRIES) {
            retryCountRef.current += 1
            clearMediaError(player)
            reloadSrc()
          } else {
            setStreamError('Playback failed.')
          }
          return
        }
        if (wantPlayOnShowRef.current) {
          wantPlayOnShowRef.current = false
          void (player.play?.() ?? Promise.resolve()).catch(() => {
            /* autoplay policy */
          })
        }
      } catch {
        /* */
      }
    }
    const onBeforeUnload = () => {
      flushProgress()
    }
    document.addEventListener('visibilitychange', onVis)
    window.addEventListener('beforeunload', onBeforeUnload)

    return () => {
      disposedRef.current = true
      setChromePlayer(null)
      if (retryTimer != null) window.clearTimeout(retryTimer)
      window.removeEventListener('beforeunload', onBeforeUnload)
      document.removeEventListener('visibilitychange', onVis)
      player.off('loadedmetadata', onLoaded)
      player.off('timeupdate', onTimeUpdate)
      player.off('ended', onEnded)
      player.off('error', onError)
      player.off('playing', onPlaying)
      player.off('pause', onPauseSave)
      disposePlayer()
      if (videoHostRef.current) videoHostRef.current.innerHTML = ''
    }
  }, [
    activePlaybackUrl,
    watchKey,
    disposePlayer,
    flushProgress,
    cinema,
    showQualityControl,
    useVhsForQuality,
  ])

  const handleResume = useCallback(() => {
    const p = playerRef.current
    if (!p || resumeSeconds == null) return
    try {
      const dur = asTime(p.duration())
      const t = clampResumePosition(
        resumeSeconds,
        Number.isFinite(dur) ? dur : 0,
      )
      p.currentTime?.(t)
      setResumeSeconds(null)
      void (p.play?.() ?? Promise.resolve()).catch(() => {
        /* autoplay policy */
      })
    } catch {
      setResumeSeconds(null)
    }
  }, [resumeSeconds])

  const handleStartOver = useCallback(() => {
    clearWatchProgress(watchKey)
    setResumeSeconds(null)
    const p = playerRef.current
    if (!p) return
    try {
      p.currentTime?.(0)
      void (p.play?.() ?? Promise.resolve()).catch(() => {})
    } catch {
      /* */
    }
  }, [watchKey])

  const handleRetryStream = useCallback(() => {
    const p = playerRef.current
    const url = activeUrlRef.current
    if (!p || !url) return
    retryCountRef.current = 0
    setStreamError(null)
    try {
      clearMediaError(p)
      p.src({ src: url, type: streamMimeType(url) })
      void (p.play?.() ?? Promise.resolve()).catch(() => {})
    } catch (e) {
      setStreamError(e instanceof Error ? e.message : 'Playback failed.')
    }
  }, [])

  const onPickQualityUrl = useCallback((i: number) => {
    if (i === qualityIndexRef.current) return
    try {
      const cur = asTime(playerRef.current?.currentTime?.())
      if (Number.isFinite(cur) && cur > 0.25) {
        seekAfterLoadRef.current = cur
      }
    } catch {
      /* */
    }
    setQualityIndex(i)
  }, [])

  useEffect(() => {
    const onMxBack = (e: Event) => {
      if (resumeSeconds != null) {
        e.preventDefault()
        setResumeSeconds(null)
        return
      }
      if (streamError) {
        e.preventDefault()
        setStreamError(null)
        return
      }
      if (cinema) return
      const p = playerRef.current
      try {
        if (p && typeof p.isFullscreen === 'function' && p.isFullscreen()) {
          e.preventDefault()
          void p.exitFullscreen()
        }
      } catch {
        /* */
      }
    }
    window.addEventListener('mx-android-back', onMxBack)
    return () => window.removeEventListener('mx-android-back', onMxBack)
  }, [resumeSeconds, streamError, cinema])

  const onShellKeyDown = useCallback((e: React.KeyboardEvent) => {
    const p = playerRef.current
    if (!p) return
    const t = e.target as HTMLElement
    if (
      t.tagName === 'INPUT' ||
      t.tagName === 'TEXTAREA' ||
      t.tagName === 'SELECT' ||
      t.isContentEditable
    )
      return

    if (e.code === 'Space') {
      e.preventDefault()
      try {
        const pausedFlag = p.paused?.()
        if (pausedFlag === true) {
          void (p.play?.() ?? Promise.resolve()).catch(() => {})
        } else if (pausedFlag === false) {
          p.pause?.()
        } else {
          void (p.play?.() ?? Promise.resolve()).catch(() => {})
        }
      } catch {
        /* */
      }
      return
    }
    if (e.code === 'ArrowLeft') {
      e.preventDefault()
      try {
        const cur = asTime(p.currentTime?.())
        if (!Number.isFinite(cur)) return
        p.currentTime?.(Math.max(0, cur - SEEK_SECONDS))
      } catch {
        /* */
      }
      return
    }
    if (e.code === 'ArrowRight') {
      e.preventDefault()
      try {
        const dur = asTime(p.duration?.())
        const cur = asTime(p.currentTime?.())
        if (!Number.isFinite(cur)) return
        const next = cur + SEEK_SECONDS
        const cap =
          Number.isFinite(dur) && dur > 0 ? Math.min(next, dur) : next
        p.currentTime?.(cap)
      } catch {
        /* */
      }
    }
  }, [])

  const shellClass = cinema ? `${styles.shell} ${styles.shellCinema}` : styles.shell

  if (playerBroken) {
    return (
      <div className={shellClass}>
        <p className={styles.fatal} role="alert">
          {playerBroken}
        </p>
      </div>
    )
  }

  return (
    <div
      ref={shellRef}
      className={shellClass}
      tabIndex={0}
      role="region"
      aria-label={`Video player: ${title}`}
      onKeyDown={onShellKeyDown}
    >
      {streamError ? (
        <div className={styles.resumeOverlay} role="alert">
          <div className={styles.resumeCard}>
            <p className={styles.resumeTitle}>Unable to play video</p>
            <p className={styles.resumeMeta}>
              {streamError.trim() || 'Something went wrong.'}
            </p>
            <div className={styles.resumeActions}>
              <button
                type="button"
                className={styles.resumePrimary}
                onClick={handleRetryStream}
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {resumeSeconds != null && !streamError && (
        <div className={styles.resumeOverlay} role="dialog" aria-modal="true">
          <div className={styles.resumeCard}>
            <p className={styles.resumeTitle}>Continue watching?</p>
            <p className={styles.resumeMeta}>
              Resume from <strong>{formatPlaybackClock(resumeSeconds)}</strong>
            </p>
            <div className={styles.resumeActions}>
              <button type="button" className={styles.resumePrimary} onClick={handleResume}>
                Resume
              </button>
              <button
                type="button"
                className={styles.resumeSecondary}
                onClick={handleStartOver}
              >
                Start over
              </button>
            </div>
          </div>
        </div>
      )}

      <div
        ref={videoHostRef}
        className={cinema ? `${styles.videoHost} ${styles.videoHostCinema}` : styles.videoHost}
        data-vjs-player
      />

      {cinema && chromePlayer ? (
        <PlayerChrome
          player={chromePlayer}
          shellRef={shellRef}
          title={title}
          compact={compact}
          onBack={onBack}
          onPrevEpisode={onPrevEpisode}
          onNextEpisode={onNextEpisode}
          qualitySources={qualitySources}
          qualityIndex={qualityIndex}
          onPickQualityUrl={onPickQualityUrl}
          useVhsForQuality={useVhsForQuality}
        />
      ) : null}

      {!cinema ? (
        <p className={styles.hints} aria-hidden="true">
          Space play/pause · ← → seek {SEEK_SECONDS}s · click player then use keys
        </p>
      ) : null}
    </div>
  )
}
