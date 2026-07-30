<template>
  <div class="search-bar">
    <el-input
      v-model="keyword"
      clearable
      placeholder="搜索相册名、路径..."
      @keyup.enter="submit"
      @clear="emit('clear')"
    >
      <template #append>
        <el-button :icon="Search" @click="submit" />
      </template>
    </el-input>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'

const props = defineProps<{ modelValue?: string }>()
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
</style>
