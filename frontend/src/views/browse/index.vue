<template>
  <div class="browse">
    <div class="layout" :class="{ collapsed: sidebarCollapsed }">
      <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
        <div class="sidebar-inner">
          <div class="sidebar-head">
            <span>目录</span>
            <el-button text class="toggle-btn" @click="toggleSidebar">×</el-button>
          </div>
          <div class="sidebar-tree">
            <NodeTree @select="onTreeSelect" />
          </div>
        </div>
      </aside>

      <main class="content">
        <div class="float-bar">
          <el-button text size="small" @click="toggleSidebar">
            {{ sidebarCollapsed ? '目录' : '收起' }}
          </el-button>
          <span class="float-divider" />
          <el-select
            v-model="sortValue"
            class="sort-select"
            size="small"
            @change="onSortChange"
          >
            <el-option
              v-for="opt in SORT_OPTIONS"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <template v-if="nodes.length">
            <span class="float-divider" />
            <el-button text size="small" @click="toggleSelectMode">{{ selectMode ? '取消' : '选择' }}</el-button>
            <template v-if="selectMode">
              <el-button text size="small" @click="toggleSelectAll">
                {{ allSelected ? '取消全选' : '全选' }}
              </el-button>
              <el-button
                text
                size="small"
                :disabled="!selectedIds.length"
                @click="openTagPicker(selectedIds)"
              >
                标签{{ selectedIds.length ? ` (${selectedIds.length})` : '' }}
              </el-button>
              <el-button
                text
                size="small"
                :disabled="!selectedIds.length"
                @click="openMovePicker(selectedIds)"
              >
                移动{{ selectedIds.length ? ` (${selectedIds.length})` : '' }}
              </el-button>
              <el-button
                text
                size="small"
                type="danger"
                :disabled="!selectedIds.length"
                :loading="deleting"
                @click="onBatchDelete"
              >
                删除{{ selectedIds.length ? ` (${selectedIds.length})` : '' }}
              </el-button>
            </template>
          </template>
        </div>

        <div class="page">
          <header class="page-head">
            <div class="title-row">
              <div>
                <h1>{{ pageTitle }}</h1>
                <p class="subtitle">{{ subtitle }}</p>
                <div v-if="currentNodeTags.length" class="node-tags">
                  <el-tag
                    v-for="tag in currentNodeTags"
                    :key="tag.id"
                    size="small"
                    class="node-tag"
                    @click="onCurrentTagClick(tag)"
                  >
                    {{ tag.name }}
                  </el-tag>
                </div>
              </div>
              <div v-if="currentNode" class="head-actions">
                <el-button
                  v-if="canFavoriteCurrent"
                  text
                  :type="isCurrentFavorite ? 'warning' : undefined"
                  @click="onToggleCurrentFavorite"
                >
                  <el-icon><StarFilled v-if="isCurrentFavorite" /><Star v-else /></el-icon>
                  {{ isCurrentFavorite ? '已收藏' : '收藏' }}
                </el-button>
                <el-button text @click="openEdit(currentNode)">编辑</el-button>
                <el-button v-if="isAlbumView && images.length" type="primary" round @click="startRead">
                  阅读
                </el-button>
              </div>
            </div>

            <BreadcrumbNav v-if="showCrumbs" :items="crumbs" @navigate="goTo" />
            <div class="search-row">
              <SearchBar
                full
                show-history
                :tags="allTags"
                placeholder="搜索相册名、路径..."
                @search="onTextSearch"
                @pick="onSearchHistoryPick"
              />
              <TagSelect
                v-model="filterTagIds"
                :tags="allTags"
                clearable
                collapse-tags
                placeholder="按标签筛选"
                width="200px"
                @change="onTagFilterChange"
              />
              <el-segmented
                v-if="filterTagIds.length > 1"
                v-model="tagMode"
                :options="TAG_SEARCH_MODE_OPTIONS"
                size="small"
              />
            </div>
          </header>

          <section class="gallery">
            <template v-if="currentNode && isAlbumView">
              <ImageGrid :node-id="currentNode.id" :images="images" @open="openReader" />
              <div v-if="nodes.length" class="section-label">子文件夹</div>
              <AlbumGrid
                v-if="nodes.length"
                :nodes="nodes"
                :selectable="selectMode"
                :selected-ids="selectedIds"
                :node-tags="nodeTagsMap"
                :progress-map="progressPercentMap"
                :favorite-ids="favoriteIds"
                show-menu
                show-favorite
                @toggle="toggleSelect"
                @open="onOpenNode"
                @toggle-favorite="onToggleFavorite"
                @edit="openEdit"
                @add-tags="(node) => openTagPicker([node.id])"
                @move="(node) => openMovePicker([node.id])"
                @delete="onDeleteNode"
              />
            </template>
            <template v-else>
              <AlbumGrid
                :nodes="nodes"
                :selectable="selectMode"
                :selected-ids="selectedIds"
                :node-tags="nodeTagsMap"
                :progress-map="progressPercentMap"
                :favorite-ids="favoriteIds"
                show-menu
                show-favorite
                @toggle="toggleSelect"
                @open="onOpenNode"
                @toggle-favorite="onToggleFavorite"
                @edit="openEdit"
                @add-tags="(node) => openTagPicker([node.id])"
                @move="(node) => openMovePicker([node.id])"
                @delete="onDeleteNode"
              />
            </template>
          </section>
        </div>
      </main>
    </div>

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
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Star, StarFilled } from '@element-plus/icons-vue'
import SearchBar from '@/components/SearchBar.vue'
import TagSelect from '@/components/TagSelect.vue'
import AlbumGrid from '@/components/AlbumGrid.vue'
import BreadcrumbNav from '@/components/BreadcrumbNav.vue'
import ImageGrid from '@/components/ImageGrid.vue'
import NodeTree from '@/components/NodeTree.vue'
import NodeEditDialog from '@/components/NodeEditDialog.vue'
import NodeMoveDialog from '@/components/NodeMoveDialog.vue'
import TagPickerDialog from '@/components/TagPickerDialog.vue'
import {
  fetchNode,
  fetchNodeAncestors,
  fetchNodeImages,
  fetchNodes,
  fetchNodesProgress,
  fetchProgress,
  deleteNodes,
  moveNodes,
} from '@/api/nodes'
import { batchAddNodeTags, fetchNodesTags, fetchTags, removeNodeTag } from '@/api/tags'
import {
  getStoredSort,
  parseSortValue,
  saveSort,
  SORT_OPTIONS,
} from '@/composables/useNodeSort'
import { saveBrowseScroll, getBrowseScroll, clearBrowseScroll } from '@/composables/useBrowseScroll'
import { addSearchHistory, type SearchHistoryItem } from '@/composables/useSearchHistory'
import { fetchFavoriteIds, toggleFavorite } from '@/composables/useFavorites'
import { touchRecentView } from '@/composables/useRecentView'
import { parseTagSearchMode, TAG_SEARCH_MODE_OPTIONS, type TagSearchMode } from '@/types/search'
import type { ImageItem, NodeItem } from '@/types/node'
import type { TagItem } from '@/types/tag'

