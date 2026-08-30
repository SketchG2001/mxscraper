import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Layout } from './components/Layout'
import { AboutPage } from './pages/docs/AboutPage'
import { ContentPolicyPage } from './pages/docs/ContentPolicyPage'
import { HelpPage } from './pages/docs/HelpPage'
import { PrivacyPage } from './pages/docs/PrivacyPage'
import { TermsPage } from './pages/docs/TermsPage'
import { BrowsePage } from './pages/BrowsePage'
import { HomePage } from './pages/HomePage'
import { WatchPage } from './pages/WatchPage'
import { fetchHealth, waitForHealth } from './lib/api'
import { isAndroidNative } from './lib/apiBase'

type LocalApiState = 'skip' | 'wait' | 'ready' | 'fail'

function useAndroidLocalApi(): LocalApiState {
  const [state, setState] = useState<LocalApiState>(() =>
    isAndroidNative() ? 'wait' : 'skip',
  )
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!isAndroidNative()) return
    let cancelled = false

    const run = async () => {
      try {
        await waitForHealth(30_000, 250)
        if (cancelled) return
        setState('ready')
      } catch (err: unknown) {
        if (cancelled) return
        console.error('[mx] local FastAPI /health failed', err)
        setState('fail')
        while (!cancelled) {
          await new Promise((r) => setTimeout(r, 2000))
          if (cancelled) return
          try {
            const health = await fetchHealth()
            if (health.status === 'ok') {
              setState('ready')
              void queryClient.invalidateQueries()
              return
            }
          } catch {
            /* still starting */
          }
        }
      }
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [queryClient])

  return state
}

function App() {
  const localApi = useAndroidLocalApi()
  return (
    <Layout
      localApiWaiting={localApi === 'wait'}
      localApiFailed={
        localApi === 'fail'
          ? 'Local API is not ready yet. Retrying… Catalog and playback will work once FastAPI is reachable on this device.'
          : null
      }
    >
      {localApi === 'wait' ? null : (
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/browse/:contentId" element={<BrowsePage />} />
        <Route path="/watch/:contentId" element={<WatchPage />} />
        <Route path="/player" element={<WatchPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/content-policy" element={<ContentPolicyPage />} />
        <Route path="/help" element={<HelpPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      )}
    </Layout>
  )
}

export default App
