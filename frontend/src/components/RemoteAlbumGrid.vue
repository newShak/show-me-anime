<template>
  <div v-if="items.length" class="grid">
    <article
      v-for="item in items"
      :key="item.id"
      class="card"
      :class="{ selected: selectable && selectedIds?.has(item.id) }"
      @click="onCardClick(item)"
    >
      <label v-if="selectable" class="check" @click.stop>
        <el-checkbox
          :model-value="selectedIds?.has(item.id)"
          @update:model-value="(v: boolean) => toggle(item.id, v)"
        />
      </label>
      <div class="cover-wrap">
        <span v-if="badge(item)" class="badge">{{ badge(item) }}</span>
        <img :src="coverSrc(item)" class="cover" loading="lazy" alt="" />
      </div>
      <div class="meta">
        <div class="name" v-html="item.title" />
        <div class="sub">{{ subText(item) }}</div>
      </div>
    </article>
  </div>
  <el-empty v-else description="暂无结果" class="empty" />
</template>

<script setup lang="ts">
import { remoteCoverUrl } from '@/api/download'
import type { RemoteAlbum } from '@/types/download'

const props = defineProps<{
  items: RemoteAlbum[]
  selectable?: boolean
  selectedIds?: Set<string>
}>()

const emit = defineEmits<{
  open: [item: RemoteAlbum]
  'update:selectedIds': [ids: Set<string>]
}>()

const coverSrc = (item: RemoteAlbum) =>
  item.cover_url.startsWith('/api/') ? item.cover_url : remoteCoverUrl(item.source, item.id)

const badge = (item: RemoteAlbum) => {
  if (item.category && item.language) return `${item.category} / ${item.language}`
  return item.language || item.category || ''
}

const subText = (item: RemoteAlbum) => {
  const parts: string[] = []
  if (item.page_count) parts.push(`${item.page_count} P`)
  if (item.language && !badge(item).includes(item.language)) parts.push(item.language)
  if (item.tags.length) parts.push(item.tags.slice(0, 2).join(' · '))
  return parts.join(' · ') || '外站相册'
}

const toggle = (id: string, checked: boolean) => {
  const next = new Set(props.selectedIds ?? [])
  if (checked) next.add(id)
  else next.delete(id)
  emit('update:selectedIds', next)
}

const onCardClick = (item: RemoteAlbum) => {
  if (props.selectable) {
    const next = new Set(props.selectedIds ?? [])
    if (next.has(item.id)) next.delete(item.id)
    else next.add(item.id)
    emit('update:selectedIds', next)
    return
  }
  emit('open', item)
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

.card.selected {
  border-color: var(--el-color-primary);
}

.card:hover {
  transform: translateY(-3px);
  box-shadow: var(--app-card-shadow-hover);
}

.check {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 3;
  padding: 2px 4px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.85);
}

.cover-wrap {
  position: relative;
  overflow: hidden;
  background: var(--app-cover-bg);
}

.badge {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 2;
  max-width: calc(100% - 20px);
  padding: 4px 10px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.3;
  backdrop-filter: blur(5px);
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.6);
  pointer-events: none;
}

.cover {
  display: block;
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
}

.meta {
  padding: 12px 14px 14px;
}

.name {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.sub {
  margin-top: 6px;
  font-size: 12px;
  color: var(--app-text-muted);
}

.empty {
  padding: 48px 0;
}
</style>
