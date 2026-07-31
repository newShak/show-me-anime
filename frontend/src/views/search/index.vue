<template>
  <div class="search-page">
    <header class="toolbar">
      <SearchBar
        :model-value="query"
        show-history
        :tags="allTags"
        @search="onTextSearch"
        @clear="onSearchClear"
        @pick="onHistoryPick"
      />
      <TagSelect
        v-model="selectedTagIds"
        :tags="allTags"
        clearable
        collapse-tags
        placeholder="按标签筛选"
        width="220px"
        @change="onTagChange"
      />
      <el-segmented
        v-if="selectedTagIds.length > 1"
        v-model="tagMode"
        :options="TAG_SEARCH_MODE_OPTIONS"
        size="small"
        @change="onTagModeChange"
      />
      <el-button @click="$router.push('/browse')">返回顶层</el-button>
    </header>

    <main class="content">
      <section v-if="!hasFilter && historyItems.length" class="history-panel">
        <div class="history-head">
          <span>搜索历史</span>
          <el-button text size="small" @click="onClearHistory">清空</el-button>
        </div>
        <div class="history-list">
          <button
            v-for="item in historyItems"
            :key="`${item.q}|${item.tagIds.join(',')}|${item.tagMode ?? 'or'}`"
            type="button"
            class="history-item"
            @click="onHistoryPick(item)"
          >
            <span>{{ historyLabel(item) }}</span>
            <el-icon class="remove" @click.stop="onRemoveHistory(item)"><Close /></el-icon>
          </button>
        </div>
      </section>
      <p v-if="hasFilter" class="summary">{{ summaryText }} · 共 {{ total }} 个结果</p>

      <el-skeleton v-if="loading && !items.length" :rows="4" animated />

      <template v-else-if="items.length">
        <AlbumGrid
          :nodes="items"
          :node-tags="nodeTagsMap"
          :progress-map="progressPercentMap"
          :favorite-ids="favoriteIds"
          show-menu
          @open="openNode"
          @toggle-favorite="onToggleFavorite"
          @edit="openEdit"
          @add-tags="(node) => openTagPicker([node.id])"
          @move="(node) => openMovePicker([node.id])"
          @delete="onDeleteNode"
        />
        <div ref="sentinelRef" class="sentinel">
          <el-skeleton v-if="loadingMore" :rows="2" animated />
          <p v-else-if="hasMore" class="load-hint">继续下拉加载更多</p>
          <p v-else class="load-hint end">已加载全部 {{ total }} 个结果</p>
        </div>
      </template>

      <el-empty v-else-if="hasFilter" description="未找到匹配的相册" />
      <el-empty v-else description="输入关键词或选择标签搜索相册" />
    </main>

    <Transition name="fade">
      <button
        v-show="showTopBtn"
        type="button"
        class="back-top"
        aria-label="回到顶部"
        @click="scrollToTop"
      >
        ↑
      </button>
    </Transition>

    <NodeEditDialog v-model="editOpen" :node="editNode" @saved="onEditSaved" @closed="editNode = null" />

    <TagPickerDialog
      v-model="tagPickerOpen"
      :all-tags="allTags"
      :existing-tags="tagPickerExistingTags"
      :exclude-tag-ids="tagPickerExcludeIds"
      :title="tagPickerTitle"
      :submitting="tagPickerSubmitting"
      @confirm="onTagPickerConfirm"
      @remove="onTagPickerRemove"
      @tag-created="onTagCreated"
    />

    <NodeMoveDialog
      v-model="movePickerOpen"
      :title="movePickerTitle"
      :exclude-paths="moveExcludePaths"
      :submitting="moving"
      @confirm="onMoveConfirm"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Close } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import SearchBar from '@/components/SearchBar.vue'
