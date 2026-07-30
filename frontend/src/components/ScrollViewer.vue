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
      <span class="page">{{ activePage + 1 }} / {{ total }}</span>
    </header>

    <div class="body">
      <aside class="thumbs" ref="thumbRef">
        <button
          v-for="i in total"
          :key="i"
          class="thumb"
          :class="{ active: activePage === i - 1 }"
          :data-index="i - 1"
          @click="scrollTo(i - 1)"
        >
          <img :src="imageThumbUrl(nodeId, i - 1)" :alt="`${i}`" loading="lazy" />
          <span>{{ i }}</span>
        </button>
      </aside>

      <main class="scroll" ref="scrollRef" @scroll="onScroll">
        <figure
          v-for="i in total"
          :key="i"
          :ref="(el) => setPageRef(i - 1, el as HTMLElement | null)"
          class="page-block"
        >
          <img :src="imageFileUrl(nodeId, i - 1)" :alt="`${i}`" loading="lazy" />
        </figure>
      </main>
    </div>

    <footer class="hint">左侧缩略图快速跳转 · ↑ ↓ 翻页 · Esc 退出</footer>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { imageFileUrl, imageThumbUrl } from '@/api/nodes'
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
const scrollRef = ref<HTMLElement | null>(null)
const thumbRef = ref<HTMLElement | null>(null)
const pageRefs = ref<(HTMLElement | null)[]>([])
const activePage = ref(props.page)
const scrolling = ref(false)

const setPageRef = (index: number, el: HTMLElement | null) => {
  pageRefs.value[index] = el
}

const scrollThumbIntoView = (index: number) => {
  const btn = thumbRef.value?.querySelector(`[data-index="${index}"]`)
  btn?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
}

const scrollTo = (index: number, smooth = true) => {
  const el = pageRefs.value[index]
  const container = scrollRef.value
  if (!el || !container) return
  scrolling.value = true
  container.scrollTo({ top: el.offsetTop, behavior: smooth ? 'smooth' : 'auto' })
  activePage.value = index
  emit('change', index)
  scrollThumbIntoView(index)
  setTimeout(() => {
    scrolling.value = false
  }, smooth ? 400 : 0)
}

const detectActivePage = () => {
  const container = scrollRef.value
  if (!container) return
  const anchor = container.scrollTop + container.clientHeight * 0.25
  let best = 0
  pageRefs.value.forEach((el, i) => {
    if (el && el.offsetTop <= anchor) best = i
  })
  if (best === activePage.value) return
  activePage.value = best
  emit('change', best)
  scrollThumbIntoView(best)
}

const onScroll = () => {
  if (scrolling.value) return
  detectActivePage()
}

const go = (index: number) => {
  if (index < 0 || index >= props.total) return
  scrollTo(index)
}

const onKeydown = (e: KeyboardEvent) => {
  if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') go(activePage.value - 1)
  if (e.key === 'ArrowDown' || e.key === 'ArrowRight') go(activePage.value + 1)
  if (e.key === 'Escape') emit('close')
}

watch(
  () => props.page,
  (p) => {
    if (p === activePage.value) return
    activePage.value = p
    nextTick(() => scrollTo(p, false))
  },
)

onMounted(async () => {
  rootRef.value?.focus()
  await nextTick()
  scrollTo(props.page, false)
})
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
  flex-shrink: 0;
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
  min-width: 64px;
  text-align: right;
}

.body {
  flex: 1;
  display: flex;
  min-height: 0;
}

.thumbs {
  width: 112px;
  flex-shrink: 0;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.45);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  padding: 8px 6px;
}

.thumb {
  display: block;
  width: 100%;
  margin-bottom: 8px;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 4px;
  background: none;
  cursor: pointer;
  overflow: hidden;
  position: relative;
}

.thumb.active {
  border-color: var(--el-color-primary);
}

.thumb img {
  display: block;
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  background: #222;
}

.thumb span {
  position: absolute;
  right: 4px;
  bottom: 4px;
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.65);
}

.scroll {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}

.page-block {
  margin: 0;
  display: flex;
  justify-content: center;
  background: #111;
}

.page-block img {
  display: block;
  width: 100%;
  max-width: 100%;
  height: auto;
  user-select: none;
}

.hint {
  text-align: center;
  font-size: 12px;
  color: #888;
  padding: 8px;
  flex-shrink: 0;
}
</style>
