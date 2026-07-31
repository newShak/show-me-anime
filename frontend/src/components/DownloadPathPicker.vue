<template>
  <div class="path-picker">
    <div class="path-row">
      <el-input :model-value="displayPath" readonly placeholder="选择保存目录" />
      <el-button @click="openDialog">选择</el-button>
    </div>
    <p v-if="hint" class="hint">{{ hint }}</p>

    <el-dialog v-model="dialogOpen" title="选择保存目录" width="480px" append-to-body @closed="resetDialog">
      <el-input
        v-model="searchQuery"
        clearable
        placeholder="搜索目录…"
        class="search-input"
        @input="onSearchInput"
      />
      <div v-if="searchQuery.trim()" class="search-wrap">
        <el-skeleton v-if="searchLoading" :rows="4" animated />
        <ul v-else-if="searchResults.length" class="search-list">
          <li
            v-for="item in searchResults"
            :key="item.id"
            class="search-item"
            :class="{ active: selectedId === item.id }"
            @click="selectSearchResult(item)"
          >
            <span class="search-name">{{ item.name }}</span>
            <span class="search-path">{{ item.path }}</span>
          </li>
        </ul>
        <p v-else class="empty-hint">无匹配目录</p>
      </div>
      <template v-else>
        <div class="root-row">
          <button
            type="button"
            class="root-btn"
            :class="{ active: selectedId === null && selectionTouched }"
            @click="selectRoot"
          >
            画廊根目录
          </button>
        </div>
        <div class="tree-wrap">
          <el-tree
            ref="treeRef"
            :key="treeKey"
            :props="treeProps"
            node-key="id"
            lazy
            :load="loadNode"
            :current-node-key="selectedId ?? undefined"
            :expand-on-click-node="false"
            highlight-current
            @node-click="onNodeClick"
          />
        </div>
      </template>
      <p class="selected-hint">已选：{{ pendingPath }}</p>
      <div class="mkdir-row">
        <el-input v-model="newFolderName" placeholder="新建文件夹名称" @keyup.enter="onMkdir" />
        <el-button :loading="mkdirLoading" @click="onMkdir">新建</el-button>
      </div>
      <p class="dialog-hint">在当前选中位置下创建文件夹，创建后会自动选中。</p>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" @click="onConfirm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, type ElTree } from 'element-plus'
import { createNodeDir, fetchNodes } from '@/api/nodes'
import { searchNodes } from '@/api/search'
import { getDownloadParentPath, saveDownloadParentPath } from '@/composables/useDownloadParentPath'
import type { NodeItem } from '@/types/node'

const model = defineModel<string>({ default: '' })
defineProps<{ hint?: string }>()

const dialogOpen = ref(false)
const selectedId = ref<number | null>(null)
const pathMap = ref<Record<number, string>>({})
const newFolderName = ref('')
const mkdirLoading = ref(false)
const treeKey = ref(0)
const searchQuery = ref('')
const searchResults = ref<NodeItem[]>([])
const searchLoading = ref(false)
const dialogInitialPath = ref('')
const selectionTouched = ref(false)
const treeRef = ref<InstanceType<typeof ElTree>>()
let searchTimer: ReturnType<typeof setTimeout> | null = null

const displayPath = computed(() => model.value || '（画廊根目录）')

const isDirNode = (item: NodeItem) =>
  item.source_type !== 'zip' &&
  (item.node_type === 'container' || item.subdir_count > 0 || item.archive_count > 0)

const treeProps = {
  label: 'name',
  isLeaf: (data: NodeItem) => data.subdir_count === 0 && data.archive_count === 0,
}

const pendingPath = computed(() => {
  if (selectionTouched.value) return selectedId.value == null ? '（画廊根目录）' : selectedPath() || '（画廊根目录）'
  return dialogInitialPath.value || '（画廊根目录）'
})

const loadNode = async (node: { level: number; data: NodeItem }, resolve: (data: NodeItem[]) => void) => {
  const parentId = node.level === 0 ? undefined : node.data.id
  const { data } = await fetchNodes(parentId)
  const dirs = data.filter(isDirNode)
  for (const item of dirs) pathMap.value[item.id] = item.path
  resolve(dirs)
}

const onNodeClick = (data: NodeItem) => {
  if (!isDirNode(data)) return
  pathMap.value[data.id] = data.path
  selectedId.value = data.id
  selectionTouched.value = true
}

