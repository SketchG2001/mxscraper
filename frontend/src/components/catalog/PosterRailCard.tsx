import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { ShelfItem } from '../../types/api'
import { formatContentType } from './formatContentType'
import styles from './PosterRailCard.module.css'

const SHOW_DELAY_MS = 380
const HIDE_DELAY_MS = 120

type Props = {
  item: ShelfItem
  onOpen: () => void
}

export function PosterRailCard({ item, onOpen }: Props) {
  const rootRef = useRef<HTMLDivElement>(null)
  const showTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [popover, setPopover] = useState<{
    left: number
    top: number
    flip: boolean
  } | null>(null)

  const clearTimers = useCallback(() => {
    if (showTimer.current) {
      clearTimeout(showTimer.current)
      showTimer.current = null
    }
    if (hideTimer.current) {
      clearTimeout(hideTimer.current)
      hideTimer.current = null
    }
  }, [])

  const computePosition = useCallback(() => {
    const el = rootRef.current
    if (!el) return null
    const rect = el.getBoundingClientRect()
    const vw = window.innerWidth
    const estH = 280
    const margin = 12
    const popW = Math.min(320, vw - 24)
    const halfW = popW / 2
    const centerX = rect.left + rect.width / 2
    const left = Math.max(
      margin + halfW,
      Math.min(centerX, vw - margin - halfW),
    )
    const spaceAbove = rect.top - margin
    const flip = spaceAbove < estH + 24
    const top = flip ? rect.bottom + 10 : rect.top - 10
    return { left, top, flip }
  }, [])

  const scheduleShow = useCallback(() => {
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return
    clearTimers()
    showTimer.current = setTimeout(() => {
      const pos = computePosition()
      if (pos) setPopover(pos)
    }, SHOW_DELAY_MS)
  }, [clearTimers, computePosition])

  const scheduleHide = useCallback(() => {
    clearTimers()
    hideTimer.current = setTimeout(() => setPopover(null), HIDE_DELAY_MS)
  }, [clearTimers])

  const cancelHide = useCallback(() => {
    if (hideTimer.current) {
      clearTimeout(hideTimer.current)
      hideTimer.current = null
    }
  }, [])

  useEffect(() => () => clearTimers(), [clearTimers])

  useEffect(() => {
    if (!popover) return
    const onScroll = () => setPopover(null)
    const onResize = () => setPopover(null)
    window.addEventListener('scroll', onScroll, true)
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('scroll', onScroll, true)
      window.removeEventListener('resize', onResize)
    }
  }, [popover])

  const typeLabel = formatContentType(item.type)

  const popoverNode =
    popover &&
    createPortal(
      <div
        className={styles.popover}
        style={{
          left: popover.left,
          top: popover.top,
          transform: popover.flip
            ? 'translate(-50%, 0)'
            : 'translate(-50%, -100%)',
        }}
        onMouseEnter={cancelHide}
        onMouseLeave={scheduleHide}
        role="dialog"
        aria-label={`${item.title} preview`}
      >
        <div className={styles.popoverMedia}>
          {item.image ? (
            <img src={item.image} alt="" loading="lazy" decoding="async" />
          ) : null}
        </div>
        <div className={styles.popoverBody}>
          <div className={styles.popoverActions}>
            <button
              type="button"
              className={styles.playBtn}
              onClick={() => {
                clearTimers()
                setPopover(null)
                onOpen()
              }}
            >
              <span className={styles.playIcon} aria-hidden>
                ▶
              </span>
              Play
            </button>
          </div>
          <p className={styles.popoverTitle}>{item.title}</p>
          <p className={styles.popoverType}>{typeLabel}</p>
        </div>
      </div>,
      document.body,
    )

  return (
    <>
      <div
        ref={rootRef}
        className={styles.root}
        onMouseEnter={scheduleShow}
        onMouseLeave={scheduleHide}
      >
        <button
          type="button"
          className={styles.tile}
          onClick={() => onOpen()}
        >
          <span className={styles.posterWrap}>
            {item.image ? (
              <img
                src={item.image}
                alt=""
                className={styles.poster}
                loading="lazy"
                decoding="async"
              />
            ) : (
              <span className={styles.posterPh}>No art</span>
            )}
          </span>
          <span className={styles.tileTitle}>{item.title}</span>
          <span className={styles.tileType}>{typeLabel}</span>
        </button>
      </div>
      {popoverNode}
    </>
  )
}
