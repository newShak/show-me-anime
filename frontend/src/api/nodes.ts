import { http } from './http'
import type { NodeSort } from '@/composables/useNodeSort'
import type { ImageList, NodeBatchDeleteResult, NodeItem, NodeUpdate } from '@/types/node'
import type { ReadProgress } from '@/types/progress'

export const fetchNodes = (parentId?: number, sort?: NodeSort) =>
  http.get<NodeItem[]>('/nodes', {
    params: {
      ...(parentId != null ? { parent_id: parentId } : {}),
      ...(sort ? { sort_by: sort.sortBy, sort_order: sort.sortOrder } : {}),
    },
  })

export const fetchNode = (id: number) => http.get<NodeItem>(`/nodes/${id}`)

export const patchNode = (id: number, body: NodeUpdate) => http.patch<NodeItem>(`/nodes/${id}`, body)

export const fetchNodeImages = (id: number) => http.get<ImageList>(`/nodes/${id}/images`)

export const fetchProgress = (nodeId: number) => http.get<ReadProgress>(`/nodes/${nodeId}/progress`)

export const fetchNodesProgress = (nodeIds: number[]) =>
  http.get<ReadProgress[]>('/nodes/progress', { params: { ids: nodeIds.join(',') } })

export const saveProgress = (nodeId: number, pageIndex: number) =>
  http.put<ReadProgress>(`/nodes/${nodeId}/progress`, { page_index: pageIndex })

export const coverThumbUrl = (id: number) => `/api/nodes/${id}/cover/thumb`

export const imageThumbUrl = (nodeId: number, index: number, v?: number) =>
  `/api/nodes/${nodeId}/images/${index}/thumb${v != null ? `?v=${v}` : ''}`

export const imageFileUrl = (nodeId: number, index: number, v?: number) =>
  `/api/nodes/${nodeId}/images/${index}/file${v != null ? `?v=${v}` : ''}`

export const deleteNodes = (ids: number[]) =>
  http.post<NodeBatchDeleteResult>('/nodes/batch-delete', { ids })
