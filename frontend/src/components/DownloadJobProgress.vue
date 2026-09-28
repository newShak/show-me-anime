<template>
  <div class="jobs">
    <div v-for="job in jobs" :key="job.id" class="job-row">
      <div class="job-head">
        <span class="job-title">{{ job.title }}</span>
        <el-button
          v-if="job.status === 'failed'"
          type="primary"
          link
          size="small"
          :loading="retryingId === job.id"
          @click="emit('retry', job)"
        >
          重试
        </el-button>
      </div>
      <el-progress :percentage="job.progress" :status="status(job)" :stroke-width="6" />
      <p v-if="job.message" class="job-msg">{{ job.message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DownloadJob } from '@/types/download'

defineProps<{
  jobs: DownloadJob[]
  retryingId?: string | null
  status: (job: DownloadJob) => 'exception' | 'success' | undefined
}>()

const emit = defineEmits<{ retry: [job: DownloadJob] }>()
</script>

<style scoped>
.jobs {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.job-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.job-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.job-title {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  color: var(--app-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.job-msg {
  margin: 0;
  font-size: 11px;
  color: var(--app-text-muted);
  line-height: 1.3;
}
</style>
