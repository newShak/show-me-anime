<template>
  <div class="browse">
    <div class="layout" :class="{ collapsed: sidebarCollapsed }">
      <aside v-show="!sidebarCollapsed" class="sidebar">
        <div class="sidebar-head">
          <span>目录</span>
          <el-button text class="toggle-btn" @click="toggleSidebar">×</el-button>
        </div>
        <div class="sidebar-tree">
          <NodeTree @select="onTreeSelect" />
        </div>
      </aside>

      <main class="content">
        <div class="float-bar">
          <el-button text size="small" @click="toggleSidebar">
            {{ sidebarCollapsed ? '目录' : '收起' }}
          </el-button>
          <span class="float-divider" />
          <el-button text size="small" :loading="scanning" @click="onScan">扫描</el-button>
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
              </div>
              <div v-if="currentNode" class="head-actions">
                <el-button text @click="editOpen = true">编辑</el-button>
                <el-button v-if="isAlbumView && images.length" type="primary" round @click="startRead">
                  阅读
                </el-button>
              </div>
            </div>

            <BreadcrumbNav v-if="showCrumbs" :items="crumbs" @navigate="goTo" />
            <SearchBar
              full
              placeholder="搜索相册名、路径..."
              @search="(q) => $router.push({ path: '/search', query: { q } })"
            />
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
                @toggle="toggleSelect"
                @open="onOpenNode"
              />
            </template>
            <template v-else>
              <AlbumGrid
                :nodes="nodes"
                :selectable="selectMode"
                :selected-ids="selectedIds"
                @toggle="toggleSelect"
                @open="onOpenNode"
              />
            </template>
          </section>
        </div>
      </main>
    </div>

    <NodeEditDialog v-model="editOpen" :node="currentNode" @saved="loadView(nodeId)" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import SearchBar from '@/components/SearchBar.vue'
import AlbumGrid from '@/components/AlbumGrid.vue'
import BreadcrumbNav from '@/components/BreadcrumbNav.vue'
import ImageGrid from '@/components/ImageGrid.vue'
import NodeTree from '@/components/NodeTree.vue'
import NodeEditDialog from '@/components/NodeEditDialog.vue'
import { fetchNode, fetchNodeImages, fetchNodes, fetchProgress, deleteNodes } from '@/api/nodes'
import { triggerScan } from '@/api/scan'
import {
  getStoredSort,
  parseSortValue,
  saveSort,
  SORT_OPTIONS,
} from '@/composables/useNodeSort'
import { getStoredReaderMode } from '@/composables/useReaderMode'
import type { ImageItem, NodeItem } from '@/types/node'

type Crumb = { id: number | null; name: string }

const route = useRoute()
const router = useRouter()

const nodes = ref<NodeItem[]>([])
const images = ref<ImageItem[]>([])
const currentNode = ref<NodeItem | null>(null)
const crumbs = ref<Crumb[]>([{ id: null, name: '画廊' }])
const scanning = ref(false)
const editOpen = ref(false)
const selectMode = ref(false)
const selectedIds = ref<number[]>([])
const deleting = ref(false)
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

const nodeId = computed(() => {
  const raw = route.params.nodeId
  return raw ? Number(raw) : null
})

const isAlbumView = computed(
  () => currentNode.value != null && currentNode.value.node_type !== 'container',
)

const pageTitle = computed(() =>
  nodeId.value == null ? '画廊' : currentNode.value?.name ?? '加载中...',
)

const subtitle = computed(() => {
  if (currentNode.value && isAlbumView.value) {
    return `${images.value.length} 张图片`
  }
  const count = nodes.value.length
  return count ? `${count} 个相册` : '暂无相册'
})

const showCrumbs = computed(() => crumbs.value.length > 1)

const allSelected = computed(
  () => nodes.value.length > 0 && selectedIds.value.length === nodes.value.length,
)

const clearSelection = () => {
  selectMode.value = false
  selectedIds.value = []
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

const loadCrumbs = async (id: number | null) => {
  const chain: Crumb[] = [{ id: null, name: '画廊' }]
  if (id == null) {
    crumbs.value = chain
    return
  }
  let cur = await fetchNode(id).then((r) => r.data)
  const stack: Crumb[] = []
  while (cur) {
    stack.unshift({ id: cur.id, name: cur.name })
    if (cur.parent_id == null) break
    cur = (await fetchNode(cur.parent_id)).data
  }
  crumbs.value = [...chain, ...stack]
}

const loadView = async (id: number | null) => {
  const sort = nodeSort.value
  if (id == null) {
    currentNode.value = null
    nodes.value = (await fetchNodes(undefined, sort)).data
    images.value = []
    crumbs.value = [{ id: null, name: '画廊' }]
    return
  }

  const node = (await fetchNode(id)).data
  currentNode.value = node
  await loadCrumbs(id)

  if (node.node_type === 'container') {
    nodes.value = (await fetchNodes(id, sort)).data
    images.value = []
    return
  }

  images.value = (await fetchNodeImages(id)).data.items
  nodes.value = node.node_type === 'both' ? (await fetchNodes(id, sort)).data : []
}

const goTo = (id: number | null) => {
  clearSelection()
  router.push(id == null ? '/browse' : `/browse/${id}`)
}

const onTreeSelect = (id: number | null) => {
  goTo(id)
  sidebarCollapsed.value = true
  localStorage.setItem(SIDEBAR_KEY, '1')
}

const onOpenNode = (node: NodeItem) => goTo(node.id)

const openReader = (page = 0) => {
  if (!currentNode.value) return
  router.push({
    path: `/reader/${currentNode.value.id}`,
    query: { page, mode: getStoredReaderMode() },
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

const onScan = async () => {
  scanning.value = true
  try {
    const { data } = await triggerScan()
    ElMessage.success(`扫描完成：新增 ${data.added}，更新 ${data.updated}`)
    await loadView(nodeId.value)
  } catch {
    ElMessage.error('扫描失败')
  } finally {
    scanning.value = false
  }
}

watch(nodeId, (id) => loadView(id), { immediate: true })

onMounted(() => loadView(nodeId.value))
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
  border-right: 1px solid var(--app-border);
  padding: 16px 12px;
  background: var(--app-surface);
  display: flex;
  flex-direction: column;
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

.head-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.page-head :deep(.crumb) {
  margin-bottom: 16px;
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
