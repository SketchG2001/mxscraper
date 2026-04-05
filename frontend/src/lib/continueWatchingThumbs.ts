import { fetchContent, fetchEpisodes } from './api'
import type { ContinueWatchingItem } from './watchProgress'

/** Resolve a 16×9 still for the Continue watching rail when ``poster`` was never saved. */
export async function resolveContinueWatchingThumb(
  it: ContinueWatchingItem,
): Promise<string | null> {
  if (it.poster?.trim()) return it.poster.trim()
  try {
    if (it.type === 'episode' && it.seasonId) {
      const { episodes } = await fetchEpisodes(it.seasonId)
      const ep = episodes.find((e) => e.id === it.contentId)
      return ep?.image?.trim() || null
    }
    const res = await fetchContent(
      it.contentId,
      it.type || 'movie',
      it.title?.trim() || undefined,
    )
    return res.item?.image?.trim() || null
  } catch {
    return null
  }
}
