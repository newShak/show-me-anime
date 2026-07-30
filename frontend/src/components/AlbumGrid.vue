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
        <span v-if="progressText(node)" class="progress-badge">{{ progressText(node) }}</span>
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
        <div class="info">
          <div class="name">{{ node.name }}</div>
          <div class="sub">{{ subText(node) }}</div>
        </div>
        <div v-if="tagsOf(node.id).length" class="tags">
          <el-tag v-for="tag in tagsOf(node.id)" :key="tag.id" size="small">{{ tag.name }}</el-tag>
        </div>
      </div>
      <div class="card-menu" @click.stop>
        <el-dropdown trigger="click" @command="(cmd: string) => onMenu(node, cmd)">
          <button type="button" class="more-btn" aria-label="更多操作">
            <el-icon><MoreFilled /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="add-tags">标签</el-dropdown-item>
              <el-dropdown-item divided command="delete">
                <span class="danger">删除</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </article>
  </div>
  <el-empty v-else description="暂无内容，请先扫描或添加文件夹" class="empty" />
</template>

<script setup lang="ts">
import { MoreFilled } from '@element-plus/icons-vue'
import type { NodeItem } from '@/types/node'
import type { TagItem } from '@/types/tag'
import { coverThumbUrl } from '@/api/nodes'

const props = defineProps<{
  nodes: NodeItem[]
  selectable?: boolean
  selectedIds?: number[]
  nodeTags?: Record<number, TagItem[]>
  progressMap?: Record<number, number>
}>()
const emit = defineEmits<{
  open: [node: NodeItem]
  toggle: [id: number]
  'add-tags': [node: NodeItem]
  delete: [node: NodeItem]
}>()

const isSelected = (id: number) => props.selectedIds?.includes(id) ?? false

const tagsOf = (nodeId: number) => props.nodeTags?.[nodeId] ?? []

const progressText = (node: NodeItem) => {
  if (node.node_type === 'container' || node.image_count <= 0) return ''
  const pct = props.progressMap?.[node.id]
  return pct != null && pct > 0 ? `${pct}%` : ''
}

const onMenu = (node: NodeItem, cmd: string) => {
  if (cmd === 'delete') emit('delete', node)
  else if (cmd === 'add-tags') emit('add-tags', node)
}

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
  position: relative;
  overflow: hidden;
  background: var(--app-cover-bg);
}

.progress-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.4;
  color: #fff;
  background: rgb(0 0 0 / 55%);
  backdrop-filter: blur(4px);
  pointer-events: none;
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
  padding: 12px;
  min-height: 56px;
}

.info {
  min-width: 0;
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

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
  padding-right: 28px;
}

.card-menu {
  position: absolute;
  right: 8px;
  bottom: 8px;
  z-index: 3;
}

.card-menu :deep(.el-dropdown) {
  display: block;
}

.more-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: color-mix(in srgb, var(--app-text) 12%, var(--app-surface));
  color: var(--app-text-secondary);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  box-shadow: var(--app-card-shadow);
}

.more-btn:hover {
  color: var(--app-text);
  background: var(--app-surface);
}

.danger {
  color: var(--el-color-danger);
}

.empty {
  margin: 60px auto;
}
</style>
