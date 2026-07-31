<template>
  <el-dialog v-model="visible" :title="title" width="480px" @closed="reset">
    <p class="hint">选择目标位置，相册将移动为其子项（可移到文件夹或其他相册内）。</p>
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
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="onConfirm">移动</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { fetchNodes } from '@/api/nodes'
import type { NodeItem } from '@/types/node'

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

const onConfirm = () => emit('confirm', selectedId.value)

const reset = () => {
  selectedId.value = null
  pathMap.value = {}
}
</script>

<style scoped>
.hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--app-text-muted);
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
