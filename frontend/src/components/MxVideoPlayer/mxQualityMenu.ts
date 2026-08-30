import videojs from 'video.js'

export type MxQualitySource = { key: string; label: string; url: string }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type QualityLevelListLike = any

export type MxQualityPlayerOptions = {
  getState: () => { sources: MxQualitySource[]; currentIndex: number }
  onPickUrl: (index: number) => void
  /** When true, single adaptive URL — menu uses player.qualityLevels() (HLS/DASH ladder). */
  useVhsLevels?: boolean
  onPickVhs?: (levelIndex: number) => void
}

let registered = false

export function menuLabelForSource(src: MxQualitySource): string {
  if (src.key === 'stream_default') {
    return `Auto (${src.label})`
  }
  if (src.key === 'stream_only') {
    return src.label || 'Auto'
  }
  const isPremium = /high|1080|gold/i.test(src.key) || /1080/i.test(src.label)
  return isPremium ? `${src.label} · Gold` : src.label
}

export function vhsSelectedLevelIndex(ql: QualityLevelListLike): number {
  if (!ql || typeof ql.length !== 'number') return -1
  const enabled: number[] = []
  for (let i = 0; i < ql.length; i++) {
    if (ql[i]?.enabled) enabled.push(i)
  }
  if (enabled.length === ql.length) return -1
  if (enabled.length === 1) return enabled[0]!
  return -1
}

export function sortVhsLevelIndices(ql: QualityLevelListLike): { idx: number; label: string }[] {
  const rows: { idx: number; h: number; bw: number }[] = []
  for (let i = 0; i < ql.length; i++) {
    const L = ql[i]
    const h = typeof L?.height === 'number' && L.height > 0 ? L.height : 0
    const bw = typeof L?.bandwidth === 'number' && L.bandwidth > 0 ? L.bandwidth : 0
    rows.push({ idx: i, h, bw })
  }
  rows.sort((a, b) => b.h - a.h || b.bw - a.bw || a.idx - b.idx)
  return rows.map((r) => {
    let label: string
    if (r.h > 0) label = `${r.h}p`
    else if (r.bw > 0) label = `${Math.round(r.bw / 1000)} kbps`
    else label = `Level ${r.idx + 1}`
    return { idx: r.idx, label }
  })
}

/** Enable Auto (all levels) or a single VHS quality ladder index. */
export function applyVhsQualityLevel(ql: QualityLevelListLike, levelIndex: number): void {
  if (!ql || typeof ql.length !== 'number') return
  if (levelIndex < 0) {
    for (let j = 0; j < ql.length; j++) {
      try {
        ql[j].enabled = true
      } catch {
        /* */
      }
    }
    return
  }
  for (let j = 0; j < ql.length; j++) {
    try {
      ql[j].enabled = j === levelIndex
    } catch {
      /* */
    }
  }
}

/**
 * Registers Video.js components for an MX-style "Video Quality" popup menu.
 */
export function registerMxQualityMenu(): void {
  if (registered) return
  registered = true

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const vjs = videojs as any
  const MenuButton = vjs.getComponent('MenuButton')
  const MenuItem = vjs.getComponent('MenuItem')

  class MxQualityMenuItem extends MenuItem {
    mxMode_: 'url' | 'vhs'
    mxIndex_: number
    mq_: MxQualityPlayerOptions

    constructor(player: unknown, options: Record<string, unknown>) {
      super(player, {
        label: options.label,
        selectable: true,
        selected: options.selected,
      })
      this.mxMode_ = options.mxMode as 'url' | 'vhs'
      this.mxIndex_ = options.mxIndex as number
      this.mq_ = options.mq as MxQualityPlayerOptions
    }

    handleClick() {
      if (this.mxMode_ === 'url') {
        this.mq_.onPickUrl(this.mxIndex_)
      } else {
        this.mq_.onPickVhs?.(this.mxIndex_)
      }
      const bar = this.player().getChild('controlBar')
      const mb = bar?.getChild?.('MxQualityMenuButton')
      mb?.update?.()
    }
  }

  class MxQualityMenuButton extends MenuButton {
    constructor(player: unknown, options: Record<string, unknown>) {
      super(player, { ...options, title: 'Video Quality' })
      this.controlText('Video quality')
      this.menuButton_.addClass('vjs-icon-hd')
    }

    buildCSSClass() {
      return `vjs-mx-quality-button ${super.buildCSSClass()}`
    }

    createItems() {
      const mq = this.player().options_.mxQuality as MxQualityPlayerOptions | undefined
      if (!mq?.getState) return []
      const { sources, currentIndex } = mq.getState()
      if (!sources?.length) return []

      if (sources.length > 1) {
        return sources.map((src, i) => {
          return new MxQualityMenuItem(this.player(), {
            label: menuLabelForSource(src),
            selected: i === currentIndex,
            mxMode: 'url',
            mxIndex: i,
            mq,
          })
        })
      }

      if (mq.useVhsLevels && typeof this.player().qualityLevels === 'function') {
        const ql = this.player().qualityLevels()
        if (ql && ql.length >= 2) {
          const sorted = sortVhsLevelIndices(ql)
          const sel = vhsSelectedLevelIndex(ql)
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const items: any[] = [
            new MxQualityMenuItem(this.player(), {
              label: 'Auto',
              selected: sel < 0,
              mxMode: 'vhs',
              mxIndex: -1,
              mq,
            }),
          ]
          for (const { idx, label } of sorted) {
            items.push(
              new MxQualityMenuItem(this.player(), {
                label,
                selected: sel === idx,
                mxMode: 'vhs',
                mxIndex: idx,
                mq,
              }),
            )
          }
          return items
        }
      }

      return []
    }
  }

  vjs.registerComponent('MxQualityMenuButton', MxQualityMenuButton)
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PlayerLike = any

export function addMxQualityMenuButton(player: PlayerLike): void {
  const mq = player.options_?.mxQuality as MxQualityPlayerOptions | undefined
  if (!mq?.getState) return
  const { sources } = mq.getState()
  if (!sources?.length) return

  const cb = player.getChild('controlBar')
  if (!cb?.addChild) return

  const fs = cb.getChild('fullscreenToggle')
  const idxFs = fs ? cb.children().indexOf(fs) : -1
  const insertAt = idxFs >= 0 ? idxFs : cb.children().length
  cb.addChild('MxQualityMenuButton', {}, insertAt)
}

/** Hide until VHS exposes 2+ rungs (avoids empty/useless menu on startup). */
export function syncMxQualityButtonVisibility(player: PlayerLike): void {
  const mq = player.options_?.mxQuality as MxQualityPlayerOptions | undefined
  const cb = player.getChild('controlBar')
  const mb = cb?.getChild?.('MxQualityMenuButton')
  if (!mq?.getState || !mb) return
  const { sources } = mq.getState()
  if (!sources?.length) return

  if (sources.length > 1) {
    mb.removeClass?.('vjs-hidden')
    mb.removeClass?.('vjs-mx-quality-pending')
    return
  }

  if (!mq.useVhsLevels || typeof player.qualityLevels !== 'function') {
    mb.addClass?.('vjs-hidden')
    return
  }

  const ql = player.qualityLevels()
  if (ql && ql.length >= 2) {
    mb.removeClass?.('vjs-hidden')
    mb.removeClass?.('vjs-mx-quality-pending')
    mb.update?.()
  } else {
    mb.addClass?.('vjs-hidden')
    mb.addClass?.('vjs-mx-quality-pending')
  }
}
