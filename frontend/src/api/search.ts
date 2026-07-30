import { http } from './http'
import type { SearchResponse } from '@/types/search'

export const searchNodes = (q: string, limit = 20, offset = 0) =>
  http.get<SearchResponse>('/search', { params: { q, limit, offset } })