const selectRoot = () => {
  selectedId.value = null
  selectionTouched.value = true
  treeRef.value?.setCurrentKey(undefined)
}

const selectedPath = () => (selectedId.value == null ? '' : pathMap.value[selectedId.value] ?? '')

const runSearch = async (q: string) => {
  const text = q.trim()
  if (!text) {
    searchResults.value = []
    searchLoading.value = false
    return
  }
  searchLoading.value = true
  try {
    const { data } = await searchNodes({ q: text, limit: 30 })
    searchResults.value = data.items.filter(isDirNode)
    for (const item of searchResults.value) pathMap.value[item.id] = item.path
  } catch {
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

const onSearchInput = () => {
  if (searchTimer) clearTimeout(searchTimer)
  const q = searchQuery.value
  if (!q.trim()) {
    searchResults.value = []
    searchLoading.value = false
    return
  }
  searchLoading.value = true
  searchTimer = setTimeout(() => void runSearch(q), 300)
}

const selectSearchResult = (item: NodeItem) => {
  if (!isDirNode(item)) return
  pathMap.value[item.id] = item.path
  selectedId.value = item.id
  selectionTouched.value = true
}

const restoreSelection = async (path: string) => {
  if (!path) return
  try {
    const name = path.split('/').pop() || path
    const { data } = await searchNodes({ q: name, limit: 50 })
    const match = data.items.find((item) => item.path === path && isDirNode(item))
    if (!match) return
    pathMap.value[match.id] = match.path
    selectedId.value = match.id
  } catch {
    /* ignore */
  }
}

const openDialog = async () => {
  dialogInitialPath.value = model.value
  if (!model.value) {
    const saved = getDownloadParentPath()
    if (saved) model.value = saved
    dialogInitialPath.value = model.value
  }
  dialogOpen.value = true
  await restoreSelection(model.value)
}

const onConfirm = () => {
  if (!selectionTouched.value) {
    model.value = dialogInitialPath.value
  } else {
    model.value = selectedId.value != null ? selectedPath() : ''
  }
  saveDownloadParentPath(model.value)
  dialogOpen.value = false
}

const onMkdir = async () => {
  const name = newFolderName.value.trim()
  if (!name) return
  mkdirLoading.value = true
  try {
    const { data } = await createNodeDir({ parent_id: selectedId.value, name })
    pathMap.value[data.id] = data.path
    selectedId.value = data.id
    selectionTouched.value = true
    newFolderName.value = ''
    searchQuery.value = ''
    searchResults.value = []
    treeKey.value += 1
    ElMessage.success(`已创建 ${data.path}`)
  } catch {
    ElMessage.error('创建文件夹失败')
  } finally {
    mkdirLoading.value = false
  }
}

const resetDialog = () => {
  newFolderName.value = ''
  selectedId.value = null
  pathMap.value = {}
  searchQuery.value = ''
  searchResults.value = []
  searchLoading.value = false
  dialogInitialPath.value = ''
  selectionTouched.value = false
  if (searchTimer) {
    clearTimeout(searchTimer)
    searchTimer = null
  }
}

const openAt = (path: string) => {
  model.value = path
}
defineExpose({ openAt })
</script>

<style scoped>
.path-row {
  display: flex;
  gap: 8px;
}

.path-row .el-input {
  flex: 1;
}

.hint,
.dialog-hint,
.empty-hint,
.selected-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--app-text-muted);
}

.selected-hint {
  margin-top: 12px;
  color: var(--el-color-primary);
}

.search-input {
  margin-bottom: 8px;
}

.search-wrap {
  max-height: 280px;
  overflow: auto;
  border: 1px solid var(--app-border);
  border-radius: 8px;
  padding: 4px;
}

.search-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.search-item {
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
}

.search-item:hover,
.search-item.active {
  background: var(--el-color-primary-light-9);
}

.search-name {
  display: block;
  font-size: 14px;
}

.search-path {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: var(--app-text-muted);
  word-break: break-all;
}

.root-row {
  margin-bottom: 8px;
}

.root-btn {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--app-border);
  border-radius: 8px;
  background: var(--app-surface);
  text-align: left;
  cursor: pointer;
  font-size: 14px;
}

.root-btn.active {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}

.tree-wrap {
  max-height: 280px;
  overflow: auto;
  border: 1px solid var(--app-border);
  border-radius: 8px;
  padding: 8px;
}

.mkdir-row {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.mkdir-row .el-input {
  flex: 1;
}

.el-tree {
  background: transparent;
}
</style>
