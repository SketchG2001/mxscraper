import { useLocation } from 'react-router-dom'
import {
  adsenseSlotBottom,
  adsenseSlotTop,
  isAdsenseConfigured,
  isWatchOrPlayerPath,
} from '../../lib/adsenseConfig'
import { AdDisplayUnit } from './AdDisplayUnit'
import styles from './adsense.module.css'

/**
 * Horizontal unit below the site header — hidden on watch routes so nothing appears
 * above or beside the cinema player.
 */
export function SiteAdTop() {
  const { pathname } = useLocation()
  if (!isAdsenseConfigured()) return null
  const slot = adsenseSlotTop()
  if (!slot || isWatchOrPlayerPath(pathname)) return null

  return (
    <div className={styles.placementTop} data-ad-region="top">
      <AdDisplayUnit slot={slot} format="horizontal" label="Advertisement" />
    </div>
  )
}

/**
 * Responsive unit at the end of the main column — below all page content.
 * On watch pages this sits under the title / episode rails, not in the player.
 */
export function SiteAdBottom() {
  if (!isAdsenseConfigured()) return null
  const slot = adsenseSlotBottom()
  if (!slot) return null

  return (
    <div className={styles.placementBottom} data-ad-region="bottom">
      <AdDisplayUnit slot={slot} format="auto" label="Advertisement" />
    </div>
  )
}
