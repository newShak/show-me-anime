<template>
  <div class="settings-page">
    <div class="settings-layout">
      <el-card shadow="never" class="panel main-panel">
        <template #header><span class="panel-title">路径与监听</span></template>
        <el-form v-if="form" label-width="96px" class="settings-form">
          <section class="form-block">
            <h3 class="block-title">存储路径</h3>
            <el-form-item label="画廊根目录">
              <el-input v-model="form.gallery_root" />
            </el-form-item>
            <el-form-item label="缩略图目录">
              <el-input v-model="form.thumb_dir" />
            </el-form-item>
          </section>

          <section class="form-block">
            <h3 class="block-title">缩略图</h3>
            <el-form-item label="最大尺寸">
              <el-input-number v-model="form.thumb_max_size" :min="64" :max="2000" />
            </el-form-item>
            <el-form-item label="缓存">
              <el-button :loading="rebuildingThumbs" @click="onRebuildThumbs">重建缩略图</el-button>
            </el-form-item>
          </section>

          <section class="form-block">
            <h3 class="block-title">首页</h3>
            <el-form-item label="最近浏览条数">
              <el-input-number v-model="form.recent_view_limit" :min="1" :max="100" />
            </el-form-item>
            <el-form-item label="最近添加条数">
              <el-input-number v-model="form.recent_added_limit" :min="1" :max="100" />
            </el-form-item>
          </section>

          <section class="form-block">
            <h3 class="block-title">日志</h3>
            <el-form-item label="日志级别">
              <el-select v-model="form.log_level" style="width: 100%">
                <el-option v-for="opt in LOG_LEVEL_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="写入文件">
              <el-switch v-model="form.log_file_enabled" />
            </el-form-item>
            <el-form-item label="日志目录">
              <el-input v-model="form.log_dir" :disabled="!form.log_file_enabled" />
            </el-form-item>
            <el-form-item label="单文件上限">
              <el-input-number
                v-model="logFileMaxMb"
                :min="1"
                :max="100"
                :disabled="!form.log_file_enabled"
              />
              <span class="unit">MB（按天或超限滚动）</span>
            </el-form-item>
            <el-form-item label="保留天数">
              <el-input-number
                v-model="form.log_file_retention_days"
                :min="1"
                :max="365"
                :disabled="!form.log_file_enabled"
              />
            </el-form-item>
          </section>

          <section class="form-block">
            <h3 class="block-title">目录监听</h3>
            <el-form-item label="启用监听">
              <el-switch v-model="form.watch_enabled" />
            </el-form-item>
            <el-form-item label="防抖秒数">
              <el-input-number v-model="form.watch_debounce_seconds" :min="1" :max="60" />
            </el-form-item>
          </section>

          <div class="form-footer">
            <el-button type="primary" :loading="savingSettings" @click="onSaveSettings">保存配置</el-button>
          </div>
        </el-form>
        <el-skeleton v-else :rows="8" animated />
      </el-card>

      <div class="side-panels">
        <el-card shadow="never" class="panel">
          <template #header><span class="panel-title">浏览与收藏</span></template>
          <p class="local-hint">以下数据保存在服务端数据库，清空后所有设备同步生效。</p>
          <el-form label-width="108px" class="settings-form">
            <el-form-item label="最近浏览">
              <el-button @click="onClearRecentView">清空最近浏览</el-button>
            </el-form-item>
            <el-form-item label="我的最爱">
              <el-button @click="onClearFavorites">清空收藏</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never" class="panel">
          <template #header><span class="panel-title">本机偏好</span></template>
          <el-form label-width="108px" class="settings-form">
            <p class="local-hint">以下配置保存在当前浏览器，不会同步到服务器或其他设备。</p>
            <el-form-item label="搜索历史条数">
              <el-input-number
                v-model="searchHistoryLimit"
                :min="SEARCH_HISTORY_LIMIT_RANGE.min"
                :max="SEARCH_HISTORY_LIMIT_RANGE.max"
                @change="onSearchHistoryLimitChange"
              />
            </el-form-item>
            <el-form-item label="搜索历史">
              <el-button @click="onClearSearchHistory">清空搜索历史</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
    </div>
  </div>
</template>



<script setup lang="ts">

import { computed, onMounted, ref } from 'vue'

import { ElMessage, ElMessageBox } from 'element-plus'

import { fetchSettings, rebuildThumbs, saveSettings } from '@/api/settings'

import { clearRecentView } from '@/composables/useRecentView'

import { clearFavorites } from '@/composables/useFavorites'

import {

  clearSearchHistory,

  getSearchHistoryLimit,

  SEARCH_HISTORY_LIMIT_RANGE,

  setSearchHistoryLimit,

} from '@/composables/useSearchHistory'