import TagSelect from '@/components/TagSelect.vue'
import AlbumGrid from '@/components/AlbumGrid.vue'
import NodeEditDialog from '@/components/NodeEditDialog.vue'
import NodeMoveDialog from '@/components/NodeMoveDialog.vue'
import TagPickerDialog from '@/components/TagPickerDialog.vue'
import { searchNodes } from '@/api/search'
import { deleteNodes, fetchNodesProgress, moveNodes } from '@/api/nodes'
import { batchAddNodeTags, fetchNodesTags, fetchTags, removeNodeTag } from '@/api/tags'
import { fetchFavoriteIds, toggleFavorite } from '@/composables/useFavorites'
import { touchRecentView } from '@/composables/useRecentView'
import {
  addSearchHistory,
  clearSearchHistory,
  formatHistoryLabel,
  getSearchHistory,
  removeSearchHistory,
  type SearchHistoryItem,
} from '@/composables/useSearchHistory'
import type { NodeItem } from '@/types/node'
import type { TagItem } from '@/types/tag'
import { parseTagSearchMode, TAG_SEARCH_MODE_OPTIONS, type TagSearchMode } from '@/types/search'

const PAGE_SIZE = 20
const TOP_THRESHOLD = 400

const route = useRoute()
const router = useRouter()

const query = ref('')
const selectedTagIds = ref<number[]>([])
const tagMode = ref<TagSearchMode>('or')
const allTags = ref<TagItem[]>([])
const items = ref<NodeItem[]>([])
const total = ref(0)
const offset = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const nodeTagsMap = ref<Record<number, TagItem[]>>({})
const progressPercentMap = ref<Record<number, number>>({})
const sentinelRef = ref<HTMLElement | null>(null)
const showTopBtn = ref(false)
const favoriteIds = ref<number[]>([])
const historyItems = ref<SearchHistoryItem[]>(getSearchHistory())
const editOpen = ref(false)
const editNode = ref<NodeItem | null>(null)
const tagPickerOpen = ref(false)
const tagPickerNodeIds = ref<number[]>([])
const tagPickerSubmitting = ref(false)
const movePickerOpen = ref(false)
const moveNodeIds = ref<number[]>([])
const moving = ref(false)

const refreshHistory = () => {
  historyItems.value = getSearchHistory()
}

const persistHistory = () => {
  const q = query.value.trim()
  const tagIds = selectedTagIds.value
  if (!q && !tagIds.length) return
  addSearchHistory(q, tagIds, tagMode.value)
  refreshHistory()
}

const tagNameOf = (id: number) => allTags.value.find((t) => t.id === id)?.name

const historyLabel = (item: SearchHistoryItem) => formatHistoryLabel(item, tagNameOf)

const hasFilter = computed(() => !!query.value.trim() || selectedTagIds.value.length > 0)
const hasMore = computed(() => items.value.length < total.value)

const summaryText = computed(() => {
  const parts: string[] = []
  if (query.value.trim()) parts.push(`关键词「${query.value.trim()}」`)
  if (selectedTagIds.value.length) {
    const names = allTags.value
      .filter((t) => selectedTagIds.value.includes(t.id))
      .map((t) => t.name)
    const joiner = selectedTagIds.value.length > 1 && tagMode.value === 'and' ? ' 且 ' : ' / '
    parts.push(`标签${selectedTagIds.value.length > 1 && tagMode.value === 'and' ? '（全部）' : ''}「${names.join(joiner)}」`)
  }
  return parts.join('，')
})

const tagPickerTitle = computed(() =>
  tagPickerNodeIds.value.length > 1
    ? `批量标签（${tagPickerNodeIds.value.length} 项）`
    : '标签',
)

const movePickerTitle = computed(() =>
  moveNodeIds.value.length > 1 ? `移动 ${moveNodeIds.value.length} 项到` : '移动到',
)

const moveExcludePaths = computed(() =>
  items.value.filter((n) => moveNodeIds.value.includes(n.id)).map((n) => n.path),
)

