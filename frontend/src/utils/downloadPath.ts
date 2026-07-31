export const albumFolderName = (title: string, albumId: string) => {
  const cleaned = title
    .replace(/<[^>]+>/g, '')
    .replace(/[^\w\s-]/gu, '')
    .trim()
    .replace(/\s+/g, '-')
    .slice(0, 60)
  return cleaned || albumId
}

export const joinTargetPath = (parent: string, folder: string) => {
  const base = parent.replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')
  return base ? `${base}/${folder}` : folder
}

export const parentFromTarget = (target: string) => {
  const norm = target.replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')
  const idx = norm.lastIndexOf('/')
  return idx >= 0 ? norm.slice(0, idx) : ''
}
