import { useCallback, useEffect, useRef, useState } from 'react'
import type { ShelfItem } from '../types/api'
import { FeedbackState } from './FeedbackState'
import { CatalogChipNav } from './catalog/CatalogChipNav'
import { CatalogSectionTitle } from './catalog/CatalogSectionTitle'
import { PosterRailCard } from './catalog/PosterRailCard'
import styles from './HomeShelves.module.css'

type Props = {
  shelves: { id: string; title: string; items: ShelfItem[] }[]
  loading: boolean
  error: string | null
  onSelectItem: (item: ShelfItem) => void
  onRetry?: () => void
}

export function HomeShelves({
  shelves,
  loading,
  error,
  onSelectItem,
  onRetry,
}: Props) {
  const railRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const [activeShelfId, setActiveShelfId] = useState(() => shelves[0]?.id ?? '')

  useEffect(() => {
    if (shelves.length && !shelves.some((s) => s.id === activeShelfId)) {
      setActiveShelfId(shelves[0].id)
    }
  }, [shelves, activeShelfId])

  useEffect(() => {
    if (!shelves.length) return
    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting)
        if (!visible.length) return
        visible.sort((a, b) => b.intersectionRatio - a.intersectionRatio)
        const id = visible[0].target.getAttribute('data-shelf-id')
        if (id) setActiveShelfId(id)
      },
      {
        root: null,
        rootMargin: '-42% 0px -38% 0px',
        threshold: [0, 0.12, 0.25, 0.4],
      },
    )
    for (const s of shelves) {
      const el = document.getElementById(`shelf-${s.id}`)
      if (el) obs.observe(el)
    }
    return () => obs.disconnect()
  }, [shelves])

  const scrollRail = useCallback((shelfId: string, dir: -1 | 1) => {
    const el = railRefs.current[shelfId]
    if (!el) return
    const delta = Math.round(el.clientWidth * 0.85) * dir
    el.scrollBy({ left: delta, behavior: 'smooth' })
  }, [])

  const scrollToShelf = useCallback((shelfId: string) => {
    setActiveShelfId(shelfId)
    document.getElementById(`shelf-${shelfId}`)?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })
  }, [])

  if (loading && shelves.length === 0) {
    return (
      <section className={styles.wrap} aria-busy="true" aria-label="Loading catalog">
        <div className={styles.skeletonNav} />
        {[0, 1, 2].map((i) => (
          <div key={i} className={styles.skeletonBlock}>
            <div className={styles.skeletonTitle} />
            <div className={styles.skeletonRail}>
              {Array.from({ length: 8 }, (_, j) => (
                <div key={j} className={styles.skeletonTile} />
              ))}
            </div>
          </div>
        ))}
      </section>
    )
  }

  if (!shelves.length && error) {
    return (
      <section className={styles.wrap}>
        <FeedbackState
          title="Something went wrong"
          message="We couldn’t load the catalog."
          onRetry={onRetry}
        />
      </section>
    )
  }

  if (!shelves.length) return null

  const chips = shelves.map((s) => ({ id: s.id, label: s.title }))

  return (
    <section className={styles.wrap} aria-label="Browse by category">
      <CatalogSectionTitle
        variant="section"
        title="Popular collections"
        subtitle="Curated rows — pick a category or scroll each rail sideways."
      />

      <CatalogChipNav
        items={chips}
        activeId={activeShelfId}
        onSelect={scrollToShelf}
      />

      {error && shelves.length > 0 && (
        <p className={styles.warn} role="status">
          Some rows may be incomplete: {error}
        </p>
      )}

      <div className={styles.shelfList}>
        {shelves.map((shelf) => (
          <div
            key={shelf.id}
            id={`shelf-${shelf.id}`}
            className={styles.shelf}
            data-shelf-id={shelf.id}
          >
            <div className={styles.shelfTop}>
              <CatalogSectionTitle
                variant="row"
                title={shelf.title}
                className={styles.shelfTitleWrap}
              />
              <div className={styles.shelfArrows}>
                <button
                  type="button"
                  className={styles.arrow}
                  aria-label={`Scroll ${shelf.title} left`}
                  onClick={() => scrollRail(shelf.id, -1)}
                >
                  ‹
                </button>
                <button
                  type="button"
                  className={styles.arrow}
                  aria-label={`Scroll ${shelf.title} right`}
                  onClick={() => scrollRail(shelf.id, 1)}
                >
                  ›
                </button>
              </div>
            </div>
            <div
              className={styles.rail}
              ref={(el) => {
                railRefs.current[shelf.id] = el
              }}
            >
              {shelf.items.map((item) => (
                <PosterRailCard
                  key={item.id}
                  item={item}
                  onOpen={() => onSelectItem(item)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
