import { onUnmounted, ref, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchDownloadRecords, resumeDownloadJob } from '@/api/download'
import type { DownloadRecord } from '@/types/download'

export const useDownloadRecords = (active: Ref<boolean>, pageSize = 20) => {
  const loading = ref(false)
  const items = ref<DownloadRecord[]>([])
  const total = ref(0)
  const page = ref(1)
  const resumingId = ref<string | null>(null)

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

  const onResume = async (row: DownloadRecord) => {
    resumingId.value = row.id
    try {
      await resumeDownloadJob(row.id)
      ElMessage.success('已开始续传')
      await refresh(false)
      startPoll()
    } catch {
      ElMessage.error('续传失败')
    } finally {
      resumingId.value = null
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
    resumingId,
    refresh,
    reset,
    onPageChange,
    onResume,
  }
}
