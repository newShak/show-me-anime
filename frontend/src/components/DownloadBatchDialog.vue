<template>
  <el-dialog v-model="visible" title="批量下载" width="560px" @closed="onClosed">
    <p class="hint">已选 {{ items.length }} 个相册，将分别保存为子文件夹。</p>
    <ul v-if="!jobs.length" class="list">
      <li v-for="item in items" :key="item.id">{{ stripTitle(item.title) }}</li>
    </ul>
    <el-form v-if="!jobs.length" label-width="88px">
      <el-form-item label="保存到">
        <DownloadPathPicker v-model="parentPath" :hint="batchHint" />
      </el-form-item>
      <el-form-item label="标签">
        <DownloadTagSection ref="tagSectionRef" :show-remote="false" />
      </el-form-item>
    </el-form>
    <div v-if="jobs.length" class="jobs">
      <div v-for="job in jobs" :key="job.id" class="job-row">
        <div class="job-head">
          <span class="job-title">{{ job.title }}</span>
          <el-button
            v-if="job.status === 'failed'"
            type="primary"
            link
            size="small"
            :loading="retryingId === job.id"
            @click="onRetryJob(job)"
          >
            重试
          </el-button>
        </div>
        <el-progress :percentage="job.progress" :status="jobStatus(job)" :stroke-width="6" />
        <p v-if="job.message" class="job-msg">{{ job.message }}</p>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button v-if="hasFailed && !running" :loading="retryingAll" @click="onRetryFailed">
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
import DownloadPathPicker from '@/components/DownloadPathPicker.vue'
import DownloadTagSection from '@/components/DownloadTagSection.vue'
import { getDownloadParentPath, saveDownloadParentPath } from '@/composables/useDownloadParentPath'
import { createDownloadJobsBatch, fetchDownloadJob, retryDownloadJob } from '@/api/download'
import { apiErrorMessage } from '@/api/http'
import { albumFolderName, joinTargetPath } from '@/utils/downloadPath'
import type { DownloadJob, RemoteAlbum } from '@/types/download'

const props = defineProps<{ items: RemoteAlbum[] }>()
const visible = defineModel<boolean>({ default: false })
const emit = defineEmits<{ submitted: [] }>()

const defaultParentPath = () => getDownloadParentPath() || 'imports/wnacg'
const parentPath = ref(defaultParentPath())
const submitting = ref(false)
const retryingId = ref<string | null>(null)
const retryingAll = ref(false)
const jobs = ref<DownloadJob[]>([])
const tagSectionRef = ref<InstanceType<typeof DownloadTagSection> | null>(null)

const running = computed(() => jobs.value.some((j) => j.status === 'running' || j.status === 'pending'))
const hasFailed = computed(() => jobs.value.some((j) => j.status === 'failed'))

const batchHint = computed(() => {
  if (!props.items.length) return ''
  const sample = joinTargetPath(parentPath.value, albumFolderName(props.items[0].title, props.items[0].id))
  return `示例：${sample}`
})

const stripTitle = (title: string) => title.replace(/<[^>]+>/g, '')

const jobStatus = (job: DownloadJob) => {
  if (job.status === 'failed') return 'exception'
  if (job.status === 'done') return 'success'
  return undefined
}

const updateJob = (data: DownloadJob) => {
  const idx = jobs.value.findIndex((j) => j.id === data.id)
  if (idx >= 0) jobs.value[idx] = data
}

const pollJobs = async () => {
  for (let round = 0; round < 120; round++) {
    let pending = false
    for (let i = 0; i < jobs.value.length; i++) {
      const job = jobs.value[i]
      if (job.status === 'done' || job.status === 'failed') continue
      pending = true
      const { data } = await fetchDownloadJob(job.id)
      jobs.value[i] = data
    }
    if (!pending) break
    await new Promise((r) => setTimeout(r, 400))
  }
  const failed = jobs.value.filter((j) => j.status === 'failed').length
  const done = jobs.value.filter((j) => j.status === 'done').length
  if (done) ElMessage.success(`已完成 ${done} 个下载`)
  const skipped = jobs.value.filter((j) => j.skipped_files > 0).length
  if (skipped) ElMessage.warning(`${skipped} 个任务跳过了已存在文件，可在下载记录中强制覆盖`)
  if (failed) ElMessage.warning(`${failed} 个下载失败，可点击重试`)
}

const onSubmit = async () => {
  if (!props.items.length) return
  saveDownloadParentPath(parentPath.value)
  submitting.value = true
  try {
    const tags = tagSectionRef.value?.getPayload() ?? { tag_ids: [], import_remote_tags: [] }
    const { data } = await createDownloadJobsBatch({
      parent_rel_path: parentPath.value,
      tag_ids: tags.tag_ids,
      items: props.items.map((i) => ({
        source: i.source,
        album_id: i.id,
        title: stripTitle(i.title),
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

const onRetryJob = async (job: DownloadJob) => {
  retryingId.value = job.id
  try {
    const { data } = await retryDownloadJob(job.id)
    updateJob(data)
    await pollJobs()
  } catch {
    ElMessage.error('重试失败')
  } finally {
    retryingId.value = null
  }
}

const onRetryFailed = async () => {
  const failed = jobs.value.filter((j) => j.status === 'failed')
  if (!failed.length) return
  retryingAll.value = true
  try {
    for (const job of failed) {
      const { data } = await retryDownloadJob(job.id)
      updateJob(data)
    }
    await pollJobs()
  } catch {
    ElMessage.error('重试失败')
  } finally {
    retryingAll.value = false
  }
}

const onClosed = () => {
  jobs.value = []
  parentPath.value = defaultParentPath()
  retryingId.value = null
  retryingAll.value = false
  tagSectionRef.value?.reset()
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

.jobs {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.job-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.job-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.job-title {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  color: var(--app-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.job-msg {
  margin: 0;
  font-size: 11px;
  color: var(--app-text-muted);
  line-height: 1.3;
}
</style>
