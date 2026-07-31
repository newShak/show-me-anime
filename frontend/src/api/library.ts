import { http } from './http'
import type { NodeItem } from '@/types/node'

export type FavoriteToggleResult = { node_id: number; favorited: boolean }
export type FavoritesPage = { total: number; items: NodeItem[] }

export const fetchRecentViewed = (limit?: number) =>
  http.get<NodeItem[]>('/library/recent', { params: limit != null ? { limit } : {} })

const recentTouchAt = new Map<number, number>()
const RECENT_TOUCH_MS = 3000

export const touchRecentView = (nodeId: number) => {
  const now = Date.now()
  const last = recentTouchAt.get(nodeId)
  if (last != null && now - last < RECENT_TOUCH_MS) return
  recentTouchAt.set(nodeId, now)
  http.post(`/library/recent/${nodeId}`).catch(() => {})
}

export const clearRecentViews = () => http.delete('/library/recent')

export const fetchFavoriteIds = () => http.get<number[]>('/library/favorites/ids')

export const fetchFavorites = (offset = 0, limit = 20) =>
  http.get<FavoritesPage>('/library/favorites', { params: { offset, limit } })

export const toggleFavorite = (nodeId: number) =>
  http.post<FavoriteToggleResult>(`/library/favorites/${nodeId}`)

export const clearFavorites = () => http.delete('/library/favorites')
