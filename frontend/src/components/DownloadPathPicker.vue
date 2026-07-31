<template>
  <div class="path-picker">
    <div class="path-row">
      <el-input :model-value="displayPath" readonly placeholder="选择保存目录" />
      <el-button @click="dialogOpen = true">选择</el-button>
    </div>
    <p v-if="hint" class="hint">{{ hint }}</p>

    <el-dialog v-model="dialogOpen" title="选择保存目录" width="480px" append-to-body @closed="resetDialog">
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
          ref="treeRef"
          :key="treeKey"
          :props="treeProps"
          node-key="id"
          lazy
          :load="loadNode"
          highlight-current
          @node-click="onNodeClick"
        />
      </div>
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
import { ElMessage } from 'element-plus'
import { createNodeDir, fetchNodes } from '@/api/nodes'
import type { NodeItem } from '@/types/node'

const model = defineModel<string>({ default: '' })
defineProps<{ hint?: string }>()

const dialogOpen = ref(false)
const selectedId = ref<number | null>(null)
const pathMap = ref<Record<number, string>>({})
const newFolderName = ref('')
const mkdirLoading = ref(false)
const treeKey = ref(0)

const displayPath = computed(() => model.value || '（画廊根目录）')

const treeProps = {
  label: 'name',
  isLeaf: (data: NodeItem) => data.node_type === 'album' && data.subdir_count === 0,
  disabled: (data: NodeItem) => data.source_type === 'zip',
}

const loadNode = async (node: { level: number; data: NodeItem }, resolve: (data: NodeItem[]) => void) => {
  const parentId = node.level === 0 ? undefined : node.data.id
  const { data } = await fetchNodes(parentId)
  for (const item of data) pathMap.value[item.id] = item.path
  resolve(data.filter((item) => item.source_type !== 'zip'))
}

const onNodeClick = (data: NodeItem) => {
  if (data.source_type === 'zip') return
  selectedId.value = data.id
}

const selectedPath = () => (selectedId.value == null ? '' : pathMap.value[selectedId.value] ?? '')

const onConfirm = () => {
  model.value = selectedPath()
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
    newFolderName.value = ''
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
.dialog-hint {
  margin: 8px 0 0;
  font-size: 12px;
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
