import { http } from './http'
import type { ImageList, NodeItem } from '@/types/node'

export const fetchNodes = (parentId?: number) =>
  http.get<NodeItem[]>('/nodes', { params: parentId != null ? { parent_id: parentId } : {} })

export const fetchNode = (id: number) => http.get<NodeItem>(`/nodes/${id}`)

export const fetchNodeImages = (id: number) => http.get<ImageList>(`/nodes/${id}/images`)

export const coverThumbUrl = (id: number) => `/api/nodes/${id}/cover/thumb`

export const imageThumbUrl = (nodeId: number, index: number) =>
  `/api/nodes/${nodeId}/images/${index}/thumb`

export const imageFileUrl = (nodeId: number, index: number) =>
  `/api/nodes/${nodeId}/images/${index}/file`

export const triggerScan = () => http.post('/scan/trigger')
