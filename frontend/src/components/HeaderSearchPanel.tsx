import { useMutation, useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { extractBrowser, resolveUrl, searchMx } from '../lib/api'
import type { ContentItem } from '../types/api'
import styles from './HeaderSearchPanel.module.css'

type Props = {
  onClose: () => void
}

function browseUrl(item: ContentItem): string {
  const t = item.type || 'tvshow'
  const q = new URLSearchParams({ type: t })
  if (item.title?.trim()) q.set('ref_title', item.title.trim())
  return `/browse/${encodeURIComponent(item.id)}?${q}`
}

export function HeaderSearchPanel({ onClose }: Props) {
  const navigate = useNavigate()
  const searchInputRef = useRef<HTMLInputElement>(null)
  const [q, setQ] = useState('')
  const [urlInput, setUrlInput] = useState('')

  const searchQuery = useQuery({
    queryKey: ['search', q],
    queryFn: () => searchMx(q),
    enabled: q.length >= 2,
  })

  const resolveMut = useMutation({
    mutationFn: (url: string) => resolveUrl(url),
    onSuccess: (data) => {
      if (data.item?.id) {
        const t = data.item.type || 'tvshow'
        const params = new URLSearchParams({ type: t })
        if (data.item.title?.trim()) params.set('ref_title', data.item.title.trim())
        void navigate(`/browse/${encodeURIComponent(data.item.id)}?${params}`)
        onClose()
        return
      }
      if (data.episodes?.length && data.type === 'season') {
        const first = data.episodes[0]
        const showId = (first as { container?: { container?: { id?: string } } })
          .container?.container?.id
        if (showId) {
          void navigate(`/browse/${showId}?type=tvshow`)
          onClose()
          return
        }
      }
      alert('Could not navigate from this URL — open API response in Network tab.')
    },
  })

  const extractMut = useMutation({
    mutationFn: (url: string) => extractBrowser(url),
    onSuccess: (data) => {
      if (data.item?.id) {
        const t = data.item.type || 'tvshow'
        const params = new URLSearchParams({ type: t })
        if (data.item.title?.trim()) params.set('ref_title', data.item.title.trim())
        void navigate(`/browse/${encodeURIComponent(data.item.id)}?${params}`)
        onClose()
        return
      }
      if (data.direct_stream_url) {
        void navigate('/player', {
          state: {
            streamUrl: data.direct_stream_url,
            title: data.item?.title ?? 'Video',
          },
        })
        onClose()
        return
      }
      alert('Extract finished but no navigation target — check response.')
    },
  })

  const submitSearch = useCallback((e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    setQ(String(fd.get('q') ?? '').trim())
  }, [])

  const goItem = useCallback(
    (item: ContentItem) => {
      void navigate(browseUrl(item))
      onClose()
    },
    [navigate, onClose],
  )

  useEffect(() => {
    const t = window.setTimeout(() => searchInputRef.current?.focus(), 50)
    return () => window.clearTimeout(t)
  }, [])

  return (
    <div className={styles.panel} id="header-search-panel" role="region" aria-label="Search and open link">
      <div className={styles.inner}>
        <div className={styles.headRow}>
          <div>
            <h2 className={styles.panelTitle}>Search catalog</h2>
            <p className={styles.panelHint}>
              Find by title, or paste an MX Player link below.
            </p>
          </div>
          <button type="button" className={styles.closeBtn} onClick={onClose}>
            Close
          </button>
        </div>

        <form className={styles.form} onSubmit={submitSearch} role="search">
          <label htmlFor="header-search-q" className="visuallyHidden">
            Search query
          </label>
          <input
            ref={searchInputRef}
            id="header-search-q"
            name="q"
            className={styles.input}
            placeholder="Title, show, movie…"
            defaultValue=""
            autoComplete="off"
          />
          <button type="submit" className={styles.submit}>
            Search
          </button>
        </form>

        {searchQuery.isFetching && (
          <div className={styles.loadingRow} aria-live="polite">
            <span className={styles.shimmer} />
            <span className={styles.loadingMuted}>Searching catalog…</span>
          </div>
        )}
        {searchQuery.isError && (
          <p className={styles.error} role="alert">
            {String(searchQuery.error)}
          </p>
        )}

        {searchQuery.data?.items && searchQuery.data.items.length > 0 && (
          <div className={styles.resultsWrap}>
            <div className={styles.resultsHead}>
              <h3 className={styles.h2}>Results</h3>
              <span className={styles.count}>
                {searchQuery.data.items.length} title
                {searchQuery.data.items.length === 1 ? '' : 's'}
              </span>
            </div>
            <ul className={styles.grid}>
              {searchQuery.data.items.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className={styles.cardBtn}
                    onClick={() => goItem(item)}
                  >
                    {item.image ? (
                      <img
                        src={item.image}
                        alt=""
                        className={styles.thumb}
                        loading="lazy"
                        decoding="async"
                      />
                    ) : (
                      <div className={styles.thumbPlaceholder}>No poster</div>
                    )}
                    <span className={styles.cardTitle}>{item.title}</span>
                    <span className={styles.badge}>{item.type || 'content'}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className={styles.linkBlock}>
          <h3 className={styles.linkTitle}>Open from link</h3>
          <p className={styles.muted}>
            Paste an <code>mxplayer.in</code> URL — load via API or extract in the browser if
            the API cannot resolve it.
          </p>
          <div className={styles.urlRow}>
            <input
              className={styles.input}
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://www.mxplayer.in/..."
              aria-label="MX Player page URL"
              autoComplete="url"
            />
            <button
              type="button"
              className={styles.secondary}
              disabled={resolveMut.isPending}
              onClick={() => {
                if (!urlInput.includes('mxplayer.in')) {
                  alert('Enter a valid MX Player URL.')
                  return
                }
                resolveMut.mutate(urlInput)
              }}
            >
              {resolveMut.isPending ? '…' : 'Load via API'}
            </button>
            <button
              type="button"
              className={styles.secondary}
              disabled={extractMut.isPending}
              onClick={() => {
                if (!urlInput.includes('mxplayer.in')) {
                  alert('Enter a valid MX Player URL.')
                  return
                }
                extractMut.mutate(urlInput)
              }}
            >
              {extractMut.isPending ? 'Extracting…' : 'Extract via browser'}
            </button>
          </div>
          {(resolveMut.isError || extractMut.isError) && (
            <p className={styles.error}>
              {String(resolveMut.error || extractMut.error)}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