type Crumb = { id: number | null; name: string }

const route = useRoute()
const router = useRouter()

const nodes = ref<NodeItem[]>([])
const images = ref<ImageItem[]>([])
const currentNode = ref<NodeItem | null>(null)
const crumbs = ref<Crumb[]>([{ id: null, name: '画廊' }])
const editOpen = ref(false)
const editNode = ref<NodeItem | null>(null)
const selectMode = ref(false)
const selectedIds = ref<number[]>([])
const deleting = ref(false)
const allTags = ref<TagItem[]>([])
const nodeTagsMap = ref<Record<number, TagItem[]>>({})
const progressPercentMap = ref<Record<number, number>>({})
const tagPickerOpen = ref(false)
const tagPickerNodeIds = ref<number[]>([])
const tagPickerSubmitting = ref(false)
const movePickerOpen = ref(false)
const moveNodeIds = ref<number[]>([])
const moving = ref(false)
const filterTagIds = ref<number[]>([])
const tagMode = ref<TagSearchMode>('or')
const favoriteIds = ref<number[]>([])
const SIDEBAR_KEY = 'sidebar-collapsed'
const sidebarCollapsed = ref(localStorage.getItem(SIDEBAR_KEY) !== '0')
const stored = getStoredSort()
const sortValue = ref(`${stored.sortBy}:${stored.sortOrder}`)
const nodeSort = computed(() => parseSortValue(sortValue.value))

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem(SIDEBAR_KEY, sidebarCollapsed.value ? '1' : '0')
}

