<template>
  <el-breadcrumb separator="/">
    <el-breadcrumb-item v-for="item in items" :key="item.id ?? 'root'">
      <a v-if="item.id != null" href="#" @click.prevent="emit('navigate', item.id)">
        {{ item.name }}
      </a>
      <span v-else>{{ item.name }}</span>
    </el-breadcrumb-item>
  </el-breadcrumb>
</template>

<script setup lang="ts">
export type Crumb = { id: number | null; name: string }

defineProps<{ items: Crumb[] }>()
const emit = defineEmits<{ navigate: [id: number | null] }>()
</script>

<style scoped>
a {
  color: var(--el-color-primary);
  text-decoration: none;
}
</style>
