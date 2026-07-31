import type { TagSearchMode } from '@/types/search'
import { parseTagSearchMode } from '@/types/search'

export type SearchHistoryItem = {
  q: string
  tagIds: number[]
  tagMode?: TagSearchMode
  at: number
}

const HISTORY_KEY = 'search-history'
const LIMIT_KEY = 'search-history-limit'
export const DEFAULT_SEARCH_HISTORY_LIMIT = 10
const MIN_LIMIT = 1
const MAX_LIMIT = 50

const itemKey = (q: string, tagIds: number[], tagMode: TagSearchMode = 'or') =>
  `${q.trim()}|${[...tagIds].sort((a, b) => a - b).join(',')}|${tagMode}`

const readLimit = () => {
  const raw = Number(localStorage.getItem(LIMIT_KEY))
  if (!Number.isInteger(raw) || raw < MIN_LIMIT || raw > MAX_LIMIT) return DEFAULT_SEARCH_HISTORY_LIMIT
  return raw
}

const readHistory = (): SearchHistoryItem[] => {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (!raw) return []
    const list = JSON.parse(raw) as SearchHistoryItem[]
    return Array.isArray(list)
      ? list.filter(
          (item) =>
            item &&
            typeof item.q === 'string' &&
            Array.isArray(item.tagIds) &&
            item.tagIds.every((id) => Number.isInteger(id)),
        )
      : []
  } catch {
    return []
  }
}

const writeHistory = (items: SearchHistoryItem[]) => {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(items))
}

export const getSearchHistoryLimit = () => readLimit()

export const setSearchHistoryLimit = (limit: number) => {
  const next = Math.min(MAX_LIMIT, Math.max(MIN_LIMIT, Math.round(limit)))
  localStorage.setItem(LIMIT_KEY, String(next))
  const trimmed = readHistory().slice(0, next)
  writeHistory(trimmed)
  return next
}

export const getSearchHistory = () => readHistory().sort((a, b) => b.at - a.at)

export const addSearchHistory = (q: string, tagIds: number[], tagMode: TagSearchMode = 'or') => {
  const text = q.trim()
  if (!text && !tagIds.length) return
  const mode = tagIds.length > 1 ? tagMode : 'or'
  const key = itemKey(text, tagIds, mode)
  const limit = readLimit()
  const next: SearchHistoryItem = { q: text, tagIds: [...tagIds], tagMode: mode, at: Date.now() }
  const items = readHistory().filter(
    (item) => itemKey(item.q, item.tagIds, parseTagSearchMode(item.tagMode)) !== key,
  )
  items.unshift(next)
  writeHistory(items.slice(0, limit))
}

export const removeSearchHistory = (item: SearchHistoryItem) => {
  const mode = parseTagSearchMode(item.tagMode)
  const key = itemKey(item.q, item.tagIds, mode)
  writeHistory(
    readHistory().filter(
      (row) => itemKey(row.q, row.tagIds, parseTagSearchMode(row.tagMode)) !== key,
    ),
  )
}

export const clearSearchHistory = () => {
  localStorage.removeItem(HISTORY_KEY)
}

export const formatHistoryLabel = (
  item: SearchHistoryItem,
  tagNameOf: (id: number) => string | undefined,
) => {
  const parts: string[] = []
  if (item.q) parts.push(item.q)
  if (item.tagIds.length) {
    const mode = parseTagSearchMode(item.tagMode)
    const joiner = item.tagIds.length > 1 && mode === 'and' ? ' & ' : ' / '
    const names = item.tagIds.map((id) => tagNameOf(id) ?? `#${id}`)
    parts.push(`标签: ${names.join(joiner)}`)
  }
  return parts.join(' · ')
}

export const filterHistory = (keyword: string) => {
  const q = keyword.trim().toLowerCase()
  return getSearchHistory().filter((item) => {
    if (!q) return true
    if (item.q.toLowerCase().includes(q)) return true
    return false
  })
}

export const SEARCH_HISTORY_LIMIT_RANGE = { min: MIN_LIMIT, max: MAX_LIMIT }
