export const formatBytes = (bytes: number) => {
  if (bytes <= 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let n = bytes
  let i = 0
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024
    i++
  }
  const text = i === 0 || n >= 100 ? n.toFixed(0) : n.toFixed(1)
  return `${text} ${units[i]}`
}
