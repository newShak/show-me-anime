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
        <el-button text @click="toggleThumbs">{{ thumbsVisible ? '隐藏预览' : '显示预览' }}</el-button>
      </div>
      <span class="page">{{ activePage + 1 }} / {{ total }}</span>
    </header>

    <div class="body">
      <aside v-show="thumbsVisible" class="thumbs" ref="thumbRef" @scroll="onThumbScroll">
        <div class="thumbs-phantom" :style="{ height: `${thumbTotalHeight}px` }">
          <div class="thumbs-window" :style="{ transform: `translateY(${thumbOffset}px)` }">
            <button
              v-for="index in visibleThumbIndices"
              :key="index"
              class="thumb"
              :class="{ active: activePage === index }"
              :data-index="index"
              :style="{ height: `${THUMB_IMG_HEIGHT}px` }"
              @click="scrollTo(index)"
            >
              <img :src="imageThumbUrl(nodeId, index)" :alt="`${index + 1}`" />
              <span>{{ index + 1 }}</span>
            </button>
          </div>
        </div>
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

    <footer class="hint">{{ thumbsVisible ? '左侧缩略图快速跳转 · ' : '' }}↑ ↓ 翻页 · Esc 退出</footer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { imageFileUrl, imageThumbUrl } from '@/api/nodes'
import type { ReaderMode } from '@/types/reader'

const THUMB_PAD = 8
const THUMB_GAP = 8
const THUMB_IMG_HEIGHT = Math.round((100 * 4) / 3)
const THUMB_ITEM_HEIGHT = THUMB_IMG_HEIGHT + THUMB_GAP
const THUMB_OVERSCAN = 4
const THUMBS_VISIBLE_KEY = 'reader-scroll-thumbs'

const readThumbsVisible = () => localStorage.getItem(THUMBS_VISIBLE_KEY) !== '0'

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
const thumbScrollTop = ref(0)
const thumbViewHeight = ref(0)
const thumbsVisible = ref(readThumbsVisible())

const toggleThumbs = () => {
  thumbsVisible.value = !thumbsVisible.value
  localStorage.setItem(THUMBS_VISIBLE_KEY, thumbsVisible.value ? '1' : '0')
  if (thumbsVisible.value) nextTick(syncThumbViewport)
}

const thumbTotalHeight = computed(() => THUMB_PAD * 2 + props.total * THUMB_ITEM_HEIGHT)

const thumbRange = computed(() => {
  if (!props.total) return { start: 0, end: 0, offset: THUMB_PAD }
  const viewH = thumbViewHeight.value || 600
  const start = Math.max(
    0,
    Math.floor((thumbScrollTop.value - THUMB_PAD) / THUMB_ITEM_HEIGHT) - THUMB_OVERSCAN,
  )
  const visible = Math.ceil(viewH / THUMB_ITEM_HEIGHT) + THUMB_OVERSCAN * 2
  const end = Math.min(props.total, start + visible)
  return { start, end, offset: THUMB_PAD + start * THUMB_ITEM_HEIGHT }
})

const visibleThumbIndices = computed(() => {
  const { start, end } = thumbRange.value
  return Array.from({ length: end - start }, (_, i) => start + i)
})

const thumbOffset = computed(() => thumbRange.value.offset)

const setPageRef = (index: number, el: HTMLElement | null) => {
  pageRefs.value[index] = el
}

const syncThumbViewport = () => {
  thumbViewHeight.value = thumbRef.value?.clientHeight ?? 0
}

const onThumbScroll = () => {
  thumbScrollTop.value = thumbRef.value?.scrollTop ?? 0
}

const scrollThumbIntoView = (index: number) => {
  const el = thumbRef.value
  if (!el) return
  const itemTop = THUMB_PAD + index * THUMB_ITEM_HEIGHT
  const itemBottom = itemTop + THUMB_ITEM_HEIGHT
  if (itemTop < el.scrollTop) el.scrollTop = Math.max(0, itemTop - THUMB_PAD)
  else if (itemBottom > el.scrollTop + el.clientHeight) {
    el.scrollTop = itemBottom - el.clientHeight + THUMB_PAD
  }
  thumbScrollTop.value = el.scrollTop
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

let resizeObserver: ResizeObserver | undefined

watch(
  () => props.page,
  (p) => {
    if (p === activePage.value) return
    activePage.value = p
    nextTick(() => scrollTo(p, false))
  },
)

watch(
  () => props.total,
  () => nextTick(syncThumbViewport),
)

onMounted(async () => {
  rootRef.value?.focus()
  syncThumbViewport()
  if (thumbRef.value) {
    resizeObserver = new ResizeObserver(syncThumbViewport)
    resizeObserver.observe(thumbRef.value)
  }
  await nextTick()
  scrollTo(props.page, false)
})

onUnmounted(() => resizeObserver?.disconnect())
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
}

.thumbs-phantom {
  position: relative;
  width: 100%;
}

.thumbs-window {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  padding: 8px 6px;
  will-change: transform;
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

.thumb:last-child {
  margin-bottom: 0;
}

.thumb.active {
  border-color: var(--el-color-primary);
}

.thumb img {
  display: block;
  width: 100%;
  height: 100%;
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
