import { http } from './http'
import type { TagItem } from '@/types/tag'

export const fetchTags = () => http.get<TagItem[]>('/tags')

export const createTag = (name: string) => http.post<TagItem>('/tags', { name })

export const deleteTag = (id: number) => http.delete(`/tags/${id}`)

export const fetchNodeTags = (nodeId: number) => http.get<TagItem[]>(`/tags/nodes/${nodeId}`)

export const setNodeTags = (nodeId: number, tagIds: number[]) =>
  http.put<TagItem[]>(`/tags/nodes/${nodeId}`, { tag_ids: tagIds })
