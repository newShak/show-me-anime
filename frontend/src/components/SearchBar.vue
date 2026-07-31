<template>
  <div class="search-bar" :class="{ full }">
    <el-autocomplete
      v-if="showHistory"
      v-model="keyword"
      :fetch-suggestions="fetchSuggestions"
      clearable
      :placeholder="placeholder"
      size="large"
      :trigger-on-focus="true"
      :debounce="0"
      value-key="label"
      @select="onPick"
      @keyup.enter="flushSearch"
      @clear="onClear"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-autocomplete>
    <el-input
      v-else
      :model-value="keyword"
      clearable
      :placeholder="placeholder"
      size="large"
      @update:model-value="onInput"
      @keyup.enter="flushSearch"
      @clear="onClear"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'
import {
  filterHistory,
  formatHistoryLabel,
  type SearchHistoryItem,
} from '@/composables/useSearchHistory'
import type { TagItem } from '@/types/tag'

type SuggestItem = SearchHistoryItem & { label: string }

const props = withDefaults(
  defineProps<{
    modelValue?: string
    full?: boolean
    placeholder?: string
    showHistory?: boolean
    tags?: TagItem[]
  }>(),
  { full: false, placeholder: 'Search', showHistory: false },
)
const emit = defineEmits<{
  search: [q: string, commit?: boolean]
  clear: []
  pick: [item: SearchHistoryItem]
}>()

const keyword = ref(props.modelValue ?? '')
let timer: ReturnType<typeof setTimeout> | null = null

watch(
  () => props.modelValue,
  (v) => {
    if (v != null && v !== keyword.value) keyword.value = v
  },
)

watch(keyword, (v, prev) => {
  if (v === prev || !props.showHistory) return
  if (timer) clearTimeout(timer)
  timer = null
  if (!v.trim()) {
    emit('clear')
    return
  }
  scheduleSearch()
})

const tagNameOf = (id: number) => props.tags?.find((t) => t.id === id)?.name

const fetchSuggestions = (queryString: string, cb: (items: SuggestItem[]) => void) => {
  cb(
    filterHistory(queryString).map((item) => ({
      ...item,
      label: formatHistoryLabel(item, tagNameOf),
    })),
  )
}

const emitSearch = (commit = false) => {
  const q = keyword.value.trim()
  if (!q && !commit) return
  emit('search', q, commit)
}

const scheduleSearch = () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => emitSearch(false), 300)
}

const onInput = (v: string) => {
  keyword.value = v
  if (!v.trim()) {
    if (timer) clearTimeout(timer)
    emit('clear')
    return
  }
  scheduleSearch()
}

const flushSearch = () => {
  if (timer) clearTimeout(timer)
  emitSearch(true)
}

const onClear = () => {
  keyword.value = ''
  if (timer) clearTimeout(timer)
  emit('clear')
}

const onPick = (item: SuggestItem) => {
  if (timer) clearTimeout(timer)
  keyword.value = item.q
  emit('pick', {
    q: item.q,
    tagIds: item.tagIds,
    tagMode: item.tagMode,
    at: item.at,
  })
  emit('search', item.q, true)
}
</script>

<style scoped>
.search-bar {
  flex: 1;
  max-width: 420px;
}

.search-bar.full {
  flex: none;
  max-width: none;
  width: 100%;
}

.search-bar :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--app-border) inset;
}

.search-bar :deep(.el-input__wrapper:hover),
.search-bar :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset;
}
</style>
