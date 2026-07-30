import { http } from './http'
import type { NodeTagsGroup, TagItem, TagPage } from '@/types/tag'

export const fetchTags = () => http.get<TagItem[]>('/tags')

export const fetchTagsPage = (page = 1, pageSize = 10) =>
  http.get<TagPage>('/tags/paged', { params: { page, pageSize } })

export const createTag = (name: string) => http.post<TagItem>('/tags', { name })

export const deleteTag = (id: number) => http.delete(`/tags/${id}`)

export const fetchNodeTags = (nodeId: number) => http.get<TagItem[]>(`/tags/nodes/${nodeId}`)

export const fetchNodesTags = (nodeIds: number[]) =>
  http.get<NodeTagsGroup[]>('/tags/nodes/tags', { params: { ids: nodeIds.join(',') } })

export const setNodeTags = (nodeId: number, tagIds: number[]) =>
  http.put<TagItem[]>(`/tags/nodes/${nodeId}`, { tag_ids: tagIds })

export const batchAddNodeTags = (nodeIds: number[], tagIds: number[]) =>
  http.post<{ updated: number }>('/tags/nodes/batch-add', { node_ids: nodeIds, tag_ids: tagIds })

export const removeNodeTag = (nodeId: number, tagId: number) =>
  http.delete(`/tags/nodes/${nodeId}/tags/${tagId}`)
