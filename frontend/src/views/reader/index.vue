<template>
  <ImageViewer
    v-if="ready && mode === 'page'"
    v-model:fit="fit"
    :node-id="nodeId"
    :total="total"
    :page="page"
    :title="title"
    :mode="mode"
    :cache-version="cacheVersion"
    :favorited="favorited"
    @close="onClose"
    @change="onPageChange"
    @mode-change="onModeChange"
    @toggle-favorite="onToggleFavorite"
  />
  <ScrollViewer
    v-else-if="ready"
    v-model:fit="fit"
    :node-id="nodeId"
    :total="total"
    :page="page"
    :title="title"
    :mode="mode"
    :cache-version="cacheVersion"
    :favorited="favorited"
    @close="onClose"
    @change="onPageChange"
    @mode-change="onModeChange"
    @toggle-favorite="onToggleFavorite"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ImageViewer from '@/components/ImageViewer.vue'
import ScrollViewer from '@/components/ScrollViewer.vue'
import { resolveReaderMode, saveReaderMode } from '@/composables/useReaderMode'
import { getStoredReaderFit, saveReaderFit } from '@/composables/useReaderFit'
import { fetchFavoriteIds, toggleFavorite } from '@/composables/useFavorites'
import { touchRecentView } from '@/composables/useRecentView'
import { fetchNode, fetchNodeImages, fetchProgress, saveProgress } from '@/api/nodes'
import type { ReaderFitMode, ReaderMode } from '@/types/reader'

const route = useRoute()
const router = useRouter()

const nodeId = computed(() => Number(route.params.nodeId))
const total = ref(0)
const page = ref(0)
const title = ref('')
const ready = ref(false)
const cacheVersion = ref(0)
const favoriteIds = ref<number[]>([])
const mode = ref<ReaderMode>(resolveReaderMode(route.query.mode as string | undefined))
const fit = ref<ReaderFitMode>(getStoredReaderFit())

const favorited = computed(() => favoriteIds.value.includes(nodeId.value))

watch(fit, (next) => saveReaderFit(next))

let saveTimer: ReturnType<typeof setTimeout> | null = null

const load = async () => {
  ready.value = false
  const id = nodeId.value
  const [nodeRes, imagesRes, progressRes, favIdsRes] = await Promise.all([
    fetchNode(id),
    fetchNodeImages(id),
    fetchProgress(id),
    fetchFavoriteIds(),
  ])
  favoriteIds.value = favIdsRes.data
  title.value = nodeRes.data.name
  total.value = imagesRes.data.total
  cacheVersion.value = nodeRes.data.dir_mtime ?? Date.now()

  const queryPage = route.query.page != null ? Number(route.query.page) : null
  const savedPage = progressRes.data.page_index
  const initial = queryPage ?? savedPage ?? 0
  page.value = Math.min(Math.max(initial, 0), Math.max(total.value - 1, 0))
  mode.value = resolveReaderMode(route.query.mode as string | undefined)
  ready.value = true
  touchRecentView(id)
}

const syncRoute = () => {
  router.replace({
    path: `/reader/${nodeId.value}`,
    query: { page: page.value, mode: mode.value },
  })
}

const persist = (index: number) => {
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    saveProgress(nodeId.value, index).catch(() => {})
  }, 300)
}

const onPageChange = (index: number) => {
  page.value = index
  syncRoute()
  persist(index)
}

const onModeChange = (next: ReaderMode) => {
  if (next === mode.value) return
  mode.value = next
  saveReaderMode(next)
  syncRoute()
}

const onToggleFavorite = async () => {
  const { data } = await toggleFavorite(nodeId.value)
  favoriteIds.value = data.favorited
    ? [...new Set([...favoriteIds.value, nodeId.value])]
    : favoriteIds.value.filter((id) => id !== nodeId.value)
}

const onClose = () => {
  persist(page.value)
  router.back()
}

watch(nodeId, load, { immediate: true })
</script>
