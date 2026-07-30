export type TaskRecord = {
  id: number
  task_type: string
  status: string
  source?: string | null
  mode?: string | null
  started_at: number | null
  finished_at: number | null
  added?: number | null
  updated?: number | null
  removed?: number | null
  message?: string | null
}

export type TaskRecordPage = {
  items: TaskRecord[]
  total: number
  page: number
  pageSize: number
}
