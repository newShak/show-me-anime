<template>
  <el-card shadow="never" class="panel">
    <template #header>
      <div class="panel-head">
        <div class="head-actions">
          <el-button size="small" @click="purgeOpen = true">清理记录</el-button>
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

  <el-dialog v-model="purgeOpen" title="清理任务记录" width="520px" destroy-on-close @closed="resetPurge">
    <p class="purge-tip">将删除所选时间范围内开始的任务记录，进行中的扫描不会被删除。</p>
    <el-radio-group v-model="purgePreset" class="purge-presets">
      <el-radio value="day">最近一天</el-radio>
      <el-radio value="week">最近一周</el-radio>
      <el-radio value="month">最近一月</el-radio>
      <el-radio value="year">最近一年</el-radio>
      <el-radio value="custom">自定义时间</el-radio>
    </el-radio-group>
    <el-date-picker
      v-if="purgePreset === 'custom'"
      v-model="customRange"
      type="datetimerange"
      range-separator="至"
      start-placeholder="开始时间"
      end-placeholder="结束时间"
      value-format="x"
      class="purge-range"
    />
    <p v-if="purgeRangeText" class="purge-range-text">{{ purgeRangeText }}</p>
    <template #footer>
      <el-button @click="purgeOpen = false">取消</el-button>
      <el-button type="danger" :loading="purging" :disabled="!canPurge" @click="onPurge">
        删除记录
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { triggerScan, type ScanMode } from '@/api/scan'
import { fetchTaskRecords, purgeTaskRecords } from '@/api/tasks'
import type { TaskPurgePreset, TaskRecord } from '@/types/task'
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

const DAY_SEC = 86400
const PRESET_SPAN: Record<Exclude<TaskPurgePreset, 'custom'>, number> = {
  day: DAY_SEC,
  week: 7 * DAY_SEC,
  month: 30 * DAY_SEC,
  year: 365 * DAY_SEC,
}

const records = ref<TaskRecord[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)
const scanning = ref<ScanMode | false>(false)
const purgeOpen = ref(false)
const purgePreset = ref<TaskPurgePreset>('week')
const customRange = ref<[string, string] | null>(null)
const purging = ref(false)

const resolvePurgeRange = (): [number, number] | null => {
  if (purgePreset.value === 'custom') {
    if (!customRange.value?.length) return null
    const [startMs, endMs] = customRange.value
    return [Number(startMs) / 1000, Number(endMs) / 1000]
  }
  const end = Date.now() / 1000
  return [end - PRESET_SPAN[purgePreset.value], end]
}

const purgeRangeText = computed(() => {
  const range = resolvePurgeRange()
  if (!range) return ''
  return `将删除 ${formatTime(range[0])} 至 ${formatTime(range[1])} 之间的记录`
})

const canPurge = computed(() => resolvePurgeRange() !== null)

const resetPurge = () => {
  purgePreset.value = 'week'
  customRange.value = null
}

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

const onPurge = async () => {
  const range = resolvePurgeRange()
  if (!range) return
  const [startTime, endTime] = range
  try {
    await ElMessageBox.confirm(`${purgeRangeText.value}，此操作不可恢复。`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  purging.value = true
  try {
    const { data } = await purgeTaskRecords(startTime, endTime)
    ElMessage.success(`已删除 ${data.deleted} 条记录`)
    purgeOpen.value = false
    page.value = 1
    await load(1)
  } catch {
    ElMessage.error('删除失败')
  } finally {
    purging.value = false
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

.head-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.purge-tip {
  margin: 0 0 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.purge-presets {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}

.purge-range {
  width: 100%;
  margin-top: 12px;
}

.purge-range-text {
  margin: 12px 0 0;
  color: var(--el-text-color-regular);
  font-size: 13px;
}
</style>
