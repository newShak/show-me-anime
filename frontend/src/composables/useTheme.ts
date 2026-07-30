export type ThemeMode = 'light' | 'dark'

const STORAGE_KEY = 'theme'

/** 读取已保存主题 */
export function getTheme(): ThemeMode {
  return localStorage.getItem(STORAGE_KEY) === 'dark' ? 'dark' : 'light'
}

/** 应用主题到 document */
export function applyTheme(mode: ThemeMode) {
  document.documentElement.classList.toggle('dark', mode === 'dark')
  localStorage.setItem(STORAGE_KEY, mode)
}

/** 启动时恢复主题，避免闪烁 */
export function initTheme() {
  applyTheme(getTheme())
}
