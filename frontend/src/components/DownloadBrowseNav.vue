<template>
  <div class="browse-nav">
    <div class="nav-row">
      <el-button
        v-for="item in nav"
        :key="item.label"
        :type="activeCate === item.cate_id ? 'primary' : 'default'"
        size="small"
        @click="emit('select', item.cate_id)"
      >
        {{ item.label }}
      </el-button>
    </div>
    <div v-if="activeGroup?.children.length" class="sub-row">
      <el-button
        v-for="child in activeGroup.children"
        :key="child.cate_id ?? child.label"
        :type="activeCate === child.cate_id ? 'primary' : 'default'"
        link
        size="small"
        @click="emit('select', child.cate_id)"
      >
        {{ child.label }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BrowseNavItem } from '@/types/download'

const props = defineProps<{
  nav: BrowseNavItem[]
  activeCate: number | null
}>()

const emit = defineEmits<{
  select: [cateId: number | null]
}>()

const activeGroup = computed(() => {
  if (props.activeCate == null) return null
  return props.nav.find(
    (item) => item.cate_id === props.activeCate || item.children.some((c) => c.cate_id === props.activeCate),
  )
})
</script>

<style scoped>
.browse-nav {
  margin-bottom: 20px;
}

.nav-row,
.sub-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sub-row {
  margin-top: 10px;
  padding-left: 4px;
}
</style>
