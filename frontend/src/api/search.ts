import { http } from './http'
import type { SearchResponse, TagSearchMode } from '@/types/search'
export type SearchParams = {
  q?: string
  tagIds?: number[]
  tagMode?: TagSearchMode
  limit?: number
  offset?: number
}

export const searchNodes = ({ q, tagIds, tagMode = 'or', limit = 20, offset = 0 }: SearchParams) =>
  http.get<SearchResponse>('/search', {
    params: {
      ...(q ? { q } : {}),
      ...(tagIds?.length ? { tags: tagIds.join(','), tag_mode: tagMode } : {}),
      limit,
      offset,
    },
  })
