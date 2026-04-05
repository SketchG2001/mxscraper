import { useEffect } from 'react'
import { adsenseClientId, isAdsenseConfigured } from '../../lib/adsenseConfig'

const SCRIPT_ID = 'mxscraper-adsense-script'

/**
 * Loads the AdSense tag once. Pair with display units (AdDisplayUnit) or use
 * Auto ads from the AdSense console.
 */
export function AdSenseLoader() {
  useEffect(() => {
    if (!isAdsenseConfigured()) return
    if (document.getElementById(SCRIPT_ID)) return

    const client = adsenseClientId()
    const s = document.createElement('script')
    s.id = SCRIPT_ID
    s.async = true
    s.crossOrigin = 'anonymous'
    s.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(client)}`
    document.head.appendChild(s)
  }, [])

  return null
}
