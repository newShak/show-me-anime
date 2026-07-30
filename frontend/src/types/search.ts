export type SearchResultItem = {
  id: number
  name: string
  path: string
  node_type: string
  image_count: number
}

export type SearchResponse = {
  q: string
  total: number
  items: SearchResultItem[]
}
