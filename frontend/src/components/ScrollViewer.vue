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
        <el-button text :type="favorited ? 'warning' : undefined" @click="emit('toggle-favorite')">
          <el-icon><StarFilled v-if="favorited" /><Star v-else /></el-icon>
        </el-button>
      </div>
      <span class="page">{{ activePage + 1 }} / {{ total }}</span>
    </header>

    <div class="body">
      <aside class="thumbs" :class="{ visible: thumbsVisible }" ref="thumbRef" @scroll="onThumbScroll">
        <div class="thumbs-inner">
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
                <img
                  :key="`${nodeId}-${index}-${cacheVersion}`"
                  :src="imageThumbUrl(nodeId, index, cacheVersion)"
                  :alt="`${index + 1}`"
                />
                <span>{{ index + 1 }}</span>
              </button>
            </div>
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
          <img
            :key="`${nodeId}-${i - 1}-${cacheVersion}`"
            :src="imageFileUrl(nodeId, i - 1, cacheVersion)"
            :alt="`${i}`"
            :loading="i - 1 <= eagerUntil ? 'eager' : 'lazy'"
          />
        </figure>
      </main>
    </div>

    <footer class="hint">{{ thumbsVisible ? '左侧缩略图快速跳转 · ' : '' }}↑ ↓ 翻页 · Esc 退出</footer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Star, StarFilled } from '@element-plus/icons-vue'
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
  cacheVersion?: number
  favorited?: boolean
}>()

const emit = defineEmits<{
  close: []
  change: [page: number]
  'mode-change': [mode: ReaderMode]
  'toggle-favorite': []
}>()

const rootRef = ref<HTMLElement | null>(null)
const scrollRef = ref<HTMLElement | null>(null)
const thumbRef = ref<HTMLElement | null>(null)
const pageRefs = ref<(HTMLElement | null)[]>([])
const activePage = ref(props.page)
const eagerUntil = ref(props.page)
const scrolling = ref(false)
const initializing = ref(true)
const thumbScrollTop = ref(0)
const thumbViewHeight = ref(0)
const thumbsVisible = ref(readThumbsVisible())

const toggleThumbs = () => {
  thumbsVisible.value = !thumbsVisible.value
  localStorage.setItem(THUMBS_VISIBLE_KEY, thumbsVisible.value ? '1' : '0')
  if (thumbsVisible.value) {
    nextTick(() => {
      syncThumbViewport()
      scrollThumbIntoView(activePage.value)
    })
  }
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

const waitForImages = (index: number) => {
  const waits: Promise<void>[] = []
  for (let i = 0; i <= index; i++) {
    const img = pageRefs.value[i]?.querySelector('img') as HTMLImageElement | null
    if (!img || img.complete) continue
    waits.push(
      new Promise((resolve) => {
        img.addEventListener('load', () => resolve(), { once: true })
        img.addEventListener('error', () => resolve(), { once: true })
      }),
    )
  }
  return Promise.all(waits)
}

const scrollTo = async (index: number, smooth = true) => {
  const el = pageRefs.value[index]
  const container = scrollRef.value
  if (!el || !container) return

  eagerUntil.value = Math.max(eagerUntil.value, index)
  await waitForImages(index)
  await nextTick()

  scrolling.value = true
  activePage.value = index
  emit('change', index)
  scrollThumbIntoView(index)
  container.scrollTo({ top: el.offsetTop, behavior: smooth ? 'smooth' : 'auto' })

  setTimeout(() => {
    scrolling.value = false
  }, smooth ? 400 : 50)
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
  if (scrolling.value || initializing.value) return
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
  () => {
    pageRefs.value = []
    nextTick(syncThumbViewport)
  },
)

onMounted(async () => {
  rootRef.value?.focus()
  syncThumbViewport()
  if (thumbRef.value) {
    resizeObserver = new ResizeObserver(syncThumbViewport)
    resizeObserver.observe(thumbRef.value)
  }
  initializing.value = true
  eagerUntil.value = props.page
  await nextTick()
  await scrollTo(props.page, false)
  initializing.value = false
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
  width: 0;
  flex-shrink: 0;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.45);
  border-right: 1px solid transparent;
  transition: width 0.28s ease, border-color 0.28s ease;
}

.thumbs.visible {
  width: 112px;
  overflow-y: auto;
  border-right-color: rgba(255, 255, 255, 0.08);
}

.thumbs-inner {
  width: 112px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.thumbs.visible .thumbs-inner {
  opacity: 1;
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
