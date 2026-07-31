<template>
  <el-tree
    :props="treeProps"
    node-key="id"
    lazy
    :load="loadNode"
    highlight-current
    @node-click="onClick"
  />
</template>

<script setup lang="ts">
import type { NodeItem } from '@/types/node'
import { fetchNodes } from '@/api/nodes'

const emit = defineEmits<{ select: [id: number | null] }>()

const treeProps = {
  label: 'name',
  isLeaf: (data: NodeItem) => data.node_type === 'album',
}

const loadNode = async (node: { level: number; data: NodeItem }, resolve: (data: NodeItem[]) => void) => {
  const parentId = node.level === 0 ? undefined : node.data.id
  const { data } = await fetchNodes(parentId)
  resolve(data)
}

const onClick = (data: NodeItem) => emit('select', data.id)
</script>

<style scoped>
.el-tree {
  background: transparent;
}

.el-tree :deep(.el-tree-node__children) {
  overflow: hidden;
}

.el-tree :deep(.el-collapse-transition-enter-active),
.el-tree :deep(.el-collapse-transition-leave-active) {
  transition: height 0.28s ease, opacity 0.22s ease;
}
</style>
