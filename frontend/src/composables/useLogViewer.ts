import { onUnmounted, ref } from 'vue'
import { fetchLogContent, fetchLogFiles } from '@/api/logs'

export const useLogViewer = () => {
  const loading = ref(false)
  const files = ref<string[]>([])
  const file = ref('app.log')
  const content = ref('')
  const offset = ref(0)
  const live = ref(true)
  const autoScroll = ref(true)
  const enabled = ref(true)
  const logDir = ref('')

  let pollTimer: ReturnType<typeof setInterval> | null = null
  let logEl: HTMLElement | null = null

  const bindEl = (el: HTMLElement | null) => {
    logEl = el
  }

  const scrollToBottom = () => {
    if (!autoScroll.value || !logEl) return
    logEl.scrollTop = logEl.scrollHeight
  }

  const stopPoll = () => {
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = null
  }

  const startPoll = () => {
    if (pollTimer || !live.value) return
    pollTimer = setInterval(() => refresh(false), 1000)
  }

  const loadFiles = async () => {
    const { data } = await fetchLogFiles()
    enabled.value = data.enabled
    logDir.value = data.dir
    files.value = data.items.map((item) => item.name)
    if (files.value.length && !files.value.includes(file.value)) {
      file.value = files.value[0]
    }
  }

  const refresh = async (showLoading: boolean) => {
    if (!enabled.value) return
    if (showLoading) loading.value = true
    try {
      const { data } = await fetchLogContent({
        file: file.value,
        tailLines: 500,
        offset: offset.value,
      })
      if (data.reset || !data.append) {
        content.value = data.content
      } else if (data.content) {
        content.value += data.content
        if (content.value.length > 500_000) {
          content.value = content.value.slice(-400_000)
        }
      }
      offset.value = data.offset
      scrollToBottom()
    } finally {
      if (showLoading) loading.value = false
    }
  }

  const reload = async () => {
    stopPoll()
    offset.value = 0
    content.value = ''
    await loadFiles()
    await refresh(true)
    if (live.value) startPoll()
  }

  const onFileChange = async (name: string) => {
    file.value = name
    offset.value = 0
    content.value = ''
    await refresh(true)
  }

  const onLiveChange = (val: boolean) => {
    live.value = val
    if (val) startPoll()
    else stopPoll()
  }

  const onAutoScrollChange = (val: boolean) => {
    autoScroll.value = val
    if (val) scrollToBottom()
  }

  onUnmounted(stopPoll)

  return {
    loading,
    files,
    file,
    content,
    live,
    autoScroll,
    enabled,
    logDir,
    bindEl,
    reload,
    refresh,
    onFileChange,
    onLiveChange,
    onAutoScrollChange,
    startPoll,
    stopPoll,
  }
}
