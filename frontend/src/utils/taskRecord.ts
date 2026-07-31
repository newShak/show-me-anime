/** 任务记录展示文案与格式化 */

import type { TaskRecord } from '@/types/task'

export const TASK_LABELS: Record<string, string> = {
  scan: '目录扫描',
  rebuild_thumbs: '重建缩略图',
}

export const STATUS_LABELS: Record<string, string> = {
  running: '进行中',
  done: '完成',
  failed: '失败',
  interrupted: '已中断',
}

export const SOURCE_LABELS: Record<string, string> = {
  api: '管理页',
  watchdog: '监听',
  manual: '手动',
}

export const SCAN_MODE_LABELS: Record<string, string> = {
  incremental: '增量',
  full: '全量',
}

export const taskTypeLabel = (type: string) => TASK_LABELS[type] ?? type
export const statusLabel = (status: string) => STATUS_LABELS[status] ?? status
export const sourceLabel = (source?: string | null) => (source ? SOURCE_LABELS[source] ?? source : '—')
export const scanModeLabel = (mode?: string | null) => (mode ? SCAN_MODE_LABELS[mode] ?? mode : '—')

export const statusTagType = (status: string) => {
  if (status === 'done') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'interrupted') return 'info'
  if (status === 'running') return 'warning'
  return 'info'
}

export const formatTime = (ts: number | null) => (ts ? new Date(ts * 1000).toLocaleString() : '—')

export const formatDuration = (start: number | null, end: number | null) => {
  if (!start || !end) return '—'
  return `${(end - start).toFixed(1)}s`
}

export const formatTaskResult = (row: TaskRecord) => {
  if (row.status === 'interrupted') return row.message ?? '进程中断，任务未正常结束'
  if (row.task_type === 'scan') {
    const mode = scanModeLabel(row.mode)
    return `${mode} · 新增 ${row.added ?? 0}，更新 ${row.updated ?? 0}，移除 ${row.removed ?? 0}`
  }
  return row.message ?? '—'
}
