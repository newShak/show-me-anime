import { http } from './http'
import type { NodeItem } from '@/types/node'

export type FavoriteToggleResult = { node_id: number; favorited: boolean }
export type FavoritesPage = { total: number; items: NodeItem[] }

export const fetchRecentViewed = (limit?: number) =>
  http.get<NodeItem[]>('/library/recent', { params: limit != null ? { limit } : {} })

export const touchRecentView = (nodeId: number) =>
  http.post(`/library/recent/${nodeId}`).catch(() => {})

export const clearRecentViews = () => http.delete('/library/recent')

export const fetchFavoriteIds = () => http.get<number[]>('/library/favorites/ids')

export const fetchFavorites = (offset = 0, limit = 20) =>
  http.get<FavoritesPage>('/library/favorites', { params: { offset, limit } })

export const toggleFavorite = (nodeId: number) =>
  http.post<FavoriteToggleResult>(`/library/favorites/${nodeId}`)

export const clearFavorites = () => http.delete('/library/favorites')
