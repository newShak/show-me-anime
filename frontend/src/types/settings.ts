export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'

export type Settings = {
  gallery_root: string
  thumb_dir: string
  database_url: string
  thumb_max_size: number
  watch_enabled: boolean
  watch_debounce_seconds: number
  album_list_cache_ttl: number
  log_level: LogLevel
  recent_view_limit: number
  recent_added_limit: number
  host: string
  port: number
}

export type SettingsUpdate = Partial<
  Pick<
    Settings,
    | 'gallery_root'
    | 'thumb_dir'
    | 'thumb_max_size'
    | 'watch_enabled'
    | 'watch_debounce_seconds'
    | 'log_level'
    | 'recent_view_limit'
    | 'recent_added_limit'
  >
>

export type SettingsSaveResult = Settings & {
  message?: string
  needs_rescan?: boolean
}

export type ThumbRebuildResult = {
  deleted: number
  message: string
}
