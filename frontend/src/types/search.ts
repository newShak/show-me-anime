import type { NodeItem } from '@/types/node'

export type TagSearchMode = 'and' | 'or'

export const TAG_SEARCH_MODE_OPTIONS = [
  { label: '或', value: 'or' as const },
  { label: '且', value: 'and' as const },
]

export const parseTagSearchMode = (raw: unknown): TagSearchMode =>
  raw === 'and' ? 'and' : 'or'

export type SearchResponse = {
  q: string
  tag_ids: number[]
  tag_mode: TagSearchMode
  total: number
  items: NodeItem[]
}
