<template>
  <div class="download-page">
    <header class="head">
      <div>
        <h1>外站下载</h1>
        <p class="sub">
          {{ mode === 'search' ? '搜索预览后下载到画廊目录' : '浏览站点首页与分类' }}
          <el-tag v-if="mockMode" size="small" type="info">Mock 模式</el-tag>
        </p>
      </div>
      <div class="head-actions">
        <el-button @click="recordsOpen = true">下载记录</el-button>
        <el-button :icon="FullScreen" title="全屏查看下载记录" @click="openRecordsFullscreen" />
        <template v-if="showGrid && items.length">
          <el-button :type="selectMode ? 'primary' : 'default'" @click="toggleSelectMode">
            {{ selectMode ? '取消多选' : '多选' }}
          </el-button>
          <el-button v-if="selectMode && selectedIds.size" type="primary" @click="openBatch">
            下载选中 ({{ selectedIds.size }})
          </el-button>
        </template>
      </div>
    </header>

    <div class="mode-row">
      <el-button-group>
        <el-button :type="mode === 'search' ? 'primary' : 'default'" @click="switchMode('search')">搜索</el-button>
        <el-button :type="mode === 'browse' ? 'primary' : 'default'" @click="switchMode('browse')">浏览站点</el-button>
      </el-button-group>
    </div>

    <div v-if="mode === 'search'" class="search-row">
      <el-input v-model="keyword" clearable placeholder="搜索关键词…" @keyup.enter="onSearch" />
      <el-button type="primary" :loading="loading" @click="onSearch">搜索</el-button>
    </div>

    <template v-else>
      <DownloadBrowseNav :nav="browseNav" :active-cate="browseCate" @select="onBrowseCate" />
      <p v-if="browseTitle" class="browse-title">{{ browseTitle }}</p>
    </template>

    <el-skeleton v-if="loading" :rows="4" animated />
    <RemoteAlbumGrid
      v-else-if="showGrid"
      :items="items"
      :selectable="selectMode"
      :selected-ids="selectedIds"
      @update:selected-ids="selectedIds = $event"
      @open="openDetail"
    />
    <el-empty v-else-if="mode === 'search'" description="输入关键词后点击搜索" class="empty-hint" />

    <el-pagination
      v-if="showGrid && total > pageSize"
      class="pager"
      layout="total, prev, pager, next"
      :total="total"
      :current-page="page"
      :page-size="pageSize"
      @current-change="onPageChange"
    />

    <DownloadDetailDialog v-model="detailOpen" :item="activeItem" :preview-batch-size="previewBatchSize" />
    <DownloadBatchDialog v-model="batchOpen" :items="selectedItems" @submitted="clearSelection" />
    <DownloadRecordDrawer ref="recordsRef" v-model="recordsOpen" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { FullScreen } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import RemoteAlbumGrid from '@/components/RemoteAlbumGrid.vue'
import DownloadBrowseNav from '@/components/DownloadBrowseNav.vue'
import DownloadDetailDialog from '@/components/DownloadDetailDialog.vue'
import DownloadBatchDialog from '@/components/DownloadBatchDialog.vue'
import DownloadRecordDrawer from '@/components/DownloadRecordDrawer.vue'
import { browseRemoteAlbums, fetchDownloadOptions, fetchDownloadSources, searchRemoteAlbums } from '@/api/download'
import type { BrowseNavItem, RemoteAlbum } from '@/types/download'

const SOURCE = 'wnacg'
const pageSize = 24

type Mode = 'search' | 'browse'

const mode = ref<Mode>('search')
const keyword = ref('')
const page = ref(1)
const total = ref(0)
const loading = ref(false)
const searched = ref(false)
const browsed = ref(false)
const items = ref<RemoteAlbum[]>([])
const mockMode = ref(true)
const previewBatchSize = ref(10)

const browseNav = ref<BrowseNavItem[]>([])
const browseCate = ref<number | null>(null)
const browseTitle = ref('')

