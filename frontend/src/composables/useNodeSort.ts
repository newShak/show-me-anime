export type NodeSortBy = 'name' | 'mtime'
export type SortOrder = 'asc' | 'desc'
export type NodeSort = { sortBy: NodeSortBy; sortOrder: SortOrder }

const SORT_KEY = 'gallery-sort'
const DEFAULT: NodeSort = { sortBy: 'name', sortOrder: 'asc' }

export const SORT_OPTIONS = [
  { label: '名称升序', value: 'name:asc' },
  { label: '名称降序', value: 'name:desc' },
  { label: '时间升序', value: 'mtime:asc' },
  { label: '时间降序', value: 'mtime:desc' },
] as const

/** 解析 sort 字符串为排序参数 */
export const parseSortValue = (value: string): NodeSort => {
  const [sortBy, sortOrder] = value.split(':') as [NodeSortBy, SortOrder]
  return { sortBy, sortOrder }
}

/** 读取本地保存的排序偏好 */
export const getStoredSort = (): NodeSort => {
  const raw = localStorage.getItem(SORT_KEY)
  if (!raw || !SORT_OPTIONS.some((o) => o.value === raw)) return DEFAULT
  return parseSortValue(raw)
}

/** 保存排序偏好 */
export const saveSort = (sort: NodeSort) => {
  localStorage.setItem(SORT_KEY, `${sort.sortBy}:${sort.sortOrder}`)
}
