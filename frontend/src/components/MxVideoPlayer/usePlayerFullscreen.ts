import { useCallback, useEffect, useState, type RefObject } from 'react'
import {
  enterPlayerFullscreen,
  exitPlayerFullscreen,
  isShellFullscreen,
} from './playerFullscreen'

type PlayerLike = { trigger?: (ev: string) => void } | null

/**
 * One fullscreen controller for cinema chrome.
 * Owns active flag + enter/exit; integrates Android orientation/system bars via playerFullscreen.
 */
export function usePlayerFullscreen(
  shellRef: RefObject<HTMLElement | null>,
  player?: PlayerLike,
) {
  const [active, setActive] = useState(false)

  const sync = useCallback(() => {
    setActive(isShellFullscreen(shellRef.current))
  }, [shellRef])

  useEffect(() => {
    const onFs = () => sync()
    document.addEventListener('fullscreenchange', onFs)
    return () => document.removeEventListener('fullscreenchange', onFs)
  }, [sync])

  // Keep React flag in sync if data-fullwindow is toggled outside this hook.
  useEffect(() => {
    const shell = shellRef.current
    if (!shell || typeof MutationObserver === 'undefined') return
    const obs = new MutationObserver(() => sync())
    obs.observe(shell, { attributes: true, attributeFilter: ['data-fullwindow'] })
    return () => obs.disconnect()
  }, [shellRef, sync])

  useEffect(() => {
    return () => {
      const shell = shellRef.current
      if (isShellFullscreen(shell)) {
        void exitPlayerFullscreen(shell, player)
      }
    }
  }, [shellRef, player])

  const enter = useCallback(async () => {
    const shell = shellRef.current
    if (!shell) return
    await enterPlayerFullscreen(shell, player)
    setActive(true)
  }, [shellRef, player])

  const exit = useCallback(async () => {
    await exitPlayerFullscreen(shellRef.current, player)
    setActive(false)
  }, [shellRef, player])

  const toggle = useCallback(async () => {
    if (isShellFullscreen(shellRef.current)) await exit()
    else await enter()
  }, [shellRef, enter, exit])

  return { active, enter, exit, toggle, sync }
}
