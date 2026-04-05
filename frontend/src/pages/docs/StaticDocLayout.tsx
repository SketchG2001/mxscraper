import { Link } from 'react-router-dom'
import styles from './StaticDoc.module.css'

export function StaticDocLayout({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className={styles.page}>
      <Link to="/" className={styles.back}>
        ← Home
      </Link>
      <article className={styles.article}>
        <h1 className={styles.h1}>{title}</h1>
        <div className={styles.prose}>{children}</div>
      </article>
    </div>
  )
}
