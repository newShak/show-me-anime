import { onUnmounted, ref, watch, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteDownloadRecord,
  fetchDownloadRecords,
  overwriteDownloadJob,
  retryDownloadJob,
} from '@/api/download'
import { apiErrorMessage } from '@/api/http'
import type { DownloadRecord } from '@/types/download'

export type DownloadRecordStatusFilter = '' | 'pending' | 'running' | 'done' | 'failed'

export const useDownloadRecords = (active: Ref<boolean>) => {
  const loading = ref(false)
  const items = ref<DownloadRecord[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const statusFilter = ref<DownloadRecordStatusFilter>('')
  const retryingId = ref<string | null>(null)
  const overwritingId = ref<string | null>(null)
  const deletingId = ref<string | null>(null)

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
      const { data } = await fetchDownloadRecords({
        page: page.value,
        pageSize: pageSize.value,
        status: statusFilter.value || undefined,
      })
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
    statusFilter.value = ''
    pageSize.value = 20
  }

  const onPageChange = (p: number) => {
    page.value = p
    refresh(true)
  }

  const onPageSizeChange = (size: number) => {
    pageSize.value = size
    page.value = 1
    refresh(true)
  }

  const onStatusChange = (status: DownloadRecordStatusFilter) => {
    statusFilter.value = status
    page.value = 1
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

  const onDelete = async (row: DownloadRecord) => {
    try {
      await ElMessageBox.confirm(`确定删除「${row.title}」的下载记录？`, '删除记录', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      })
    } catch {
      return
    }
    deletingId.value = row.id
    try {
      await deleteDownloadRecord(row.id)
      ElMessage.success('已删除')
      if (items.value.length === 1 && page.value > 1) page.value -= 1
      await refresh(false)
    } catch (err) {
      ElMessage.error(apiErrorMessage(err, '删除失败'))
    } finally {
      deletingId.value = null
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
    statusFilter,
    retryingId,
    overwritingId,
    deletingId,
    refresh,
    reset,
    onPageChange,
    onPageSizeChange,
    onStatusChange,
    onRetry,
    onOverwrite,
    onDelete,
  }
}
