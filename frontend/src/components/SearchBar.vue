<template>
  <div class="search-bar" :class="{ full }">
    <el-input
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

const props = withDefaults(
  defineProps<{ modelValue?: string; full?: boolean; placeholder?: string }>(),
  { full: false, placeholder: 'Search' },
)
const emit = defineEmits<{ search: [q: string]; clear: [] }>()

const keyword = ref(props.modelValue ?? '')
let timer: ReturnType<typeof setTimeout> | null = null

watch(
  () => props.modelValue,
  (v) => {
    if (v != null && v !== keyword.value) keyword.value = v
  },
)

const emitSearch = () => emit('search', keyword.value.trim())

const scheduleSearch = () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(emitSearch, 300)
}

const onInput = (v: string) => {
  keyword.value = v
  scheduleSearch()
}

const flushSearch = () => {
  if (timer) clearTimeout(timer)
  emitSearch()
}

const onClear = () => {
  keyword.value = ''
  emit('clear')
  flushSearch()
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