const tagPickerExistingTags = computed(() => {
  const ids = tagPickerNodeIds.value
  if (!ids.length) return []
  const seen = new Map<number, TagItem>()
  for (const id of ids) {
    for (const tag of nodeTagsMap.value[id] ?? []) seen.set(tag.id, tag)
  }
  return [...seen.values()].sort((a, b) => a.name.localeCompare(b.name))
})

const tagPickerExcludeIds = computed(() => {
  const ids = tagPickerNodeIds.value
  if (!ids.length) return []
  if (ids.length === 1) return (nodeTagsMap.value[ids[0]] ?? []).map((t) => t.id)
  const tagSets = ids.map((id) => new Set((nodeTagsMap.value[id] ?? []).map((t) => t.id)))
  return [...tagSets[0]].filter((tagId) => tagSets.every((s) => s.has(tagId)))
})

const syncRoute = () => {
  const next: Record<string, string> = {}
  if (query.value.trim()) next.q = query.value.trim()
  if (selectedTagIds.value.length) {
    next.tags = selectedTagIds.value.join(',')
    if (selectedTagIds.value.length > 1 && tagMode.value === 'and') next.tag_mode = 'and'
  }
  router.replace({ path: '/search', query: next })
}

const mergeNodeTags = (nodes: NodeItem[]) => {
  const ids = nodes.map((n) => n.id)
  if (!ids.length) return
  fetchNodesTags(ids).then(({ data }) => {
    const next = { ...nodeTagsMap.value }
    for (const g of data) next[g.node_id] = g.tags
    nodeTagsMap.value = next
  })
}

const mergeProgress = (nodes: NodeItem[]) => {
  const albums = nodes.filter((n) => n.node_type !== 'container' && n.image_count > 0)
  if (!albums.length) return
  fetchNodesProgress(albums.map((n) => n.id)).then(({ data }) => {
    const next = { ...progressPercentMap.value }
    for (const row of data) {
      if (row.updated_at == null) continue
      const node = albums.find((n) => n.id === row.node_id)
      if (!node) continue
      const pct = Math.min(100, Math.round(((row.page_index + 1) / node.image_count) * 100))
      if (pct > 0) next[row.node_id] = pct
    }
    progressPercentMap.value = next
  })
}

const loadMeta = (nodes: NodeItem[]) => {
  mergeNodeTags(nodes)
  mergeProgress(nodes)
}

