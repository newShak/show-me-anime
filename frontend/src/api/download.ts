import { http } from './http'
import type {
  DownloadCacheClearResult,
  DownloadJob,
  DownloadJobBatchCreate,
  DownloadJobBatchResult,
  DownloadJobCreate,
  DownloadOptions,
  DownloadRecordList,
  DownloadSource,
  ProxyTestResult,
  RemoteDetail,
  RemotePreviewBatch,
  RemoteBrowseResult,
  RemoteSearchResult,
} from '@/types/download'

export const fetchDownloadSources = () => http.get<DownloadSource[]>('/download/sources')

export const fetchDownloadOptions = () => http.get<DownloadOptions>('/download/options')

export const fetchDownloadRecords = (params: {
  page?: number
  pageSize?: number
  status?: string
} = {}) =>
  http.get<DownloadRecordList>('/download/records', {
    params: {
      page: params.page ?? 1,
      pageSize: params.pageSize ?? 20,
      ...(params.status ? { status: params.status } : {}),
    },
  })

export const deleteDownloadRecord = (id: string) => http.delete(`/download/records/${id}`)

export const browseRemoteAlbums = (params: {
  page?: number
  pageSize?: number
  cateId?: number | null
  source?: string
}) =>
  http.get<RemoteBrowseResult>('/download/browse', {
    params: {
      page: params.page ?? 1,
      pageSize: params.pageSize ?? 24,
      source: params.source ?? 'wnacg',
      ...(params.cateId != null ? { cateId: params.cateId } : {}),
    },
  })

export const searchRemoteAlbums = (params: {
  q: string
  page?: number
  pageSize?: number
  source?: string
}) =>
  http.get<RemoteSearchResult>('/download/search', {
    params: {
      q: params.q,
      page: params.page ?? 1,
      pageSize: params.pageSize ?? 24,
      source: params.source ?? 'wnacg',
    },
  })

export const fetchRemoteDetail = (source: string, id: string) =>
  http.get<RemoteDetail>('/download/detail', { params: { source, id } })

export const fetchRemotePreviews = (source: string, id: string, offset: number, limit?: number) =>
  http.get<RemotePreviewBatch>('/download/previews', {
    params: { source, id, offset, ...(limit != null ? { limit } : {}) },
  })

export const remoteCoverUrl = (source: string, id: string, v?: number) =>
  `/api/download/cover?source=${encodeURIComponent(source)}&id=${encodeURIComponent(id)}${v != null ? `&v=${v}` : ''}`

export const createDownloadJob = (body: DownloadJobCreate) =>
  http.post<DownloadJob>('/download/jobs', body)

export const createDownloadJobsBatch = (body: DownloadJobBatchCreate) =>
  http.post<DownloadJobBatchResult>('/download/jobs/batch', body)

export const fetchDownloadJob = (jobId: string) => http.get<DownloadJob>(`/download/jobs/${jobId}`)

export const resumeDownloadJob = (jobId: string) =>
  http.post<DownloadJob>(`/download/jobs/${jobId}/resume`)

export const cancelDownloadJob = (jobId: string) =>
  http.post<DownloadJob>(`/download/jobs/${jobId}/cancel`)

export const retryDownloadJob = (jobId: string) =>
  http.post<DownloadJob>(`/download/jobs/${jobId}/retry`)

export const overwriteDownloadJob = (jobId: string) =>
  http.post<DownloadJob>(`/download/jobs/${jobId}/overwrite`)

export const testDownloadProxy = () => http.post<ProxyTestResult>('/download/proxy/test')

export const clearDownloadCache = () => http.post<DownloadCacheClearResult>('/download/cache/clear')
