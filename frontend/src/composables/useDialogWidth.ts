import { computed, type ComputedRef } from 'vue'
import { useBreakpoint } from '@/composables/useBreakpoint'

/** 弹窗宽度：桌面固定 px，H5 用视口百分比 */
export const useDialogWidth = (desktop: string): ComputedRef<string> => {
  const { isMobile } = useBreakpoint()
  return computed(() => (isMobile.value ? '92vw' : desktop))
}
