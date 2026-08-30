import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent, type RefObject } from 'react'
import { formatPlaybackClock } from '../../lib/watchProgress'
import type { ProxiedQualitySource } from '../../lib/streamQuality'
import {
  menuLabelForSource,
  sortVhsLevelIndices,
  vhsSelectedLevelIndex,
  applyVhsQualityLevel,
} from './mxQualityMenu'
import {
  AUTO_NEXT_SECONDS,
  DOUBLE_TAP_MS,
  PLAYBACK_RATES,
  SEEK_SECONDS,
  asTime,
  ccSizePx,
  loadPlayerPrefs,
  savePlayerPrefs,
  type CcSize,
} from './playerConstants'
import { isShellFullscreen } from './playerFullscreen'
import { usePlayerControlsVisibility } from './usePlayerControlsVisibility'
import { usePlayerFullscreen } from './usePlayerFullscreen'
import styles from './playerChrome.module.css'

type QualityLevelList = {
  length: number
  on: (ev: string, fn: () => void) => void
  off?: (ev: string, fn: () => void) => void
  [index: number]: { enabled: boolean; height?: number; bandwidth?: number }
}

export type ChromePlayer = {
  play: () => Promise<void> | void
  pause: () => void
  paused: () => boolean
  currentTime: (n?: number) => unknown
  duration: () => unknown
  buffered: () => { length: number; end: (i: number) => number }
  playbackRate: (n?: number) => unknown
  on: (ev: string, fn: (...args: unknown[]) => void) => void
  off: (ev: string, fn: (...args: unknown[]) => void) => void
  audioTracks?: () => {
    length: number
    addEventListener?: (ev: string, fn: () => void) => void
    removeEventListener?: (ev: string, fn: () => void) => void
    [i: number]: { enabled: boolean; label?: string; language?: string }
  }
  textTracks?: () => TextTrackList
  qualityLevels?: () => QualityLevelList
  readyState?: () => number
  el?: () => HTMLElement
  trigger?: (ev: string) => void
}

type MenuId = 'quality' | 'audio' | 'subtitles' | 'speed' | 'ccStyle' | 'more' | null

type Props = {
  player: ChromePlayer
  shellRef: RefObject<HTMLElement | null>
  title: string
  compact: boolean
  onBack?: () => void
  onPrevEpisode?: () => void
  onNextEpisode?: () => void
  qualitySources?: ProxiedQualitySource[]
  qualityIndex: number
  onPickQualityUrl: (index: number) => void
  useVhsForQuality: boolean
}

function IconBack() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M15 5l-7 7 7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function IconPlay() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M8 5v14l11-7z" />
    </svg>
  )
}

function IconPause() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M6 5h4v14H6zm8 0h4v14h-4z" />
    </svg>
  )
}

function IconSkip({ fwd }: { fwd?: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden style={fwd ? undefined : { transform: 'scaleX(-1)' }}>
      <path d="M6 6v12l8.5-6zm9 0h2v12h-2z" />
    </svg>
  )
}

function IconFs({ exit }: { exit?: boolean }) {
  return exit ? (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M9 9H5V5M15 9h4V5M9 15H5v4M15 15h4v4" />
    </svg>
  ) : (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M9 3H3v6M15 3h6v6M9 21H3v-6M21 15v6h-6" />
    </svg>
  )
}

function IconLock({ on }: { on?: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      {on ? (
        <path d="M7 11V8a5 5 0 0110 0v3M6 11h12v10H6z" />
      ) : (
        <path d="M7 11V8a5 5 0 019.5-2M6 11h12v10H6z" />
      )}
    </svg>
  )
}

function applyCcStyle(player: ChromePlayer, size: CcSize, bg: number) {
  const el = player.el?.()
  if (!el) return
  el.style.setProperty('--mx-cc-size', ccSizePx(size))
  el.style.setProperty('--mx-cc-bg', String(bg))
}

function bufferedEnd(player: ChromePlayer): number {
  try {
    const b = player.buffered()
    if (!b || !b.length) return 0
    return b.end(b.length - 1)
  } catch {
    return 0
  }
}

