import styles from './SiteCredit.module.css'

export function SiteCredit() {
  return (
    <p className={styles.line}>
      Made with{' '}
      <span className={styles.heart} role="img" aria-label="love">
        ❤️
      </span>{' '}
      by Sketch
    </p>
  )
}
