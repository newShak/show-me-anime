import { http } from './http'
import type { ImageList, NodeItem, NodeUpdate } from '@/types/node'
import type { ReadProgress } from '@/types/progress'

export const fetchNodes = (parentId?: number) =>
  http.get<NodeItem[]>('/nodes', { params: parentId != null ? { parent_id: parentId } : {} })

export const fetchNode = (id: number) => http.get<NodeItem>(`/nodes/${id}`)

export const patchNode = (id: number, body: NodeUpdate) => http.patch<NodeItem>(`/nodes/${id}`, body)

export const fetchNodeImages = (id: number) => http.get<ImageList>(`/nodes/${id}/images`)

export const fetchProgress = (nodeId: number) => http.get<ReadProgress>(`/nodes/${nodeId}/progress`)

export const saveProgress = (nodeId: number, pageIndex: number) =>
  http.put<ReadProgress>(`/nodes/${nodeId}/progress`, { page_index: pageIndex })

export const coverThumbUrl = (id: number) => `/api/nodes/${id}/cover/thumb`

export const imageThumbUrl = (nodeId: number, index: number) =>
  `/api/nodes/${nodeId}/images/${index}/thumb`

export const imageFileUrl = (nodeId: number, index: number) =>
  `/api/nodes/${nodeId}/images/${index}/file`
