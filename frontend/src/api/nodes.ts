import { http } from './http'
import type { NodeSort } from '@/composables/useNodeSort'
import type { CoverCandidateList, ImageList, NodeBatchDeleteResult, NodeItem, NodeMkdirPayload, NodeMkdirResult, NodeMovePayload, NodeMoveResult, NodeUpdate, RecentNodesResult } from '@/types/node'
import type { ReadProgress } from '@/types/progress'

export const fetchNodes = (parentId?: number, sort?: NodeSort) =>
  http.get<NodeItem[]>('/nodes', {
    params: {
      ...(parentId != null ? { parent_id: parentId } : {}),
      ...(sort ? { sort_by: sort.sortBy, sort_order: sort.sortOrder } : {}),
    },
  })

export type RecentNodesParams = {
  since?: number
  until?: number
  offset?: number
  limit?: number
}

export const fetchRecentNodes = (params?: RecentNodesParams | number) => {
  const p: RecentNodesParams =
    typeof params === 'number' ? { limit: params } : (params ?? {})
  return http.get<RecentNodesResult>('/nodes/recent', { params: p })
}

export const fetchNodesBatch = (ids: number[]) =>
  ids.length
    ? http.get<NodeItem[]>('/nodes/batch', { params: { ids: ids.join(',') } })
    : Promise.resolve({ data: [] as NodeItem[] })

export const fetchNode = (id: number) => http.get<NodeItem>(`/nodes/${id}`)

export const fetchNodeAncestors = (id: number) => http.get<NodeItem[]>(`/nodes/${id}/ancestors`)

export const patchNode = (id: number, body: NodeUpdate) => http.patch<NodeItem>(`/nodes/${id}`, body)

export const fetchNodeImages = (id: number) => http.get<ImageList>(`/nodes/${id}/images`)

export const fetchCoverCandidates = (id: number) =>
  http.get<CoverCandidateList>(`/nodes/${id}/cover/candidates`)

export const fetchProgress = (nodeId: number) => http.get<ReadProgress>(`/nodes/${nodeId}/progress`)

export const fetchNodesProgress = (nodeIds: number[]) =>
  http.get<ReadProgress[]>('/nodes/progress', { params: { ids: nodeIds.join(',') } })

export const saveProgress = (nodeId: number, pageIndex: number) =>
  http.put<ReadProgress>(`/nodes/${nodeId}/progress`, { page_index: pageIndex })

export const coverThumbUrl = (id: number, cover?: string | null) => {
  const base = `/api/nodes/${id}/cover/thumb`
  return cover ? `${base}?v=${encodeURIComponent(cover)}` : base
}

export const imageThumbUrl = (nodeId: number, index: number, v?: number) =>
  `/api/nodes/${nodeId}/images/${index}/thumb${v != null ? `?v=${v}` : ''}`

export const imageFileUrl = (nodeId: number, index: number, v?: number) =>
  `/api/nodes/${nodeId}/images/${index}/file${v != null ? `?v=${v}` : ''}`

export const deleteNodes = (ids: number[]) =>
  http.post<NodeBatchDeleteResult>('/nodes/batch-delete', { ids })

export const moveNodes = (body: NodeMovePayload) =>
  http.post<NodeMoveResult>('/nodes/move', body)

export const createNodeDir = (body: NodeMkdirPayload) =>
  http.post<NodeMkdirResult>('/nodes/mkdir', body)
