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
        <LazyCover
          v-if="node.cover_rel_path"
          :src="coverThumbUrl(node.id, node.cover_rel_path)"
        />
        <div v-else class="cover placeholder">📁</div>
        <button
          v-if="showFavorite"
          type="button"
          class="fav-btn"
          :class="{ active: isFavorite(node.id) }"
          aria-label="收藏"
          title="收藏"
          @click.stop="emit('toggle-favorite', node)"
        >
          <svg class="fav-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path
              v-if="isFavorite(node.id)"
              fill="currentColor"
              d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"
            />
            <path
              v-else
              fill="none"
              stroke="currentColor"
              stroke-width="1.6"
              d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"
            />
          </svg>
        </button>
      </div>
      <div class="meta">
        <div class="info">
          <div class="name">{{ node.name }}</div>
          <div class="sub">{{ subText(node) }}</div>
        </div>
        <div v-if="tagsOf(node.id).length" class="tags">
          <el-tag
            v-for="tag in tagsOf(node.id)"
            :key="tag.id"
            size="small"
            class="tag-chip"
            @click.stop="emit('tag-click', tag)"
          >
            {{ tag.name }}
          </el-tag>
        </div>
      </div>
      <button
        v-if="showMenu"
        type="button"
        class="card-menu more-btn"
        aria-label="更多操作"
        @click.stop="openMenu(node, $event)"
      >
        <el-icon><MoreFilled /></el-icon>
      </button>
    </article>
  </div>
  <el-empty v-else description="暂无内容，请先扫描或添加文件夹" class="empty" />

  <Teleport to="body">
    <div
      v-if="menu"
      class="menu-pop"
      :style="{ top: `${menu.y}px`, left: `${menu.x}px` }"
      @click.stop
    >
      <button type="button" @click="pickMenu('edit')">编辑</button>
      <button type="button" @click="pickMenu('add-tags')">标签</button>
      <button type="button" @click="pickMenu('move')">移动到…</button>
      <button type="button" class="danger" @click="pickMenu('delete')">删除</button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { MoreFilled } from '@element-plus/icons-vue'
import LazyCover from '@/components/LazyCover.vue'
import type { NodeItem } from '@/types/node'
import type { TagItem } from '@/types/tag'
import { coverThumbUrl } from '@/api/nodes'

const props = withDefaults(
  defineProps<{
    nodes: NodeItem[]
    selectable?: boolean
    selectedIds?: number[]
    nodeTags?: Record<number, TagItem[]>
    progressMap?: Record<number, number>
    showMenu?: boolean
    showFavorite?: boolean
    favoriteIds?: number[]
  }>(),
  { showMenu: true, showFavorite: true },
)

const emit = defineEmits<{
  open: [node: NodeItem]
  toggle: [id: number]
  edit: [node: NodeItem]
  'add-tags': [node: NodeItem]
  move: [node: NodeItem]
  delete: [node: NodeItem]
  'toggle-favorite': [node: NodeItem]
  'tag-click': [tag: TagItem]
}>()

const favoriteSet = computed(() => new Set(props.favoriteIds ?? []))
const selectedSet = computed(() => new Set(props.selectedIds ?? []))

const isSelected = (id: number) => selectedSet.value.has(id)
const isFavorite = (id: number) => favoriteSet.value.has(id)
const tagsOf = (nodeId: number) => props.nodeTags?.[nodeId] ?? []

const menu = ref<{ node: NodeItem; x: number; y: number } | null>(null)

const openMenu = (node: NodeItem, e: MouseEvent) => {
  const el = e.currentTarget as HTMLElement
  const r = el.getBoundingClientRect()
  menu.value = { node, x: Math.max(8, r.right - 120), y: r.bottom + 4 }
}

const closeMenu = () => {
  menu.value = null
}

const pickMenu = (cmd: string) => {
  const node = menu.value?.node
  if (!node) return
  onMenu(node, cmd)
  closeMenu()
}

const onDocClick = () => closeMenu()

onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))

const progressText = (node: NodeItem) => {
  if (node.node_type === 'container' || node.image_count <= 0) return ''
  const pct = props.progressMap?.[node.id]
  return pct != null && pct > 0 ? `${pct}%` : ''
}

const onMenu = (node: NodeItem, cmd: string) => {
  if (cmd === 'delete') emit('delete', node)
  else if (cmd === 'edit') emit('edit', node)
  else if (cmd === 'add-tags') emit('add-tags', node)
  else if (cmd === 'move') emit('move', node)
}

const onCardClick = (node: NodeItem) => {
  if (props.selectable) emit('toggle', node.id)
  else emit('open', node)
}

const subText = (node: NodeItem) => {
  const parts: string[] = []
  if (node.node_type !== 'container' && node.image_count > 0) parts.push(`${node.image_count} 张`)
  if (node.subdir_count > 0) parts.push(`${node.subdir_count} 个文件夹`)
  if (node.archive_count > 0) parts.push(`${node.archive_count} 个压缩包`)
  if (parts.length) return parts.join(' · ')
  if (node.node_type === 'container') return '空文件夹'
  if (node.source_type === 'zip') return `${node.image_count} 张`
  return '空相册'
}
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(var(--grid-card-min), 1fr));
  gap: 16px;
}

@media (min-width: 768px) {
.grid {
  gap: 24px;
}
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
  content-visibility: auto;
  contain-intrinsic-size: 200px 280px;
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
  z-index: 5;
}

.cover-wrap {
  position: relative;
  overflow: hidden;
  background: var(--app-cover-bg);
}

.fav-btn {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  background: transparent;
  color: rgb(255 255 255 / 92%);
  cursor: pointer;
  filter: drop-shadow(0 1px 3px rgb(0 0 0 / 55%));
  transition: transform 0.15s ease, color 0.15s ease;
}

.fav-btn:hover {
  transform: scale(1.1);
  color: #ffd04b;
}

.fav-btn.active {
  color: #ffc107;
}

.fav-icon {
  width: 22px;
  height: 22px;
  display: block;
  pointer-events: none;
}

.progress-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 4;
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

.cover-wrap :deep(.cover) {
  transition: transform 0.3s ease;
}

.cover {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  display: block;
  transition: transform 0.3s ease;
}

.card:hover .cover-wrap :deep(.cover) {
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
  padding: 12px 44px 12px 12px;
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
}

.tag-chip {
  cursor: pointer;
}

.card-menu {
  position: absolute;
  right: 8px;
  bottom: 8px;
  z-index: 5;
}

.more-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  margin: 0;
  border: none;
  background: transparent;
  color: var(--app-text-muted);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  transition: color 0.15s ease;
}

.more-btn:hover {
  color: var(--app-text);
}

.menu-pop {
  position: fixed;
  z-index: 3000;
  min-width: 120px;
  padding: 4px;
  border: 1px solid var(--app-border);
  border-radius: 8px;
  background: var(--app-surface);
  box-shadow: var(--app-card-shadow-hover);
}

.menu-pop button {
  display: block;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--app-text);
  font-size: 14px;
  text-align: left;
  cursor: pointer;
}

.menu-pop button:hover {
  background: color-mix(in srgb, var(--el-color-primary) 10%, transparent);
}

.menu-pop button.danger {
  color: var(--el-color-danger);
}

.danger {
  color: var(--el-color-danger);
}

.empty {
  margin: 60px auto;
}
</style>