import type { LogLevel, Settings } from '@/types/settings'



const LOG_LEVEL_OPTIONS: { label: string; value: LogLevel }[] = [

  { label: 'DEBUG（调试）', value: 'DEBUG' },

  { label: 'INFO（默认）', value: 'INFO' },

  { label: 'WARNING', value: 'WARNING' },

  { label: 'ERROR', value: 'ERROR' },

  { label: 'CRITICAL', value: 'CRITICAL' },

]



const form = ref<Settings | null>(null)
const logFileMaxMb = computed({
  get: () => Math.round((form.value?.log_file_max_bytes ?? 10 * 1024 * 1024) / (1024 * 1024)),
  set: (mb: number) => {
    if (form.value) form.value.log_file_max_bytes = mb * 1024 * 1024
  },
})

const savingSettings = ref(false)

const rebuildingThumbs = ref(false)

const searchHistoryLimit = ref(getSearchHistoryLimit())



const load = async () => {

  const { data } = await fetchSettings()

  form.value = { ...data }

}



const onSaveSettings = async () => {

  if (!form.value) return

  savingSettings.value = true

  try {

    const { data } = await saveSettings({

      gallery_root: form.value.gallery_root,

      thumb_dir: form.value.thumb_dir,

      thumb_max_size: form.value.thumb_max_size,

      watch_enabled: form.value.watch_enabled,

      watch_debounce_seconds: form.value.watch_debounce_seconds,

      log_level: form.value.log_level,

      log_dir: form.value.log_dir,

      log_file_enabled: form.value.log_file_enabled,

      log_file_max_bytes: form.value.log_file_max_bytes,

      log_file_retention_days: form.value.log_file_retention_days,

      recent_view_limit: form.value.recent_view_limit,

      recent_added_limit: form.value.recent_added_limit,

    })

    form.value = { ...data }

    ElMessage.success(data.message ?? '配置已保存')

    if (data.needs_rescan) ElMessage.warning('画廊根目录已变更，请到任务执行记录页重新扫描')

  } catch {

    ElMessage.error('保存失败')

  } finally {

    savingSettings.value = false

  }

}



const onSearchHistoryLimitChange = (val: number | undefined) => {

  if (val == null) return

  searchHistoryLimit.value = setSearchHistoryLimit(val)

  ElMessage.success('搜索历史条数已更新')

}



const onClearRecentView = async () => {

  try {

    await ElMessageBox.confirm('确定清空最近浏览记录？', '清空最近浏览', {

      type: 'warning',

      confirmButtonText: '清空',

      cancelButtonText: '取消',

    })

  } catch {

    return

  }

  await clearRecentView()

  ElMessage.success('已清空最近浏览')

}



const onClearFavorites = async () => {

  try {

    await ElMessageBox.confirm('确定清空所有收藏？', '清空收藏', {

      type: 'warning',

      confirmButtonText: '清空',

      cancelButtonText: '取消',

    })

  } catch {

    return

  }

  await clearFavorites()

  ElMessage.success('已清空收藏')

}



const onClearSearchHistory = async () => {

  try {

    await ElMessageBox.confirm('确定清空本机所有搜索历史？', '清空搜索历史', {

      type: 'warning',

      confirmButtonText: '清空',

      cancelButtonText: '取消',

    })

  } catch {

    return

  }

  clearSearchHistory()

  ElMessage.success('已清空搜索历史')

}



const onRebuildThumbs = async () => {

  try {

    await ElMessageBox.confirm(

      '将清空缩略图缓存目录，下次浏览相册时会按当前尺寸重新生成。原图不受影响。',

      '重建缩略图',

      { type: 'warning', confirmButtonText: '重建', cancelButtonText: '取消' },

    )

  } catch {

    return

  }

  rebuildingThumbs.value = true

  try {

    const { data } = await rebuildThumbs()

    ElMessage.success(data.message)

  } catch {

    ElMessage.error('重建失败')

  } finally {

    rebuildingThumbs.value = false

  }

}



onMounted(load)

</script>



<style scoped>
.settings-page {
  max-width: var(--app-page-width, 960px);
}

.settings-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
  align-items: start;
}

.side-panels {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel {
  border: 1px solid var(--el-border-color-lighter);
}

.panel :deep(.el-card__header) {
  padding: 12px 16px;
}

.panel :deep(.el-card__body) {
  padding: 16px;
}

.panel-title {
  font-weight: 600;
  font-size: 14px;
}

.form-block + .form-block {
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.block-title {
  margin: 0 0 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
}

.settings-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.form-footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.unit {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.local-hint {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

@media (max-width: 860px) {
  .settings-layout {
    grid-template-columns: 1fr;
  }
}
</style>

