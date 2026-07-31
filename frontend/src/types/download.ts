export type DownloadSource = {
  id: string
  name: string
  mock: boolean
}

export type RemoteAlbum = {
  source: string
  id: string
  title: string
  cover_url: string
  page_count: number | null
  category: string | null
  language: string | null
  tags: string[]
}

export type RemoteSearchResult = {
  items: RemoteAlbum[]
  total: number
  page: number
  page_size: number
}

export type BrowseNavItem = {
  label: string
  cate_id: number | null
  children: BrowseNavItem[]
}

export type RemoteBrowseResult = {
  items: RemoteAlbum[]
  total: number
  page: number
  page_size: number
  cate_id: number | null
  title: string
  nav: BrowseNavItem[]
}

export type RemoteDetail = {
  source: string
  id: string
  title: string
  page_count: number
  cover_url: string
  preview_urls: string[]
  preview_has_more: boolean
  preview_total: number
  category: string | null
  language: string | null
  tags: string[]
  default_target_rel_path: string
  default_parent_rel_path: string
}

export type RemotePreviewBatch = {
  preview_urls: string[]
  offset: number
  count: number
  total: number
  has_more: boolean
}

export type DownloadJob = {
  id: string
  source: string
  album_id: string
  title: string
  target_rel_path: string
  status: string
  progress: number
  message: string | null
  saved_files: number
}

export type DownloadJobCreate = {
  source: string
  album_id: string
  title: string
  target_rel_path: string
}

export type DownloadJobBatchCreate = {
  parent_rel_path: string
  items: Pick<DownloadJobCreate, 'source' | 'album_id' | 'title'>[]
}

export type DownloadJobBatchResult = {
  jobs: DownloadJob[]
}

export type DownloadOptions = {
  preview_batch_size: number
  concurrency: number
}

export type DownloadRecord = {
  id: string
  source: string
  album_id: string
  title: string
  target_rel_path: string
  status: string
  progress: number
  message: string | null
  saved_files: number
  created_at: number
  finished_at: number | null
  resumable: boolean
}

export type DownloadRecordList = {
  items: DownloadRecord[]
  total: number
  page: number
  page_size: number
}

export type DownloadCacheClearResult = {
  deleted: number
  message: string
}

export type ProxyTestResult = {
  ok: boolean
  message: string
}