const selectMode = ref(false)
const selectedIds = ref(new Set<string>())

const detailOpen = ref(false)
const activeItem = ref<RemoteAlbum | null>(null)
const batchOpen = ref(false)
const recordsOpen = ref(false)
const recordsRef = ref<{ openFullscreen: () => void } | null>(null)

const selectedItems = computed(() => items.value.filter((i) => selectedIds.value.has(i.id)))
const showGrid = computed(() => (mode.value === 'search' ? searched.value : browsed.value))

const loadSources = async () => {
  try {
    const [{ data: sources }, { data: options }] = await Promise.all([
      fetchDownloadSources(),
      fetchDownloadOptions(),
    ])
    mockMode.value = sources.find((s) => s.id === SOURCE)?.mock ?? false
    previewBatchSize.value = options.preview_batch_size
  } catch {
    /* ignore */
  }
}

const loadSearch = async () => {
  loading.value = true
  try {
    const { data } = await searchRemoteAlbums({
      q: keyword.value.trim(),
      page: page.value,
      pageSize,
      source: SOURCE,
    })
    items.value = data.items
    total.value = data.total
    selectedIds.value = new Set([...selectedIds.value].filter((id) => data.items.some((i) => i.id === id)))
  } catch {
    items.value = []
    total.value = 0
    ElMessage.error('搜索失败，请检查代理配置或 Mock 模式')
  } finally {
    loading.value = false
  }
}

const loadBrowse = async () => {
  loading.value = true
  try {
    const { data } = await browseRemoteAlbums({
      page: page.value,
      pageSize,
      cateId: browseCate.value,
      source: SOURCE,
    })
    items.value = data.items
    total.value = data.total
    browseNav.value = data.nav
    browseTitle.value = data.title
    browsed.value = true
    selectedIds.value = new Set([...selectedIds.value].filter((id) => data.items.some((i) => i.id === id)))
  } catch {
    items.value = []
    total.value = 0
    ElMessage.error('浏览失败，请检查代理配置或 Mock 模式')
  } finally {
    loading.value = false
  }
}

const load = () => (mode.value === 'search' ? loadSearch() : loadBrowse())

const onSearch = () => {
  page.value = 1
  searched.value = true
  selectedIds.value = new Set()
  loadSearch()
}

const onBrowseCate = (cateId: number | null) => {
  browseCate.value = cateId
  page.value = 1
  selectedIds.value = new Set()
  loadBrowse()
}

const switchMode = (next: Mode) => {
  if (mode.value === next) return
  mode.value = next
  page.value = 1
  selectedIds.value = new Set()
  selectMode.value = false
  if (next === 'browse') {
    browseCate.value = null
    loadBrowse()
  }
}

const onPageChange = (p: number) => {
  page.value = p
  load()
}

const toggleSelectMode = () => {
  selectMode.value = !selectMode.value
  if (!selectMode.value) selectedIds.value = new Set()
}

const clearSelection = () => {
  selectMode.value = false
  selectedIds.value = new Set()
}

const openDetail = (item: RemoteAlbum) => {
  activeItem.value = item
  detailOpen.value = true
}

const openBatch = () => {
  if (!selectedItems.value.length) return
  batchOpen.value = true
}

const openRecordsFullscreen = () => recordsRef.value?.openFullscreen()

onMounted(loadSources)
</script>

<style scoped>
.download-page {
  max-width: var(--app-page-width);
  margin: 0 auto;
  padding: 24px 32px 48px;
}

.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.head-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

h1 {
  margin: 0;
  font-size: 28px;
}

.sub {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--app-text-muted);
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-row {
  margin-bottom: 16px;
}

.search-row {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.search-row .el-input {
  flex: 1;
}

.browse-title {
  margin: 0 0 16px;
  font-size: 15px;
  color: var(--app-text-muted);
}

.pager {
  margin-top: 24px;
  justify-content: center;
}

.empty-hint {
  padding: 48px 0;
}
</style>
