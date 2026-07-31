export type NodeItem = {
  id: number
  parent_id: number | null
  name: string
  path: string
  node_type: string
  source_type: string
  image_count: number
  subdir_count: number
  archive_count: number
  cover_rel_path: string | null
  cover_manual: boolean
  dir_mtime?: number | null
  created_at?: number | null
}

export type CoverCandidate = {
  value: string
  label: string
  source_node_id: number
}

export type CoverCandidateList = {
  node_id: number
  items: CoverCandidate[]
}

export type ImageItem = {
  index: number
  filename: string
}

export type NodeUpdate = {
  node_type?: string
  cover_rel_path?: string | null
  cover_index?: number
  cover_manual?: boolean
}

export type ImageList = {
  node_id: number
  total: number
  items: ImageItem[]
}

export type NodeBatchDeleteResult = {
  deleted: number
  errors: string[]
}

export type NodeMovePayload = {
  ids: number[]
  target_parent_id: number | null
}

export type NodeMkdirPayload = {
  parent_id?: number | null
  name: string
}

export type NodeMkdirResult = {
  id: number
  path: string
  name: string
}

export type NodeMoveResult = {
  moved: number
  errors: string[]
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

export type RecentNodesResult = {
  total: number
  items: NodeItem[]
}