const runSearch = async (append = false) => {
  const q = query.value.trim()
  const tagIds = selectedTagIds.value
  if (!q && !tagIds.length) {
    items.value = []
    total.value = 0
    offset.value = 0
    nodeTagsMap.value = {}
    progressPercentMap.value = {}
    return
  }

  if (append) loadingMore.value = true
  else {
    loading.value = true
    offset.value = 0
    items.value = []
    nodeTagsMap.value = {}
    progressPercentMap.value = {}
  }

  try {
    const { data } = await searchNodes({
      q: q || undefined,
      tagIds,
      tagMode: tagMode.value,
      limit: PAGE_SIZE,
      offset: offset.value,
    })
    const batch = data.items
    items.value = append ? [...items.value, ...batch] : batch
    total.value = data.total
    offset.value = items.value.length
    loadMeta(batch)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = () => {
  if (loading.value || loadingMore.value || !hasMore.value || !hasFilter.value) return
  runSearch(true)
}

const onTextSearch = (q: string, commit?: boolean) => {
  const trimmed = q.trim()
  if (!trimmed) return
  query.value = trimmed
  syncRoute()
  if (commit) persistHistory()
}

const onSearchClear = () => {
  query.value = ''
  syncRoute()
}

const onTagChange = () => {
  syncRoute()
  persistHistory()
}

const onTagModeChange = () => {
  if (selectedTagIds.value.length <= 1) return
  syncRoute()
  persistHistory()
}

const onHistoryPick = (item: SearchHistoryItem) => {
  query.value = item.q
  selectedTagIds.value = [...item.tagIds]
  tagMode.value = parseTagSearchMode(item.tagMode)
  syncRoute()
  persistHistory()
}

const onRemoveHistory = (item: SearchHistoryItem) => {
  removeSearchHistory(item)
  refreshHistory()
}

const onClearHistory = () => {
  clearSearchHistory()
  refreshHistory()
}

const openNode = (node: NodeItem) => {
  touchRecentView(node.id)
  router.push(`/browse/${node.id}`)
}

const onToggleFavorite = async (node: NodeItem) => {
  const { data } = await toggleFavorite(node.id)
  favoriteIds.value = data.favorited
    ? [...new Set([...favoriteIds.value, node.id])]
    : favoriteIds.value.filter((id) => id !== node.id)
}

const openEdit = (node: NodeItem) => {
  editNode.value = node
  editOpen.value = true
}

const onEditSaved = (node?: NodeItem) => {
  if (node) items.value = items.value.map((n) => (n.id === node.id ? node : n))
}

const openTagPicker = (nodeIds: number[]) => {
  tagPickerNodeIds.value = nodeIds
  tagPickerOpen.value = true
}

const onTagCreated = (tag: TagItem) => {
  if (!allTags.value.some((t) => t.id === tag.id)) {
    allTags.value = [...allTags.value, tag].sort((a, b) => a.name.localeCompare(b.name))
  }
}

const refreshNodeTags = async (ids: number[]) => {
  if (!ids.length) return
  const { data } = await fetchNodesTags(ids)
  const next = { ...nodeTagsMap.value }
  for (const g of data) next[g.node_id] = g.tags
  nodeTagsMap.value = next
}

const onTagPickerConfirm = async (tagIds: number[]) => {
  if (!tagPickerNodeIds.value.length || !tagIds.length) return
  tagPickerSubmitting.value = true
  try {
    const { data } = await batchAddNodeTags(tagPickerNodeIds.value, tagIds)
    const n = tagPickerNodeIds.value.length
    ElMessage.success(n > 1 ? `已为 ${data.updated} 个相册添加标签` : '已添加标签')
    const ids = [...tagPickerNodeIds.value]
    tagPickerOpen.value = false
    tagPickerNodeIds.value = []
    await refreshNodeTags(ids)
  } catch {
    ElMessage.error('添加标签失败')
  } finally {
    tagPickerSubmitting.value = false
  }
}

const onTagPickerRemove = async (tagId: number) => {
  const nodeIds = tagPickerNodeIds.value.filter((id) =>
    (nodeTagsMap.value[id] ?? []).some((t) => t.id === tagId),
  )
  if (!nodeIds.length) return
  try {
    await Promise.all(nodeIds.map((id) => removeNodeTag(id, tagId)))
    await refreshNodeTags(nodeIds)
    ElMessage.success('已移除标签')
  } catch {
    ElMessage.error('移除标签失败')
  }
}

const openMovePicker = (nodeIds: number[]) => {
  moveNodeIds.value = nodeIds
  movePickerOpen.value = true
}

const onMoveConfirm = async (targetParentId: number | null) => {
  if (!moveNodeIds.value.length) return
  moving.value = true
  try {
    const ids = [...moveNodeIds.value]
    const { data } = await moveNodes({ ids, target_parent_id: targetParentId })
    if (data.errors.length) {
      ElMessage.warning(
        data.moved > 0
          ? `已移动 ${data.moved} 项，部分失败：${data.errors.join('; ')}`
          : data.errors.join('; '),
      )
    } else {
      ElMessage.success(`已移动 ${data.moved} 项`)
    }
    if (data.moved > 0) {
      if (data.errors.length) await runSearch()
      else {
        const moved = new Set(ids)
        items.value = items.value.filter((n) => !moved.has(n.id))
        total.value = Math.max(0, total.value - data.moved)
      }
    }
    movePickerOpen.value = false
    moveNodeIds.value = []
  } catch {
    ElMessage.error('移动失败')
  } finally {
    moving.value = false
  }
}

const deleteHint = (node: NodeItem) =>
  node.source_type === 'zip' ? '磁盘上的压缩包将被永久删除。' : '磁盘上的文件夹将被永久删除。'

const onDeleteNode = async (node: NodeItem) => {
  try {
    await ElMessageBox.confirm(
      `确定删除「${node.name}」？\n\n${deleteHint(node)}`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const { data } = await deleteNodes([node.id])
    if (data.errors.length) {
      ElMessage.error(data.errors.join('; '))
      return
    }
    items.value = items.value.filter((n) => n.id !== node.id)
    total.value = Math.max(0, total.value - 1)
    ElMessage.success('已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const onWindowScroll = () => {
  showTopBtn.value = window.scrollY > TOP_THRESHOLD
}

const parseTagIds = (raw: unknown) => {
  const text = typeof raw === 'string' ? raw : ''
  return text.split(',').flatMap((part) => {
    const n = Number(part.trim())
    return Number.isInteger(n) && n > 0 ? [n] : []
  })
}

let observer: IntersectionObserver | undefined

watch(
  () => [route.query.q, route.query.tags, route.query.tag_mode] as const,
  ([q, tags, mode]) => {
    query.value = typeof q === 'string' ? q : ''
    selectedTagIds.value = parseTagIds(tags)
    tagMode.value = parseTagSearchMode(mode)
    runSearch()
  },
  { immediate: true },
)

watch(sentinelRef, (el, _, onCleanup) => {
  observer?.disconnect()
  if (!el) return
  observer = new IntersectionObserver(
    ([entry]) => {
      if (entry?.isIntersecting) loadMore()
    },
    { rootMargin: '240px' },
  )
  observer.observe(el)
  onCleanup(() => observer?.disconnect())
})

onMounted(async () => {
  const [tagsRes, favIdsRes] = await Promise.all([fetchTags(), fetchFavoriteIds()])
  allTags.value = tagsRes.data
  favoriteIds.value = favIdsRes.data
  window.addEventListener('scroll', onWindowScroll, { passive: true })
  onWindowScroll()
})

onUnmounted(() => {
  window.removeEventListener('scroll', onWindowScroll)
  observer?.disconnect()
})
</script>

<style scoped>
.search-page {
  min-height: 100vh;
  background: var(--app-bg);
}

.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 16px 24px;
  background: var(--app-surface);
  border-bottom: 1px solid var(--app-border);
}

.content {
  max-width: var(--app-page-width);
  margin: 0 auto;
  padding: 32px 32px 80px;
}

.history-panel {
  margin-bottom: 28px;
}

.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text-muted);
}

.history-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.history-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 1px solid var(--app-border);
  border-radius: 999px;
  background: var(--app-surface);
  color: var(--app-text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s ease, color 0.2s ease;
}

.history-item:hover {
  border-color: var(--el-color-primary);
  color: var(--app-text);
}

.history-item .remove {
  font-size: 12px;
  color: var(--app-text-muted);
}

.history-item .remove:hover {
  color: var(--el-color-danger);
}

.summary {
  margin: 0 0 24px;
  color: var(--app-text-secondary);
  font-size: 14px;
}

.sentinel {
  margin-top: 24px;
  min-height: 48px;
}

.load-hint {
  margin: 0;
  text-align: center;
  font-size: 13px;
  color: var(--app-text-muted);
  padding: 16px 0;
}

.load-hint.end {
  color: var(--app-text-secondary);
}

.back-top {
  position: fixed;
  right: 28px;
  bottom: 32px;
  z-index: 300;
  width: 44px;
  height: 44px;
  border: 1px solid var(--app-border);
  border-radius: 50%;
  background: color-mix(in srgb, var(--app-surface) 92%, transparent);
  color: var(--app-text-secondary);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  box-shadow: var(--app-card-shadow-hover);
  backdrop-filter: blur(12px);
  transition: transform 0.2s ease, color 0.2s ease;
}

.back-top:hover {
  color: var(--app-text);
  transform: translateY(-2px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