const onSortChange = () => {
  saveSort(nodeSort.value)
  loadView(nodeId.value)
}

const buildSearchQuery = (q: string, tagIds: number[], mode: TagSearchMode = 'or') => {
  const query: Record<string, string> = {}
  if (q) query.q = q
  if (tagIds.length) {
    query.tags = tagIds.join(',')
    if (tagIds.length > 1 && mode === 'and') query.tag_mode = 'and'
  }
  return query
}

const goSearch = (q: string, tagIds: number[] = [], mode: TagSearchMode = 'or') => {
  router.push({ path: '/search', query: buildSearchQuery(q, tagIds, mode) })
}

const onTextSearch = (q: string, commit?: boolean) => {
  const trimmed = q.trim()
  if (!trimmed && !filterTagIds.value.length) return
  if (trimmed || commit) addSearchHistory(q, filterTagIds.value, tagMode.value)
  goSearch(q, filterTagIds.value, tagMode.value)
}

const onSearchHistoryPick = (item: SearchHistoryItem) => {
  tagMode.value = parseTagSearchMode(item.tagMode)
  goSearch(item.q, item.tagIds, tagMode.value)
}

const onTagFilterChange = () => {
  if (!filterTagIds.value.length) return
  addSearchHistory('', filterTagIds.value, tagMode.value)
  goSearch('', filterTagIds.value, tagMode.value)
}

const nodeId = computed(() => {
  const raw = route.params.nodeId
  return raw ? Number(raw) : null
})

const isAlbumView = computed(
  () => currentNode.value != null && currentNode.value.node_type !== 'container',
)

const canFavoriteCurrent = computed(
  () =>
    currentNode.value != null &&
    (currentNode.value.node_type !== 'container' || currentNode.value.image_count > 0),
)

const isCurrentFavorite = computed(
  () => currentNode.value != null && favoriteIds.value.includes(currentNode.value.id),
)

const currentNodeTags = computed(() => {
  const id = currentNode.value?.id
  return id != null ? (nodeTagsMap.value[id] ?? []) : []
})

const pageTitle = computed(() =>
  nodeId.value == null ? '画廊' : currentNode.value?.name ?? '加载中...',
)

const subtitle = computed(() => {
  if (currentNode.value && isAlbumView.value) {
    return `${images.value.length} 张图片`
  }
  if (currentNode.value) {
    const parts: string[] = []
    if (currentNode.value.subdir_count > 0) parts.push(`${currentNode.value.subdir_count} 个文件夹`)
    if (currentNode.value.archive_count > 0) parts.push(`${currentNode.value.archive_count} 个压缩包`)
    if (parts.length) return parts.join(' · ')
  }
  const count = nodes.value.length
  return count ? `${count} 项` : '暂无内容'
})

const showCrumbs = computed(() => crumbs.value.length > 1)

const allSelected = computed(
  () => nodes.value.length > 0 && selectedIds.value.length === nodes.value.length,
)

const clearSelection = () => {
  selectMode.value = false
  selectedIds.value = []
}

const openEdit = (node: NodeItem) => {
  editNode.value = node
  editOpen.value = true
}

const onEditSaved = async (node?: NodeItem) => {
  if (node) {
    if (currentNode.value?.id === node.id) currentNode.value = node
    nodes.value = nodes.value.map((n) => (n.id === node.id ? node : n))
  }
  await loadView(nodeId.value)
}

