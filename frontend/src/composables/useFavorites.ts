export {
  fetchFavoriteIds,
  fetchFavorites,
  toggleFavorite,
  clearFavorites,
} from '@/api/library'

export const isFavorite = (nodeId: number, ids: number[]) => ids.includes(nodeId)
