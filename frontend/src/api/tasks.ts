import { http } from './http'
import type { TaskRecordPage } from '@/types/task'

export const fetchTaskRecords = (page = 1, pageSize = 10) =>
  http.get<TaskRecordPage>('/tasks', { params: { page, pageSize } })
