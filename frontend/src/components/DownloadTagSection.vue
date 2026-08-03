<template>
  <div class="download-tags">
    <div v-if="showRemote && remoteTags.length" class="section">
      <div class="section-head">
        <span class="section-label">外站标签</span>
        <div class="section-actions">
          <el-button link type="primary" size="small" @click="selectAllRemote">全选</el-button>
          <el-button link size="small" @click="clearRemote">全不选</el-button>
        </div>
      </div>
      <el-checkbox-group v-model="selectedRemote" class="remote-group">
        <el-checkbox v-for="tag in remoteTags" :key="tag" :label="tag">{{ tag }}</el-checkbox>
      </el-checkbox-group>
      <p class="section-hint">勾选的外站标签将在下载完成后导入为本地标签</p>
    </div>

    <div class="section">
      <div class="section-head">
        <span class="section-label">本地标签</span>
      </div>
      <TagSelect v-model="selectedLocalIds" :tags="allTags" placeholder="搜索或选择本地标签" />
      <div class="create-row">
        <el-input
          v-model="newName"
          placeholder="新标签名称"
          maxlength="32"
          @keyup.enter="onCreate"
        />
        <el-button :loading="creating" :disabled="!newName.trim()" @click="onCreate">创建</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createTag, fetchTags } from '@/api/tags'
import TagSelect from '@/components/TagSelect.vue'
import type { TagItem } from '@/types/tag'

export type DownloadTagPayload = {
  tag_ids: number[]
  import_remote_tags: string[]
}

const props = withDefaults(
  defineProps<{
    remoteTags?: string[]
    showRemote?: boolean
  }>(),
  { remoteTags: () => [], showRemote: true },
)

const allTags = ref<TagItem[]>([])
const selectedRemote = ref<string[]>([])
const selectedLocalIds = ref<number[]>([])
const newName = ref('')
const creating = ref(false)

const loadTags = async () => {
  try {
    const { data } = await fetchTags()
    allTags.value = data
  } catch {
    ElMessage.error('加载标签失败')
  }
}

const selectAllRemote = () => {
  selectedRemote.value = [...props.remoteTags]
}

const clearRemote = () => {
  selectedRemote.value = []
}

const onCreate = async () => {
  const name = newName.value.trim()
  if (!name) return
  creating.value = true
  try {
    const { data } = await createTag(name)
    if (!allTags.value.some((t) => t.id === data.id)) {
      allTags.value = [...allTags.value, data].sort((a, b) => a.name.localeCompare(b.name))
    }
    if (!selectedLocalIds.value.includes(data.id)) {
      selectedLocalIds.value = [...selectedLocalIds.value, data.id]
    }
    newName.value = ''
    ElMessage.success('标签已创建')
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    if (status === 409) {
      const existing = allTags.value.find((t) => t.name === name)
      if (existing && !selectedLocalIds.value.includes(existing.id)) {
        selectedLocalIds.value = [...selectedLocalIds.value, existing.id]
      }
      newName.value = ''
      ElMessage.warning('标签已存在，已选中')
      return
    }
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

const getPayload = (): DownloadTagPayload => ({
  tag_ids: [...selectedLocalIds.value],
  import_remote_tags: [...selectedRemote.value],
})

const reset = () => {
  selectedRemote.value = []
  selectedLocalIds.value = []
  newName.value = ''
}

watch(
  () => props.remoteTags,
  () => {
    selectedRemote.value = []
  },
)

loadTags()

defineExpose({ getPayload, reset })
</script>

<style scoped>
.download-tags {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.section-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.section-hint {
  margin: 0;
  font-size: 12px;
  color: var(--app-text-muted);
  line-height: 1.4;
}

.remote-group {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
}

.create-row {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.create-row .el-input {
  flex: 1;
}
</style>
