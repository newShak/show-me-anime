<template>
  <ImageViewer
    v-if="ready"
    :node-id="nodeId"
    :total="total"
    :page="page"
    :title="title"
    @close="onClose"
    @change="onPageChange"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ImageViewer from '@/components/ImageViewer.vue'
import { fetchNode, fetchNodeImages, fetchProgress, saveProgress } from '@/api/nodes'

const route = useRoute()
const router = useRouter()

const nodeId = computed(() => Number(route.params.nodeId))
const total = ref(0)
const page = ref(0)
const title = ref('')
const ready = ref(false)

let saveTimer: ReturnType<typeof setTimeout> | null = null

const load = async () => {
  ready.value = false
  const id = nodeId.value
  const [nodeRes, imagesRes, progressRes] = await Promise.all([
    fetchNode(id),
    fetchNodeImages(id),
    fetchProgress(id),
  ])
  title.value = nodeRes.data.name
  total.value = imagesRes.data.total

  const queryPage = route.query.page != null ? Number(route.query.page) : null
  const savedPage = progressRes.data.page_index
  const initial = queryPage ?? savedPage ?? 0
  page.value = Math.min(Math.max(initial, 0), Math.max(total.value - 1, 0))
  ready.value = true
}

const persist = (index: number) => {
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    saveProgress(nodeId.value, index).catch(() => {})
  }, 300)
}

const onPageChange = (index: number) => {
  page.value = index
  router.replace({ path: `/reader/${nodeId.value}`, query: { page: index } })
  persist(index)
}

const onClose = () => {
  persist(page.value)
  router.back()
}

watch(nodeId, load, { immediate: true })
</script>
