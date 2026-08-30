import styles from './FeedbackState.module.css'

type Props = {
  title: string
  message?: string
  onRetry?: () => void
  retryLabel?: string
}

export function FeedbackState({
  title,
  message,
  onRetry,
  retryLabel = 'Try again',
}: Props) {
  return (
    <div className={styles.wrap} role="status">
      <p className={styles.title}>{title}</p>
      {message ? <p className={styles.message}>{message}</p> : null}
      {onRetry ? (
        <button type="button" className={styles.retry} onClick={onRetry}>
          {retryLabel}
        </button>
      ) : null}
    </div>
  )
}
