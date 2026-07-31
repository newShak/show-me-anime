<template>
  <div class="recent-added-page">
    <header class="head">
      <el-button text class="back" @click="$router.push('/')">← 返回首页</el-button>
      <h1>最近添加</h1>
      <span v-if="totalAlbums" class="count">共 {{ totalAlbums }} 个</span>
      <el-segmented v-model="range" :options="RECENT_ADDED_RANGE_OPTIONS" size="small" @change="onRangeChange" />
    </header>

    <el-skeleton v-if="loading" :rows="4" animated />

    <template v-else-if="pagedGroups.length">
      <section v-for="group in pagedGroups" :key="group.date" class="day-group">
        <div class="day-head">
          <h2>{{ group.label }}</h2>
          <span class="day-count">{{ group.total }} 个</span>
        </div>
        <AlbumGrid
          :nodes="group.visibleItems"
          :node-tags="nodeTagsMap"
          :progress-map="progressPercentMap"
          :favorite-ids="favoriteIds"
          :show-menu="false"
          @open="openNode"
          @toggle-favorite="onToggleFavorite"
        />
        <div v-if="group.hasMore" class="group-more">
          <el-button text :loading="group.loading" @click="loadMoreGroup(group.date)">加载更多</el-button>
        </div>
      </section>

      <el-pagination
        v-if="totalDays > daysPerPage"
        v-model:current-page="dayPage"
        :page-size="daysPerPage"
        :total="totalDays"
        layout="prev, pager, next, total"
        class="pager"
        @current-change="onDayPageChange"
      />
    </template>

    <el-empty v-else description="该时间范围内暂无新相册" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AlbumGrid from '@/components/AlbumGrid.vue'
import { fetchRecentNodes } from '@/api/nodes'
import { touchRecentView, toggleFavorite as apiToggleFavorite } from '@/api/library'
import { useNodeGridMeta } from '@/composables/useNodeGridMeta'
import {
  RECENT_ADDED_RANGE_OPTIONS,
  recentAddedDayBounds,
  recentAddedDayKey,
  recentAddedDayLabel,
  recentAddedRangeBounds,
  type RecentAddedRange,
} from '@/composables/useRecentAddedRange'
import {
  RECENT_ADDED_DAYS_PER_PAGE,
  RECENT_ADDED_FETCH_LIMIT,
  RECENT_ADDED_GROUP_SIZE,
} from '@/constants/home'
import type { NodeItem } from '@/types/node'

type DayGroupState = {
  date: string
  label: string
  total: number
  items: NodeItem[]
  visibleCount: number
  loading: boolean
}

const router = useRouter()
const range = ref<RecentAddedRange>('week')
const loading = ref(true)
const totalAlbums = ref(0)
const dayGroups = ref<DayGroupState[]>([])
const dayPage = ref(1)
const daysPerPage = RECENT_ADDED_DAYS_PER_PAGE

const { nodeTagsMap, progressPercentMap, favoriteIds, loadFavoriteIds, loadMeta } = useNodeGridMeta()

const totalDays = computed(() => dayGroups.value.length)

const pagedGroups = computed(() => {
  const start = (dayPage.value - 1) * daysPerPage
  return dayGroups.value.slice(start, start + daysPerPage).map((g) => ({
    ...g,
    visibleItems: g.items.slice(0, g.visibleCount),
    hasMore: g.visibleCount < g.total,
  }))
})

const buildGroups = (items: NodeItem[]) => {
  const map = new Map<string, NodeItem[]>()
  for (const item of items) {
    const ts = item.created_at ?? 0
    const key = recentAddedDayKey(ts)
    const list = map.get(key) ?? []
    list.push(item)
    map.set(key, list)
  }
  return [...map.entries()]
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([date, nodes]) => ({
      date,
      label: recentAddedDayLabel(date),
      total: nodes.length,
      items: nodes,
      visibleCount: Math.min(RECENT_ADDED_GROUP_SIZE, nodes.length),
      loading: false,
    }))
}

const loadRange = async () => {
  loading.value = true
  dayPage.value = 1
  try {
    const { since, until } = recentAddedRangeBounds(range.value)
    const { data } = await fetchRecentNodes({
      since,
      until,
      offset: 0,
      limit: RECENT_ADDED_FETCH_LIMIT,
    })
    totalAlbums.value = data.total
    dayGroups.value = buildGroups(data.items)
    await loadMeta(data.items)
  } finally {
    loading.value = false
  }
}

const onRangeChange = () => loadRange()

const onDayPageChange = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const findGroup = (date: string) => dayGroups.value.find((g) => g.date === date)

const loadMoreGroup = async (date: string) => {
  const group = findGroup(date)
  if (!group || group.loading) return

  if (group.visibleCount < group.items.length) {
    group.visibleCount = Math.min(group.visibleCount + RECENT_ADDED_GROUP_SIZE, group.items.length)
    return
  }

  if (group.items.length >= group.total) return

  group.loading = true
  try {
    const { since, until } = recentAddedDayBounds(date)
    const { data } = await fetchRecentNodes({
      since,
      until,
      offset: group.items.length,
      limit: RECENT_ADDED_GROUP_SIZE,
    })
    if (data.items.length) {
      group.items.push(...data.items)
      group.total = data.total
      group.visibleCount = Math.min(group.visibleCount + RECENT_ADDED_GROUP_SIZE, group.items.length)
      await loadMeta(data.items)
    } else {
      group.total = group.items.length
    }
  } finally {
    group.loading = false
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
}

watch(range, () => {
  /* segmented @change 已触发；保留 watch 便于后续 query 同步 */
})

onMounted(async () => {
  await loadFavoriteIds()
  await loadRange()
})
</script>

<style scoped>
.recent-added-page {
  max-width: var(--app-page-width);
  margin: 0 auto;
  padding: 32px 32px 60px;
}

.head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 28px;
}

.back {
  padding-left: 0;
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

.head :deep(.el-segmented) {
  margin-left: auto;
}

.day-group + .day-group {
  margin-top: 36px;
}

.day-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 16px;
}

.day-head h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.day-count {
  font-size: 13px;
  color: var(--app-text-muted);
}

.group-more {
  margin-top: 12px;
  text-align: center;
}

.pager {
  margin-top: 36px;
  justify-content: center;
}
</style>
