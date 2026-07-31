import { http } from './http'

export type LogFileItem = {
  name: string
  size: number
  modified_at: number
}

export type LogFileList = {
  dir: string
  enabled: boolean
  items: LogFileItem[]
}

export type LogContent = {
  file: string
  content: string
  offset: number
  reset: boolean
  append: boolean
}

export const fetchLogFiles = () => http.get<LogFileList>('/logs/files')

export const fetchLogContent = (params: {
  file?: string
  tailLines?: number
  offset?: number
}) =>
  http.get<LogContent>('/logs/content', {
    params: {
      file: params.file ?? 'app.log',
      tailLines: params.tailLines ?? 500,
      offset: params.offset ?? 0,
    },
  })