function seekTo(player: ChromePlayer, seconds: number) {
  const dur = asTime(player.duration())
  let t = seconds
  if (t < 0) t = 0
  if (Number.isFinite(dur) && dur > 0) t = Math.min(t, dur)
  try {
    player.currentTime(t)
  } catch {
    /* */
  }
}

function seekBy(player: ChromePlayer, delta: number) {
  const cur = asTime(player.currentTime())
  if (!Number.isFinite(cur)) return
  seekTo(player, cur + delta)
}

export function PlayerChrome({
  player,
  shellRef,
  title,
  compact,
  onBack,
  onPrevEpisode,
  onNextEpisode,
  qualitySources,
  qualityIndex,
  onPickQualityUrl,
  useVhsForQuality,
}: Props) {
  const [paused, setPaused] = useState(() => {
    try {
      return player.paused() !== false
    } catch {
      return true
    }
  })
  const [buffering, setBuffering] = useState(false)
  const [locked, setLocked] = useState(false)
  const [lockPeek, setLockPeek] = useState(false)
  const [menu, setMenu] = useState<MenuId>(null)
  const [hint, setHint] = useState<{ side: 'l' | 'r'; label: string } | null>(null)
  const [nextIn, setNextIn] = useState<number | null>(null)
  const [rate, setRate] = useState(() => loadPlayerPrefs().rate ?? 1)
  const [ccSize, setCcSize] = useState<CcSize>(() => loadPlayerPrefs().ccSize ?? 'md')
  const [ccBg, setCcBg] = useState(() => loadPlayerPrefs().ccBg ?? 0.65)
  const [tracksTick, setTracksTick] = useState(0)

  const { active: fs, exit: exitFullscreen, toggle: toggleFsApi } = usePlayerFullscreen(
    shellRef,
    player,
  )

  const {
    visible,
    show: showChrome,
    toggle: toggleChrome,
    clearTimer: clearHideTimer,
    setVisible,
  } = usePlayerControlsVisibility({
    player,
    paused,
    locked,
    menuOpen: menu != null || nextIn != null,
  })

  const peekTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const hintTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const singleTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const lastTap = useRef({ t: 0, side: 'c' as 'l' | 'r' | 'c' })
  const seeking = useRef(false)
  const seekInputRef = useRef<HTMLInputElement>(null)
  const fillRef = useRef<HTMLSpanElement>(null)
  const bufRef = useRef<HTMLSpanElement>(null)
  const curRef = useRef<HTMLSpanElement>(null)
  const durRef = useRef<HTMLSpanElement>(null)
  const waitShow = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  const bumpTracks = useCallback(() => setTracksTick((n) => n + 1), [])

  useEffect(() => {
    return () => {
      if (peekTimer.current) window.clearTimeout(peekTimer.current)
      if (hintTimer.current) window.clearTimeout(hintTimer.current)
      if (singleTimer.current) window.clearTimeout(singleTimer.current)
      if (waitShow.current) window.clearTimeout(waitShow.current)
    }
  }, [])

  useEffect(() => {
    try {
      player.playbackRate(rate)
    } catch {
      /* */
    }
    applyCcStyle(player, ccSize, ccBg)
  }, [player, rate, ccSize, ccBg])

  useEffect(() => {
    const syncPaused = () => {
      try {
        setPaused(player.paused() !== false)
      } catch {
        /* */
      }
    }
    const onWaiting = () => {
      if (waitShow.current) window.clearTimeout(waitShow.current)
      waitShow.current = window.setTimeout(() => {
        try {
          if (player.paused() === false) setBuffering(true)
        } catch {
          setBuffering(true)
        }
      }, 180)
    }
    const clearBuffering = () => {
      if (waitShow.current) window.clearTimeout(waitShow.current)
      setBuffering(false)
    }
    const onPlaying = () => {
      clearBuffering()
      setPaused(false)
    }
    const onPause = () => {
      setPaused(true)
    }
    const onEnded = () => {
      setPaused(true)
      if (!onNextEpisode) return
      setNextIn(AUTO_NEXT_SECONDS)
    }
    const onTime = () => {
      if (seeking.current) return
      const dur = asTime(player.duration())
      const cur = asTime(player.currentTime())
      if (durRef.current && Number.isFinite(dur) && dur > 0) {
        durRef.current.textContent = formatPlaybackClock(dur)
      }
      if (curRef.current && Number.isFinite(cur)) {
        curRef.current.textContent = formatPlaybackClock(cur)
      }
      if (Number.isFinite(dur) && dur > 0 && Number.isFinite(cur)) {
        const pct = Math.max(0, Math.min(1, cur / dur))
        if (fillRef.current) fillRef.current.style.width = `${pct * 100}%`
        if (seekInputRef.current && document.activeElement !== seekInputRef.current) {
          seekInputRef.current.value = String(Math.round(pct * 1000))
        }
        const buf = bufferedEnd(player)
        if (bufRef.current) bufRef.current.style.width = `${Math.min(100, (buf / dur) * 100)}%`
      }
    }

    const safeOff = (ev: string, fn: (...args: unknown[]) => void) => {
      try {
        player.off(ev, fn)
      } catch {
        /* disposed */
      }
    }

    player.on('play', syncPaused)
    player.on('pause', onPause)
    player.on('playing', onPlaying)
    player.on('waiting', onWaiting)
    player.on('canplay', clearBuffering)
    player.on('ended', onEnded)
    player.on('timeupdate', onTime)
    player.on('loadedmetadata', onTime)
    syncPaused()
    onTime()

    const at = player.audioTracks?.()
    const tt = player.textTracks?.()
    at?.addEventListener?.('addtrack', bumpTracks)
    at?.addEventListener?.('change', bumpTracks)
    tt?.addEventListener?.('addtrack', bumpTracks)
    tt?.addEventListener?.('change', bumpTracks)
    try {
      const ql = player.qualityLevels?.()
      ql?.on('addqualitylevel', bumpTracks)
      ql?.on('change', bumpTracks)
    } catch {
      /* */
    }

    return () => {
      safeOff('play', syncPaused)
      safeOff('pause', onPause)
      safeOff('playing', onPlaying)
      safeOff('waiting', onWaiting)
      safeOff('canplay', clearBuffering)
      safeOff('ended', onEnded)
      safeOff('timeupdate', onTime)
      safeOff('loadedmetadata', onTime)
      at?.removeEventListener?.('addtrack', bumpTracks)
      at?.removeEventListener?.('change', bumpTracks)
      tt?.removeEventListener?.('addtrack', bumpTracks)
      tt?.removeEventListener?.('change', bumpTracks)
    }
  }, [player, onNextEpisode, bumpTracks])

  const nextFnRef = useRef(onNextEpisode)
  nextFnRef.current = onNextEpisode

  useEffect(() => {
    if (nextIn == null) return
    if (nextIn <= 0) {
      const fn = nextFnRef.current
      setNextIn(null)
      fn?.()
      return
    }
    const id = window.setTimeout(() => setNextIn(nextIn - 1), 1000)
    return () => window.clearTimeout(id)
  }, [nextIn])

  const exitFs = useCallback(async () => {
    await exitFullscreen()
  }, [exitFullscreen])

  useEffect(() => {
    const onMxBack = (e: Event) => {
      if (menu) {
        e.preventDefault()
        setMenu(null)
        return
      }
      if (nextIn != null) {
        e.preventDefault()
        setNextIn(null)
        return
      }
      if (locked) {
        e.preventDefault()
        setLocked(false)
        setLockPeek(false)
        showChrome()
        return
      }
      if (isShellFullscreen(shellRef.current)) {
        e.preventDefault()
        void exitFs()
      }
    }
    window.addEventListener('mx-android-back', onMxBack)
    return () => window.removeEventListener('mx-android-back', onMxBack)
  }, [menu, nextIn, locked, shellRef, showChrome, exitFs])

  const togglePlay = useCallback(() => {
    try {
      if (player.paused()) void Promise.resolve(player.play()).catch(() => {})
      else player.pause()
    } catch {
      /* */
    }
    showChrome()
  }, [player, showChrome])

  const flashHint = (side: 'l' | 'r', delta: number) => {
    setHint({ side, label: `${Math.abs(delta)} sec` })
    if (hintTimer.current) window.clearTimeout(hintTimer.current)
    hintTimer.current = window.setTimeout(() => setHint(null), 700)
  }

  const doSeek = (delta: number) => {
    seekBy(player, delta)
    flashHint(delta < 0 ? 'l' : 'r', delta)
    showChrome()
  }

  const toggleFs = () => {
    void toggleFsApi()
    showChrome()
  }

  const onHitUp = (e: ReactPointerEvent) => {
    if (e.button !== 0) return
    if (locked) {
      setLockPeek(true)
      if (peekTimer.current) window.clearTimeout(peekTimer.current)
      peekTimer.current = window.setTimeout(() => setLockPeek(false), 2200)
      return
    }
    if (menu) return
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = (e.clientX - rect.left) / Math.max(1, rect.width)
    const side: 'l' | 'r' | 'c' = ratio < 0.35 ? 'l' : ratio > 0.65 ? 'r' : 'c'
    const now = Date.now()
    const dbl = now - lastTap.current.t < DOUBLE_TAP_MS && lastTap.current.side === side
    if (dbl) {
      if (singleTimer.current) window.clearTimeout(singleTimer.current)
      lastTap.current.t = 0
      if (side === 'c') {
        if (!compact) toggleFs()
        return
      }
      doSeek(side === 'l' ? -SEEK_SECONDS : SEEK_SECONDS)
      return
    }
    lastTap.current = { t: now, side }
    if (singleTimer.current) window.clearTimeout(singleTimer.current)
    singleTimer.current = window.setTimeout(() => {
      toggleChrome()
    }, DOUBLE_TAP_MS)
  }

  const onSeekInput = (el: HTMLInputElement, commit: boolean) => {
    const dur = asTime(player.duration())
    if (!Number.isFinite(dur) || dur <= 0) return
    const t = (Number(el.value) / 1000) * dur
    if (fillRef.current) fillRef.current.style.width = `${(t / dur) * 100}%`
    if (curRef.current) curRef.current.textContent = formatPlaybackClock(t)
    if (commit) seekTo(player, t)
  }

  const audioList = (() => {
    void tracksTick
    const at = player.audioTracks?.()
    if (!at || at.length < 2) return []
    const rows: { i: number; label: string; on: boolean }[] = []
    for (let i = 0; i < at.length; i++) {
      const a = at[i]
      rows.push({
        i,
        label: a.label || a.language || `Audio ${i + 1}`,
        on: Boolean(a.enabled),
      })
    }
    return rows
  })()

  const textList = (() => {
    void tracksTick
    const tt = player.textTracks?.()
    if (!tt || tt.length < 1) return []
    const rows: { i: number; label: string; on: boolean; kind: string }[] = []
    for (let i = 0; i < tt.length; i++) {
      const t = tt[i]
      if (t.kind !== 'subtitles' && t.kind !== 'captions') continue
      rows.push({
        i,
        label: t.label || t.language || `Track ${i + 1}`,
        on: t.mode === 'showing',
        kind: t.kind,
      })
    }
    return rows
  })()

  const qualityRows = (() => {
    void tracksTick
    if (qualitySources && qualitySources.length > 1) {
      return qualitySources.map((src, i) => ({
        id: src.key,
        label: menuLabelForSource(src),
        on: i === qualityIndex,
        pick: () => onPickQualityUrl(i),
      }))
    }
    if (useVhsForQuality) {
      try {
        const ql = player.qualityLevels?.()
        if (ql && ql.length >= 2) {
          const sel = vhsSelectedLevelIndex(ql)
          const sorted = sortVhsLevelIndices(ql)
          return [
            {
              id: 'auto',
              label: 'Auto',
              on: sel < 0,
              pick: () => {
                applyVhsQualityLevel(ql, -1)
                bumpTracks()
              },
            },
            ...sorted.map((r) => ({
              id: `v${r.idx}`,
              label: r.label,
              on: sel === r.idx,
              pick: () => {
                applyVhsQualityLevel(ql, r.idx)
                bumpTracks()
              },
            })),
          ]
        }
      } catch {
        /* */
      }
    }
    return []
  })()

  const showQuality = qualityRows.length >= 2
  const showAudio = audioList.length >= 2
  const showCc = textList.length > 0
  // Narrow: fold audio/CC into More so secondary stays tappable.
  const useMoreOverflow = compact && (showAudio || showCc)

  const pickAudio = (index: number) => {
    const at = player.audioTracks?.()
    if (!at) return
    for (let i = 0; i < at.length; i++) {
      try {
        at[i].enabled = i === index
      } catch {
        /* */
      }
    }
    setMenu(null)
    bumpTracks()
  }

  const pickText = (index: number | null) => {
    const tt = player.textTracks?.()
    if (!tt) return
    for (let i = 0; i < tt.length; i++) {
      const t = tt[i]
      if (t.kind !== 'subtitles' && t.kind !== 'captions') continue
      t.mode = index === i ? 'showing' : 'disabled'
    }
    setMenu(null)
    bumpTracks()
  }

  const pickRate = (r: number) => {
    setRate(r)
    savePlayerPrefs({ rate: r })
    try {
      player.playbackRate(r)
    } catch {
      /* */
    }
    setMenu(null)
  }

  const openMenu = (id: MenuId) => {
    setMenu(id)
    clearHideTimer()
    setVisible(true)
  }

  const menuTitle =
    menu === 'quality'
      ? 'Quality'
      : menu === 'audio'
        ? 'Audio'
        : menu === 'subtitles'
          ? 'Subtitles'
          : menu === 'speed'
            ? 'Speed'
            : menu === 'ccStyle'
              ? 'Subtitle style'
              : menu === 'more'
                ? 'More'
                : ''

  return (
    <div
      className={styles.root}
      data-visible={visible && !locked ? 'true' : 'false'}
      data-locked={locked ? 'true' : 'false'}
    >
      <div className={styles.hit} onPointerUp={onHitUp} />
      <div className={styles.scrim} aria-hidden />

      {buffering && !paused ? (
        <div className={styles.spinner} role="status" aria-label="Loading">
          <div className={styles.spinRing} />
        </div>
      ) : null}

      {hint ? (
        <div className={styles.hint} data-side={hint.side} aria-live="polite">
          <span aria-hidden>{hint.side === 'l' ? '↶' : '↷'}</span>
          {hint.label}
        </div>
      ) : null}

      {locked && lockPeek ? (
        <button
          type="button"
          className={`${styles.iconBtn} ${styles.playBtn} ${styles.lockPeek}`}
          aria-label="Unlock player"
          onClick={() => {
            setLocked(false)
            setLockPeek(false)
            showChrome()
          }}
        >
          <IconLock on />
        </button>
      ) : null}

      <div className={styles.stack}>
        <div className={styles.top}>
          {onBack ? (
            <button type="button" className={styles.iconBtn} aria-label="Back" onClick={onBack}>
              <IconBack />
            </button>
          ) : null}
          <p className={styles.title}>{title}</p>
        </div>

        <div className={styles.mid}>
          <button
            type="button"
            className={`${styles.iconBtn} ${styles.playBtn}`}
            aria-label={paused ? 'Play' : 'Pause'}
            onClick={togglePlay}
          >
            {paused ? <IconPlay /> : <IconPause />}
          </button>
        </div>

        <div className={styles.dock}>
          <div className={styles.seekRow}>
            <span className={styles.time} ref={curRef}>
              0:00
            </span>
            <div className={styles.seekHit}>
              <div className={styles.seekTrack} aria-hidden>
                <span className={styles.seekBuf} ref={bufRef} />
                <span className={styles.seekFill} ref={fillRef} />
              </div>
              <input
                ref={seekInputRef}
                className={styles.seekInput}
                type="range"
                min={0}
                max={1000}
                defaultValue={0}
                aria-label="Seek"
                onPointerDown={() => {
                  seeking.current = true
                  clearHideTimer()
                }}
                onInput={(e) => onSeekInput(e.currentTarget, false)}
                onPointerUp={(e) => {
                  onSeekInput(e.currentTarget, true)
                  seeking.current = false
                  showChrome()
                }}
                onPointerCancel={() => {
                  seeking.current = false
                  showChrome()
                }}
                onChange={(e) => onSeekInput(e.currentTarget, true)}
              />
            </div>
            <span className={`${styles.time} ${styles.timeEnd}`} ref={durRef}>
              0:00
            </span>
          </div>

          <div className={styles.transport} role="group" aria-label="Playback controls">
            {onPrevEpisode ? (
              <button
                type="button"
                className={styles.iconBtn}
                aria-label="Previous episode"
                onClick={onPrevEpisode}
              >
                <IconSkip />
              </button>
            ) : (
              <span className={styles.spacer} aria-hidden />
            )}
            <button
              type="button"
              className={styles.iconBtn}
              aria-label={`Seek backward ${SEEK_SECONDS} seconds`}
              onClick={() => doSeek(-SEEK_SECONDS)}
            >
              <span className={styles.seekSkip}>
                <span aria-hidden>↶</span>
                {SEEK_SECONDS}
              </span>
            </button>
            <button
              type="button"
              className={`${styles.iconBtn} ${styles.transportPlay}`}
              aria-label={paused ? 'Play' : 'Pause'}
              onClick={togglePlay}
            >
              {paused ? <IconPlay /> : <IconPause />}
            </button>
            <button
              type="button"
              className={styles.iconBtn}
              aria-label={`Seek forward ${SEEK_SECONDS} seconds`}
              onClick={() => doSeek(SEEK_SECONDS)}
            >
              <span className={styles.seekSkip}>
                <span aria-hidden>↷</span>
                {SEEK_SECONDS}
              </span>
            </button>
            {onNextEpisode ? (
              <button
                type="button"
                className={styles.iconBtn}
                aria-label="Next episode"
                onClick={onNextEpisode}
              >
                <IconSkip fwd />
              </button>
            ) : (
              <span className={styles.spacer} aria-hidden />
            )}
          </div>

          <div className={styles.secondary} role="group" aria-label="Player settings">
            {showQuality ? (
              <button
                type="button"
                className={styles.iconBtn}
                aria-label="Select quality"
                data-on={menu === 'quality'}
                onClick={() => openMenu('quality')}
              >
                HD
              </button>
            ) : null}
            {!useMoreOverflow && showAudio ? (
              <button
                type="button"
                className={styles.iconBtn}
                aria-label="Select audio"
                data-on={menu === 'audio'}
                onClick={() => openMenu('audio')}
              >
                Au
              </button>
            ) : null}
            {!useMoreOverflow && showCc ? (
              <button
                type="button"
                className={styles.iconBtn}
                aria-label="Select subtitles"
                data-on={menu === 'subtitles'}
                onClick={() => openMenu('subtitles')}
              >
                CC
              </button>
            ) : null}
            <button
              type="button"
              className={styles.iconBtn}
              aria-label="Select playback speed"
              data-on={menu === 'speed'}
              onClick={() => openMenu('speed')}
            >
              {rate === 1 ? '1x' : `${rate}x`}
            </button>
            {useMoreOverflow ? (
              <button
                type="button"
                className={styles.iconBtn}
                aria-label="More player options"
                data-on={menu === 'more' || menu === 'audio' || menu === 'subtitles'}
                onClick={() => openMenu('more')}
              >
                ···
              </button>
            ) : null}
            <button
              type="button"
              className={styles.iconBtn}
              aria-label="Lock player"
              onClick={() => {
                setLocked(true)
                setVisible(false)
                setMenu(null)
                setLockPeek(true)
                clearHideTimer()
                if (peekTimer.current) window.clearTimeout(peekTimer.current)
                peekTimer.current = window.setTimeout(() => setLockPeek(false), 1800)
              }}
            >
              <IconLock />
            </button>
            <button
              type="button"
              className={styles.iconBtn}
              aria-label={fs ? 'Exit fullscreen' : 'Enter fullscreen'}
              onClick={toggleFs}
            >
              <IconFs exit={fs} />
            </button>
          </div>
        </div>
      </div>

      {menu ? (
        <>
          <button
            type="button"
            className={styles.sheetBack}
            aria-label="Close menu"
            onClick={() => setMenu(null)}
          />
          <div className={styles.sheet} role="dialog" aria-label={menuTitle}>
            <div className={styles.sheetHead}>
              <h2 className={styles.sheetTitle}>{menuTitle}</h2>
              <button type="button" className={styles.iconBtn} aria-label="Close" onClick={() => setMenu(null)}>
                ×
              </button>
            </div>
            {menu === 'quality'
              ? qualityRows.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    className={styles.row}
                    data-on={r.on}
                    onClick={() => {
                      r.pick()
                      setMenu(null)
                    }}
                  >
                    {r.on ? '✓ ' : ''}
                    {r.label}
                  </button>
                ))
              : null}
            {menu === 'audio'
              ? audioList.map((r) => (
                  <button
                    key={r.i}
                    type="button"
                    className={styles.row}
                    data-on={r.on}
                    onClick={() => pickAudio(r.i)}
                  >
                    {r.on ? '✓ ' : ''}
                    {r.label}
                  </button>
                ))
              : null}
            {menu === 'subtitles' ? (
              <>
                <button
                  type="button"
                  className={styles.row}
                  data-on={!textList.some((t) => t.on)}
                  onClick={() => pickText(null)}
                >
                  {!textList.some((t) => t.on) ? '✓ ' : ''}
                  Off
                </button>
                {textList.map((r) => (
                  <button
                    key={r.i}
                    type="button"
                    className={styles.row}
                    data-on={r.on}
                    onClick={() => pickText(r.i)}
                  >
                    {r.on ? '✓ ' : ''}
                    {r.label}
                  </button>
                ))}
                <button type="button" className={styles.row} onClick={() => openMenu('ccStyle')}>
                  Style…
                </button>
              </>
            ) : null}
            {menu === 'speed'
              ? PLAYBACK_RATES.map((r) => (
                  <button
                    key={r}
                    type="button"
                    className={styles.row}
                    data-on={rate === r}
                    onClick={() => pickRate(r)}
                  >
                    {rate === r ? '✓ ' : ''}
                    {r}x
                  </button>
                ))
              : null}
            {menu === 'more' ? (
              <>
                {showAudio ? (
                  <button type="button" className={styles.row} onClick={() => openMenu('audio')}>
                    Audio
                  </button>
                ) : null}
                {showCc ? (
                  <button type="button" className={styles.row} onClick={() => openMenu('subtitles')}>
                    Subtitles / CC
                  </button>
                ) : null}
              </>
            ) : null}
            {menu === 'ccStyle' ? (
              <>
                {(['sm', 'md', 'lg'] as const).map((s) => (
                  <button
                    key={s}
                    type="button"
                    className={styles.row}
                    data-on={ccSize === s}
                    onClick={() => {
                      setCcSize(s)
                      savePlayerPrefs({ ccSize: s })
                      applyCcStyle(player, s, ccBg)
                    }}
                  >
                    {ccSize === s ? '✓ ' : ''}
                    Size {s}
                  </button>
                ))}
                {[0, 0.4, 0.65, 0.9].map((bg) => (
                  <button
                    key={bg}
                    type="button"
                    className={styles.row}
                    data-on={ccBg === bg}
                    onClick={() => {
                      setCcBg(bg)
                      savePlayerPrefs({ ccBg: bg })
                      applyCcStyle(player, ccSize, bg)
                    }}
                  >
                    {ccBg === bg ? '✓ ' : ''}
                    Background {Math.round(bg * 100)}%
                  </button>
                ))}
              </>
            ) : null}
          </div>
        </>
      ) : null}

      {nextIn != null && onNextEpisode ? (
        <div className={styles.nextCard} role="dialog" aria-label="Next episode">
          <p className={styles.nextTitle}>Next episode</p>
          <p className={styles.nextName}>Starting in {nextIn}…</p>
          <div className={styles.nextActions}>
            <button type="button" className={styles.nextPlay} onClick={() => {
              setNextIn(null)
              onNextEpisode()
            }}>
              Play now
            </button>
            <button type="button" className={styles.nextCancel} onClick={() => setNextIn(null)}>
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
