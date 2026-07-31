<template>
  <div class="home">
    <section v-for="block in blocks" :key="block.key" class="section">
      <div class="section-head">
        <h2>{{ block.title }}</h2>
        <span v-if="block.total" class="count">{{ block.total }}</span>
        <router-link :to="block.moreTo" class="more">更多</router-link>
      </div>
      <el-skeleton v-if="loading" :rows="2" animated />
      <AlbumGrid
        v-else-if="block.nodes.length"
        :nodes="block.nodes"
        :node-tags="nodeTagsMap"
        :progress-map="progressPercentMap"
        :favorite-ids="favoriteIds"
        :show-menu="false"
        @open="openNode"
        @toggle-favorite="onToggleFavorite"
      />
      <el-empty v-else :description="block.empty" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AlbumGrid from '@/components/AlbumGrid.vue'
import { fetchRecentNodes } from '@/api/nodes'
import { fetchFavorites, touchRecentView } from '@/api/library'
import { fetchRecentViewed } from '@/composables/useRecentView'
import { toggleFavorite } from '@/composables/useFavorites'
import { useNodeGridMeta } from '@/composables/useNodeGridMeta'
import { HOME_PREVIEW_COUNT } from '@/constants/home'
import type { NodeItem } from '@/types/node'

const router = useRouter()
const { nodeTagsMap, progressPercentMap, favoriteIds, loadFavoriteIds, loadMeta } = useNodeGridMeta()

const loading = ref(true)
const recentAdded = ref<NodeItem[]>([])
const recentViewed = ref<NodeItem[]>([])
const favorites = ref<NodeItem[]>([])
const favTotal = ref(0)
const addedTotal = ref(0)
const viewedTotal = ref(0)

const blocks = computed(() => [
  {
    key: 'added',
    title: '最近添加',
    nodes: recentAdded.value,
    total: addedTotal.value,
    empty: '暂无新相册',
    moreTo: '/recent-added',
  },
  {
    key: 'viewed',
    title: '最近浏览',
    nodes: recentViewed.value,
    total: viewedTotal.value,
    empty: '还没有浏览记录',
    moreTo: '/recent-viewed',
  },
  {
    key: 'fav',
    title: '我的最爱',
    nodes: favorites.value,
    total: favTotal.value,
    empty: '点击卡片上的星标收藏相册',
    moreTo: '/favorites',
  },
])

const load = async () => {
  loading.value = true
  try {
    const [addedRes, viewedRes, favRes] = await Promise.all([
      fetchRecentNodes(),
      fetchRecentViewed(),
      fetchFavorites(0, HOME_PREVIEW_COUNT),
      loadFavoriteIds(),
    ])
    addedTotal.value = addedRes.data.total
    viewedTotal.value = viewedRes.data.length
    recentAdded.value = addedRes.data.items.slice(0, HOME_PREVIEW_COUNT)
    recentViewed.value = viewedRes.data.slice(0, HOME_PREVIEW_COUNT)
    favTotal.value = favRes.data.total
    favorites.value = favRes.data.items.slice(0, HOME_PREVIEW_COUNT)
    await loadMeta([...recentAdded.value, ...recentViewed.value, ...favorites.value])
  } finally {
    loading.value = false
  }
}

const openNode = (node: NodeItem) => {
  touchRecentView(node.id)
  router.push(`/browse/${node.id}`)
}

const onToggleFavorite = async (node: NodeItem) => {
  const { data } = await toggleFavorite(node.id)
  favoriteIds.value = data.favorited
    ? [...new Set([...favoriteIds.value, node.id])]
    : favoriteIds.value.filter((id) => id !== node.id)
  if (data.favorited) {
    favTotal.value += 1
    favorites.value = [...favorites.value.filter((n) => n.id !== node.id), node].slice(0, HOME_PREVIEW_COUNT)
  } else {
    favTotal.value = Math.max(0, favTotal.value - 1)
    favorites.value = favorites.value.filter((n) => n.id !== node.id)
  }
}

onMounted(load)
</script>

<style scoped>
.home {
  max-width: var(--app-page-width);
  margin: 0 auto;
  padding: 32px 32px 60px;
}

.section + .section {
  margin-top: 40px;
}

.section-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 20px;
}

h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.count {
  font-size: 13px;
  color: var(--app-text-muted);
}

.more {
  margin-left: auto;
  font-size: 13px;
  color: var(--el-color-primary);
  text-decoration: none;
}

.more:hover {
  opacity: 0.85;
}
</style>
