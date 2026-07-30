import { http } from './http'
import type { SearchResponse } from '@/types/search'

export type SearchParams = {
  q?: string
  tagIds?: number[]
  limit?: number
  offset?: number
}

export const searchNodes = ({ q, tagIds, limit = 20, offset = 0 }: SearchParams) =>
  http.get<SearchResponse>('/search', {
    params: {
      ...(q ? { q } : {}),
      ...(tagIds?.length ? { tags: tagIds.join(',') } : {}),
      limit,
      offset,
    },
  })
