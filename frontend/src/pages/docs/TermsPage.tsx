import { usePageMeta } from '../../hooks/usePageMeta'
import { StaticDocLayout } from './StaticDocLayout'

export function TermsPage() {
  usePageMeta('Terms of Use', 'Terms of Use for MX Scraper.')

  return (
    <StaticDocLayout title="Terms of Use">
      <p>
        <strong>MX Scraper</strong> is an unofficial hobby project for browsing publicly
        available catalog metadata. By using this app, you agree to the following.
      </p>
      <h2>Acceptable use</h2>
      <p>
        You use the service at your own risk. Do not attempt to misuse authentication,
        overload servers, or circumvent technical protections. Playback and catalog
        access depend on third-party services and may change or stop working at any time.
      </p>
      <h2>No warranty</h2>
      <p>
        The app is provided &quot;as is&quot; without warranties of any kind. We are not
        responsible for any loss or damage arising from your use of the app.
      </p>
      <h2>Changes</h2>
      <p>
        These terms may be updated occasionally. Continued use after changes means you
        accept the revised terms.
      </p>
    </StaticDocLayout>
  )
}
