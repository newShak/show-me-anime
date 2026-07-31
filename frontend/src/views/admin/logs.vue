<template>
  <el-card shadow="never" class="panel">
    <template #header>
      <div class="toolbar">
        <el-select
          v-model="file"
          size="small"
          class="file-select"
          :disabled="!enabled || !files.length"
          @change="onFileChange"
        >
          <el-option v-for="name in files" :key="name" :label="name" :value="name" />
        </el-select>
        <el-switch v-model="live" size="small" inline-prompt active-text="实时" inactive-text="暂停" @change="onLiveChange" />
        <el-switch v-model="autoScroll" size="small" inline-prompt active-text="滚底" inactive-text="固定" @change="onAutoScrollChange" />
        <el-button size="small" :loading="loading" @click="onManualRefresh">刷新</el-button>
        <router-link to="/admin/settings" class="settings-link">日志配置</router-link>
      </div>
    </template>

    <el-alert
      v-if="!enabled"
      type="warning"
      :closable="false"
      title="文件日志已关闭，请在配置页启用后查看。"
      show-icon
      class="hint"
    />
    <p v-else class="dir-hint">目录：{{ logDir }}</p>

    <div ref="logRef" v-loading="loading" class="log-view" @scroll="onScroll">
      <pre>{{ content || '暂无日志' }}</pre>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useLogViewer } from '@/composables/useLogViewer'

const {
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
  stopPoll,
} = useLogViewer()

const logRef = ref<HTMLElement | null>(null)

const onScroll = () => {
  const el = logRef.value
  if (!el) return
  if (el.scrollTop + el.clientHeight < el.scrollHeight - 48 && autoScroll.value) {
    onAutoScrollChange(false)
  }
}

const onManualRefresh = async () => {
  await refresh(true)
  onAutoScrollChange(true)
}

watch(logRef, (el) => bindEl(el))

onMounted(reload)
onUnmounted(stopPoll)
</script>

<style scoped>
.panel {
  border: 1px solid var(--el-border-color-lighter);
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.file-select {
  width: 180px;
}

.settings-link {
  margin-left: auto;
  font-size: 13px;
  color: var(--el-color-primary);
  text-decoration: none;
}

.hint,
.dir-hint {
  margin: 0 0 12px;
}

.dir-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.log-view {
  height: min(70vh, 720px);
  overflow: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: #0f1117;
  padding: 12px;
}

.log-view pre {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #d4d4d8;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