const toggleSelectMode = () => {
  if (selectMode.value) clearSelection()
  else selectMode.value = true
}

const toggleSelect = (id: number) => {
  const set = new Set(selectedIds.value)
  if (set.has(id)) set.delete(id)
  else set.add(id)
  selectedIds.value = [...set]
}

const toggleSelectAll = () => {
  selectedIds.value = allSelected.value ? [] : nodes.value.map((n) => n.id)
}

const loadNodeTags = async (ids: number[]) => {
  if (!ids.length) {
    nodeTagsMap.value = {}
    return
  }
  const { data } = await fetchNodesTags(ids)
  nodeTagsMap.value = Object.fromEntries(data.map((g) => [g.node_id, g.tags]))
}

const refreshTags = () => {
  const ids = nodes.value.map((n) => n.id)
  if (currentNode.value) ids.push(currentNode.value.id)
  loadNodeTags([...new Set(ids)])
}

const onCurrentTagClick = (tag: TagItem) => {
  goSearch('', [tag.id])
}

const loadProgress = async () => {
  const albums = nodes.value.filter((n) => n.node_type !== 'container' && n.image_count > 0)
  if (!albums.length) {
    progressPercentMap.value = {}
    return
  }
  const { data } = await fetchNodesProgress(albums.map((n) => n.id))
  const next: Record<number, number> = {}
  for (const row of data) {
    if (row.updated_at == null) continue
    const node = albums.find((n) => n.id === row.node_id)
    if (!node) continue
    const pct = Math.min(100, Math.round(((row.page_index + 1) / node.image_count) * 100))
    if (pct > 0) next[row.node_id] = pct
  }
  progressPercentMap.value = next
}

const tagPickerTitle = computed(() =>
  tagPickerNodeIds.value.length > 1
    ? `批量标签（${tagPickerNodeIds.value.length} 项）`
    : '标签',
)

const movePickerTitle = computed(() =>
  moveNodeIds.value.length > 1
    ? `移动 ${moveNodeIds.value.length} 项到`
    : '移动到',
)

const moveExcludePaths = computed(() =>
  nodes.value.filter((n) => moveNodeIds.value.includes(n.id)).map((n) => n.path),
)

const openMovePicker = (nodeIds: number[]) => {
  moveNodeIds.value = nodeIds
  movePickerOpen.value = true
}

const onMoveConfirm = async (targetParentId: number | null) => {
  if (!moveNodeIds.value.length) return
  moving.value = true
  try {
    const { data } = await moveNodes({ ids: moveNodeIds.value, target_parent_id: targetParentId })
    if (data.errors.length) {
      ElMessage.warning(
        data.moved > 0
          ? `已移动 ${data.moved} 项，部分失败：${data.errors.join('; ')}`
          : data.errors.join('; '),
      )
    } else {
      ElMessage.success(`已移动 ${data.moved} 项`)
    }
    movePickerOpen.value = false
    moveNodeIds.value = []
    clearSelection()
    await loadView(nodeId.value)
  } catch {
    ElMessage.error('移动失败')
  } finally {
    moving.value = false
  }
}

