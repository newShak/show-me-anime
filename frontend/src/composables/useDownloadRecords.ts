import { onUnmounted, ref, watch, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  cancelDownloadJob,
  deleteDownloadRecord,
  fetchDownloadRecords,
  overwriteDownloadJob,
  retryAllFailedDownloadJobs,
  retryDownloadJob,
} from '@/api/download'
import { apiErrorMessage } from '@/api/http'
import type { DownloadRecord } from '@/types/download'

export type DownloadRecordStatusFilter = '' | 'pending' | 'running' | 'done' | 'failed'

export const useDownloadRecords = (active: Ref<boolean>) => {
  const loading = ref(false)
  const items = ref<DownloadRecord[]>([])
  const total = ref(0)
  const pageTotalBytes = ref(0)
  const failedTotal = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const statusFilter = ref<DownloadRecordStatusFilter>('')
  const retryingId = ref<string | null>(null)
  const retryingAll = ref(false)
  const overwritingId = ref<string | null>(null)
  const cancellingId = ref<string | null>(null)
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
      pageTotalBytes.value = data.page_total_bytes
      failedTotal.value = data.failed_total ?? 0
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

  const onRetryAllFailed = async () => {
    if (!failedTotal.value) return
    try {
      await ElMessageBox.confirm(
        `将重试全部 ${failedTotal.value} 条失败任务（合集会自动拆成章节任务），是否继续？`,
        '全部重试',
        { type: 'warning', confirmButtonText: '重试', cancelButtonText: '取消' },
      )
    } catch {
      return
    }
    retryingAll.value = true
    try {
      const { data } = await retryAllFailedDownloadJobs()
      const parts: string[] = []
      if (data.retried) parts.push(`已处理 ${data.retried} 条`)
      if (data.spawned) parts.push(`新建 ${data.spawned} 个章节任务`)
      if (data.skipped) parts.push(`${data.skipped} 条跳过`)
      ElMessage.success(parts.length ? parts.join('，') : '没有可重试的失败任务')
      if (data.errors.length) ElMessage.warning(data.errors.slice(0, 3).join('；'))
      await refresh(false)
      startPoll()
    } catch (err) {
      ElMessage.error(apiErrorMessage(err, '全部重试失败'))
    } finally {
      retryingAll.value = false
    }
  }

  const onRetry = async (row: DownloadRecord) => {
    retryingId.value = row.id
    try {
      const { data } = await retryDownloadJob(row.id)
      if (data.spawned_jobs.length) {
        ElMessage.success(`已创建 ${data.spawned_jobs.length} 个章节下载任务`)
      } else {
        ElMessage.success('已开始重试')
      }
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

  const onCancel = async (row: DownloadRecord) => {
    try {
      await ElMessageBox.confirm(`确定中断「${row.title}」的下载？`, '中断下载', {
        type: 'warning',
        confirmButtonText: '中断',
        cancelButtonText: '取消',
      })
    } catch {
      return
    }
    cancellingId.value = row.id
    try {
      await cancelDownloadJob(row.id)
      ElMessage.success('已中断')
      await refresh(false)
    } catch (err) {
      ElMessage.error(apiErrorMessage(err, '中断失败'))
    } finally {
      cancellingId.value = null
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
    pageTotalBytes,
    failedTotal,
    page,
    pageSize,
    statusFilter,
    retryingId,
    retryingAll,
    overwritingId,
    cancellingId,
    deletingId,
    refresh,
    reset,
    onPageChange,
    onPageSizeChange,
    onStatusChange,
    onRetry,
    onRetryAllFailed,
    onOverwrite,
    onCancel,
    onDelete,
  }
}
