import { Link } from 'react-router-dom'
import { usePageMeta } from '../../hooks/usePageMeta'
import { StaticDocLayout } from './StaticDocLayout'

export function HelpPage() {
  usePageMeta('Help & FAQ', 'How to use MX Scraper — search, browse, and playback.')

  return (
    <StaticDocLayout title="Help & FAQ">
      <p>
        Quick answers for using <strong>MX Scraper</strong>. For legal and privacy topics,
        see the links in the footer.
      </p>
      <h2>Finding titles</h2>
      <p>
        Open <strong>Search</strong> in the header to look up movies and shows. You can
        also paste or resolve an <code>mxplayer.in</code> link when that flow is available
        in the app.
      </p>
      <h2>Browsing and watching</h2>
      <p>
        From the home page, open rows and posters to reach a title page, then play or pick
        an episode. <Link to="/">Return home</Link> anytime to see shelves and continue
        watching.
      </p>
      <h2>Playback</h2>
      <p>
        Open a title and press Play. If a stream fails to load, confirm the backend and
        HLS proxy are running.
      </p>
      <h2>Resume progress</h2>
      <p>
        Watch progress is saved in this browser so you can resume. Clearing site data will
        remove that history.
      </p>
      <h2>Keyboard shortcuts (player)</h2>
      <p>
        In the video player: Space toggles play/pause; arrow keys seek by about ten seconds
        after the player is focused.
      </p>
    </StaticDocLayout>
  )
}
