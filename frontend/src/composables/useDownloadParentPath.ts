const KEY = 'download-parent-path'

export const getDownloadParentPath = () => localStorage.getItem(KEY) ?? ''

export const saveDownloadParentPath = (path: string) => {
  localStorage.setItem(KEY, path.replace(/\\/g, '/').replace(/^\/+|\/+$/g, ''))
}
