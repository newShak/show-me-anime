<template>
  <div class="search-page">
    <header class="toolbar">
      <SearchBar :model-value="query" @search="onSearch" />
      <el-button @click="$router.push('/browse')">返回顶层</el-button>
    </header>

    <main class="content">
      <p v-if="query" class="summary">「{{ query }}」共 {{ total }} 个结果</p>
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

      <el-empty v-else-if="query" description="未找到匹配的相册" />
      <el-empty v-else description="输入关键词搜索相册" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SearchBar from '@/components/SearchBar.vue'
import { searchNodes } from '@/api/search'
import type { SearchResultItem } from '@/types/search'

const route = useRoute()
const router = useRouter()

const query = ref('')
const items = ref<SearchResultItem[]>([])
const total = ref(0)
const loading = ref(false)

const runSearch = async (q: string) => {
  query.value = q
  if (!q.trim()) {
    items.value = []
    total.value = 0
    return
  }
  loading.value = true
  try {
    const { data } = await searchNodes(q.trim())
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

const onSearch = (q: string) => {
  router.replace({ path: '/search', query: { q } })
}

const openNode = (item: SearchResultItem) => {
  router.push(`/browse/${item.id}`)
}

watch(
  () => route.query.q,
  (q) => {
    const text = typeof q === 'string' ? q : ''
    if (text) runSearch(text)
  },
  { immediate: true },
)
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
