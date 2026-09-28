<template>
  <el-dialog v-model="visible" :title="title" :width="dialogWidth" @closed="reset">
    <p class="hint">选择目标位置，相册将移动为其子项（可移到文件夹或其他相册内）。</p>
    <el-input
      v-model="searchQuery"
      clearable
      placeholder="搜索文件夹或相册…"
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
          :class="{ active: selectedId === item.id, disabled: isBlocked(item) }"
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
          :class="{ active: selectedId === null }"
          @click="selectedId = null"
        >
          画廊根目录
        </button>
      </div>
      <div class="tree-wrap">
        <el-tree
          :props="treeProps"
          node-key="id"
          lazy
          :load="loadNode"
          highlight-current
          @node-click="onNodeClick"
        />
      </div>
    </template>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="onConfirm">移动</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { fetchNodes } from '@/api/nodes'
import { searchNodes } from '@/api/search'
import { useDialogWidth } from '@/composables/useDialogWidth'
import type { NodeItem } from '@/types/node'

const dialogWidth = useDialogWidth('480px')

const props = withDefaults(
  defineProps<{
    excludePaths?: string[]
    title?: string
    submitting?: boolean
  }>(),
  { excludePaths: () => [], title: '移动到', submitting: false },
)

const emit = defineEmits<{ confirm: [targetParentId: number | null] }>()

const visible = defineModel<boolean>({ default: false })
const selectedId = ref<number | null>(null)
const pathMap = ref<Record<number, string>>({})
const searchQuery = ref('')
const searchResults = ref<NodeItem[]>([])
const searchLoading = ref(false)
let searchTimer: ReturnType<typeof setTimeout> | null = null

const treeProps = {
  label: 'name',
  isLeaf: (data: NodeItem) => data.node_type === 'album' && data.subdir_count === 0,
  disabled: (data: NodeItem) => isBlocked(data),
}

const isBlocked = (node: NodeItem) => {
  if (node.source_type === 'zip') return true
  const path = pathMap.value[node.id] ?? node.path
  return props.excludePaths.some((ex) => path === ex || path.startsWith(`${ex}/`))
}

const isMovableTarget = (item: NodeItem) => item.source_type !== 'zip' && !isBlocked(item)

const loadNode = async (node: { level: number; data: NodeItem }, resolve: (data: NodeItem[]) => void) => {
  const parentId = node.level === 0 ? undefined : node.data.id
  const { data } = await fetchNodes(parentId)
  for (const item of data) pathMap.value[item.id] = item.path
  resolve(data.filter((item) => item.source_type !== 'zip'))
}

const onNodeClick = (data: NodeItem) => {
  if (isBlocked(data)) return
  selectedId.value = data.id
}

const runSearch = async (q: string) => {
  const text = q.trim()
  if (!text) {
    searchResults.value = []
    searchLoading.value = false
    return
  }
  searchLoading.value = true
  try {
    const { data } = await searchNodes({ q: text, limit: 40 })
    searchResults.value = data.items.filter(isMovableTarget)
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
  if (!isMovableTarget(item)) return
  pathMap.value[item.id] = item.path
  selectedId.value = item.id
}

const onConfirm = () => emit('confirm', selectedId.value)

const reset = () => {
  selectedId.value = null
  pathMap.value = {}
  searchQuery.value = ''
  searchResults.value = []
  searchLoading.value = false
  if (searchTimer) {
    clearTimeout(searchTimer)
    searchTimer = null
  }
}
</script>

<style scoped>
.hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--app-text-muted);
}

.search-input {
  margin-bottom: 8px;
}

.search-wrap {
  max-height: 320px;
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

.search-item:hover:not(.disabled),
.search-item.active {
  background: color-mix(in srgb, var(--el-color-primary) 12%, transparent);
}

.search-item.disabled {
  opacity: 0.45;
  cursor: not-allowed;
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

.empty-hint {
  margin: 12px;
  font-size: 13px;
  color: var(--app-text-muted);
  text-align: center;
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
  max-height: 320px;
  overflow: auto;
  border: 1px solid var(--app-border);
  border-radius: 8px;
  padding: 8px;
}

.el-tree {
  background: transparent;
}
</style>
