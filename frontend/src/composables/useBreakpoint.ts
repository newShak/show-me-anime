import { computed, onMounted, onUnmounted, ref } from 'vue'

export const MOBILE_MAX = 767

const isMobile = ref(
  typeof window !== 'undefined' ? window.matchMedia(`(max-width: ${MOBILE_MAX}px)`).matches : false,
)

let listeners = 0
let mq: MediaQueryList | null = null

const sync = () => {
  isMobile.value = mq?.matches ?? false
}

/** 视口是否 ≤767px（H5 / 手机竖屏） */
export const useBreakpoint = () => {
  onMounted(() => {
    if (!mq) {
      mq = window.matchMedia(`(max-width: ${MOBILE_MAX}px)`)
      sync()
      mq.addEventListener('change', sync)
    }
    listeners += 1
  })

  onUnmounted(() => {
    listeners -= 1
    if (listeners <= 0 && mq) {
      mq.removeEventListener('change', sync)
      mq = null
    }
  })

  return {
    isMobile,
    isDesktop: computed(() => !isMobile.value),
  }
}
