import type { ImageItem, NodeItem } from '@/types/node'
import type { NodeSort } from '@/composables/useNodeSort'

export type BrowseViewSnapshot = {
  nodes: NodeItem[]
  images: ImageItem[]
  currentNode: NodeItem | null
  scrollY: number
  sort: NodeSort
}

const MAX_ENTRIES = 12
const store = new Map<string, BrowseViewSnapshot>()
const order: string[] = []

const cacheKey = (nodeId: number | null, sort: NodeSort) =>
  `${nodeId ?? 'root'}:${sort.sortBy}:${sort.sortOrder}`

const touch = (key: string) => {
  const i = order.indexOf(key)
  if (i >= 0) order.splice(i, 1)
  order.push(key)
  while (order.length > MAX_ENTRIES) {
    const oldest = order.shift()
    if (oldest) store.delete(oldest)
  }
}

export const getBrowseViewCache = (
  nodeId: number | null,
  sort: NodeSort,
): BrowseViewSnapshot | null => {
  const hit = store.get(cacheKey(nodeId, sort))
  return hit ? { ...hit, nodes: [...hit.nodes], images: [...hit.images] } : null
}

export const setBrowseViewCache = (
  nodeId: number | null,
  sort: NodeSort,
  snapshot: BrowseViewSnapshot,
) => {
  const key = cacheKey(nodeId, sort)
  store.set(key, {
    nodes: [...snapshot.nodes],
    images: [...snapshot.images],
    currentNode: snapshot.currentNode ? { ...snapshot.currentNode } : null,
    scrollY: snapshot.scrollY,
    sort: { ...snapshot.sort },
  })
  touch(key)
}

export const clearBrowseViewCache = () => {
  store.clear()
  order.length = 0
}
