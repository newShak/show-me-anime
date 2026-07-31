<template>
  <el-dialog v-model="visible" title="批量下载" width="560px" @closed="onClosed">
    <p class="hint">已选 {{ items.length }} 个相册，将分别保存为子文件夹。</p>
    <ul class="list">
      <li v-for="item in items" :key="item.id">{{ stripTitle(item.title) }}</li>
    </ul>
    <el-form label-width="88px">
      <el-form-item label="保存到">
        <DownloadPathPicker v-model="parentPath" :hint="batchHint" />
      </el-form-item>
    </el-form>
    <div v-if="jobs.length" class="jobs">
      <div v-for="job in jobs" :key="job.id" class="job-row">
        <span class="job-title">{{ job.title }}</span>
        <el-progress :percentage="job.progress" :status="jobStatus(job)" :stroke-width="6" />
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button type="primary" :loading="submitting" :disabled="!!running" @click="onSubmit">
        开始下载
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import DownloadPathPicker from '@/components/DownloadPathPicker.vue'
import { createDownloadJobsBatch, fetchDownloadJob } from '@/api/download'
import { albumFolderName, joinTargetPath } from '@/utils/downloadPath'
import type { DownloadJob, RemoteAlbum } from '@/types/download'

const props = defineProps<{ items: RemoteAlbum[] }>()
const visible = defineModel<boolean>({ default: false })

const parentPath = ref('imports/wnacg')
const submitting = ref(false)
const jobs = ref<DownloadJob[]>([])

const running = computed(() => jobs.value.some((j) => j.status === 'running' || j.status === 'pending'))

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
  if (failed) ElMessage.error(`${failed} 个下载失败`)
}

const onSubmit = async () => {
  if (!props.items.length) return
  submitting.value = true
  try {
    const { data } = await createDownloadJobsBatch({
      parent_rel_path: parentPath.value,
      items: props.items.map((i) => ({
        source: i.source,
        album_id: i.id,
        title: stripTitle(i.title),
      })),
    })
    jobs.value = data.jobs
    await pollJobs()
  } catch {
    ElMessage.error('创建下载任务失败')
  } finally {
    submitting.value = false
  }
}

const onClosed = () => {
  jobs.value = []
  parentPath.value = 'imports/wnacg'
}

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
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.job-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.job-title {
  font-size: 12px;
  color: var(--app-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
