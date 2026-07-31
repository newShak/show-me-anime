<template>
  <el-drawer
    v-show="!fullscreen"
    v-model="visible"
    :size="560"
    @closed="onDrawerClosed"
  >
    <template #header>
      <div class="head">
        <span class="title">下载记录</span>
        <el-button text :icon="FullScreen" @click="enterFullscreen">全屏</el-button>
      </div>
    </template>
    <DownloadRecordTable
      :loading="records.loading.value"
      :items="records.items.value"
      :total="records.total.value"
      :page="records.page.value"
      :page-size="records.pageSize.value"
      :status-filter="records.statusFilter.value"
      :retrying-id="records.retryingId.value"
      :overwriting-id="records.overwritingId.value"
      :deleting-id="records.deletingId.value"
      @page-change="records.onPageChange"
      @page-size-change="records.onPageSizeChange"
      @status-change="records.onStatusChange"
      @retry="records.onRetry"
      @overwrite="records.onOverwrite"
      @delete="records.onDelete"
    />
  </el-drawer>

  <el-dialog
    v-model="fullscreen"
    fullscreen
    append-to-body
    class="record-fullscreen-dialog"
    @closed="onFullscreenClosed"
  >
    <template #header>
      <div class="head">
        <span class="title">下载记录</span>
        <el-button text :icon="Close" @click="exitFullscreen">退出全屏</el-button>
      </div>
    </template>
    <DownloadRecordTable
      is-fullscreen
      :loading="records.loading.value"
      :items="records.items.value"
      :total="records.total.value"
      :page="records.page.value"
      :page-size="records.pageSize.value"
      :status-filter="records.statusFilter.value"
      :retrying-id="records.retryingId.value"
      :overwriting-id="records.overwritingId.value"
      :deleting-id="records.deletingId.value"
      @page-change="records.onPageChange"
      @page-size-change="records.onPageSizeChange"
      @status-change="records.onStatusChange"
      @retry="records.onRetry"
      @overwrite="records.onOverwrite"
      @delete="records.onDelete"
    />
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Close, FullScreen } from '@element-plus/icons-vue'
import DownloadRecordTable from '@/components/DownloadRecordTable.vue'
import { useDownloadRecords } from '@/composables/useDownloadRecords'

const visible = defineModel<boolean>({ default: false })
const fullscreen = ref(false)
const directFullscreen = ref(false)

const active = computed(() => visible.value || fullscreen.value)
const records = useDownloadRecords(active)

const enterFullscreen = () => {
  directFullscreen.value = false
  fullscreen.value = true
}

const exitFullscreen = () => {
  fullscreen.value = false
  if (directFullscreen.value) visible.value = false
}

const onDrawerClosed = () => {
  fullscreen.value = false
  directFullscreen.value = false
  records.reset()
}

const onFullscreenClosed = () => {
  if (directFullscreen.value) visible.value = false
  directFullscreen.value = false
  if (!visible.value) records.reset()
}

watch(visible, (v) => {
  if (!v && !fullscreen.value) records.reset()
})

defineExpose({
  openFullscreen: () => {
    directFullscreen.value = true
    visible.value = true
    fullscreen.value = true
  },
})
</script>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 8px;
}

.title {
  font-size: 16px;
  font-weight: 600;
}
</style>

<style>
.record-fullscreen-dialog .el-dialog__body {
  padding-top: 8px;
}
</style>
