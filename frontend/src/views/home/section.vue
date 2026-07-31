<template>
  <div class="section-page">
    <header class="head">
      <el-button text class="back" @click="$router.push('/')">← 返回首页</el-button>
      <h1>{{ title }}</h1>
      <span v-if="total" class="count">共 {{ total }} 个</span>
    </header>

    <el-skeleton v-if="loading" :rows="4" animated />

    <template v-else-if="nodes.length">
      <AlbumGrid
        :nodes="nodes"
        :node-tags="nodeTagsMap"
        :progress-map="progressPercentMap"
        :favorite-ids="favoriteIds"
        :show-menu="false"
        @open="openNode"
        @toggle-favorite="onToggleFavorite"
      />
      <el-pagination
        v-if="isFavorites && total > pageSize"
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        class="pager"
        @current-change="load"
      />
    </template>

    <el-empty v-else :description="emptyText" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AlbumGrid from '@/components/AlbumGrid.vue'
import { fetchFavorites, touchRecentView, toggleFavorite as apiToggleFavorite } from '@/api/library'
import { fetchRecentViewed } from '@/composables/useRecentView'
import { useNodeGridMeta } from '@/composables/useNodeGridMeta'
import { FAVORITES_PAGE_SIZE } from '@/constants/home'
import type { NodeItem } from '@/types/node'

type SectionKind = 'viewed' | 'favorites'

const route = useRoute()
const router = useRouter()
const kind = computed(() => route.meta.section as SectionKind)

const title = computed(() => {
  if (kind.value === 'viewed') return '最近浏览'
  return '我的最爱'
})

const emptyText = computed(() => {
  if (kind.value === 'viewed') return '还没有浏览记录'
  return '点击卡片上的星标收藏相册'
})

const isFavorites = computed(() => kind.value === 'favorites')
const pageSize = FAVORITES_PAGE_SIZE

const loading = ref(true)
const nodes = ref<NodeItem[]>([])
const total = ref(0)
const page = ref(1)

const { nodeTagsMap, progressPercentMap, favoriteIds, loadFavoriteIds, loadMeta } = useNodeGridMeta()

const load = async () => {
  loading.value = true
  try {
    if (kind.value === 'viewed') {
      const { data } = await fetchRecentViewed()
      nodes.value = data
      total.value = data.length
    } else {
      const { data } = await fetchFavorites((page.value - 1) * pageSize, pageSize)
      nodes.value = data.items
      total.value = data.total
    }
    await loadMeta(nodes.value)
  } finally {
    loading.value = false
  }
}

const openNode = (node: NodeItem) => {
  touchRecentView(node.id)
  router.push(`/browse/${node.id}`)
}

const onToggleFavorite = async (node: NodeItem) => {
  const { data } = await apiToggleFavorite(node.id)
  favoriteIds.value = data.favorited
    ? [...new Set([...favoriteIds.value, node.id])]
    : favoriteIds.value.filter((id) => id !== node.id)
  if (!isFavorites.value || data.favorited) return
  nodes.value = nodes.value.filter((n) => n.id !== node.id)
  total.value = Math.max(0, total.value - 1)
  if (total.value === 0) page.value = 1
  else if (!nodes.value.length && page.value > 1) {
    page.value -= 1
    await load()
  }
}

onMounted(async () => {
  await loadFavoriteIds()
  await load()
})
</script>

<style scoped>
.section-page {
  max-width: var(--app-page-width);
  margin: 0 auto;
  padding: 32px 32px 60px;
}

.head {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 24px;
}

.back {
  padding-left: 0;
  margin-right: 4px;
}

h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.count {
  font-size: 13px;
  color: var(--app-text-muted);
}

.pager {
  margin-top: 32px;
  justify-content: center;
}
</style>
