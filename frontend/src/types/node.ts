export type NodeItem = {
  id: number
  parent_id: number | null
  name: string
  path: string
  node_type: string
  source_type: string
  image_count: number
  cover_rel_path: string | null
}

export type ImageItem = {
  index: number
  filename: string
}

export type ImageList = {
  node_id: number
  total: number
  items: ImageItem[]
}

export type ScanJob = {
  id: number
  status: string
  started_at: number | null
  finished_at: number | null
  added: number
  updated: number
  removed: number
  message: string | null
}
