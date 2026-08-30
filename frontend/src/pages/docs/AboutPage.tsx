import { usePageMeta } from '../../hooks/usePageMeta'
import { StaticDocLayout } from './StaticDocLayout'

export function AboutPage() {
  usePageMeta('About', 'About MX Scraper.')

  return (
    <StaticDocLayout title="About MX Scraper">
      <p>
        <strong>MX Scraper</strong> is a small web app for exploring the MX Player catalog:
        search, browse shelves, open detail pages, and watch with a stream-style player when
        your environment is configured for it.
      </p>
      <h2>What it is not</h2>
      <p>
        This is not the official MX Player app or website. It is an independent project for
        learning and personal use. Trademarks belong to their respective owners.
      </p>
      <h2>Tech stack</h2>
      <p>
        The UI is built with React; catalog and stream APIs are provided by a backend you
        run locally or deploy yourself.
      </p>
    </StaticDocLayout>
  )
}
