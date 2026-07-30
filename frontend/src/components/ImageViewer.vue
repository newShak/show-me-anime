<template>
  <div class="viewer" tabindex="0" ref="rootRef" @keydown="onKeydown">
    <header class="bar">
      <el-button text @click="emit('close')">← 返回</el-button>
      <span class="title">{{ title }}</span>
      <div class="modes">
        <el-button text :type="mode === 'page' ? 'primary' : undefined" @click="emit('mode-change', 'page')">
          翻页
        </el-button>
        <el-button text :type="mode === 'scroll' ? 'primary' : undefined" @click="emit('mode-change', 'scroll')">
          滚动
        </el-button>
      </div>
      <span class="page">{{ page + 1 }} / {{ total }}</span>
    </header>

    <div class="stage" @click="onStageClick">
      <img v-if="currentUrl" :src="currentUrl" :alt="`${page + 1}`" />
      <el-empty v-else description="加载中..." />
    </div>

    <footer class="hint">← → 翻页 · Esc 退出 · 点击左右区域翻页</footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { imageFileUrl } from '@/api/nodes'
import type { ReaderMode } from '@/types/reader'

const props = defineProps<{
  nodeId: number
  total: number
  page: number
  title: string
  mode: ReaderMode
}>()

const emit = defineEmits<{
  close: []
  change: [page: number]
  'mode-change': [mode: ReaderMode]
}>()

const rootRef = ref<HTMLElement | null>(null)

const currentUrl = computed(() =>
  props.total > 0 && props.page >= 0 && props.page < props.total
    ? imageFileUrl(props.nodeId, props.page)
    : '',
)

const preload = (index: number) => {
  if (index < 0 || index >= props.total) return
  const img = new Image()
  img.src = imageFileUrl(props.nodeId, index)
}

const go = (index: number) => {
  if (index < 0 || index >= props.total) return
  emit('change', index)
}

const onKeydown = (e: KeyboardEvent) => {
  if (e.key === 'ArrowLeft') go(props.page - 1)
  if (e.key === 'ArrowRight') go(props.page + 1)
  if (e.key === 'Escape') emit('close')
}

const onStageClick = (e: MouseEvent) => {
  const w = (e.currentTarget as HTMLElement).clientWidth
  if (e.clientX < w / 2) go(props.page - 1)
  else go(props.page + 1)
}

watch(
  () => props.page,
  (p) => {
    preload(p - 1)
    preload(p + 1)
  },
  { immediate: true },
)

onMounted(() => rootRef.value?.focus())
</script>

<style scoped>
.viewer {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: #111;
  color: #fff;
  display: flex;
  flex-direction: column;
  outline: none;
}

.bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.6);
}

.title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.modes {
  display: flex;
  gap: 4px;
}

.page {
  color: #ccc;
  font-size: 14px;
}

.stage {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
  cursor: pointer;
}

.stage img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  user-select: none;
}

.hint {
  text-align: center;
  font-size: 12px;
  color: #888;
  padding: 8px;
}
</style>
