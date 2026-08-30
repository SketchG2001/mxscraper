import { SystemBars } from '@capacitor/core'
import { ScreenOrientation } from '@capacitor/screen-orientation'
import { isAndroidNative } from '../../lib/apiBase'

export const PLAYER_FS_CLASS = 'mx-player-fs'

function setFsDocumentClass(on: boolean) {
  const root = document.documentElement
  const body = document.body
  if (on) {
    root.classList.add(PLAYER_FS_CLASS)
    body.classList.add(PLAYER_FS_CLASS)
  } else {
    root.classList.remove(PLAYER_FS_CLASS)
    body.classList.remove(PLAYER_FS_CLASS)
  }
}

function orientationKind(): 'landscape' | 'portrait' | 'unknown' {
  const t = screen.orientation?.type || ''
  if (t.includes('landscape')) return 'landscape'
  if (t.includes('portrait')) return 'portrait'
  if (typeof window.matchMedia === 'function') {
    if (window.matchMedia('(orientation: landscape)').matches) return 'landscape'
    if (window.matchMedia('(orientation: portrait)').matches) return 'portrait'
  }
  return 'unknown'
}

function waitForOrientation(
  kind: 'landscape' | 'portrait',
  timeoutMs: number,
): Promise<void> {
  if (orientationKind() === kind) return Promise.resolve()
  return new Promise((resolve) => {
    let settled = false
    const finish = () => {
      if (settled) return
      settled = true
      window.clearTimeout(timer)
      try {
        screen.orientation?.removeEventListener?.('change', onChange)
      } catch {
        /* */
      }
      window.removeEventListener('orientationchange', onChange)
      resolve()
    }
    const onChange = () => {
      if (orientationKind() === kind) finish()
    }
    const timer = window.setTimeout(finish, timeoutMs)
    try {
      screen.orientation?.addEventListener?.('change', onChange)
    } catch {
      /* */
    }
    window.addEventListener('orientationchange', onChange)
  })
}

async function lockLandscapeNative(): Promise<void> {
  if (!isAndroidNative()) return
  try {
    await ScreenOrientation.lock({ orientation: 'landscape' })
  } catch {
    /* tablet / OS may ignore */
  }
}

async function restorePortraitNative(): Promise<void> {
  if (!isAndroidNative()) return
  try {
    await ScreenOrientation.lock({ orientation: 'portrait' })
    await waitForOrientation('portrait', 500)
  } catch {
    /* */
  }
  try {
    await ScreenOrientation.unlock()
  } catch {
    /* */
  }
}

async function hideSystemBars(): Promise<void> {
  if (!isAndroidNative()) return
  try {
    await SystemBars.hide()
  } catch {
    /* */
  }
}

async function showSystemBars(): Promise<void> {
  if (!isAndroidNative()) return
  try {
    await SystemBars.show()
  } catch {
    /* */
  }
}

export function isShellFullscreen(shell: HTMLElement | null | undefined): boolean {
  if (!shell) return Boolean(document.fullscreenElement)
  return Boolean(document.fullscreenElement === shell || shell.hasAttribute('data-fullwindow'))
}

/** Notify Video.js / layout after size change without remounting. */
export function bumpPlayerLayout(player?: { trigger?: (ev: string) => void } | null) {
  try {
    player?.trigger?.('resize')
  } catch {
    /* */
  }
  try {
    window.dispatchEvent(new Event('resize'))
  } catch {
    /* */
  }
}

/**
 * Enter immersive player fullscreen.
 * One source of truth for Android + web.
 * Android: landscape lock → hide system bars → CSS full-window (WebView FS unreliable).
 * Web: element.requestFullscreen when available.
 */
export async function enterPlayerFullscreen(
  shell: HTMLElement,
  player?: { trigger?: (ev: string) => void } | null,
): Promise<void> {
  setFsDocumentClass(true)

  if (isAndroidNative()) {
    await lockLandscapeNative()
    await hideSystemBars()
    await waitForOrientation('landscape', 700)
    shell.setAttribute('data-fullwindow', 'true')
    bumpPlayerLayout(player)
    window.requestAnimationFrame(() => bumpPlayerLayout(player))
    return
  }

  try {
    if (typeof shell.requestFullscreen === 'function') {
      await shell.requestFullscreen()
      bumpPlayerLayout(player)
      return
    }
  } catch {
    /* browser rejected */
  }

  shell.setAttribute('data-fullwindow', 'true')
  bumpPlayerLayout(player)
}

export async function exitPlayerFullscreen(
  shell: HTMLElement | null | undefined,
  player?: { trigger?: (ev: string) => void } | null,
): Promise<void> {
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
    }
  } catch {
    /* */
  }
  shell?.removeAttribute('data-fullwindow')
  setFsDocumentClass(false)
  await restorePortraitNative()
  await showSystemBars()
  bumpPlayerLayout(player)
  window.requestAnimationFrame(() => bumpPlayerLayout(player))
}
