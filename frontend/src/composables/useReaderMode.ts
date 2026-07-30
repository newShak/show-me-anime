import type { ReaderMode } from '@/types/reader'

const MODE_KEY = 'reader-mode'
const DEFAULT: ReaderMode = 'scroll'

/** 读取本地保存的阅读模式 */
export const getStoredReaderMode = (): ReaderMode =>
  localStorage.getItem(MODE_KEY) === 'scroll' ? 'scroll' : DEFAULT

/** 保存阅读模式偏好 */
export const saveReaderMode = (mode: ReaderMode) => localStorage.setItem(MODE_KEY, mode)

/** 解析 URL / 本地存储中的阅读模式 */
export const resolveReaderMode = (queryMode?: string | null): ReaderMode => {
  if (queryMode === 'page' || queryMode === 'scroll') return queryMode
  return getStoredReaderMode()
}
