<template>
  <el-breadcrumb separator="/" class="crumb">
    <el-breadcrumb-item v-for="item in items" :key="item.id ?? 'root'">
      <a href="#" @click.prevent="emit('navigate', item.id)">{{ item.name }}</a>
    </el-breadcrumb-item>
  </el-breadcrumb>
</template>

<script setup lang="ts">
export type Crumb = { id: number | null; name: string }

defineProps<{ items: Crumb[] }>()
const emit = defineEmits<{ navigate: [id: number | null] }>()
</script>

<style scoped>
.crumb {
  font-size: 13px;
}

.crumb a {
  color: var(--app-text-muted);
  text-decoration: none;
}

.crumb a:hover {
  color: var(--el-color-primary);
}

.crumb :deep(.el-breadcrumb__separator) {
  color: var(--app-text-muted);
}
</style>
