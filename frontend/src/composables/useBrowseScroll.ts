const prefix = 'browse-scroll:'

const key = (nodeId: number | null) => `${prefix}${nodeId ?? 'root'}`

export const saveBrowseScroll = (nodeId: number | null) => {
  sessionStorage.setItem(key(nodeId), String(window.scrollY))
}

export const hasBrowseScroll = (nodeId: number | null) =>
  sessionStorage.getItem(key(nodeId)) != null

export const getBrowseScroll = (nodeId: number | null): number | null => {
  const raw = sessionStorage.getItem(key(nodeId))
  return raw != null ? Number(raw) : null
}

export const clearBrowseScroll = (nodeId: number | null) => {
  sessionStorage.removeItem(key(nodeId))
}
