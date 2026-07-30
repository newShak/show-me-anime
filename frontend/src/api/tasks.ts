import { http } from './http'
import type { TaskPurgeResult, TaskRecordPage } from '@/types/task'

export const fetchTaskRecords = (page = 1, pageSize = 10) =>
  http.get<TaskRecordPage>('/tasks', { params: { page, pageSize } })

export const purgeTaskRecords = (startTime: number, endTime: number) =>
  http.post<TaskPurgeResult>('/tasks/purge', { startTime, endTime })
