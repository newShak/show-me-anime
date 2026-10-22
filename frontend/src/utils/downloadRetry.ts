import type { DownloadJob, DownloadJobRetryResult } from '@/types/download'

/** 把任务及其后拆出的章节合并进列表。 */
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
  return next
}
