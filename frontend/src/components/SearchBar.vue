<template>
  <div class="search-bar" :class="{ full }">
    <el-input
      v-model="keyword"
      clearable
      :placeholder="placeholder"
      size="large"
      @keyup.enter="submit"
      @clear="emit('clear')"
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

watch(
  () => props.modelValue,
  (v) => {
    if (v != null) keyword.value = v
  },
)

const submit = () => {
  const q = keyword.value.trim()
  if (q) emit('search', q)
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
