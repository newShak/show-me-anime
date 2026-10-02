import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchDownloadJob, retryDownloadJob } from '@/api/download'
import type { DownloadJob } from '@/types/download'
import { applyDownloadJobRetry } from '@/utils/downloadRetry'

const POLL_ROUNDS = 120
const POLL_INTERVAL_MS = 400

const isFinished = (job: DownloadJob) => job.status === 'done' || job.status === 'failed'

/** 批量下载任务的进度轮询与重试，详情弹窗和批量弹窗共用。 */
export const useJobPolling = () => {
  const jobs = ref<DownloadJob[]>([])
  const retryingId = ref<string | null>(null)
  const retryingAll = ref(false)
  let generation = 0

  const running = computed(() => jobs.value.some((j) => !isFinished(j)))
  const hasFailed = computed(() => jobs.value.some((j) => j.status === 'failed'))

  const jobStatus = (job: DownloadJob) => {
    if (job.status === 'failed') return 'exception'
    if (job.status === 'done') return 'success'
    return undefined
  }

  const updateJob = (data: DownloadJob) => {
    const idx = jobs.value.findIndex((j) => j.id === data.id)
    if (idx >= 0) jobs.value[idx] = data
  }

  const reportResult = () => {
    const done = jobs.value.filter((j) => j.status === 'done').length
    const failed = jobs.value.filter((j) => j.status === 'failed').length
    const skipped = jobs.value.filter((j) => j.skipped_files > 0).length
    if (done) ElMessage.success(`已完成 ${done} 个下载`)
    if (skipped) ElMessage.warning(`${skipped} 个任务跳过了已存在文件，可在下载记录中强制覆盖`)
    if (failed) ElMessage.warning(`${failed} 个下载失败，可点击重试`)
  }

  const pollJobs = async (): Promise<boolean> => {
    const gen = ++generation
    try {
      for (let round = 0; round < POLL_ROUNDS; round++) {
        let pending = false
        for (let i = 0; i < jobs.value.length; i++) {
          if (isFinished(jobs.value[i])) continue
          pending = true
          const { data } = await fetchDownloadJob(jobs.value[i].id)
          if (gen !== generation) return true
          jobs.value[i] = data
        }
        if (!pending) break
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS))
        if (gen !== generation) return true
      }
      if (gen !== generation) return true
      reportResult()
      return true
    } catch {
      return false
    }
  }

  const retryJob = async (job: DownloadJob) => {
    retryingId.value = job.id
    try {
      const { data } = await retryDownloadJob(job.id)
      jobs.value = applyDownloadJobRetry(jobs.value, data)
      await pollJobs()
    } catch {
      ElMessage.error('重试失败')
    } finally {
      retryingId.value = null
    }
  }

  const retryFailed = async () => {
    const failed = jobs.value.filter((j) => j.status === 'failed')
    if (!failed.length) return
    retryingAll.value = true
    try {
      for (const job of failed) {
        const { data } = await retryDownloadJob(job.id)
        jobs.value = applyDownloadJobRetry(jobs.value, data)
      }
      await pollJobs()
    } catch {
      ElMessage.error('重试失败')
    } finally {
      retryingAll.value = false
    }
  }

  const reset = (next: DownloadJob[] = []) => {
    generation += 1
    jobs.value = next
    retryingId.value = null
    retryingAll.value = false
  }

  return {
    jobs,
    running,
    hasFailed,
    retryingId,
    retryingAll,
    jobStatus,
    updateJob,
    pollJobs,
    retryJob,
    retryFailed,
    reset,
  }
}
