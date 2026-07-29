<template>
  <div v-if="images.length" class="grid">
    <div v-for="img in images" :key="img.index" class="item">
      <img :src="imageThumbUrl(nodeId, img.index)" loading="lazy" :alt="img.filename" />
      <span>{{ img.filename }}</span>
    </div>
  </div>
  <el-empty v-else description="相册为空" />
</template>

<script setup lang="ts">
import type { ImageItem } from '@/types/node'
import { imageThumbUrl } from '@/api/nodes'

defineProps<{ nodeId: number; images: ImageItem[] }>()
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

img {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  border-radius: 4px;
  background: #eef1f6;
}

span {
  font-size: 12px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
