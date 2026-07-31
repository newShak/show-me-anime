export type RecentAddedRange = 'today' | 'week' | 'month'

export const RECENT_ADDED_RANGE_OPTIONS: { label: string; value: RecentAddedRange }[] = [
  { label: '今天', value: 'today' },
  { label: '最近一周', value: 'week' },
  { label: '最近一月', value: 'month' },
]

const startOfLocalDay = (d = new Date()) => {
  const x = new Date(d)
  x.setHours(0, 0, 0, 0)
  return x
}

/** 返回 unix 秒：范围起点（含）与当前时刻（含） */
export const recentAddedRangeBounds = (range: RecentAddedRange) => {
  const until = Date.now() / 1000
  const start = startOfLocalDay()
  if (range === 'week') start.setDate(start.getDate() - 6)
  else if (range === 'month') start.setDate(start.getDate() - 29)
  return { since: start.getTime() / 1000, until }
}

export const recentAddedDayKey = (createdAt: number) => {
  const d = new Date(createdAt * 1000)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export const recentAddedDayLabel = (dayKey: string) => {
  const today = recentAddedDayKey(Date.now() / 1000)
  const y = new Date()
  y.setDate(y.getDate() - 1)
  const yesterday = recentAddedDayKey(y.getTime() / 1000)
  if (dayKey === today) return '今天'
  if (dayKey === yesterday) return '昨天'
  const [yy, mm, dd] = dayKey.split('-').map(Number)
  return `${yy}年${mm}月${dd}日`
}

export const recentAddedDayBounds = (dayKey: string) => {
  const [y, m, d] = dayKey.split('-').map(Number)
  const start = new Date(y, m - 1, d, 0, 0, 0, 0)
  const end = new Date(y, m - 1, d, 23, 59, 59, 999)
  return { since: start.getTime() / 1000, until: end.getTime() / 1000 }
}
