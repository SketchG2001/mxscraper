import { usePageMeta } from '../../hooks/usePageMeta'
import { StaticDocLayout } from './StaticDocLayout'

export function PrivacyPage() {
  usePageMeta('Privacy Policy', 'How MX Scraper handles your data.')

  return (
    <StaticDocLayout title="Privacy Policy">
      <p>
        This policy describes how <strong>MX Scraper</strong> treats information when you
        use the app. We aim to keep this minimal and transparent.
      </p>
      <h2>What we collect</h2>
      <ul>
        <li>
          <strong>Watch progress:</strong> Resume position and related metadata may be
          stored locally in your browser (for example in <code>localStorage</code>) so you
          can continue watching on this device.
        </li>
        <li>
          <strong>Network requests:</strong> Your browser talks to our backend and to
          streaming endpoints as needed for search and playback. Those servers may log
          standard technical data such as IP address and timestamps.
        </li>
      </ul>
      <h2>What we do not do</h2>
      <p>
        We do not sell your personal information. This project is not an ad network and is
        not affiliated with MX Player or its parent company.
      </p>
      <h2>Your choices</h2>
      <p>
        You can clear site data in your browser to remove locally stored progress.
      </p>
    </StaticDocLayout>
  )
}
