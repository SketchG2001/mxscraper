import { Link } from 'react-router-dom'
import { SiteCredit } from './SiteCredit'
import styles from './AppFooter.module.css'

type Col = { title: string; links: { label: string; to: string }[] }

const COLUMNS: Col[] = [
  {
    title: 'Explore',
    links: [
      { label: 'Home', to: '/' },
      { label: 'Browse catalog', to: '/#catalog' },
    ],
  },
  {
    title: 'Legal',
    links: [
      { label: 'Terms of Use', to: '/terms' },
      { label: 'Privacy Policy', to: '/privacy' },
      { label: 'Content Policy', to: '/content-policy' },
    ],
  },
  {
    title: 'About',
    links: [
      { label: 'About MX Scraper', to: '/about' },
      { label: 'Help & FAQ', to: '/help' },
    ],
  },
]

export function AppFooter() {
  const year = new Date().getFullYear()

  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.top}>
          <div className={styles.brandCol}>
            <Link to="/" className={styles.logo}>
              MX Scraper
            </Link>
            <p className={styles.tagline}>
              Browse the catalog, keep watch progress on this device, and play in a
              stream-style player — all inside this app.
            </p>
          </div>

          <div className={styles.columns}>
            {COLUMNS.map((col) => (
              <nav key={col.title} aria-label={col.title}>
                <h2 className={styles.colTitle}>{col.title}</h2>
                <ul className={styles.list}>
                  {col.links.map((item) => (
                    <li key={item.label}>
                      <Link className={styles.link} to={item.to}>
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
            ))}
          </div>
        </div>

        <div className={styles.bottom}>
          <p className={styles.copy}>
            © {year} MX Scraper · Content and trademarks belong to their respective owners.
            This project is not affiliated with MX Media & Entertainment.
          </p>
          <div className={styles.creditWrap}>
            <SiteCredit />
          </div>
        </div>
      </div>
    </footer>
  )
}
