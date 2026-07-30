<template>
  <el-dialog v-model="visible" title="编辑节点" width="520px" @closed="emit('closed')">
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
      <el-form-item v-if="images.length" label="封面">
        <el-select v-model="form.cover_index" style="width: 100%" clearable placeholder="默认第一张">
          <el-option
            v-for="img in images"
            :key="img.index"
            :label="`${img.index + 1}. ${img.filename}`"
            :value="img.index"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="标签">
        <el-select v-model="form.tag_ids" multiple filterable style="width: 100%" placeholder="选择标签">
          <el-option v-for="tag in allTags" :key="tag.id" :label="tag.name" :value="tag.id" />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchNodeImages, patchNode } from '@/api/nodes'
import { fetchNodeTags, fetchTags, setNodeTags } from '@/api/tags'
import type { ImageItem, NodeItem } from '@/types/node'
import type { TagItem } from '@/types/tag'

const props = defineProps<{ node: NodeItem | null }>()
const emit = defineEmits<{ saved: []; closed: [] }>()

const visible = defineModel<boolean>({ default: false })

const saving = ref(false)
const images = ref<ImageItem[]>([])
const allTags = ref<TagItem[]>([])
const form = ref({ node_type: 'album', cover_index: undefined as number | undefined, tag_ids: [] as number[] })

const load = async (node: NodeItem) => {
  form.value.node_type = node.node_type
  form.value.cover_index = undefined
  form.value.tag_ids = []

  const [imgRes, tagRes, nodeTagRes] = await Promise.all([
    node.node_type !== 'container' ? fetchNodeImages(node.id) : Promise.resolve({ data: { items: [] } }),
    fetchTags(),
    fetchNodeTags(node.id),
  ])

  images.value = imgRes.data.items
  allTags.value = tagRes.data
  form.value.tag_ids = nodeTagRes.data.map((t) => t.id)

  if (node.cover_rel_path && images.value.length) {
    const idx = images.value.findIndex((i) => i.filename === node.cover_rel_path)
    if (idx >= 0) form.value.cover_index = idx
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
    const body: { node_type: string; cover_index?: number } = { node_type: form.value.node_type }
    if (form.value.cover_index != null) body.cover_index = form.value.cover_index
    await patchNode(props.node.id, body)
    await setNodeTags(props.node.id, form.value.tag_ids)
    ElMessage.success('已保存')
    visible.value = false
    emit('saved')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>
