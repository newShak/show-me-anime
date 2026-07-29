<template>
  <div class="browse">
    <header class="toolbar">
      <BreadcrumbNav :items="crumbs" @navigate="goTo" />
      <el-button type="primary" :loading="scanning" @click="onScan">扫描目录</el-button>
    </header>

    <div class="layout">
      <aside class="sidebar">
        <NodeTree @select="goTo" />
      </aside>

      <main class="content">
        <template v-if="currentNode && isAlbumView">
          <h2>{{ currentNode.name }}</h2>
          <ImageGrid :node-id="currentNode.id" :images="images" />
          <AlbumGrid v-if="nodes.length" :nodes="nodes" class="subfolders" @open="onOpenNode" />
        </template>
        <template v-else>
          <h2>{{ currentTitle }}</h2>
          <AlbumGrid :nodes="nodes" @open="onOpenNode" />
        </template>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AlbumGrid from '@/components/AlbumGrid.vue'
import BreadcrumbNav from '@/components/BreadcrumbNav.vue'
import ImageGrid from '@/components/ImageGrid.vue'
import NodeTree from '@/components/NodeTree.vue'
import { fetchNode, fetchNodeImages, fetchNodes, triggerScan } from '@/api/nodes'
import type { ImageItem, NodeItem } from '@/types/node'

type Crumb = { id: number | null; name: string }

const route = useRoute()
const router = useRouter()

const nodes = ref<NodeItem[]>([])
const images = ref<ImageItem[]>([])
const currentNode = ref<NodeItem | null>(null)
const crumbs = ref<Crumb[]>([{ id: null, name: '画廊' }])
const scanning = ref(false)

const nodeId = computed(() => {
  const raw = route.params.nodeId
  return raw ? Number(raw) : null
})

const isAlbumView = computed(
  () => currentNode.value != null && currentNode.value.node_type !== 'container',
)

const currentTitle = computed(() =>
  nodeId.value == null ? '全部相册' : currentNode.value?.name ?? '加载中...',
)

const loadCrumbs = async (id: number | null) => {
  const chain: Crumb[] = [{ id: null, name: '画廊' }]
  if (id == null) {
    crumbs.value = chain
    return
  }
  let cur = await fetchNode(id).then((r) => r.data)
  const stack: Crumb[] = []
  while (cur) {
    stack.unshift({ id: cur.id, name: cur.name })
    if (cur.parent_id == null) break
    cur = (await fetchNode(cur.parent_id)).data
  }
  crumbs.value = [...chain, ...stack]
}

const loadView = async (id: number | null) => {
  if (id == null) {
    currentNode.value = null
    nodes.value = (await fetchNodes()).data
    images.value = []
    crumbs.value = [{ id: null, name: '画廊' }]
    return
  }

  const node = (await fetchNode(id)).data
  currentNode.value = node
  await loadCrumbs(id)

  if (node.node_type === 'container') {
    nodes.value = (await fetchNodes(id)).data
    images.value = []
    return
  }

  images.value = (await fetchNodeImages(id)).data.items
  if (node.node_type === 'both') {
    nodes.value = (await fetchNodes(id)).data
  } else {
    nodes.value = []
  }
}

const goTo = (id: number | null) => {
  router.push(id == null ? '/browse' : `/browse/${id}`)
}

const onOpenNode = (node: NodeItem) => goTo(node.id)

const onScan = async () => {
  scanning.value = true
  try {
    const { data } = await triggerScan()
    ElMessage.success(`扫描完成：新增 ${data.added}，更新 ${data.updated}`)
    await loadView(nodeId.value)
  } catch {
    ElMessage.error('扫描失败')
  } finally {
    scanning.value = false
  }
}

watch(nodeId, (id) => loadView(id), { immediate: true })

onMounted(() => loadView(nodeId.value))
</script>

<style scoped>
.browse {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.layout {
  flex: 1;
  display: grid;
  grid-template-columns: 260px 1fr;
  min-height: 0;
}

.sidebar {
  border-right: 1px solid #ebeef5;
  padding: 12px;
  overflow: auto;
  background: #fff;
}

.content {
  padding: 20px 24px;
  overflow: auto;
}

h2 {
  margin: 0 0 16px;
  font-size: 18px;
}

.subfolders {
  margin-top: 24px;
}
</style>
