import { ref } from 'vue'
import { fetchNodesProgress } from '@/api/nodes'
import { fetchFavoriteIds } from '@/api/library'
import { fetchNodesTags } from '@/api/tags'
import type { NodeItem } from '@/types/node'
import type { TagItem } from '@/types/tag'

export const useNodeGridMeta = () => {
  const nodeTagsMap = ref<Record<number, TagItem[]>>({})
  const progressPercentMap = ref<Record<number, number>>({})
  const favoriteIds = ref<number[]>([])

  const loadFavoriteIds = async () => {
    favoriteIds.value = (await fetchFavoriteIds()).data
  }

  const loadMeta = async (nodes: NodeItem[]) => {
    const ids = nodes.map((n) => n.id)
    if (!ids.length) return
    const albums = nodes.filter((n) => n.node_type !== 'container' && n.image_count > 0)
    const [tagsRes, progressRes] = await Promise.all([
      fetchNodesTags(ids),
      albums.length ? fetchNodesProgress(albums.map((n) => n.id)) : Promise.resolve({ data: [] }),
    ])
    const tags = { ...nodeTagsMap.value }
    for (const g of tagsRes.data) tags[g.node_id] = g.tags
    nodeTagsMap.value = tags
    const progress: Record<number, number> = { ...progressPercentMap.value }
    for (const row of progressRes.data) {
      if (row.updated_at == null) continue
      const node = albums.find((n) => n.id === row.node_id)
      if (!node) continue
      const pct = Math.min(100, Math.round(((row.page_index + 1) / node.image_count) * 100))
      if (pct > 0) progress[row.node_id] = pct
    }
    progressPercentMap.value = progress
  }

  return { nodeTagsMap, progressPercentMap, favoriteIds, loadFavoriteIds, loadMeta }
}
