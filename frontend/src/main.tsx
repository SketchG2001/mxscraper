import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { isAndroidNative } from './lib/apiBase.ts'
import { AuthGate } from './providers/AuthGate.tsx'
import { QueryProvider } from './providers/QueryProvider.tsx'

if (isAndroidNative()) {
  document.documentElement.classList.add('mx-android')
}

/* StrictMode omitted — matches the previous production mount. */
createRoot(document.getElementById('root')!).render(
  <QueryProvider>
    <AuthGate>
      <App />
    </AuthGate>
  </QueryProvider>,
)
