<template>
  <el-card shadow="never" class="panel">
    <div class="tag-add">
      <el-input v-model="newTag" placeholder="新标签名" @keyup.enter="onAddTag" />
      <el-button type="primary" :loading="addingTag" @click="onAddTag">添加</el-button>
    </div>
    <el-table :data="tags" size="small" empty-text="暂无标签" v-loading="loading">
      <el-table-column prop="name" label="名称" show-overflow-tooltip />
      <el-table-column label="操作" width="72" align="center">
        <template #default="{ row }">
          <el-button link type="danger" @click="onDeleteTag(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-if="total > 0"
      class="pagination"
      layout="total, prev, pager, next"
      :total="total"
      :current-page="page"
      :page-size="pageSize"
      small
      @current-change="onPageChange"
    />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createTag, deleteTag, fetchTagsPage } from '@/api/tags'
import type { TagItem } from '@/types/tag'

const tags = ref<TagItem[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)
const newTag = ref('')
const addingTag = ref(false)

const load = async (p = page.value) => {
  loading.value = true
  try {
    const { data } = await fetchTagsPage(p, pageSize.value)
    tags.value = data.items
    total.value = data.total
    page.value = data.page
  } finally {
    loading.value = false
  }
}

const onPageChange = (p: number) => {
  page.value = p
  load(p)
}

const onAddTag = async () => {
  const name = newTag.value.trim()
  if (!name) return
  addingTag.value = true
  try {
    await createTag(name)
    newTag.value = ''
    await load(1)
    ElMessage.success('标签已添加')
  } catch {
    ElMessage.error('添加失败')
  } finally {
    addingTag.value = false
  }
}

const onDeleteTag = async (id: number) => {
  try {
    await ElMessageBox.confirm('删除后节点上的该标签也会移除', '确认删除')
    await deleteTag(id)
    const p = tags.value.length === 1 && page.value > 1 ? page.value - 1 : page.value
    await load(p)
    ElMessage.success('已删除')
  } catch {
    /* cancel */
  }
}

onMounted(load)
</script>

<style scoped>
.panel {
  max-width: 640px;
  border: 1px solid var(--el-border-color-lighter);
}

.panel :deep(.el-card__body) {
  padding: 16px;
}

.tag-add {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
