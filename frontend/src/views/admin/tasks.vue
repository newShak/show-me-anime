<template>
  <el-card shadow="never" class="panel">
    <template #header>
      <div class="panel-head">
        <div class="scan-actions">
          <el-button size="small" :loading="scanning === 'incremental'" @click="onScan('incremental')">
            增量扫描
          </el-button>
          <el-button type="primary" size="small" :loading="scanning === 'full'" @click="onScan('full')">
            全量扫描
          </el-button>
        </div>
      </div>
    </template>
    <el-table
      :data="records"
      :row-key="(row: TaskRecord) => `${row.task_type}-${row.id}`"
      size="small"
      stripe
      empty-text="暂无记录"
      v-loading="loading"
    >
      <el-table-column label="任务" width="112">
        <template #default="{ row }">{{ taskTypeLabel(row.task_type) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="88" align="center">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="来源" width="80" align="center">
        <template #default="{ row }">{{ sourceLabel(row.source) }}</template>
      </el-table-column>
      <el-table-column label="模式" width="72" align="center">
        <template #default="{ row }">
          {{ row.task_type === 'scan' ? scanModeLabel(row.mode) : '—' }}
        </template>
      </el-table-column>
      <el-table-column label="开始时间" min-width="160">
        <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
      </el-table-column>
      <el-table-column label="耗时" width="72" align="center">
        <template #default="{ row }">{{ formatDuration(row.started_at, row.finished_at) }}</template>
      </el-table-column>
      <el-table-column label="结果" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ formatTaskResult(row) }}</template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-if="total > 0"
      class="pagination"
      layout="total, prev, pager, next, sizes"
      :total="total"
      :current-page="page"
      :page-size="pageSize"
      :page-sizes="[10, 20, 50]"
      small
      @current-change="onPageChange"
      @size-change="onPageSizeChange"
    />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { triggerScan, type ScanMode } from '@/api/scan'
import { fetchTaskRecords } from '@/api/tasks'
import type { TaskRecord } from '@/types/task'
import {
  formatDuration,
  formatTaskResult,
  formatTime,
  scanModeLabel,
  sourceLabel,
  statusLabel,
  statusTagType,
  taskTypeLabel,
} from '@/utils/taskRecord'

const records = ref<TaskRecord[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)
const scanning = ref<ScanMode | false>(false)

const load = async (p = page.value) => {
  loading.value = true
  try {
    const { data } = await fetchTaskRecords(p, pageSize.value)
    records.value = data.items
    total.value = data.total
    page.value = data.page
  } finally {
    loading.value = false
  }
}

const onPageChange = (p: number) => {
  page.value = p
  load(p)
}

const onPageSizeChange = (size: number) => {
  pageSize.value = size
  page.value = 1
  load(1)
}

const onScan = async (mode: ScanMode) => {
  if (mode === 'full') {
    try {
      await ElMessageBox.confirm(
        '全量扫描会重新读取所有目录与压缩包，大图库可能耗时较长。是否继续？',
        '全量扫描',
        { type: 'warning', confirmButtonText: '开始', cancelButtonText: '取消' },
      )
    } catch {
      return
    }
  }
  scanning.value = mode
  try {
    const { data } = await triggerScan(mode)
    const label = mode === 'full' ? '全量扫描' : '增量扫描'
    ElMessage.success(`${label}完成：新增 ${data.added}，更新 ${data.updated}`)
    page.value = 1
    await load(1)
  } catch {
    ElMessage.error('扫描失败')
  } finally {
    scanning.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.panel {
  border: 1px solid var(--el-border-color-lighter);
}

.panel :deep(.el-card__header) {
  padding: 12px 16px;
}

.panel :deep(.el-card__body) {
  padding: 16px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.scan-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
