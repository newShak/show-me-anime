export type TagItem = {
  id: number
  name: string
}

export type TagPage = {
  items: TagItem[]
  total: number
  page: number
  pageSize: number
}

export type NodeTagsGroup = {
  node_id: number
  tags: TagItem[]
}
