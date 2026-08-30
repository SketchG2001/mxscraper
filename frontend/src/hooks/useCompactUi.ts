import { useEffect, useState } from 'react'
import { isAndroidNative } from '../lib/apiBase'

const MOBILE_MQ = '(max-width: 720px)'

/** Android native, or a narrow viewport — app-shell chrome instead of the desktop site. */
export function useCompactUi(): boolean {
  const [compact, setCompact] = useState(
    () =>
      isAndroidNative() ||
      (typeof window !== 'undefined' && window.matchMedia(MOBILE_MQ).matches),
  )

  useEffect(() => {
    if (isAndroidNative()) {
      setCompact(true)
      return
    }
    const mq = window.matchMedia(MOBILE_MQ)
    const onChange = () => setCompact(mq.matches)
    onChange()
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  return compact
}
