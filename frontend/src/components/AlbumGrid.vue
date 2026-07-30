<template>
  <div v-if="nodes.length" class="grid">
    <article
      v-for="node in nodes"
      :key="node.id"
      class="card"
      :class="{ selected: selectable && isSelected(node.id) }"
      @click="onCardClick(node)"
    >
      <el-checkbox
        v-if="selectable"
        class="check"
        :model-value="isSelected(node.id)"
        @click.stop
        @change="emit('toggle', node.id)"
      />
      <div class="cover-wrap">
        <img
          v-if="node.node_type !== 'container'"
          :src="coverThumbUrl(node.id)"
          class="cover"
          loading="lazy"
          alt=""
        />
        <div v-else class="cover placeholder">📁</div>
      </div>
      <div class="meta">
        <div class="name">{{ node.name }}</div>
        <div class="sub">{{ subText(node) }}</div>
      </div>
    </article>
  </div>
  <el-empty v-else description="暂无内容，请先扫描或添加文件夹" class="empty" />
</template>

<script setup lang="ts">
import type { NodeItem } from '@/types/node'
import { coverThumbUrl } from '@/api/nodes'

const props = defineProps<{
  nodes: NodeItem[]
  selectable?: boolean
  selectedIds?: number[]
}>()
const emit = defineEmits<{ open: [node: NodeItem]; toggle: [id: number] }>()

const isSelected = (id: number) => props.selectedIds?.includes(id) ?? false

const onCardClick = (node: NodeItem) => {
  if (props.selectable) emit('toggle', node.id)
  else emit('open', node)
}

const subText = (node: NodeItem) => {
  const parts: string[] = []
  if (node.node_type !== 'container' && node.image_count > 0) {
    parts.push(`${node.image_count} 张`)
  }
  if (node.subdir_count > 0) {
    parts.push(`${node.subdir_count} 个文件夹`)
  }
  if (parts.length) return parts.join(' · ')
  if (node.node_type === 'container') return '空文件夹'
  return '空相册'
}
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 24px;
}

.card {
  position: relative;
  cursor: pointer;
  background: var(--app-surface);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: var(--app-card-shadow);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border: 2px solid transparent;
}

.card:hover {
  transform: translateY(-3px);
  box-shadow: var(--app-card-shadow-hover);
}

.card.selected {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 1px var(--el-color-primary);
}

.check {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 1;
}

.cover-wrap {
  overflow: hidden;
  background: var(--app-cover-bg);
}

.cover {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  display: block;
  transition: transform 0.3s ease;
}

.card:hover .cover {
  transform: scale(1.03);
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 3 / 4;
  font-size: 48px;
}

.meta {
  padding: 14px 16px 16px;
}

.name {
  font-weight: 600;
  font-size: 15px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sub {
  color: var(--app-text-muted);
  font-size: 13px;
  margin-top: 4px;
}

.empty {
  margin: 60px auto;
}
</style>
