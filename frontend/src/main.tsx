import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { AuthGate } from './providers/AuthGate.tsx'
import { QueryProvider } from './providers/QueryProvider.tsx'

/* StrictMode is intentionally omitted: React 18 double-mounting can run Auth0's
   redirect handler twice and invalidate the one-time OAuth code, leaving the user
   stuck logged out. */

createRoot(document.getElementById('root')!).render(
  <QueryProvider>
    <AuthGate>
      <App />
    </AuthGate>
  </QueryProvider>,
)
