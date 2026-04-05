import { useEffect } from 'react'

const SITE = 'MX Scraper'
const DEFAULT_DESC =
  'Search MX Player movies and shows, open detail pages, and watch streams in one place. Sign in for playback.'

/** Updates document title and meta description for SPA SEO hints and browser UI. */
export function usePageMeta(title: string, description?: string) {
  useEffect(() => {
    const fullTitle = title.includes(SITE) ? title : `${title} · ${SITE}`
    document.title = fullTitle
    const el = document.querySelector(
      'meta[name="description"]',
    ) as HTMLMetaElement | null
    if (el) {
      el.setAttribute('content', (description ?? DEFAULT_DESC).slice(0, 320))
    }
    const ogTitle = document.querySelector(
      'meta[property="og:title"]',
    ) as HTMLMetaElement | null
    const ogDesc = document.querySelector(
      'meta[property="og:description"]',
    ) as HTMLMetaElement | null
    if (ogTitle) ogTitle.setAttribute('content', fullTitle)
    if (ogDesc)
      ogDesc.setAttribute('content', (description ?? DEFAULT_DESC).slice(0, 300))

    return () => {
      document.title = SITE
      if (el) el.setAttribute('content', DEFAULT_DESC)
      if (ogTitle) ogTitle.setAttribute('content', SITE)
      if (ogDesc) ogDesc.setAttribute('content', DEFAULT_DESC)
    }
  }, [title, description])
}
