<template>
  <el-dialog v-model="visible" title="编辑节点" width="600px" @closed="emit('closed')">
    <el-form v-if="node" label-width="88px">
      <el-form-item label="名称">
        <el-input :model-value="node.name" disabled />
      </el-form-item>
      <el-form-item label="类型">
        <el-select v-model="form.node_type" style="width: 100%">
          <el-option label="容器" value="container" />
          <el-option label="相册" value="album" />
          <el-option label="混合" value="both" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="showCoverPicker" label="封面">
        <div class="cover-picker">
          <div class="cover-preview" :class="{ empty: !previewUrl }">
            <img v-if="previewUrl" :src="previewUrl" alt="" />
            <span v-else-if="form.cover_choice === '__auto__'">自动跟随子项</span>
            <span v-else>选择封面预览</span>
          </div>
          <div class="cover-options">
            <button
              v-if="showAutoCover"
              type="button"
              class="cover-opt"
              :class="{ active: form.cover_choice === '__auto__' }"
              @click="form.cover_choice = '__auto__'"
            >
              <div class="cover-opt-thumb auto">自动</div>
              <span class="cover-opt-label">跟随子项</span>
            </button>
            <button
              v-for="img in images"
              :key="`local-${img.index}`"
              type="button"
              class="cover-opt"
              :class="{ active: form.cover_choice === `local:${img.index}` }"
              @click="form.cover_choice = `local:${img.index}`"
            >
              <img :src="imageThumbUrl(node.id, img.index)" class="cover-opt-thumb" alt="" loading="lazy" />
              <span class="cover-opt-label">{{ img.filename }}</span>
            </button>
            <button
              v-for="item in candidates"
              :key="item.value"
              type="button"
              class="cover-opt"
              :class="{ active: form.cover_choice === item.value }"
              @click="form.cover_choice = item.value"
            >
              <img
                :src="coverThumbUrl(item.source_node_id)"
                class="cover-opt-thumb"
                alt=""
                loading="lazy"
              />
              <span class="cover-opt-label">{{ item.label }}</span>
            </button>
          </div>
        </div>
      </el-form-item>
      <el-form-item label="标签">
        <TagSelect v-model="form.tag_ids" :tags="allTags" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { coverThumbUrl, fetchCoverCandidates, fetchNodeImages, imageThumbUrl, patchNode } from '@/api/nodes'
import TagSelect from '@/components/TagSelect.vue'
import { fetchNodeTags, fetchTags, setNodeTags } from '@/api/tags'
import type { CoverCandidate, ImageItem, NodeItem } from '@/types/node'
import type { TagItem } from '@/types/tag'

const props = defineProps<{ node: NodeItem | null }>()
const emit = defineEmits<{ saved: [node: NodeItem]; closed: [] }>()

const visible = defineModel<boolean>({ default: false })

const saving = ref(false)
const images = ref<ImageItem[]>([])
const candidates = ref<CoverCandidate[]>([])
const allTags = ref<TagItem[]>([])
const form = ref({
  node_type: 'album',
  cover_choice: undefined as string | undefined,
  tag_ids: [] as number[],
})

const showAutoCover = computed(
  () => form.value.node_type === 'container' || form.value.node_type === 'both',
)
const showCoverPicker = computed(
  () => showAutoCover.value || images.value.length > 0 || candidates.value.length > 0,
)

const previewUrl = computed(() => {
  const node = props.node
  const choice = form.value.cover_choice
  if (!node || !choice) return ''

  if (choice === '__auto__') {
    return node.cover_rel_path ? coverThumbUrl(node.id, node.cover_rel_path) : ''
  }
  if (choice.startsWith('local:')) {
    return imageThumbUrl(node.id, Number(choice.slice(6)))
  }
  const cand = candidates.value.find((c) => c.value === choice)
  return cand ? coverThumbUrl(cand.source_node_id) : ''
})

const load = async (node: NodeItem) => {
  form.value.node_type = node.node_type
  form.value.cover_choice = undefined
  form.value.tag_ids = []

  const needImages = node.node_type !== 'container'
  const needCandidates = node.node_type !== 'album'

  const [imgRes, candRes, tagRes, nodeTagRes] = await Promise.all([
    needImages ? fetchNodeImages(node.id) : Promise.resolve({ data: { items: [] } }),
    needCandidates ? fetchCoverCandidates(node.id).catch(() => ({ data: { items: [] } })) : Promise.resolve({ data: { items: [] } }),
    fetchTags(),
    fetchNodeTags(node.id),
  ])

  images.value = imgRes.data.items
  candidates.value = candRes.data.items
  allTags.value = tagRes.data
  form.value.tag_ids = nodeTagRes.data.map((t) => t.id)

  if (node.node_type !== 'album' && !node.cover_manual) {
    form.value.cover_choice = '__auto__'
    return
  }
  if (node.cover_rel_path) {
    const idx = images.value.findIndex((i) => i.filename === node.cover_rel_path)
    if (idx >= 0) {
      form.value.cover_choice = `local:${idx}`
      return
    }
    if (candidates.value.some((c) => c.value === node.cover_rel_path)) {
      form.value.cover_choice = node.cover_rel_path
    }
  }
}

watch(
  () => [visible.value, props.node] as const,
  ([open, node]) => {
    if (open && node) load(node)
  },
)

const onSave = async () => {
  if (!props.node) return
  saving.value = true
  try {
    const body: {
      node_type: string
      cover_index?: number
      cover_rel_path?: string
      cover_manual?: boolean
    } = { node_type: form.value.node_type }

    const choice = form.value.cover_choice
    if (choice === '__auto__') {
      body.cover_manual = false
    } else if (choice?.startsWith('local:')) {
      body.cover_index = Number(choice.slice(6))
    } else if (choice) {
      body.cover_rel_path = choice
      body.cover_manual = true
    }

    const { data } = await patchNode(props.node.id, body)
    await setNodeTags(props.node.id, form.value.tag_ids)
    ElMessage.success('已保存')
    visible.value = false
    emit('saved', data)
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.cover-picker {
  width: 100%;
}

.cover-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 160px;
  margin-bottom: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-fill-color-light);
  overflow: hidden;
}

.cover-preview.empty {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.cover-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.cover-options {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
  gap: 8px;
  max-height: 220px;
  overflow-y: auto;
  padding: 2px;
}

.cover-opt {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px;
  border: 2px solid transparent;
  border-radius: 8px;
  background: none;
  cursor: pointer;
  text-align: center;
}

.cover-opt:hover {
  background: var(--el-fill-color-light);
}

.cover-opt.active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.cover-opt-thumb {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  border-radius: 4px;
  background: var(--el-fill-color);
}

.cover-opt-thumb.auto {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.cover-opt-label {
  font-size: 11px;
  line-height: 1.3;
  color: var(--el-text-color-regular);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
