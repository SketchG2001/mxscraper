import { useMutation, useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { extractBrowser, resolveUrl, searchMx } from '../lib/api'
import { isAndroidNative } from '../lib/apiBase'
import type { ContentItem } from '../types/api'
import { FeedbackState } from './FeedbackState'
import styles from './HeaderSearchPanel.module.css'

type Props = {
  onClose: () => void
  fullscreen?: boolean
}

function browseUrl(item: ContentItem): string {
  const t = item.type || 'tvshow'
  const q = new URLSearchParams({ type: t })
  if (item.title?.trim()) q.set('ref_title', item.title.trim())
  return `/browse/${encodeURIComponent(item.id)}?${q}`
}

export function HeaderSearchPanel({ onClose, fullscreen = false }: Props) {
  const navigate = useNavigate()
  const searchInputRef = useRef<HTMLInputElement>(null)
  const [draft, setDraft] = useState('')
  const [q, setQ] = useState('')
  const [urlInput, setUrlInput] = useState('')
  const [linkError, setLinkError] = useState<string | null>(null)
  const android = isAndroidNative()

  useEffect(() => {
    const t = window.setTimeout(() => setQ(draft.trim()), 300)
    return () => window.clearTimeout(t)
  }, [draft])

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
      setLinkError('Could not open that link.')
    },
    onError: (err: unknown) => {
      setLinkError(err instanceof Error ? err.message : 'Could not open that link.')
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
      setLinkError('Extract finished but nothing to open.')
    },
    onError: (err: unknown) => {
      setLinkError(err instanceof Error ? err.message : 'Extract failed.')
    },
  })

  const submitSearch = useCallback((e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setQ(draft.trim())
  }, [draft])

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

  const items = searchQuery.data?.items ?? []
  const empty =
    q.length >= 2 &&
    !searchQuery.isFetching &&
    !searchQuery.isError &&
    items.length === 0

  return (
    <div
      className={`${styles.panel} ${fullscreen ? styles.panelFullscreen : ''}`}
      id="header-search-panel"
      role="region"
      aria-label="Search"
    >
      <div className={styles.inner}>
        <div className={styles.headRow}>
          {fullscreen ? (
            <button
              type="button"
              className={styles.iconClose}
              onClick={onClose}
              aria-label="Back"
            >
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" aria-hidden>
                <path
                  d="M15 5l-7 7 7 7"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          ) : (
            <div>
              <h2 className={styles.panelTitle}>Search catalog</h2>
              <p className={styles.panelHint}>
                Find by title, or paste an MX Player link below.
              </p>
            </div>
          )}
          {fullscreen ? (
            <h2 className={styles.panelTitle}>Search</h2>
          ) : (
            <button type="button" className={styles.closeBtn} onClick={onClose}>
              Close
            </button>
          )}
        </div>

        <form className={styles.form} onSubmit={submitSearch} role="search">
          <label htmlFor="header-search-q" className="visuallyHidden">
            Search query
          </label>
          <div className={styles.fieldWrap}>
            <input
              ref={searchInputRef}
              id="header-search-q"
              name="q"
              className={styles.input}
              placeholder="Title, show, movie…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              autoComplete="off"
              enterKeyHint="search"
              inputMode="search"
            />
            {draft ? (
              <button
                type="button"
                className={styles.clearBtn}
                aria-label="Clear search"
                onClick={() => {
                  setDraft('')
                  setQ('')
                  searchInputRef.current?.focus()
                }}
              >
                ×
              </button>
            ) : null}
          </div>
          {!fullscreen ? (
            <button type="submit" className={styles.submit}>
              Search
            </button>
          ) : null}
        </form>

        {searchQuery.isFetching && (
          <div className={styles.resultsSkel} aria-busy="true" aria-label="Searching">
            <div className={styles.skelRow} />
            <div className={styles.skelRow} />
            <div className={styles.skelRow} />
          </div>
        )}
        {searchQuery.isError && (
          <FeedbackState
            title="Something went wrong"
            message="We couldn't search the catalog."
            onRetry={() => void searchQuery.refetch()}
          />
        )}
        {empty ? (
          <FeedbackState
            title="No results"
            message={`Nothing matched “${q}”.`}
          />
        ) : null}

        {items.length > 0 && (
          <div className={styles.resultsWrap}>
            <div className={styles.resultsHead}>
              <h3 className={styles.h2}>Results</h3>
              <span className={styles.count}>
                {items.length} title{items.length === 1 ? '' : 's'}
              </span>
            </div>
            <ul className={fullscreen ? styles.list : styles.grid}>
              {items.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className={fullscreen ? styles.rowBtn : styles.cardBtn}
                    onClick={() => goItem(item)}
                  >
                    {item.image ? (
                      <img
                        src={item.image}
                        alt=""
                        className={fullscreen ? styles.rowThumb : styles.thumb}
                        loading="lazy"
                        decoding="async"
                      />
                    ) : (
                      <div
                        className={
                          fullscreen ? styles.rowThumbPh : styles.thumbPlaceholder
                        }
                      >
                        {fullscreen ? '' : 'No poster'}
                      </div>
                    )}
                    <span className={fullscreen ? styles.rowMeta : undefined}>
                      <span className={styles.cardTitle}>{item.title}</span>
                      <span className={styles.badge}>{item.type || 'content'}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {!android ? (
          <div className={styles.linkBlock}>
            <h3 className={styles.linkTitle}>Open from link</h3>
            <p className={styles.muted}>
              Paste an <code>mxplayer.in</code> URL — load via API or extract in the
              browser if the API cannot resolve it.
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
                  setLinkError(null)
                  if (!urlInput.includes('mxplayer.in')) {
                    setLinkError('Enter a valid MX Player URL.')
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
                  setLinkError(null)
                  if (!urlInput.includes('mxplayer.in')) {
                    setLinkError('Enter a valid MX Player URL.')
                    return
                  }
                  extractMut.mutate(urlInput)
                }}
              >
                {extractMut.isPending ? 'Extracting…' : 'Extract via browser'}
              </button>
            </div>
            {linkError ? (
              <p className={styles.error} role="alert">
                {linkError}
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  )
}
