import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { AboutPage } from './pages/docs/AboutPage'
import { ContentPolicyPage } from './pages/docs/ContentPolicyPage'
import { HelpPage } from './pages/docs/HelpPage'
import { PrivacyPage } from './pages/docs/PrivacyPage'
import { TermsPage } from './pages/docs/TermsPage'
import { BrowsePage } from './pages/BrowsePage'
import { HomePage } from './pages/HomePage'
import { WatchPage } from './pages/WatchPage'

function App() {
  return (
    <Layout>
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
    </Layout>
  )
}

export default App
