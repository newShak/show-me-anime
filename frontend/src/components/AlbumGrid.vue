<template>
  <div v-if="nodes.length" class="grid">
    <el-card
      v-for="node in nodes"
      :key="node.id"
      shadow="hover"
      class="card"
      @click="emit('open', node)"
    >
      <img
        v-if="node.node_type !== 'container'"
        :src="coverThumbUrl(node.id)"
        class="cover"
        loading="lazy"
        alt=""
      />
      <div v-else class="cover placeholder">📁</div>
      <div class="meta">
        <div class="name">{{ node.name }}</div>
        <div class="sub">{{ node.image_count ? `${node.image_count} 张` : '文件夹' }}</div>
      </div>
    </el-card>
  </div>
  <el-empty v-else description="暂无内容，请先扫描或添加文件夹" />
</template>

<script setup lang="ts">
import type { NodeItem } from '@/types/node'
import { coverThumbUrl } from '@/api/nodes'

defineProps<{ nodes: NodeItem[] }>()
const emit = defineEmits<{ open: [node: NodeItem] }>()
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.card {
  cursor: pointer;
  overflow: hidden;
}

.cover {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  display: block;
  background: #eef1f6;
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
}

.meta {
  padding: 8px 0 0;
}

.name {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sub {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
</style>
