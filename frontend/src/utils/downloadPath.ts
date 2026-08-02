const HTML_TAG = /<[^>]+>/g
const PATH_INVALID = /[<>:"/\\|?*\u0000-\u001f]/g
const MAX_LEN = 60

export const albumFolderName = (title: string, albumId: string) => {
  let text = title.replace(HTML_TAG, '').trim()
  text = text.replace(PATH_INVALID, '').replace(/\s+/g, ' ').trim()
  let slug = text.replace(/\s+/g, '-')
  if (slug.length > MAX_LEN) slug = slug.slice(0, MAX_LEN).replace(/-+$/, '')
  if (!slug || slug === albumId) return `album-${albumId}`
  if (/^\d+$/.test(slug)) return `${slug}-${albumId}`
  return slug
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
