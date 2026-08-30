import { useCallback, useEffect, useRef, useState } from 'react'
import { CONTROL_HIDE_MS } from './playerConstants'

type PlayerPaused = { paused: () => boolean }

/**
 * Single controls-visibility controller for cinema chrome.
 * Video.js remains playback source of truth; this only owns UI visibility + one hide timer.
 */
export function usePlayerControlsVisibility(opts: {
  player: PlayerPaused
  paused: boolean
  locked: boolean
  menuOpen: boolean
  hideMs?: number
}) {
  const { player, paused, locked, menuOpen, hideMs = CONTROL_HIDE_MS } = opts
  const [visible, setVisible] = useState(true)
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current)
      timerRef.current = undefined
    }
  }, [])

  const armHide = useCallback(() => {
    clearTimer()
    if (locked || menuOpen || paused) return
    try {
      if (player.paused() !== false) return
    } catch {
      return
    }
    timerRef.current = window.setTimeout(() => setVisible(false), hideMs)
  }, [clearTimer, locked, menuOpen, paused, player, hideMs])

  const show = useCallback(() => {
    setVisible(true)
    armHide()
  }, [armHide])

  const hide = useCallback(() => {
    if (locked || menuOpen || paused) return
    clearTimer()
    setVisible(false)
  }, [locked, menuOpen, paused, clearTimer])

  const toggle = useCallback(() => {
    setVisible((v) => {
      if (v) {
        if (locked || menuOpen || paused) return true
        clearTimer()
        return false
      }
      return true
    })
  }, [locked, menuOpen, paused, clearTimer])

  // After becoming visible via toggle, arm hide when playing.
  useEffect(() => {
    if (!visible) return
    armHide()
  }, [visible, armHide])

  useEffect(() => {
    if (paused || locked || menuOpen) {
      clearTimer()
      setVisible(true)
      return
    }
    armHide()
  }, [paused, locked, menuOpen, armHide, clearTimer])

  useEffect(() => () => clearTimer(), [clearTimer])

  return { visible, show, hide, toggle, armHide, clearTimer, setVisible }
}