const tagPickerExistingTags = computed(() => {
  const ids = tagPickerNodeIds.value
  if (!ids.length) return []
  const seen = new Map<number, TagItem>()
  for (const id of ids) {
    for (const tag of nodeTagsMap.value[id] ?? []) {
      seen.set(tag.id, tag)
    }
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

const openTagPicker = (nodeIds: number[]) => {
  tagPickerNodeIds.value = nodeIds
  tagPickerOpen.value = true
}

const onTagCreated = (tag: TagItem) => {
  if (!allTags.value.some((t) => t.id === tag.id)) {
    allTags.value = [...allTags.value, tag].sort((a, b) => a.name.localeCompare(b.name))
  }
}

const onTagPickerConfirm = async (tagIds: number[]) => {
  if (!tagPickerNodeIds.value.length || !tagIds.length) return
  tagPickerSubmitting.value = true
  try {
    const { data } = await batchAddNodeTags(tagPickerNodeIds.value, tagIds)
    const n = tagPickerNodeIds.value.length
    ElMessage.success(n > 1 ? `已为 ${data.updated} 个相册添加标签` : '已添加标签')
    tagPickerOpen.value = false
    tagPickerNodeIds.value = []
    await refreshTags()
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
    await refreshTags()
    ElMessage.success('已移除标签')
  } catch {
    ElMessage.error('移除标签失败')
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

  deleting.value = true
  try {
    const { data } = await deleteNodes([node.id])
    if (data.errors.length) {
      ElMessage.error(data.errors.join('; '))
    } else {
      ElMessage.success('已删除')
    }
    await loadView(nodeId.value)
  } catch {
    ElMessage.error('删除失败')
  } finally {
    deleting.value = false
  }
}

const onBatchDelete = async () => {
  if (!selectedIds.value.length) return
  const names = nodes.value.filter((n) => selectedIds.value.includes(n.id)).map((n) => n.name)
  try {
    await ElMessageBox.confirm(
      `确定删除 ${names.length} 个相册？\n\n${names.join('、')}\n\n磁盘上的文件夹将被永久删除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }

  deleting.value = true
  try {
    const { data } = await deleteNodes(selectedIds.value)
    if (data.errors.length) {
      ElMessage.warning(`已删除 ${data.deleted} 项，部分失败：${data.errors.join('; ')}`)
    } else {
      ElMessage.success(`已删除 ${data.deleted} 项`)
    }
    clearSelection()
    await loadView(nodeId.value)
  } catch {
    ElMessage.error('删除失败')
  } finally {
    deleting.value = false
  }
}

const loadCrumbs = async (node: NodeItem | null) => {
  const chain: Crumb[] = [{ id: null, name: '画廊' }]
  if (node == null) {
    crumbs.value = chain
    return
  }
  const ancestors =
    node.parent_id == null ? [] : (await fetchNodeAncestors(node.id)).data
  crumbs.value = [
    ...chain,
    ...ancestors.map((a) => ({ id: a.id, name: a.name })),
    { id: node.id, name: node.name },
  ]
}

const applyBrowseScroll = async () => {
  const top = getBrowseScroll(nodeId.value)
  if (top == null) return
  await nextTick()
  await new Promise<void>((r) => requestAnimationFrame(() => r()))
  window.scrollTo(0, top)
  clearBrowseScroll(nodeId.value)
}

const loadView = async (id: number | null) => {
  const sort = nodeSort.value
  if (id == null) {
    currentNode.value = null
    nodes.value = (await fetchNodes(undefined, sort)).data
    images.value = []
    crumbs.value = [{ id: null, name: '画廊' }]
    await Promise.all([refreshTags(), loadProgress()])
    return
  }

  const [nodeRes, childrenRes] = await Promise.all([fetchNode(id), fetchNodes(id, sort)])
  const node = nodeRes.data
  currentNode.value = node

  if (node.node_type === 'container') {
    nodes.value = childrenRes.data
    images.value = []
    await Promise.all([loadCrumbs(node), refreshTags(), loadProgress()])
    return
  }

  const [imagesRes] = await Promise.all([fetchNodeImages(id), loadCrumbs(node)])
  images.value = imagesRes.data.items
  nodes.value = node.node_type === 'both' ? childrenRes.data : []
  await Promise.all([refreshTags(), loadProgress()])
}

const goTo = (id: number | null) => {
  clearSelection()
  router.push(id == null ? '/browse' : `/browse/${id}`)
}

const onTreeSelect = (id: number | null) => {
  goTo(id)
}

const onOpenNode = (node: NodeItem) => {
  goTo(node.id)
}

const onToggleFavorite = async (node: NodeItem) => {
  const { data } = await toggleFavorite(node.id)
  favoriteIds.value = data.favorited
    ? [...new Set([...favoriteIds.value, node.id])]
    : favoriteIds.value.filter((id) => id !== node.id)
}

const onToggleCurrentFavorite = async () => {
  if (!currentNode.value) return
  await onToggleFavorite(currentNode.value)
}

const openReader = (page = 0) => {
  if (!currentNode.value) return
  saveBrowseScroll(nodeId.value)
  router.push({
    path: `/reader/${currentNode.value.id}`,
    query: { page, mode: 'scroll' },
  })
}

const startRead = async () => {
  if (!currentNode.value) return
  const { data } = await fetchProgress(currentNode.value.id)
  const progress = data.page_index

  if (progress <= 0) {
    openReader(0)
    return
  }

  try {
    await ElMessageBox.confirm(
      `上次阅读至第 ${progress + 1} / ${images.value.length} 页`,
      '开始阅读',
      {
        confirmButtonText: `从进度继续（第 ${progress + 1} 页）`,
        cancelButtonText: '从头开始',
        distinguishCancelAndClose: true,
      },
    )
    openReader(progress)
  } catch (action) {
    if (action === 'cancel') openReader(0)
  }
}

watch(nodeId, async (id, prev) => {
  if (id != null && id !== prev) touchRecentView(id)
  await loadView(id)
  await applyBrowseScroll()
}, { immediate: true })

onMounted(async () => {
  const [tagsRes, favIdsRes] = await Promise.all([fetchTags(), fetchFavoriteIds()])
  allTags.value = tagsRes.data
  favoriteIds.value = favIdsRes.data
})
</script>

<style scoped>
.browse {
  min-height: calc(100vh - 52px);
}

.layout {
  display: flex;
  min-height: calc(100vh - 52px);
}

.sidebar {
  width: 240px;
  flex-shrink: 0;
  overflow: hidden;
  border-right: 1px solid var(--app-border);
  background: var(--app-surface);
  transition: width 0.28s ease, border-color 0.28s ease;
}

.sidebar.collapsed {
  width: 0;
  border-right-color: transparent;
}

.sidebar-inner {
  width: 240px;
  height: 100%;
  min-height: calc(100vh - 52px);
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  opacity: 1;
  transition: opacity 0.2s ease;
}

.sidebar.collapsed .sidebar-inner {
  opacity: 0;
  pointer-events: none;
}

.sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text-secondary);
}

.toggle-btn {
  padding: 4px;
  font-size: 18px;
  min-width: auto;
}

.sidebar-tree {
  flex: 1;
  overflow: auto;
  min-height: 0;
}

.content {
  flex: 1;
  overflow: auto;
  padding: 40px 32px 60px;
  position: relative;
}

.float-bar {
  position: fixed;
  top: 60px;
  right: 24px;
  z-index: 200;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 8px;
  background: color-mix(in srgb, var(--app-surface) 92%, transparent);
  border: 1px solid var(--app-border);
  border-radius: 999px;
  box-shadow: var(--app-card-shadow-hover);
  backdrop-filter: blur(12px);
}

.float-divider {
  width: 1px;
  height: 16px;
  margin: 0 2px;
  background: var(--app-border);
  flex-shrink: 0;
}

.sort-select {
  width: 108px;
}

.sort-select :deep(.el-select__wrapper) {
  box-shadow: none;
  background: transparent;
  padding: 0 8px;
}

.page {
  max-width: var(--app-page-width);
  margin: 0 auto;
}

.page-head {
  margin-bottom: 32px;
}

.title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

h1 {
  margin: 0;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.subtitle {
  margin: 6px 0 0;
  font-size: 14px;
  color: var(--app-text-muted);
}

.node-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.node-tag {
  cursor: pointer;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.page-head :deep(.crumb) {
  margin-bottom: 16px;
}

.search-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-row :deep(.search-bar.full) {
  flex: 1;
  width: auto;
  max-width: none;
}

.tag-filter {
  width: 200px;
  flex-shrink: 0;
}

.gallery {
  margin-top: 8px;
}

.section-label {
  margin: 32px 0 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
</style>
