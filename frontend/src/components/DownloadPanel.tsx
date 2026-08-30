import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import {
  ApiError,
  cancelDownload,
  createDownload,
  fetchDownload,
  fetchDownloadFile,
} from '../lib/api'
import type { StreamResponse } from '../types/api'
import styles from './DownloadPanel.module.css'

type Props = {
  contentId: string
  contentType: string
  seasonId?: string | null
  title: string
  refTitle?: string
  stream?: StreamResponse
  ffmpeg?: string
}

export function DownloadPanel({
  contentId,
  contentType,
  seasonId,
  title,
  refTitle,
  stream,
  ffmpeg,
}: Props) {
  const [jobId, setJobId] = useState<string | null>(null)
  const [language, setLanguage] = useState(stream?.languages[0]?.id ?? '')
  const [localError, setLocalError] = useState<string | null>(null)

  useEffect(() => {
    if (!language && stream?.languages[0]?.id) {
      setLanguage(stream.languages[0].id)
    }
  }, [language, stream])

  const jobQuery = useQuery({
    queryKey: ['download', jobId],
    queryFn: async () => {
      if (!jobId) throw new Error('Missing download job')
      return fetchDownload(jobId)
    },
    enabled: Boolean(jobId),
    refetchInterval: (q) => {
      const status = q.state.data?.status
      return status === 'queued' || status === 'downloading' ? 1000 : false
    },
  })

  const startMut = useMutation({
    mutationFn: async () =>
      createDownload({
        content_id: contentId,
        type: contentType,
        season_id: seasonId,
        language: language || undefined,
        ref_title: refTitle,
        title,
      }),
    onSuccess: (job) => {
      setLocalError(null)
      setJobId(job.job_id)
    },
    onError: (err: unknown) => {
      setLocalError(err instanceof ApiError ? err.message : 'Could not start download.')
    },
  })

  const cancelMut = useMutation({
    mutationFn: async () => {
      if (!jobId) throw new Error('Missing download job')
      return cancelDownload(jobId)
    },
  })

  const saveMut = useMutation({
    mutationFn: async () => {
      if (!jobId) throw new Error('Missing download job')
      const blob = await fetchDownloadFile(jobId)
      const name = jobQuery.data?.filename || 'download.mp4'
      const href = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = href
      a.download = name
      a.click()
      URL.revokeObjectURL(href)
    },
  })

  const job = jobQuery.data
  const busy = job?.status === 'queued' || job?.status === 'downloading'
  const drm = Boolean(stream?.drm)
  const ffmpegReady = ffmpeg !== 'unavailable'
  const pct = job ? Math.round(job.progress) : 0
  const statusLabel =
    job?.status === 'queued'
      ? 'Queued'
      : job?.status === 'downloading'
        ? 'Downloading…'
        : job?.status === 'completed'
          ? 'Downloaded'
          : job?.status === 'cancelled'
            ? 'Cancelled'
            : job?.status === 'failed'
              ? 'Failed'
              : job?.status

  return (
    <section className={styles.panel} aria-label="Download">
      {stream?.languages.length ? (
        <div className={styles.block}>
          <h2 className={styles.heading}>Audio</h2>
          <label className={styles.lang}>
            <span className={styles.langLabel}>Language for download</span>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              disabled={busy}
            >
              {stream.languages.map((lang) => (
                <option key={lang.id} value={lang.id}>
                  {lang.name || lang.id}
                </option>
              ))}
            </select>
          </label>
        </div>
      ) : null}

      <div className={styles.block}>
        <h2 className={styles.heading}>Download</h2>
        <div className={styles.row}>
          <button
            type="button"
            className={styles.btn}
            disabled={drm || !ffmpegReady || busy || startMut.isPending}
            onClick={() => startMut.mutate()}
          >
            Download episode
          </button>
          {busy ? (
            <button
              type="button"
              className={styles.btnGhost}
              onClick={() => cancelMut.mutate()}
              disabled={cancelMut.isPending}
            >
              Cancel
            </button>
          ) : null}
          {job?.file_available ? (
            <button
              type="button"
              className={styles.btnGhost}
              onClick={() => saveMut.mutate()}
              disabled={saveMut.isPending}
            >
              Save
            </button>
          ) : null}
        </div>
      </div>

      {drm ? <p className={styles.warn}>This content is protected and cannot be downloaded.</p> : null}
      {!ffmpegReady ? (
        <p className={styles.warn} role="status">
          Status: FFmpeg is not available on this device.
        </p>
      ) : null}
      {job && busy ? (
        <div className={styles.progressBlock} role="status">
          <p className={styles.status}>
            {statusLabel} · {pct}%
          </p>
          <div className={styles.track} aria-hidden>
            <div className={styles.fill} style={{ width: `${Math.min(100, pct)}%` }} />
          </div>
        </div>
      ) : null}
      {job && !busy ? (
        <p className={styles.status} role="status">
          {statusLabel}
          {job.filename ? ` · ${job.filename}` : ''}
          {job.error ? ` · ${job.error}` : ''}
        </p>
      ) : null}
      {localError ? (
        <p className={styles.warn} role="alert">
          {localError}
        </p>
      ) : null}
    </section>
  )
}
