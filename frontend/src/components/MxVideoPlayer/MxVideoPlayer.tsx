import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import videojs from 'video.js'
import 'video.js/dist/video-js.css'
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
  registerMxQualityMenu,
  syncMxQualityButtonVisibility,
} from './mxQualityMenu'
import { applyMxPlayerReady, type PlayerWithControlBar } from './mxPlayerReady'
import styles from './MxVideoPlayer.module.css'

registerMxQualityMenu()

const SAVE_INTERVAL_MS = 4000

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

function asTime(v: unknown): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : NaN
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
  backTo?: string
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
  backTo,
  onPrevEpisode,
  onNextEpisode,
}: Props) {
  const videoHostRef = useRef<HTMLDivElement>(null)
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

  const [resumeSeconds, setResumeSeconds] = useState<number | null>(null)
  const [playerBroken, setPlayerBroken] = useState<string | null>(null)

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
    resumeHandled.current = false
    setResumeSeconds(null)
    setPlayerBroken(null)
    lastSaveAt.current = 0

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
        controls: true,
        fluid: true,
        responsive: true,
        preload: 'metadata',
        playbackRates: [0.5, 0.75, 1, 1.25, 1.5, 2],
        controlBar: {
          skipButtons: {
            backward: 10,
            forward: 10,
          },
          remainingTimeDisplay: false,
        },
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
                  const ql = p?.qualityLevels?.()
                  if (!ql || typeof ql.length !== 'number') return
                  if (levelIndex < 0) {
                    for (let j = 0; j < ql.length; j++) {
                      try {
                        ql[j].enabled = true
                      } catch {
                        /* */
                      }
                    }
                  } else {
                    for (let j = 0; j < ql.length; j++) {
                      try {
                        ql[j].enabled = j === levelIndex
                      } catch {
                        /* */
                      }
                    }
                  }
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

    player.on('loadedmetadata', onLoaded)
    player.on('timeupdate', onTimeUpdate)
    player.on('ended', onEnded)

    player.ready(() => {
      applyMxPlayerReady(player as unknown as PlayerWithControlBar, {
        onPrevEpisode: onPrevEpisode
          ? () => {
              prevEpRef.current?.()
            }
          : undefined,
        onNextEpisode: onNextEpisode
          ? () => {
              nextEpRef.current?.()
            }
          : undefined,
      })
      addMxQualityMenuButton(player)

      if (showQualityControl && useVhsForQuality) {
        const bumpQualityUi = () => {
          syncMxQualityButtonVisibility(player)
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
    })

    const onVis = () => {
      if (document.visibilityState === 'hidden') flushProgress()
    }
    const onBeforeUnload = () => {
      flushProgress()
    }
    document.addEventListener('visibilitychange', onVis)
    window.addEventListener('beforeunload', onBeforeUnload)

    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload)
      document.removeEventListener('visibilitychange', onVis)
      player.off('loadedmetadata', onLoaded)
      player.off('timeupdate', onTimeUpdate)
      player.off('ended', onEnded)
      disposePlayer()
      if (videoHostRef.current) videoHostRef.current.innerHTML = ''
    }
  }, [
    activePlaybackUrl,
    watchKey,
    disposePlayer,
    flushProgress,
    onPrevEpisode,
    onNextEpisode,
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
        p.currentTime?.(Math.max(0, cur - 10))
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
        const next = cur + 10
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
      className={shellClass}
      tabIndex={0}
      role="region"
      aria-label={`Video player: ${title}`}
      onKeyDown={onShellKeyDown}
    >
      {cinema && backTo ? (
        <Link to={backTo} className={styles.backOverlay}>
          <span className={styles.backIcon} aria-hidden>
            ←
          </span>
          <span className={styles.srOnly}>Back</span>
        </Link>
      ) : null}

      {resumeSeconds != null && (
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

      {!cinema ? (
        <p className={styles.hints} aria-hidden="true">
          Space play/pause · ← → seek 10s · click player then use keys
        </p>
      ) : null}
    </div>
  )
}
