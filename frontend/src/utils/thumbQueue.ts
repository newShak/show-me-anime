const MAX = 4
let active = 0
const waiters: (() => void)[] = []

export const acquireThumb = (): Promise<void> =>
  new Promise((resolve) => {
    if (active < MAX) {
      active++
      resolve()
      return
    }
    waiters.push(() => {
      active++
      resolve()
    })
  })

export const releaseThumb = () => {
  active = Math.max(0, active - 1)
  waiters.shift()?.()
}
