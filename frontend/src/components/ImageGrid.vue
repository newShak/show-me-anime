<template>
  <div v-if="images.length" class="grid">
    <article v-for="img in images" :key="img.index" class="card" @click="emit('open', img.index)">
      <img :src="imageThumbUrl(nodeId, img.index)" loading="lazy" :alt="img.filename" />
      <span>{{ img.filename }}</span>
    </article>
  </div>
  <el-empty v-else description="相册为空" />
</template>

<script setup lang="ts">
import type { ImageItem } from '@/types/node'
import { imageThumbUrl } from '@/api/nodes'

defineProps<{ nodeId: number; images: ImageItem[] }>()
const emit = defineEmits<{ open: [index: number] }>()
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
  margin-bottom: 8px;
}

.card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  cursor: pointer;
}

img {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  border-radius: 8px;
  background: var(--app-cover-bg);
  box-shadow: var(--app-card-shadow);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.card:hover img {
  transform: translateY(-2px);
  box-shadow: var(--app-card-shadow-hover);
}

span {
  font-size: 12px;
  color: var(--app-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0 2px;
}
</style>
