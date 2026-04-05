import styles from './CatalogSectionTitle.module.css'

type Props = {
  title: string
  subtitle?: string
  /** Larger “Popular collections” style vs compact row header */
  variant?: 'section' | 'row'
  className?: string
  id?: string
}

export function CatalogSectionTitle({
  title,
  subtitle,
  variant = 'section',
  className,
  id,
}: Props) {
  const Tag = variant === 'section' ? 'h2' : 'h3'
  return (
    <div className={`${styles.wrap} ${className ?? ''}`.trim()}>
      <Tag
        id={id}
        className={`${styles.title} ${variant === 'section' ? styles.titleSection : styles.titleRow}`}
      >
        <span>{title}</span>
        <span className={styles.chev} aria-hidden>
          ›
        </span>
      </Tag>
      {subtitle ? <p className={styles.sub}>{subtitle}</p> : null}
    </div>
  )
}
