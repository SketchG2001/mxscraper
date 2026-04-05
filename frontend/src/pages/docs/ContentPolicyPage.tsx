import { usePageMeta } from '../../hooks/usePageMeta'
import { StaticDocLayout } from './StaticDocLayout'

export function ContentPolicyPage() {
  usePageMeta('Content Policy', 'Content and intellectual property — MX Scraper.')

  return (
    <StaticDocLayout title="Content Policy">
      <p>
        <strong>MX Scraper</strong> does not host video files. Streams and artwork come
        from third-party services and remain the property of their respective rights
        holders.
      </p>
      <h2>Respect for rights</h2>
      <p>
        You are responsible for complying with copyright and applicable laws in your
        region. Use the app only in ways that respect content owners and platform terms.
      </p>
      <h2>Trademarks</h2>
      <p>
        Names and logos such as &quot;MX Player&quot; belong to their owners. This app is
        an independent project and is not endorsed by or affiliated with MX Media &
        Entertainment.
      </p>
      <h2>Takedowns</h2>
      <p>
        If you believe this app improperly references your content, contact the project
        maintainer with details so the issue can be reviewed.
      </p>
    </StaticDocLayout>
  )
}
