<template>
  <el-dialog v-model="visible" :title="title" width="420px" @closed="reset">
    <TagSelect v-model="selectedIds" :tags="selectableTags" placeholder="搜索或选择标签" />

    <div class="create-row">
      <el-input
        v-model="newName"
        placeholder="新标签名称"
        maxlength="32"
        @keyup.enter="onCreate"
      />
      <el-button :loading="creating" :disabled="!newName.trim()" @click="onCreate">创建</el-button>
    </div>

    <div v-if="existingTags.length" class="existing">
      <div class="existing-label">已有标签</div>
      <div class="existing-tags">
        <el-tag
          v-for="tag in existingTags"
          :key="tag.id"
          size="small"
          closable
          :disable-transitions="false"
          @close="onRemove(tag)"
        >
          {{ tag.name }}
        </el-tag>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" :disabled="!selectedIds.length" @click="onConfirm">
        添加
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createTag } from '@/api/tags'
import TagSelect from '@/components/TagSelect.vue'
import type { TagItem } from '@/types/tag'

const props = withDefaults(
  defineProps<{
    allTags: TagItem[]
    existingTags?: TagItem[]
    excludeTagIds?: number[]
    title?: string
    submitting?: boolean
  }>(),
  { existingTags: () => [], excludeTagIds: () => [], title: '标签', submitting: false },
)

const emit = defineEmits<{
  confirm: [tagIds: number[]]
  remove: [tagId: number]
  'tag-created': [tag: TagItem]
}>()

const visible = defineModel<boolean>({ default: false })

const selectedIds = ref<number[]>([])
const newName = ref('')
const creating = ref(false)

const excludeSet = computed(() => new Set(props.excludeTagIds))

const selectableTags = computed(() => props.allTags.filter((t) => !excludeSet.value.has(t.id)))

const reset = () => {
  selectedIds.value = []
  newName.value = ''
}

const onCreate = async () => {
  const name = newName.value.trim()
  if (!name) return

  creating.value = true
  try {
    const { data } = await createTag(name)
    emit('tag-created', data)
    if (!excludeSet.value.has(data.id) && !selectedIds.value.includes(data.id)) {
      selectedIds.value = [...selectedIds.value, data.id]
    }
    newName.value = ''
    ElMessage.success('标签已创建')
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    if (status === 409) {
      const existing = props.allTags.find((t) => t.name === name)
      if (existing && !excludeSet.value.has(existing.id) && !selectedIds.value.includes(existing.id)) {
        selectedIds.value = [...selectedIds.value, existing.id]
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

const onConfirm = () => {
  if (!selectedIds.value.length) return
  emit('confirm', [...selectedIds.value])
}

const onRemove = async (tag: TagItem) => {
  try {
    await ElMessageBox.confirm(`确定移除标签「${tag.name}」？`, '移除标签', {
      type: 'warning',
      confirmButtonText: '移除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  emit('remove', tag.id)
}
</script>

<style scoped>
.create-row {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.create-row .el-input {
  flex: 1;
}

.existing {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.existing-label {
  font-size: 13px;
  color: var(--app-text-muted);
  margin-bottom: 10px;
}

.existing-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
