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
  log_dir: string
  log_file_enabled: boolean
  log_file_max_bytes: number
  log_file_retention_days: number
  recent_view_limit: number
  recent_added_limit: number
  download_proxy_enabled: boolean
  download_proxy: string
  download_default_subdir: string
  download_use_mock: boolean
  download_api_domain: string
  download_preview_batch_size: number
  download_concurrency: number
  download_speed_limit_kbps: number
  download_cache_dir: string
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
    | 'log_dir'
    | 'log_file_enabled'
    | 'log_file_max_bytes'
    | 'log_file_retention_days'
    | 'recent_view_limit'
    | 'recent_added_limit'
    | 'download_proxy_enabled'
    | 'download_proxy'
    | 'download_default_subdir'
    | 'download_use_mock'
    | 'download_api_domain'
    | 'download_preview_batch_size'
    | 'download_concurrency'
    | 'download_speed_limit_kbps'
    | 'download_cache_dir'
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
