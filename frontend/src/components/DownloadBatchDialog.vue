<template>
  <el-dialog v-model="visible" title="批量下载" :width="dialogWidth" @closed="onClosed">
    <p class="hint">已选 {{ items.length }} 个相册，将分别保存为子文件夹。</p>
    <ul v-if="!jobs.length" class="list">
      <li v-for="item in items" :key="item.id">{{ stripTitle(item.title) }}</li>
    </ul>
    <el-form v-if="!jobs.length" label-width="88px">
      <el-form-item label="保存到">
        <DownloadPathPicker v-model="parentPath" :hint="batchHint" />
      </el-form-item>
    </el-form>
    <div v-if="jobs.length" class="jobs-wrap">
      <DownloadJobProgress
        :jobs="jobs"
        :retrying-id="retryingId"
        :status="jobStatus"
        @retry="retryJob"
      />
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button v-if="hasFailed && !running" :loading="retryingAll" @click="retryFailed">
        重试失败项
      </el-button>
      <el-button
        v-if="!jobs.length"
        type="primary"
        :loading="submitting"
        @click="onSubmit"
      >
        开始下载
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import DownloadJobProgress from '@/components/DownloadJobProgress.vue'
import DownloadPathPicker from '@/components/DownloadPathPicker.vue'
import { useDialogWidth } from '@/composables/useDialogWidth'
import { useJobPolling } from '@/composables/useJobPolling'
import { getDownloadParentPath, saveDownloadParentPath } from '@/composables/useDownloadParentPath'
import { createDownloadJobsBatch } from '@/api/download'
import { apiErrorMessage } from '@/api/http'
import { albumFolderName, joinTargetPath } from '@/utils/downloadPath'
import type { RemoteAlbum } from '@/types/download'

const dialogWidth = useDialogWidth('560px')

const props = defineProps<{ items: RemoteAlbum[] }>()
const visible = defineModel<boolean>({ default: false })
const emit = defineEmits<{ submitted: [] }>()

const defaultParentPath = () => getDownloadParentPath() || 'imports/wnacg'
const parentPath = ref(defaultParentPath())
const submitting = ref(false)

const { jobs, running, hasFailed, retryingId, retryingAll, jobStatus, pollJobs, retryJob, retryFailed, reset } =
  useJobPolling()

const batchHint = computed(() => {
  if (!props.items.length) return ''
  const sample = joinTargetPath(parentPath.value, albumFolderName(props.items[0].title, props.items[0].id))
  return `示例：${sample}`
})

const stripTitle = (title: string) => title.replace(/<[^>]+>/g, '')

const onSubmit = async () => {
  if (!props.items.length) return
  saveDownloadParentPath(parentPath.value)
  submitting.value = true
  try {
    const { data } = await createDownloadJobsBatch({
      parent_rel_path: parentPath.value,
      auto_import_remote_tags: true,
      items: props.items.map((i) => ({
        source: i.source,
        album_id: i.id,
        title: stripTitle(i.title),
        ...(i.tags?.length ? { import_remote_tags: [...i.tags] } : {}),
      })),
    })
    jobs.value = data.jobs
    emit('submitted')
    if (data.jobs.some((j) => j.target_existed)) {
      ElMessage.warning('部分目标路径已存在，将跳过下载')
    }
    await pollJobs()
  } catch (e) {
    ElMessage.error(apiErrorMessage(e, '创建下载任务失败'))
  } finally {
    submitting.value = false
  }
}

const onClosed = () => {
  reset()
  parentPath.value = defaultParentPath()
}

watch(visible, (open) => {
  if (open && !jobs.value.length) parentPath.value = defaultParentPath()
})

defineExpose({
  setParentPath: (path: string) => {
    parentPath.value = path
  },
})
</script>

<style scoped>
.hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--app-text-muted);
}

.list {
  margin: 0 0 16px;
  padding-left: 18px;
  max-height: 120px;
  overflow-y: auto;
  font-size: 13px;
  color: var(--app-text-muted);
}

.jobs-wrap {
  margin-top: 8px;
}
</style>
