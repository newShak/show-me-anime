<template>
  <div class="record-table" :class="{ fullscreen: isFullscreen }">
    <el-table v-loading="loading" :data="items" :size="isFullscreen ? 'default' : 'small'" stripe empty-text="暂无记录">
      <el-table-column label="标题" :min-width="isFullscreen ? 200 : 120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.title }}</template>
      </el-table-column>
      <el-table-column label="状态" :width="isFullscreen ? 100 : 88" align="center">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          <el-tag v-if="row.target_existed" type="info" size="small" class="skip-tag">路径已存在</el-tag>
          <el-tag v-if="row.skipped_files > 0" type="warning" size="small" class="skip-tag">
            跳过 {{ row.skipped_files }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="进度" :min-width="isFullscreen ? 240 : 180">
        <template #default="{ row }">
          <el-progress
            :percentage="row.progress"
            :status="progressStatus(row)"
            :stroke-width="8"
            :striped="isActive(row)"
            :striped-flow="isActive(row)"
          />
          <p v-if="row.message" class="msg">{{ row.message }}</p>
        </template>
      </el-table-column>
      <el-table-column label="路径" :min-width="isFullscreen ? 180 : 100" show-overflow-tooltip>
        <template #default="{ row }">{{ row.target_rel_path }}</template>
      </el-table-column>
      <el-table-column label="时间" :width="isFullscreen ? 168 : 140">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" :width="isFullscreen ? 140 : 120" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'failed'"
            type="primary"
            link
            size="small"
            :loading="retryingId === row.id"
            @click="emit('retry', row)"
          >
            重试
          </el-button>
          <el-button
            v-if="row.can_overwrite"
            type="warning"
            link
            size="small"
            :loading="overwritingId === row.id"
            @click="emit('overwrite', row)"
          >
            强制覆盖
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-if="total > pageSize"
      class="pager"
      layout="total, prev, pager, next"
      :small="!isFullscreen"
      :total="total"
      :current-page="page"
      :page-size="pageSize"
      @current-change="(p: number) => emit('page-change', p)"
    />
  </div>
</template>

<script setup lang="ts">
import type { DownloadRecord } from '@/types/download'

defineProps<{
  loading: boolean
  items: DownloadRecord[]
  total: number
  page: number
  pageSize: number
  retryingId: string | null
  overwritingId: string | null
  isFullscreen?: boolean
}>()

const emit = defineEmits<{
  'page-change': [page: number]
  retry: [row: DownloadRecord]
  overwrite: [row: DownloadRecord]
}>()

const isActive = (row: DownloadRecord) => row.status === 'pending' || row.status === 'running'

const statusType = (status: string) => {
  if (status === 'done') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  return 'info'
}

const progressStatus = (row: DownloadRecord) => {
  if (row.status === 'failed') return 'exception'
  if (row.status === 'done') return 'success'
  return undefined
}

const statusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: '等待',
    running: '下载中',
    done: '完成',
    failed: '失败',
  }
  return map[status] ?? status
}

const formatTime = (ts: number) => new Date(ts * 1000).toLocaleString()
</script>

<style scoped>
.msg {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--app-text-muted);
  line-height: 1.3;
}

.skip-tag {
  margin-top: 4px;
}

.pager {
  margin-top: 16px;
  justify-content: center;
}

.record-table.fullscreen {
  padding: 0 8px 16px;
}
</style>
