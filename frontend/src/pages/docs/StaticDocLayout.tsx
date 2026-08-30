import { useNavigate } from 'react-router-dom'
import { navigateBack } from '../../lib/navBack'
import styles from './StaticDoc.module.css'

export function StaticDocLayout({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  const navigate = useNavigate()
  return (
    <div className={styles.page}>
      <button
        type="button"
        className={styles.back}
        onClick={() => navigateBack(navigate)}
      >
        ← Back
      </button>
      <article className={styles.article}>
        <h1 className={styles.h1}>{title}</h1>
        <div className={styles.prose}>{children}</div>
      </article>
    </div>
  )
}
