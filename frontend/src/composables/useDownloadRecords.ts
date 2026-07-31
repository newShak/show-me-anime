import { onUnmounted, ref, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchDownloadRecords, overwriteDownloadJob, retryDownloadJob } from '@/api/download'
import type { DownloadRecord } from '@/types/download'

export const useDownloadRecords = (active: Ref<boolean>, pageSize = 20) => {
  const loading = ref(false)
  const items = ref<DownloadRecord[]>([])
  const total = ref(0)
  const page = ref(1)
  const retryingId = ref<string | null>(null)
  const overwritingId = ref<string | null>(null)

  let pollTimer: ReturnType<typeof setInterval> | null = null

  const isActive = (row: DownloadRecord) => row.status === 'pending' || row.status === 'running'
  const hasActive = () => items.value.some(isActive)

  const stopPoll = () => {
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = null
  }

  const startPoll = () => {
    if (pollTimer) return
    pollTimer = setInterval(() => {
      if (!active.value) {
        stopPoll()
        return
      }
      refresh(false)
    }, 800)
  }

  const refresh = async (showLoading: boolean) => {
    if (showLoading) loading.value = true
    try {
      const { data } = await fetchDownloadRecords(page.value, pageSize)
      items.value = data.items
      total.value = data.total
      if (hasActive()) startPoll()
      else stopPoll()
    } finally {
      if (showLoading) loading.value = false
    }
  }

  const reset = () => {
    stopPoll()
    page.value = 1
  }

  const onPageChange = (p: number) => {
    page.value = p
    refresh(true)
  }

  const onRetry = async (row: DownloadRecord) => {
    retryingId.value = row.id
    try {
      await retryDownloadJob(row.id)
      ElMessage.success('已开始重试')
      await refresh(false)
      startPoll()
    } catch {
      ElMessage.error('重试失败')
    } finally {
      retryingId.value = null
    }
  }

  const onOverwrite = async (row: DownloadRecord) => {
    overwritingId.value = row.id
    try {
      await overwriteDownloadJob(row.id)
      ElMessage.success('已开始强制覆盖')
      await refresh(false)
      startPoll()
    } catch {
      ElMessage.error('强制覆盖失败')
    } finally {
      overwritingId.value = null
    }
  }

  watch(active, (v) => {
    if (v) refresh(true)
    else stopPoll()
  })

  onUnmounted(stopPoll)

  return {
    loading,
    items,
    total,
    page,
    pageSize,
    retryingId,
    overwritingId,
    refresh,
    reset,
    onPageChange,
    onRetry,
    onOverwrite,
  }
}
