import { useEffect, useRef } from 'react'
import { adsenseClientId, isAdsenseConfigured } from '../../lib/adsenseConfig'
import styles from './adsense.module.css'

declare global {
  interface Window {
    adsbygoogle?: Record<string, unknown>[]
  }
}

type Props = {
  slot: string
  /** layout= horizontal | rectangle | vertical — passed to data-ad-format where supported */
  format?: 'auto' | 'horizontal' | 'rectangle' | 'vertical' | 'fluid'
  className?: string
  /** Screen-reader / small caption above unit */
  label?: string
  variant?: 'default' | 'sidebar'
}

export function AdDisplayUnit({
  slot,
  format = 'auto',
  className = '',
  label = 'Advertisement',
  variant = 'default',
}: Props) {
  const insRef = useRef<HTMLModElement>(null)
  const filledRef = useRef(false)

  useEffect(() => {
    if (!isAdsenseConfigured() || !slot.trim()) return
    const el = insRef.current
    if (!el || filledRef.current) return

    try {
      filledRef.current = true
      ;(window.adsbygoogle = window.adsbygoogle || []).push({})
    } catch {
      filledRef.current = false
    }

    return () => {
      filledRef.current = false
    }
  }, [slot])

  if (!isAdsenseConfigured() || !slot.trim()) return null

  const unitClass =
    variant === 'sidebar'
      ? `${styles.unit} ${styles.unitSidebar} ${className}`.trim()
      : `${styles.unit} ${className}`.trim()

  return (
    <div className={styles.wrap}>
      <div className="mxscraper-ad-inner" style={{ width: '100%', maxWidth: '100%' }}>
        {label ? <p className={styles.label}>{label}</p> : null}
        <ins
          ref={insRef}
          className={`adsbygoogle ${unitClass}`}
          style={{ display: 'block' }}
          data-ad-client={adsenseClientId()}
          data-ad-slot={slot.trim()}
          data-ad-format={format}
          data-full-width-responsive={format === 'auto' ? 'true' : undefined}
        />
      </div>
    </div>
  )
}
