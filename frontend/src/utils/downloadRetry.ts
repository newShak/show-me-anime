import { ElMessage } from 'element-plus'
import type { DownloadJob, DownloadJobRetryResult } from '@/types/download'

/** 重试 API 结果合并进任务列表（合集会拆成多条章节任务）。 */
export const applyDownloadJobRetry = (
  jobs: DownloadJob[],
  data: DownloadJobRetryResult,
): DownloadJob[] => {
  const next = jobs.map((j) => (j.id === data.job.id ? data.job : j))
  const ids = new Set(next.map((j) => j.id))
  for (const spawned of data.spawned_jobs) {
    if (!ids.has(spawned.id)) {
      next.push(spawned)
      ids.add(spawned.id)
    }
  }
  if (data.spawned_jobs.length) {
    ElMessage.info(`合集已拆分为 ${data.spawned_jobs.length} 个章节下载任务`)
  }
  return next
}
