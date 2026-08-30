/** video.js Player typing in this repo does not expose controlBar on the public type. */
export type PlayerWithControlBar = {
  controlBar: {
    el: () => HTMLElement
    getChild(name: string): {
      el?: () => HTMLElement | undefined
    } | undefined
    children: () => unknown[]
    addChild: (
      child: string,
      options: Record<string, unknown>,
      index?: number,
    ) => unknown
  }
}

export type MxPlayerReadyOptions = {
  onPrevEpisode?: () => void
  onNextEpisode?: () => void
}

/**
 * MX-style control bar tweaks: progress on its own top row; optional prev/next episode
 * buttons (SPA navigate via callbacks).
 */
export function applyMxPlayerReady(
  player: PlayerWithControlBar,
  opts: MxPlayerReadyOptions,
): void {
  const bar = player.controlBar
  if (!bar) return

  const barEl = bar.el()
  const prog = bar.getChild('progressControl')
  const progEl = prog?.el?.()
  if (barEl && progEl && barEl.firstChild !== progEl) {
    barEl.insertBefore(progEl, barEl.firstChild)
  }

  const prevFn = opts.onPrevEpisode
  const nextFn = opts.onNextEpisode

  const playToggle = bar.getChild('playToggle')
  const idxPlay = playToggle ? bar.children().indexOf(playToggle) : -1
  if (idxPlay >= 0 && typeof prevFn === 'function') {
    bar.addChild(
      'button',
      {
        className: 'vjs-mx-prev-episode vjs-control vjs-button vjs-hidden',
        controlText: 'Previous episode',
        clickHandler() {
          prevFn()
        },
      },
      idxPlay + 1,
    )
  }

  const skipForward = bar.getChild('skipForward')
  const idxSf = skipForward ? bar.children().indexOf(skipForward) : -1
  if (idxSf >= 0 && typeof nextFn === 'function') {
    bar.addChild(
      'button',
      {
        className: 'vjs-mx-next-episode vjs-control vjs-button vjs-hidden',
        controlText: 'Next episode',
        clickHandler() {
          nextFn()
        },
      },
      idxSf + 1,
    )
  }
}

/** Show/hide episode skip buttons without recreating the player. */
export function syncMxEpisodeButtons(
  player: PlayerWithControlBar,
  flags: { hasPrev: boolean; hasNext: boolean },
): void {
  const barEl = player.controlBar?.el?.()
  if (!barEl) return
  const prev = barEl.querySelector('.vjs-mx-prev-episode')
  const next = barEl.querySelector('.vjs-mx-next-episode')
  prev?.classList.toggle('vjs-hidden', !flags.hasPrev)
  next?.classList.toggle('vjs-hidden', !flags.hasNext)
}
