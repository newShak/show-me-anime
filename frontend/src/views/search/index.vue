<template>
  <div class="search-page">
    <header class="toolbar">
      <SearchBar :model-value="query" @search="onTextSearch" />
      <TagSelect
        v-model="selectedTagIds"
        :tags="allTags"
        clearable
        collapse-tags
        placeholder="按标签筛选"
        width="220px"
        @change="onTagChange"
      />
      <el-button @click="$router.push('/browse')">返回顶层</el-button>
    </header>

    <main class="content">
      <p v-if="hasFilter" class="summary">{{ summaryText }} · 共 {{ total }} 个结果</p>
      <el-skeleton v-if="loading" :rows="4" animated />

      <div v-else-if="items.length" class="list">
        <el-card
          v-for="item in items"
          :key="item.id"
          shadow="hover"
          class="item"
          @click="openNode(item)"
        >
          <div class="name">{{ item.name }}</div>
          <div class="path">{{ item.path || '根目录' }}</div>
          <div class="meta">
            <el-tag size="small">{{ item.node_type }}</el-tag>
            <span v-if="item.image_count">{{ item.image_count }} 张</span>
          </div>
        </el-card>
      </div>

      <el-empty v-else-if="hasFilter" description="未找到匹配的相册" />
      <el-empty v-else description="输入关键词或选择标签搜索相册" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SearchBar from '@/components/SearchBar.vue'
import TagSelect from '@/components/TagSelect.vue'
import { searchNodes } from '@/api/search'
import { fetchTags } from '@/api/tags'
import type { SearchResultItem } from '@/types/search'
import type { TagItem } from '@/types/tag'

const route = useRoute()
const router = useRouter()

const query = ref('')
const selectedTagIds = ref<number[]>([])
const allTags = ref<TagItem[]>([])
const items = ref<SearchResultItem[]>([])
const total = ref(0)
const loading = ref(false)

const hasFilter = computed(() => !!query.value.trim() || selectedTagIds.value.length > 0)

const summaryText = computed(() => {
  const parts: string[] = []
  if (query.value.trim()) parts.push(`关键词「${query.value.trim()}」`)
  if (selectedTagIds.value.length) {
    const names = allTags.value
      .filter((t) => selectedTagIds.value.includes(t.id))
      .map((t) => t.name)
    parts.push(`标签「${names.join(' / ')}」`)
  }
  return parts.join('，')
})

const syncRoute = () => {
  const next: Record<string, string> = {}
  if (query.value.trim()) next.q = query.value.trim()
  if (selectedTagIds.value.length) next.tags = selectedTagIds.value.join(',')
  router.replace({ path: '/search', query: next })
}

const runSearch = async () => {
  const q = query.value.trim()
  const tagIds = selectedTagIds.value
  if (!q && !tagIds.length) {
    items.value = []
    total.value = 0
    return
  }
  loading.value = true
  try {
    const { data } = await searchNodes({ q: q || undefined, tagIds })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

const onTextSearch = (q: string) => {
  query.value = q
  syncRoute()
}

const onTagChange = () => {
  syncRoute()
}

const openNode = (item: SearchResultItem) => {
  router.push(`/browse/${item.id}`)
}

const parseTagIds = (raw: unknown) => {
  const text = typeof raw === 'string' ? raw : ''
  return text.split(',').flatMap((part) => {
    const n = Number(part.trim())
    return Number.isInteger(n) && n > 0 ? [n] : []
  })
}

watch(
  () => [route.query.q, route.query.tags] as const,
  ([q, tags]) => {
    query.value = typeof q === 'string' ? q : ''
    selectedTagIds.value = parseTagIds(tags)
    runSearch()
  },
  { immediate: true },
)

onMounted(async () => {
  allTags.value = (await fetchTags()).data
})
</script>

<style scoped>
.search-page {
  min-height: 100vh;
  background: var(--app-bg);
}

.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 16px 24px;
  background: var(--app-surface);
  border-bottom: 1px solid var(--app-border);
}

.tag-filter {
  width: 220px;
  flex-shrink: 0;
}

.content {
  max-width: 960px;
  margin: 0 auto;
  padding: 20px 24px;
}

.summary {
  margin: 0 0 16px;
  color: var(--app-text-secondary);
}

.list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.item {
  cursor: pointer;
}

.name {
  font-weight: 600;
  font-size: 16px;
}

.path {
  color: var(--app-text-muted);
  font-size: 13px;
  margin-top: 4px;
}

.meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--app-text-muted);
}
</style>
