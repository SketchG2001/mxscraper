import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { fetchBanners, fetchHomeShelves } from '../lib/api'
import { ContinueWatching } from '../components/ContinueWatching'
import { HomeShelves } from '../components/HomeShelves'
import { MxPlayerBanners } from '../components/MxPlayerBanners'
import { usePageMeta } from '../hooks/usePageMeta'
import type { ContentItem } from '../types/api'
import styles from './HomePage.module.css'

export function HomePage() {
  usePageMeta(
    'Search MX Player',
    'Search movies and TV shows on MX Player. Use Search in the header to find titles or paste a link.',
  )
  const navigate = useNavigate()

  const bannersQuery = useQuery({
    queryKey: ['banners'],
    queryFn: () => fetchBanners(12),
    staleTime: 30 * 60 * 1000,
  })

  const shelvesQuery = useQuery({
    queryKey: ['homeShelves'],
    queryFn: () => fetchHomeShelves(14),
    staleTime: 20 * 60 * 1000,
  })

  const goItem = (item: ContentItem) => {
    const t = item.type || 'tvshow'
    const q = new URLSearchParams({ type: t })
    if (item.title?.trim()) q.set('ref_title', item.title.trim())
    void navigate(`/browse/${encodeURIComponent(item.id)}?${q}`)
  }

  const bannerItems = bannersQuery.data?.items ?? []
  const showFallbackHero =
    bannerItems.length === 0 && !bannersQuery.isPending

  return (
    <div className={styles.page}>
      <div className={styles.heroShell}>
        <MxPlayerBanners
          items={bannerItems}
          fetchError={
            bannersQuery.isError
              ? bannersQuery.error instanceof Error
                ? bannersQuery.error.message
                : String(bannersQuery.error)
              : (bannersQuery.data?.error ?? null)
          }
        >
          {bannersQuery.isPending && bannerItems.length === 0 ? (
            <div className={styles.heroInner} aria-busy="true">
              <p className={styles.heroLoading}>Loading featured titles…</p>
            </div>
          ) : showFallbackHero ? (
            <div className={styles.heroInner}>
              <p className={styles.kicker}>Discover · Stream · Enjoy</p>
              <h1 className={styles.h1}>Find your next watch</h1>
              <p className={styles.lead}>
                Use <strong>Search</strong> in the header to find titles or open an{' '}
                <code>mxplayer.in</code> link — then browse the catalog below. Sign in to
                play when your API is configured.
              </p>
            </div>
          ) : null}
        </MxPlayerBanners>
      </div>

      <section id="catalog" aria-label="Catalog" className={styles.catalog}>
        <ContinueWatching />

        <HomeShelves
          shelves={shelvesQuery.data?.shelves ?? []}
          loading={shelvesQuery.isPending}
          error={
            shelvesQuery.isError
              ? shelvesQuery.error instanceof Error
                ? shelvesQuery.error.message
                : String(shelvesQuery.error)
              : (shelvesQuery.data?.error ?? null)
          }
          onSelectItem={(item) =>
            goItem({
              id: item.id,
              title: item.title,
              type: item.type,
              image: item.image,
            })
          }
        />
      </section>
    </div>
  )
}
