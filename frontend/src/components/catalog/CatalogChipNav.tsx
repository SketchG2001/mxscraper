import styles from './CatalogChipNav.module.css'

export type CatalogChip = { id: string; label: string }

type Props = {
  items: CatalogChip[]
  activeId: string
  onSelect: (id: string) => void
  'aria-label'?: string
}

export function CatalogChipNav({
  items,
  activeId,
  onSelect,
  'aria-label': ariaLabel = 'Jump to category',
}: Props) {
  return (
    <nav className={styles.nav} aria-label={ariaLabel}>
      {items.map((c) => (
        <button
          key={c.id}
          type="button"
          className={styles.chip}
          data-active={c.id === activeId}
          onClick={() => onSelect(c.id)}
        >
          {c.label}
        </button>
      ))}
    </nav>
  )
}
